"""
LLM配置模型
定义大模型配置的数据库模型和默认配置
"""

from typing import Optional, Dict, Any
from sqlalchemy import String, Boolean, Integer, Float, Text, JSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column
import enum

from src.models.base import Base, TimestampMixin, GUID


class LLMProvider(str, enum.Enum):
    """LLM提供商枚举"""
    # 国际大模型
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENROUTE = "openroute"
    
    # 国内大模型
    DEEPSEEK = "deepseek"
    QWEN = "qwen"  # 通义千问
    GLM = "glm"  # 智谱AI
    MINIMAX = "minimax"
    MOONSHOT = "moonshot"  # 月之暗面 Kimi
    BAICHUAN = "baichuan"  # 百川
    SPARKDESK = "sparkdesk"  # 讯飞星火
    ERNIE = "ernie"  # 文心一言
    HUNYUAN = "hunyuan"  # 腾讯混元
    DOUBAO = "doubao"  # 字节跳动豆包
    STEPFUN = "stepfun"  # 阶跃星辰
    YI = "yi"  # 零一万物
    
    # 本地/开源模型
    OLLAMA = "ollama"
    LOCALAI = "localai"
    LLAMACPP = "llamacpp"
    VLLM = "vllm"
    XINFERENCE = "xinference"
    CUSTOM = "custom"  # 自定义OpenAI兼容接口


class LLMConfigType(str, enum.Enum):
    """配置类型"""
    LLM = "llm"  # 大语言模型
    EMBEDDING = "embedding"  # 向量模型
    RERANKER = "reranker"  # 重排序模型


class LLMConfig(Base, TimestampMixin):
    """LLM配置表"""
    __tablename__ = "llm_configs"
    
    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="配置名称")
    provider: Mapped[str] = mapped_column(String(50), nullable=False, comment="提供商")
    config_type: Mapped[str] = mapped_column(String(20), default="llm", comment="配置类型: llm/embedding/reranker")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="描述信息")
    
    # API配置
    api_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="API密钥(加密存储)")
    api_base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="API基础URL")
    api_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="API版本")
    
    # 模型参数
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="模型名称")
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="模型版本")
    
    # 生成参数
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096, comment="最大token数")
    temperature: Mapped[float] = mapped_column(Float, default=0.7, comment="温度参数")
    top_p: Mapped[Optional[float]] = mapped_column(Float, default=1.0, nullable=True, comment="Top-P采样")
    top_k: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Top-K采样")
    frequency_penalty: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True, comment="频率惩罚")
    presence_penalty: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True, comment="存在惩罚")
    
    # 本地模型参数
    local_endpoint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="本地服务端点")
    local_model_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True, comment="本地模型路径")
    gpu_layers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="GPU层数")
    context_length: Mapped[Optional[int]] = mapped_column(Integer, default=4096, nullable=True, comment="上下文长度")
    
    # 高级配置
    extra_params: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict, nullable=True, comment="额外参数")
    headers: Mapped[Optional[Dict[str, str]]] = mapped_column(JSONB, default=dict, nullable=True, comment="自定义请求头")
    
    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为默认配置")
    priority: Mapped[int] = mapped_column(Integer, default=0, comment="优先级")
    
    # 统计信息
    total_calls: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True, comment="总调用次数")
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True, comment="总消耗token数")
    avg_latency: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="平均延迟(ms)")
    
    # 多租户
    org_id: Mapped[Optional[str]] = mapped_column(GUID(), nullable=True, comment="组织ID")
    
    def __repr__(self):
        return f"<LLMConfig {self.name} ({self.provider}/{self.model_name})>"


