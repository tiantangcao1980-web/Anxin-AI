"""
律所知识管理平台

功能：
1. 案例经验库 — 按领域/类型/结果分类的实务经验
2. 文档模板管理 — 律所自定义模板（继承 template_engine 能力）
3. 智能推荐 — 根据当前任务推荐相关经验和模板
4. 知识沉淀 — 从日常工作中自动提取可复用知识
"""

from dataclasses import asdict
from datetime import datetime
from typing import Any, cast
from uuid import uuid4

from src.services.pii_service import pii_service

# ===== 案例经验分类 =====

EXPERIENCE_CATEGORIES = {
    "contract_dispute": "合同纠纷",
    "labor_dispute": "劳动争议",
    "ip_infringement": "知识产权侵权",
    "corporate_governance": "公司治理",
    "real_estate": "房产纠纷",
    "debt_collection": "债务催收",
    "criminal_defense": "刑事辩护",
    "administrative": "行政诉讼",
    "compliance": "合规咨询",
    "m_and_a": "并购重组",
}

OUTCOME_TYPES = {
    "win": "胜诉",
    "partial_win": "部分胜诉",
    "loss": "败诉",
    "settlement": "调解",
    "mediation": "和解",
    "withdrawn": "撤诉",
}

KnowledgeDict = dict[str, Any]


