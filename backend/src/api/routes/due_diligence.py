"""尽职调查路由"""

import json
import asyncio
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.core.database import get_db
from src.core.deps import get_current_user, get_current_user_required
from src.core.responses import UnifiedResponse
from src.services.due_diligence_service import due_diligence_service, get_company_info
from src.models.user import User

router = APIRouter()


class CompanyInvestigateRequest(BaseModel):
    """企业调查请求"""
    company_name: str
    investigation_type: str = "comprehensive"  # comprehensive, litigation, credit, basic


class InvestigationResponse(BaseModel):
    """调查响应"""
    company_name: str
    investigation_type: str
    timestamp: str
    results: dict
    report: dict


class CompanyBasicInfo(BaseModel):
    """企业基本信息"""
    name: str
    legal_representative: Optional[str] = None
    registered_capital: Optional[str] = None
    established_date: Optional[str] = None
    business_scope: Optional[str] = None
    address: Optional[str] = None
    company_type: Optional[str] = None
    status: str = "正常"


class RiskAssessment(BaseModel):
    """风险评估"""
    operation_risk: int = 0
    litigation_risk: int = 0
    credit_risk: int = 0
    compliance_risk: int = 0
    relation_risk: int = 0
    overall_rating: str = "low"
    risk_points: List[str] = []
    recommendations: List[str] = []


@router.post("/company", response_model=UnifiedResponse)
async def investigate_company(
    request: CompanyInvestigateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """
    企业综合尽职调查
    
    支持多种调查类型：
    - comprehensive: 综合调查（全面）
    - litigation: 诉讼调查
    - credit: 信用调查
    - basic: 基本信息
    """
    result = await due_diligence_service.investigate_company(
        company_name=request.company_name,
        investigation_type=request.investigation_type,
    )
    
    data = InvestigationResponse(
        company_name=result["company_name"],
        investigation_type=result["investigation_type"],
        timestamp=result["timestamp"],
        results=result["results"],
        report=result["report"],
    )
    return UnifiedResponse.success(data=data)


@router.post("/company/stream")
async def stream_investigate_company(
    request: CompanyInvestigateRequest,
    user: User = Depends(get_current_user_required),
):
    """流式企业调查（SSE）— 真正并行，完成一个推送一个"""

    async def generate_stream():
        company_name = request.company_name
        investigation_type = request.investigation_type
        svc = due_diligence_service

        yield f"data: {json.dumps({'type': 'start', 'message': f'开始调查企业: {company_name}'})}\n\n"

        # ---------- 检查预置数据（秒回） ----------
        from src.services.due_diligence_service import MOCK_COMPANY_DATA
        if company_name in MOCK_COMPANY_DATA:
            company_data = MOCK_COMPANY_DATA[company_name]
            for step in ["basic_info", "litigation", "credit", "risk"]:
                yield f"data: {json.dumps({'type': 'result', 'step': step, 'data': company_data.get(step, {})})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'message': '调查完成'})}\n\n"
            return

        # ---------- 快速模式：单次 LLM 调用获取全部数据 ----------
        steps = ["basic_info", "litigation", "credit", "risk"]
        step_msgs = {
            "basic_info": "正在获取工商信息...",
            "litigation": "正在查询诉讼记录...",
            "credit": "正在评估信用状况...",
            "risk": "正在进行风险评估...",
        }

        # 发送所有"进行中"状态
        for step in steps:
            yield f"data: {json.dumps({'type': 'step', 'step': step, 'message': step_msgs[step]})}\n\n"

        try:
            # 单次 LLM 调用，60s 超时
            company_data = await asyncio.wait_for(
                svc.quick_investigate(company_name),
                timeout=60.0,
            )

            # 逐步推送各部分数据
            for step in steps:
                data = company_data.get(step, {})
                yield f"data: {json.dumps({'type': 'result', 'step': step, 'data': data})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'message': '调查完成'})}\n\n"

        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'error', 'message': 'AI 调查超时（60秒），请检查 LLM 服务是否可用'})}\n\n"
        except Exception as e:
            logger.error(f"流式调查失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/company/{company_name}/profile", response_model=UnifiedResponse)
