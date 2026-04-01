# -*- coding: utf-8 -*-
"""
Report Engine v2 — 调查报告生成引擎（增强版）

灵感来源：BettaFish ReportEngine 的 6 阶段管线
流程：模板选择 → 模板切片 → 文档布局 → 字数预算 → 章节逐一生成 → 组装渲染

报告模板：
1. comprehensive — 综合尽职调查报告（完整版）
2. risk_focus — 风险评估专项报告
3. litigation — 诉讼风险专项报告
4. credit — 信用合规专项报告
5. executive — 管理层简报（精简版）
6. compliance — 合规审计报告

章节生成支持 LLM 增强（可选）和流式进度回调。
"""

import asyncio
import json
import re
from typing import Dict, Any, Optional, List, AsyncGenerator, Callable
from datetime import datetime
from dataclasses import dataclass, field
from loguru import logger


# ===== 报告模板定义 =====

@dataclass
class ChapterTemplate:
    """章节模板"""
    id: str
    title: str
    description: str
    word_budget: int  # 目标字数
    required: bool = True
    data_keys: List[str] = field(default_factory=list)  # 所需数据字段


@dataclass
class ReportTemplate:
    """报告模板"""
    id: str
    name: str
    description: str
    chapters: List[ChapterTemplate] = field(default_factory=list)
    total_word_budget: int = 3000


# 预定义报告模板
REPORT_TEMPLATES: Dict[str, ReportTemplate] = {
    "comprehensive": ReportTemplate(
        id="comprehensive",
        name="综合尽职调查报告",
        description="全面深入的企业尽职调查报告，涵盖所有维度",
        total_word_budget=5000,
        chapters=[
            ChapterTemplate("executive_summary", "执行摘要", "概述调查结论和核心发现", 500, data_keys=["risk", "consensus"]),
            ChapterTemplate("company_profile", "企业概况", "企业基本信息与经营状态", 600, data_keys=["basic_info"]),
            ChapterTemplate("risk_assessment", "风险评估", "五维度风险评分与分析", 800, data_keys=["risk"]),
            ChapterTemplate("litigation_analysis", "诉讼分析", "涉诉记录与司法风险", 700, data_keys=["litigation"]),
            ChapterTemplate("credit_compliance", "信用合规", "信用评级与合规审查", 600, data_keys=["credit"]),
            ChapterTemplate("relationship_analysis", "关联关系", "股权穿透与关联网络", 500, data_keys=["basic_info", "risk"]),
            ChapterTemplate("forum_debate", "多专家论证", "多专家分析过程与辩论记录", 600, required=False, data_keys=["forum", "conflicts"]),
            ChapterTemplate("deep_research", "深度研究发现", "迭代式研究的关键发现", 400, required=False, data_keys=["research"]),
            ChapterTemplate("recommendations", "结论与建议", "综合结论和行动建议", 500, data_keys=["risk", "consensus"]),
        ],
    ),
    "risk_focus": ReportTemplate(
        id="risk_focus",
        name="风险评估专项报告",
        description="聚焦风险评估的专项报告",
        total_word_budget=3000,
        chapters=[
            ChapterTemplate("executive_summary", "执行摘要", "风险概述", 400, data_keys=["risk"]),
            ChapterTemplate("risk_assessment", "风险评估详情", "详细的五维度风险分析", 1000, data_keys=["risk"]),
            ChapterTemplate("litigation_analysis", "诉讼风险", "涉诉记录分析", 600, data_keys=["litigation"]),
            ChapterTemplate("risk_trends", "风险趋势", "风险演变趋势预测", 500, data_keys=["risk"]),
            ChapterTemplate("recommendations", "风险应对建议", "风险缓释策略", 500, data_keys=["risk", "consensus"]),
        ],
    ),
    "executive": ReportTemplate(
        id="executive",
        name="管理层简报",
        description="面向管理层的精简尽调报告",
        total_word_budget=1500,
        chapters=[
            ChapterTemplate("executive_summary", "调查结论", "核心结论与建议", 500, data_keys=["risk", "consensus"]),
            ChapterTemplate("key_findings", "关键发现", "重点风险项", 500, data_keys=["risk", "litigation"]),
            ChapterTemplate("action_items", "行动建议", "立即需要采取的措施", 500, data_keys=["risk", "consensus"]),
        ],
    ),
    "litigation": ReportTemplate(
        id="litigation",
        name="诉讼风险专项报告",
        description="聚焦诉讼和司法风险",
        total_word_budget=3000,
        chapters=[
            ChapterTemplate("summary", "概述", "诉讼风险概况", 400, data_keys=["litigation"]),
            ChapterTemplate("case_analysis", "案件分析", "主要案件详细分析", 1000, data_keys=["litigation"]),
            ChapterTemplate("execution_risk", "执行风险", "被执行与失信记录", 600, data_keys=["litigation"]),
            ChapterTemplate("litigation_trends", "诉讼趋势", "涉诉趋势与预测", 500, data_keys=["litigation"]),
            ChapterTemplate("recommendations", "应对建议", "诉讼风险应对策略", 500, data_keys=["risk"]),
        ],
    ),
    "credit": ReportTemplate(
        id="credit",
        name="信用合规专项报告",
        description="聚焦信用评级与合规",
        total_word_budget=2500,
        chapters=[
            ChapterTemplate("summary", "概述", "信用合规概况", 400, data_keys=["credit"]),
            ChapterTemplate("credit_rating", "信用评级", "信用评级分析", 600, data_keys=["credit"]),
            ChapterTemplate("compliance_check", "合规审查", "行政处罚与违规记录", 800, data_keys=["credit"]),
            ChapterTemplate("recommendations", "合规建议", "合规改善建议", 500, data_keys=["risk"]),
        ],
    ),
    "compliance": ReportTemplate(
        id="compliance",
        name="合规审计报告",
        description="合规性审计报告",
        total_word_budget=3000,
        chapters=[
            ChapterTemplate("summary", "审计概述", "合规审计范围和结论", 400, data_keys=["credit"]),
            ChapterTemplate("regulatory_check", "监管合规", "监管要求符合性审查", 700, data_keys=["credit"]),
            ChapterTemplate("penalty_records", "处罚记录", "行政处罚详情", 600, data_keys=["credit"]),
            ChapterTemplate("compliance_gaps", "合规缺口", "发现的合规问题", 700, data_keys=["credit", "risk"]),
            ChapterTemplate("improvement_plan", "整改建议", "合规改善计划", 600, data_keys=["risk"]),
        ],
    ),
}


