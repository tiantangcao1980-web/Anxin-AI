"""
合同审查服务
"""

import asyncio
import difflib
import hashlib
import re
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import settings
from src.models.contract import (
    Contract,
    ContractAttachment,
    ContractRisk,
    ContractStatus,
    ContractVersion,
    RiskLevel,
)
from src.services.contract_lifecycle_service import ContractLifecycleStateMachine
from src.services.contract_review_lock import ContractReviewLock
from src.services.object_storage_service import ObjectStorageService, get_object_storage

if TYPE_CHECKING:
    from src.agents.workforce import LegalWorkforce

JSONDict = dict[str, Any]
RiskPayload = dict[str, Any]


class ContractReviewTimeoutError(TimeoutError):
    """Raised when contract review exceeds the configured business timeout."""


class ContractReviewExecutionError(RuntimeError):
    """Raised when contract review fails after the contract was marked retryable."""


class ContractService:
    """合同审查服务"""

    def __init__(
        self,
        db: AsyncSession,
        object_storage: ObjectStorageService | None = None,
    ):
        self.db = db
        self._workforce: LegalWorkforce | None = None
        self.object_storage = object_storage or get_object_storage()
        self.review_lock = ContractReviewLock()

    @property
    def workforce(self) -> "LegalWorkforce":
        """延迟导入 workforce，避免循环依赖"""
        if self._workforce is None:
            from src.agents.workforce import get_workforce

            self._workforce = get_workforce()
        return self._workforce

    async def create_contract(
        self,
        title: str,
        contract_type: str,
        document_id: str | None = None,
        org_id: str | None = None,
        party_a: JSONDict | None = None,
        party_b: JSONDict | None = None,
        amount: float | None = None,
        effective_date: date | None = None,
        expiry_date: date | None = None,
    ) -> Contract:
        """创建合同记录"""
        contract_number = f"CONTRACT-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"

        contract = Contract(
            title=title,
            contract_number=contract_number,
            contract_type=contract_type,
            status=ContractStatus.DRAFT,
            document_id=document_id,
            org_id=org_id,
            party_a=party_a,
            party_b=party_b,
            amount=amount,
            effective_date=effective_date,
            expiry_date=expiry_date,
        )

        self.db.add(contract)
        await self.db.flush()

        logger.info(f"合同创建成功: {contract.contract_number}")
        return contract

    async def get_contract(self, contract_id: str, org_id: str | None = None) -> Contract | None:
        """获取合同详情"""
        query = (
            select(Contract)
            .options(selectinload(Contract.clauses))
            .options(selectinload(Contract.risks))
            .where(Contract.id == contract_id)
        )
        if org_id:
            query = query.where(Contract.org_id == org_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_contracts(
        self,
        org_id: str | None = None,
        status: str | None = None,
        contract_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Contract], int]:
        """获取合同列表"""
        query = select(Contract)
        count_query = select(func.count(Contract.id))

        conditions = []
        if org_id:
            conditions.append(Contract.org_id == org_id)
        if status:
            conditions.append(Contract.status == ContractStatus(status))
        if contract_type:
            conditions.append(Contract.contract_type == contract_type)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Contract.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        contracts = list(result.scalars().all())

        return contracts, total

    async def review_contract(
        self,
        contract_id: str,
        contract_text: str,
        reviewed_by: str | None = None,
        org_id: str | None = None,
    ) -> JSONDict:
        """
        AI审查合同

        Args:
            contract_id: 合同ID
            contract_text: 合同文本内容
            reviewed_by: 审核人ID

        Returns:
            审查结果
        """
        contract = await self.get_contract(contract_id, org_id=org_id)
        if not contract:
            raise ValueError("合同不存在")

        lock_key = self._review_lock_key(contract)
        timeout_seconds = max(float(settings.CONTRACT_REVIEW_TIMEOUT_SECONDS), 0.01)
        lock_ttl = max(int(settings.CONTRACT_REVIEW_LOCK_TTL_SECONDS), int(timeout_seconds) + 30)
        lock_token = await self.review_lock.acquire(lock_key, ttl_seconds=lock_ttl)

        # T7: 创建 task_engine 状态机记录
        from src.harness.task_engine import TaskContract, TaskState, task_engine
        task_record = task_engine.create_task(
            description=f"合同审查: {contract.title[:80]}",
            route="contract_review",
            agent_name="contract_reviewer",
            user_id=reviewed_by,
            contract=TaskContract(
                goal="审查合同, 识别风险点, 提供修改建议",
                success_criteria=["返回 risks 列表", "返回 risk_score", "返回 summary"],
                output_format="json",
                timeout_seconds=int(timeout_seconds),
            ),
        )
        task_engine.transition(task_record.task_id, TaskState.RUNNING)

        try:
            # 保存原始合同文本
            contract.original_text = contract_text
            await self._ensure_initial_version(
                contract,
                actor_id=reviewed_by,
                description="contract review source",
            )

            ContractLifecycleStateMachine.transition(
                contract,
                ContractStatus.UNDER_REVIEW,
                actor_id=reviewed_by,
                reason="contract_review_started",
            )
            await self.db.flush()

            # 调用合同审查智能体
            task_description = f"""
请审查以下合同文本，识别风险点并提供修改建议：

合同名称：{contract.title}
合同类型：{contract.contract_type}

合同内容：
{contract_text[:10000]}  # 限制长度
"""

            try:
                result = await asyncio.wait_for(
                    self.workforce.process_task_governed(
                        task_description=task_description,
                        task_type="contract_review",
                        context={
                            "contract_id": contract_id,
                            "contract_type": contract.contract_type,
                        },
                    ),
                    timeout=timeout_seconds,
                )
            except TimeoutError as exc:
                task_engine.transition(task_record.task_id, TaskState.TIMEOUT, error_msg=str(exc))
                await self._mark_review_failed(
                    contract,
                    actor_id=reviewed_by,
                    reason="contract_review_timeout",
                    message=f"合同审查超过 {timeout_seconds} 秒，请稍后重试",
                )
                raise ContractReviewTimeoutError("合同审查超时，请稍后重试") from exc
            except Exception as exc:
                task_engine.transition(task_record.task_id, TaskState.FAILED, error_msg=str(exc))
                await self._mark_review_failed(
                    contract,
                    actor_id=reviewed_by,
                    reason="contract_review_failed",
                    message="合同审查失败，请稍后重试",
                )
                raise ContractReviewExecutionError("合同审查失败，请稍后重试") from exc

            # 解析审查结果
            review_result = self._normalize_review_result(result.get("final_result", {}))

            # 计算风险评分
            risk_score = self._calculate_risk_score(review_result)
            risk_level = self._get_risk_level(risk_score)

            # 更新合同信息
            contract.review_result = review_result
            contract.risk_score = risk_score
            contract.risk_level = risk_level
            contract.review_summary = review_result.get("summary", "")
            ContractLifecycleStateMachine.transition(
                contract,
                ContractStatus.PENDING_REVIEW,
                actor_id=reviewed_by,
                reason="contract_review_completed",
            )
            contract.reviewed_by = reviewed_by

            await self.db.flush()

            # 保存风险点
            await self._save_risks(contract_id, review_result.get("risks", []))

            logger.info(f"合同审查完成: {contract.contract_number}, 风险等级: {risk_level}")

            task_engine.transition(
                task_record.task_id, TaskState.COMPLETED, result={"risk_level": str(risk_level), "risk_score": risk_score}
            )

            return {
                "contract_id": contract_id,
                "task_id": task_record.task_id,
                "risk_score": risk_score,
                "risk_level": risk_level.value if risk_level else None,
                "summary": review_result.get("summary", ""),
                "risks": review_result.get("risks", []),
                "suggestions": review_result.get("suggestions", []),
                "key_terms": review_result.get("key_terms", {}),
                "missing_clauses": review_result.get("missing_clauses", []),
            }
        finally:
            await self.review_lock.release(lock_key, lock_token)

    def _calculate_risk_score(self, review_result: JSONDict) -> float:
        """计算风险评分"""
        risks = review_result.get("risks", [])
        if not risks:
            return 0.1

        # 根据风险数量和等级计算评分
        risk_weights = {
            "critical": 0.4,
            "high": 0.25,
            "medium": 0.1,
            "low": 0.05,
        }

        total_score = 0.0
        for risk in risks:
            level = risk.get("level", "medium").lower()
            total_score += risk_weights.get(level, 0.1)

        return min(total_score, 1.0)

    def _get_risk_level(self, score: float) -> RiskLevel:
        """根据评分获取风险等级"""
        if score >= 0.7:
            return RiskLevel.CRITICAL
        elif score >= 0.5:
            return RiskLevel.HIGH
        elif score >= 0.3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _normalize_review_result(self, review_result: JSONDict | None) -> JSONDict:
        if not isinstance(review_result, dict):
            review_result = {}

        risks = review_result.get("risks")
        key_risks = review_result.get("key_risks")

        if not isinstance(risks, list):
            risks = key_risks if isinstance(key_risks, list) else []

        suggestions = review_result.get("suggestions")
        key_terms = review_result.get("key_terms")
        missing_clauses = review_result.get("missing_clauses")

        return {
            **review_result,
            "summary": review_result.get("summary", ""),
            "risks": risks,
            "suggestions": suggestions if isinstance(suggestions, list) else [],
            "key_terms": key_terms if isinstance(key_terms, dict) else {},
            "missing_clauses": missing_clauses if isinstance(missing_clauses, list) else [],
        }

    async def _mark_review_failed(
        self,
        contract: Contract,
        *,
        actor_id: str | None,
        reason: str,
        message: str,
    ) -> None:
        ContractLifecycleStateMachine.transition(
            contract,
            ContractStatus.REVIEW_FAILED,
            actor_id=actor_id,
            reason=reason,
        )
        contract.review_result = {
            "status": "failed",
            "reason": reason,
            "message": message,
        }
        contract.review_summary = message
        await self.db.flush()

    @staticmethod
    def _review_lock_key(contract: Contract) -> str:
        review_round = contract.version or 1
        return f"contract-review:{contract.id}:v{review_round}"

    async def _save_risks(self, contract_id: str, risks: list[RiskPayload]) -> None:
        """保存风险点（包含法律依据）"""
        for risk_data in risks:
            # 将法律依据合并到描述中
            description = risk_data.get("description", "")
            legal_basis = risk_data.get("legal_basis", "")
            if legal_basis:
                description = f"{description}\n\n【法律依据】{legal_basis}"

            risk = ContractRisk(
                contract_id=contract_id,
                risk_type=risk_data.get("type", "unknown"),
                risk_level=RiskLevel(risk_data.get("level", "medium").lower()),
                title=risk_data.get("title", "未知风险"),
                description=description,
                related_clause=risk_data.get("clause"),
                original_text=risk_data.get("original_text"),
                suggestion=risk_data.get("suggestion"),
                suggested_text=risk_data.get("suggested_text"),
            )
            self.db.add(risk)

        await self.db.flush()

    async def get_risks(self, contract_id: str, org_id: str | None = None) -> list[ContractRisk]:
        """获取合同风险点列表"""
        query = (
            select(ContractRisk)
            .join(Contract, Contract.id == ContractRisk.contract_id)
            .where(ContractRisk.contract_id == contract_id)
            .order_by(ContractRisk.risk_level.desc())
        )
        if org_id:
            query = query.where(Contract.org_id == org_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def resolve_risk(
        self,
        risk_id: str,
        resolution_note: str | None = None,
        contract_id: str | None = None,
        org_id: str | None = None,
    ) -> bool:
        """标记风险已解决"""
        query = (
            select(ContractRisk)
            .join(Contract, Contract.id == ContractRisk.contract_id)
            .where(ContractRisk.id == risk_id)
        )
        if contract_id:
            query = query.where(ContractRisk.contract_id == contract_id)
        if org_id:
            query = query.where(Contract.org_id == org_id)

        result = await self.db.execute(query)
        risk = result.scalar_one_or_none()

        if not risk:
            return False

        risk.is_resolved = True
        risk.resolution_note = resolution_note
        await self.db.flush()

        return True

    async def apply_suggestions(
        self,
        contract_id: str,
        accepted_risk_ids: list[str],
        org_id: str | None = None,
        actor_id: str | None = None,
    ) -> str:
        """应用用户接受的修改建议，返回修改后的文本"""
        contract = await self.get_contract(contract_id, org_id=org_id)
        if not contract or not contract.original_text:
            raise ValueError("合同不存在或未审查")

        await self._ensure_initial_version(
            contract,
            actor_id=actor_id,
            description="contract original text",
        )
        modified = contract.original_text

        # 获取接受的风险记录，按 original_text 在文本中出现的位置倒序排列（从后往前替换避免位移问题）
        accepted_risks = [
            r
            for r in contract.risks
            if r.id in accepted_risk_ids and r.original_text and r.suggested_text
        ]

        # 按原文在 modified 中的位置倒序排
        risk_positions: list[tuple[int, ContractRisk]] = []
        for risk in accepted_risks:
            original_text = risk.original_text
            if original_text is None:
                continue
            pos = modified.find(original_text)
            if pos >= 0:
                risk_positions.append((pos, risk))
        risk_positions.sort(key=lambda x: x[0], reverse=True)

        for pos, risk in risk_positions:
            original_text = risk.original_text
            suggested_text = risk.suggested_text
            if original_text is None or suggested_text is None:
                continue
            modified = modified[:pos] + suggested_text + modified[pos + len(original_text) :]
            risk.is_resolved = True
            risk.resolution_note = "用户已接受修改建议"

        contract.modified_text = modified
        await self._append_version(
            contract,
            text=modified,
            source="suggestion",
            actor_id=actor_id,
            description="accepted risk suggestions",
        )
        await self.db.flush()
        return modified

    async def get_contract_versions(
        self,
        contract_id: str,
        org_id: str | None = None,
    ) -> list[ContractVersion]:
        """Return contract version snapshots in descending version order."""
        contract = await self.get_contract(contract_id, org_id=org_id)
        if not contract:
            raise ValueError("合同不存在")

        await self._ensure_initial_version(contract, description="contract baseline")
        result = await self.db.execute(
            select(ContractVersion)
            .where(ContractVersion.contract_id == contract_id)
            .order_by(ContractVersion.version.desc())
        )
        return list(result.scalars().all())

    async def get_version_diff(
        self,
        contract_id: str,
        from_version: int,
        to_version: int,
        org_id: str | None = None,
    ) -> JSONDict:
        """Return a structured paragraph diff between two contract versions."""
        contract = await self.get_contract(contract_id, org_id=org_id)
        if not contract:
            raise ValueError("合同不存在")
        await self._ensure_initial_version(contract, description="contract baseline")

        old_version = await self._get_version(contract_id, from_version)
        new_version = await self._get_version(contract_id, to_version)
        old_parts = self._split_paragraphs(old_version.text)
        new_parts = self._split_paragraphs(new_version.text)

        changes: list[JSONDict] = []
        matcher = difflib.SequenceMatcher(a=old_parts, b=new_parts)
        for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
            if tag == "equal":
                continue
            changes.append(
                {
                    "type": tag,
                    "old_start": old_start + 1,
                    "old_end": old_end,
                    "new_start": new_start + 1,
                    "new_end": new_end,
                    "old_text": "\n\n".join(old_parts[old_start:old_end]),
                    "new_text": "\n\n".join(new_parts[new_start:new_end]),
                }
            )

        return {
            "contract_id": contract.id,
            "from_version": from_version,
            "to_version": to_version,
            "summary": {
                "changes": len(changes),
                "insertions": sum(1 for item in changes if item["type"] == "insert"),
                "deletions": sum(1 for item in changes if item["type"] == "delete"),
                "replacements": sum(1 for item in changes if item["type"] == "replace"),
            },
            "changes": changes,
        }

    async def rollback_to_version(
        self,
        contract_id: str,
        target_version: int,
        *,
        actor_id: str | None = None,
        reason: str | None = None,
        org_id: str | None = None,
    ) -> Contract:
        """Rollback editable contract text to a prior version via lifecycle rules."""
        contract = await self.get_contract(contract_id, org_id=org_id)
        if not contract:
            raise ValueError("合同不存在")
        await self._ensure_initial_version(contract, description="contract baseline")
        target = await self._get_version(contract_id, target_version)

        ContractLifecycleStateMachine.transition(
            contract,
            ContractStatus.DRAFT,
            actor_id=actor_id,
            reason=reason or f"rollback_to_v{target_version}",
        )
        contract.modified_text = target.text
        await self._append_version(
            contract,
            text=target.text,
            source="rollback",
            actor_id=actor_id,
            description=f"rollback to version {target_version}",
        )
        await self.db.flush()
        return contract

    async def _ensure_initial_version(
        self,
        contract: Contract,
        *,
        actor_id: str | None = None,
        description: str | None = None,
    ) -> None:
        existing = await self.db.scalar(
            select(func.count(ContractVersion.id)).where(ContractVersion.contract_id == contract.id)
        )
        if existing:
            return

        text = contract.original_text or contract.modified_text or ""
        self.db.add(
            ContractVersion(
                contract_id=contract.id,
                version=1,
                text=text,
                source="baseline",
                description=description,
                created_by=actor_id,
            )
        )
        contract.version = max(contract.version or 1, 1)
        await self.db.flush()

    async def _append_version(
        self,
        contract: Contract,
        *,
        text: str,
        source: str,
        actor_id: str | None = None,
        description: str | None = None,
    ) -> ContractVersion:
        max_version = await self.db.scalar(
            select(func.max(ContractVersion.version)).where(
                ContractVersion.contract_id == contract.id
            )
        )
        next_version = (max_version or 0) + 1
        version = ContractVersion(
            contract_id=contract.id,
            version=next_version,
            text=text,
            source=source,
            description=description,
            created_by=actor_id,
        )
        contract.version = next_version
        self.db.add(version)
        await self.db.flush()
        return version

    async def _get_version(self, contract_id: str, version: int) -> ContractVersion:
        result = await self.db.execute(
            select(ContractVersion).where(
                ContractVersion.contract_id == contract_id,
                ContractVersion.version == version,
            )
        )
        snapshot = result.scalar_one_or_none()
        if not snapshot:
            raise ValueError("合同版本不存在")
        return snapshot

    @staticmethod
    def _split_paragraphs(text: str) -> list[str]:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        if paragraphs:
            return paragraphs
        return [line.strip() for line in text.splitlines() if line.strip()] or [text]

    async def transition_status(
        self,
        contract_id: str,
        target_status: ContractStatus | str,
        *,
        actor_id: str | None = None,
        reason: str | None = None,
        org_id: str | None = None,
    ) -> Contract:
        """Transition a contract through the lifecycle state machine."""
        contract = await self.get_contract(contract_id, org_id=org_id)
        if not contract:
            raise ValueError("合同不存在")

        ContractLifecycleStateMachine.transition(
            contract,
            target_status,
            actor_id=actor_id,
            reason=reason,
        )
        await self.db.flush()
        return contract

    async def save_contract_file(
        self, contract_id: str, user_id: str | None = None, org_id: str | None = None
    ) -> str:
        """保存合同文件到对象存储，返回对象 key"""
        contract = await self.get_contract(contract_id, org_id=org_id)
        if not contract:
            raise ValueError("合同不存在")

        text = contract.modified_text or contract.original_text
        if not text:
            raise ValueError("没有可保存的合同内容")

        object_key = (
            f"contracts/{org_id or user_id or 'default'}/"
            f"{contract.contract_number}/{contract.id}.txt"
        )
        stored = await self.object_storage.put(
            object_key=object_key,
            content=text.encode("utf-8"),
            content_type="text/plain; charset=utf-8",
        )

        return stored.object_key

    async def upload_attachment(
        self,
        contract_id: str,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        org_id: str | None = None,
        actor_id: str | None = None,
    ) -> ContractAttachment:
        """上传合同附件到对象存储并创建附件记录。"""
        contract = await self.get_contract(contract_id, org_id=org_id)
        if not contract:
            raise ValueError("合同不存在")
        if not contract.org_id:
            raise ValueError("合同未绑定组织，无法保存附件")

        attachment_id = str(uuid4())
        safe_filename = filename.replace("\\", "/").rsplit("/", 1)[-1] or "attachment"
        file_hash = hashlib.sha256(content).hexdigest()
        file_ext = Path(safe_filename).suffix.lower() or ".bin"
        object_key = (
            f"contracts/{contract.org_id}/{contract.id}/attachments/"
            f"{attachment_id}_{file_hash[:8]}{file_ext}"
        )
        stored = await self.object_storage.put(
            object_key=object_key,
            content=content,
            content_type=content_type,
        )

        attachment = ContractAttachment(
            id=attachment_id,
            contract_id=contract.id,
            org_id=contract.org_id,
            original_filename=safe_filename,
            content_type=content_type,
            storage_backend=stored.backend,
            object_key=stored.object_key,
            file_size=stored.size,
            file_hash=file_hash,
            uploaded_by=actor_id,
        )
        self.db.add(attachment)
        await self.db.flush()
        return attachment

    async def list_attachments(
        self,
        contract_id: str,
        *,
        org_id: str | None = None,
    ) -> list[ContractAttachment]:
        """列出当前组织可访问的合同附件。"""
        contract = await self.get_contract(contract_id, org_id=org_id)
        if not contract:
            raise ValueError("合同不存在")

        result = await self.db.execute(
            select(ContractAttachment)
            .where(ContractAttachment.contract_id == contract.id)
            .order_by(ContractAttachment.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_attachment(
        self,
        contract_id: str,
        attachment_id: str,
        *,
        org_id: str | None = None,
    ) -> ContractAttachment | None:
        """获取附件记录，并约束合同所属组织。"""
        query = (
            select(ContractAttachment)
            .join(Contract, Contract.id == ContractAttachment.contract_id)
            .where(
                ContractAttachment.id == attachment_id,
                ContractAttachment.contract_id == contract_id,
            )
        )
        if org_id:
            query = query.where(Contract.org_id == org_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_attachment_content(
        self,
        contract_id: str,
        attachment_id: str,
        *,
        org_id: str | None = None,
    ) -> tuple[ContractAttachment, bytes]:
        """读取合同附件内容。"""
        attachment = await self.get_attachment(
            contract_id,
            attachment_id,
            org_id=org_id,
        )
        if not attachment:
            raise ValueError("附件不存在")

        content = await self.object_storage.get(attachment.object_key)
        return attachment, content

    async def get_attachment_download_url(
        self,
        contract_id: str,
        attachment_id: str,
        *,
        org_id: str | None = None,
        expires_seconds: int = 3600,
    ) -> tuple[ContractAttachment, str]:
        """Create an object-storage download URL for a contract attachment."""
        attachment = await self.get_attachment(
            contract_id,
            attachment_id,
            org_id=org_id,
        )
        if not attachment:
            raise ValueError("附件不存在")

        url = await self.object_storage.presigned_get_url(
            attachment.object_key,
            expires_seconds=expires_seconds,
        )
        return attachment, url

    async def delete_attachment(
        self,
        contract_id: str,
        attachment_id: str,
        *,
        org_id: str | None = None,
    ) -> ContractAttachment:
        """删除合同附件对象与数据库记录。"""
        attachment = await self.get_attachment(
            contract_id,
            attachment_id,
            org_id=org_id,
        )
        if not attachment:
            raise ValueError("附件不存在")

        await self.object_storage.delete(attachment.object_key)
        await self.db.delete(attachment)
        await self.db.flush()
        return attachment
