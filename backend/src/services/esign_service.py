"""
电子签章服务 - 提供商无关接口

支持对接 e签宝、法大大等第三方电子签章平台。
通过工厂函数 get_esign_provider() 根据环境变量选择具体实现。
开发/测试环境默认使用 MockESignProvider。
"""

import base64
import hashlib
import hmac
import json
import os
import random
import secrets
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, cast
from urllib.parse import urlencode

import httpx
from loguru import logger
from pydantic import BaseModel, Field

from src.core.config import settings

# ========== 数据模型 ==========


class SignType(str, Enum):
    """签署方类型"""
    PERSONAL = "personal"
    COMPANY = "company"


class FlowStatus(str, Enum):
    """签署流程状态"""
    CREATED = "created"
    SIGNING = "signing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SignerStatus(str, Enum):
    """单个签署人状态"""
    PENDING = "pending"
    SIGNED = "signed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class SignerInfo(BaseModel):
    """签署人信息"""
    signer_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="签署人姓名/企业名称")
    id_number: str | None = Field(None, description="身份证号/统一社会信用代码")
    mobile: str | None = Field(None, description="手机号码")
    email: str | None = Field(None, description="邮箱")
    sign_type: SignType = Field(default=SignType.PERSONAL, description="签署类型")
    sign_order: int = Field(default=0, description="签署顺序，0 表示不限顺序")


class SignerStatusInfo(BaseModel):
    """签署人状态信息"""
    signer_id: str
    name: str
    sign_type: SignType
    status: SignerStatus = SignerStatus.PENDING
    signed_at: datetime | None = None
    reject_reason: str | None = None


class SignFlowResult(BaseModel):
    """创建签署流程结果"""
    flow_id: str
    contract_id: str
    sign_urls: dict[str, str] = Field(default_factory=dict, description="signer_id -> sign_url")
    status: FlowStatus = FlowStatus.CREATED
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime | None = None


class SignFlowStatus(BaseModel):
    """签署流程状态详情"""
    flow_id: str
    contract_id: str
    status: FlowStatus
    signers_status: list[SignerStatusInfo] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime | None = None
    completed_at: datetime | None = None


class ESignProviderConfigError(RuntimeError):
    """Raised when an official e-sign provider lacks required configuration."""


class ESignProviderAPIError(RuntimeError):
    """Raised when an official e-sign provider call fails."""


# ========== 抽象接口 ==========


class ESignProvider(ABC):
    """电子签章提供商抽象接口"""

    @abstractmethod
    async def create_sign_flow(
        self,
        contract_id: str,
        title: str,
        signers: list[SignerInfo],
        document_url: str | None = None,
        expire_hours: int = 72,
    ) -> SignFlowResult:
        """
        创建签署流程

        Args:
            contract_id: 合同ID
            title: 签署流程标题
            signers: 签署人列表
            document_url: 待签署文件URL
            expire_hours: 过期时间（小时）

        Returns:
            SignFlowResult: 签署流程信息（含签署链接）
        """
        ...

    @abstractmethod
    async def get_sign_url(self, flow_id: str, signer_id: str) -> str:
        """
        获取指定签署人的签署链接

        Args:
            flow_id: 签署流程ID
            signer_id: 签署人ID

        Returns:
            签署页面URL
        """
        ...

    @abstractmethod
    async def get_flow_status(self, flow_id: str) -> SignFlowStatus:
        """
        查询签署流程状态

        Args:
            flow_id: 签署流程ID

        Returns:
            SignFlowStatus: 当前流程状态
        """
        ...

    @abstractmethod
    async def download_signed_doc(self, flow_id: str) -> bytes:
        """
        下载已签署的文件

        Args:
            flow_id: 签署流程ID

        Returns:
            签署完成的文件内容
        """
        ...

    @abstractmethod
    async def cancel_flow(self, flow_id: str, reason: str = "") -> bool:
        """
        取消签署流程

        Args:
            flow_id: 签署流程ID
            reason: 取消原因

        Returns:
            是否取消成功
        """
        ...


# ========== Mock 实现（开发/测试用） ==========