class ReportSection:
    """报告章节"""

    def __init__(
        self,
        id: str,
        title: str,
        content: str,
        status: str = "normal",
        word_count: int = 0,
    ):
        self.id = id
        self.title = title
        self.content = content
        self.status = status  # normal, pass, warning, fail
        self.word_count = word_count or len(content)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "status": self.status,
            "word_count": self.word_count,
        }


class ReportEngine:
    """调查报告生成引擎 v2"""

    def __init__(self):
        self._llm_agent = None

    @property
    def llm_agent(self):
        if self._llm_agent is None:
            try:
                from src.agents.workforce import get_workforce
                wf = get_workforce()
                self._llm_agent = (
                    wf.agents.get("due_diligence")
                    or wf.agents.get("legal_advisor")
                    or (list(wf.agents.values())[0] if wf.agents else None)
                )
            except Exception:
                pass
        return self._llm_agent

    # ========== 模板管理 ==========

    def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有可用报告模板"""
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "chapters": len(t.chapters),
                "word_budget": t.total_word_budget,
            }
            for t in REPORT_TEMPLATES.values()
        ]

    def get_template(self, template_id: str) -> Optional[ReportTemplate]:
        return REPORT_TEMPLATES.get(template_id)

    # ========== 阶段 1: 选择模板 ==========

    def select_template(
        self,
        investigation_type: str = "comprehensive",
        data: Optional[Dict[str, Any]] = None,
    ) -> ReportTemplate:
        """根据调查类型自动选择报告模板"""
        mapping = {
            "comprehensive": "comprehensive",
            "litigation": "litigation",
            "credit": "credit",
            "compliance": "compliance",
            "basic": "executive",
            "risk": "risk_focus",
        }
        template_id = mapping.get(investigation_type, "comprehensive")
        return REPORT_TEMPLATES.get(template_id, REPORT_TEMPLATES["comprehensive"])

    # ========== 阶段 2-3: 切片与布局 ==========

    def plan_chapters(
        self,
        template: ReportTemplate,
        data: Dict[str, Any],
    ) -> List[ChapterTemplate]:
        """根据数据可用性规划实际章节"""
        planned = []
        for chapter in template.chapters:
            # 检查是否有所需数据
            has_data = any(
                data.get(key) for key in chapter.data_keys
            ) if chapter.data_keys else True

            if chapter.required or has_data:
                planned.append(chapter)

        return planned

    # ========== 阶段 4: 字数预算 ==========

    def allocate_word_budget(
        self,
        chapters: List[ChapterTemplate],
        total_budget: int,
    ) -> Dict[str, int]:
        """分配各章节字数预算"""
        # 按模板预设比例分配
        total_preset = sum(c.word_budget for c in chapters)
        budget_map = {}
        for chapter in chapters:
            if total_preset > 0:
                ratio = chapter.word_budget / total_preset
                budget_map[chapter.id] = max(100, int(total_budget * ratio))
            else:
                budget_map[chapter.id] = total_budget // len(chapters)
        return budget_map

    # ========== 阶段 5: 章节逐一生成 ==========

    async def generate_chapter(
        self,
        chapter: ChapterTemplate,
        data: Dict[str, Any],
        company_name: str,
        word_budget: int,
        use_llm: bool = True,
    ) -> ReportSection:
        """生成单个报告章节"""
        # 提取该章节所需数据
        chapter_data = {}
        for key in chapter.data_keys:
            if key in data:
                chapter_data[key] = data[key]

        # 尝试使用 LLM 生成增强内容
        if use_llm and self.llm_agent and chapter_data:
            try:
                content = await self._llm_generate_chapter(
                    chapter, chapter_data, company_name, word_budget
                )
                if content and len(content) > 50:
                    status = self._assess_chapter_status(chapter.id, chapter_data)
                    return ReportSection(
                        id=chapter.id,
                        title=chapter.title,
                        content=content,
                        status=status,
                        word_count=len(content),
                    )
            except Exception as e:
                logger.warning(f"LLM 生成章节 {chapter.id} 失败: {e}")

        # Fallback: 模板化生成
        content = self._template_generate_chapter(chapter, chapter_data, company_name)
        status = self._assess_chapter_status(chapter.id, chapter_data)
        return ReportSection(
            id=chapter.id,
            title=chapter.title,
            content=content,
            status=status,
            word_count=len(content),
        )

    async def _llm_generate_chapter(
        self,
        chapter: ChapterTemplate,
        chapter_data: Dict[str, Any],
        company_name: str,
        word_budget: int,
    ) -> str:
        """使用 LLM 生成章节内容"""
        data_str = json.dumps(chapter_data, ensure_ascii=False, default=str)[:2000]

        prompt = f"""请为「{company_name}」的尽职调查报告撰写以下章节：

