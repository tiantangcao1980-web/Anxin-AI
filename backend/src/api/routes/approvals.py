# -*- coding: utf-8 -*-
"""审批流路由 — 支持审批链、审批模板、统计、批量审批"""

from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from loguru import logger

from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.models.approval import (
    Approval, ApprovalStatus, ApprovalType,
    ApprovalTemplate, ChainMode,
)

router = APIRouter()


# ========== Pydantic 模型 ==========

class ChainStepConfig(BaseModel):
    """审批链步骤配置"""
    step: int = Field(..., description="步骤序号，从 1 开始")
    approver_id: str = Field(..., description="审批人ID")
    approver_name: Optional[str] = Field(None, description="审批人姓名")
    status: str = Field(default="pending", description="步骤状态")
    comment: Optional[str] = Field(None, description="审批意见")
    resolved_at: Optional[datetime] = Field(None, description="审批时间")


class ChainConfig(BaseModel):
    """审批链配置"""
    mode: str = Field(default="sequential", description="sequential | parallel")
    steps: List[ChainStepConfig] = Field(default_factory=list)


class ApprovalCreate(BaseModel):
    """创建审批请求"""
    title: str = Field(..., max_length=500, description="审批标题")
    type: str = Field(default=ApprovalType.custom.value, description="审批类型")
    description: Optional[str] = Field(None, description="审批说明")
    approver_id: Optional[str] = Field(None, description="审批人ID（单人审批时使用）")
    resource_type: Optional[str] = Field(None, description="关联资源类型")
    resource_id: Optional[str] = Field(None, description="关联资源ID")
    priority: int = Field(default=1, ge=1, le=3, description="优先级")
    # 审批链支持
    approval_chain: Optional[ChainConfig] = Field(None, description="审批链配置")
    template_id: Optional[str] = Field(None, description="使用审批模板ID")


class ApprovalResponse(BaseModel):
    """审批响应"""
    id: str
    title: str
    type: str
    status: str
    description: Optional[str] = None
    requester_id: str
    approver_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    comment: Optional[str] = None
    risk_level: str = "low"
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    # 审批链字段
    approval_chain: Optional[dict] = None
    current_step: int = 0
    template_id: Optional[str] = None


class ApprovalListResponse(BaseModel):
    items: List[ApprovalResponse]
    total: int
    page: int
    page_size: int


class ApprovalActionRequest(BaseModel):
    comment: Optional[str] = Field(None, description="审批意见")


class ApprovalStatsResponse(BaseModel):
    total: int = 0
    pending: int = 0
    approved: int = 0
    rejected: int = 0
    withdrawn: int = 0
    # 增强统计字段
    pending_count: int = 0
    approved_today: int = 0
    rejected_today: int = 0
    avg_approval_time_hours: Optional[float] = None


# ---------- 审批模板 Pydantic ----------

class TemplateCreate(BaseModel):
    """创建审批模板"""
    name: str = Field(..., max_length=200, description="模板名称")
    description: Optional[str] = Field(None, description="模板说明")
    type: str = Field(default=ApprovalType.custom.value, description="适用审批类型")
    chain_config: Optional[dict] = Field(None, description="审批链配置JSON")


class TemplateUpdate(BaseModel):
    """更新审批模板"""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    type: Optional[str] = None
    chain_config: Optional[dict] = None
    enabled: Optional[bool] = None


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    type: str
    chain_config: Optional[dict] = None
    created_by: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class TemplateListResponse(BaseModel):
    items: List[TemplateResponse]
    total: int


# ---------- 批量审批 Pydantic ----------

class BatchApprovalRequest(BaseModel):
    """批量审批请求"""
    approval_ids: List[str] = Field(..., min_length=1, max_length=50, description="审批ID列表")
    action: str = Field(..., pattern="^(approve|reject)$", description="操作：approve / reject")
    comment: Optional[str] = Field(None, description="审批意见")


class BatchApprovalResultItem(BaseModel):
    approval_id: str
    success: bool
    message: str


class BatchApprovalResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: List[BatchApprovalResultItem]


# ========== 辅助函数 ==========

