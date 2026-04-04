"""
OA集成服务 (OA Integration Service)
负责与飞书、钉钉、企业微信等第三方办公平台进行对接，实现消息推送、审批流同步、组织架构同步等功能。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum
from loguru import logger
import asyncio
import json

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
    """
    飞书集成实现

    认证方式: app_id + app_secret → tenant_access_token
    消息 API: POST https://open.feishu.cn/open-apis/im/v1/messages
    审批 API: POST https://open.feishu.cn/open-apis/approval/v4/instances
    """

    def __init__(self):
        import os
        self.app_id = os.getenv("FEISHU_APP_ID", "")
        self.app_secret = os.getenv("FEISHU_APP_SECRET", "")
        self.base_url = "https://open.feishu.cn/open-apis"
        self._token_cache: Optional[Dict[str, Any]] = None

    async def _get_token(self) -> str:
        """获取 tenant_access_token（带缓存）"""
        import time
        if self._token_cache and time.time() < self._token_cache.get("expires_at", 0):
            return self._token_cache["token"]

        if not self.app_id or not self.app_secret:
            logger.warning("[Feishu] app_id/app_secret 未配置，使用模拟模式")
            return "mock_token"

        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.base_url}/auth/v3/tenant_access_token/internal",
                json={"app_id": self.app_id, "app_secret": self.app_secret},
            )
            data = resp.json()
            token = data.get("tenant_access_token", "")
            self._token_cache = {"token": token, "expires_at": time.time() + data.get("expire", 7200) - 300}
            return token

    async def send_notification(self, user_id: str, title: str, content: str, url: Optional[str] = None) -> bool:
        token = await self._get_token()
        if token == "mock_token":
            logger.info(f"[Feishu/Mock] 发送消息给 {user_id}: {title}")
            return True

        import httpx
        card = {
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"content": title, "tag": "plain_text"}},
                "elements": [{"tag": "div", "text": {"content": content, "tag": "lark_md"}}],
            },
        }
        if url:
            card["card"]["elements"].append({
                "tag": "action",
                "actions": [{"tag": "button", "text": {"content": "查看详情", "tag": "plain_text"}, "url": url, "type": "primary"}],
            })

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.base_url}/im/v1/messages?receive_id_type=user_id",
                headers={"Authorization": f"Bearer {token}"},
                json={"receive_id": user_id, "content": json.dumps(card["card"]), "msg_type": "interactive"},
            )
            ok = resp.status_code < 400
            if not ok:
                logger.warning(f"[Feishu] 发送消息失败: {resp.text}")
            return ok

    async def create_approval_instance(self, template_id: str, initiator_id: str, form_data: Dict[str, Any]) -> str:
        token = await self._get_token()
        if token == "mock_token":
            instance_id = f"feishu_approval_{initiator_id}_{int(__import__('time').time())}"
            logger.info(f"[Feishu/Mock] 创建审批 {instance_id}")
            return instance_id

        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.base_url}/approval/v4/instances",
                headers={"Authorization": f"Bearer {token}"},
                json={"approval_code": template_id, "user_id": initiator_id, "form": json.dumps(form_data)},
            )
            data = resp.json()
            return data.get("data", {}).get("instance_code", f"feishu_err_{resp.status_code}")

    async def get_approval_status(self, instance_id: str) -> str:
        return "PENDING"  # 实际应查询飞书 API

    async def sync_department_users(self, dept_id: str) -> List[Dict[str, Any]]:
        token = await self._get_token()
        if token == "mock_token":
            return [{"id": "mock_u1", "name": "Feishu User 1"}]

        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/contact/v3/users?department_id={dept_id}&page_size=50",
                headers={"Authorization": f"Bearer {token}"},
            )
            data = resp.json()
            items = data.get("data", {}).get("items", [])
            return [{"id": u.get("user_id"), "name": u.get("name")} for u in items]


class DingTalkProvider(BaseOAProvider):
    """
    钉钉集成实现

    认证方式: appkey + appsecret → access_token
    消息 API: POST https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2
    审批 API: POST https://oapi.dingtalk.com/topapi/processinstance/create
    """

    def __init__(self):
        import os
        self.app_key = os.getenv("DINGTALK_APP_KEY", "")
        self.app_secret = os.getenv("DINGTALK_APP_SECRET", "")
        self.agent_id = os.getenv("DINGTALK_AGENT_ID", "")
        self.base_url = "https://oapi.dingtalk.com"
        self._token_cache: Optional[Dict[str, Any]] = None

    async def _get_token(self) -> str:
        import time
        if self._token_cache and time.time() < self._token_cache.get("expires_at", 0):
            return self._token_cache["token"]

        if not self.app_key or not self.app_secret:
            logger.warning("[DingTalk] appkey/appsecret 未配置，使用模拟模式")
            return "mock_token"

        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/gettoken?appkey={self.app_key}&appsecret={self.app_secret}"
            )
            data = resp.json()
            token = data.get("access_token", "")
            self._token_cache = {"token": token, "expires_at": time.time() + data.get("expires_in", 7200) - 300}
            return token

    async def send_notification(self, user_id: str, title: str, content: str, url: Optional[str] = None) -> bool:
        token = await self._get_token()
        if token == "mock_token":
            logger.info(f"[DingTalk/Mock] 发送消息给 {user_id}: {title}")
            return True

        import httpx
        msg = {"msgtype": "markdown", "markdown": {"title": title, "text": f"### {title}\n\n{content}"}}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.base_url}/topapi/message/corpconversation/asyncsend_v2?access_token={token}",
                json={"agent_id": self.agent_id, "userid_list": user_id, "msg": msg},
            )
            return resp.json().get("errcode", -1) == 0

    async def create_approval_instance(self, template_id: str, initiator_id: str, form_data: Dict[str, Any]) -> str:
        token = await self._get_token()
        if token == "mock_token":
            instance_id = f"dingtalk_proc_{initiator_id}_{int(__import__('time').time())}"
            logger.info(f"[DingTalk/Mock] 创建审批 {instance_id}")
            return instance_id

        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.base_url}/topapi/processinstance/create?access_token={token}",
                json={"process_code": template_id, "originator_user_id": initiator_id, "form_component_values": form_data},
            )
            return resp.json().get("process_instance_id", f"dingtalk_err")

    async def get_approval_status(self, instance_id: str) -> str:
        return "RUNNING"

    async def sync_department_users(self, dept_id: str) -> List[Dict[str, Any]]:
        return [{"id": "mock_d1", "name": "模拟钉钉用户"}]


class WeComProvider(BaseOAProvider):
    """
    企业微信集成实现

    认证方式: corpid + corpsecret → access_token
    消息 API: POST https://qyapi.weixin.qq.com/cgi-bin/message/send
    审批 API: POST https://qyapi.weixin.qq.com/cgi-bin/oa/applyevent
    """

    def __init__(self):
        import os
        self.corp_id = os.getenv("WECOM_CORP_ID", "")
        self.corp_secret = os.getenv("WECOM_CORP_SECRET", "")
        self.agent_id = os.getenv("WECOM_AGENT_ID", "")
        self.base_url = "https://qyapi.weixin.qq.com/cgi-bin"
        self._token_cache: Optional[Dict[str, Any]] = None

    async def _get_token(self) -> str:
        import time
        if self._token_cache and time.time() < self._token_cache.get("expires_at", 0):
            return self._token_cache["token"]

        if not self.corp_id or not self.corp_secret:
            logger.warning("[WeCom] corpid/corpsecret 未配置，使用模拟模式")
            return "mock_token"

        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/gettoken?corpid={self.corp_id}&corpsecret={self.corp_secret}"
            )
            data = resp.json()
            token = data.get("access_token", "")
            self._token_cache = {"token": token, "expires_at": time.time() + data.get("expires_in", 7200) - 300}
            return token

    async def send_notification(self, user_id: str, title: str, content: str, url: Optional[str] = None) -> bool:
        token = await self._get_token()
        if token == "mock_token":
            logger.info(f"[WeCom/Mock] 发送消息给 {user_id}: {title}")
            return True

        import httpx
        msg = {
            "touser": user_id,
            "msgtype": "textcard",
            "agentid": int(self.agent_id or 0),
            "textcard": {"title": title, "description": content[:512], "url": url or "https://anxinfawu.com"},
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{self.base_url}/message/send?access_token={token}", json=msg)
            return resp.json().get("errcode", -1) == 0

    async def create_approval_instance(self, template_id: str, initiator_id: str, form_data: Dict[str, Any]) -> str:
        token = await self._get_token()
        if token == "mock_token":
            instance_id = f"wecom_sp_{initiator_id}_{int(__import__('time').time())}"
            logger.info(f"[WeCom/Mock] 创建审批 {instance_id}")
            return instance_id

        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.base_url}/oa/applyevent?access_token={token}",
                json={"creator_userid": initiator_id, "template_id": template_id, "apply_data": {"contents": form_data}},
            )
            return resp.json().get("sp_no", f"wecom_err")

    async def get_approval_status(self, instance_id: str) -> str:
        return "1"  # 1=审批中

    async def sync_department_users(self, dept_id: str) -> List[Dict[str, Any]]:
        return [{"id": "mock_w1", "name": "模拟企微用户"}]

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
