"""
合同审查服务
"""

from datetime import datetime, date
from typing import Optional, List
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from loguru import logger

from src.models.contract import Contract, ContractClause, ContractRisk, ContractStatus, RiskLevel


class ContractService:
    """合同审查服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._workforce = None
    
    @property
    def workforce(self):
        """延迟导入 workforce，避免循环依赖"""
        if self._workforce is None:
            from src.agents.workforce import get_workforce
            self._workforce = get_workforce()
        return self._workforce
    
    async def create_contract(
        self,
        title: str,
        contract_type: str,
        document_id: Optional[str] = None,
        org_id: Optional[str] = None,
        party_a: Optional[dict] = None,
        party_b: Optional[dict] = None,
        amount: Optional[float] = None,
        effective_date: Optional[date] = None,
        expiry_date: Optional[date] = None,
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
    
    async def get_contract(self, contract_id: str) -> Optional[Contract]:
        """获取合同详情"""
        result = await self.db.execute(
            select(Contract)
            .options(selectinload(Contract.clauses))
            .options(selectinload(Contract.risks))
            .where(Contract.id == contract_id)
        )
        return result.scalar_one_or_none()
    
    async def list_contracts(
        self,
        org_id: Optional[str] = None,
        status: Optional[str] = None,
        contract_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Contract], int]:
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
        reviewed_by: Optional[str] = None,
    ) -> dict:
        """
        AI审查合同
        
        Args:
            contract_id: 合同ID
            contract_text: 合同文本内容
            reviewed_by: 审核人ID
            
        Returns:
            审查结果
        """
        contract = await self.get_contract(contract_id)
        if not contract:
            raise ValueError("合同不存在")
        
        # 保存原始合同文本
        contract.original_text = contract_text

        # 更新状态为审核中
        contract.status = ContractStatus.UNDER_REVIEW
        await self.db.flush()
        
        # 调用合同审查智能体
        task_description = f"""
请审查以下合同文本，识别风险点并提供修改建议：

合同名称：{contract.title}
合同类型：{contract.contract_type}

合同内容：
{contract_text[:10000]}  # 限制长度
"""
        
        result = await self.workforce.process_task(
            task_description=task_description,
            task_type="contract_review",
            context={
                "contract_id": contract_id,
                "contract_type": contract.contract_type,
            }
        )
        
        # 解析审查结果
        review_result = result.get("final_result", {})
        
        # 计算风险评分
        risk_score = self._calculate_risk_score(review_result)
        risk_level = self._get_risk_level(risk_score)
        
        # 更新合同信息
        contract.review_result = review_result
        contract.risk_score = risk_score
        contract.risk_level = risk_level
        contract.review_summary = review_result.get("summary", "")
        contract.status = ContractStatus.PENDING_REVIEW
        contract.reviewed_by = reviewed_by
        
        await self.db.flush()
        
        # 保存风险点
        await self._save_risks(contract_id, review_result.get("risks", []))
        
        logger.info(f"合同审查完成: {contract.contract_number}, 风险等级: {risk_level}")
        
        return {
            "contract_id": contract_id,
            "risk_score": risk_score,
            "risk_level": risk_level.value if risk_level else None,
            "summary": review_result.get("summary", ""),
            "risks": review_result.get("risks", []),
            "suggestions": review_result.get("suggestions", []),
            "key_terms": review_result.get("key_terms", {}),
        }
    
    def _calculate_risk_score(self, review_result: dict) -> float:
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
    
    async def _save_risks(self, contract_id: str, risks: list) -> None:
        """保存风险点"""
        for risk_data in risks:
            risk = ContractRisk(
                contract_id=contract_id,
                risk_type=risk_data.get("type", "unknown"),
                risk_level=RiskLevel(risk_data.get("level", "medium").lower()),
                title=risk_data.get("title", "未知风险"),
                description=risk_data.get("description", ""),
                related_clause=risk_data.get("clause"),
                original_text=risk_data.get("original_text"),
                suggestion=risk_data.get("suggestion"),
                suggested_text=risk_data.get("suggested_text"),
            )
            self.db.add(risk)
        
        await self.db.flush()
    
    async def get_risks(self, contract_id: str) -> List[ContractRisk]:
        """获取合同风险点列表"""
        result = await self.db.execute(
            select(ContractRisk)
            .where(ContractRisk.contract_id == contract_id)
            .order_by(ContractRisk.risk_level.desc())
        )
        return list(result.scalars().all())
    
    async def resolve_risk(
        self,
        risk_id: str,
        resolution_note: Optional[str] = None,
    ) -> bool:
        """标记风险已解决"""
        result = await self.db.execute(
            select(ContractRisk).where(ContractRisk.id == risk_id)
        )
        risk = result.scalar_one_or_none()

        if not risk:
            return False

        risk.is_resolved = True
        risk.resolution_note = resolution_note
        await self.db.flush()

        return True

    async def apply_suggestions(self, contract_id: str, accepted_risk_ids: list[str]) -> str:
        """应用用户接受的修改建议，返回修改后的文本"""
        contract = await self.get_contract(contract_id)
        if not contract or not contract.original_text:
            raise ValueError("合同不存在或未审查")

        modified = contract.original_text

        # 获取接受的风险记录，按 original_text 在文本中出现的位置倒序排列（从后往前替换避免位移问题）
        accepted_risks = [
            r for r in contract.risks
            if r.id in accepted_risk_ids and r.original_text and r.suggested_text
        ]

        # 按原文在 modified 中的位置倒序排
        risk_positions = []
        for risk in accepted_risks:
            pos = modified.find(risk.original_text)
            if pos >= 0:
                risk_positions.append((pos, risk))
        risk_positions.sort(key=lambda x: x[0], reverse=True)

        for pos, risk in risk_positions:
            modified = modified[:pos] + risk.suggested_text + modified[pos + len(risk.original_text):]
            risk.is_resolved = True
            risk.resolution_note = "用户已接受修改建议"

        contract.modified_text = modified
        await self.db.flush()
        return modified

    async def save_contract_file(self, contract_id: str, user_id: Optional[str] = None) -> str:
        """保存合同文件到服务器，返回文件路径"""
        contract = await self.get_contract(contract_id)
        if not contract:
            raise ValueError("合同不存在")

        text = contract.modified_text or contract.original_text
        if not text:
            raise ValueError("没有可保存的合同内容")

        import os

        # 保存到 data/contracts/{user_id or 'default'}/{contract_number}/
        base_dir = os.path.join("data", "contracts", user_id or "default", contract.contract_number)
        os.makedirs(base_dir, exist_ok=True)

        file_path = os.path.join(base_dir, f"{contract.title}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        return file_path