class MockESignProvider(ESignProvider):
    """
    Mock 电子签章提供商

    用于开发和测试环境，不依赖任何外部服务。
    签署状态基于时间自动推进。
    """

    def __init__(self) -> None:
        # 内存存储，仅用于开发
        self._flows: dict[str, dict[str, Any]] = {}

    async def create_sign_flow(
        self,
        contract_id: str,
        title: str,
        signers: list[SignerInfo],
        document_url: str | None = None,
        expire_hours: int = 72,
    ) -> SignFlowResult:
        flow_id = f"mock_flow_{uuid.uuid4().hex[:12]}"
        now = datetime.now()

        sign_urls: dict[str, str] = {}
        signers_status: list[dict[str, Any]] = []
        for signer in signers:
            sign_url = f"https://mock-esign.example.com/sign/{flow_id}/{signer.signer_id}"
            sign_urls[signer.signer_id] = sign_url
            signers_status.append({
                "signer_id": signer.signer_id,
                "name": signer.name,
                "sign_type": signer.sign_type.value,
                "status": SignerStatus.PENDING.value,
                "signed_at": None,
                "reject_reason": None,
            })

        self._flows[flow_id] = {
            "flow_id": flow_id,
            "contract_id": contract_id,
            "title": title,
            "status": FlowStatus.CREATED.value,
            "sign_urls": sign_urls,
            "signers_status": signers_status,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=expire_hours)).isoformat(),
            "updated_at": now.isoformat(),
        }

        logger.info(
            f"[MockESign] 创建签署流程: flow_id={flow_id}, "
            f"contract_id={contract_id}, signers={len(signers)}"
        )

        return SignFlowResult(
            flow_id=flow_id,
            contract_id=contract_id,
            sign_urls=sign_urls,
            status=FlowStatus.CREATED,
            created_at=now,
            expires_at=now + timedelta(hours=expire_hours),
        )

    async def get_sign_url(self, flow_id: str, signer_id: str) -> str:
        flow = self._flows.get(flow_id)
        if not flow:
            raise ValueError(f"签署流程不存在: {flow_id}")

        url = flow["sign_urls"].get(signer_id)
        if not url:
            raise ValueError(f"签署人不存在: {signer_id}")

        logger.info(f"[MockESign] 获取签署链接: flow_id={flow_id}, signer_id={signer_id}")
        return str(url)

    async def get_flow_status(self, flow_id: str) -> SignFlowStatus:
        flow = self._flows.get(flow_id)
        if not flow:
            raise ValueError(f"签署流程不存在: {flow_id}")

        # Mock 逻辑：根据创建时间推进状态
        created_at = datetime.fromisoformat(flow["created_at"])
        elapsed = (datetime.now() - created_at).total_seconds()

        signers_status_list: list[SignerStatusInfo] = []
        all_signed = True
        for s in flow["signers_status"]:
            signer_status = SignerStatus(s["status"])
            signed_at = None

            # 模拟签署进度：每个签署人在创建后随机时间内"签署"
            if signer_status == SignerStatus.PENDING and elapsed > 30:
                # 30 秒后模拟部分签署人已签署（概率 70%）
                if random.random() < 0.7:
                    signer_status = SignerStatus.SIGNED
                    signed_at = created_at + timedelta(seconds=random.randint(10, int(elapsed)))
                    s["status"] = SignerStatus.SIGNED.value
                    s["signed_at"] = signed_at.isoformat()

            if signer_status != SignerStatus.SIGNED:
                all_signed = False

            signers_status_list.append(SignerStatusInfo(
                signer_id=s["signer_id"],
                name=s["name"],
                sign_type=SignType(s["sign_type"]),
                status=signer_status,
                signed_at=signed_at,
                reject_reason=s.get("reject_reason"),
            ))

        # 更新流程状态
        if all_signed and flow["signers_status"]:
            flow["status"] = FlowStatus.COMPLETED.value
        elif elapsed > 10:
            flow["status"] = FlowStatus.SIGNING.value

        current_status = FlowStatus(flow["status"])
        completed_at = None
        if current_status == FlowStatus.COMPLETED:
            completed_at = datetime.now()

        return SignFlowStatus(
            flow_id=flow_id,
            contract_id=flow["contract_id"],
            status=current_status,
            signers_status=signers_status_list,
            created_at=created_at,
            updated_at=datetime.now(),
            completed_at=completed_at,
        )

    async def download_signed_doc(self, flow_id: str) -> bytes:
        flow = self._flows.get(flow_id)
        if not flow:
            raise ValueError(f"签署流程不存在: {flow_id}")

        if FlowStatus(flow["status"]) != FlowStatus.COMPLETED:
            raise ValueError("签署尚未完成，无法下载")

        logger.info(f"[MockESign] 下载签署文件: flow_id={flow_id}")
        # 返回一个模拟的 PDF 占位内容
        return b"%PDF-1.4 mock signed document content"

    async def cancel_flow(self, flow_id: str, reason: str = "") -> bool:
        flow = self._flows.get(flow_id)
        if not flow:
            raise ValueError(f"签署流程不存在: {flow_id}")

        if FlowStatus(flow["status"]) in (FlowStatus.COMPLETED, FlowStatus.CANCELLED):
            return False

        flow["status"] = FlowStatus.CANCELLED.value
        flow["updated_at"] = datetime.now().isoformat()
        logger.info(f"[MockESign] 取消签署流程: flow_id={flow_id}, reason={reason}")
        return True