def _to_response(a: Approval) -> ApprovalResponse:
    return ApprovalResponse(
        id=str(a.id),
        title=a.title,
        type=a.approval_type,
        status=a.status,
        description=a.description,
        requester_id=str(a.requester_id),
        approver_id=str(a.approver_id) if a.approver_id else None,
        resource_type=a.resource_type,
        resource_id=a.resource_id,
        comment=a.resolution_note,
        risk_level=a.risk_level,
        created_at=a.created_at,
        updated_at=a.updated_at,
        resolved_at=a.resolved_at,
        approval_chain=a.approval_chain,
        current_step=a.current_step if a.current_step is not None else 0,
        template_id=str(a.template_id) if a.template_id else None,
    )


def _to_template_response(t: ApprovalTemplate) -> TemplateResponse:
    return TemplateResponse(
        id=str(t.id),
        name=t.name,
        description=t.description,
        type=t.type,
        chain_config=t.chain_config,
        created_by=str(t.created_by),
        enabled=t.enabled,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _advance_chain(approval: Approval, user_id: str, action: str, comment: Optional[str]) -> bool:
    """处理审批链推进逻辑。
    返回 True 表示整个审批已最终完成（通过或驳回），False 表示链尚未走完。
    """
    chain = approval.approval_chain
    if not chain or "steps" not in chain:
        # 没有审批链，直接按单人审批处理
        return True

    mode = chain.get("mode", "sequential")
    steps = chain["steps"]
    now_str = datetime.now(timezone.utc).isoformat()

    if mode == ChainMode.sequential.value:
        # 顺序审批：只处理 current_step 指向的步骤
        idx = approval.current_step
        if idx < len(steps):
            steps[idx]["status"] = "approved" if action == "approve" else "rejected"
            steps[idx]["comment"] = comment
            steps[idx]["resolved_at"] = now_str

            if action == "reject":
                # 任一步骤驳回，整条链驳回
                approval.approval_chain = chain
                return True

            # 推进到下一步
            approval.current_step = idx + 1
            if approval.current_step >= len(steps):
                # 最后一步通过，整条链通过
                approval.approval_chain = chain
                return True
            else:
                # 更新 approver_id 为下一步审批人
                next_step = steps[approval.current_step]
                approval.approver_id = next_step.get("approver_id")
                approval.approval_chain = chain
                return False
        return True

    elif mode == ChainMode.parallel.value:
        # 并行审批（会签）：当前用户在 steps 中找到自己的步骤并标记
        for step in steps:
            if step.get("approver_id") == user_id and step.get("status") == "pending":
                step["status"] = "approved" if action == "approve" else "rejected"
                step["comment"] = comment
                step["resolved_at"] = now_str
                break

        approval.approval_chain = chain

        if action == "reject":
            # 任一人驳回，整条链驳回
            return True

        # 检查是否所有步骤都已 approved
        all_done = all(s.get("status") == "approved" for s in steps)
        return all_done

    # 未知模式，兜底
    return True


# ========== 固定路径路由（放在参数路由之前） ==========

@router.get("/stats", response_model=UnifiedResponse)
async def get_approval_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取审批统计（增强版：含今日审批数、平均审批时长）"""
    try:
        total_r = await db.execute(select(func.count(Approval.id)))
        total = total_r.scalar() or 0

        stats = {}
        for s in ApprovalStatus:
            r = await db.execute(
                select(func.count(Approval.id)).where(Approval.status == s.value)
            )
            stats[s.value] = r.scalar() or 0

        # 今日统计
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        approved_today_r = await db.execute(
            select(func.count(Approval.id)).where(
                and_(
                    Approval.status == ApprovalStatus.approved.value,
                    Approval.resolved_at >= today_start,
                )
            )
        )
        approved_today = approved_today_r.scalar() or 0

        rejected_today_r = await db.execute(
            select(func.count(Approval.id)).where(
                and_(
                    Approval.status == ApprovalStatus.rejected.value,
                    Approval.resolved_at >= today_start,
                )
            )
        )
        rejected_today = rejected_today_r.scalar() or 0

        # 平均审批时长（仅已完成的审批）
        avg_time = None
        try:
            avg_r = await db.execute(
                select(
                    func.avg(
                        func.extract('epoch', Approval.resolved_at)
                        - func.extract('epoch', Approval.created_at)
                    )
                ).where(
                    and_(
                        Approval.resolved_at.isnot(None),
                        Approval.status.in_([
                            ApprovalStatus.approved.value,
                            ApprovalStatus.rejected.value,
                        ]),
                    )
                )
            )
            avg_seconds = avg_r.scalar()
            if avg_seconds is not None:
                avg_time = round(avg_seconds / 3600, 2)
        except Exception:
            # extract 函数在 SQLite 不支持，降级忽略
            avg_time = None

        data = ApprovalStatsResponse(
            total=total,
            pending=stats.get("pending", 0),
            approved=stats.get("approved", 0),
            rejected=stats.get("rejected", 0),
            withdrawn=stats.get("withdrawn", 0),
            pending_count=stats.get("pending", 0),
            approved_today=approved_today,
            rejected_today=rejected_today,
            avg_approval_time_hours=avg_time,
        )
        return UnifiedResponse.success(data=data)
    except Exception as e:
        logger.error(f"获取审批统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取审批统计失败")


# ========== 审批模板 CRUD ==========

@router.get("/templates", response_model=UnifiedResponse)
async def list_templates(
    type: Optional[str] = Query(None, description="按类型筛选"),
    enabled: Optional[bool] = Query(None, description="按启用状态筛选"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取审批模板列表"""
    try:
        conditions = []
        if type:
            conditions.append(ApprovalTemplate.type == type)
        if enabled is not None:
            conditions.append(ApprovalTemplate.enabled == enabled)

        where = and_(*conditions) if conditions else True

        count_r = await db.execute(
            select(func.count(ApprovalTemplate.id)).where(where)
        )
        total = count_r.scalar() or 0

        result = await db.execute(
            select(ApprovalTemplate).where(where)
            .order_by(ApprovalTemplate.created_at.desc())
        )
        items = result.scalars().all()

        data = TemplateListResponse(
            items=[_to_template_response(t) for t in items],
            total=total,
        )
        return UnifiedResponse.success(data=data)
    except Exception as e:
        logger.error(f"获取审批模板列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取审批模板列表失败")


@router.post("/templates", response_model=UnifiedResponse)
async def create_template(
    body: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """创建审批模板"""
    try:
        template = ApprovalTemplate(
            name=body.name,
            description=body.description,
            type=body.type,
            chain_config=body.chain_config,
            created_by=str(user.id),
        )
        db.add(template)
        await db.commit()
        await db.refresh(template)
        return UnifiedResponse.success(
            data=_to_template_response(template),
            message="审批模板已创建",
        )
    except Exception as e:
        logger.error(f"创建审批模板失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="创建审批模板失败")


@router.get("/templates/{template_id}", response_model=UnifiedResponse)
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取审批模板详情"""
    result = await db.execute(
        select(ApprovalTemplate).where(ApprovalTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        return UnifiedResponse.error(code=404, message="审批模板不存在")
    return UnifiedResponse.success(data=_to_template_response(template))


@router.put("/templates/{template_id}", response_model=UnifiedResponse)
async def update_template(
    template_id: str,
    body: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """更新审批模板"""
    try:
        result = await db.execute(
            select(ApprovalTemplate).where(ApprovalTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if not template:
            return UnifiedResponse.error(code=404, message="审批模板不存在")

        if body.name is not None:
            template.name = body.name
        if body.description is not None:
            template.description = body.description
        if body.type is not None:
            template.type = body.type
        if body.chain_config is not None:
            template.chain_config = body.chain_config
        if body.enabled is not None:
            template.enabled = body.enabled

        await db.commit()
        await db.refresh(template)
        return UnifiedResponse.success(
            data=_to_template_response(template),
            message="审批模板已更新",
        )
    except Exception as e:
        logger.error(f"更新审批模板失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="更新审批模板失败")


@router.delete("/templates/{template_id}", response_model=UnifiedResponse)
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """删除审批模板"""
    try:
        result = await db.execute(
            select(ApprovalTemplate).where(ApprovalTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if not template:
            return UnifiedResponse.error(code=404, message="审批模板不存在")

        await db.delete(template)
        await db.commit()
        return UnifiedResponse.success(message="审批模板已删除")
    except Exception as e:
        logger.error(f"删除审批模板失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="删除审批模板失败")


# ========== 批量审批 ==========

@router.post("/batch", response_model=UnifiedResponse)
async def batch_approval(
    body: BatchApprovalRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """批量审批（通过或驳回）"""
    results: List[BatchApprovalResultItem] = []
    succeeded = 0
    failed = 0

    for aid in body.approval_ids:
        try:
            result = await db.execute(
                select(Approval).where(Approval.id == aid)
            )
            approval = result.scalar_one_or_none()

            if not approval:
                results.append(BatchApprovalResultItem(
                    approval_id=aid, success=False, message="审批记录不存在"
                ))
                failed += 1
                continue

            if approval.status != ApprovalStatus.pending.value:
                results.append(BatchApprovalResultItem(
                    approval_id=aid, success=False, message="当前状态无法审批"
                ))
                failed += 1
                continue

            # 处理审批链逻辑
            chain_done = _advance_chain(approval, str(user.id), body.action, body.comment)

            if chain_done:
                if body.action == "approve":
                    approval.status = ApprovalStatus.approved.value
                else:
                    approval.status = ApprovalStatus.rejected.value
                approval.resolved_at = datetime.now(timezone.utc)

            approval.approver_id = str(user.id)
            if body.comment:
                approval.resolution_note = body.comment

            results.append(BatchApprovalResultItem(
                approval_id=aid, success=True,
                message="审批已通过" if body.action == "approve" else "审批已驳回"
            ))
            succeeded += 1

        except Exception as e:
            logger.error(f"批量审批 {aid} 失败: {e}")
            results.append(BatchApprovalResultItem(
                approval_id=aid, success=False, message=f"操作失败: {str(e)}"
            ))
            failed += 1

    try:
        await db.commit()
    except Exception as e:
        logger.error(f"批量审批提交失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="批量审批提交失败")

    data = BatchApprovalResponse(
        total=len(body.approval_ids),
        succeeded=succeeded,
        failed=failed,
        results=results,
    )
    return UnifiedResponse.success(data=data, message=f"批量审批完成：成功 {succeeded}，失败 {failed}")


# ========== CRUD 路由 ==========

@router.get("/", response_model=UnifiedResponse)
async def list_approvals(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    requester_id: Optional[str] = Query(None),
    approver_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取审批列表"""
    try:
        conditions = []
        if status:
            conditions.append(Approval.status == status)
        if type:
            conditions.append(Approval.approval_type == type)
        if requester_id:
            conditions.append(Approval.requester_id == requester_id)
        if approver_id:
            conditions.append(Approval.approver_id == approver_id)

        where = and_(*conditions) if conditions else True

        count_r = await db.execute(select(func.count(Approval.id)).where(where))
        total = count_r.scalar() or 0

        offset = (page - 1) * page_size
        result = await db.execute(
            select(Approval).where(where)
            .order_by(Approval.created_at.desc())
            .offset(offset).limit(page_size)
        )
        items = result.scalars().all()

        data = ApprovalListResponse(
            items=[_to_response(a) for a in items],
            total=total, page=page, page_size=page_size,
        )
        return UnifiedResponse.success(data=data)
    except Exception as e:
        logger.error(f"获取审批列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取审批列表失败")


@router.post("/", response_model=UnifiedResponse)
async def create_approval(
    body: ApprovalCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """创建审批（支持审批链和模板）"""
    try:
        now = datetime.now(timezone.utc)

        chain_data = None
        first_approver_id = body.approver_id

        # 如果指定了 template_id，从模板加载审批链配置
        if body.template_id:
            tpl_r = await db.execute(
                select(ApprovalTemplate).where(ApprovalTemplate.id == body.template_id)
            )
            template = tpl_r.scalar_one_or_none()
            if not template:
                return UnifiedResponse.error(code=404, message="审批模板不存在")
            if not template.enabled:
                return UnifiedResponse.error(code=400, message="审批模板已停用")
            chain_data = template.chain_config
        elif body.approval_chain:
            chain_data = body.approval_chain.model_dump()

        # 如果有审批链，第一个审批人取自链条第一步
        if chain_data and chain_data.get("steps"):
            first_step = chain_data["steps"][0]
            first_approver_id = first_step.get("approver_id", body.approver_id)

        approval = Approval(
            title=body.title,
            approval_type=body.type,
            description=body.description,
            requester_id=str(user.id),
            org_id=str(user.org_id) if hasattr(user, 'org_id') and user.org_id else None,
            approver_id=first_approver_id,
            resource_type=body.resource_type,
            resource_id=body.resource_id,
            risk_level="low",
            status=ApprovalStatus.pending.value,
            approval_chain=chain_data,
            current_step=0,
            template_id=body.template_id,
            created_at=now,
            updated_at=now,
        )
        db.add(approval)
        await db.commit()
        await db.refresh(approval)
        return UnifiedResponse.success(data=_to_response(approval), message="审批已创建")
    except Exception as e:
        logger.error(f"创建审批失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="创建审批失败")


@router.get("/{approval_id}", response_model=UnifiedResponse)
async def get_approval(
    approval_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取审批详情"""
    result = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        return UnifiedResponse.error(code=404, message="审批记录不存在")
    return UnifiedResponse.success(data=_to_response(approval))


@router.put("/{approval_id}/approve", response_model=UnifiedResponse)
async def approve_approval(
    approval_id: str,
    body: ApprovalActionRequest = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """通过审批（支持审批链自动推进）"""
    try:
        result = await db.execute(select(Approval).where(Approval.id == approval_id))
        approval = result.scalar_one_or_none()
        if not approval:
            return UnifiedResponse.error(code=404, message="审批记录不存在")
        if approval.status != ApprovalStatus.pending.value:
            return UnifiedResponse.error(code=400, message="当前状态无法审批")

        comment = body.comment if body else None
        chain_done = _advance_chain(approval, str(user.id), "approve", comment)

        if chain_done:
            approval.status = ApprovalStatus.approved.value
            approval.resolved_at = datetime.now(timezone.utc)

        approval.approver_id = str(user.id)
        if comment:
            approval.resolution_note = comment

        await db.commit()
        await db.refresh(approval)

        if chain_done:
            msg = "审批已通过"
        else:
            msg = f"当前步骤已通过，已推进至第 {approval.current_step + 1} 步"

        return UnifiedResponse.success(data=_to_response(approval), message=msg)
    except Exception as e:
        logger.error(f"审批通过失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="审批操作失败")


@router.put("/{approval_id}/reject", response_model=UnifiedResponse)
async def reject_approval(
    approval_id: str,
    body: ApprovalActionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """驳回审批"""
    try:
        result = await db.execute(select(Approval).where(Approval.id == approval_id))
        approval = result.scalar_one_or_none()
        if not approval:
            return UnifiedResponse.error(code=404, message="审批记录不存在")
        if approval.status != ApprovalStatus.pending.value:
            return UnifiedResponse.error(code=400, message="当前状态无法驳回")

        comment = body.comment if body else None
        _advance_chain(approval, str(user.id), "reject", comment)

        approval.status = ApprovalStatus.rejected.value
        approval.approver_id = str(user.id)
        approval.resolved_at = datetime.now(timezone.utc)
        approval.resolution_note = comment

        await db.commit()
        await db.refresh(approval)
        return UnifiedResponse.success(data=_to_response(approval), message="审批已驳回")
    except Exception as e:
        logger.error(f"驳回审批失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="驳回审批失败")


@router.put("/{approval_id}/withdraw", response_model=UnifiedResponse)
async def withdraw_approval(
    approval_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """撤回审批"""
    try:
        result = await db.execute(select(Approval).where(Approval.id == approval_id))
        approval = result.scalar_one_or_none()
        if not approval:
            return UnifiedResponse.error(code=404, message="审批记录不存在")
        if str(approval.requester_id) != str(user.id):
            return UnifiedResponse.error(code=403, message="仅发起人可撤回")
        if approval.status != ApprovalStatus.pending.value:
            return UnifiedResponse.error(code=400, message="当前状态无法撤回")

        approval.status = ApprovalStatus.withdrawn.value
        await db.commit()
        await db.refresh(approval)
        return UnifiedResponse.success(data=_to_response(approval), message="审批已撤回")
    except Exception as e:
        logger.error(f"撤回审批失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="撤回审批失败")
