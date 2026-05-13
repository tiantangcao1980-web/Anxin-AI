"""
OA集成服务 (OA Integration Service)
负责与飞书、钉钉、企业微信等第三方办公平台进行对接，实现消息推送、审批流同步、组织架构同步等功能。
"""

import json
from abc import ABC, abstractmethod
from collections.abc import Mapping
from enum import Enum
from typing import Any, TypedDict

from loguru import logger

from src.core.config import settings


class OAProviderConfigError(RuntimeError):
    """Raised when an OA provider would otherwise fall back to mock data."""


class TokenCache(TypedDict):
    token: str
    expires_at: float


def _commercial_environment() -> bool:
    return settings.ENVIRONMENT.lower() in {"production", "staging"}


def _missing_config_message(provider: str, env_names: list[str]) -> str:
    return f"{provider} 未配置 {', '.join(env_names)}，staging/production 环境禁止使用模拟 OA 集成。"


def _require_non_mock_capability(provider: str, capability: str) -> None:
    if _commercial_environment():
        raise OAProviderConfigError(f"{provider} {capability} 尚未接入真实 API，staging/production 环境禁止返回模拟结果。")


def _string_value(data: Mapping[str, Any], key: str, default: str = "") -> str:
    value = data.get(key, default)
    return value if isinstance(value, str) else default


def _number_value(data: Mapping[str, Any], key: str, default: float) -> float:
    value = data.get(key, default)
    return float(value) if isinstance(value, int | float) else default


def _mapping_value(data: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    return value if isinstance(value, dict) else {}


class OAProviderType(Enum):
    FEISHU = "feishu"
    DINGTALK = "dingtalk"
    WECOM = "wecom"
    GENERIC = "generic" # 通用/自定义

class BaseOAProvider(ABC):
    """OA提供商基类"""

    @abstractmethod
    async def send_notification(self, user_id: str, title: str, content: str, url: str | None = None) -> bool:
        """发送通知消息"""
        pass

    @abstractmethod
    async def create_approval_instance(self, template_id: str, initiator_id: str, form_data: dict[str, object]) -> str:
        """创建审批实例，返回实例ID"""
        pass

    @abstractmethod
    async def get_approval_status(self, instance_id: str) -> str:
        """获取审批状态"""
        pass

    @abstractmethod
    async def sync_department_users(self, dept_id: str) -> list[dict[str, object]]:
        """同步部门用户"""
        pass

class FeishuProvider(BaseOAProvider):
    """
    飞书集成实现

    认证方式: app_id + app_secret → tenant_access_token
    消息 API: POST https://open.feishu.cn/open-apis/im/v1/messages
    审批 API: POST https://open.feishu.cn/open-apis/approval/v4/instances
    """

    def __init__(self) -> None:
        import os
        self.app_id = os.getenv("FEISHU_APP_ID", "")
        self.app_secret = os.getenv("FEISHU_APP_SECRET", "")
        self.base_url = "https://open.feishu.cn/open-apis"
        self._token_cache: TokenCache | None = None

    async def _get_token(self) -> str:
        """获取 tenant_access_token（带缓存）"""
        import time
        if self._token_cache and time.time() < self._token_cache["expires_at"]:
            return self._token_cache["token"]

        if not self.app_id or not self.app_secret:
            if _commercial_environment():
                raise OAProviderConfigError(_missing_config_message("Feishu", ["FEISHU_APP_ID", "FEISHU_APP_SECRET"]))
            logger.warning("[Feishu] app_id/app_secret 未配置，使用模拟模式")
            return "mock_token"

        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.base_url}/auth/v3/tenant_access_token/internal",
                json={"app_id": self.app_id, "app_secret": self.app_secret},
            )
            data = resp.json()
            token = _string_value(data, "tenant_access_token")
            expires_in = _number_value(data, "expire", 7200)
            self._token_cache = {"token": token, "expires_at": time.time() + expires_in - 300}
            return token

    async def send_notification(self, user_id: str, title: str, content: str, url: str | None = None) -> bool:
        token = await self._get_token()
        if token == "mock_token":
            logger.info(f"[Feishu/Mock] 发送消息给 {user_id}: {title}")
            return True

        import httpx
        elements: list[dict[str, object]] = [
            {"tag": "div", "text": {"content": content, "tag": "lark_md"}},
        ]
        card_payload: dict[str, object] = {
            "header": {"title": {"content": title, "tag": "plain_text"}},
            "elements": elements,
        }
        if url:
            elements.append({
                "tag": "action",
                "actions": [{"tag": "button", "text": {"content": "查看详情", "tag": "plain_text"}, "url": url, "type": "primary"}],
            })

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.base_url}/im/v1/messages?receive_id_type=user_id",
                headers={"Authorization": f"Bearer {token}"},
                json={"receive_id": user_id, "content": json.dumps(card_payload), "msg_type": "interactive"},
            )
            ok = resp.status_code < 400
            if not ok:
                logger.warning(f"[Feishu] 发送消息失败: {resp.text}")
            return ok

    async def create_approval_instance(self, template_id: str, initiator_id: str, form_data: dict[str, object]) -> str:
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
            payload = _mapping_value(data, "data")
            return _string_value(payload, "instance_code", f"feishu_err_{resp.status_code}")

    async def get_approval_status(self, instance_id: str) -> str:
        _require_non_mock_capability("Feishu", "审批状态查询")
        return "PENDING"  # 实际应查询飞书 API

    async def sync_department_users(self, dept_id: str) -> list[dict[str, object]]:
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
            payload = _mapping_value(data, "data")
            items = payload.get("items", [])
            if not isinstance(items, list):
                return []
            return [
                {"id": _string_value(u, "user_id"), "name": _string_value(u, "name")}
                for u in items
                if isinstance(u, dict)
            ]


