"""
案件管理服务
"""

from datetime import datetime, date
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from loguru import logger

from src.models.case import Case, CaseEvent, CaseStatus, CasePriority, CaseType


def get_workforce():
    """延迟获取智能体团队，保留模块级入口方便测试替身注入。"""
    from src.agents.workforce import get_workforce as _get_workforce

    return _get_workforce()


class CaseService:
    """案件管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_case(
        self,
        title: str,
        case_type: str,
        description: Optional[str] = None,
        priority: str = "medium",
        org_id: str = None,
        created_by: str = None,
        parties: Optional[dict] = None,
        deadline: Optional[datetime] = None,
    ) -> Case:
        """创建案件"""
        if not org_id:
            raise ValueError("组织ID不能为空")
            
        case_number = f"CASE-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        
        case = Case(
            title=title,
            case_number=case_number,
            case_type=CaseType(case_type) if case_type in [e.value for e in CaseType] else CaseType.OTHER,
            description=description,
            priority=CasePriority(priority) if priority in [e.value for e in CasePriority] else CasePriority.MEDIUM,
            status=CaseStatus.PENDING,
            org_id=org_id,
            created_by=created_by,
            parties=parties,
            deadline=deadline,
        )
        
        self.db.add(case)
        await self.db.flush()
        
        # 添加创建事件
        await self.add_event(
            case_id=case.id,
            event_type="created",
            title="案件创建",
            description=f"案件 {title} ({case_number}) 已由用户 {created_by} 创建",
            created_by=created_by,
        )
        
        logger.info(f"案件创建成功: {case.case_number} [Org: {org_id}]")
        return case

    async def get_case(self, case_id: str, org_id: Optional[str] = None) -> Optional[Case]:
        """获取案件详情 (带组织隔离)"""
        try:
            UUID(str(case_id))
        except (TypeError, ValueError):
            logger.warning(f"忽略非法 case_id: {case_id}")
            return None

        query = select(Case).options(selectinload(Case.events), selectinload(Case.documents)).where(Case.id == case_id)
        if org_id:
            query = query.where(Case.org_id == org_id)
            
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_cases(
        self,
        org_id: Optional[str] = None,
        status: Optional[str] = None,
        case_type: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Case], int]:
        """获取案件列表"""
        query = select(Case)
        count_query = select(func.count(Case.id))
        
        conditions = []
        if org_id:
            conditions.append(Case.org_id == org_id)
        # 模型使用 ValueEnum —— DB 写入的是 enum.value（小写短名），
        # 过滤时须匹配 value，而不是 .name。直接把 enum 实例交给 SQLAlchemy
        # 由方言负责序列化成 value，避免手工 upper()/lower() 误判。
        if status:
            try:
                conditions.append(Case.status == CaseStatus(status))
            except ValueError:
                conditions.append(Case.status == status.lower())
        if case_type:
            try:
                conditions.append(Case.case_type == CaseType(case_type))
            except ValueError:
                conditions.append(Case.case_type == case_type.lower())
        if priority:
            try:
                conditions.append(Case.priority == CasePriority(priority))
            except ValueError:
                conditions.append(Case.priority == priority.lower())
        if assignee_id:
            conditions.append(Case.assignee_id == assignee_id)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # 总数
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 分页
        query = query.order_by(Case.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        cases = list(result.scalars().all())
        
        return cases, total
    
    async def update_case(
        self,
        case_id: str,
        **kwargs
    ) -> Optional[Case]:
        """更新案件"""
        case = await self.get_case(case_id)
        if not case:
            return None
        
        for key, value in kwargs.items():
            if value is not None and hasattr(case, key):
                if key == "status":
                    value = CaseStatus(value)
                elif key == "priority":
                    value = CasePriority(value)
                elif key == "case_type":
                    value = CaseType(value)
                setattr(case, key, value)
        
        case.updated_at = datetime.now()
        await self.db.flush()
        
        return case
    
    async def delete_case(self, case_id: str) -> bool:
        """删除案件"""
        case = await self.get_case(case_id)
        if not case:
            return False
        
        await self.db.delete(case)
        await self.db.flush()
        return True
    
    async def get_timeline(self, case_id: str) -> List[CaseEvent]:
        """获取案件时间线"""
        result = await self.db.execute(
            select(CaseEvent)
            .where(CaseEvent.case_id == case_id)
            .order_by(CaseEvent.event_time.desc())
        )
        return list(result.scalars().all())
    
    async def add_event(
        self,
        case_id: str,
        event_type: str,
        title: str,
        description: Optional[str] = None,
        event_data: Optional[dict] = None,
        created_by: Optional[str] = None,
    ) -> CaseEvent:
        """添加案件事件"""
        event = CaseEvent(
            case_id=case_id,
            event_type=event_type,
            title=title,
            description=description,
            event_data=event_data,
            event_time=datetime.now(),
            created_by=created_by,
        )
        self.db.add(event)
        await self.db.flush()
        return event
    
    async def analyze_case(self, case_id: str, user_id: str = "00000000-0000-0000-0000-000000000001") -> dict:
        """AI分析案件"""
        case = await self.get_case(case_id)
        if not case:
            raise ValueError("案件不存在")
        
        workforce = get_workforce()
        
        # 获取关联文档内容
        doc_summaries = []
        if case.documents:
            for doc in case.documents[:5]:  # 限制文档数量
                doc_summaries.append(f"- 文档名称: {doc.name}, 类型: {doc.doc_type}, 摘要: {doc.ai_summary or '暂无'}")
        
        task_description = f"""
