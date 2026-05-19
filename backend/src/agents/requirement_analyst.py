"""
需求分析引导智能体 (Requirement Analyst Agent)

职责：
1. 分析用户输入的完整度（主体、诉求、背景、文件是否齐全）
2. 输出结构化需求摘要
3. 当关键要素缺失时生成引导问题
4. 在 Coordinator 之前运行，确保任务描述充分
"""

import json
import re
from typing import Any, cast

from loguru import logger

from src.agents._prompt_safety import USER_INPUT_BOUNDARY, wrap_user_input
from src.agents.base import AgentConfig, AgentResponse, BaseLegalAgent
from src.prompts import load_prompt

_FALLBACK_PROMPT = "你是一位专业的法务需求分析师，负责快速分析用户的法律需求输入。"


class RequirementAnalystAgent(BaseLegalAgent):
    """需求分析引导智能体"""

    def __init__(self) -> None:
        config = AgentConfig(
            name="需求分析Agent",
            role="需求分析师",
            description="分析用户输入的完整度，引导用户补充关键信息",
            system_prompt=load_prompt("agents/requirement_analyst.txt", fallback=_FALLBACK_PROMPT),
            temperature=0.2,
        )
        super().__init__(config)

    async def process(self, task: dict[str, Any]) -> AgentResponse:
        """处理需求分析任务"""
        description = task.get("description", "")
        context = task.get("context", {})

        prompt = (
            f"{USER_INPUT_BOUNDARY}\n\n"
            f"请分析下列用户需求：\n"
            f"{wrap_user_input(description, label='description')}"
        )

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
    ) -> dict[str, Any]:
        """
        快速分析需求完整度
        
        Returns:
            结构化需求分析结果，包含 is_complete、summary、guidance_questions 等
        """
        prompt = (
            f"{USER_INPUT_BOUNDARY}\n\n"
            f"请分析下列用户需求：\n"
            f"{wrap_user_input(user_input, label='description')}"
        )
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

    def _fallback_analysis(self, user_input: str) -> dict[str, Any]:
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

    def _parse_json(self, text: str) -> dict[str, Any]:
        """解析 JSON"""
        if not text:
            return {}
        try:
            return cast(dict[str, Any], json.loads(text))
        except (json.JSONDecodeError, TypeError):
            match = re.search(r'(\{.*\})', text, re.DOTALL)
            if match:
                try:
                    return cast(dict[str, Any], json.loads(match.group(1)))
                except (json.JSONDecodeError, TypeError):
                    pass
        return {}
