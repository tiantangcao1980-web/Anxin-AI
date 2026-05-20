"""
共识决策智能体 (Consensus Agent)
"""

import json
import re
from typing import Any

from src.agents._prompt_safety import USER_INPUT_BOUNDARY, wrap_user_input
from src.agents.base import AgentConfig, AgentResponse, BaseLegalAgent
from src.prompts import load_prompt

_FALLBACK_PROMPT = "你是一个专业的法务共识仲裁专家。"


class ConsensusAgent(BaseLegalAgent):
    """共识决策智能体"""

    def __init__(self) -> None:
        config = AgentConfig(
            name="共识决策Agent",
            role="仲裁者",
            description="解决智能体间的意见分歧，达成最终共识",
            system_prompt=load_prompt("agents/consensus_agent.txt", fallback=_FALLBACK_PROMPT),
            temperature=0.2,
        )
        super().__init__(config)

    async def process(self, task: dict[str, Any]) -> AgentResponse:
        """处理共识任务"""
        # 这里 task 应该包含原始任务描述和各 Agent 的结果
        description = task.get("description", "")
        agent_results = task.get("agent_results", [])

        results_str = "\n\n".join(
            [
                f"--- Agent: {r.agent_name} ---\n{r.content}"
                for r in agent_results
                if isinstance(r, AgentResponse)
            ]
        )

        prompt = f"任务背景：{wrap_user_input(description, label='description')}\n\n以下是各智能体的分析结果，请进行冲突审查并给出最终共识结论：\n\n{results_str}"

        response_text = await self.chat(prompt)

        # 解析 JSON
        json_match = re.search(r"(\{.*\})", response_text, re.DOTALL)
        metadata = {}
        content = response_text

        if json_match:
            try:
                metadata = json.loads(json_match.group(1))
                content = metadata.get("final_decision", response_text)
            except Exception:
                pass

        return AgentResponse(agent_name=self.name, content=content, metadata=metadata)
