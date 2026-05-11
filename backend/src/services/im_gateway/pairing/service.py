# -*- coding: utf-8 -*-
"""
PairingService —— IM 配对授权业务门面（P3-B）

业务闭环（参考 Accio Work「配对授权」交互）:

1. 用户在 IM 渠道（飞书 / 微信群）@bot 发送配对请求
   → ``create_pairing_request()`` 落库一条 ``PENDING`` 记录，
   ``expires_at = now + 24h``
2. 管理员在管理后台 / IM 卡片中点 "通过" / "驳回"
   → ``approve()`` 写入 ``IMBinding`` 并尝试通过 FeishuAdapter 回执
   → ``reject(reason=...)`` 标记为 ``REJECTED``
3. 24h 未处理则被 Celery beat 任务扫描置为 ``EXPIRED``
   → ``cleanup_expired()``

与 ``models/approval.py``（合同/文档/案件审批）业务域完全分离：
独占 ``im_gateway_pairings`` 表，不复用 ``approvals`` 表，避免审批链
触发器、模板、通知等通用流程被 IM 配对污染。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from loguru import logger
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.im_gateway.models import (
    IMBinding,
    PairingRequest,
    PairingStatus,
)


# 24 小时配对窗口（业务规则）
PAIRING_WINDOW = timedelta(hours=24)


class PairingNotFoundError(LookupError):
    """配对请求不存在。"""


class PairingNotPendingError(RuntimeError):
    """配对请求不在 PENDING 状态（可能已审批 / 驳回 / 过期）。"""

    def __init__(self, current: PairingStatus) -> None:
        super().__init__(f"配对请求当前状态为 {current.value}，无法执行该操作")
        self.current = current


class PairingExpiredError(RuntimeError):
    """配对请求已过期但状态尚未被 worker 同步（兜底保护）。"""


class PairingService:
    """配对授权业务服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # 创建
    # ------------------------------------------------------------------
    async def create_pairing_request(
        self,
        *,
        channel_id: str,
        external_user_id: str,
        external_user_name: str | None = None,
    ) -> PairingRequest:
        """创建一条 24h 过期窗口的 ``PENDING`` 配对请求。

        参数：
            channel_id: ``im_gateway_channels.id``
            external_user_id: 平台侧用户 ID（飞书 ``open_id`` / Slack ``Uxxx`` 等）
            external_user_name: 平台侧昵称（仅日志记录，不入库 — 当前模型未冗余该列）

        返回：
            刚 flush 的 ``PairingRequest`` 实例（含 ``id`` / ``expires_at``）。
        """
        now = datetime.now(timezone.utc)
        request = PairingRequest(
            channel_id=channel_id,
            external_user_id=external_user_id,
            status=PairingStatus.PENDING,
            expires_at=now + PAIRING_WINDOW,
        )
        self.session.add(request)
        await self.session.flush()
        await self.session.refresh(request)

        logger.info(
            "im_pairing.create channel={} ext_user={} name={} expires_at={}",
            channel_id,
            external_user_id,
            external_user_name,
            request.expires_at.isoformat(),
        )
        return request

    # ------------------------------------------------------------------
    # 审批
    # ------------------------------------------------------------------
    async def approve(self, request_id: str, approver_id: str) -> IMBinding:
        """通过审批：写入 ``IMBinding``、把请求置 APPROVED、回执 IM 卡片。

        - 已是 APPROVED 的请求会幂等返回已有绑定（按 channel_id+external_user_id 查）
        - REJECTED / EXPIRED 不允许再 approve（抛 ``PairingNotPendingError``）
        - 兜底过期保护：``expires_at < now`` 会先把状态置 EXPIRED 再抛错
        """
        request = await self._get_or_raise(request_id)

        if request.status == PairingStatus.APPROVED:
            existing = await self._get_existing_binding(
                request.channel_id, request.external_user_id
            )
            if existing is not None:
                return existing
            # 状态是 APPROVED 但 binding 缺失（极少数异常）—— fallthrough 重建
        elif request.status != PairingStatus.PENDING:
            raise PairingNotPendingError(request.status)

        now = datetime.now(timezone.utc)
        if self._is_expired(request, now):
            request.status = PairingStatus.EXPIRED
            await self.session.flush()
            raise PairingExpiredError(
                f"配对请求 {request_id} 已过期 (expires_at={request.expires_at.isoformat()})"
            )

        # 1. 创建 / 复用 binding（approver 即代表内部用户）
        binding = await self._get_existing_binding(
            request.channel_id, request.external_user_id
        )
        if binding is None:
            binding = IMBinding(
                channel_id=request.channel_id,
                external_user_id=request.external_user_id,
                internal_user_id=approver_id,
                bound_at=now,
            )
            self.session.add(binding)

        # 2. 推进 pairing 状态
        request.status = PairingStatus.APPROVED
        request.approved_at = now

        await self.session.flush()
        await self.session.refresh(binding)
        await self.session.refresh(request)

        # 3. 回执 IM 卡片（best-effort，失败不影响审批主流程）
        await self._send_approval_receipt(request, binding, approver_id)

        logger.info(
            "im_pairing.approve request_id={} channel={} ext_user={} approver={} binding_id={}",
            request_id,
            request.channel_id,
            request.external_user_id,
            approver_id,
            binding.id,
        )
        return binding

    async def reject(
        self,
        request_id: str,
        approver_id: str,
        reason: str,
    ) -> PairingRequest:
        """驳回审批：标记为 REJECTED 并记录驳回理由日志。"""
        if not reason or not reason.strip():
            raise ValueError("驳回必须填写理由")

        request = await self._get_or_raise(request_id)

        if request.status not in (PairingStatus.PENDING,):
            raise PairingNotPendingError(request.status)

        request.status = PairingStatus.REJECTED
        await self.session.flush()
        await self.session.refresh(request)

        logger.info(
            "im_pairing.reject request_id={} channel={} ext_user={} approver={} reason={}",
            request_id,
            request.channel_id,
            request.external_user_id,
            approver_id,
            reason,
        )
        return request

    # ------------------------------------------------------------------
    # 列表查询
    # ------------------------------------------------------------------
    async def list_pending(
        self,
        channel_id: str | None = None,
        limit: int = 50,
    ) -> list[PairingRequest]:
        """列出未处理且未过期的 PENDING 请求（按 created_at 倒序）。"""
        now = datetime.now(timezone.utc)
        stmt = (
            select(PairingRequest)
            .where(PairingRequest.status == PairingStatus.PENDING)
            .where(PairingRequest.expires_at > now)
        )
        if channel_id:
            stmt = stmt.where(PairingRequest.channel_id == channel_id)
        stmt = stmt.order_by(desc(PairingRequest.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_authorized(
        self,
        channel_id: str | None = None,
        limit: int = 50,
    ) -> list[IMBinding]:
        """列出已生效的绑定（按 bound_at 倒序）。"""
        stmt = select(IMBinding)
        if channel_id:
            stmt = stmt.where(IMBinding.channel_id == channel_id)
        stmt = stmt.order_by(desc(IMBinding.bound_at)).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # 过期清理
    # ------------------------------------------------------------------
    async def cleanup_expired(self) -> int:
        """把所有 ``PENDING`` 且 ``expires_at < now`` 的请求置为 ``EXPIRED``。

        返回更新的行数。供 Celery beat 周期任务调用。
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(PairingRequest)
            .where(PairingRequest.status == PairingStatus.PENDING)
            .where(PairingRequest.expires_at < now)
            .values(status=PairingStatus.EXPIRED)
            # ``fetch`` 让 DB 直接做 WHERE 过滤，再回填 ORM；避免 SQLite 测试场景下
            # ORM 默认 ``evaluate`` 同步策略对 naive vs aware datetime 的本地比较异常。
            .execution_options(synchronize_session="fetch")
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        affected = int(result.rowcount or 0)
        if affected:
            logger.info("im_pairing.cleanup_expired affected={} now={}", affected, now.isoformat())
        return affected

    # ------------------------------------------------------------------
    # 内部 helper
    # ------------------------------------------------------------------
    async def _get_or_raise(self, request_id: str) -> PairingRequest:
        result = await self.session.execute(
            select(PairingRequest).where(PairingRequest.id == request_id)
        )
        request = result.scalar_one_or_none()
        if request is None:
            raise PairingNotFoundError(f"配对请求不存在: {request_id}")
        return request

    async def _get_existing_binding(
        self,
        channel_id: str,
        external_user_id: str,
    ) -> IMBinding | None:
        result = await self.session.execute(
            select(IMBinding)
            .where(IMBinding.channel_id == channel_id)
            .where(IMBinding.external_user_id == external_user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _is_expired(request: PairingRequest, now: datetime) -> bool:
        # PostgreSQL 返回 tz-aware；SQLite 测试可能返回 naive，统一兼容
        expires_at = request.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at < now

    async def _send_approval_receipt(
        self,
        request: PairingRequest,
        binding: IMBinding,
        approver_id: str,
    ) -> None:
        """通过飞书 adapter 发审批通过卡片回执（失败不抛）。

        - 通道类型不是 FEISHU 时跳过（其它平台 P3 之后再实装）
        - registry / adapter 不可用时仅打 warning
        """
        try:
            from src.services.im_gateway.models import IMChannel, IMChannelType
            from src.services.im_gateway.registry import IMAdapterRegistry
        except Exception:  # pragma: no cover - 防御性
            return

        try:
            channel_row = await self.session.get(IMChannel, request.channel_id)
            if channel_row is None:
                return
            if channel_row.channel_type != IMChannelType.FEISHU:
                return
            adapter = IMAdapterRegistry.get(channel_row.channel_type)
            await adapter.send_message(
                channel_id=request.channel_id,
                target=request.external_user_id,
                content=self._build_approval_card_payload(request, binding, approver_id),
            )
        except Exception as e:  # 回执失败不影响审批主流程
            logger.warning(
                "im_pairing.receipt_failed request_id={} err={}",
                request.id,
                e,
            )

    @staticmethod
    def _build_approval_card_payload(
        request: PairingRequest,
        binding: IMBinding,
        approver_id: str,
    ) -> dict[str, Any]:
        """构造飞书审批通过回执卡片 payload（结构契合 FeishuAdapter.send_message）。"""
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "✅ 配对授权已通过"},
                    "template": "green",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": (
                                f"**外部账号**: {request.external_user_id}\n"
                                f"**绑定内部用户**: {binding.internal_user_id}\n"
                                f"**审批人**: {approver_id}\n"
                                f"**生效时间**: {binding.bound_at.isoformat()}"
                            ),
                        },
                    }
                ],
            },
        }
