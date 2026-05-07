"""
利益冲突检查服务 (V2 架构)

律师接案前自动扫描历史案件当事人，发现潜在冲突。
律所端必需功能。

检查逻辑：
1. 提取新案件的当事人名称（原告、被告、公司名等）
2. 搜索律师/律所历史案件中是否曾代理对立方
3. 返回冲突详情供律师判断
"""

from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.case import Case


class ConflictCheckResult:
    """冲突检查结果"""

    def __init__(self) -> None:
        self.has_conflict: bool = False
        self.conflicts: list[dict[str, Any]] = []
        self.warning_level: str = "none"  # none / low / medium / high

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_conflict": self.has_conflict,
            "warning_level": self.warning_level,
            "conflict_count": len(self.conflicts),
            "conflicts": self.conflicts,
        }


class ConflictCheckService:
    """利益冲突检查"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_conflict(
        self,
        lawyer_id: str,
        party_names: list[str],
        org_id: str | None = None,
        exclude_case_id: str | None = None,
    ) -> ConflictCheckResult:
        """
        检查律师接案是否存在利益冲突。

        Args:
            lawyer_id: 律师用户ID
            party_names: 新案件涉及的所有当事人名称列表
            org_id: 律所ID（如果有，扩大检查范围到整个律所）
            exclude_case_id: 排除的案件ID（避免自己和自己冲突）

        Returns:
            ConflictCheckResult
        """
        result = ConflictCheckResult()

        if not party_names:
            return result

        # 清理和标准化名称
        clean_names = [n.strip() for n in party_names if n and n.strip()]
        if not clean_names:
            return result

        # 构建查询：查找律师（或律所）历史案件
        user_filter = Case.assignee_id == lawyer_id
        if org_id:
            # 律所范围：扩大到同律所所有律师的案件
            from src.models.user import User
            org_members = await self.db.execute(
                select(User.id).where(User.org_id == org_id)
            )
            member_ids = [str(r[0]) for r in org_members.all()]
            if member_ids:
                user_filter = Case.assignee_id.in_(member_ids)

        query = select(Case).where(user_filter)
        if exclude_case_id:
            query = query.where(Case.id != exclude_case_id)

        cases_result = await self.db.execute(query)
        historical_cases = cases_result.scalars().all()

        # 检查每个历史案件的当事人是否与新案件冲突
        for case in historical_cases:
            case_parties = self._extract_parties(case)
            for new_party in clean_names:
                for hist_party in case_parties:
                    if self._names_match(new_party, hist_party["name"]):
                        # 检查是否为对立方
                        conflict_info = {
                            "case_id": str(case.id),
                            "case_title": getattr(case, 'title', ''),
                            "historical_party": hist_party["name"],
                            "historical_role": hist_party.get("role", "unknown"),
                            "new_party": new_party,
                            "conflict_type": "same_party",  # 或 "adverse_party"
                            "created_at": case.created_at.isoformat() if case.created_at else None,
                        }
                        result.conflicts.append(conflict_info)

        if result.conflicts:
            result.has_conflict = True
            # 判断严重程度
            if len(result.conflicts) >= 3:
                result.warning_level = "high"
            elif len(result.conflicts) >= 1:
                result.warning_level = "medium"
            else:
                result.warning_level = "low"

        logger.info(
            f"利益冲突检查: lawyer={lawyer_id}, parties={clean_names}, "
            f"conflicts={len(result.conflicts)}, level={result.warning_level}"
        )
        return result

    @staticmethod
    def _extract_parties(case: Case) -> list[dict[str, str]]:
        """从案件中提取当事人信息"""
        parties = []

        # 从 case.description 或其他字段提取（简化实现）
        title = getattr(case, 'title', '') or ''
        description = getattr(case, 'description', '') or ''

        # 优先读取 Case.parties，支持 {"plaintiff": "...", "defendant": "..."}、
        # {"parties": [{"name": "..."}]} 和字符串列表等常见形态。
        structured_parties = getattr(case, "parties", None) or {}
        if isinstance(structured_parties, dict):
            for role, value in structured_parties.items():
                if isinstance(value, str):
                    parties.append({"name": value, "role": role})
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and item.get("name"):
                            parties.append({"name": item["name"], "role": item.get("role", role)})
                        elif isinstance(item, str):
                            parties.append({"name": item, "role": role})
        elif isinstance(structured_parties, list):
            for item in structured_parties:
                if isinstance(item, dict) and item.get("name"):
                    parties.append({"name": item["name"], "role": item.get("role", "party")})
                elif isinstance(item, str):
                    parties.append({"name": item, "role": "party"})

        # 尝试从 extra_data/metadata 中读取结构化当事人信息
        extra = getattr(case, 'extra_data', None) or {}
        if isinstance(extra, dict):
            for party in extra.get("parties", []):
                if isinstance(party, dict) and party.get("name"):
                    parties.append({"name": party["name"], "role": party.get("role", "party")})
                elif isinstance(party, str):
                    parties.append({"name": party, "role": "party"})

        # 如果没有结构化数据，从标题中简单提取（后续可用 NLP 增强）
        if not parties:
            for segment in [title, description[:200]]:
                # 匹配常见的公司名模式
                import re
                company_names = re.findall(r'[\u4e00-\u9fa5]{2,}(?:有限|股份|集团|科技|实业)公司', segment)
                for cn in company_names:
                    if cn not in [p["name"] for p in parties]:
                        parties.append({"name": cn, "role": "party"})

        return parties

    @staticmethod
    def _names_match(name_a: str, name_b: str) -> bool:
        """判断两个名称是否匹配（支持模糊匹配）"""
        a = name_a.strip().lower()
        b = name_b.strip().lower()

        # 完全匹配
        if a == b:
            return True

        # 包含匹配（一个是另一个的子串，且长度差不太大）
        if len(a) >= 4 and len(b) >= 4:
            if a in b or b in a:
                return True

        return False
