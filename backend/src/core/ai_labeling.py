"""
AI内容标识服务

依据：
- 《人工智能生成合成内容标识办法》(2025年9月1日施行)
- GB 45438-2025 《网络安全技术 人工智能生成合成内容标识方法》
- 《生成式人工智能服务管理暂行办法》

标识要求：
1. 显式标识：在AI生成的文本、文档中添加可见的标识信息
2. 隐式标识：在文件元数据中嵌入AI生成标识（水印）
3. 交互标识：在用户界面中明确标注AI生成内容
"""

import hashlib
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class AIContentType(str, Enum):
    """AI内容类型"""
    TEXT = "text"                # 文本（对话、咨询回复）
    DOCUMENT = "document"       # 文档（合同、文书）
    ANALYSIS = "analysis"       # 分析报告（审查、尽调）
    SUGGESTION = "suggestion"   # 建议（修改建议、法律意见）


class AILabelingService:
    """
    AI内容标识服务

    根据GB 45438-2025标准实施三级标识：
    - Level 1: 显式文本标识（用户可见的声明）
    - Level 2: 元数据标识（文件属性中的标识信息）
    - Level 3: 隐式水印（不影响内容呈现的嵌入式标识）
    """

    # 平台标识信息
    PLATFORM_NAME = "安心AI法务"
    PLATFORM_VERSION = "1.0"
    PROVIDER_NAME = "安心智能科技"

    # 显式标识模板
    LABEL_TEMPLATES = {
        AIContentType.TEXT: "本内容由AI辅助生成，仅供参考，不构成法律意见。如需专业法律服务，请咨询执业律师。",
        AIContentType.DOCUMENT: "本文书由AI辅助起草，使用前请由专业律师审核确认。",
        AIContentType.ANALYSIS: "本分析报告由AI辅助生成，分析结论仅供参考，请结合实际情况综合判断。",
        AIContentType.SUGGESTION: "本建议由AI辅助生成，具体实施方案请咨询专业律师。",
    }

    # 简短标识（用于消息气泡等紧凑场景）
    SHORT_LABELS = {
        AIContentType.TEXT: "AI辅助生成 · 仅供参考",
        AIContentType.DOCUMENT: "AI辅助起草 · 请专业审核",
        AIContentType.ANALYSIS: "AI辅助分析 · 仅供参考",
        AIContentType.SUGGESTION: "AI辅助建议 · 仅供参考",
    }

    @classmethod
    def get_display_label(
        cls,
        content_type: AIContentType = AIContentType.TEXT,
        short: bool = False,
    ) -> str:
        """获取显式标识文本（Level 1）"""
        if short:
            return cls.SHORT_LABELS.get(content_type, cls.SHORT_LABELS[AIContentType.TEXT])
        return cls.LABEL_TEMPLATES.get(content_type, cls.LABEL_TEMPLATES[AIContentType.TEXT])

    @classmethod
    def get_metadata_label(
        cls,
        content_type: AIContentType = AIContentType.TEXT,
        model_name: str | None = None,
        agent_name: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """
        生成元数据标识（Level 2）

        符合GB 45438-2025要求的结构化元数据
        """
        now = datetime.now(UTC).isoformat()

        metadata = {
            "ai_generated": True,
            "ai_label_version": "GB45438-2025",
            "platform": {
                "name": cls.PLATFORM_NAME,
                "version": cls.PLATFORM_VERSION,
                "provider": cls.PROVIDER_NAME,
            },
            "generation": {
                "type": content_type.value,
                "timestamp": now,
                "model": model_name or "unknown",
                "agent": agent_name,
                "task_id": task_id,
            },
            "disclaimer": cls.LABEL_TEMPLATES.get(content_type, ""),
        }

        return metadata

    @classmethod
    def generate_content_hash(cls, content: str) -> str:
        """
        生成内容指纹（Level 3 辅助）

        用于验证AI生成内容的完整性和溯源
        """
        payload = f"{cls.PLATFORM_NAME}:{content}:{datetime.now(UTC).date().isoformat()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def wrap_streaming_metadata(
        cls,
        content_type: AIContentType = AIContentType.TEXT,
        model_name: str | None = None,
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        """
        生成流式输出的元数据包装

        用于SSE流式响应的首个和末尾事件
        """
        return {
            "type": "ai_label",
            "data": {
                "ai_generated": True,
                "label": cls.get_display_label(content_type, short=True),
                "full_disclaimer": cls.get_display_label(content_type, short=False),
                "model": model_name,
                "agent": agent_name,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        }

    @classmethod
    def get_document_footer(
        cls,
        content_type: AIContentType = AIContentType.DOCUMENT,
    ) -> str:
        """
        获取文档页脚标识文本

        用于DOCX/PDF导出时添加到页脚
        """
        now = datetime.now().strftime("%Y年%m月%d日")
        return (
            f"{'─' * 40}\n"
            f"声明：{cls.LABEL_TEMPLATES[content_type]}\n"
            f"生成平台：{cls.PLATFORM_NAME} | 生成日期：{now}\n"
            f"依据：GB 45438-2025《网络安全技术 人工智能生成合成内容标识方法》"
        )

    @classmethod
    def get_export_metadata(
        cls,
        content_type: AIContentType = AIContentType.DOCUMENT,
        model_name: str | None = None,
    ) -> dict[str, str]:
        """
        获取文档导出属性元数据

        用于设置DOCX/PDF文件属性
        """
        return {
            "creator": cls.PLATFORM_NAME,
            "producer": f"{cls.PLATFORM_NAME} v{cls.PLATFORM_VERSION}",
            "subject": f"AI辅助生成 - {content_type.value}",
            "keywords": "AI生成,法律文书,安心AI法务",
            "comments": cls.LABEL_TEMPLATES.get(content_type, ""),
            "category": "AI辅助生成内容",
            "ai_model": model_name or "",
        }
