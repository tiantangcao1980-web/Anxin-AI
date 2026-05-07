"""
Agent Forum — 多 Agent 辩论论坛引擎

灵感来源：BettaFish ForumEngine
核心机制：
1. 多个专业 Agent 各自独立分析同一目标
2. 主持人（Host）综合各方观点，发现矛盾
3. 针对矛盾点发起定向辩论
4. 最终形成共识结论

辩论维度（借鉴 BettaFish 四维度综合）：
1. 事件/事实梳理 — 各 Agent 发现是否一致
2. 观点整合与矛盾标记 — 识别分歧
3. 风险/趋势预测 — 前瞻性分析
4. 后续建议 — 形成行动方案
"""

import json
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, TypedDict, cast

from loguru import logger


@dataclass
class AgentSpeech:
    """Agent 发言"""
    agent_name: str
    agent_role: str
    content: str
    dimension: str
    confidence: float
    key_findings: list[str] = field(default_factory=list)
    risk_level: str = "unknown"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "content": self.content[:1000],
            "dimension": self.dimension,
            "confidence": self.confidence,
            "key_findings": self.key_findings,
            "risk_level": self.risk_level,
            "timestamp": self.timestamp,
        }


@dataclass
class DebateConflict:
    """辩论冲突"""
    topic: str
    agents_involved: list[str]
    positions: dict[str, str]
    resolved: bool = False
    resolution: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "agents_involved": self.agents_involved,
            "positions": self.positions,
            "resolved": self.resolved,
            "resolution": self.resolution,
        }


@dataclass
class ForumConsensus:
    """论坛共识结论"""
    risk_level: str
    confidence: float
    key_conclusions: list[str]
    debate_summary: str
    action_items: list[str]
    agents_participated: list[str]
    conflicts_count: int
    conflicts_resolved: int
    dimensions_covered: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "key_conclusions": self.key_conclusions,
            "debate_summary": self.debate_summary,
            "action_items": self.action_items,
            "agents_participated": self.agents_participated,
            "conflicts_count": self.conflicts_count,
            "conflicts_resolved": self.conflicts_resolved,
            "dimensions_covered": self.dimensions_covered,
        }


# ===== Agent 角色定义 =====

class ForumAgentDefinition(TypedDict):
    name: str
    role: str
    focus: str
    dimensions: list[str]


FORUM_AGENTS: list[ForumAgentDefinition] = [
    {
        "name": "due_diligence_expert",
        "role": "尽职调查专家",
        "focus": "企业基本面与经营状况",
        "dimensions": ["工商信息核实", "经营状态评估", "股权关系分析"],
    },
    {
        "name": "legal_risk_analyst",
        "role": "法律风险分析师",
        "focus": "诉讼与法律合规风险",
        "dimensions": ["涉诉记录分析", "行政处罚审查", "合规隐患识别"],
    },
    {
        "name": "financial_analyst",
        "role": "财务风险评估师",
        "focus": "信用与财务健康度",
        "dimensions": ["信用评级分析", "财务指标评估", "债务风险识别"],
    },
    {
        "name": "industry_researcher",
        "role": "行业研究员",
        "focus": "行业趋势与舆情",
        "dimensions": ["行业政策分析", "舆情风险评估", "竞争格局研判"],
    },
]


class ForumChatAgent(Protocol):
    async def chat(
        self,
        message: str,
        system_prompt_override: str | None = None,
        **kwargs: Any,
    ) -> str: ...


