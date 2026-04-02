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


# ===== 多 Agent 协同调查 (阶段二) =====

class OrchestratedInvestigateRequest(BaseModel):
    """增强版协同调查请求"""
    company_name: str
    investigation_type: str = "comprehensive"
    enable_deep_research: bool = True
    enable_forum: bool = True
    enable_report: bool = False
    report_template: str = "comprehensive"


@router.post("/company/orchestrated-stream")
async def orchestrated_stream_investigate(
    request: CompanyInvestigateRequest,
    user: User = Depends(get_current_user_required),
):
    """多 Agent 协同流式调查 — 支持增强 SSE 事件（v1 兼容）"""

    async def generate_stream():
        try:
            from src.services.investigation_orchestrator import investigation_orchestrator
            async for event in investigation_orchestrator.orchestrate_investigation(
                company_name=request.company_name,
                investigation_type=request.investigation_type,
                user_id=str(user.id) if user else None,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"协同调查失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/company/deep-investigate")
async def deep_investigate_stream(
    request: OrchestratedInvestigateRequest,
    user: User = Depends(get_current_user_required),
):
    """
    增强版深度调查（v2）— 六阶段管线

    支持：
    - 深度研究（迭代式搜索-反思-优化循环）
    - 多专家论坛辩论
    - 模板化报告生成
    """

    async def generate_stream():
        try:
            from src.services.investigation_orchestrator import investigation_orchestrator
            async for event in investigation_orchestrator.orchestrate_investigation_v2(
                company_name=request.company_name,
                investigation_type=request.investigation_type,
                user_id=str(user.id) if user else None,
                enable_deep_research=request.enable_deep_research,
                enable_forum=request.enable_forum,
                enable_report=request.enable_report,
                report_template=request.report_template,
            ):
                # 过滤内部事件
                if not event.get("type", "").startswith("_"):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"深度调查失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ===== 调查历史 =====

@router.get("/investigations")
async def list_investigations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取调查历史列表"""
    try:
        from sqlalchemy import select, desc
        from src.models.investigation import Investigation
        stmt = (
            select(Investigation)
            .where(Investigation.user_id == str(user.id))
            .order_by(desc(Investigation.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        investigations = result.scalars().all()
        return UnifiedResponse.success(data=[inv.to_dict() for inv in investigations])
    except Exception as e:
        logger.debug(f"查询调查历史失败（表可能未创建）: {e}")
        return UnifiedResponse.success(data=[])


@router.get("/investigations/{investigation_id}")
async def get_investigation(
    investigation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取单条调查详情"""
    try:
        from src.models.investigation import Investigation
        result = await db.get(Investigation, investigation_id)
        if result:
            return UnifiedResponse.success(data=result.to_dict())
    except Exception as e:
        logger.debug(f"获取调查详情失败: {e}")
    return UnifiedResponse.error(message="调查记录不存在")


# ===== 调查报告 (阶段四) =====

class ReportRequest(BaseModel):
    """报告生成请求"""
    format: str = "html"  # html / json
    template_id: str = "comprehensive"  # comprehensive / risk_focus / executive / litigation / credit / compliance
    use_llm: bool = False  # 是否使用 LLM 增强章节内容