请作为专业法务专家团队，分析以下案件并给出深度意见：

【案件基本信息】
- 案号：{case.case_number}
- 名称：{case.title}
- 类型：{case.case_type.value}
- 优先级：{case.priority.value}
- 描述：{case.description or '无'}

【关联证据/文档】
{chr(10).join(doc_summaries) if doc_summaries else '暂无关联文档'}

【分析要求】
1. 案件性质与法律关系深度剖析
2. 核心法律风险点识别（评分 0-100）
3. 类似判例倾向分析（基于知识库）
4. 针对性的抗辩或处理策略
5. 预计时间线与关键节点建议
"""
        
        result = await workforce.process_task(
            task_description=task_description,
            task_type="case_analysis",
            context={
                "case_id": case_id,
                "org_id": case.org_id,
                "case_type": case.case_type.value,
            }
        )
        
        # 保存分析结果
        final_result = result.get("final_result", {})
        case.ai_analysis = final_result
        await self.db.flush()
        
        # 添加分析事件
        await self.add_event(
            case_id=case_id,
            event_type="ai_analysis",
            title="AI 智能分析完成",
            description="系统已生成多智能体协作分析报告",
            event_data=final_result,
            created_by=user_id
        )
        
        return result
    
    async def link_document(
        self,
        case_id: str,
        document_id: str,
        created_by: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> bool:
        """关联文档到案件"""
        from src.models.document import Document
        
        case = await self.get_case(case_id, org_id=org_id)
        if not case:
            return False
        
        # 获取文档
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                *( [Document.org_id == org_id] if org_id else [] ),
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return False
        
        # 设置关联
        doc.case_id = case_id
        await self.db.flush()
        
        # 添加事件
        await self.add_event(
            case_id=case_id,
            event_type="document_linked",
            title="关联文档",
            description=f"关联文档: {doc.name}",
            event_data={"document_id": document_id, "document_name": doc.name},
            created_by=created_by,
        )
        
        logger.info(f"文档 {document_id} 已关联到案件 {case_id}")
        return True
    
    async def unlink_document(
        self,
        case_id: str,
        document_id: str,
        created_by: Optional[str] = None,
    ) -> bool:
        """取消文档关联"""
        from src.models.document import Document
        
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.case_id == case_id
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return False
        
        doc_name = doc.name
        doc.case_id = None
        await self.db.flush()
        
        # 添加事件
        await self.add_event(
            case_id=case_id,
            event_type="document_unlinked",
            title="取消文档关联",
            description=f"取消关联文档: {doc_name}",
            event_data={"document_id": document_id},
            created_by=created_by,
        )
        
        return True
    
    async def get_case_documents(
        self,
        case_id: str,
        org_id: Optional[str] = None,
    ) -> list:
        """获取案件关联的文档列表"""
        from src.models.document import Document
        conditions = [Document.case_id == case_id]
        if org_id:
            conditions.append(Document.org_id == org_id)
        result = await self.db.execute(
            select(Document)
            .where(and_(*conditions))
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_case_statistics(
        self,
        org_id: Optional[str] = None,
    ) -> dict:
        """获取案件统计信息"""
        from sqlalchemy import cast, String
        # 按状态统计 — 数据库列是 VARCHAR，存储大写枚举名
        status_stats = {}
        for status in CaseStatus:
            query = select(func.count(Case.id)).where(
                cast(Case.status, String) == status.name
            )
            if org_id:
                query = query.where(Case.org_id == org_id)
            result = await self.db.execute(query)
            status_stats[status.value] = result.scalar() or 0

        # 按类型统计
        type_stats = {}
        for case_type in CaseType:
            query = select(func.count(Case.id)).where(
                cast(Case.case_type, String) == case_type.name
            )
            if org_id:
                query = query.where(Case.org_id == org_id)
            result = await self.db.execute(query)
            type_stats[case_type.value] = result.scalar() or 0

        # 按优先级统计
        priority_stats = {}
        for priority in CasePriority:
            query = select(func.count(Case.id)).where(
                cast(Case.priority, String) == priority.name
            )
            if org_id:
                query = query.where(Case.org_id == org_id)
            result = await self.db.execute(query)
            priority_stats[priority.value] = result.scalar() or 0
        
        # 按负责人统计 (Workload)
        assignee_stats = {}
        # Need to import User model inside method to avoid circular import if any
        from src.models.user import User
        
        assignee_query = (
            select(Case.assignee_id, User.name, func.count(Case.id))
            .outerjoin(User, Case.assignee_id == User.id)
            .where(Case.org_id == org_id)
            .group_by(Case.assignee_id, User.name)
        )
        assignee_result = await self.db.execute(assignee_query)
        
        workload_data = []
        for assignee_id, user_name, count in assignee_result.all():
            if assignee_id:
                workload_data.append({
                    "id": str(assignee_id),
                    "name": user_name or "Unknown",
                    "count": count
                })
            else:
                workload_data.append({
                    "id": "unassigned",
                    "name": "未分配",
                    "count": count
                })
        
        # 总数
        total_query = select(func.count(Case.id))
        if org_id:
            total_query = total_query.where(Case.org_id == org_id)
        total_result = await self.db.execute(total_query)
        total = total_result.scalar() or 0
        
        return {
            "total": total,
            "by_status": status_stats,
            "by_type": type_stats,
            "by_priority": priority_stats,
            "workload": workload_data,
        }

    async def get_recent_events(self, org_id: str, limit: int = 10) -> List[tuple[CaseEvent, Case]]:
        """获取最近的案件事件 (跨案件)"""
        query = (
            select(CaseEvent, Case)
            .join(Case, CaseEvent.case_id == Case.id)
            .where(Case.org_id == org_id)
            .order_by(CaseEvent.event_time.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.all())

    async def get_compliance_score(self, org_id: str) -> dict:
        """计算合规健康分"""
        # 基础分
        base_score = 100
        
        from sqlalchemy import cast, String
        # 1. 扣分项：高风险案件
        high_risk_query = select(func.count(Case.id)).where(
            Case.org_id == org_id,
            Case.risk_score >= 80,
            cast(Case.status, String) != CaseStatus.COMPLETED.name
        )
        high_risk_count = (await self.db.execute(high_risk_query)).scalar() or 0
        base_score -= (high_risk_count * 5)

        # 2. 扣分项：逾期案件
        overdue_query = select(func.count(Case.id)).where(
            Case.org_id == org_id,
            Case.deadline < datetime.now(),
            cast(Case.status, String) != CaseStatus.COMPLETED.name
        )
        overdue_count = (await self.db.execute(overdue_query)).scalar() or 0
        base_score -= (overdue_count * 3)

        # 3. 扣分项：未结案件过多
        pending_query = select(func.count(Case.id)).where(
            Case.org_id == org_id,
            cast(Case.status, String) != CaseStatus.COMPLETED.name
        )
        pending_count = (await self.db.execute(pending_query)).scalar() or 0
        if pending_count > 50:
            base_score -= 5
            
        # 限制分数范围
        final_score = max(0, min(100, base_score))
        
        # 计算细项指标 (Mock for now, can be real later)
        metrics = {
            "doc_compliance": "95%",
            "risk_control": f"{max(0, 100 - high_risk_count * 10)}%",
            "process_norm": "88%"
        }
        
        return {
            "score": final_score,
            "metrics": metrics,
            "trend": 5 # Mock trend
        }

    async def get_alerts(self, org_id: str) -> List[dict]:
        """获取系统预警 (截止日期、高风险等)"""
        alerts = []
        
        # 1. 即将到期的案件 (7天内)
        from datetime import timedelta
        deadline_threshold = datetime.now() + timedelta(days=7)
        
        from sqlalchemy import cast, String as SqlString
        deadline_query = (
            select(Case)
            .where(
                Case.org_id == org_id,
                Case.deadline.isnot(None),
                Case.deadline <= deadline_threshold,
                cast(Case.status, SqlString) != CaseStatus.COMPLETED.name,
                cast(Case.status, SqlString) != CaseStatus.CLOSED.name
            )
            .order_by(Case.deadline)
            .limit(5)
        )
        deadline_cases = (await self.db.execute(deadline_query)).scalars().all()
        
        for case in deadline_cases:
            try:
                dl = case.deadline if isinstance(case.deadline, datetime) else datetime.combine(case.deadline, datetime.min.time())
                # 统一为 naive datetime 比较
                dl_naive = dl.replace(tzinfo=None) if dl.tzinfo else dl
                days_left = (dl_naive.date() - datetime.now().date()).days
            except Exception:
                days_left = 0
            alerts.append({
                "id": f"deadline-{case.id}",
                "type": "urgent" if days_left <= 3 else "warning",
                "title": "案件即将到期",
                "content": f"案件 {case.case_number} ({case.title}) 将于 {dl_naive.strftime('%Y年%m月%d日')} 截止",
                "time": f"{days_left}天后" if days_left > 0 else "今天",
                "created_at": datetime.now() # Mock for sorting
            })
            
        # 2. 高风险案件
        risk_query = (
            select(Case)
            .where(
                Case.org_id == org_id,
                Case.risk_score >= 0.8,
                cast(Case.status, SqlString) != CaseStatus.COMPLETED.name
            )
            .limit(5)
        )
        risk_cases = (await self.db.execute(risk_query)).scalars().all()
        
        for case in risk_cases:
            alerts.append({
                "id": f"risk-{case.id}",
                "type": "urgent",
                "title": "高风险案件提醒",
                "content": f"案件 {case.title} 风险评分高达 {int(case.risk_score * 100)}分",
                "time": "需立即关注",
                "created_at": datetime.now()
            })
            
        return alerts