class DingTalkProvider(BaseOAProvider):
    """
    钉钉集成实现

    认证方式: appkey + appsecret → access_token
    消息 API: POST https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2
    审批 API: POST https://oapi.dingtalk.com/topapi/processinstance/create
    """

    def __init__(self) -> None:
        import os
        self.app_key = os.getenv("DINGTALK_APP_KEY", "")
        self.app_secret = os.getenv("DINGTALK_APP_SECRET", "")
        self.agent_id = os.getenv("DINGTALK_AGENT_ID", "")
        self.base_url = "https://oapi.dingtalk.com"
        self._token_cache: TokenCache | None = None

    async def _get_token(self) -> str:
        import time
        if self._token_cache and time.time() < self._token_cache["expires_at"]:
            return self._token_cache["token"]

        if not self.app_key or not self.app_secret:
            if _commercial_environment():
                raise OAProviderConfigError(_missing_config_message("DingTalk", ["DINGTALK_APP_KEY", "DINGTALK_APP_SECRET"]))
            logger.warning("[DingTalk] appkey/appsecret 未配置，使用模拟模式")
            return "mock_token"

        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/gettoken?appkey={self.app_key}&appsecret={self.app_secret}"
            )
            data = resp.json()
            token = _string_value(data, "access_token")
            expires_in = _number_value(data, "expires_in", 7200)
            self._token_cache = {"token": token, "expires_at": time.time() + expires_in - 300}
            return token

    async def send_notification(self, user_id: str, title: str, content: str, url: str | None = None) -> bool:
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
            data = resp.json()
            return _number_value(data, "errcode", -1) == 0

    async def create_approval_instance(self, template_id: str, initiator_id: str, form_data: dict[str, object]) -> str:
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
            data = resp.json()
            return _string_value(data, "process_instance_id", "dingtalk_err")

    async def get_approval_status(self, instance_id: str) -> str:
        _require_non_mock_capability("DingTalk", "审批状态查询")
        return "RUNNING"

    async def sync_department_users(self, dept_id: str) -> list[dict[str, object]]:
        _require_non_mock_capability("DingTalk", "组织架构同步")
        return [{"id": "mock_d1", "name": "模拟钉钉用户"}]


