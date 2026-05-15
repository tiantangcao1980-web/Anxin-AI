"""
Prompt 组装与质量评分服务 (Prompt Assembler)

核心能力：
1. 动态 Prompt 组装 — 将用户输入 + 场景模板 slot + 用户画像 + 对话历史组装为高质量 prompt
2. 就绪度评分 — 在生成前评估 prompt 质量，给用户控制感
3. 对话修复 — 检测当前输入与历史的矛盾/跑偏
4. 上下文摘要注入 — 将已收集信息结构化注入 Agent prompt
"""

import re
from typing import Any


class PromptAssembler:
    """Prompt 组装与质量评分"""

    def assemble_and_score(
        self,
        user_input: str,
        intent: str,
        filled_slots: list[dict[str, Any]],
        missing_elements: list[str],
        user_profile: dict[str, Any] | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """
        组装最终 Prompt 并评分。

        Returns:
            {
                "enhanced_prompt": str,      # 增强后的 prompt（注入上下文）
                "readiness_score": float,    # 0-1 就绪度
                "readiness_level": str,      # high / medium / low
                "missing_info": [str],       # 缺失信息列表
                "quality_notes": [str],      # 质量说明
                "can_proceed": bool,         # 是否可以继续生成
            }
        """
        profile = user_profile or {}
        history = conversation_history or []

        # === 1. 构建上下文注入块 ===
        context_blocks = []

        # 已收集 slot 信息
        if filled_slots:
            slot_lines = []
            for slot in filled_slots:
                source = {
                    "input": "用户提供",
                    "profile": "历史记录",
                    "clarification": "补充确认",
                }.get(slot.get("source", ""), "用户提供")
                slot_lines.append(
                    f"  - {slot.get('label', '')}: {slot.get('value', '')}（{source}）"
                )
            context_blocks.append("[已收集的需求信息]\n" + "\n".join(slot_lines))

        # 用户画像上下文
        sophistication = profile.get("legal_sophistication", "intermediate")
        if sophistication == "novice":
            context_blocks.append(
                "[用户特征] 用户可能对法律不太熟悉，请用通俗语言解释，避免过多术语。"
            )
        elif sophistication == "expert":
            context_blocks.append("[用户特征] 用户是法律专业人士，可直接使用术语和法条引用。")

        default_ctx = profile.get("default_context", {})
        if default_ctx:
            ctx_lines = [f"  - {k}: {v}" for k, v in default_ctx.items() if v]
            if ctx_lines:
                context_blocks.append("[用户默认上下文]\n" + "\n".join(ctx_lines))

        # === 2. 组装增强 prompt ===
        parts = [user_input]
        if context_blocks:
            parts.append("\n\n" + "\n\n".join(context_blocks))

        enhanced_prompt = "\n".join(parts)

        # === 3. 计算就绪度评分 ===
        score = self._calculate_readiness(user_input, filled_slots, missing_elements, history)

        quality_notes = []
        if filled_slots:
            labels = [s.get("label", "") for s in filled_slots]
            quality_notes.append(f"已包含：{', '.join(labels)}")
        if len(user_input) > 100:
            quality_notes.append("用户描述较详细")
        if history and len(history) > 2:
            quality_notes.append("有多轮对话上下文")

        if score >= 0.7:
            level = "high"
        elif score >= 0.4:
            level = "medium"
        else:
            level = "low"

        return {
            "enhanced_prompt": enhanced_prompt,
            "readiness_score": score,
            "readiness_level": level,
            "missing_info": missing_elements,
            "quality_notes": quality_notes,
            "can_proceed": score >= 0.4,
        }

    def detect_contradiction(
        self,
        current_input: str,
        conversation_history: list[dict[str, str]],
    ) -> dict[str, Any] | None:
        """
        检测当前输入与历史对话的矛盾或主题跑偏。

        Returns:
            None — 无矛盾
            {"type": "contradiction"|"topic_shift", "message": str, "details": dict}
        """
        if not conversation_history or len(conversation_history) < 2:
            return None

        # 提取历史中的关键意图信号
        history_intents = set()
        current_intents = set()

        intent_keywords = {
            "contract": ["合同", "审查", "协议", "条款"],
            "labor": ["劳动", "员工", "辞退", "工资", "社保"],
            "litigation": ["诉讼", "起诉", "仲裁", "法院"],
            "ip": ["专利", "商标", "侵权", "知识产权"],
            "drafting": ["起草", "草拟", "文书", "律师函"],
            "compliance": ["合规", "监管", "政策"],
            "tax": ["税", "财务", "发票"],
        }

        for kw_group, keywords in intent_keywords.items():
            if any(kw in current_input for kw in keywords):
                current_intents.add(kw_group)
            for msg in conversation_history[-4:]:  # 只看最近 4 条
                msg_content = msg.get("content", "")
                if msg.get("role") == "user" and any(kw in msg_content for kw in keywords):
                    history_intents.add(kw_group)

        # 检测主题跳转（用户历史一直在谈 A，突然切到 B）
        if (
            current_intents
            and history_intents
            and not current_intents.intersection(history_intents)
        ):
            intent_names = {
                "contract": "合同相关",
                "labor": "劳动人事",
                "litigation": "诉讼",
                "ip": "知识产权",
                "drafting": "文书起草",
                "compliance": "合规",
                "tax": "财税",
            }
            old_topic = "、".join(intent_names.get(i, i) for i in history_intents)
            new_topic = "、".join(intent_names.get(i, i) for i in current_intents)

            return {
                "type": "topic_shift",
                "message": f"您之前在咨询「{old_topic}」相关问题，现在转到了「{new_topic}」。这是一个新问题，还是和之前的问题有关联？",
                "details": {
                    "previous_topics": list(history_intents),
                    "current_topics": list(current_intents),
                },
                "options": [
                    "这是新问题，请单独处理",
                    "和之前的问题相关",
                    "请先处理之前的问题",
                ],
            }

        # 检测角色矛盾（先说自己是雇主，又说自己是员工）
        role_signals = {
            "employer": [
                r"我是老板",
                r"我是雇主",
                r"公司方面",
                r"我是.*HR",
                r"公司HR",
                r"人事部",
                r"想辞退",
                r"要开除",
            ],
            "employee": [
                r"我被.*辞退",
                r"被公司辞退",
                r"我的工资",
                r"我是员工",
                r"老板不给",
                r"拖欠我",
                r"我被开除",
            ],
        }
        current_role = None
        history_role = None

        for role, patterns in role_signals.items():
            if any(re.search(p, current_input) for p in patterns):
                current_role = role
            for msg in conversation_history:
                if msg.get("role") == "user":
                    if any(re.search(p, msg.get("content", "")) for p in patterns):
                        history_role = role

        if current_role and history_role and current_role != history_role:
            role_names = {"employer": "雇主/HR", "employee": "员工"}
            return {
                "type": "contradiction",
                "message": (
                    f"您之前提到您是「{role_names.get(history_role, history_role)}」，"
                    f"但这次描述更像是「{role_names.get(current_role, current_role)}」的视角。"
                    f"请确认您的角色，这会影响我给出的建议方向。"
                ),
                "details": {
                    "previous_role": history_role,
                    "current_role": current_role,
                },
                "options": [
                    f"我是{role_names.get(current_role, current_role)}",
                    f"我是{role_names.get(history_role, history_role)}",
                    "我是第三方咨询",
                ],
            }

        return None

    @staticmethod
    def _calculate_readiness(
        user_input: str,
        filled_slots: list[dict[str, Any]],
        missing_elements: list[str],
        history: list[dict[str, str]],
    ) -> float:
        """计算 prompt 就绪度评分"""
        score = 0.3  # 基础分（有用户输入就有 0.3）

        # 输入长度贡献
        input_len = len(user_input)
        if input_len > 50:
            score += 0.1
        if input_len > 150:
            score += 0.1

        # 已填 slot 贡献
        total_slots = len(filled_slots) + len(missing_elements)
        if total_slots > 0:
            fill_ratio = len(filled_slots) / total_slots
            score += fill_ratio * 0.3

        # 对话历史贡献（多轮对话意味着更多上下文）
        user_turns = sum(1 for m in history if m.get("role") == "user")
        if user_turns >= 1:
            score += 0.1
        if user_turns >= 3:
            score += 0.1

        return min(round(score, 2), 1.0)


# 全局实例
prompt_assembler = PromptAssembler()
