"""
共识决策智能体 (Consensus Agent)
"""

from typing import Any, Dict, List, Optional
from loguru import logger
import json
import re

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse


CONSENSUS_PROMPT = """你是一个专业的法务共识仲裁专家。

你的任务是：
1. **冲突识别**：审查多个专业法务智能体对同一问题的分析结果，找出其中的矛盾点、分歧点或不一致的法律建议。
2. **深度辩论与评分**：
   - 针对每个分歧点，模拟多方辩论。
   - 对每个智能体的观点进行评分 (0-10分)，评分标准：法律依据充分性 (40%)、证据逻辑严密性 (30%)、风险规避有效性 (30%)。
3. **达成共识**：基于加权评分结果，选出最优方案或综合生成一个新的最优方案。
4. **风险评级**：对最终方案的风险等级进行最终定性。

输入格式：
- 任务描述
- 多个智能体的原始输出

输出格式 (严格 JSON):
{
  "conflicts": [
    {
      "point": "分歧点描述",
      "positions": [
        {"agent": "AgentA", "view": "观点A", "score": 8, "reason": "评分理由"},
        {"agent": "AgentB", "view": "观点B", "score": 6, "reason": "评分理由"}
      ],
      "winner": "AgentA"
    }
  ],
  "debate_summary": "对分歧点的辩论过程总结",
  "final_decision": "最终一致性结论",
  "reasoning": "达成此结论的法理依据",
  "risk_level": "low/medium/high",
  "is_consensus_reached": true
}
"""


class ConsensusAgent(BaseLegalAgent):
    """共识决策智能体"""
    
    def __init__(self):
        config = AgentConfig(
            name="共识决策Agent",
            role="仲裁者",
            description="解决智能体间的意见分歧，达成最终共识",
            system_prompt=CONSENSUS_PROMPT,
            temperature=0.2,
        )
        super().__init__(config)
    
    async def process(self, task: Dict[str, Any]) -> AgentResponse:
        """处理共识任务"""
        # 这里 task 应该包含原始任务描述和各 Agent 的结果
        description = task.get("description", "")
        agent_results = task.get("agent_results", [])
        
        results_str = "\n\n".join([
            f"--- Agent: {r.agent_name} ---\n{r.content}" 
            for r in agent_results if isinstance(r, AgentResponse)
        ])
        
        prompt = f"任务背景：{description}\n\n以下是各智能体的分析结果，请进行冲突审查并给出最终共识结论：\n\n{results_str}"
        
        response_text = await self.chat(prompt)
        
        # 解析 JSON
        json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
        metadata = {}
        content = response_text
        
        if json_match:
            try:
                metadata = json.loads(json_match.group(1))
                content = metadata.get("final_decision", response_text)
            except:
                pass
                
        return AgentResponse(
            agent_name=self.name,
            content=content,
            metadata=metadata
        )
