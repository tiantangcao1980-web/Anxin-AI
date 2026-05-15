"""
PairingService 单元测试（P3-B）

覆盖 5 个核心方法：
    - create_pairing_request   : 24h 过期窗口
    - approve                  : 创建 IMBinding
    - reject                   : 标记 REJECTED + reason 必填
    - cleanup_expired          : 把 PENDING 过期请求改 EXPIRED
    - list_pending             : channel_id 过滤

通过 conftest 的 ``db_session`` fixture 在 SQLite 内存库跑（StaticPool）。
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# SQLite ↔ PostgreSQL JSONB 兼容补丁（必须在导入 im_gateway.models 之前生效）
#
# im_gateway/models.py 直接用了 ``sqlalchemy.dialects.postgresql.JSONB``，
# 在生产 PostgreSQL 上工作良好；但 conftest 里默认走 SQLite 内存库做 ``create_all``
# 时 SQLite 方言不识别 JSONB DDL，会抛 CompileError。
#
# 这里通过给 ``SQLiteTypeCompiler`` 注入 ``visit_JSONB`` 回退到 ``visit_JSON``，
# 保持线上模型不变（不修改 im_gateway/models.py）。
# ---------------------------------------------------------------------------
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler as _SQLiteTC

if not hasattr(_SQLiteTC, "visit_JSONB"):

    def _visit_JSONB(self, type_, **kw):  # noqa: N802 — SQLAlchemy visitor naming
        return self.visit_JSON(type_, **kw)

    _SQLiteTC.visit_JSONB = _visit_JSONB  # type: ignore[attr-defined]


from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# 触发 ORM 表注册 — 导入即注册到 Base.metadata
from src.services.im_gateway.models import (  # noqa: F401
    IMBinding,
    IMChannel,
    IMChannelType,
    PairingRequest,
    PairingStatus,
)
from src.services.im_gateway.pairing.service import (
    PAIRING_WINDOW,
    PairingNotPendingError,
    PairingService,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
#
# 备注：im_gateway_* 三张表通过本模块顶部的 ``import ... models`` 副作用注册到
# ``Base.metadata``，conftest 的 session-scope ``setup_test_db`` 会统一 create_all
# （配合上面的 SQLite-JSONB 兼容补丁）。因此这里无需再做按需建表。


async def _make_channel(db_session: AsyncSession) -> IMChannel:
    channel = IMChannel(
        id=str(uuid4()),
        channel_type=IMChannelType.FEISHU,
        name="测试飞书机器人",
        config={"app_id": "cli_xxx"},
        enabled=True,
    )
    db_session.add(channel)
    await db_session.flush()
    return channel


async def _make_user(db_session: AsyncSession):
    """创建一个带 org 的最小 User，用于 IMBinding.internal_user_id 外键。"""
    from src.models.user import Organization, User

    org = Organization(id=str(uuid4()), name="审批人组织")
    db_session.add(org)
    await db_session.flush()

    user = User(
        id=str(uuid4()),
        email=f"approver-{uuid4().hex[:8]}@example.com",
        name="审批人",
        hashed_password="x",
        org_id=org.id,
        is_active=True,
        role="admin",
    )
    db_session.add(user)
    await db_session.flush()
    return user


# ---------------------------------------------------------------------------
# 用例
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_request_24h_window(db_session: AsyncSession) -> None:
    channel = await _make_channel(db_session)
    service = PairingService(db_session)

    before = datetime.now(UTC)
    request = await service.create_pairing_request(
        channel_id=channel.id,
        external_user_id="ou_feishu_user_001",
        external_user_name="张三",
    )
    after = datetime.now(UTC)

    assert request.id is not None
    assert request.status == PairingStatus.PENDING
    assert request.channel_id == channel.id
    assert request.external_user_id == "ou_feishu_user_001"

    # SQLite 可能返回 naive datetime，统一比较
    expires = request.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)

    expected_min = before + PAIRING_WINDOW - timedelta(seconds=2)
    expected_max = after + PAIRING_WINDOW + timedelta(seconds=2)
    assert expected_min <= expires <= expected_max
    assert (expires - before) >= timedelta(hours=23, minutes=59)


@pytest.mark.asyncio
async def test_approve_creates_binding(db_session: AsyncSession) -> None:
    channel = await _make_channel(db_session)
    user = await _make_user(db_session)
    service = PairingService(db_session)

    request = await service.create_pairing_request(
        channel_id=channel.id,
        external_user_id="ou_to_approve",
    )

    binding = await service.approve(request.id, approver_id=str(user.id))

    assert binding.id is not None
    assert binding.channel_id == channel.id
    assert binding.external_user_id == "ou_to_approve"
    assert binding.internal_user_id == str(user.id)
    assert binding.bound_at is not None

    # 请求状态推进
    await db_session.refresh(request)
    assert request.status == PairingStatus.APPROVED
    assert request.approved_at is not None

    # 幂等：再次 approve 同一 request 返回同一 binding
    binding2 = await service.approve(request.id, approver_id=str(user.id))
    assert binding2.id == binding.id


@pytest.mark.asyncio
async def test_reject_with_reason(db_session: AsyncSession) -> None:
    channel = await _make_channel(db_session)
    user = await _make_user(db_session)
    service = PairingService(db_session)

    request = await service.create_pairing_request(
        channel_id=channel.id,
        external_user_id="ou_to_reject",
    )

    rejected = await service.reject(
        request.id,
        approver_id=str(user.id),
        reason="非授权员工",
    )
    assert rejected.status == PairingStatus.REJECTED

    # reason 必填 — 空字符串应抛 ValueError
    request2 = await service.create_pairing_request(
        channel_id=channel.id,
        external_user_id="ou_to_reject_2",
    )
    with pytest.raises(ValueError):
        await service.reject(request2.id, approver_id=str(user.id), reason="   ")

    # REJECTED 后再 reject 应抛 PairingNotPendingError
    with pytest.raises(PairingNotPendingError):
        await service.reject(rejected.id, approver_id=str(user.id), reason="重复驳回")


@pytest.mark.asyncio
async def test_cleanup_expired_marks_status(db_session: AsyncSession) -> None:
    channel = await _make_channel(db_session)
    service = PairingService(db_session)

    # 1 条已过期
    expired_req = PairingRequest(
        channel_id=channel.id,
        external_user_id="ou_expired",
        status=PairingStatus.PENDING,
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    # 1 条未过期
    fresh_req = PairingRequest(
        channel_id=channel.id,
        external_user_id="ou_fresh",
        status=PairingStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(hours=2),
    )
    db_session.add_all([expired_req, fresh_req])
    await db_session.flush()

    affected = await service.cleanup_expired()
    assert affected == 1

    await db_session.refresh(expired_req)
    await db_session.refresh(fresh_req)
    assert expired_req.status == PairingStatus.EXPIRED
    assert fresh_req.status == PairingStatus.PENDING

    # 再跑一次幂等 — 0 条受影响
    affected2 = await service.cleanup_expired()
    assert affected2 == 0


@pytest.mark.asyncio
async def test_list_pending_filter_by_channel(db_session: AsyncSession) -> None:
    channel_a = await _make_channel(db_session)
    channel_b = await _make_channel(db_session)
    service = PairingService(db_session)

    req_a1 = await service.create_pairing_request(
        channel_id=channel_a.id, external_user_id="ext_a1"
    )
    req_a2 = await service.create_pairing_request(
        channel_id=channel_a.id, external_user_id="ext_a2"
    )
    req_b1 = await service.create_pairing_request(
        channel_id=channel_b.id, external_user_id="ext_b1"
    )

    pending_a = await service.list_pending(channel_id=channel_a.id)
    pending_b = await service.list_pending(channel_id=channel_b.id)
    pending_all = await service.list_pending()

    a_ids = {r.id for r in pending_a}
    b_ids = {r.id for r in pending_b}
    assert {req_a1.id, req_a2.id} <= a_ids
    assert req_b1.id not in a_ids
    assert {req_b1.id} <= b_ids
    assert req_a1.id not in b_ids

    all_ids = {r.id for r in pending_all}
    assert {req_a1.id, req_a2.id, req_b1.id} <= all_ids