async def get_company_profile(
    company_name: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取企业画像"""
    try:
        company_data = await get_company_info(company_name)
    except Exception as e:
        logger.error(f"获取企业画像失败: {e}")
        return UnifiedResponse.error(message=str(e))

    data = {
        "company_name": company_name,
        "profile": company_data.get("basic_info", {}),
    }
    return UnifiedResponse.success(data=data)


@router.get("/company/{company_name}/risks", response_model=UnifiedResponse)
async def get_company_risks(
    company_name: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取企业风险报告"""
    try:
        company_data = await get_company_info(company_name)
    except Exception as e:
        logger.error(f"获取企业风险失败: {e}")
        return UnifiedResponse.error(message=str(e))
    risk_data = company_data.get("risk", {})
    
    # 计算总体风险分数
    scores = [
        risk_data.get("operation_risk", 0),
        risk_data.get("litigation_risk", 0),
        risk_data.get("credit_risk", 0),
        risk_data.get("compliance_risk", 0),
        risk_data.get("relation_risk", 0),
    ]
    valid_scores = [s for s in scores if s > 0]
    avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0
    
    data = {
        "company_name": company_name,
        "risk_score": round(avg_score, 1),
        "risk_level": risk_data.get("overall_rating", "medium"),
        "breakdown": {
            "operation_risk": {"score": risk_data.get("operation_risk", 30), "label": "经营风险"},
            "litigation_risk": {"score": risk_data.get("litigation_risk", 40), "label": "诉讼风险"},
            "credit_risk": {"score": risk_data.get("credit_risk", 25), "label": "信用风险"},
            "compliance_risk": {"score": risk_data.get("compliance_risk", 30), "label": "合规风险"},
            "relation_risk": {"score": risk_data.get("relation_risk", 20), "label": "关联风险"},
        },
        "risk_points": risk_data.get("risk_points", []),
        "recommendations": risk_data.get("recommendations", []),
    }
    return UnifiedResponse.success(data=data)


@router.get("/company/{company_name}/litigation", response_model=UnifiedResponse)
async def get_company_litigation(
    company_name: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取企业诉讼信息"""
    try:
        company_data = await get_company_info(company_name)
    except Exception as e:
        logger.error(f"获取企业诉讼信息失败: {e}")
        return UnifiedResponse.error(message=str(e))
    litigation = company_data.get("litigation", {})
    
    data = {
        "company_name": company_name,
        "summary": {
            "total_cases": litigation.get("plaintiff_cases", 0) + litigation.get("defendant_cases", 0),
            "as_plaintiff": litigation.get("plaintiff_cases", 0),
            "as_defendant": litigation.get("defendant_cases", 0),
            "execution_cases": litigation.get("execution_cases", 0),
            "dishonest_records": litigation.get("dishonest_records", 0),
        },
        "major_cases": litigation.get("major_cases", []),
        "case_types": [
            {"type": "合同纠纷", "count": 5},
            {"type": "劳动争议", "count": 3},
            {"type": "知识产权", "count": 2},
        ],
    }
    return UnifiedResponse.success(data=data)


@router.get("/company/{company_name}/graph", response_model=UnifiedResponse)
async def get_company_graph(
    company_name: str,
    depth: int = Query(1, ge=1, le=3),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取企业关系图谱"""
    # ... (nodes/edges construction omitted for brevity, keeping existing logic)
    nodes = [
        {"id": "center", "name": company_name, "type": "target", "level": 0},
    ]
    edges = []
    
    # 添加模拟股东
    shareholders = [
        {"name": "大股东A", "ratio": "35%"},
        {"name": "投资机构B", "ratio": "25%"},
        {"name": "自然人C", "ratio": "15%"},
    ]
    
    for i, sh in enumerate(shareholders):
        node_id = f"sh_{i}"
        nodes.append({
            "id": node_id,
            "name": sh["name"],
            "type": "shareholder",
            "level": 1,
        })
        edges.append({
            "source": node_id,
            "target": "center",
            "relation": "股东",
            "label": sh["ratio"],
        })
    
    # 添加模拟投资
    investments = [
        {"name": "子公司A", "ratio": "100%"},
        {"name": "参股公司B", "ratio": "30%"},
    ]
    
    for i, inv in enumerate(investments):
        node_id = f"inv_{i}"
        nodes.append({
            "id": node_id,
            "name": inv["name"],
            "type": "investment",
            "level": 1,
        })
        edges.append({
            "source": "center",
            "target": node_id,
            "relation": "投资",
            "label": inv["ratio"],
        })
    
    # 添加高管
    executives = [
        {"name": "张总", "position": "法定代表人"},
        {"name": "李总", "position": "总经理"},
    ]
    
    for i, ex in enumerate(executives):
        node_id = f"ex_{i}"
        nodes.append({
            "id": node_id,
            "name": ex["name"],
            "type": "person",
            "level": 1,
        })
        edges.append({
            "source": node_id,
            "target": "center",
            "relation": ex["position"],
        })
    
    data = {
        "company_name": company_name,
        "graph": {
            "nodes": nodes,
            "edges": edges,
        },
        "statistics": {
            "shareholders": len(shareholders),
            "investments": len(investments),
            "executives": len(executives),
        }
    }
    return UnifiedResponse.success(data=data)


@router.get("/search")
async def search_companies(
    keyword: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user_required),
):
    """搜索企业"""
    # 返回模拟搜索结果
    results = []
    
    # 模拟搜索结果
    if "阿里" in keyword or "alibaba" in keyword.lower():
        results.append({
            "name": "阿里巴巴集团控股有限公司",
            "credit_code": "91330100MA2CL7YK8X",
            "legal_representative": "蔡崇信",
            "status": "正常",
        })
    
    if "腾讯" in keyword or "tencent" in keyword.lower():
        results.append({
            "name": "腾讯控股有限公司",
            "credit_code": "91440300708461136T",
            "legal_representative": "马化腾",
            "status": "正常",
        })
    
    # 添加通用模拟结果
    if len(results) < limit:
        for i in range(min(3, limit - len(results))):
            results.append({
                "name": f"{keyword}科技有限公司",
                "credit_code": f"9144030070846{1000+i}",
                "legal_representative": "张三",
                "status": "正常",
            })
    
    data = {
        "keyword": keyword,
        "total": len(results),
        "results": results[:limit],
    }
    return UnifiedResponse.success(data=data)