@router.post("/investigations/{investigation_id}/report")
async def generate_investigation_report(
    investigation_id: str,
    request: ReportRequest = ReportRequest(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """生成调查报告"""
    try:
        from src.services.report_engine import report_engine
        from src.models.investigation import Investigation

        inv = await db.get(Investigation, investigation_id)
        if not inv:
            return UnifiedResponse.error(message="调查记录不存在")

        investigation_data = {
            "company_name": inv.company_name,
            "basic_info": inv.basic_info or {},
            "risk": inv.risk or {},
            "litigation": inv.litigation or {},
            "credit": inv.credit or {},
            "consensus": inv.consensus_result or {},
            "conflicts": inv.conflicts or [],
        }

        report = await report_engine.generate_report(
            investigation_data, request.format, request.template_id, request.use_llm
        )
        return UnifiedResponse.success(data=report)
    except Exception as e:
        logger.error(f"报告生成失败: {e}")
        return UnifiedResponse.error(message=str(e))


@router.post("/report/generate")
async def generate_report_direct(
    request: CompanyInvestigateRequest,
    user: User = Depends(get_current_user_required),
):
    """直接根据企业名生成报告（无需先保存调查）"""
    try:
        from src.services.report_engine import report_engine

        company_data = await get_company_info(request.company_name)
        investigation_data = {
            "company_name": request.company_name,
            "basic_info": company_data.get("basic_info", {}),
            "risk": company_data.get("risk", {}),
            "litigation": company_data.get("litigation", {}),
            "credit": company_data.get("credit", {}),
        }
        report = await report_engine.generate_report(investigation_data, "html")
        return UnifiedResponse.success(data=report)
    except Exception as e:
        logger.error(f"报告生成失败: {e}")
        return UnifiedResponse.error(message=str(e))


@router.get("/report/templates")
async def list_report_templates(
    user: User = Depends(get_current_user_required),
):
    """列出所有可用报告模板"""
    try:
        from src.services.report_engine import report_engine
        templates = report_engine.list_templates()
        return UnifiedResponse.success(data=templates)
    except Exception as e:
        return UnifiedResponse.error(message=str(e))


@router.post("/report/generate/stream")
async def generate_report_stream(
    request: ReportRequest,
    company_name: str = Query(..., min_length=1),
    user: User = Depends(get_current_user_required),
):
    """流式报告生成（逐章返回进度）"""

    async def generate_stream():
        try:
            from src.services.report_engine import report_engine

            company_data = await get_company_info(company_name)
            investigation_data = {
                "company_name": company_name,
                "basic_info": company_data.get("basic_info", {}),
                "risk": company_data.get("risk", {}),
                "litigation": company_data.get("litigation", {}),
                "credit": company_data.get("credit", {}),
            }
            async for event in report_engine.generate_report_stream(
                investigation_data, request.template_id, request.use_llm
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ===== 风险场景推演 (阶段四) =====

class SimulationRequest(BaseModel):
    """场景推演请求"""
    scenario_id: str
    company_name: str
    current_risk: Optional[dict] = None


@router.post("/simulate")
async def simulate_scenario(
    request: SimulationRequest,
    user: User = Depends(get_current_user_required),
):
    """执行风险场景推演"""
    try:
        from src.services.scenario_simulation import scenario_simulation_service
        result = await scenario_simulation_service.simulate_scenario(
            scenario_id=request.scenario_id,
            company_name=request.company_name,
            current_risk=request.current_risk,
        )
        return UnifiedResponse.success(data=result)
    except Exception as e:
        logger.error(f"场景推演失败: {e}")
        return UnifiedResponse.error(message=str(e))


@router.post("/simulate/stream")
async def simulate_scenario_stream(
    request: SimulationRequest,
    user: User = Depends(get_current_user_required),
):
    """流式风险场景推演"""

    async def generate_stream():
        try:
            from src.services.scenario_simulation import scenario_simulation_service
            async for event in scenario_simulation_service.simulate_stream(
                scenario_id=request.scenario_id,
                company_name=request.company_name,
                current_risk=request.current_risk,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/simulate/scenarios")
async def list_simulation_scenarios(
    user: User = Depends(get_current_user_required),
):
    """列出可用的推演场景"""
    try:
        from src.services.scenario_simulation import scenario_simulation_service
        scenarios = scenario_simulation_service.list_scenarios()
        return UnifiedResponse.success(data=scenarios)
    except Exception as e:
        return UnifiedResponse.error(message=str(e))


# ===== 时间序列快照 =====

@router.get("/snapshots/{company_name}")
async def get_company_snapshots(
    company_name: str,
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user_required),
):
    """获取企业历史快照列表"""
    try:
        from src.services.investigation_data_store import investigation_data_store
        snapshots = await investigation_data_store.get_snapshots(
            company_name=company_name,
            limit=limit,
            user_id=str(user.id),
        )
        return UnifiedResponse.success(data=snapshots)
    except Exception as e:
        logger.debug(f"查询快照失败: {e}")
        return UnifiedResponse.success(data=[])


@router.get("/snapshots/{company_name}/trend")
async def get_risk_trend(
    company_name: str,
    limit: int = Query(30, ge=1, le=100),
    user: User = Depends(get_current_user_required),
):
    """获取企业风险趋势数据（用于折线图）"""
    try:
        from src.services.investigation_data_store import investigation_data_store
        trend = await investigation_data_store.get_risk_trend(
            company_name=company_name,
            limit=limit,
        )
        return UnifiedResponse.success(data=trend)
    except Exception as e:
        logger.debug(f"查询风险趋势失败: {e}")
        return UnifiedResponse.success(data=[])


@router.get("/snapshots/compare/{snapshot_a}/{snapshot_b}")
async def compare_snapshots(
    snapshot_a: str,
    snapshot_b: str,
    user: User = Depends(get_current_user_required),
):
    """对比两个快照的差异"""
    try:
        from src.services.investigation_data_store import investigation_data_store
        result = await investigation_data_store.compare_snapshots(snapshot_a, snapshot_b)
        return UnifiedResponse.success(data=result)
    except Exception as e:
        return UnifiedResponse.error(message=str(e))


# ===== 缓存管理 =====

@router.get("/cache/{company_name}")
async def get_cache_status(
    company_name: str,
    user: User = Depends(get_current_user_required),
):
    """获取某企业各维度的缓存状态"""
    try:
        from src.services.investigation_data_store import investigation_data_store
        dimensions = await investigation_data_store.get_cached_dimensions(company_name)
        return UnifiedResponse.success(data=dimensions)
    except Exception as e:
        logger.debug(f"查询缓存状态失败: {e}")
        return UnifiedResponse.success(data={})


@router.delete("/cache/{company_name}")
async def invalidate_cache(
    company_name: str,
    data_source: Optional[str] = Query(None, description="指定失效的数据源，不传则全部失效"),
    user: User = Depends(get_current_user_required),
):
    """使某企业的缓存失效（强制下次调查重新抓取）"""
    try:
        from src.services.investigation_data_store import investigation_data_store
        count = await investigation_data_store.invalidate_cache(company_name, data_source)
        return UnifiedResponse.success(data={"invalidated": count})
    except Exception as e:
        return UnifiedResponse.error(message=str(e))


# ===== 用户偏好 =====

@router.get("/preferences")
async def get_user_preferences(
    user: User = Depends(get_current_user_required),
):
    """获取当前用户的调查偏好"""
    try:
        from src.services.investigation_data_store import investigation_data_store
        pref = await investigation_data_store.get_user_preference(str(user.id))
        return UnifiedResponse.success(data=pref)
    except Exception as e:
        logger.debug(f"查询用户偏好失败: {e}")
        return UnifiedResponse.success(data=None)


@router.get("/preferences/recommendations")
async def get_smart_recommendations(
    company_name: Optional[str] = Query(None),
    user: User = Depends(get_current_user_required),
):
    """获取基于用户偏好的智能推荐"""
    try:
        from src.services.investigation_data_store import investigation_data_store
        rec = await investigation_data_store.get_smart_recommendations(
            user_id=str(user.id),
            company_name=company_name,
        )
        return UnifiedResponse.success(data=rec)
    except Exception as e:
        return UnifiedResponse.success(data={})
