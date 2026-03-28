"""
需求分析引导智能体 (Requirement Analyst Agent)

职责：
1. 分析用户输入的完整度（主体、诉求、背景、文件是否齐全）
2. 输出结构化需求摘要
3. 当关键要素缺失时生成引导问题
4. 在 Coordinator 之前运行，确保任务描述充分
"""

from typing import Any, Dict, Optional
from loguru import logger
import json
import re

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse


REQUIREMENT_ANALYST_PROMPT = """你是一位专业的法务需求分析师。你的任务是快速分析用户的法律需求输入，
判断需求是否完整，并输出结构化的需求摘要。

### 分析维度
1. **核心诉求**：用户想要解决什么问题？
2. **涉及主体**：谁是当事人？对方是谁？
3. **关键事实**：发生了什么事？时间、地点、金额等关键信息
4. **法律领域**：属于合同法、劳动法、知识产权、公司法、诉讼等哪个领域
5. **期望结果**：用户希望得到什么（咨询意见/文书起草/风险评估/诉讼策略）
6. **附件材料**：是否提供了合同文本、证据材料等

### 输出要求

请严格输出以下 JSON 格式：
{
  "is_complete": true/false,
  "completeness_score": 0.0-1.0,
  "summary": "一句话需求摘要",
  "elements": {
    "core_demand": "核心诉求描述",
    "parties": "涉及主体",
    "key_facts": "关键事实",
    "legal_area": "法律领域",
    "expected_outcome": "期望结果",
    "has_attachments": false
  },
  "missing_elements": ["缺失要素1", "缺失要素2"],
  "guidance_questions": [
    {
      "question": "引导问题",
      "options": ["选项A", "选项B", "选项C"],
      "purpose": "补充什么信息"
    }
  ],
  "suggested_agents": ["legal_advisor", "contract_reviewer"],
  "complexity": "simple" | "moderate" | "complex"
}

注意：
- 如果 completeness_score >= 0.7，设置 is_complete = true，不生成 guidance_questions
- 如果 completeness_score < 0.7，生成 2-3 个引导问题帮助用户补充信息
- guidance_questions 的 options 应该是具体可选的答案，不是开放式问题
- 简单问答（如"什么是不可抗力"）直接标记为 complete，不需要追问
"""


class RequirementAnalystAgent(BaseLegalAgent):
    """需求分析引导智能体"""
    
    def __init__(self):
        config = AgentConfig(
            name="需求分析Agent",
            role="需求分析师",
            description="分析用户输入的完整度，引导用户补充关键信息",
            system_prompt=REQUIREMENT_ANALYST_PROMPT,
            temperature=0.2,
        )
        super().__init__(config)
    
    async def process(self, task: Dict[str, Any]) -> AgentResponse:
        """处理需求分析任务"""
        description = task.get("description", "")
        context = task.get("context", {})
        
        prompt = f"用户输入：{description}"
        
        if context.get("has_attachments"):
            prompt += "\n\n[注意：用户已上传附件文件]"
        
        llm_config = context.get("llm_config") or task.get("llm_config")
        response = await self.chat(prompt, llm_config=llm_config)
        
        parsed = self._parse_json(response)
        
        return AgentResponse(
            agent_name=self.name,
            content=parsed.get("summary", response),
            metadata=parsed,
        )
    
    async def analyze_requirement(
        self,
        user_input: str,
        has_attachments: bool = False,
        llm_config: Any = None,
    ) -> Dict[str, Any]:
        """
        快速分析需求完整度
        
        Returns:
            结构化需求分析结果，包含 is_complete、summary、guidance_questions 等
        """
        prompt = f"用户输入：{user_input}"
        if has_attachments:
            prompt += "\n\n[注意：用户已上传附件文件]"
        
        try:
            response = await self.chat(prompt, llm_config=llm_config)
            result = self._parse_json(response)
            
            # 确保必需字段存在
            if not result:
                return self._fallback_analysis(user_input)
            
            result.setdefault("is_complete", True)
            result.setdefault("completeness_score", 0.8)
            result.setdefault("summary", user_input[:100])
            result.setdefault("missing_elements", [])
            result.setdefault("guidance_questions", [])
            result.setdefault("complexity", "simple")
            result.setdefault("suggested_agents", ["legal_advisor"])
            
            return result
            
        except Exception as e:
            logger.warning(f"需求分析失败: {e}")
            return self._fallback_analysis(user_input)
    
    def _fallback_analysis(self, user_input: str) -> Dict[str, Any]:
        """兜底分析（规则引擎）"""
        # 简单关键词判断复杂度
        complex_keywords = ["起诉", "仲裁", "尽职调查", "并购", "股权"]
        moderate_keywords = ["合同", "审查", "起草", "风险", "协议", "文书"]
        
        complexity = "simple"
        if any(kw in user_input for kw in complex_keywords):
            complexity = "complex"
        elif any(kw in user_input for kw in moderate_keywords):
            complexity = "moderate"
        
        is_complete = len(user_input) > 20 or complexity == "simple"
        
        return {
            "is_complete": is_complete,
            "completeness_score": 0.8 if is_complete else 0.4,
            "summary": user_input[:100],
            "elements": {
                "core_demand": user_input[:200],
                "parties": "",
                "key_facts": "",
                "legal_area": "通用",
                "expected_outcome": "",
                "has_attachments": False,
            },
            "missing_elements": [] if is_complete else ["详细描述"],
            "guidance_questions": [],
            "suggested_agents": ["legal_advisor"],
            "complexity": complexity,
        }
    
    def _parse_json(self, text: str) -> Dict[str, Any]:
        """解析 JSON"""
        if not text:
            return {}
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            match = re.search(r'(\{.*\})', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except (json.JSONDecodeError, TypeError):
                    pass
        return {}
