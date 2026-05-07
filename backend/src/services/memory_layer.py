"""
Memory Layer — 分层记忆演化系统

融合方案：
- Mem0: 三级记忆结构（User/Session/Agent）+ Graph Memory
- Memobase: 结构化用户画像 + 事件时间线 + 批量处理
- OpenViking: L0/L1/L2 上下文分层加载

法律场景适配：
- 用户级记忆：客户法律画像（企业类型、行业、常见纠纷、偏好服务）
- 会话级记忆：当前咨询上下文、调查进度
- Agent级记忆：推理链、工具调用结果、决策依据
- 图记忆：实体关系（当事人-企业-合同-法条-判例）
- 事件时间线：法律时效（合同到期、诉讼时效、法规变更）

L0/L1/L2 分层加载：
- L0（摘要）: 一句话描述，用于快速相关性判断（~10 token）
- L1（概要）: 核心信息，用于规划决策（~500 token）
- L2（详情）: 完整内容，仅按需加载
"""

import copy
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

# ===== 用户法律画像 Schema =====

DEFAULT_LEGAL_PROFILE: dict[str, Any] = {
    "basic_info": {
        "company_type": None,       # 企业类型
        "industry": None,           # 所属行业
        "company_size": None,       # 企业规模
        "region": None,             # 所在地区
    },
    "legal_needs": {
        "primary_domain": None,     # 主要法律需求领域
        "secondary_domains": [],    # 次要需求领域
        "urgency_pattern": "medium",  # 通常的紧急程度
    },
    "risk_profile": {
        "focus_dimensions": {},     # 关注的风险维度权重
        "risk_tolerance": "medium", # 风险容忍度
        "known_risks": [],          # 已知风险点
    },
    "interaction_pattern": {
        "preferred_depth": "deep",  # 调查深度偏好
        "report_format": "comprehensive",  # 报告格式偏好
        "communication_style": "professional",  # 沟通风格
        "frequent_queries": [],     # 高频查询模式
    },
    "timeline_events": [],          # 法律时效事件列表
    "confidence": 0.0,              # 画像置信度 (0-1)
    "last_updated": None,
}


