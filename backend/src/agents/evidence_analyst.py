"""
证据分析与多模态处理智能体
"""

from typing import Any, Dict, List

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse


EVIDENCE_ANALYST_PROMPT = """你是一位专业的证据分析专家与多模态数据处理专员。

你的职责是：
1. **多模态证据处理**：
   - 文本：提取关键信息、实体关系、时间线。
   - 图片/扫描件：识别（OCR）文档内容、印章、手写签名，并转化为结构化文本。
   - 音频/视频：提取对话内容（ASR），识别情绪，标记关键事件时间点。
2. **证据关联性分析**：分析不同证据之间的逻辑联系，构建证据链（Evidence Chain）。
3. **证明力评估**：评估证据的真实性、合法性、关联性（三性），指出证据瑕疵。
4. **证据整理**：生成证据清单，分类归档。

处理逻辑：
- 收到非文本数据（File Token/Path）时，首先模拟调用相应的提取工具（如 OCR, ASR）获取文本内容。
- 然后对提取出的文本进行法律层面的分析。

输出要求：
1. 清晰区分“原始内容”与“分析结论”。
2. 对于多模态内容，注明来源类型（如：[录音转录]、[合同扫描件OCR]）。
3. 构建证据图谱，说明证据A如何佐证事实B。
"""


class EvidenceAnalystAgent(BaseLegalAgent):
    """证据分析与多模态处理智能体"""
    
    def __init__(self):
        config = AgentConfig(
            name="证据分析Agent",
            role="取证分析师",
            description="处理文本、图片、音视频等多模态证据，分析关联性与证明力",
            system_prompt=EVIDENCE_ANALYST_PROMPT,
            tools=["ocr_tool", "asr_tool", "image_analysis", "entity_extraction"],
        )
        super().__init__(config)
    
    async def process(self, task: Dict[str, Any]) -> AgentResponse:
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
                extracted_text = f"【模拟OCR结果 - {name}】\n(此处通过OCR提取了图片中的文字...)\n" + (content if isinstance(content, str) else "内容摘要...")
            elif file_type in ["audio", "video"]:
                extracted_text = f"【模拟ASR转录 - {name}】\n(此处通过ASR提取了音视频中的对话...)\n" + (content if isinstance(content, str) else "对话摘要...")
            else:
                extracted_text = f"【文本证据 - {name}】\n{content}"
            
            processed_content.append(extracted_text)
            
        combined_evidence_text = "\n\n".join(processed_content)
        
        prompt = f"""
请对以下多模态证据材料进行分析：

任务目标：{description}

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
            actions=[
                {"type": "evidence_processing", "description": "多模态证据处理与分析完成"}
            ]
        )
