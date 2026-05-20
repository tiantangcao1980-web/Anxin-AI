"""
证据分析与多模态处理智能体
"""

from typing import Any

from src.agents._prompt_safety import USER_INPUT_BOUNDARY, wrap_user_input
from src.agents.base import AgentConfig, AgentResponse, BaseLegalAgent
from src.prompts import load_prompt

_FALLBACK_PROMPT = "你是一位专业的证据分析专家与多模态数据处理专员。"


class EvidenceAnalystAgent(BaseLegalAgent):
    """证据分析与多模态处理智能体"""

    def __init__(self) -> None:
        config = AgentConfig(
            name="证据分析Agent",
            role="取证分析师",
            description="处理文本、图片、音视频等多模态证据，分析关联性与证明力",
            system_prompt=load_prompt("agents/evidence_analyst.txt", fallback=_FALLBACK_PROMPT),
            tools=["ocr_tool", "asr_tool", "image_analysis", "entity_extraction"],
        )
        super().__init__(config)

    async def process(self, task: dict[str, Any]) -> AgentResponse:
        """处理证据分析任务"""
        # 任务描述
        description = task.get("description", "")
        # 输入数据列表，包含类型和内容/路径
        evidence_files = task.get("context", {}).get("evidence_files", [])

        # 1. 模拟多模态预处理（实际项目中这里会调用 OCR/ASR 服务）
        processed_content = []
        for file in evidence_files:
            file_type = file.get("type", "text")
            content = file.get("content", "")
            name = file.get("name", "未命名文件")

            extracted_text = ""
            if file_type in ["image", "scan", "pdf_image"]:
                extracted_text = (
                    f"【模拟OCR结果 - {name}】\n(此处通过OCR提取了图片中的文字...)\n"
                    + (content if isinstance(content, str) else "内容摘要...")
                )
            elif file_type in ["audio", "video"]:
                extracted_text = (
                    f"【模拟ASR转录 - {name}】\n(此处通过ASR提取了音视频中的对话...)\n"
                    + (content if isinstance(content, str) else "对话摘要...")
                )
            else:
                extracted_text = f"【文本证据 - {name}】\n{content}"

            processed_content.append(extracted_text)

        combined_evidence_text = "\n\n".join(processed_content)

        prompt = f"""
请对以下多模态证据材料进行分析：

任务目标：{wrap_user_input(description, label='description')}

证据材料内容（包含预处理后的文本）：
{combined_evidence_text}

请提供：
1. **证据内容摘要**：梳理每个证据的核心信息。
2. **三性评估**：分析证据的真实性、合法性、关联性。
3. **关联分析**：不同证据之间是否存在相互印证或矛盾之处？
4. **证据链构建**：这些证据组合起来证明了什么法律事实？
5. **补强建议**：目前证据链是否存在缺口？需要补充什么类型的证据（如：只有录音孤证，建议补充聊天记录或转账凭证）？
"""

        # 调用Agent
        response = await self.chat(prompt)

        return AgentResponse(
            agent_name=self.name,
            content=response,
            reasoning="基于证据规则与逻辑推理",
            actions=[{"type": "evidence_processing", "description": "多模态证据处理与分析完成"}],
        )