class MemoryEntry:
    """单条记忆"""

    def __init__(
        self,
        content: str,
        memory_type: str,  # user / session / agent / graph
        level: int = 1,    # 0=L0, 1=L1, 2=L2
        metadata: dict[str, Any] | None = None,
        source: str = "system",
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        self.id = hashlib.md5(f"{content}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        self.content = content
        self.memory_type = memory_type
        self.level = level
        self.metadata = metadata or {}
        self.source = source
        self.user_id = user_id
        self.session_id = session_id
        self.created_at = datetime.now()
        self.accessed_at = datetime.now()
        self.access_count = 0
        self.confidence = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "level": self.level,
            "metadata": self.metadata,
            "source": self.source,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count,
            "confidence": self.confidence,
        }


class ContextLoader:
    """
    L0/L1/L2 上下文分层加载器

    灵感：OpenViking 的文件系统范式
    - L0（~10 token）: 一句话摘要，快速筛选
    - L1（~500 token）: 关键信息摘要，用于决策
    - L2（完整）: 原始内容，按需加载

    法律场景：一份合同 5000 token，但 L0 只需"买卖合同，甲方XX乙方YY，2024签订"
    """

    @staticmethod
    def generate_l0(content: str, content_type: str = "general") -> str:
        """生成 L0 单句摘要"""
        if not content:
            return ""

        # 法律文档类型的 L0 模板
        if content_type == "contract":
            # 提取合同核心要素
            return ContextLoader._extract_contract_l0(content)
        elif content_type == "case":
            return ContextLoader._extract_case_l0(content)
        elif content_type == "regulation":
            return ContextLoader._extract_regulation_l0(content)
        elif content_type == "investigation":
            return ContextLoader._extract_investigation_l0(content)
        else:
            # 通用：取前 50 字
            return content[:100].replace("\n", " ").strip() + ("..." if len(content) > 100 else "")

    @staticmethod
    def generate_l1(content: str, content_type: str = "general", max_tokens: int = 500) -> str:
        """生成 L1 概要（约 500 token）"""
        if not content:
            return ""

        # 按段落提取关键信息
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        if content_type == "investigation":
            # 调查报告：提取各维度评分和风险点
            return ContextLoader._extract_investigation_l1(content)
        elif content_type == "contract":
            return ContextLoader._extract_contract_l1(content)

        # 通用：按重要性选择段落，控制在 max_chars 以内
        max_chars = max_tokens * 2  # 粗略估计
        result_parts = []
        current_len = 0

        for p in paragraphs:
            if current_len + len(p) > max_chars:
                break
            result_parts.append(p)
            current_len += len(p)

        return "\n\n".join(result_parts) if result_parts else content[:max_chars]

    @staticmethod
    def _extract_contract_l0(content: str) -> str:
        """合同 L0：类型+双方+日期"""
        import re
        parties = re.findall(r'[甲乙丙丁]方[：:]\s*(.{2,30})', content)
        date = re.findall(r'(\d{4})[年/.-](\d{1,2})[月/.-](\d{1,2})', content)
        contract_type = "合同"
        for t in ["买卖", "租赁", "劳动", "借款", "服务", "合作", "技术"]:
            if t in content[:200]:
                contract_type = t + "合同"
                break
        parts = [contract_type]
        if parties:
            parts.append("、".join(parties[:2]))
        if date:
            parts.append(f"{date[0][0]}年签订")
        return "，".join(parts)

    @staticmethod
    def _extract_case_l0(content: str) -> str:
        """案件 L0：案号+案由+当事人"""
        import re
        case_no = re.findall(r'[（(]\d{4}[)）][^，,。]+号', content)
        return (case_no[0] if case_no else content[:80].replace("\n", " ")) + "..."

    @staticmethod
    def _extract_regulation_l0(content: str) -> str:
        """法规 L0：法规名+生效日期"""
        import re
        title_match = re.findall(r'《([^》]+)》', content)
        title = title_match[0] if title_match else content[:30]
        return f"法规：{title}"

    @staticmethod
    def _extract_investigation_l0(content: str) -> str:
        """调查 L0：企业名+风险等级"""
        if isinstance(content, dict):
            name = content.get("company_name", "")
            risk = content.get("risk_level", "unknown")
            return f"调查：{name}，风险{risk}"
        return content[:80].replace("\n", " ")

    @staticmethod
    def _extract_investigation_l1(content: str) -> str:
        """调查 L1：五维评分+主要风险点"""
        if isinstance(content, dict):
            risk = content.get("risk", {})
            dims = ["operation_risk", "litigation_risk", "credit_risk", "compliance_risk", "relation_risk"]
            scores = [f"{d.replace('_risk','')}: {risk.get(d, 0)}" for d in dims]
            points = risk.get("risk_points", [])[:3]
            parts = [f"风险评分: {', '.join(scores)}"]
            if points:
                parts.append(f"风险点: {'；'.join(points)}")
            return "\n".join(parts)
        return content[:1000]

    @staticmethod
    def _extract_contract_l1(content: str) -> str:
        """合同 L1：关键条款摘要"""
        import re
        key_sections = []
        # 提取金额
        amounts = re.findall(r'[\d,]+(?:\.\d+)?\s*(?:万|元|美元)', content)
        if amounts:
            key_sections.append(f"金额: {', '.join(amounts[:3])}")
        # 提取期限
        terms = re.findall(r'(?:期限|有效期)[：:]\s*(.{5,30})', content)
        if terms:
            key_sections.append(f"期限: {terms[0]}")
        # 取前 800 字补充
        remaining = 800 - sum(len(s) for s in key_sections)
        if remaining > 100:
            key_sections.append(content[:remaining])
        return "\n".join(key_sections)


class MemoryLayer:
    """
    分层记忆系统主服务

    三级记忆：
    - User Memory: 跨会话持久化的用户画像
    - Session Memory: 单次会话上下文
    - Agent Memory: Agent 推理链和工具结果

    + 图记忆: 实体关系自动沉淀
    + 事件时间线: 法律时效追踪
    """

    def __init__(self) -> None:
        self._user_profiles: dict[str, dict[str, Any]] = {}  # user_id -> profile
        self._session_memories: dict[str, list[MemoryEntry]] = {}  # session_id -> entries
        self._session_artifacts: dict[str, dict[str, Any]] = {}  # session_id -> artifact_type -> data
        self._buffer: dict[str, list[dict[str, Any]]] = {}  # user_id -> pending messages
        self._buffer_threshold = 10  # 缓冲区满 10 条触发处理
        self.context_loader = ContextLoader()

    # ===== User Memory =====

    async def get_user_profile(self, user_id: str) -> dict[str, Any]:
        """获取用户法律画像"""
        if user_id in self._user_profiles:
            return self._user_profiles[user_id]

        # 尝试从数据库加载
        try:
            from src.services.investigation_data_store import investigation_data_store
            if investigation_data_store:
                prefs = await investigation_data_store.get_user_preference(user_id)
                if prefs:
                    profile: dict[str, Any] = copy.deepcopy(DEFAULT_LEGAL_PROFILE)
                    profile["interaction_pattern"]["preferred_depth"] = prefs.get("preferred_depth", "deep")
                    profile["interaction_pattern"]["report_format"] = prefs.get("preferred_report_template", "comprehensive")
                    profile["risk_profile"]["focus_dimensions"] = prefs.get("risk_focus_weights", {})
                    profile["interaction_pattern"]["frequent_queries"] = prefs.get("search_keywords_history", [])
                    profile["confidence"] = min(1.0, (prefs.get("total_investigations", 0) / 20))
                    self._user_profiles[user_id] = profile
                    return profile
        except Exception:
            pass

        profile = copy.deepcopy(DEFAULT_LEGAL_PROFILE)
        self._user_profiles[user_id] = profile
        return profile

    async def update_user_profile(self, user_id: str, updates: dict[str, Any]) -> None:
        """增量更新用户画像"""
        profile = await self.get_user_profile(user_id)

        for key, value in updates.items():
            if key in profile and isinstance(profile[key], dict) and isinstance(value, dict):
                profile[key].update(value)
            else:
                profile[key] = value

        profile["last_updated"] = datetime.now().isoformat()
        # 每次更新提升置信度
        profile["confidence"] = min(1.0, profile.get("confidence", 0) + 0.05)
        self._user_profiles[user_id] = profile

    async def get_user_context(self, user_id: str, max_tokens: int = 500) -> str:
        """
        获取用户画像的 prompt 注入格式（Memobase context() 思路）

        Returns:
            可直接注入 system prompt 的用户画像摘要
        """
        profile = await self.get_user_profile(user_id)

        parts = []
        bi = profile.get("basic_info", {})
        if bi.get("industry"):
            parts.append(f"行业: {bi['industry']}")
        if bi.get("company_type"):
            parts.append(f"企业类型: {bi['company_type']}")

        ln = profile.get("legal_needs", {})
        if ln.get("primary_domain"):
            parts.append(f"主要法律需求: {ln['primary_domain']}")

        rp = profile.get("risk_profile", {})
        if rp.get("focus_dimensions"):
            top_dims = sorted(rp["focus_dimensions"].items(), key=lambda x: x[1], reverse=True)[:3]
            if top_dims:
                parts.append(f"关注风险: {', '.join(d for d, _ in top_dims)}")

        ip = profile.get("interaction_pattern", {})
        if ip.get("frequent_queries"):
            parts.append(f"常搜: {', '.join(ip['frequent_queries'][:5])}")

        timeline = profile.get("timeline_events", [])
        upcoming = [e for e in timeline if e.get("date", "") > datetime.now().isoformat()[:10]]
        if upcoming:
            parts.append(f"待关注事件: {len(upcoming)} 项")

        if not parts:
            return ""

        return f"[用户画像 置信度{profile.get('confidence', 0):.0%}] " + " | ".join(parts)

    # ===== Session Memory =====

    def add_session_memory(
        self,
        session_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """添加会话记忆"""
        if session_id not in self._session_memories:
            self._session_memories[session_id] = []

        entry = MemoryEntry(
            content=content,
            memory_type="session",
            session_id=session_id,
            metadata=metadata,
        )
        self._session_memories[session_id].append(entry)

    def get_session_context(self, session_id: str, max_entries: int = 10) -> list[dict[str, Any]]:
        """获取会话记忆"""
        entries = self._session_memories.get(session_id, [])
        return [e.to_dict() for e in entries[-max_entries:]]

    async def get_session_artifact(self, session_id: str, artifact_type: str) -> Any | None:
        """获取会话级中间产物，用于跨会话上下文交接。"""
        return self._session_artifacts.get(session_id, {}).get(artifact_type)

    async def set_session_artifact(
        self,
        session_id: str,
        artifact_type: str,
        data: Any,
    ) -> None:
        """保存会话级中间产物，用于跨会话上下文交接。"""
        self._session_artifacts.setdefault(session_id, {})[artifact_type] = data

    # ===== Buffer & Batch Processing (Memobase 思路) =====

    async def buffer_message(self, user_id: str, message: dict[str, Any]) -> None:
        """缓冲消息，达到阈值时批量处理"""
        if user_id not in self._buffer:
            self._buffer[user_id] = []

        self._buffer[user_id].append({
            **message,
            "timestamp": datetime.now().isoformat(),
        })

        # 触发批量处理
        if len(self._buffer[user_id]) >= self._buffer_threshold:
            await self._flush_buffer(user_id)

    async def _flush_buffer(self, user_id: str) -> None:
        """
        批量处理缓冲区（Memobase flush 思路）

        从对话中提取：
        1. 用户偏好更新
        2. 法律时效事件
        3. 实体关系
        """
        messages = self._buffer.pop(user_id, [])
        if not messages:
            return

        # 提取用户偏好信号
        updates: dict[str, Any] = {}
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                # 检测行业关键词
                from src.services.lawyer_matching_service import DOMAIN_KEYWORDS, DOMAIN_LABELS
                for domain, keywords in DOMAIN_KEYWORDS.items():
                    if any(kw in content for kw in keywords):
                        updates.setdefault("legal_needs", {})["primary_domain"] = DOMAIN_LABELS.get(domain, domain)
                        break

        if updates:
            await self.update_user_profile(user_id, updates)

        # 通知 AutoDream 有新活动
        try:
            from src.services.auto_dream import auto_dream_engine
            auto_dream_engine.record_activity(user_id, "conversation")
        except Exception:
            pass

    # ===== L0/L1/L2 Context Loading =====

    def load_context(
        self,
        content: Any,
        content_type: str = "general",
        level: int = 1,
    ) -> str:
        """
        按层级加载内容

        Args:
            content: 原始内容
            content_type: general/contract/case/regulation/investigation
            level: 0=L0, 1=L1, 2=L2

        Returns:
            对应层级的内容
        """
        if isinstance(content, dict):
            content_str = json.dumps(content, ensure_ascii=False)
        else:
            content_str = str(content)

        if level == 0:
            return self.context_loader.generate_l0(content_str, content_type)
        elif level == 1:
            return self.context_loader.generate_l1(content_str, content_type)
        else:
            return content_str  # L2: 完整内容

    # ===== Timeline Events =====

    async def add_timeline_event(
        self,
        user_id: str,
        event_type: str,
        title: str,
        date: str,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        添加法律时效事件到用户时间线

        event_type: contract_expiry / statute_limitation / regulation_change / hearing_date
        """
        profile = await self.get_user_profile(user_id)
        events = profile.get("timeline_events", [])

        events.append({
            "event_type": event_type,
            "title": title,
            "date": date,
            "description": description,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
        })

        # 按日期排序
        events.sort(key=lambda e: e.get("date", ""))
        profile["timeline_events"] = events
        self._user_profiles[user_id] = profile

    async def get_upcoming_events(
        self,
        user_id: str,
        days_ahead: int = 30,
    ) -> list[dict[str, Any]]:
        """获取即将到来的法律时效事件"""
        profile = await self.get_user_profile(user_id)
        events = profile.get("timeline_events", [])

        now = datetime.now().strftime("%Y-%m-%d")
        cutoff = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        return [e for e in events if now <= e.get("date", "") <= cutoff]

    # ===== 综合上下文构建 =====

    async def build_enriched_context(
        self,
        user_id: str,
        session_id: str | None = None,
        query: str = "",
        max_tokens: int = 1000,
    ) -> str:
        """
        构建增强上下文（注入 system prompt）

        融合：用户画像 + 会话记忆 + 即将到期事件
        控制在 max_tokens 以内
        """
        parts = []

        # 1. 用户画像 (L1)
        user_ctx = await self.get_user_context(user_id, max_tokens=300)
        if user_ctx:
            parts.append(user_ctx)

        # 2. 即将到期事件
        upcoming = await self.get_upcoming_events(user_id, days_ahead=7)
        if upcoming:
            event_strs = [f"- {e['title']}({e['date']})" for e in upcoming[:3]]
            parts.append(f"[近期法律事件] {'; '.join(event_strs)}")

        # 3. 会话记忆摘要 (L0)
        if session_id:
            session_entries = self.get_session_context(session_id, max_entries=5)
            if session_entries:
                summaries = [self.context_loader.generate_l0(e["content"]) for e in session_entries]
                parts.append(f"[会话上下文] {'；'.join(summaries[-3:])}")

        return "\n".join(parts) if parts else ""


# 全局实例
memory_layer = MemoryLayer()
