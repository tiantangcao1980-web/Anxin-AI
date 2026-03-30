# -*- coding: utf-8 -*-
"""
Report Engine — 调查报告生成引擎

灵感来源：BettaFish IR 中间表示报告引擎
流程：调查数据 → IR (结构化章节字典) → HTML 模板 → PDF

报告章节：
1. 执行摘要
2. 企业概况
3. 风险评估
4. 诉讼分析
5. 信用合规
6. 关系分析
7. 舆情概览
8. 建议措施
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger


class ReportSection:
    """报告章节"""

    def __init__(self, id: str, title: str, content: str, status: str = "normal"):
        self.id = id
        self.title = title
        self.content = content
        self.status = status  # normal, pass, warning, fail


class ReportEngine:
    """调查报告生成引擎"""

    def generate_ir(self, investigation_data: Dict[str, Any]) -> List[ReportSection]:
        """
        生成中间表示（IR）— 结构化报告章节

        Args:
            investigation_data: 包含 basic_info, risk, litigation, credit, consensus 的调查数据

        Returns:
            ReportSection 列表
        """
        company_name = investigation_data.get("company_name", "未知企业")
        basic_info = investigation_data.get("basic_info", {})
        risk = investigation_data.get("risk", {})
        litigation = investigation_data.get("litigation", {})
        credit = investigation_data.get("credit", {})
        consensus = investigation_data.get("consensus", {})
        conflicts = investigation_data.get("conflicts", [])

        # 计算风险评分
        risk_scores = [
            risk.get("operation_risk", 0),
            risk.get("litigation_risk", 0),
            risk.get("credit_risk", 0),
            risk.get("compliance_risk", 0),
            risk.get("relation_risk", 0),
        ]
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        risk_level = "高风险" if avg_risk > 60 else "中风险" if avg_risk > 35 else "低风险"

        sections = []

        # 1. 执行摘要
        summary_parts = [
            f"本报告对 {company_name} 进行了全面的尽职调查分析。",
            f"调查涵盖企业基本信息、风险评估、诉讼分析、信用合规及关联关系等多个维度。",
            f"\n综合风险评分为 {avg_risk:.0f} 分（满分 100），整体风险等级为{risk_level}。",
        ]
        if consensus.get("debate_summary"):
            summary_parts.append(f"\n\n共识分析：{consensus['debate_summary']}")
        if conflicts:
            summary_parts.append(f"\n\n调查过程中发现 {len(conflicts)} 处数据矛盾。")

        sections.append(ReportSection(
            "summary", "执行摘要", "".join(summary_parts)
        ))

        # 2. 企业概况
        company_lines = []
        field_map = [
            ("name", "企业名称"), ("legal_representative", "法定代表人"),
            ("registered_capital", "注册资本"), ("established_date", "成立日期"),
            ("status", "经营状态"), ("business_scope", "经营范围"),
            ("address", "注册地址"), ("company_type", "企业类型"),
        ]
        for key, label in field_map:
            val = basic_info.get(key, "-")
            if val and val != "-":
                company_lines.append(f"{label}：{val}")

        sections.append(ReportSection(
            "company", "企业概况", "\n".join(company_lines) if company_lines else "暂无企业基本信息"
        ))

        # 3. 风险评估
        risk_status = "fail" if avg_risk > 60 else "warning" if avg_risk > 35 else "pass"
        risk_lines = [
            f"经营风险：{risk.get('operation_risk', 0)}/100",
            f"诉讼风险：{risk.get('litigation_risk', 0)}/100",
            f"信用风险：{risk.get('credit_risk', 0)}/100",
            f"合规风险：{risk.get('compliance_risk', 0)}/100",
            f"关联风险：{risk.get('relation_risk', 0)}/100",
            f"\n综合评分：{avg_risk:.0f}/100",
            f"风险等级：{risk_level}",
        ]
        if risk.get("risk_points"):
            risk_lines.append("\n主要风险点：")
            for i, point in enumerate(risk["risk_points"], 1):
                risk_lines.append(f"  {i}. {point}")

        sections.append(ReportSection(
            "risk", "风险评估", "\n".join(risk_lines), risk_status
        ))

        # 4. 诉讼分析
        lit_count = litigation.get("plaintiff_cases", 0) + litigation.get("defendant_cases", 0)
        lit_status = "fail" if lit_count > 5 else "warning" if lit_count > 0 else "pass"
        lit_lines = [
            f"涉诉总数：{lit_count} 起",
            f"作为原告：{litigation.get('plaintiff_cases', 0)} 起",
            f"作为被告：{litigation.get('defendant_cases', 0)} 起",
            f"执行案件：{litigation.get('execution_cases', 0)} 起",
            f"失信记录：{litigation.get('dishonest_records', 0)} 条",
        ]
        major_cases = litigation.get("major_cases", [])
        if major_cases:
            lit_lines.append("\n主要案件：")
            for i, case in enumerate(major_cases[:5], 1):
                case_no = case.get("case_no", case.get("caseNo", "未公布"))
                case_type = case.get("case_type", case.get("type", "未知"))
                role = case.get("role", "未知")
                lit_lines.append(f"  {i}. {case_no} - {case_type} ({role})")

        sections.append(ReportSection(
            "litigation", "诉讼分析", "\n".join(lit_lines), lit_status
        ))

        # 5. 信用合规
        credit_rating = credit.get("credit_rating", "-")
        credit_status = "pass" if credit_rating >= "A" else "warning" if credit_rating else "pass"
        credit_lines = [
            f"信用评级：{credit_rating}",
            f"行政处罚：{credit.get('administrative_penalties', 0)} 条",
            f"税务违规：{credit.get('tax_violations', 0)} 条",
            f"环保处罚：{credit.get('environmental_penalties', 0)} 条",
            f"经营异常：{credit.get('abnormal_operations', 0)} 条",
            f"严重违法：{credit.get('serious_violations', 0)} 条",
        ]

        sections.append(ReportSection(
            "compliance", "信用合规", "\n".join(credit_lines), credit_status
        ))

        # 6. 建议措施
        recommendations = risk.get("recommendations", [
            "定期监控企业风险指标变化",
            "关注涉诉案件进展",
            "持续跟踪信用评级动态",
            "建立合规预警机制",
            "评估关联企业风险传导",
        ])
        rec_lines = [f"{i}. {r}" for i, r in enumerate(recommendations, 1)]

        sections.append(ReportSection(
            "recommendations", "建议措施", "\n".join(rec_lines)
        ))

        return sections

    def render_html(self, sections: List[ReportSection], company_name: str) -> str:
        """渲染为 HTML 报告"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_parts = [
            "<!DOCTYPE html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="UTF-8">',
            f"<title>{company_name} — 尽职调查报告</title>",
            "<style>",
            "body { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; max-width: 800px; margin: 0 auto; padding: 40px; color: #1C1C1E; }",
            "h1 { text-align: center; color: #007AFF; border-bottom: 2px solid #007AFF; padding-bottom: 10px; }",
            "h2 { color: #1C1C1E; margin-top: 30px; padding: 8px 12px; background: #F2F2F7; border-left: 4px solid #007AFF; }",
            ".status-pass { color: #34C759; } .status-warning { color: #FF9500; } .status-fail { color: #FF3B30; }",
            "pre { white-space: pre-wrap; font-family: inherit; line-height: 1.8; }",
            ".footer { text-align: center; color: #8E8E93; font-size: 12px; margin-top: 40px; border-top: 1px solid #E5E5EA; padding-top: 20px; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{company_name}<br><small style='font-size:14px;color:#8E8E93'>尽职调查报告</small></h1>",
        ]

        status_labels = {"pass": "✅ 正常", "warning": "⚠️ 关注", "fail": "❌ 异常"}

        for section in sections:
            status_html = ""
            if section.status in status_labels:
                css_class = f"status-{section.status}"
                status_html = f' <span class="{css_class}">[{status_labels[section.status]}]</span>'

            html_parts.append(f"<h2>{section.title}{status_html}</h2>")
            html_parts.append(f"<pre>{section.content}</pre>")

        html_parts.extend([
            '<div class="footer">',
            f"<p>本报告由安心智能法律服务平台 AI 辅助生成，仅供参考</p>",
            f"<p>生成时间：{now}</p>",
            "</div>",
            "</body></html>",
        ])

        return "\n".join(html_parts)

    async def generate_report(
        self,
        investigation_data: Dict[str, Any],
        output_format: str = "html",
    ) -> Dict[str, Any]:
        """
        生成完整调查报告

        Args:
            investigation_data: 调查数据
            output_format: html / json

        Returns:
            包含报告内容的字典
        """
        company_name = investigation_data.get("company_name", "未知企业")

        # 生成 IR
        sections = self.generate_ir(investigation_data)

        if output_format == "html":
            html = self.render_html(sections, company_name)
            return {
                "format": "html",
                "content": html,
                "company_name": company_name,
                "sections": len(sections),
                "generated_at": datetime.now().isoformat(),
            }
        else:
            return {
                "format": "json",
                "company_name": company_name,
                "sections": [
                    {"id": s.id, "title": s.title, "content": s.content, "status": s.status}
                    for s in sections
                ],
                "generated_at": datetime.now().isoformat(),
            }


# 全局实例
report_engine = ReportEngine()
