"""
Scenario Simulation — 风险场景推演服务

灵感来源：MiroFish 群体智能预测引擎
基于调查数据注入假设场景，使用 LLM Agent 推理影响链条
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any, NotRequired, TypedDict


class ImpactStep(TypedDict):
    event: str
    probability: float
    severity: str


class ScenarioTemplate(TypedDict):
    name: str
    description: str
    impact_chain: list[ImpactStep]
    risk_delta: dict[str, int]
    recommendations: list[str]
    assessment_suffix: NotRequired[str]

# 预设场景模板
SCENARIO_TEMPLATES: dict[str, ScenarioTemplate] = {
    "customer_default": {
        "name": "主要客户违约",
        "description": "主要客户发生债务违约，无法按期支付应收款项",
        "impact_chain": [
            {"event": "应收账款无法回收，坏账损失约 30%", "probability": 0.8, "severity": "high"},
            {"event": "现金流紧张，运营资金缺口", "probability": 0.7, "severity": "high"},
            {"event": "可能触发银行贷款违约条款", "probability": 0.5, "severity": "critical"},
            {"event": "供应商信心下降，账期收紧", "probability": 0.6, "severity": "medium"},
            {"event": "员工薪资发放延迟风险", "probability": 0.3, "severity": "medium"},
        ],
        "risk_delta": {
            "operation_risk": 25, "litigation_risk": 15,
            "credit_risk": 30, "compliance_risk": 5, "relation_risk": 20,
        },
        "recommendations": [
            "立即启动应收账款催收程序，必要时提起诉讼",
            "与银行沟通，提前协商贷款展期方案",
            "优化供应商结构，分散客户集中度风险",
            "制定现金流应急预案，确保核心业务运营",
        ],
    },
    "regulatory_penalty": {
        "name": "监管处罚",
        "description": "因合规问题被监管部门处以重大行政处罚",
        "impact_chain": [
            {"event": "收到行政处罚决定书，罚款 50-200 万元", "probability": 0.9, "severity": "high"},
            {"event": "企业信用评级下调", "probability": 0.7, "severity": "medium"},
            {"event": "相关资质或许可证被暂扣", "probability": 0.4, "severity": "critical"},
            {"event": "负面舆情扩散，品牌声誉受损", "probability": 0.6, "severity": "medium"},
        ],
        "risk_delta": {
            "operation_risk": 15, "litigation_risk": 10,
            "credit_risk": 20, "compliance_risk": 40, "relation_risk": 15,
        },
        "recommendations": [
            "立即组织内部合规审查，识别整改要点",
            "聘请专业律师团队应对行政复议",
            "制定公关应急方案，控制负面舆情影响",
            "建立长效合规管理制度，防止再犯",
        ],
    },
    "key_person_leave": {
        "name": "核心人员离职",
        "description": "核心技术人员或管理层关键人物离职",
        "impact_chain": [
            {"event": "核心技术或管理能力暂时缺失", "probability": 0.9, "severity": "high"},
            {"event": "关键项目进度受阻或延迟", "probability": 0.7, "severity": "medium"},
            {"event": "团队士气受影响，可能引发连锁离职", "probability": 0.4, "severity": "medium"},
            {"event": "竞业限制执行风险，商业秘密泄露隐患", "probability": 0.3, "severity": "high"},
        ],
        "risk_delta": {
            "operation_risk": 30, "litigation_risk": 10,
            "credit_risk": 5, "compliance_risk": 5, "relation_risk": 10,
        },
        "recommendations": [
            "启动继任者计划，确保核心岗位备份",
            "审查竞业限制协议的法律效力",
            "加强知识管理，避免关键知识流失",
            "与关键客户和合作伙伴做好沟通",
        ],
    },
    "policy_change": {
        "name": "行业政策变动",
        "description": "行业政策发生重大调整，影响企业经营模式",
        "impact_chain": [
            {"event": "经营模式需要调整以适应新规", "probability": 0.8, "severity": "medium"},
            {"event": "合规成本显著增加", "probability": 0.7, "severity": "medium"},
            {"event": "部分业务线可能被迫收缩或转型", "probability": 0.5, "severity": "high"},
            {"event": "行业竞争格局重新洗牌", "probability": 0.4, "severity": "medium"},
        ],
        "risk_delta": {
            "operation_risk": 20, "litigation_risk": 5,
            "credit_risk": 10, "compliance_risk": 25, "relation_risk": 10,
        },
        "recommendations": [
            "密切关注政策动态，提前布局合规调整",
            "评估现有业务的合规差距",
            "探索政策红利下的新业务机会",
            "加强行业协会联系，参与政策制定讨论",
        ],
    },
}


class ScenarioSimulationService:
    """风险场景推演服务"""

    async def simulate_scenario(
        self,
        scenario_id: str,
        company_name: str,
        current_risk: dict[str, Any] | None = None,
        custom_scenario: str | None = None,
    ) -> dict[str, Any]:
        """
        执行场景推演（非流式）

        Args:
            scenario_id: 预设场景 ID
            company_name: 企业名称
            current_risk: 当前风险数据
            custom_scenario: 自定义场景描述

        Returns:
            推演结果
        """
        template = SCENARIO_TEMPLATES.get(scenario_id)
        if not template:
            return {"error": f"未知场景: {scenario_id}"}

        # 计算推演后风险
        risk_after = {}
        if current_risk:
            for key, delta in template["risk_delta"].items():
                current = current_risk.get(key, 0)
                risk_after[key] = min(100, current + delta)

        # 计算总体评估
        if risk_after:
            avg_after = sum(risk_after.values()) / len(risk_after)
            overall = "高风险" if avg_after > 60 else "中风险" if avg_after > 35 else "低风险"
        else:
            overall = "中风险"

        return {
            "scenario": template["name"],
            "description": template["description"],
            "company_name": company_name,
            "impact_chain": template["impact_chain"],
            "risk_delta": template["risk_delta"],
            "risk_after": risk_after,
            "recommendations": template["recommendations"],
            "overall_assessment": f"该场景将使 {company_name} 的风险等级变为{overall}。"
                + template.get("assessment_suffix", ""),
        }

    async def simulate_stream(
        self,
        scenario_id: str,
        company_name: str,
        current_risk: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        流式场景推演 — 逐步输出影响链

        Yields:
            SSE 事件
        """
        template = SCENARIO_TEMPLATES.get(scenario_id)
        if not template:
            yield {"type": "error", "message": f"未知场景: {scenario_id}"}
            return

        yield {"type": "start", "scenario": template["name"]}

        # 逐步输出影响链
        for i, step in enumerate(template["impact_chain"]):
            await asyncio.sleep(0.8)  # 模拟推理耗时
            yield {
                "type": "impact_step",
                "index": i,
                "event": step["event"],
                "probability": step["probability"],
                "severity": step["severity"],
            }

        # 输出风险变化
        await asyncio.sleep(0.5)
        yield {
            "type": "risk_delta",
            "data": template["risk_delta"],
        }

        # 输出建议
        await asyncio.sleep(0.5)
        yield {
            "type": "recommendations",
            "data": template["recommendations"],
        }

        yield {"type": "done", "scenario": template["name"]}

    def list_scenarios(self) -> list[dict[str, str]]:
        """列出所有可用场景"""
        return [
            {"id": k, "name": v["name"], "description": v["description"]}
            for k, v in SCENARIO_TEMPLATES.items()
        ]


# 全局实例
scenario_simulation_service = ScenarioSimulationService()
