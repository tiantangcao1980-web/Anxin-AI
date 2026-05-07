"""
企业合规自检 API

免费引流工具 — 用户无需登录即可使用基础版
完整报告需要登录/注册

功能：
1. 选择行业和企业规模
2. 回答合规检查清单问题
3. AI 生成合规评分和风险报告
4. 引导注册/升级获取完整报告
"""

from datetime import datetime
from typing import Any, Literal, TypedDict

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.core.deps import get_current_user_required
from src.models.user import User

router = APIRouter(prefix="/compliance-check", tags=["合规自检"])


# ===== 行业模板数据 =====

RiskLevel = Literal["high", "medium", "low"]


class ComplianceTemplateItem(TypedDict):
    id: str
    question: str
    risk_level: RiskLevel
    law_ref: str


class ComplianceTemplateCategory(TypedDict):
    name: str
    items: list[ComplianceTemplateItem]


class ComplianceTemplate(TypedDict):
    name: str
    categories: list[ComplianceTemplateCategory]


INDUSTRY_TEMPLATES: dict[str, ComplianceTemplate] = {
    "technology": {
        "name": "科技/互联网",
        "categories": [
            {
                "name": "数据安全与隐私",
                "items": [
                    {"id": "tech_data_01", "question": "是否制定了个人信息保护政策？", "risk_level": "high", "law_ref": "《个人信息保护法》第13条"},
                    {"id": "tech_data_02", "question": "是否建立了数据分级分类制度？", "risk_level": "high", "law_ref": "《数据安全法》第21条"},
                    {"id": "tech_data_03", "question": "是否定期进行数据安全风险评估？", "risk_level": "medium", "law_ref": "《数据安全法》第30条"},
                    {"id": "tech_data_04", "question": "用户数据存储是否在境内？如有出境是否完成安全评估？", "risk_level": "high", "law_ref": "《个人信息保护法》第38条"},
                ],
            },
            {
                "name": "知识产权保护",
                "items": [
                    {"id": "tech_ip_01", "question": "核心技术是否已申请专利或著作权登记？", "risk_level": "medium", "law_ref": "《专利法》《著作权法》"},
                    {"id": "tech_ip_02", "question": "是否与员工签订了知识产权归属协议？", "risk_level": "medium", "law_ref": "《劳动合同法》"},
                    {"id": "tech_ip_03", "question": "是否建立了商业秘密保护制度？", "risk_level": "high", "law_ref": "《反不正当竞争法》第9条"},
                ],
            },
            {
                "name": "劳动用工合规",
                "items": [
                    {"id": "tech_labor_01", "question": "是否与全部员工签订书面劳动合同？", "risk_level": "high", "law_ref": "《劳动合同法》第10条"},
                    {"id": "tech_labor_02", "question": "是否按规定缴纳五险一金？", "risk_level": "high", "law_ref": "《社会保险法》第58条"},
                    {"id": "tech_labor_03", "question": "加班制度是否符合法律规定？", "risk_level": "medium", "law_ref": "《劳动法》第36-41条"},
                    {"id": "tech_labor_04", "question": "是否制定了员工手册并依法公示？", "risk_level": "low", "law_ref": "《劳动合同法》第4条"},
                ],
            },
            {
                "name": "合同管理",
                "items": [
                    {"id": "tech_contract_01", "question": "重要合同是否经过法务审查？", "risk_level": "high", "law_ref": "《民法典》合同编"},
                    {"id": "tech_contract_02", "question": "合同是否有完整的签署、归档、跟踪流程？", "risk_level": "medium", "law_ref": "企业内控规范"},
                    {"id": "tech_contract_03", "question": "是否定期检查合同到期和续约情况？", "risk_level": "low", "law_ref": "企业内控规范"},
                ],
            },
        ],
    },
    "manufacturing": {
        "name": "制造业",
        "categories": [
            {
                "name": "安全生产",
                "items": [
                    {"id": "mfg_safety_01", "question": "是否取得安全生产许可证？", "risk_level": "high", "law_ref": "《安全生产法》第62条"},
                    {"id": "mfg_safety_02", "question": "是否定期开展安全生产培训？", "risk_level": "high", "law_ref": "《安全生产法》第28条"},
                    {"id": "mfg_safety_03", "question": "是否制定了应急预案并定期演练？", "risk_level": "medium", "law_ref": "《安全生产法》第78条"},
                ],
            },
            {
                "name": "环境保护",
                "items": [
                    {"id": "mfg_env_01", "question": "是否完成环境影响评价？", "risk_level": "high", "law_ref": "《环境影响评价法》"},
                    {"id": "mfg_env_02", "question": "污染物排放是否达标？", "risk_level": "high", "law_ref": "《环境保护法》第42条"},
                    {"id": "mfg_env_03", "question": "危险废物处置是否合规？", "risk_level": "high", "law_ref": "《固体废物污染环境防治法》"},
                ],
            },
            {
                "name": "劳动用工合规",
                "items": [
                    {"id": "mfg_labor_01", "question": "是否与全部员工签订书面劳动合同？", "risk_level": "high", "law_ref": "《劳动合同法》第10条"},
                    {"id": "mfg_labor_02", "question": "是否按规定缴纳五险一金？", "risk_level": "high", "law_ref": "《社会保险法》第58条"},
                    {"id": "mfg_labor_03", "question": "是否依法为员工进行职业健康检查？", "risk_level": "high", "law_ref": "《职业病防治法》第35条"},
                ],
            },
        ],
    },
    "retail": {
        "name": "零售/电商",
        "categories": [
            {
                "name": "消费者权益",
                "items": [
                    {"id": "ret_consumer_01", "question": "商品/服务描述是否真实准确？", "risk_level": "high", "law_ref": "《消费者权益保护法》第20条"},
                    {"id": "ret_consumer_02", "question": "是否建立了完善的退换货制度？", "risk_level": "high", "law_ref": "《消费者权益保护法》第24条"},
                    {"id": "ret_consumer_03", "question": "促销活动是否合规？", "risk_level": "medium", "law_ref": "《反不正当竞争法》"},
                ],
            },
            {
                "name": "数据合规",
                "items": [
                    {"id": "ret_data_01", "question": "收集用户数据是否获得明确同意？", "risk_level": "high", "law_ref": "《个人信息保护法》第13条"},
                    {"id": "ret_data_02", "question": "是否制定了隐私政策并公示？", "risk_level": "high", "law_ref": "《个人信息保护法》第17条"},
                ],
            },
            {
                "name": "劳动用工",
                "items": [
                    {"id": "ret_labor_01", "question": "是否与全部员工签订书面劳动合同？", "risk_level": "high", "law_ref": "《劳动合同法》第10条"},
                    {"id": "ret_labor_02", "question": "是否按规定缴纳五险一金？", "risk_level": "high", "law_ref": "《社会保险法》第58条"},
                ],
            },
        ],
    },
}