# 预定义的提供商配置模板
LLM_PROVIDER_CONFIGS = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": {
            "llm": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "o1-preview", "o1-mini"],
            "embedding": ["text-embedding-3-large", "text-embedding-3-small", "text-embedding-ada-002"]
        },
        "supports_streaming": True,
        "api_key_required": True
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "base_url": "https://api.anthropic.com/v1",
        "models": {
            "llm": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
        },
        "supports_streaming": True,
        "api_key_required": True
    },
    "google": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "models": {
            "llm": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-pro-002", "gemini-1.5-flash-002"]
        },
        "supports_streaming": True,
        "api_key_required": True,
        "openai_compatible": True
    },
    "openroute": {
        "name": "OpenRoute",
        "base_url": "https://openrouter.ai/api/v1",
        "models": {
            "llm": ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "google/gemini-pro-1.5", "meta-llama/llama-3.1-405b-instruct", "mistral/mistral-large"]
        },
        "supports_streaming": True,
        "api_key_required": True,
        "openai_compatible": True
    },
    "deepseek": {
        "name": "DeepSeek (深度求索)",
        "base_url": "https://api.deepseek.com/v1",
        "models": {
            "llm": ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"]
        },
        "supports_streaming": True,
        "api_key_required": True,
        "openai_compatible": True
    },
    "qwen": {
        "name": "通义千问 (Qwen)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": {
            "llm": ["qwen-max", "qwen-plus", "qwen-turbo", "qwen-long", "qwen-vl-max", "qwen-vl-plus", "qwen2.5-72b-instruct", "qwen2.5-coder-32b-instruct"],
            "embedding": ["text-embedding-v3", "text-embedding-v2"]
        },
        "supports_streaming": True,
        "api_key_required": True,
        "openai_compatible": True
    },
    "glm": {
        "name": "智谱AI (GLM)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": {
            "llm": ["glm-4-plus", "glm-4-air", "glm-4-flash", "glm-4-0520", "glm-4-long", "glm-4v-plus"],
            "embedding": ["embedding-3", "embedding-2"]
        },
        "supports_streaming": True,
        "api_key_required": True,
        "openai_compatible": True
    },
    "minimax": {
        "name": "Minimax",
        "base_url": "https://api.minimax.chat/v1",
        "models": {
            "llm": ["abab7-chat", "abab6.5s-chat", "abab6.5g-chat", "abab5.5s-chat"]
        },
        "supports_streaming": True,
        "api_key_required": True,
        "extra_headers": {"Content-Type": "application/json"},
        "openai_compatible": True
    },
    "moonshot": {
        "name": "月之暗面 (Kimi)",
        "base_url": "https://api.moonshot.cn/v1",
        "models": {
            "llm": [
                "kimi-k2",
                "kimi-k2.5",
                "kimi-k2-thinking",
                "moonshot-v1-auto",
                "moonshot-v1-8k",
                "moonshot-v1-32k",
                "moonshot-v1-128k",
            ]
        },
        "supports_streaming": True,
        "api_key_required": True,
        "openai_compatible": True
    },
    "baichuan": {
        "name": "百川智能",
        "base_url": "https://api.baichuan-ai.com/v1",
        "models": {
            "llm": ["Baichuan4", "Baichuan3-Turbo", "Baichuan2-Turbo"]
        },
        "supports_streaming": True,
        "api_key_required": True,
        "openai_compatible": True
    },
    "sparkdesk": {
        "name": "讯飞星火",
        "base_url": "https://spark-api-open.xf-yun.com/v1",
        "models": {
            "llm": ["generalv3.5", "4.0Ultra"]
        },
        "supports_streaming": True,
        "api_key_required": True,
        "note": "需要配置 APIKey:APISecret 格式"
    },
    "ernie": {
        "name": "文心一言 (Ernie)",
        "base_url": "https://aip.baidubce.com",
        "models": {
            "llm": ["ernie-4.0-8k", "ernie-3.5-8k", "ernie-speed-128k", "ernie-lite-8k"],
            "embedding": ["bge-large-zh", "bge-large-en"]
        },
        "supports_streaming": True,
        "api_key_required": True,
        "note": "需要 Access Token"
    },
    "hunyuan": {
        "name": "腾讯混元",
        "base_url": "https://hunyuan.tencentcloudapi.com",
        "models": {
            "llm": ["hunyuan-pro", "hunyuan-standard", "hunyuan-lite"]
        },
        "supports_streaming": True,
        "api_key_required": True,
        "note": "需要 SecretId 和 SecretKey"
    },
    "doubao": {
        "name": "字节豆包 (Doubao)",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "models": {
            "llm": ["doubao-pro-32k", "doubao-lite-32k", "doubao-pro-128k"]
        },
        "supports_streaming": True,
        "api_key_required": True,
        "openai_compatible": True
    },
    "stepfun": {
        "name": "阶跃星辰",
        "base_url": "https://api.stepfun.com/v1",
        "models": {
            "llm": ["step-2-16k", "step-1-256k", "step-1-8k", "step-1v-32k"]
        },
        "supports_streaming": True,
        "api_key_required": True,
        "openai_compatible": True
    },
    "yi": {
        "name": "零一万物 (Yi)",
        "base_url": "https://api.lingyiwanwu.com/v1",
        "models": {
            "llm": ["yi-lightning", "yi-large", "yi-medium", "yi-vision"]
        },
        "supports_streaming": True,
        "api_key_required": True,
        "openai_compatible": True
    },
    "ollama": {
        "name": "Ollama (本地)",
        "base_url": "http://localhost:11434/v1",
        "models": {
            "llm": ["llama3.2", "llama3.1", "qwen2.5", "deepseek-r1", "mistral", "gemma2"],
            "embedding": ["nomic-embed-text", "mxbai-embed-large"]
        },
        "supports_streaming": True,
        "api_key_required": False,
        "is_local": True,
        "openai_compatible": True
    },
    "localai": {
        "name": "LocalAI (本地)",
        "base_url": "http://localhost:8080/v1",
        "models": {
            "llm": ["gpt-3.5-turbo", "gpt-4"],
            "embedding": ["text-embedding-ada-002"]
        },
        "supports_streaming": True,
        "api_key_required": False,
        "is_local": True,
        "openai_compatible": True
    },
    "llamacpp": {
        "name": "llama.cpp Server (本地)",
        "base_url": "http://localhost:8080/v1",
        "models": {
            "llm": []
        },
        "supports_streaming": True,
        "api_key_required": False,
        "is_local": True,
        "openai_compatible": True,
        "note": "需要启动 llama.cpp server"
    },
    "vllm": {
        "name": "vLLM (本地)",
        "base_url": "http://localhost:8000/v1",
        "models": {
            "llm": []
        },
        "supports_streaming": True,
        "api_key_required": False,
        "is_local": True,
        "openai_compatible": True,
        "note": "高性能推理服务器"
    },
    "xinference": {
        "name": "Xinference (本地)",
        "base_url": "http://localhost:9997/v1",
        "models": {
            "llm": [],
            "embedding": []
        },
        "supports_streaming": True,
        "api_key_required": False,
        "is_local": True,
        "openai_compatible": True,
        "note": "支持多种开源模型"
    },
    "custom": {
        "name": "自定义 (OpenAI兼容)",
        "base_url": "",
        "models": {
            "llm": [],
            "embedding": []
        },
        "supports_streaming": True,
        "api_key_required": False,
        "is_local": False,
        "openai_compatible": True,
        "note": "兼容 OpenAI 格式的 API 服务"
    }
}