def _json_bytes(payload: dict[str, Any] | None) -> bytes:
    if payload is None:
        return b""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _form_json(payload: dict[str, Any] | None) -> str:
    if payload is None:
        return ""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        timestamp = float(text)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _first_value(payload: dict[str, Any], *keys: str) -> Any | None:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _data(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("data")
    return cast(dict[str, Any], value) if isinstance(value, dict) else payload


def _provider_error_message(provider: str, response: dict[str, Any]) -> str:
    return str(
        response.get("message")
        or response.get("msg")
        or response.get("errorMessage")
        or response.get("error")
        or f"{provider} API business error"
    )


def _normalize_flow_status(raw: Any) -> FlowStatus:
    state = str(raw or "").strip().lower()
    state = state.replace("-", "_").replace(" ", "_")
    if state in {"0", "created", "init", "draft", "wait_start"}:
        return FlowStatus.CREATED
    if state in {"1", "2", "signing", "in_progress", "processing", "started", "wait_sign"}:
        return FlowStatus.SIGNING
    if state in {"3", "completed", "complete", "finished", "finish", "signed", "success"}:
        return FlowStatus.COMPLETED
    if state in {"4", "rejected", "reject", "refused", "declined"}:
        return FlowStatus.REJECTED
    if state in {"5", "expired", "timeout"}:
        return FlowStatus.EXPIRED
    if state in {"6", "cancelled", "canceled", "cancel", "revoked", "abolished", "terminated"}:
        return FlowStatus.CANCELLED
    return FlowStatus.SIGNING


def _signer_status_from_provider(raw: Any) -> SignerStatus:
    state = str(raw or "").strip().lower()
    state = state.replace("-", "_").replace(" ", "_")
    if state in {"2", "signed", "success", "completed", "complete"}:
        return SignerStatus.SIGNED
    if state in {"4", "rejected", "reject", "refused", "declined"}:
        return SignerStatus.REJECTED
    if state in {"5", "expired", "timeout"}:
        return SignerStatus.EXPIRED
    return SignerStatus.PENDING


def _content_md5(body: bytes) -> str:
    if not body:
        return ""
    return base64.b64encode(hashlib.md5(body).digest()).decode("ascii")


def _esignbao_signature(method: str, path_with_query: str, body: bytes, app_secret: str) -> tuple[str, str]:
    content_type = "application/json; charset=UTF-8" if method.upper() not in {"GET", "DELETE"} else ""
    content_md5 = _content_md5(body) if method.upper() not in {"GET", "DELETE"} else ""
    string_to_sign = "\n".join(
        [
            method.upper(),
            "*/*",
            content_md5,
            content_type,
            "",
        ]
    ) + "\n" + path_with_query
    digest = hmac.new(app_secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii"), content_md5


def _fadada_sorted_params(params: dict[str, str]) -> str:
    return "&".join(f"{key}={params[key]}" for key in sorted(params) if params[key] != "")


def _fadada_signature(params: dict[str, str], timestamp: str, app_secret: str) -> str:
    sign_text = hashlib.sha256(_fadada_sorted_params(params).encode("utf-8")).hexdigest().lower()
    temporary_key = hmac.new(app_secret.encode("utf-8"), timestamp.encode("utf-8"), hashlib.sha256).digest()
    return hmac.new(temporary_key, sign_text.encode("utf-8"), hashlib.sha256).hexdigest().lower()


# ========== e签宝 官方协议实现 ==========


class ESignBaoProvider(ESignProvider):
    """
    e签宝电子签章提供商。

    默认路径采用公有云签署服务 API；不同账号产品线可通过 ESIGN_BAO_*_PATH
    做灰度覆盖，避免把沙箱/生产账号的版本差异硬编码进业务层。
    """

    def __init__(self) -> None:
        self.app_id: str = settings.ESIGN_BAO_APP_ID or os.getenv("ESIGN_BAO_APP_ID") or ""
        self.app_secret: str = settings.ESIGN_BAO_APP_SECRET or os.getenv("ESIGN_BAO_APP_SECRET") or ""
        self.api_url: str = (settings.ESIGN_BAO_API_URL or os.getenv(
            "ESIGN_BAO_API_URL",
            "https://smlopenapi.esign.cn",
        )).rstrip("/")
        self.create_path: str = settings.ESIGN_BAO_CREATE_FLOW_PATH
        self.start_path: str = settings.ESIGN_BAO_START_FLOW_PATH
        self.sign_url_path: str = settings.ESIGN_BAO_SIGN_URL_PATH
        self.status_path: str = settings.ESIGN_BAO_STATUS_PATH
        self.download_path: str = settings.ESIGN_BAO_DOWNLOAD_PATH
        self.cancel_path: str = settings.ESIGN_BAO_CANCEL_PATH
        if not self.app_id or not self.app_secret:
            logger.warning(
                "e签宝未配置 APP_ID / APP_SECRET，调用时将抛出异常。"
                "请在 .env 中设置 ESIGN_BAO_APP_ID 和 ESIGN_BAO_APP_SECRET。"
            )

    def _check_config(self) -> None:
        if not self.app_id or not self.app_secret:
            raise ESignProviderConfigError(
                "e签宝配置缺失: ESIGN_BAO_APP_ID, ESIGN_BAO_APP_SECRET"
            )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        expect_binary: bool = False,
    ) -> Any:
        self._check_config()
        path_with_query = f"{path}?{urlencode(query)}" if query else path
        body = _json_bytes(json_body)
        signature, content_md5 = _esignbao_signature(method, path_with_query, body, self.app_secret)
        headers: dict[str, str] = {
            "Accept": "*/*",
            "X-Tsign-Open-App-Id": self.app_id,
            "X-Tsign-Open-Auth-Mode": "Signature",
            "X-Tsign-Open-Ca-Timestamp": str(int(time.time() * 1000)),
            "X-Tsign-Open-Ca-Signature": signature,
            "Content-MD5": content_md5,
        }
        if method.upper() not in {"GET", "DELETE"}:
            headers["Content-Type"] = "application/json; charset=UTF-8"

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(
                method,
                f"{self.api_url}{path_with_query}",
                content=body if body else None,
                headers=headers,
            )
        if response.status_code >= 400:
            raise ESignProviderAPIError(f"e签宝 API 调用失败: {response.status_code} {response.text}")
        if expect_binary:
            return response.content
        if not response.content:
            return {}
        payload = response.json()
        code = str(payload.get("code", "0"))
        if code not in {"0", "200", "SUCCESS", "success"}:
            raise ESignProviderAPIError(f"e签宝 API 业务失败: {_provider_error_message('e签宝', payload)}")
        return payload

    def _build_create_payload(
        self,
        contract_id: str,
        title: str,
        signers: list[SignerInfo],
        document_url: str | None,
        expire_hours: int,
    ) -> dict[str, Any]:
        validity_days = max(1, expire_hours // 24)
        payload: dict[str, Any] = {
            "flowInfo": {
                "businessScene": title,
                "autoArchive": True,
                "contractValidity": validity_days,
                "flowConfigInfo": {"noticeType": "1"},
            },
            "signers": [
                {
                    "signerAccount": {
                        "signerAccountId": signer.signer_id,
                        "signerName": signer.name,
                        "signerMobile": signer.mobile,
                        "signerEmail": signer.email,
                    },
                    "signOrder": signer.sign_order,
                }
                for signer in signers
            ],
            "thirdOrderNo": contract_id,
        }
        if document_url:
            payload["docs"] = [{"fileId": document_url, "fileName": f"{title}.pdf"}]
        return payload

    def _status_from_payload(self, flow_id: str, payload: dict[str, Any]) -> SignFlowStatus:
        flow_data = _data(payload)
        raw_signers = (
            flow_data.get("signers")
            or flow_data.get("signerList")
            or flow_data.get("signersStatus")
            or []
        )
        signers: list[SignerStatusInfo] = []
        if isinstance(raw_signers, list):
            for index, signer in enumerate(raw_signers):
                if not isinstance(signer, dict):
                    continue
                signer_id = str(_first_value(signer, "accountId", "signerAccountId", "signerId", "id") or index)
                signers.append(
                    SignerStatusInfo(
                        signer_id=signer_id,
                        name=str(_first_value(signer, "name", "signerName", "accountName") or signer_id),
                        sign_type=SignType.COMPANY
                        if str(_first_value(signer, "signType", "type") or "").lower() in {"company", "org", "2"}
                        else SignType.PERSONAL,
                        status=_signer_status_from_provider(_first_value(signer, "signStatus", "status", "result")),
                        signed_at=_parse_datetime(_first_value(signer, "signedAt", "signTime", "signed_time")),
                        reject_reason=_first_value(signer, "rejectReason", "resultDescription", "reason"),
                    )
                )
        status = _normalize_flow_status(
            _first_value(flow_data, "status", "flowStatus", "signFlowStatus", "signResult")
        )
        return SignFlowStatus(
            flow_id=str(_first_value(flow_data, "flowId", "signFlowId") or flow_id),
            contract_id=str(_first_value(flow_data, "thirdOrderNo", "businessId", "contractId") or ""),
            status=status,
            signers_status=signers,
            created_at=_parse_datetime(_first_value(flow_data, "createTime", "createdAt", "created_at")) or datetime.now(),
            updated_at=_parse_datetime(_first_value(flow_data, "updateTime", "updatedAt", "updated_at")),
            completed_at=_parse_datetime(_first_value(flow_data, "finishTime", "completedAt", "completed_at")),
        )

    async def create_sign_flow(
        self,
        contract_id: str,
        title: str,
        signers: list[SignerInfo],
        document_url: str | None = None,
        expire_hours: int = 72,
    ) -> SignFlowResult:
        payload = self._build_create_payload(contract_id, title, signers, document_url, expire_hours)
        response = await self._request("POST", self.create_path, json_body=payload)
        data = _data(response)
        flow_id = str(_first_value(data, "flowId", "signFlowId", "flow_id") or "")
        if not flow_id:
            raise ESignProviderAPIError("e签宝创建签署流程响应缺少 flowId。")
        if self.start_path:
            await self._request("PUT", self.start_path.format(flow_id=flow_id))
        sign_urls: dict[str, str] = {}
        for signer in signers:
            try:
                sign_urls[signer.signer_id] = await self.get_sign_url(flow_id, signer.signer_id)
            except ESignProviderAPIError:
                logger.warning(f"e签宝签署链接获取失败，保留流程创建结果: flow_id={flow_id}, signer={signer.signer_id}")
        now = datetime.now()
        return SignFlowResult(
            flow_id=flow_id,
            contract_id=contract_id,
            sign_urls=sign_urls,
            status=FlowStatus.SIGNING,
            created_at=now,
            expires_at=now + timedelta(hours=expire_hours),
        )

    async def get_sign_url(self, flow_id: str, signer_id: str) -> str:
        response = await self._request(
            "GET",
            self.sign_url_path.format(flow_id=flow_id, signer_id=signer_id),
            query={"accountId": signer_id, "organizeId": "0", "urlType": "0"},
        )
        data = _data(response)
        url = _first_value(data, "url", "shortUrl", "signUrl", "executeUrl")
        if not url:
            raise ESignProviderAPIError("e签宝签署链接响应缺少 url。")
        return str(url)

    async def get_flow_status(self, flow_id: str) -> SignFlowStatus:
        response = await self._request("GET", self.status_path.format(flow_id=flow_id))
        return self._status_from_payload(flow_id, response)

    async def download_signed_doc(self, flow_id: str) -> bytes:
        response = await self._request("GET", self.download_path.format(flow_id=flow_id))
        data = _data(response)
        download_url = _first_value(data, "downloadUrl", "url", "fileUrl", "docsDownloadUrl")
        if download_url:
            async with httpx.AsyncClient(timeout=30) as client:
                download = await client.get(str(download_url))
            if download.status_code >= 400:
                raise ESignProviderAPIError(f"e签宝已签文件下载失败: {download.status_code}")
            return download.content
        content = _first_value(data, "content", "fileContent")
        if isinstance(content, str):
            try:
                return base64.b64decode(content)
            except Exception as exc:
                raise ESignProviderAPIError("e签宝已签文件响应缺少有效下载地址或 base64 内容。") from exc
        raise ESignProviderAPIError("e签宝已签文件响应缺少下载地址。")

    async def cancel_flow(self, flow_id: str, reason: str = "") -> bool:
        await self._request(
            "PUT",
            self.cancel_path.format(flow_id=flow_id),
            json_body={"revokeReason": reason or "用户取消签署流程"},
        )
        return True


# ========== 法大大 官方协议实现 ==========


class FaDaDaProvider(ESignProvider):
    """
    法大大 FASC OpenAPI v5.1 电子签章提供商。

    需要配置以下环境变量才能使用：
    - FADADA_APP_ID: 应用ID
    - FADADA_APP_SECRET: 应用密钥
    - FADADA_API_URL: API地址
    """

    def __init__(self) -> None:
        self.app_id: str = settings.FADADA_APP_ID or os.getenv("FADADA_APP_ID") or ""
        self.app_secret: str = settings.FADADA_APP_SECRET or os.getenv("FADADA_APP_SECRET") or ""
        self.api_url: str = (settings.FADADA_API_URL or os.getenv(
            "FADADA_API_URL",
            "https://api.fadada.com/api/v5",
        )).rstrip("/")
        self.access_token: str = settings.FADADA_ACCESS_TOKEN or os.getenv("FADADA_ACCESS_TOKEN") or ""

    def _check_config(self) -> None:
        if not self.app_id or not self.app_secret:
            raise ESignProviderConfigError(
                "法大大配置缺失: FADADA_APP_ID, FADADA_APP_SECRET"
            )

    def _headers(self, biz_content: str | None, access_token: str | None) -> dict[str, str]:
        self._check_config()
        timestamp = str(int(time.time() * 1000))
        values: dict[str, str] = {
            "X-FASC-App-Id": self.app_id,
            "X-FASC-Timestamp": timestamp,
            "X-FASC-Sign-Type": "HMAC-SHA256",
            "X-FASC-Nonce": secrets.token_hex(16),
            "X-FASC-Api-SubVersion": "5.1",
        }
        if access_token:
            values["X-FASC-AccessToken"] = access_token
            if biz_content is not None:
                values["bizContent"] = biz_content
        else:
            values["X-FASC-Grant-Type"] = "client_credential"
        values["X-FASC-Sign"] = _fadada_signature(values, timestamp, self.app_secret)
        values.pop("bizContent", None)
        values["Content-Type"] = "application/x-www-form-urlencoded;charset=UTF-8"
        return values

    async def _request(
        self,
        path: str,
        *,
        biz_content: dict[str, Any] | None = None,
        access_token: str | None = None,
        expect_binary: bool = False,
    ) -> Any:
        body_json = _form_json(biz_content)
        headers = self._headers(body_json if biz_content is not None else None, access_token)
        data = {"bizContent": body_json} if biz_content is not None else None
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.api_url}{path}",
                data=data,
                headers=headers,
            )
        if response.status_code >= 400:
            raise ESignProviderAPIError(f"法大大 API 调用失败: {response.status_code} {response.text}")
        if expect_binary:
            return response.content
        payload = response.json() if response.content else {}
        code = str(payload.get("code", "100000"))
        if code not in {"100000", "0", "200", "SUCCESS", "success"}:
            raise ESignProviderAPIError(f"法大大 API 业务失败: {_provider_error_message('法大大', payload)}")
        return payload

    async def _get_access_token(self) -> str:
        if self.access_token:
            return self.access_token
        response = await self._request(settings.FADADA_ACCESS_TOKEN_PATH, access_token=None)
        data = _data(response)
        token = _first_value(data, "accessToken", "access_token", "token")
        if not token:
            raise ESignProviderAPIError("法大大 access token 响应缺少 accessToken。")
        self.access_token = str(token)
        return self.access_token

    def _build_create_payload(
        self,
        contract_id: str,
        title: str,
        signers: list[SignerInfo],
        document_url: str | None,
        expire_hours: int,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "signTaskSubject": title,
            "autoStart": True,
            "autoFinish": True,
            "transReferenceId": contract_id,
            "expiresTime": int(time.time() * 1000) + expire_hours * 3600 * 1000,
            "actors": [
                {
                    "actor": {
                        "actorId": signer.signer_id,
                        "actorType": "corp" if signer.sign_type == SignType.COMPANY else "person",
                        "actorName": signer.name,
                        "permissions": ["sign"],
                        "sendNotification": bool(signer.mobile or signer.email),
                        "mobile": signer.mobile,
                        "email": signer.email,
                    },
                    "orderNo": signer.sign_order,
                }
                for signer in signers
            ],
        }
        if document_url:
            payload["docs"] = [{"docId": document_url, "docName": f"{title}.pdf"}]
        return payload

    async def create_sign_flow(
        self,
        contract_id: str,
        title: str,
        signers: list[SignerInfo],
        document_url: str | None = None,
        expire_hours: int = 72,
    ) -> SignFlowResult:
        token = await self._get_access_token()
        response = await self._request(
            settings.FADADA_CREATE_TASK_PATH,
            biz_content=self._build_create_payload(contract_id, title, signers, document_url, expire_hours),
            access_token=token,
        )
        data = _data(response)
        flow_id = str(_first_value(data, "signTaskId", "taskId", "flowId") or "")
        if not flow_id:
            raise ESignProviderAPIError("法大大创建签署任务响应缺少 signTaskId。")
        sign_urls: dict[str, str] = {}
        for signer in signers:
            try:
                sign_urls[signer.signer_id] = await self.get_sign_url(flow_id, signer.signer_id)
            except ESignProviderAPIError:
                logger.warning(f"法大大签署链接获取失败，保留任务创建结果: flow_id={flow_id}, signer={signer.signer_id}")
        now = datetime.now()
        return SignFlowResult(
            flow_id=flow_id,
            contract_id=contract_id,
            sign_urls=sign_urls,
            status=FlowStatus.SIGNING,
            created_at=now,
            expires_at=now + timedelta(hours=expire_hours),
        )

    async def get_sign_url(self, flow_id: str, signer_id: str) -> str:
        token = await self._get_access_token()
        response = await self._request(
            settings.FADADA_SIGN_URL_PATH,
            biz_content={"signTaskId": flow_id, "actorId": signer_id},
            access_token=token,
        )
        data = _data(response)
        url = _first_value(data, "actorSignTaskUrl", "actorSignTaskEmbedUrl", "signUrl", "url")
        if not url:
            raise ESignProviderAPIError("法大大签署链接响应缺少 actorSignTaskUrl。")
        return str(url)

    async def get_flow_status(self, flow_id: str) -> SignFlowStatus:
        token = await self._get_access_token()
        response = await self._request(
            settings.FADADA_STATUS_PATH,
            biz_content={"signTaskId": flow_id},
            access_token=token,
        )
        data = _data(response)
        raw_signers = data.get("actors") or data.get("actorList") or []
        signers: list[SignerStatusInfo] = []
        if isinstance(raw_signers, list):
            for index, signer in enumerate(raw_signers):
                if not isinstance(signer, dict):
                    continue
                actor: dict[str, Any] = (
                    cast(dict[str, Any], signer.get("actor"))
                    if isinstance(signer.get("actor"), dict)
                    else signer
                )
                signer_id = str(_first_value(actor, "actorId", "openUserId", "id") or index)
                signers.append(
                    SignerStatusInfo(
                        signer_id=signer_id,
                        name=str(_first_value(actor, "actorName", "name") or signer_id),
                        sign_type=SignType.COMPANY
                        if str(_first_value(actor, "actorType", "type") or "").lower() == "corp"
                        else SignType.PERSONAL,
                        status=_signer_status_from_provider(
                            _first_value(signer, "signStatus", "actorSignStatus", "status")
                        ),
                        signed_at=_parse_datetime(_first_value(signer, "signTime", "signedAt")),
                        reject_reason=_first_value(signer, "rejectReason", "reason"),
                    )
                )
        return SignFlowStatus(
            flow_id=str(_first_value(data, "signTaskId", "taskId") or flow_id),
            contract_id=str(_first_value(data, "transReferenceId", "contractId", "businessId") or ""),
            status=_normalize_flow_status(_first_value(data, "signTaskStatus", "status", "taskStatus")),
            signers_status=signers,
            created_at=_parse_datetime(_first_value(data, "createTime", "createdAt")) or datetime.now(),
            updated_at=_parse_datetime(_first_value(data, "updateTime", "updatedAt")),
            completed_at=_parse_datetime(_first_value(data, "finishTime", "completedAt")),
        )

    async def download_signed_doc(self, flow_id: str) -> bytes:
        token = await self._get_access_token()
        response = await self._request(
            settings.FADADA_DOWNLOAD_URL_PATH,
            biz_content={"signTaskId": flow_id},
            access_token=token,
        )
        data = _data(response)
        download_url = _first_value(data, "downloadUrl", "docDownloadUrl", "ownerDownloadUrl", "url")
        if not download_url:
            raise ESignProviderAPIError("法大大已签文件响应缺少下载地址。")
        async with httpx.AsyncClient(timeout=30) as client:
            download = await client.get(str(download_url))
        if download.status_code >= 400:
            raise ESignProviderAPIError(f"法大大已签文件下载失败: {download.status_code}")
        return download.content

    async def cancel_flow(self, flow_id: str, reason: str = "") -> bool:
        token = await self._get_access_token()
        await self._request(
            settings.FADADA_CANCEL_PATH,
            biz_content={"signTaskId": flow_id, "cancelReason": reason or "用户取消签署任务"},
            access_token=token,
        )
        return True