class WeComProvider(BaseOAProvider):
    """
    企业微信集成实现

    认证方式: corpid + corpsecret → access_token
    消息 API: POST https://qyapi.weixin.qq.com/cgi-bin/message/send
    审批 API: POST https://qyapi.weixin.qq.com/cgi-bin/oa/applyevent
    """

    def __init__(self) -> None:
        import os
        self.corp_id = os.getenv("WECOM_CORP_ID", "")
        self.corp_secret = os.getenv("WECOM_CORP_SECRET", "")
        self.agent_id = os.getenv("WECOM_AGENT_ID", "")
        self.base_url = "https://qyapi.weixin.qq.com/cgi-bin"
        self._token_cache: TokenCache | None = None

    async def _get_token(self) -> str:
        import time
        if self._token_cache and time.time() < self._token_cache["expires_at"]:
            return self._token_cache["token"]

        if not self.corp_id or not self.corp_secret:
            if _commercial_environment():
                raise OAProviderConfigError(_missing_config_message("WeCom", ["WECOM_CORP_ID", "WECOM_CORP_SECRET"]))
            logger.warning("[WeCom] corpid/corpsecret 未配置，使用模拟模式")
            return "mock_token"

        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/gettoken?corpid={self.corp_id}&corpsecret={self.corp_secret}"
            )
            data = resp.json()
            token = _string_value(data, "access_token")
            expires_in = _number_value(data, "expires_in", 7200)
            self._token_cache = {"token": token, "expires_at": time.time() + expires_in - 300}
            return token

    async def send_notification(self, user_id: str, title: str, content: str, url: str | None = None) -> bool:
        token = await self._get_token()
        if token == "mock_token":
            logger.info(f"[WeCom/Mock] 发送消息给 {user_id}: {title}")
            return True

        import httpx
        msg = {
            "touser": user_id,
            "msgtype": "textcard",
            "agentid": int(self.agent_id or 0),
            "textcard": {"title": title, "description": content[:512], "url": url or "https://anxinai.com"},
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{self.base_url}/message/send?access_token={token}", json=msg)
            data = resp.json()
            return _number_value(data, "errcode", -1) == 0

    async def create_approval_instance(self, template_id: str, initiator_id: str, form_data: dict[str, object]) -> str:
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
            data = resp.json()
            return _string_value(data, "sp_no", "wecom_err")

    async def get_approval_status(self, instance_id: str) -> str:
        _require_non_mock_capability("WeCom", "审批状态查询")
        return "1"  # 1=审批中

    async def sync_department_users(self, dept_id: str) -> list[dict[str, object]]:
        _require_non_mock_capability("WeCom", "组织架构同步")
        return [{"id": "mock_w1", "name": "模拟企微用户"}]

class OAIntegrationService:

    def __init__(self) -> None:
        self.providers: dict[str, BaseOAProvider] = {
            OAProviderType.FEISHU.value: FeishuProvider(),
            OAProviderType.DINGTALK.value: DingTalkProvider(),
            OAProviderType.WECOM.value: WeComProvider()
        }
        # 默认提供商，可通过配置切换
        self.default_provider_name = OAProviderType.FEISHU.value
        logger.info("OA集成服务初始化完成")

    def get_provider(self, provider_name: str | None = None) -> BaseOAProvider:
        name = provider_name or self.default_provider_name
        return self.providers.get(name, self.providers[OAProviderType.FEISHU.value])

    async def send_notification(self, user_id: str, title: str, content: str, provider: str | None = None) -> bool:
        """统一发送通知接口"""
        return await self.get_provider(provider).send_notification(user_id, title, content)

    async def initiate_approval(self, title: str, details: dict[str, object], initiator_id: str, provider: str | None = None) -> str:
        """统一发起审批接口"""
        # 实际场景中这里需要根据业务类型映射到OA的模板ID
        template_id = "generic_approval_template"
        return await self.get_provider(provider).create_approval_instance(template_id, initiator_id, details)

    async def sync_org_structure(self, provider: str | None = None) -> dict[str, object]:
        """同步组织架构"""
        # 模拟同步根部门
        users = await self.get_provider(provider).sync_department_users("root")
        return {"synced_count": len(users), "users": users}

# 全局实例
oa_service = OAIntegrationService()