# ===== 请求/响应模型 =====

class ComplianceAnswer(BaseModel):
    item_id: str
    answer: bool  # True=合规, False=不合规


class ComplianceCheckRequest(BaseModel):
    industry: str = Field(..., description="行业: technology/manufacturing/retail")
    company_size: str = Field("small", description="规模: micro/small/medium/large")
    answers: list[ComplianceAnswer] = Field(..., description="每道题的回答")


# ===== API 端点 =====

@router.get("/industries")
async def list_industries() -> dict[str, list[dict[str, str | int]]]:
    """获取支持的行业列表（无需登录）"""
    return {
        "industries": [
            {"id": k, "name": v["name"], "category_count": len(v["categories"]),
             "item_count": sum(len(c["items"]) for c in v["categories"])}
            for k, v in INDUSTRY_TEMPLATES.items()
        ]
    }


@router.get("/checklist/{industry}")
async def get_checklist(industry: str) -> dict[str, Any]:
    """获取行业合规检查清单（无需登录）"""
    template = INDUSTRY_TEMPLATES.get(industry)
    if not template:
        return {"error": "不支持的行业", "supported": list(INDUSTRY_TEMPLATES.keys())}
    return {
        "industry": industry,
        "industry_name": template["name"],
        "categories": template["categories"],
    }


