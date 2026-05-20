"""
Experience Engine — 经验积累与持续学习引擎

灵感来源：
- Claude Code continuous-learning skill（会话结束时自动提取模式）
- AutoDream Phase 2 信号收集（跨会话模式识别）

五类可检测模式：
1. error_resolution — 错误解决方案（遇到XX错误 → 用XX方法修复）
2. user_corrections — 用户纠正模式（用户说"不对" → 正确做法是XX）
3. legal_patterns — 法律实务模式（XX类纠纷 → 适用XX法条）
4. workflow_optimizations — 工作流优化（做XX任务时 → 先做A再做B效果好）
5. domain_knowledge — 领域知识（XX行业 → 常见法律风险是XX）

经验生命周期：
- 创建：从会话/调查中自动提取
- 积累：相同模式重复出现 → 置信度提升
- 衰减：长期未使用 → 置信度下降
- 淘汰：置信度低于阈值 → 标记为过期
- 矛盾处理：新经验与旧经验冲突 → 保留新的，降级旧的
"""

import hashlib
from datetime import datetime
from typing import Any, TypedDict

from loguru import logger

# ===== 配置 =====

SessionMessage = dict[str, Any]
StringMap = dict[str, str]
ExperienceData = dict[str, Any]


class ExperienceConfig(TypedDict):
    min_confidence: float
    initial_confidence: float
    confirmed_boost: float
    contradiction_penalty: float
    decay_rate_per_day: float
    max_experiences: int
    extraction_threshold: int


EXPERIENCE_CONFIG: ExperienceConfig = {
    "min_confidence": 0.3,  # 最低置信度（低于此值标记过期）
    "initial_confidence": 0.6,  # 新经验初始置信度
    "confirmed_boost": 0.15,  # 每次确认提升
    "contradiction_penalty": 0.3,  # 矛盾时降级
    "decay_rate_per_day": 0.005,  # 每日衰减率
    "max_experiences": 500,  # 单用户最大经验数
    "extraction_threshold": 10,  # 最少 10 条消息才触发提取
}

PATTERN_CATEGORIES = [
    "error_resolution",
    "user_corrections",
    "legal_patterns",
    "workflow_optimizations",
    "domain_knowledge",
]

# 模式检测关键词
CORRECTION_KEYWORDS = ["不对", "错了", "不是", "应该是", "修改", "纠正", "重新", "换个", "别用"]
ERROR_KEYWORDS = ["报错", "失败", "异常", "错误", "bug", "error", "fail", "exception"]
LEGAL_KEYWORDS = ["依据", "法条", "适用", "判例", "司法解释", "根据", "规定", "条款"]