章节标题：{chapter.title}
章节说明：{chapter.description}
目标字数：{word_budget} 字

数据支撑：
{data_str}

写作要求：
1. 语言专业、客观，符合法律尽调报告规范
2. 数据引用准确，观点有据可循
3. 重点突出风险和关注事项
4. 字数控制在 {word_budget} 字左右
5. 使用清晰的分段和要点列表

请直接输出章节正文内容（纯文本，可用序号和项目符号）。"""

        return await self.llm_agent.chat(
            message=prompt,
            system_prompt_override=(
                "你是资深法律尽职调查报告撰写专家。"
                "请撰写专业、客观、结构清晰的报告章节内容。直接输出正文。"
            ),
        )

    def _template_generate_chapter(
        self,
        chapter: ChapterTemplate,
        chapter_data: Dict[str, Any],
        company_name: str,
    ) -> str:
        """模板化生成章节（fallback）"""
        generators = {
            "executive_summary": self._gen_executive_summary,
            "summary": self._gen_executive_summary,
            "company_profile": self._gen_company_profile,
            "risk_assessment": self._gen_risk_assessment,
            "litigation_analysis": self._gen_litigation_analysis,
            "case_analysis": self._gen_litigation_analysis,
            "credit_compliance": self._gen_credit_compliance,
            "credit_rating": self._gen_credit_compliance,
            "compliance_check": self._gen_credit_compliance,
            "relationship_analysis": self._gen_relationship_analysis,
            "forum_debate": self._gen_forum_debate,
            "deep_research": self._gen_deep_research,
            "recommendations": self._gen_recommendations,
            "key_findings": self._gen_key_findings,
            "action_items": self._gen_action_items,
        }

        generator = generators.get(chapter.id, self._gen_generic)
        return generator(company_name, chapter_data)

    def _assess_chapter_status(self, chapter_id: str, data: Dict[str, Any]) -> str:
        """评估章节状态"""
        risk = data.get("risk", {})
        litigation = data.get("litigation", {})
        credit = data.get("credit", {})

        if chapter_id in ("risk_assessment", "risk_trends"):
            scores = [
                risk.get("operation_risk", 0),
                risk.get("litigation_risk", 0),
                risk.get("credit_risk", 0),
                risk.get("compliance_risk", 0),
                risk.get("relation_risk", 0),
            ]
            avg = sum(scores) / len(scores) if scores else 0
            return "fail" if avg > 60 else "warning" if avg > 35 else "pass"

        if chapter_id in ("litigation_analysis", "case_analysis", "execution_risk"):
            total = int(litigation.get("plaintiff_cases", 0)) + int(litigation.get("defendant_cases", 0))
            return "fail" if total > 5 else "warning" if total > 0 else "pass"

        if chapter_id in ("credit_compliance", "credit_rating", "compliance_check"):
            rating = credit.get("credit_rating", "B")
            if rating in ("A", "AA", "AAA"):
                return "pass"
            elif rating in ("C", "D"):
                return "fail"
            return "warning"

        return "normal"

    # ========== 模板化章节生成器 ==========

    def _gen_executive_summary(self, company_name: str, data: Dict) -> str:
        risk = data.get("risk", {})
        consensus = data.get("consensus", {})
        scores = [risk.get(k, 0) for k in ("operation_risk", "litigation_risk", "credit_risk", "compliance_risk", "relation_risk")]
        avg_risk = sum(scores) / len(scores) if scores else 0
        risk_label = "高风险" if avg_risk > 60 else "中风险" if avg_risk > 35 else "低风险"

        parts = [
            f"本报告对「{company_name}」进行了全面的尽职调查分析。",
            f"调查涵盖企业基本信息、风险评估、诉讼分析、信用合规及关联关系等多个维度。",
            f"\n综合风险评分：{avg_risk:.0f}/100，整体风险等级：{risk_label}。",
        ]

        if consensus.get("debate_summary"):
            parts.append(f"\n\n多专家论证结论：{consensus['debate_summary']}")

        if consensus.get("key_conclusions"):
            parts.append("\n\n核心结论：")
            for i, c in enumerate(consensus["key_conclusions"][:5], 1):
                parts.append(f"  {i}. {c}")

        return "\n".join(parts)

    def _gen_company_profile(self, company_name: str, data: Dict) -> str:
        basic = data.get("basic_info", {})
        fields = [
            ("name", "企业名称"), ("legal_representative", "法定代表人"),
            ("registered_capital", "注册资本"), ("established_date", "成立日期"),
            ("status", "经营状态"), ("business_scope", "经营范围"),
            ("address", "注册地址"), ("company_type", "企业类型"),
            ("credit_code", "统一社会信用代码"),
        ]
        lines = []
        for key, label in fields:
            val = basic.get(key, "-")
            if val and val != "-":
                lines.append(f"{label}：{val}")
        return "\n".join(lines) if lines else "暂无企业基本信息"

    def _gen_risk_assessment(self, company_name: str, data: Dict) -> str:
        risk = data.get("risk", {})
        dimensions = [
            ("operation_risk", "经营风险"), ("litigation_risk", "诉讼风险"),
            ("credit_risk", "信用风险"), ("compliance_risk", "合规风险"),
            ("relation_risk", "关联风险"),
        ]
        lines = [f"「{company_name}」五维风险评估：\n"]
        for key, label in dimensions:
            score = risk.get(key, 0)
            level = "🔴 高" if score > 60 else "🟡 中" if score > 35 else "🟢 低"
            bar = "█" * (score // 10) + "░" * (10 - score // 10)
            lines.append(f"  {label}：{score}/100 [{bar}] {level}")

        scores = [risk.get(k, 0) for k in dict(dimensions)]
        avg = sum(scores) / len(scores) if scores else 0
        lines.append(f"\n综合评分：{avg:.0f}/100")

        if risk.get("risk_points"):
            lines.append("\n主要风险点：")
            for i, p in enumerate(risk["risk_points"], 1):
                lines.append(f"  {i}. {p}")

        return "\n".join(lines)

    def _gen_litigation_analysis(self, company_name: str, data: Dict) -> str:
        lit = data.get("litigation", {})
        lines = [
            f"涉诉总数：{int(lit.get('plaintiff_cases', 0)) + int(lit.get('defendant_cases', 0))} 起",
            f"  作为原告：{lit.get('plaintiff_cases', 0)} 起",
            f"  作为被告：{lit.get('defendant_cases', 0)} 起",
            f"执行案件：{lit.get('execution_cases', 0)} 起",
            f"失信记录：{lit.get('dishonest_records', 0)} 条",
        ]
        major = lit.get("major_cases", [])
        if major:
            lines.append("\n主要案件：")
            for i, c in enumerate(major[:5], 1):
                case_no = c.get("case_no", c.get("caseNo", "未公布"))
                case_type = c.get("case_type", c.get("type", "未知"))
                lines.append(f"  {i}. {case_no} — {case_type}")
        return "\n".join(lines)

    def _gen_credit_compliance(self, company_name: str, data: Dict) -> str:
        credit = data.get("credit", {})
        lines = [
            f"信用评级：{credit.get('credit_rating', '-')}",
            f"行政处罚：{credit.get('administrative_penalties', 0)} 条",
            f"税务违规：{credit.get('tax_violations', 0)} 条",
            f"环保处罚：{credit.get('environmental_penalties', 0)} 条",
            f"经营异常：{credit.get('abnormal_operations', 0)} 条",
            f"严重违法：{credit.get('serious_violations', 0)} 条",
        ]
        return "\n".join(lines)

    def _gen_relationship_analysis(self, company_name: str, data: Dict) -> str:
        return f"「{company_name}」的股权结构和关联关系分析。\n\n（详细关联图谱请参见平台交互式图谱功能）"

    def _gen_forum_debate(self, company_name: str, data: Dict) -> str:
        forum = data.get("forum", {})
        conflicts = data.get("conflicts", [])
        if not forum and not conflicts:
            return "本次调查未进行多专家论证。"

        consensus = forum.get("consensus", {})
        parts = [f"共有 {len(forum.get('agents_participated', []))} 位专家参与论证。"]

        if conflicts:
            parts.append(f"\n发现 {len(conflicts)} 处分析分歧：")
            for i, c in enumerate(conflicts, 1):
                if isinstance(c, dict):
                    parts.append(f"  {i}. {c.get('topic', c.get('description', ''))}")
                    if c.get("resolution") or c.get("resolved"):
                        parts.append(f"     → 裁决：{c.get('resolution', '已解决')}")

        if consensus.get("debate_summary"):
            parts.append(f"\n论证结论：{consensus['debate_summary']}")

        return "\n".join(parts)

    def _gen_deep_research(self, company_name: str, data: Dict) -> str:
        research = data.get("research", {})
        if not research:
            return "本次调查未进行深度研究。"

        parts = [
            f"共进行 {research.get('total_rounds', 0)} 轮迭代式深度研究。",
            f"搜索结果总数：{research.get('total_results', 0)} 条。",
            f"研究信心：{research.get('confidence', 0):.0%}。",
        ]
        if research.get("summary"):
            parts.append(f"\n研究摘要：\n{research['summary']}")
        return "\n".join(parts)

    def _gen_recommendations(self, company_name: str, data: Dict) -> str:
        risk = data.get("risk", {})
        consensus = data.get("consensus", {})

        items = (
            consensus.get("action_items")
            or risk.get("recommendations")
            or [
                "定期监控企业风险指标变化",
                "关注涉诉案件进展",
                "持续跟踪信用评级动态",
                "建立合规预警机制",
                "评估关联企业风险传导",
            ]
        )
        return "\n".join(f"{i}. {r}" for i, r in enumerate(items, 1))

    def _gen_key_findings(self, company_name: str, data: Dict) -> str:
        risk = data.get("risk", {})
        lit = data.get("litigation", {})
        points = risk.get("risk_points", [])
        lines = []
        if points:
            for i, p in enumerate(points, 1):
                lines.append(f"{i}. {p}")
        total_cases = int(lit.get("plaintiff_cases", 0)) + int(lit.get("defendant_cases", 0))
        if total_cases > 0:
            lines.append(f"\n涉诉案件共 {total_cases} 起，需要重点关注。")
        return "\n".join(lines) if lines else "未发现显著风险点。"

    def _gen_action_items(self, company_name: str, data: Dict) -> str:
        return self._gen_recommendations(company_name, data)

    def _gen_generic(self, company_name: str, data: Dict) -> str:
        return f"「{company_name}」相关分析。\n\n数据摘要：{json.dumps(data, ensure_ascii=False, default=str)[:500]}"

    # ========== 阶段 6: 组装与渲染 ==========

    async def generate_report_stream(
        self,
        investigation_data: Dict[str, Any],
        template_id: str = "comprehensive",
        use_llm: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式生成报告，逐章返回进度

        事件类型：
        - report_start: 开始生成
        - template_selected: 模板选中
        - chapter_start: 章节开始生成
        - chapter_done: 章节生成完成
        - report_done: 报告完成
        """
        company_name = investigation_data.get("company_name", "未知企业")

        # 阶段 1: 选择模板
        template = self.get_template(template_id) or self.select_template("comprehensive")

        yield {
            "type": "report_start",
            "template": template.name,
            "total_chapters": len(template.chapters),
        }

        yield {
            "type": "template_selected",
            "template_id": template.id,
            "template_name": template.name,
            "chapters": [{"id": c.id, "title": c.title} for c in template.chapters],
        }

        # 阶段 2-3: 规划章节
        planned_chapters = self.plan_chapters(template, investigation_data)

        # 阶段 4: 分配字数预算
        budget_map = self.allocate_word_budget(planned_chapters, template.total_word_budget)

        # 阶段 5: 逐章生成
        sections: List[ReportSection] = []
        for i, chapter in enumerate(planned_chapters, 1):
            yield {
                "type": "chapter_start",
                "chapter_index": i,
                "chapter_id": chapter.id,
                "chapter_title": chapter.title,
                "word_budget": budget_map.get(chapter.id, 300),
            }

            try:
                section = await self.generate_chapter(
                    chapter,
                    investigation_data,
                    company_name,
                    budget_map.get(chapter.id, 300),
                    use_llm=use_llm,
                )
                sections.append(section)

                yield {
                    "type": "chapter_done",
                    "chapter_index": i,
                    "chapter_id": chapter.id,
                    "section": section.to_dict(),
                }
            except Exception as e:
                logger.error(f"章节 {chapter.id} 生成失败: {e}")
                fallback_section = ReportSection(
                    id=chapter.id,
                    title=chapter.title,
                    content=f"（章节生成失败：{str(e)[:100]}）",
                    status="fail",
                )
                sections.append(fallback_section)

                yield {
                    "type": "chapter_done",
                    "chapter_index": i,
                    "chapter_id": chapter.id,
                    "section": fallback_section.to_dict(),
                    "error": str(e),
                }

        # 阶段 6: 组装
        html = self.render_html(sections, company_name)

        yield {
            "type": "report_done",
            "format": "html",
            "content": html,
            "sections_count": len(sections),
            "total_words": sum(s.word_count for s in sections),
        }

    # ========== 兼容旧接口 ==========

    def generate_ir(self, investigation_data: Dict[str, Any]) -> List[ReportSection]:
        """生成中间表示（IR）— 兼容旧接口"""
        template = self.select_template("comprehensive")
        chapters = self.plan_chapters(template, investigation_data)
        company_name = investigation_data.get("company_name", "未知企业")

        sections = []
        for chapter in chapters:
            content = self._template_generate_chapter(
                chapter, investigation_data, company_name
            )
            status = self._assess_chapter_status(chapter.id, investigation_data)
            sections.append(ReportSection(
                id=chapter.id, title=chapter.title, content=content, status=status
            ))
        return sections

    def render_html(self, sections: List[ReportSection], company_name: str) -> str:
        """渲染为 HTML 报告"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        status_labels = {"pass": "✅ 正常", "warning": "⚠️ 关注", "fail": "❌ 异常"}

        html_parts = [
            "<!DOCTYPE html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="UTF-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f"<title>{company_name} — 尽职调查报告</title>",
            "<style>",
            "* { box-sizing: border-box; margin: 0; padding: 0; }",
            "body { font-family: 'PingFang SC', 'Microsoft YaHei', -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 40px 30px; color: #1C1C1E; line-height: 1.8; background: #FAFAFA; }",
            ".report-header { text-align: center; padding: 30px 0; margin-bottom: 30px; border-bottom: 3px solid #007AFF; }",
            ".report-header h1 { color: #007AFF; font-size: 24px; margin-bottom: 8px; }",
            ".report-header .subtitle { color: #8E8E93; font-size: 14px; }",
            ".report-header .meta { color: #8E8E93; font-size: 12px; margin-top: 12px; }",
            ".toc { background: #F2F2F7; padding: 20px 24px; border-radius: 12px; margin-bottom: 30px; }",
            ".toc h2 { font-size: 16px; color: #1C1C1E; margin-bottom: 12px; }",
            ".toc-item { display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px; color: #3C3C43; }",
            ".chapter { background: white; padding: 24px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }",
            ".chapter h2 { color: #1C1C1E; font-size: 18px; padding: 8px 12px; background: #F2F2F7; border-left: 4px solid #007AFF; border-radius: 4px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }",
            ".chapter pre { white-space: pre-wrap; font-family: inherit; line-height: 1.8; font-size: 14px; color: #3C3C43; }",
            ".status-pass { color: #34C759; font-size: 13px; } .status-warning { color: #FF9500; font-size: 13px; } .status-fail { color: #FF3B30; font-size: 13px; }",
            ".footer { text-align: center; color: #8E8E93; font-size: 12px; margin-top: 40px; padding: 20px 0; border-top: 1px solid #E5E5EA; }",
            "@media print { body { background: white; } .chapter { box-shadow: none; border: 1px solid #E5E5EA; } }",
            "</style>",
            "</head>",
            "<body>",
            '<div class="report-header">',
            f'<h1>{company_name}</h1>',
            '<div class="subtitle">企业尽职调查报告</div>',
            f'<div class="meta">安心智能法律服务平台 · AI 辅助生成 · {now}</div>',
            "</div>",
        ]

        # 目录
        html_parts.append('<div class="toc">')
        html_parts.append("<h2>目录</h2>")
        for i, section in enumerate(sections, 1):
            status_tag = ""
            if section.status in status_labels:
                status_tag = f' <span class="status-{section.status}">{status_labels[section.status]}</span>'
            html_parts.append(
                f'<div class="toc-item"><span>{i}. {section.title}</span>{status_tag}</div>'
            )
        html_parts.append("</div>")

        # 章节
        for i, section in enumerate(sections, 1):
            status_html = ""
            if section.status in status_labels:
                css_class = f"status-{section.status}"
                status_html = f'<span class="{css_class}">[{status_labels[section.status]}]</span>'

            html_parts.append(f'<div class="chapter" id="{section.id}">')
            html_parts.append(f"<h2>{i}. {section.title} {status_html}</h2>")
            html_parts.append(f"<pre>{section.content}</pre>")
            html_parts.append("</div>")

        html_parts.extend([
            '<div class="footer">',
            "<p>本报告由安心智能法律服务平台 AI 辅助生成，仅供参考</p>",
            "<p>报告中的数据和分析基于公开信息，建议在正式决策前进行核实</p>",
            f"<p>生成时间：{now}</p>",
            "</div>",
            "</body></html>",
        ])

        return "\n".join(html_parts)

    async def generate_report(
        self,
        investigation_data: Dict[str, Any],
        output_format: str = "html",
        template_id: str = "comprehensive",
        use_llm: bool = False,
    ) -> Dict[str, Any]:
        """
        生成完整调查报告（兼容旧接口 + 新功能）
        """
        company_name = investigation_data.get("company_name", "未知企业")

        # 使用新模板系统
        template = self.get_template(template_id) or self.select_template("comprehensive")
        chapters = self.plan_chapters(template, investigation_data)
        budget_map = self.allocate_word_budget(chapters, template.total_word_budget)

        sections = []
        for chapter in chapters:
            section = await self.generate_chapter(
                chapter,
                investigation_data,
                company_name,
                budget_map.get(chapter.id, 300),
                use_llm=use_llm,
            )
            sections.append(section)

        if output_format == "html":
            html = self.render_html(sections, company_name)
            return {
                "format": "html",
                "content": html,
                "company_name": company_name,
                "template": template.name,
                "sections": len(sections),
                "total_words": sum(s.word_count for s in sections),
                "generated_at": datetime.now().isoformat(),
            }
        else:
            return {
                "format": "json",
                "company_name": company_name,
                "template": template.name,
                "sections": [s.to_dict() for s in sections],
                "generated_at": datetime.now().isoformat(),
            }


# 全局实例
report_engine = ReportEngine()