@router.post("/evaluate")
async def evaluate_compliance(
    req: ComplianceCheckRequest,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """评估合规状况，生成报告（基础版免费，完整版需登录）"""
    template = INDUSTRY_TEMPLATES.get(req.industry)
    if not template:
        return {"error": "不支持的行业"}

    # 收集所有检查项
    all_items: dict[str, ComplianceTemplateItem] = {}
    for cat in template["categories"]:
        for item in cat["items"]:
            all_items[item["id"]] = item

    # 计算评分
    total = len(all_items)
    compliant = sum(1 for a in req.answers if a.answer)
    non_compliant_items: list[ComplianceTemplateItem] = []

    for a in req.answers:
        if not a.answer and a.item_id in all_items:
            item = all_items[a.item_id]
            non_compliant_items.append({
                "id": item["id"],
                "question": item["question"],
                "risk_level": item["risk_level"],
                "law_ref": item["law_ref"],
            })

    score = round((compliant / total) * 100) if total > 0 else 0

    # 风险等级
    high_risks = [i for i in non_compliant_items if i["risk_level"] == "high"]
    medium_risks = [i for i in non_compliant_items if i["risk_level"] == "medium"]
    low_risks = [i for i in non_compliant_items if i["risk_level"] == "low"]

    if score >= 90:
        grade = "A"
        grade_label = "优秀"
    elif score >= 75:
        grade = "B"
        grade_label = "良好"
    elif score >= 60:
        grade = "C"
        grade_label = "需改进"
    else:
        grade = "D"
        grade_label = "风险较高"

    # 基础报告（免费）
    report: dict[str, Any] = {
        "score": score,
        "grade": grade,
        "grade_label": grade_label,
        "total_items": total,
        "compliant_count": compliant,
        "non_compliant_count": total - compliant,
        "risk_summary": {
            "high": len(high_risks),
            "medium": len(medium_risks),
            "low": len(low_risks),
        },
        "industry": req.industry,
        "industry_name": template["name"],
        "evaluated_at": datetime.utcnow().isoformat(),
    }

    # 完整报告（需登录）
    if user:
        report["non_compliant_details"] = non_compliant_items
        report["recommendations"] = [
            f"【{item['risk_level'].upper()}】{item['question']} — 参考法规：{item['law_ref']}"
            for item in sorted(non_compliant_items, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["risk_level"]])
        ]
        report["full_report"] = True
    else:
        report["non_compliant_details"] = high_risks[:2]  # 免费版只显示2条高风险
        report["full_report"] = False
        report["upgrade_hint"] = "登录后查看完整合规报告和整改建议"

    return report


# ===== 报告生成 =====

class ReportRequest(BaseModel):
    """报告生成请求"""
    evaluation: dict[str, Any] = Field(..., description="评估结果数据")
    company_name: str = Field("被检企业", description="企业名称")


@router.post("/report")
async def generate_compliance_report(
    req: ReportRequest,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """生成合规检查 HTML 报告"""
    from src.services.compliance_service import compliance_service
    result = await compliance_service.generate_report(
        evaluation_result=req.evaluation,
        company_name=req.company_name,
    )
    return result


@router.post("/compare")
async def compare_evaluations(
    current: dict[str, Any],
    previous: dict[str, Any],
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """对比两次合规检查结果"""
    from src.services.compliance_service import compliance_service
    result = await compliance_service.compare_evaluations(current, previous)
    return result