class Experience:
    """单条经验"""

    def __init__(
        self,
        pattern: str,
        category: str,
        context: str,
        solution: str = "",
        confidence: float = 0.6,
        source: str = "auto",
        user_id: str | None = None,
    ) -> None:
        self.id = hashlib.md5(
            f"{pattern}{context}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        self.pattern = pattern  # 触发条件
        self.category = category  # 模式类别
        self.context = context  # 上下文描述
        self.solution = solution  # 解决方案/结论
        self.confidence = confidence
        self.source = source
        self.user_id = user_id
        self.created_at = datetime.now()
        self.last_used_at = datetime.now()
        self.use_count = 0
        self.confirmed_count = 0
        self.contradicted_count = 0
        self.is_active = True

    def use(self) -> None:
        """标记为使用过"""
        self.last_used_at = datetime.now()
        self.use_count += 1

    def confirm(self) -> None:
        """确认有效，提升置信度"""
        self.confirmed_count += 1
        self.confidence = min(0.95, self.confidence + EXPERIENCE_CONFIG["confirmed_boost"])
        self.last_used_at = datetime.now()

    def contradict(self, new_evidence: str = "") -> None:
        """矛盾，降低置信度"""
        self.contradicted_count += 1
        self.confidence -= EXPERIENCE_CONFIG["contradiction_penalty"]
        if self.confidence < EXPERIENCE_CONFIG["min_confidence"]:
            self.is_active = False

    def decay(self) -> None:
        """日常衰减"""
        days_since = (datetime.now() - self.last_used_at).days
        if days_since > 0:
            self.confidence -= EXPERIENCE_CONFIG["decay_rate_per_day"] * days_since
            if self.confidence < EXPERIENCE_CONFIG["min_confidence"]:
                self.is_active = False

    def to_dict(self) -> ExperienceData:
        return {
            "id": self.id,
            "pattern": self.pattern,
            "category": self.category,
            "context": self.context,
            "solution": self.solution,
            "confidence": round(self.confidence, 3),
            "use_count": self.use_count,
            "confirmed_count": self.confirmed_count,
            "contradicted_count": self.contradicted_count,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat(),
        }


class ExperienceEngine:
    """
    经验积累引擎（Harness 增强版）

    改进：经验数据持久化到 PostgreSQL experience_patterns 表，
    服务重启后自动恢复，不再丢失学习成果。
    """

    def __init__(self) -> None:
        self._store: dict[str, list[Experience]] = {}  # user_id -> experiences（内存缓存）
        self._persistence_enabled = False
        self._try_enable_persistence()

    def _try_enable_persistence(self) -> None:
        """尝试启用数据库持久化"""
        try:
            self._persistence_enabled = True
            logger.info("[ExperienceEngine] 数据库持久化已启用")
        except Exception:
            logger.debug("[ExperienceEngine] 数据库不可用，使用内存模式")

    def _get_user_experiences(self, user_id: str) -> list[Experience]:
        if user_id not in self._store:
            self._store[user_id] = []
        return self._store[user_id]

    async def _persist_experience(self, exp: Experience) -> None:
        """将经验持久化到数据库"""
        if not self._persistence_enabled:
            return
        try:
            from sqlalchemy import text

            from src.core.database import async_session_maker

            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        INSERT INTO experience_patterns
                        (id, user_id, pattern, category, context, solution, confidence,
                         source, use_count, confirmed_count, contradicted_count, is_active, status)
                        VALUES (:id, :user_id, :pattern, :category, :context, :solution, :confidence,
                                :source, :use_count, :confirmed_count, :contradicted_count, :is_active, :status)
                        ON CONFLICT (id) DO UPDATE SET
                            confidence = :confidence,
                            use_count = :use_count,
                            confirmed_count = :confirmed_count,
                            contradicted_count = :contradicted_count,
                            is_active = :is_active,
                            status = :status,
                            last_used_at = NOW()
                    """),
                    {
                        "id": exp.id,
                        "user_id": exp.user_id,
                        "pattern": exp.pattern,
                        "category": exp.category,
                        "context": exp.context,
                        "solution": exp.solution,
                        "confidence": exp.confidence,
                        "source": exp.source,
                        "use_count": exp.use_count,
                        "confirmed_count": exp.confirmed_count,
                        "contradicted_count": exp.contradicted_count,
                        "is_active": exp.is_active,
                        "status": "candidate" if exp.confirmed_count == 0 else "validated",
                    },
                )
                await db.commit()
        except Exception as e:
            logger.debug(f"[ExperienceEngine] 持久化失败: {e}")

    async def load_user_experiences(self, user_id: str) -> list[Experience]:
        """从数据库加载用户经验（启动时或首次访问时）"""
        if user_id in self._store and self._store[user_id]:
            return self._store[user_id]
        if not self._persistence_enabled:
            return []
        try:
            from sqlalchemy import text

            from src.core.database import async_session_maker

            async with async_session_maker() as db:
                result = await db.execute(
                    text("""
                        SELECT id, pattern, category, context, solution, confidence,
                               source, use_count, confirmed_count, contradicted_count, is_active
                        FROM experience_patterns
                        WHERE user_id = :user_id AND is_active = true
                        ORDER BY confidence DESC
                        LIMIT :limit
                    """),
                    {"user_id": user_id, "limit": EXPERIENCE_CONFIG["max_experiences"]},
                )
                rows = result.fetchall()
                experiences = []
                for row in rows:
                    exp = Experience(
                        pattern=row.pattern,
                        category=row.category,
                        context=row.context,
                        solution=row.solution,
                        confidence=row.confidence,
                        source=row.source,
                        user_id=user_id,
                    )
                    exp.id = row.id
                    exp.use_count = row.use_count
                    exp.confirmed_count = row.confirmed_count
                    exp.contradicted_count = row.contradicted_count
                    exp.is_active = row.is_active
                    experiences.append(exp)
                self._store[user_id] = experiences
                if experiences:
                    logger.info(
                        f"[ExperienceEngine] 加载 {len(experiences)} 条经验 (user={user_id[:8]})"
                    )
                return experiences
        except Exception as e:
            logger.debug(f"[ExperienceEngine] 加载经验失败: {e}")
            return []

    # ===== 经验提取 =====

    async def extract_from_session(
        self,
        user_id: str,
        messages: list[SessionMessage],
    ) -> list[Experience]:
        """
        从会话中自动提取经验模式

        在会话结束时调用（continuous-learning 思路）
        """
        if len(messages) < EXPERIENCE_CONFIG["extraction_threshold"]:
            return []

        extracted: list[Experience] = []

        # 1. 提取用户纠正模式
        corrections = self._detect_corrections(messages)
        for corr in corrections:
            exp = Experience(
                pattern=corr["trigger"],
                category="user_corrections",
                context=corr["context"],
                solution=corr["correction"],
                user_id=user_id,
            )
            extracted.append(exp)

        # 2. 提取法律实务模式
        legal = self._detect_legal_patterns(messages)
        for lp in legal:
            exp = Experience(
                pattern=lp["issue"],
                category="legal_patterns",
                context=lp["context"],
                solution=lp["resolution"],
                user_id=user_id,
            )
            extracted.append(exp)

        # 3. 提取错误解决方案
        errors = self._detect_error_resolutions(messages)
        for err in errors:
            exp = Experience(
                pattern=err["error"],
                category="error_resolution",
                context=err["context"],
                solution=err["fix"],
                user_id=user_id,
            )
            extracted.append(exp)

        # 合并到用户经验库（去重+矛盾处理）
        user_exps = self._get_user_experiences(user_id)
        for new_exp in extracted:
            existing = self._find_similar(user_exps, new_exp)
            if existing:
                # 相同模式 → 确认
                existing.confirm()
                # Harness: 持久化确认更新
                await self._persist_experience(existing)
            else:
                # 新模式 → 添加
                user_exps.append(new_exp)
                # Harness: 持久化新经验
                await self._persist_experience(new_exp)

        # 限制数量
        if len(user_exps) > EXPERIENCE_CONFIG["max_experiences"]:
            user_exps.sort(key=lambda e: e.confidence, reverse=True)
            self._store[user_id] = user_exps[: EXPERIENCE_CONFIG["max_experiences"]]

        logger.info(f"经验提取完成 (user={user_id}): 新增 {len(extracted)} 条，已持久化")
        return extracted

    def _detect_corrections(self, messages: list[SessionMessage]) -> list[StringMap]:
        """检测用户纠正模式"""
        corrections: list[StringMap] = []
        for i, msg in enumerate(messages):
            if msg.get("role") != "user":
                continue
            content = msg.get("content", "")
            if any(kw in content for kw in CORRECTION_KEYWORDS):
                # 找到纠正前 AI 说了什么
                prev_ai = ""
                for j in range(i - 1, -1, -1):
                    if messages[j].get("role") == "assistant":
                        prev_ai = messages[j].get("content", "")[:200]
                        break
                corrections.append(
                    {
                        "trigger": prev_ai[:100] if prev_ai else "未知触发",
                        "context": "AI回复后用户纠正",
                        "correction": content[:200],
                    }
                )
        return corrections

    def _detect_legal_patterns(self, messages: list[SessionMessage]) -> list[StringMap]:
        """检测法律实务模式"""
        patterns: list[StringMap] = []
        for i, msg in enumerate(messages):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            if any(kw in content for kw in LEGAL_KEYWORDS):
                # 提取法条引用上下文
                import re

                citations = re.findall(r"《([^》]+)》(?:第\d+条)?", content)
                if citations:
                    # 找用户问的问题
                    user_q = ""
                    for j in range(i - 1, -1, -1):
                        if messages[j].get("role") == "user":
                            user_q = messages[j].get("content", "")[:150]
                            break
                    patterns.append(
                        {
                            "issue": user_q[:80] if user_q else "法律问题",
                            "context": f"引用了 {', '.join(citations[:3])}",
                            "resolution": content[:200],
                        }
                    )
        return patterns

    def _detect_error_resolutions(self, messages: list[SessionMessage]) -> list[StringMap]:
        """检测错误解决模式"""
        resolutions: list[StringMap] = []
        error_context: str | None = None

        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")

            if any(kw in content.lower() for kw in ERROR_KEYWORDS):
                error_context = content[:200]
            elif error_context and role == "assistant" and len(content) > 50:
                # 可能是解决方案
                resolutions.append(
                    {
                        "error": error_context[:100],
                        "context": "错误解决",
                        "fix": content[:200],
                    }
                )
                error_context = None

        return resolutions

    def _find_similar(self, experiences: list[Experience], new: Experience) -> Experience | None:
        """找相似的已有经验"""
        for exp in experiences:
            if not exp.is_active:
                continue
            if exp.category != new.category:
                continue
            # 简单相似度：模式前 50 字匹配
            if exp.pattern[:50] == new.pattern[:50]:
                return exp
        return None

    # ===== 经验检索 =====

    async def search_experiences(
        self,
        user_id: str,
        query: str,
        category: str | None = None,
        top_k: int = 5,
    ) -> list[ExperienceData]:
        """搜索相关经验"""
        experiences = self._get_user_experiences(user_id)

        # 过滤活跃 + 类别
        active = [e for e in experiences if e.is_active]
        if category:
            active = [e for e in active if e.category == category]

        # 简单关键词匹配评分
        scored: list[tuple[Experience, float]] = []
        query_lower = query.lower()
        for exp in active:
            score = 0.0
            if query_lower in exp.pattern.lower():
                score += 3
            if query_lower in exp.context.lower():
                score += 2
            if query_lower in exp.solution.lower():
                score += 1
            # 置信度加权
            score *= exp.confidence
            if score > 0:
                scored.append((exp, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        results: list[ExperienceData] = []
        for exp, score in scored[:top_k]:
            exp.use()  # 标记使用
            results.append({**exp.to_dict(), "relevance_score": round(score, 2)})

        return results

    # ===== 经验反馈 =====

    def confirm_experience(self, user_id: str, experience_id: str) -> bool:
        """确认经验有效"""
        for exp in self._get_user_experiences(user_id):
            if exp.id == experience_id:
                exp.confirm()
                return True
        return False

    def contradict_experience(
        self, user_id: str, experience_id: str, new_evidence: str = ""
    ) -> bool:
        """标记经验矛盾"""
        for exp in self._get_user_experiences(user_id):
            if exp.id == experience_id:
                exp.contradict(new_evidence)
                return True
        return False

    # ===== 日常维护 =====

    def decay_all(self, user_id: str) -> int:
        """对用户所有经验执行衰减"""
        experiences = self._get_user_experiences(user_id)
        decayed = 0
        for exp in experiences:
            old_active = exp.is_active
            exp.decay()
            if old_active and not exp.is_active:
                decayed += 1
        return decayed

    def get_stats(self, user_id: str) -> dict[str, Any]:
        """获取用户经验统计"""
        experiences = self._get_user_experiences(user_id)
        active = [e for e in experiences if e.is_active]
        return {
            "total": len(experiences),
            "active": len(active),
            "by_category": {
                cat: sum(1 for e in active if e.category == cat) for cat in PATTERN_CATEGORIES
            },
            "avg_confidence": round(sum(e.confidence for e in active) / max(len(active), 1), 3),
            "most_used": sorted(
                [e.to_dict() for e in active],
                key=lambda x: x["use_count"],
                reverse=True,
            )[:5],
        }

    def build_experience_context(self, user_id: str, query: str = "", max_tokens: int = 500) -> str:
        """
        构建经验上下文注入 prompt

        返回与当前查询最相关的经验摘要
        """
        experiences = self._get_user_experiences(user_id)
        active = [e for e in experiences if e.is_active and e.confidence > 0.5]

        if not active:
            return ""

        # 如果有查询，按相关性筛选
        if query:
            relevant = []
            for exp in active:
                if any(kw in query.lower() for kw in exp.pattern.lower().split()[:5]):
                    relevant.append(exp)
            if not relevant:
                relevant = sorted(active, key=lambda e: e.confidence, reverse=True)[:3]
        else:
            relevant = sorted(active, key=lambda e: e.confidence, reverse=True)[:5]

        lines = ["[历史经验]"]
        for exp in relevant[:5]:
            lines.append(
                f"- [{exp.category}] {exp.pattern[:60]} → {exp.solution[:80]} (置信度{exp.confidence:.0%})"
            )

        result = "\n".join(lines)
        return result[: max_tokens * 2]  # 粗估 token


# 全局实例
experience_engine = ExperienceEngine()
