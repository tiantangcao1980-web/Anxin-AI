# -*- coding: utf-8 -*-
"""
电子签章服务 - 提供商无关接口

支持对接 e签宝、法大大等第三方电子签章平台。
通过工厂函数 get_esign_provider() 根据环境变量选择具体实现。
开发/测试环境默认使用 MockESignProvider。
"""

import os
import uuid
import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from loguru import logger


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
    id_number: Optional[str] = Field(None, description="身份证号/统一社会信用代码")
    mobile: Optional[str] = Field(None, description="手机号码")
    email: Optional[str] = Field(None, description="邮箱")
    sign_type: SignType = Field(default=SignType.PERSONAL, description="签署类型")
    sign_order: int = Field(default=0, description="签署顺序，0 表示不限顺序")


class SignerStatusInfo(BaseModel):
    """签署人状态信息"""
    signer_id: str
    name: str
    sign_type: SignType
    status: SignerStatus = SignerStatus.PENDING
    signed_at: Optional[datetime] = None
    reject_reason: Optional[str] = None


class SignFlowResult(BaseModel):
    """创建签署流程结果"""
    flow_id: str
    contract_id: str
    sign_urls: dict[str, str] = Field(default_factory=dict, description="signer_id -> sign_url")
    status: FlowStatus = FlowStatus.CREATED
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


class SignFlowStatus(BaseModel):
    """签署流程状态详情"""
    flow_id: str
    contract_id: str
    status: FlowStatus
    signers_status: list[SignerStatusInfo] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ========== 抽象接口 ==========


class ESignProvider(ABC):
    """电子签章提供商抽象接口"""

    @abstractmethod
    async def create_sign_flow(
        self,
        contract_id: str,
        title: str,
        signers: list[SignerInfo],
        document_url: Optional[str] = None,
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

    def __init__(self):
        # 内存存储，仅用于开发
        self._flows: dict[str, dict] = {}

    async def create_sign_flow(
        self,
        contract_id: str,
        title: str,
        signers: list[SignerInfo],
        document_url: Optional[str] = None,
        expire_hours: int = 72,
    ) -> SignFlowResult:
        flow_id = f"mock_flow_{uuid.uuid4().hex[:12]}"
        now = datetime.now()

        sign_urls = {}
        signers_status = []
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
        return url

    async def get_flow_status(self, flow_id: str) -> SignFlowStatus:
        flow = self._flows.get(flow_id)
        if not flow:
            raise ValueError(f"签署流程不存在: {flow_id}")

        # Mock 逻辑：根据创建时间推进状态
        created_at = datetime.fromisoformat(flow["created_at"])
        elapsed = (datetime.now() - created_at).total_seconds()

        signers_status_list = []
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


# ========== e签宝 占位实现 ==========


class ESignBaoProvider(ESignProvider):
    """
    e签宝电子签章提供商（占位实现）

    需要配置以下环境变量才能使用：
    - ESIGN_BAO_APP_ID: 应用ID
    - ESIGN_BAO_APP_SECRET: 应用密钥
    - ESIGN_BAO_API_URL: API地址（默认沙箱）
    """

    def __init__(self):
        self.app_id = os.getenv("ESIGN_BAO_APP_ID", "")
        self.app_secret = os.getenv("ESIGN_BAO_APP_SECRET", "")
        self.api_url = os.getenv(
            "ESIGN_BAO_API_URL",
            "https://smlopenapi.esign.cn"  # 沙箱地址
        )
        if not self.app_id or not self.app_secret:
            logger.warning(
                "e签宝未配置 APP_ID / APP_SECRET，调用时将抛出异常。"
                "请在 .env 中设置 ESIGN_BAO_APP_ID 和 ESIGN_BAO_APP_SECRET。"
            )

    def _check_config(self):
        if not self.app_id or not self.app_secret:
            raise NotImplementedError(
                "e签宝集成尚未配置。请在 .env 中设置 ESIGN_BAO_APP_ID 和 ESIGN_BAO_APP_SECRET 环境变量。"
            )

    async def create_sign_flow(
        self,
        contract_id: str,
        title: str,
        signers: list[SignerInfo],
        document_url: Optional[str] = None,
        expire_hours: int = 72,
    ) -> SignFlowResult:
        self._check_config()
        # TODO: 调用 e签宝 API 创建签署流程
        # POST {api_url}/v3/sign-flow/create
        raise NotImplementedError("e签宝签署流程创建尚未实现，请联系开发团队完成对接。")

    async def get_sign_url(self, flow_id: str, signer_id: str) -> str:
        self._check_config()
        raise NotImplementedError("e签宝签署链接获取尚未实现，请联系开发团队完成对接。")

    async def get_flow_status(self, flow_id: str) -> SignFlowStatus:
        self._check_config()
        raise NotImplementedError("e签宝状态查询尚未实现，请联系开发团队完成对接。")

    async def download_signed_doc(self, flow_id: str) -> bytes:
        self._check_config()
        raise NotImplementedError("e签宝文件下载尚未实现，请联系开发团队完成对接。")

    async def cancel_flow(self, flow_id: str, reason: str = "") -> bool:
        self._check_config()
        raise NotImplementedError("e签宝流程取消尚未实现，请联系开发团队完成对接。")


# ========== 法大大 占位实现 ==========


class FaDaDaProvider(ESignProvider):
    """
    法大大电子签章提供商（占位实现）

    需要配置以下环境变量才能使用：
    - FADADA_APP_ID: 应用ID
    - FADADA_APP_SECRET: 应用密钥
    - FADADA_API_URL: API地址
    """

    def __init__(self):
        self.app_id = os.getenv("FADADA_APP_ID", "")
        self.app_secret = os.getenv("FADADA_APP_SECRET", "")
        self.api_url = os.getenv("FADADA_API_URL", "https://testapi.fadada.com")

    def _check_config(self):
        if not self.app_id or not self.app_secret:
            raise NotImplementedError(
                "法大大集成尚未配置。请在 .env 中设置 FADADA_APP_ID 和 FADADA_APP_SECRET 环境变量。"
            )

    async def create_sign_flow(self, contract_id, title, signers, document_url=None, expire_hours=72):
        self._check_config()
        raise NotImplementedError("法大大签署流程创建尚未实现，请联系开发团队完成对接。")

    async def get_sign_url(self, flow_id, signer_id):
        self._check_config()
        raise NotImplementedError("法大大签署链接获取尚未实现。")

    async def get_flow_status(self, flow_id):
        self._check_config()
        raise NotImplementedError("法大大状态查询尚未实现。")

    async def download_signed_doc(self, flow_id):
        self._check_config()
        raise NotImplementedError("法大大文件下载尚未实现。")

    async def cancel_flow(self, flow_id, reason=""):
        self._check_config()
        raise NotImplementedError("法大大流程取消尚未实现。")


# ========== 工厂函数 ==========


# 单例缓存
_provider_instance: Optional[ESignProvider] = None


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

    if provider_name == "esignbao":
        _provider_instance = ESignBaoProvider()
        logger.info("电子签章提供商: e签宝")
    elif provider_name == "fadada":
        _provider_instance = FaDaDaProvider()
        logger.info("电子签章提供商: 法大大")
    else:
        _provider_instance = MockESignProvider()
        logger.info("电子签章提供商: Mock（开发模式）")

    return _provider_instance


def reset_esign_provider():
    """重置提供商实例（用于测试）"""
    global _provider_instance
    _provider_instance = None
