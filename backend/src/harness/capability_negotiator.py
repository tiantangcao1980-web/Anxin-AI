"""
多端能力协商器

桌面端切换运行模式（cloud/hybrid/top-secret）时：
1. 自动评估本地 LLM 能力（模型大小 → 可处理任务范围）
2. 自动裁剪工具集（top-secret 模式下不可用的工具）
3. 通知用户哪些功能不可用
4. 生成当前模式下的能力清单
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger


class AppMode(str, Enum):
    """应用运行模式（与 Tauri tauri-bridge.ts 对齐）"""
    CLOUD = "cloud"              # 全云端，完整功能
    HYBRID = "hybrid"            # 混合模式，本地缓存 + 云端回退
    TOP_SECRET = "top_secret"    # 纯本地，敏感数据不出本机


class PlatformType(str, Enum):
    """平台类型"""
    WEB = "web"
    DESKTOP = "desktop"
    MOBILE = "mobile"
    MINI_PROGRAM = "mini_program"


@dataclass
class LocalLLMCapability:
    """本地 LLM 能力描述"""
    provider: str         # ollama / vllm / localai / lmstudio
    model_name: str       # qwen2.5:7b
    model_size_b: float   # 参数量（十亿）
    vram_gb: float        # 显存需求
    context_window: int   # 上下文窗口
    supports_tools: bool  # 是否支持 tool calling
    supports_chinese: bool  # 是否支持中文

    @property
    def tier(self) -> str:
        """能力等级"""
        if self.model_size_b >= 30:
            return "high"      # 34B+ 深度法律分析
        elif self.model_size_b >= 10:
            return "medium"    # 14B-30B 标准法律任务
        else:
            return "basic"     # 7B-9B 简单问答和检索


# ===== 模式对应能力矩阵 =====
# A1 (2026-05-14): 在原本的 infrastructure capability 基础上, 追加 user-facing
# feature key (lawyer_matching / sentiment_monitor / ...), 让前端 ModeGate
# 直接传入这些 key 做 capability 协商, 不再硬编码.
MODE_CAPABILITIES = {
    AppMode.CLOUD: {
        # ---- infrastructure capabilities ----
        "full_agent_orchestration": True,
        "knowledge_graph": True,
        "vector_search": True,
        "web_crawling": True,
        "real_time_collaboration": True,
        "audio_video_call": True,
        "multi_agent_consensus": True,
        "deep_research": True,
        "document_export": True,
        "push_notification": True,
        # ---- A1: user-facing features (ModeGate 调用方一致命名) ----
        "lawyer_matching": True,        # 找律师 (需要后端律师库 + 实时网络)
        "sentiment_monitor": True,      # 舆情监测 (需要爬虫 + ES 检索)
        "due_diligence": True,          # 企业尽调 (需要工商接口)
        "im_messaging": True,           # 即时通讯 (需要 IM 网关)
        "case_market": True,            # 案源市场 (需要中心化撮合)
        "legal_knowledge_base": True,   # 法律智库 (本地或云端均可, 此处默认全开)
    },
    AppMode.HYBRID: {
        "full_agent_orchestration": True,   # 云端回退
        "knowledge_graph": True,             # 云端
        "vector_search": True,               # 本地缓存 + 云端
        "web_crawling": True,                # 云端
        "real_time_collaboration": True,     # 需要网络
        "audio_video_call": True,            # 需要网络
        "multi_agent_consensus": True,       # 云端
        "deep_research": True,               # 云端
        "document_export": True,             # 本地
        "push_notification": True,
        "lawyer_matching": True,
        "sentiment_monitor": True,
        "due_diligence": True,
        "im_messaging": True,
        "case_market": True,
        "legal_knowledge_base": True,
    },
    AppMode.TOP_SECRET: {
        "full_agent_orchestration": False,  # 仅本地单 Agent
        "knowledge_graph": False,            # 需要 Neo4j 云端
        "vector_search": False,              # 需要 Qdrant 云端
        "web_crawling": False,               # 不允许外网
        "real_time_collaboration": False,    # 不允许网络
        "audio_video_call": False,           # 不允许网络
        "multi_agent_consensus": False,      # 需要多次 LLM 调用
        "deep_research": False,              # 需要外部数据
        "document_export": True,             # 本地可用
        "push_notification": False,
        # ---- user-facing features 在 TOP_SECRET (本地) 下默认关闭 ----
        "lawyer_matching": False,       # 需要云端律师库
        "sentiment_monitor": False,     # 需要外网爬虫
        "due_diligence": False,         # 需要工商外网接口
        "im_messaging": False,          # 需要 IM 网关
        "case_market": False,           # 需要中心化撮合
        "legal_knowledge_base": True,   # 法律智库本地包可用
    },
}

# 平台基础能力
PLATFORM_CAPABILITIES = {
    PlatformType.WEB: {
        "local_llm": False,
        "offline_mode": False,
        "file_system_access": False,  # 仅上传
        "biometric_auth": False,
        "system_tray": False,
        "push_notification": True,    # 浏览器通知
    },
    PlatformType.DESKTOP: {
        "local_llm": True,
        "offline_mode": True,
        "file_system_access": True,
        "biometric_auth": True,       # Touch/Face ID via Tauri
        "system_tray": True,
        "push_notification": True,
    },
    PlatformType.MOBILE: {
        "local_llm": False,
        "offline_mode": False,        # 有限缓存
        "file_system_access": False,  # 仅拍照/相册
        "biometric_auth": True,
        "system_tray": False,
        "push_notification": True,
    },
    PlatformType.MINI_PROGRAM: {
        "local_llm": False,
        "offline_mode": False,
        "file_system_access": False,
        "biometric_auth": False,
        "system_tray": False,
        "push_notification": False,   # 仅订阅消息
    },
}

# 本地 LLM 能力对应可处理的任务
LLM_TIER_TASKS = {
    "high": [
        "contract_review", "document_drafting", "legal_research",
        "risk_assessment", "compliance_check", "general_consultation",
    ],
    "medium": [
        "contract_review", "document_drafting", "general_consultation",
        "simple_research",
    ],
    "basic": [
        "general_consultation", "simple_qa", "document_summary",
    ],
}


@dataclass
class NegotiationResult:
    """能力协商结果"""
    platform: PlatformType
    mode: AppMode
    available_features: dict[str, bool]
    unavailable_features: list[str]
    available_tasks: list[str]
    local_llm: LocalLLMCapability | None = None
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class CapabilityNegotiator:
    """
    多端能力协商器

    根据平台类型、运行模式和本地硬件能力，
    生成当前环境下的可用功能清单。
    """

    def negotiate(
        self,
        platform: PlatformType,
        mode: AppMode = AppMode.CLOUD,
        local_llm: LocalLLMCapability | None = None,
    ) -> NegotiationResult:
        """
        执行能力协商

        Args:
            platform: 平台类型
            mode: 运行模式
            local_llm: 本地 LLM 能力（仅桌面端）

        Returns:
            NegotiationResult 包含可用功能、不可用功能、建议
        """
        # 合并模式能力 + 平台能力
        mode_caps = MODE_CAPABILITIES.get(mode, {})
        platform_caps = PLATFORM_CAPABILITIES.get(platform, {})

        available = {}
        unavailable = []
        warnings = []
        recommendations = []

        # 合并：取交集
        all_features = set(list(mode_caps.keys()) + list(platform_caps.keys()))
        for feature in all_features:
            mode_ok = mode_caps.get(feature, True)
            platform_ok = platform_caps.get(feature, True)
            available[feature] = mode_ok and platform_ok
            if not available[feature]:
                unavailable.append(feature)

        # Top-Secret 模式特殊处理
        if mode == AppMode.TOP_SECRET:
            if not local_llm:
                warnings.append("涉密模式下未检测到本地 LLM，AI 功能将不可用")
                recommendations.append("请安装 Ollama 并下载推荐模型：ollama pull qwen2.5:7b")
            elif local_llm.tier == "basic":
                warnings.append(f"本地模型 {local_llm.model_name} 能力有限，仅支持简单问答")
                recommendations.append("建议升级到 14B+ 模型以支持合同审阅等复杂任务")

        # 推断可处理的任务
        if mode == AppMode.TOP_SECRET and local_llm:
            available_tasks = LLM_TIER_TASKS.get(local_llm.tier, [])
        elif mode == AppMode.TOP_SECRET:
            available_tasks = []
        else:
            available_tasks = LLM_TIER_TASKS["high"]  # 云端全功能

        # 移动端和小程序的建议
        if platform == PlatformType.MOBILE:
            recommendations.append("移动端建议使用拍照识别合同功能，复杂分析请使用桌面端")
        elif platform == PlatformType.MINI_PROGRAM:
            recommendations.append("小程序功能精简，完整功能请使用 Web 端或桌面端")

        result = NegotiationResult(
            platform=platform,
            mode=mode,
            available_features=available,
            unavailable_features=unavailable,
            available_tasks=available_tasks,
            local_llm=local_llm,
            warnings=warnings,
            recommendations=recommendations,
        )

        logger.info(
            f"[CapabilityNegotiator] {platform.value}/{mode.value} | "
            f"可用: {sum(available.values())}/{len(available)} | "
            f"任务: {len(available_tasks)} | "
            f"警告: {len(warnings)}"
        )

        return result

    def get_degradation_notice(
        self,
        from_mode: AppMode,
        to_mode: AppMode,
        platform: PlatformType = PlatformType.DESKTOP,
    ) -> dict[str, Any]:
        """
        模式切换时生成降级通知

        Returns:
            包含新增不可用功能和建议的字典
        """
        from_caps = MODE_CAPABILITIES.get(from_mode, {})
        to_caps = MODE_CAPABILITIES.get(to_mode, {})

        lost_features = [
            feature for feature, available in from_caps.items()
            if available and not to_caps.get(feature, True)
        ]
        gained_features = [
            feature for feature, available in to_caps.items()
            if available and not from_caps.get(feature, True)
        ]

        return {
            "from_mode": from_mode.value,
            "to_mode": to_mode.value,
            "lost_features": lost_features,
            "gained_features": gained_features,
            "warning": f"切换到{to_mode.value}模式后，{len(lost_features)}个功能将不可用" if lost_features else None,
        }


# 全局单例
capability_negotiator = CapabilityNegotiator()