# ========== 工厂函数 ==========


# 单例缓存
_provider_instance: ESignProvider | None = None


def get_esign_provider() -> ESignProvider:
    """
    获取电子签章提供商实例

    根据环境变量 ESIGN_PROVIDER 决定使用哪个提供商：
    - "mock" (默认): 开发/测试用 Mock 实现
    - "esignbao": e签宝
    - "fadada": 法大大

    Returns:
        ESignProvider 实例
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    provider_name = os.getenv("ESIGN_PROVIDER", "mock").lower()
    if settings.ENVIRONMENT.lower() in {"production", "staging"} and provider_name == "mock":
        raise ESignProviderConfigError("staging/production 环境必须配置真实 ESIGN_PROVIDER，禁止使用 Mock 电子签章渠道。")

    if provider_name == "esignbao":
        _provider_instance = ESignBaoProvider()
        logger.info("电子签章提供商: e签宝")
    elif provider_name == "fadada":
        _provider_instance = FaDaDaProvider()
        logger.info("电子签章提供商: 法大大")
    elif provider_name == "mock":
        _provider_instance = MockESignProvider()
        logger.info("电子签章提供商: Mock（开发模式）")
    else:
        raise ESignProviderConfigError(f"未知电子签章渠道 '{provider_name}'，请配置 esignbao 或 fadada。")

    return _provider_instance


def reset_esign_provider() -> None:
    """重置提供商实例（用于测试）"""
    global _provider_instance
    _provider_instance = None
