"""
审计日志服务
记录和查询用户操作审计日志
"""

import functools
from datetime import datetime, timedelta
from typing import Optional, Any, List, Callable, TypeVar

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from fastapi import Request

from src.models.audit import AuditLog, AuditAction, ResourceType
from src.models.user import User


T = TypeVar('T')


class AuditService:
    """审计日志服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user: Optional[User] = None,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> AuditLog:
        """
        记录审计日志
        
        Args:
            action: 操作类型
            resource_type: 资源类型
            resource_id: 资源ID
            user: 操作用户
            old_value: 变更前的值
            new_value: 变更后的值
            ip_address: 客户端IP
            user_agent: 用户代理
            request_id: 请求ID
            status: 操作状态
            error_message: 错误信息
            extra_data: 额外数据
            
        Returns:
            创建的审计日志记录
        """
        audit_log = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            user_role=user.role if user else None,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status=status,
            error_message=error_message,
            extra_data=extra_data,
        )
        
        self.db.add(audit_log)
        await self.db.flush()
        
        logger.info(
            f"审计日志: {action} | 用户: {user.email if user else 'anonymous'} | "
            f"资源: {resource_type}/{resource_id} | 状态: {status}"
        )
        
        return audit_log
    
    async def log_from_request(
        self,
        request: Request,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user: Optional[User] = None,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> AuditLog:
        """
        从请求对象记录审计日志
        
        自动提取IP地址、User-Agent等信息
        """
        # 获取客户端IP（考虑代理）
        ip_address = request.headers.get("X-Forwarded-For")
        if ip_address:
            ip_address = ip_address.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else None
        
        # 获取请求ID
        request_id = request.headers.get("X-Request-ID")
        
        return await self.log(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user=user,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=request.headers.get("User-Agent"),
            request_id=request_id,
            status=status,
            error_message=error_message,
            extra_data=extra_data,
        )
    
    async def query(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        actions: Optional[List[str]] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_desc: bool = True,
    ) -> List[AuditLog]:
        """
        查询审计日志
        
        Args:
            user_id: 按用户ID筛选
            action: 按单个操作类型筛选
            actions: 按多个操作类型筛选
            resource_type: 按资源类型筛选
            resource_id: 按资源ID筛选
            status: 按状态筛选
            start_time: 开始时间
            end_time: 结束时间
            ip_address: 按IP地址筛选
            limit: 返回数量限制
            offset: 偏移量
            order_desc: 是否按时间倒序
            
        Returns:
            审计日志列表
        """
        query = select(AuditLog)
        
        # 构建查询条件
        conditions = []
        
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        
        if action:
            conditions.append(AuditLog.action == action)
        
        if actions:
            conditions.append(AuditLog.action.in_(actions))
        
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
        
        if resource_id:
            conditions.append(AuditLog.resource_id == resource_id)
        
        if status:
            conditions.append(AuditLog.status == status)
        
        if start_time:
            conditions.append(AuditLog.created_at >= start_time)
        
        if end_time:
            conditions.append(AuditLog.created_at <= end_time)
        
        if ip_address:
            conditions.append(AuditLog.ip_address == ip_address)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # 排序
        if order_desc:
            query = query.order_by(AuditLog.created_at.desc())
        else:
            query = query.order_by(AuditLog.created_at.asc())
        
        # 分页
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def count(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """
        统计审计日志数量
        """
        query = select(func.count(AuditLog.id))
        
        conditions = []
        
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        
        if action:
            conditions.append(AuditLog.action == action)
        
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
        
        if status:
            conditions.append(AuditLog.status == status)
        
        if start_time:
            conditions.append(AuditLog.created_at >= start_time)
        
        if end_time:
            conditions.append(AuditLog.created_at <= end_time)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def get_user_activity(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        获取用户最近活动
        """
        start_time = datetime.utcnow() - timedelta(days=days)
        return await self.query(
            user_id=user_id,
            start_time=start_time,
            limit=limit,
        )
    
    async def get_resource_history(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 50,
    ) -> List[AuditLog]:
        """
        获取资源的变更历史
        """
        return await self.query(
            resource_type=resource_type,
            resource_id=resource_id,
            limit=limit,
        )
    
    async def get_security_events(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        获取安全相关事件
        """
        security_actions = [
            AuditAction.USER_LOGIN.value,
            AuditAction.USER_LOGOUT.value,
            AuditAction.USER_PASSWORD_CHANGE.value,
            AuditAction.PERMISSION_GRANT.value,
            AuditAction.PERMISSION_REVOKE.value,
            AuditAction.ROLE_CHANGE.value,
            AuditAction.TOKEN_REFRESH.value,
            AuditAction.TOKEN_REVOKE.value,
        ]
        
        start_time = datetime.utcnow() - timedelta(hours=hours)
        return await self.query(
            actions=security_actions,
            start_time=start_time,
            limit=limit,
        )
    
    async def get_failed_operations(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        获取失败的操作
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)
        return await self.query(
            status="failed",
            start_time=start_time,
            limit=limit,
        )
    
    async def get_action_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[dict]:
        """
        获取操作统计
        """
        query = select(
            AuditLog.action,
            func.count(AuditLog.id).label("count"),
        ).group_by(AuditLog.action)
        
        conditions = []
        if start_time:
            conditions.append(AuditLog.created_at >= start_time)
        if end_time:
            conditions.append(AuditLog.created_at <= end_time)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(func.count(AuditLog.id).desc())
        
        result = await self.db.execute(query)
        return [{"action": row[0], "count": row[1]} for row in result.all()]


def audit_log(
    action: str,
    resource_type: str,
    get_resource_id: Optional[Callable[..., str]] = None,
    get_old_value: Optional[Callable[..., dict]] = None,
    get_new_value: Optional[Callable[..., dict]] = None,
):
    """
    审计日志装饰器
    
    用于自动记录函数执行的审计日志
    
    Args:
        action: 操作类型
        resource_type: 资源类型
        get_resource_id: 从函数参数获取资源ID的函数
        get_old_value: 获取旧值的函数
        get_new_value: 获取新值的函数
        
    Example:
        @audit_log(
            action=AuditAction.CASE_CREATE.value,
            resource_type=ResourceType.CASE.value,
            get_resource_id=lambda result: result.id,
        )
        async def create_case(db, user, data):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # 尝试从参数获取数据库会话和用户
            db = kwargs.get("db")
            user = kwargs.get("user")
            request = kwargs.get("request")
            
            # 获取旧值（如果需要）
            old_value = None
            if get_old_value:
                try:
                    old_value = get_old_value(*args, **kwargs)
                except Exception:
                    pass
            
            # 执行原函数
            error_message = None
            status = "success"
            result = None
            
            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                status = "failed"
                error_message = str(e)
                raise
            finally:
                # 记录审计日志
                if db:
                    try:
                        audit_service = AuditService(db)
                        
                        # 获取资源ID
                        resource_id = None
                        if get_resource_id and result:
                            try:
                                resource_id = get_resource_id(result)
                            except Exception:
                                pass
                        
                        # 获取新值
                        new_value = None
                        if get_new_value and result:
                            try:
                                new_value = get_new_value(result)
                            except Exception:
                                pass
                        
                        # 记录日志
                        if request:
                            await audit_service.log_from_request(
                                request=request,
                                action=action,
                                resource_type=resource_type,
                                resource_id=resource_id,
                                user=user,
                                old_value=old_value,
                                new_value=new_value,
                                status=status,
                                error_message=error_message,
                            )
                        else:
                            await audit_service.log(
                                action=action,
                                resource_type=resource_type,
                                resource_id=resource_id,
                                user=user,
                                old_value=old_value,
                                new_value=new_value,
                                status=status,
                                error_message=error_message,
                            )
                    except Exception as log_error:
                        logger.error(f"审计日志记录失败: {log_error}")
            
            return result
        
        return wrapper
    return decorator