class AgentForum:
    """
    多 Agent 辩论论坛

    流程：
    1. 分发阶段 — 各 Agent 独立分析
    2. 发言阶段 — 各 Agent 提交发言
    3. 主持人综合 — 识别矛盾，提出追问
    4. 辩论轮次 — 针对矛盾展开辩论
    5. 共识达成 — 综合形成最终结论
    """

    MAX_DEBATE_ROUNDS = 2  # 最大辩论轮次

    def __init__(self) -> None:
        self._llm_agent: ForumChatAgent | None = None

    @property
    def llm_agent(self) -> ForumChatAgent | None:
        if self._llm_agent is None:
            try:
                from src.agents.workforce import get_workforce
                wf = get_workforce()
                self._llm_agent = cast(ForumChatAgent | None, (
                    wf.agents.get("due_diligence")
                    or wf.agents.get("legal_advisor")
                    or (list(wf.agents.values())[0] if wf.agents else None)
                ))
            except Exception as e:
                logger.warning(f"无法加载 LLM Agent: {e}")
        return self._llm_agent

    async def run_forum_stream(
        self,
        company_name: str,
        investigation_data: dict[str, Any],
        research_summary: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        流式运行论坛辩论

        事件类型：
        - forum_start: 论坛开始
        - agent_speaking: Agent 开始发言
        - agent_speech: Agent 发言完成
        - host_analysis: 主持人分析
        - debate_start: 辩论开始
        - debate_round: 辩论轮次
        - conflict_found: 发现冲突
        - conflict_resolved: 冲突解决
        - consensus_reached: 达成共识
        - forum_done: 论坛结束
        """
        speeches: list[AgentSpeech] = []
        conflicts: list[DebateConflict] = []

        yield {
            "type": "forum_start",
            "message": f"多 Agent 论坛开始，{len(FORUM_AGENTS)} 位专家参与讨论",
            "agents": [{"name": a["name"], "role": a["role"]} for a in FORUM_AGENTS],
        }

        # ===== 阶段 1：各 Agent 独立发言 =====
        for agent_def in FORUM_AGENTS:
            yield {
                "type": "agent_speaking",
                "agent": agent_def["name"],
                "role": agent_def["role"],
                "focus": agent_def["focus"],
            }

            speech = await self._get_agent_speech(
                agent_def, company_name, investigation_data, research_summary
            )
            speeches.append(speech)

            yield {
                "type": "agent_speech",
                "agent": agent_def["name"],
                "speech": speech.to_dict(),
            }

        # ===== 阶段 2：主持人综合分析，识别矛盾 =====
        yield {
            "type": "host_analysis",
            "message": "主持人正在综合分析各方观点...",
        }

        host_result = await self._host_synthesize(
            company_name, speeches, investigation_data
        )
        conflicts = host_result["conflicts"]
        follow_up_questions = host_result.get("follow_up_questions", [])

        if conflicts:
            for conflict in conflicts:
                yield {
                    "type": "conflict_found",
                    "conflict": conflict.to_dict(),
                }

        # ===== 阶段 3：辩论轮次（如果有冲突） =====
        if conflicts and follow_up_questions:
            yield {
                "type": "debate_start",
                "conflicts_count": len(conflicts),
                "message": f"发现 {len(conflicts)} 处分析分歧，启动定向辩论",
            }

            for debate_round in range(1, self.MAX_DEBATE_ROUNDS + 1):
                unresolved = [c for c in conflicts if not c.resolved]
                if not unresolved:
                    break

                yield {
                    "type": "debate_round",
                    "round": debate_round,
                    "unresolved_count": len(unresolved),
                }

                # 各 Agent 针对冲突点补充发言
                for conflict in unresolved:
                    resolution = await self._resolve_conflict(
                        conflict, company_name, speeches, investigation_data
                    )
                    conflict.resolved = True
                    conflict.resolution = resolution

                    yield {
                        "type": "conflict_resolved",
                        "conflict": conflict.to_dict(),
                    }

        # ===== 阶段 4：形成共识 =====
        consensus = await self._reach_consensus(
            company_name, speeches, conflicts, investigation_data, research_summary
        )

        yield {
            "type": "consensus_reached",
            "consensus": consensus.to_dict(),
        }

        yield {
            "type": "forum_done",
            "data": {
                "speeches_count": len(speeches),
                "conflicts_count": len(conflicts),
                "conflicts_resolved": sum(1 for c in conflicts if c.resolved),
                "consensus": consensus.to_dict(),
            },
        }

    # ========== 内部方法 ==========

    async def _get_agent_speech(
        self,
        agent_def: ForumAgentDefinition,
        company_name: str,
        data: dict[str, Any],
        research_summary: str,
    ) -> AgentSpeech:
        """获取单个 Agent 的发言"""
        agent = self.llm_agent
        if not agent:
            return AgentSpeech(
                agent_name=agent_def["name"],
                agent_role=agent_def["role"],
                content=f"作为{agent_def['role']}，基于现有数据无法进行深入分析。",
                dimension=agent_def["focus"],
                confidence=0.3,
                key_findings=["LLM 不可用"],
            )

        data_summary = json.dumps(data, ensure_ascii=False, default=str)[:2000]

        prompt = f"""你是{agent_def['role']}，正在参与对「{company_name}」的多专家协同尽职调查论坛。

你的专业领域：{agent_def['focus']}
你需要关注的维度：{', '.join(agent_def['dimensions'])}

已有调查数据：
{data_summary}

{f'深度研究摘要：{research_summary[:500]}' if research_summary else ''}

请以你的专业视角分析该企业，返回 JSON 格式：
{{
    "content": "你的分析发言（200-400字）",
    "confidence": 0.0-1.0,
    "risk_level": "low/medium/high",
    "key_findings": ["关键发现1", "关键发现2", "关键发现3"],
    "concerns": ["需要关注的问题1", "需要关注的问题2"]
}}

请直接返回 JSON，不要其他文字。"""

        try:
            response = await agent.chat(
                message=prompt,
                system_prompt_override=f"你是{agent_def['role']}。请以专业视角分析并直接返回 JSON。",
            )

            cleaned = re.sub(r'```(?:json)?\s*', '', response).strip()
            cleaned = re.sub(r'```\s*$', '', cleaned).strip()
            json_match = re.search(r'\{[\s\S]*\}', cleaned)

            if json_match:
                parsed = json.loads(json_match.group())
                return AgentSpeech(
                    agent_name=agent_def["name"],
                    agent_role=agent_def["role"],
                    content=parsed.get("content", ""),
                    dimension=agent_def["focus"],
                    confidence=min(1.0, max(0.0, float(parsed.get("confidence", 0.5)))),
                    key_findings=parsed.get("key_findings", []),
                    risk_level=parsed.get("risk_level", "unknown"),
                )
        except Exception as e:
            logger.warning(f"Agent {agent_def['name']} 发言失败: {e}")

        return AgentSpeech(
            agent_name=agent_def["name"],
            agent_role=agent_def["role"],
            content=f"作为{agent_def['role']}，根据现有数据进行了初步分析。",
            dimension=agent_def["focus"],
            confidence=0.4,
        )

    async def _host_synthesize(
        self,
        company_name: str,
        speeches: list[AgentSpeech],
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """主持人综合分析：整合观点，识别矛盾"""
        agent = self.llm_agent
        if not agent:
            return {"conflicts": [], "follow_up_questions": []}

        speeches_text = "\n\n".join(
            f"【{s.agent_role}】(信心: {s.confidence:.0%}, 风险: {s.risk_level})\n"
            f"{s.content}\n关键发现: {', '.join(s.key_findings)}"
            for s in speeches
        )

        prompt = f"""你是多专家论坛的主持人。请综合分析以下各专家对「{company_name}」的分析发言。

各专家发言：
{speeches_text}

请识别：
1. 各专家观点中的矛盾/分歧
2. 需要进一步辩论的问题

请以 JSON 格式返回：
{{
    "conflicts": [
        {{
            "topic": "矛盾主题",
            "agents_involved": ["agent_name1", "agent_name2"],
            "positions": {{"agent_name1": "观点1", "agent_name2": "观点2"}},
            "severity": "high/medium/low"
        }}
    ],
    "follow_up_questions": ["需要进一步讨论的问题1", "问题2"],
    "synthesis": "各方观点的初步综合"
}}

请直接返回 JSON。"""

        try:
            response = await agent.chat(
                message=prompt,
                system_prompt_override="你是多专家辩论论坛的主持人。请综合分析并直接返回 JSON。",
            )

            cleaned = re.sub(r'```(?:json)?\s*', '', response).strip()
            cleaned = re.sub(r'```\s*$', '', cleaned).strip()
            json_match = re.search(r'\{[\s\S]*\}', cleaned)

            if json_match:
                parsed = json.loads(json_match.group())
                conflicts = [
                    DebateConflict(
                        topic=c.get("topic", ""),
                        agents_involved=c.get("agents_involved", []),
                        positions=c.get("positions", {}),
                    )
                    for c in parsed.get("conflicts", [])
                ]
                return {
                    "conflicts": conflicts,
                    "follow_up_questions": parsed.get("follow_up_questions", []),
                    "synthesis": parsed.get("synthesis", ""),
                }
        except Exception as e:
            logger.warning(f"主持人综合分析失败: {e}")

        return {"conflicts": [], "follow_up_questions": []}

    async def _resolve_conflict(
        self,
        conflict: DebateConflict,
        company_name: str,
        speeches: list[AgentSpeech],
        data: dict[str, Any],
    ) -> str:
        """解决特定冲突"""
        agent = self.llm_agent
        if not agent:
            return "LLM 不可用，无法解决冲突"

        prompt = f"""作为仲裁者，请解决以下关于「{company_name}」分析中的分歧：

分歧主题：{conflict.topic}
涉及专家：{', '.join(conflict.agents_involved)}
各方立场：
{json.dumps(conflict.positions, ensure_ascii=False, indent=2)}

已有数据参考：
{json.dumps(data, ensure_ascii=False, default=str)[:1000]}

请给出客观、平衡的裁决意见（100字以内）。"""

        try:
            return await agent.chat(
                message=prompt,
                system_prompt_override="你是公正的分析仲裁者。请基于事实给出简明裁决。",
            )
        except Exception as e:
            logger.warning(f"冲突解决失败: {e}")
            return "自动裁决：建议进一步核实数据后确定。"

    async def _reach_consensus(
        self,
        company_name: str,
        speeches: list[AgentSpeech],
        conflicts: list[DebateConflict],
        data: dict[str, Any],
        research_summary: str,
    ) -> ForumConsensus:
        """达成最终共识"""
        agent = self.llm_agent

        # 计算各维度统计
        risk_levels = [s.risk_level for s in speeches if s.risk_level != "unknown"]
        avg_confidence = sum(s.confidence for s in speeches) / len(speeches) if speeches else 0.5
        all_findings = []
        for s in speeches:
            all_findings.extend(s.key_findings)

        if not agent:
            consensus_risk = "medium"
            if risk_levels:
                if risk_levels.count("high") > len(risk_levels) / 2:
                    consensus_risk = "high"
                elif risk_levels.count("low") > len(risk_levels) / 2:
                    consensus_risk = "low"

            return ForumConsensus(
                risk_level=consensus_risk,
                confidence=avg_confidence,
                key_conclusions=all_findings[:5],
                debate_summary=f"共 {len(speeches)} 位专家参与分析，发现 {len(conflicts)} 处分歧。",
                action_items=["建议进一步人工核查"],
                agents_participated=[s.agent_name for s in speeches],
                conflicts_count=len(conflicts),
                conflicts_resolved=sum(1 for c in conflicts if c.resolved),
                dimensions_covered=[s.dimension for s in speeches],
            )

        speeches_summary = "\n".join(
            f"- {s.agent_role}: 风险={s.risk_level}, 信心={s.confidence:.0%}, 要点: {'; '.join(s.key_findings[:3])}"
            for s in speeches
        )

        conflicts_summary = "\n".join(
            f"- {c.topic}: {'已解决 — ' + c.resolution if c.resolved else '未解决'}"
            for c in conflicts
        ) if conflicts else "无冲突"

        prompt = f"""请综合以下多专家论坛讨论，形成对「{company_name}」的最终共识结论。

各专家观点：
{speeches_summary}

冲突处理：
{conflicts_summary}

{f'深度研究参考：{research_summary[:300]}' if research_summary else ''}

请以 JSON 格式返回最终共识：
{{
    "risk_level": "low/medium/high",
    "confidence": 0.0-1.0,
    "key_conclusions": ["核心结论1", "核心结论2", "核心结论3"],
    "debate_summary": "辩论过程摘要（100-200字）",
    "action_items": ["建议行动1", "建议行动2", "建议行动3"]
}}

请直接返回 JSON。"""

        try:
            response = await agent.chat(
                message=prompt,
                system_prompt_override="你是尽职调查结论综合专家。请基于多方分析形成最终共识并直接返回 JSON。",
            )

            cleaned = re.sub(r'```(?:json)?\s*', '', response).strip()
            cleaned = re.sub(r'```\s*$', '', cleaned).strip()
            json_match = re.search(r'\{[\s\S]*\}', cleaned)

            if json_match:
                parsed = json.loads(json_match.group())
                return ForumConsensus(
                    risk_level=parsed.get("risk_level", "medium"),
                    confidence=min(1.0, max(0.0, float(parsed.get("confidence", avg_confidence)))),
                    key_conclusions=parsed.get("key_conclusions", all_findings[:5]),
                    debate_summary=parsed.get("debate_summary", ""),
                    action_items=parsed.get("action_items", []),
                    agents_participated=[s.agent_name for s in speeches],
                    conflicts_count=len(conflicts),
                    conflicts_resolved=sum(1 for c in conflicts if c.resolved),
                    dimensions_covered=[s.dimension for s in speeches],
                )
        except Exception as e:
            logger.warning(f"共识达成失败: {e}")

        # Fallback
        consensus_risk = "medium"
        if risk_levels:
            high_count = risk_levels.count("high")
            if high_count > len(risk_levels) / 2:
                consensus_risk = "high"
            elif risk_levels.count("low") > len(risk_levels) / 2:
                consensus_risk = "low"

        return ForumConsensus(
            risk_level=consensus_risk,
            confidence=avg_confidence,
            key_conclusions=all_findings[:5],
            debate_summary=f"共 {len(speeches)} 位专家参与论坛讨论，经过分析和辩论后形成共识。",
            action_items=["建议核查工商数据", "持续监控诉讼动态", "评估合规风险"],
            agents_participated=[s.agent_name for s in speeches],
            conflicts_count=len(conflicts),
            conflicts_resolved=sum(1 for c in conflicts if c.resolved),
            dimensions_covered=[s.dimension for s in speeches],
        )


# 全局实例
agent_forum = AgentForum()