class CaseExperience:
    """单条案例经验"""

    def __init__(
        self,
        title: str,
        category: str,
        summary: str,
        key_points: list[str],
        outcome: str = "",
        applicable_laws: list[str] | None = None,
        lessons_learned: str = "",
        org_id: str | None = None,
        author_id: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        self.id = f"exp_{uuid4().hex}"
        self.title = title
        self.category = category
        self.summary = summary
        self.key_points = key_points
        self.outcome = outcome
        self.applicable_laws = applicable_laws or []
        self.lessons_learned = lessons_learned
        self.org_id = org_id
        self.author_id = author_id
        self.tags = tags or []
        self.created_at = datetime.now()
        self.view_count = 0
        self.useful_count = 0

    def to_dict(self) -> KnowledgeDict:
        return cast(
            KnowledgeDict,
            pii_service.scrub_for_output(
                {
                    "id": self.id,
                    "title": self.title,
                    "category": self.category,
                    "category_label": EXPERIENCE_CATEGORIES.get(self.category, self.category),
                    "summary": self.summary,
                    "key_points": self.key_points,
                    "outcome": self.outcome,
                    "outcome_label": OUTCOME_TYPES.get(self.outcome, self.outcome),
                    "applicable_laws": self.applicable_laws,
                    "lessons_learned": self.lessons_learned,
                    "tags": self.tags,
                    "created_at": self.created_at.isoformat(),
                    "view_count": self.view_count,
                    "useful_count": self.useful_count,
                }
            ),
        )


class KnowledgeManagementService:
    """律所知识管理服务"""

    def __init__(self) -> None:
        self._experiences: dict[str, list[CaseExperience]] = {}  # org_id -> experiences
        self._custom_templates: dict[str, list[KnowledgeDict]] = {}  # org_id -> templates

    # ===== 案例经验库 =====

    async def add_experience(
        self,
        org_id: str,
        title: str,
        category: str,
        summary: str,
        key_points: list[str],
        outcome: str = "",
        applicable_laws: list[str] | None = None,
        lessons_learned: str = "",
        author_id: str | None = None,
        tags: list[str] | None = None,
    ) -> CaseExperience:
        """添加案例经验"""
        exp = CaseExperience(
            title=title,
            category=category,
            summary=summary,
            key_points=key_points,
            outcome=outcome,
            applicable_laws=applicable_laws,
            lessons_learned=lessons_learned,
            org_id=org_id,
            author_id=author_id,
            tags=tags,
        )
        if org_id not in self._experiences:
            self._experiences[org_id] = []
        self._experiences[org_id].append(exp)
        return exp

    async def search_experiences(
        self,
        org_id: str,
        query: str = "",
        category: str | None = None,
        outcome: str | None = None,
        top_k: int = 10,
    ) -> list[KnowledgeDict]:
        """搜索案例经验"""
        bounded_top_k = max(1, min(top_k, 50))
        experiences = self._experiences.get(org_id, [])

        if category:
            experiences = [e for e in experiences if e.category == category]
        if outcome:
            experiences = [e for e in experiences if e.outcome == outcome]

        if query:
            scored: list[tuple[CaseExperience, int]] = []
            query_lower = query.lower()
            for exp in experiences:
                score = 0
                if query_lower in exp.title.lower():
                    score += 5
                if query_lower in exp.summary.lower():
                    score += 3
                for kp in exp.key_points:
                    if query_lower in kp.lower():
                        score += 2
                for tag in exp.tags:
                    if query_lower in tag.lower():
                        score += 1
                if score > 0:
                    scored.append((exp, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            experiences = [e for e, _ in scored]

        results: list[KnowledgeDict] = []
        for exp in experiences[:bounded_top_k]:
            exp.view_count += 1
            results.append(exp.to_dict())
        return results

    async def get_experience(self, org_id: str, experience_id: str) -> KnowledgeDict | None:
        """获取单条经验详情"""
        for exp in self._experiences.get(org_id, []):
            if exp.id == experience_id:
                exp.view_count += 1
                return exp.to_dict()
        return None

    async def mark_useful(self, org_id: str, experience_id: str) -> bool:
        """标记经验有用"""
        for exp in self._experiences.get(org_id, []):
            if exp.id == experience_id:
                exp.useful_count += 1
                return True
        return False

    # ===== 智能推荐 =====

    async def recommend_for_task(
        self,
        org_id: str,
        task_description: str,
        task_type: str = "general",
        top_k: int = 5,
    ) -> dict[str, Any]:
        """根据当前任务智能推荐相关经验和模板"""
        recommendations: KnowledgeDict = {
            "experiences": [],
            "templates": [],
            "related_laws": [],
        }

        # 1. 推荐相关经验
        experiences = await self.search_experiences(org_id, query=task_description, top_k=top_k)
        recommendations["experiences"] = experiences

        # 2. 推荐相关模板
        try:
            from src.services.template_engine import get_template_library

            templates = [asdict(template) for template in get_template_library()]
            # 简单关键词匹配
            for tmpl in templates:
                name = tmpl.get("name", "")
                if any(kw in task_description for kw in name):
                    recommendations["templates"].append(tmpl)
        except Exception:
            pass

        # 3. 推荐相关法条
        try:
            from src.services.legal_rag import legal_rag_service

            ctx = await legal_rag_service.retrieve(task_description, max_results=3)
            recommendations["related_laws"] = ctx.sources
        except Exception:
            pass

        return cast(KnowledgeDict, pii_service.scrub_for_output(recommendations))

    # ===== 自定义模板 =====

    async def add_custom_template(
        self,
        org_id: str,
        name: str,
        content: str,
        template_type: str = "contract",
        author_id: str | None = None,
        tags: list[str] | None = None,
    ) -> KnowledgeDict:
        """添加律所自定义模板"""
        template = {
            "id": f"tmpl_{uuid4().hex}",
            "name": name,
            "content": content,
            "template_type": template_type,
            "author_id": author_id,
            "tags": tags or [],
            "org_id": org_id,
            "created_at": datetime.now().isoformat(),
            "use_count": 0,
        }
        if org_id not in self._custom_templates:
            self._custom_templates[org_id] = []
        self._custom_templates[org_id].append(template)
        return cast(KnowledgeDict, pii_service.scrub_for_output(template))

    async def list_custom_templates(
        self,
        org_id: str,
        template_type: str | None = None,
    ) -> list[KnowledgeDict]:
        """列出律所自定义模板"""
        templates = self._custom_templates.get(org_id, [])
        if template_type:
            templates = [t for t in templates if t.get("template_type") == template_type]
        return cast(list[KnowledgeDict], pii_service.scrub_for_output(templates))

    # ===== 知识沉淀（从审查/咨询中自动提取） =====

    async def extract_from_review(
        self,
        org_id: str,
        review_result: dict[str, Any],
        author_id: str | None = None,
    ) -> CaseExperience | None:
        """从合同审查结果中自动提取可复用经验"""
        risk_points = review_result.get("risk_points", [])
        suggestions = review_result.get("suggestions", [])
        contract_type = review_result.get("contract_type", "")

        if not risk_points and not suggestions:
            return None

        # 自动分类
        category = "contract_dispute"
        if "劳动" in contract_type:
            category = "labor_dispute"
        elif "知识产权" in contract_type or "专利" in contract_type:
            category = "ip_infringement"
        elif "股权" in contract_type or "并购" in contract_type:
            category = "m_and_a"

        exp = await self.add_experience(
            org_id=org_id,
            title=f"{contract_type}审查经验",
            category=category,
            summary=f"从{contract_type}审查中提取的{len(risk_points)}个风险点和{len(suggestions)}条建议",
            key_points=risk_points[:5],
            lessons_learned="; ".join(suggestions[:3]) if suggestions else "",
            author_id=author_id,
            tags=[contract_type, "自动提取"],
        )
        return exp

    # ===== 统计 =====

    def get_stats(self, org_id: str) -> dict[str, Any]:
        """获取知识库统计"""
        experiences = self._experiences.get(org_id, [])
        templates = self._custom_templates.get(org_id, [])
        return {
            "total_experiences": len(experiences),
            "total_templates": len(templates),
            "by_category": {
                cat: sum(1 for e in experiences if e.category == cat)
                for cat in EXPERIENCE_CATEGORIES
                if any(e.category == cat for e in experiences)
            },
            "by_outcome": {
                out: sum(1 for e in experiences if e.outcome == out)
                for out in OUTCOME_TYPES
                if any(e.outcome == out for e in experiences)
            },
            "most_viewed": sorted(
                [e.to_dict() for e in experiences],
                key=lambda x: x["view_count"],
                reverse=True,
            )[:5],
        }


# 全局实例
knowledge_management_service = KnowledgeManagementService()
