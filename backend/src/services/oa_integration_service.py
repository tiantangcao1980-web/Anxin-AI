"""
OA集成服务 (OA Integration Service)
负责与飞书、钉钉、企业微信等第三方办公平台进行对接，实现消息推送、审批流同步、组织架构同步等功能。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum
from loguru import logger
import asyncio

class OAProviderType(Enum):
    FEISHU = "feishu"
    DINGTALK = "dingtalk"
    WECOM = "wecom"
    GENERIC = "generic" # 通用/自定义

class BaseOAProvider(ABC):
    """OA提供商基类"""
    
    @abstractmethod
    async def send_notification(self, user_id: str, title: str, content: str, url: Optional[str] = None) -> bool:
        """发送通知消息"""
        pass
    
    @abstractmethod
    async def create_approval_instance(self, template_id: str, initiator_id: str, form_data: Dict[str, Any]) -> str:
        """创建审批实例，返回实例ID"""
        pass
    
    @abstractmethod
    async def get_approval_status(self, instance_id: str) -> str:
        """获取审批状态"""
        pass
    
    @abstractmethod
    async def sync_department_users(self, dept_id: str) -> List[Dict[str, Any]]:
        """同步部门用户"""
        pass

class FeishuProvider(BaseOAProvider):
    """飞书集成实现 (Mock)"""
    
    async def send_notification(self, user_id: str, title: str, content: str, url: Optional[str] = None) -> bool:
        logger.info(f"[Feishu] Sending card to {user_id}: {title} - {content}")
        return True
        
    async def create_approval_instance(self, template_id: str, initiator_id: str, form_data: Dict[str, Any]) -> str:
        instance_id = f"feishu_approval_{initiator_id}_123"
        logger.info(f"[Feishu] Created approval {instance_id} with data {form_data}")
        return instance_id
        
    async def get_approval_status(self, instance_id: str) -> str:
        return "PENDING"
        
    async def sync_department_users(self, dept_id: str) -> List[Dict[str, Any]]:
        return [{"id": "u1", "name": "Feishu User 1"}]

class DingTalkProvider(BaseOAProvider):
    """钉钉集成实现 (Mock)"""
    
    async def send_notification(self, user_id: str, title: str, content: str, url: Optional[str] = None) -> bool:
        logger.info(f"[DingTalk] Sending message to {user_id}: {title}")
        return True
        
    async def create_approval_instance(self, template_id: str, initiator_id: str, form_data: Dict[str, Any]) -> str:
        instance_id = f"dingtalk_proc_{initiator_id}_456"
        logger.info(f"[DingTalk] Created process {instance_id}")
        return instance_id
        
    async def get_approval_status(self, instance_id: str) -> str:
        return "RUNNING"
        
    async def sync_department_users(self, dept_id: str) -> List[Dict[str, Any]]:
        return [{"id": "d1", "name": "DingTalk User 1"}]

class WeComProvider(BaseOAProvider):
    """企业微信集成实现 (Mock)"""
    
    async def send_notification(self, user_id: str, title: str, content: str, url: Optional[str] = None) -> bool:
        logger.info(f"[WeCom] Sending textcard to {user_id}: {title}")
        return True
        
    async def create_approval_instance(self, template_id: str, initiator_id: str, form_data: Dict[str, Any]) -> str:
        instance_id = f"wecom_sp_{initiator_id}_789"
        logger.info(f"[WeCom] Created approval {instance_id}")
        return instance_id
        
    async def get_approval_status(self, instance_id: str) -> str:
        return "1" # 1=审批中
        
    async def sync_department_users(self, dept_id: str) -> List[Dict[str, Any]]:
        return [{"id": "w1", "name": "WeCom User 1"}]

class OAIntegrationService:
    
    def __init__(self):
        self.providers: Dict[str, BaseOAProvider] = {
            OAProviderType.FEISHU.value: FeishuProvider(),
            OAProviderType.DINGTALK.value: DingTalkProvider(),
            OAProviderType.WECOM.value: WeComProvider()
        }
        # 默认提供商，可通过配置切换
        self.default_provider_name = OAProviderType.FEISHU.value
        logger.info("OA集成服务初始化完成")

    def get_provider(self, provider_name: Optional[str] = None) -> BaseOAProvider:
        name = provider_name or self.default_provider_name
        return self.providers.get(name, self.providers[OAProviderType.FEISHU.value])

    async def send_notification(self, user_id: str, title: str, content: str, provider: Optional[str] = None) -> bool:
        """统一发送通知接口"""
        return await self.get_provider(provider).send_notification(user_id, title, content)

    async def initiate_approval(self, title: str, details: Dict[str, Any], initiator_id: str, provider: Optional[str] = None) -> str:
        """统一发起审批接口"""
        # 实际场景中这里需要根据业务类型映射到OA的模板ID
        template_id = "generic_approval_template"
        return await self.get_provider(provider).create_approval_instance(template_id, initiator_id, details)

    async def sync_org_structure(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """同步组织架构"""
        # 模拟同步根部门
        users = await self.get_provider(provider).sync_department_users("root")
        return {"synced_count": len(users), "users": users}

# 全局实例
oa_service = OAIntegrationService()
