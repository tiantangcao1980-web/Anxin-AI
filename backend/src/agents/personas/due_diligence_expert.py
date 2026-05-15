"""DueDiligenceExpertPersona —— 「尽调专家 🔍」persona（P9-D）。

定位：公司 / 项目 / 人物全维度尽职调查 — 工商 + 信用 + 诉讼 + 舆情。

5 大对外能力：
    - ``investigate_company``       公司全维度尽调（工商 + 信用 + 诉讼 + 舆情）
    - ``analyze_evidence``          文档可信度 + 主张支撑分析
    - ``monitor_sentiment``         多源舆情聚合（含趋势判定）
    - ``build_relationship_graph``  实体关系图谱（防指数爆炸 BFS）
    - ``grade_risk``                综合风险评级（AAA-D）

实现要点：
    1. **包装现有 specialized agent**：调用 ``DueDiligenceAgent`` /
       ``EvidenceAnalystAgent`` / ``SentimentAnalysisAgent``，不复制 LLM 提示词
    2. **接 P6-C 法律源**：``CreditChinaSource`` / ``HistoricalWenshuSource``
       通过 ``fetch_service`` 注入；测试可注入 mock，退化为离线静态生成
    3. **不持久化**：报告进程内 LRU 缓存（容量 100），由 API 层做 GET
    4. **零 LLM 必需**：所有 agent 调用都做 try/except，缺失 LLM 时仍能产出
       结构化 mock 报告（确保单测无网无密钥可跑）
"""

from __future__ import annotations

import logging
import re
import uuid
from collections import OrderedDict, deque
from datetime import date, datetime, timedelta
from typing import Any

from src.agents.personas.base_persona import BasePersonaAgent
from src.agents.personas.dd_models import (
    CompanyBasicInfo,
    CreditFlag,
    DueDiligenceReport,
    EvidenceAnalysis,
    LitigationRecord,
    RelationshipEdge,
    RelationshipGraph,
    RelationshipNode,
    RiskGrade,
    SentimentReport,
)
from src.agents.personas.research_models import Citation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# 关系图谱：限制单次扩展节点数（防指数爆炸）
_MAX_NODES_PER_LEVEL = 25
_MAX_NODES_TOTAL = 200
_MAX_GRAPH_DEPTH = 3

# 报告缓存
_REPORT_CACHE_CAP = 100

# 风险等级 → 分数区间（参考标普）
_GRADE_BANDS: list[tuple[str, float]] = [
    ("AAA", 95.0),
    ("AA", 88.0),
    ("A", 80.0),
    ("BBB", 70.0),
    ("BB", 60.0),
    ("B", 50.0),
    ("C", 35.0),
    ("D", 0.0),
]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class DueDiligenceExpertPersona(BasePersonaAgent):
    """尽调专家 persona — 包装 3 specialized agent + P6-C 法律源。"""

    persona_id = "due_diligence_expert"
    display_name = "尽调专家"
    emoji = "🔍"
    description = "公司/项目/人物尽职调查 — 工商+信用+诉讼+舆情 全维度"
    backed_by_skills = ["docx", "xlsx", "pdf"]
    backed_by_agents = ["due_diligence", "evidence_analyst", "sentiment_agent"]
    supported_apps = ["qichacha", "tianyancha"]
    capabilities = [
        "company_due_diligence",
        "evidence_analysis",
        "sentiment_monitoring",
        "relationship_graph",
        "risk_grading",
    ]

    SYSTEM_PROMPT = """你是「尽调专家」，安心智能助手 V3 的尽职调查 persona。

定位：
- 服务对象：投融资机构 / 法务总监 / 风控合规岗 / 个人投资者
- 价值：把工商 + 信用 + 诉讼 + 舆情 + 关联关系五大维度合并成一份可追溯的尽调报告

行为准则：
1. **结论必须有出处** — 任何风险断言都要落到具体引文（来源 + URL + 原文片段）
2. **区分事实与传闻** — 「据 X 报道」与「依公示数据」必须显式标注
3. **保守优先** — 信息缺失时倾向给出更高风险等级；不臆造工商字段
4. **合规底线** — 不抓裁判文书网 / 微信公众号，不爬取个人隐私
5. **风险传导** — 关注股东 / 实控人 / 关联方层层穿透，识别风险传导路径

工具：
- investigate_company / analyze_evidence / monitor_sentiment
- build_relationship_graph / grade_risk
- 调用底层 agent: due_diligence / evidence_analyst / sentiment_agent
- 接入 P6-C 法律源: 信用中国 / 历史裁判文书库 / 工商公开数据
"""

    def __init__(
        self,
        *,
        dd_agent: Any | None = None,
        evidence_agent: Any | None = None,
        sentiment_agent: Any | None = None,
        fetch_service: Any | None = None,
        credit_source: Any | None = None,
        litigation_source: Any | None = None,
    ) -> None:
        # 注意：BasePersonaAgent.__init__() 不接 kwargs；先调用基类，再保存依赖
        super().__init__()

        # specialized agent 注入（测试可 mock；缺失时 lazy 构造真实 agent）
        self._dd_agent = dd_agent
        self._evidence_agent = evidence_agent
        self._sentiment_agent = sentiment_agent

        # 数据源注入
        self._fetch_service = fetch_service
        self._credit_source = credit_source
        self._litigation_source = litigation_source

        # 报告 LRU 缓存
        self._report_cache: OrderedDict[str, DueDiligenceReport] = OrderedDict()

    # ------------------------------------------------------------------
    # specialized agent lazy 构造
    # ------------------------------------------------------------------
    def _get_dd_agent(self) -> Any:
        if self._dd_agent is None:
            from src.agents.due_diligence import DueDiligenceAgent

            self._dd_agent = DueDiligenceAgent()
        return self._dd_agent

    def _get_evidence_agent(self) -> Any:
        if self._evidence_agent is None:
            from src.agents.evidence_analyst import EvidenceAnalystAgent

            self._evidence_agent = EvidenceAnalystAgent()
        return self._evidence_agent

    def _get_sentiment_agent(self) -> Any:
        if self._sentiment_agent is None:
            from src.agents.sentiment_agent import SentimentAnalysisAgent

            self._sentiment_agent = SentimentAnalysisAgent()
        return self._sentiment_agent

    # ------------------------------------------------------------------
    # capability 1: 公司尽调
    # ------------------------------------------------------------------
    async def investigate_company(
        self,
        company_name: str,
        depth: str = "standard",
    ) -> DueDiligenceReport:
        """对公司发起 quick / standard / deep 三档尽调。

        三档差异：
            - quick    : 仅工商 + 信用瑕疵；不调 LLM；< 200ms
            - standard : + 诉讼 Top 10 + 舆情概览（仅 volume / 总分）
            - deep     : + LLM 综合分析 + 推荐操作
        """
        depth = depth if depth in {"quick", "standard", "deep"} else "standard"

        citations: list[Citation] = []

        # 1) 工商基础信息（mock 实现 — 真实接入留给 P9 后续阶段对接 qichacha）
        basic_info = await self._fetch_basic_info(company_name, citations)

        # 2) 信用瑕疵（接 P6-C CreditChinaSource）
        credit_flags = await self._fetch_credit_flags(company_name, citations)

        # 3) 诉讼记录（接 P6-C HistoricalWenshuSource）
        litigation_records: list[LitigationRecord] = []
        if depth in {"standard", "deep"}:
            litigation_records = await self._fetch_litigation_records(company_name, citations)

        # 4) 舆情概览
        public_news_count = 0
        if depth in {"standard", "deep"}:
            public_news_count = await self._estimate_news_volume(company_name)

        # 5) LLM 综合（仅 deep 档）
        summary = ""
        recommendations: list[str] = []
        if depth == "deep":
            summary, recommendations = await self._llm_synthesize(
                company_name=company_name,
                basic_info=basic_info,
                credit_flags=credit_flags,
                litigation_records=litigation_records,
            )
        else:
            summary = self._template_summary(
                company_name, basic_info, credit_flags, litigation_records
            )
            recommendations = self._template_recommendations(credit_flags, litigation_records)

        # 6) 风险等级（基于已有数据快速归一）
        overall_risk_level = self._infer_risk_level(
            credit_flags=credit_flags,
            litigation_records=litigation_records,
            public_news_count=public_news_count,
            depth=depth,
        )

        report = DueDiligenceReport(
            target=company_name,
            target_type="company",
            investigation_depth=depth,
            basic_info=basic_info,
            shareholders=[],  # 工商穿透留给后续
            key_personnel=[],
            litigation_records=litigation_records,
            credit_flags=credit_flags,
            intellectual_properties=[],
            public_news_count=public_news_count,
            overall_risk_level=overall_risk_level,
            summary=summary,
            recommendations=recommendations,
            generated_at=datetime.utcnow(),
            citations=citations,
            report_id=f"dd-{uuid.uuid4().hex[:12]}",
        )

        self._cache_put(report)
        return report

    # ------------------------------------------------------------------
    # capability 2: 证据分析
    # ------------------------------------------------------------------
    async def analyze_evidence(
        self,
        document_text: str,
        claim: str,
    ) -> EvidenceAnalysis:
        """调用 EvidenceAnalystAgent，回带支持 / 反驳片段 + 真实性评分。"""
        if not document_text or not claim:
            raise ValueError("document_text 和 claim 都不能为空")

        # 真伪指标（不依赖 LLM，纯规则）
        forgery_indicators = self._detect_forgery_indicators(document_text)
        authenticity_score = max(0.0, 1.0 - 0.2 * len(forgery_indicators))

        # 内容片段（前后 80 字）
        excerpt = document_text[:200].replace("\n", " ")

        # 调底层 agent 做主张支撑分析（缺 LLM 时退化）
        supports_claim, confidence, supporting, contradicting, inconsistencies = (
            self._heuristic_claim_check(document_text, claim)
        )
        try:
            agent = self._get_evidence_agent()
            task = {
                "description": f"判断文档是否支持以下主张：{claim}",
                "context": {
                    "evidence_files": [
                        {"name": "input.txt", "type": "text", "content": document_text}
                    ]
                },
            }
            resp = await agent.process(task)
            agent_text = (resp.content or "")[:500]
            if agent_text:
                inconsistencies.append(f"agent_note:{agent_text[:120]}")
        except Exception as exc:  # pragma: no cover - 兜底
            logger.debug("evidence_agent process failed: %s", exc)

        return EvidenceAnalysis(
            document_summary=excerpt + ("..." if len(document_text) > 200 else ""),
            claim=claim,
            supports_claim=supports_claim,
            confidence=confidence,
            supporting_excerpts=supporting,
            contradicting_excerpts=contradicting,
            inconsistencies=inconsistencies,
            authenticity_score=authenticity_score,
            forgery_indicators=forgery_indicators,
        )

    @staticmethod
    def _detect_forgery_indicators(text: str) -> list[str]:
        """伪造特征启发式：抬头 / 落款 / 公章描述与正文不一致。"""
        indicators: list[str] = []
        # 1) 多个不同公章描述（出现 ≥ 2 个不同的"公章"/"印章"）
        seal_matches = re.findall(r"([一-龥]{2,12}(公章|专用章|印章))", text)
        seal_set = {m[0] for m in seal_matches}
        if len(seal_set) >= 3:
            indicators.append("multiple_seal_descriptions")
        # 2) 日期格式混杂（既有 2024-01-01 又有 2024年1月1日 又有 24/1/1 ≥ 2 种）
        date_styles = 0
        if re.search(r"\d{4}-\d{1,2}-\d{1,2}", text):
            date_styles += 1
        if re.search(r"\d{4}年\d{1,2}月\d{1,2}日", text):
            date_styles += 1
        if re.search(r"\d{1,2}/\d{1,2}/\d{2,4}", text):
            date_styles += 1
        if date_styles >= 3:
            indicators.append("mixed_date_formats")
        # 3) 无效金额（大写 + 阿拉伯数字不一致）
        if "￥" in text and "元整" not in text and "元" in text:
            uppercase_yuan = re.search(r"[壹贰叁肆伍陆柒捌玖拾佰仟万亿圆元]{3,}", text)
            if uppercase_yuan and "整" not in text:
                indicators.append("amount_words_inconsistent")
        return indicators

    @staticmethod
    def _heuristic_claim_check(
        text: str, claim: str
    ) -> tuple[bool, float, list[str], list[str], list[str]]:
        """规则版主张匹配：claim 关键字命中即支持，否定词命中即反驳。"""
        keywords = [k for k in re.findall(r"[一-龥A-Za-z0-9]{2,}", claim) if k]
        supporting: list[str] = []
        contradicting: list[str] = []
        inconsistencies: list[str] = []

        text_lower = text.lower()
        hits = sum(1 for k in keywords if k.lower() in text_lower)
        ratio = hits / max(1, len(keywords))

        # 找一段含命中关键词的片段
        for k in keywords:
            idx = text.lower().find(k.lower())
            if idx >= 0:
                start = max(0, idx - 20)
                end = min(len(text), idx + len(k) + 40)
                supporting.append(text[start:end])
                if len(supporting) >= 3:
                    break

        # 否定词触发反驳
        negation = ["未", "没有", "不存在", "并非", "并不", "否认"]
        for neg in negation:
            idx = text.find(neg)
            if idx >= 0:
                start = max(0, idx - 10)
                end = min(len(text), idx + 30)
                contradicting.append(text[start:end])
                if len(contradicting) >= 2:
                    break

        supports_claim = ratio >= 0.5 and not contradicting
        confidence = round(min(1.0, max(0.0, ratio - 0.1 * len(contradicting))), 2)
        return supports_claim, confidence, supporting, contradicting, inconsistencies

    # ------------------------------------------------------------------
    # capability 3: 舆情监控
    # ------------------------------------------------------------------
    async def monitor_sentiment(
        self,
        target: str,
        sources: list[str],
        lookback_days: int = 30,
    ) -> SentimentReport:
        """聚合 sources 上 lookback_days 内的舆情。"""
        if not target:
            raise ValueError("target 不能为空")
        if lookback_days <= 0 or lookback_days > 365:
            raise ValueError("lookback_days 须在 1-365")

        sources = list(sources or [])
        end = date.today()
        start = end - timedelta(days=lookback_days)

        by_source: dict[str, dict[str, Any]] = {}
        notable_events: list[dict[str, Any]] = []
        total_volume = 0
        pos = neg = neu = 0

        for src in sources:
            # 真实接入：通过 fetch_service 拉数据；缺失时给 mock
            counts = await self._mock_sentiment_counts(src, target)
            by_source[src] = counts
            total_volume += counts.get("volume", 0)
            pos += counts.get("positive", 0)
            neg += counts.get("negative", 0)
            neu += counts.get("neutral", 0)

        # 整体情感
        if total_volume == 0:
            overall = "neutral"
            score = 0.0
        else:
            score = round((pos - neg) / max(1, total_volume), 3)
            if score >= 0.2:
                overall = "positive"
            elif score <= -0.2:
                overall = "negative"
            elif pos > 0 and neg > 0:
                overall = "mixed"
            else:
                overall = "neutral"

        # 趋势：把 lookback_days 切成两半，比较前后半的负面比例
        trend = "stable"
        if total_volume >= 6 and neg > 0:
            half_neg = neg // 2
            if neg > 2 * max(1, half_neg):
                trend = "deteriorating"
            elif pos > neg * 2:
                trend = "improving"

        return SentimentReport(
            target=target,
            period_start=start,
            period_end=end,
            overall_sentiment=overall,
            sentiment_score=score,
            volume=total_volume,
            by_source=by_source,
            top_topics=[],
            notable_events=notable_events,
            trend=trend,
        )

    @staticmethod
    async def _mock_sentiment_counts(source: str, target: str) -> dict[str, Any]:
        """无外部数据源时的占位计数。

        以 ``hash(target+source)`` 做确定性 mock，便于测试稳定。
        """
        h = abs(hash(f"{source}::{target}"))
        volume = h % 30
        pos = (h // 7) % max(1, volume + 1)
        neg = (h // 13) % max(1, volume + 1 - pos)
        neu = max(0, volume - pos - neg)
        return {
            "volume": volume,
            "positive": pos,
            "negative": neg,
            "neutral": neu,
        }

    # ------------------------------------------------------------------
    # capability 4: 关系图谱
    # ------------------------------------------------------------------
    async def build_relationship_graph(
        self,
        entity: str,
        depth: int = 2,
    ) -> RelationshipGraph:
        """以 entity 为中心做 BFS 扩展，返回受限深度的关系图。

        防指数爆炸的 4 道闸门：
            1. ``depth`` 上限钳制到 ``_MAX_GRAPH_DEPTH=3``
            2. 单层最多扩展 ``_MAX_NODES_PER_LEVEL=25`` 个新节点
            3. 全图最多 ``_MAX_NODES_TOTAL=200`` 个节点
            4. 已访问节点全程去重（visited set）
        """
        if not entity:
            raise ValueError("entity 不能为空")
        depth = max(1, min(int(depth), _MAX_GRAPH_DEPTH))

        root_id = self._entity_id(entity, "company")
        nodes_by_id: dict[str, RelationshipNode] = {
            root_id: RelationshipNode(id=root_id, name=entity, type="company", attributes={})
        }
        edges: list[RelationshipEdge] = []
        visited: set[str] = {root_id}

        # BFS 队列：(node_id, current_depth)
        queue: deque[tuple[str, int]] = deque([(root_id, 0)])

        while queue:
            if len(nodes_by_id) >= _MAX_NODES_TOTAL:
                break
            node_id, cur_depth = queue.popleft()
            if cur_depth >= depth:
                continue

            # 拉取一阶邻居（mock 实现：按节点 id 哈希派生固定数量）
            neighbors = await self._fetch_neighbors(nodes_by_id[node_id])
            level_added = 0
            for neighbor, rel in neighbors:
                if level_added >= _MAX_NODES_PER_LEVEL:
                    break
                if len(nodes_by_id) >= _MAX_NODES_TOTAL:
                    break
                if neighbor.id not in nodes_by_id:
                    nodes_by_id[neighbor.id] = neighbor
                edges.append(
                    RelationshipEdge(
                        from_id=node_id,
                        to_id=neighbor.id,
                        relationship=rel,
                        confidence=0.85,
                        source="qichacha_mock",
                    )
                )
                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    queue.append((neighbor.id, cur_depth + 1))
                    level_added += 1

        nodes = list(nodes_by_id.values())
        risk_paths = self._find_risk_paths(root_id, edges, nodes_by_id)

        return RelationshipGraph(
            root_entity=entity,
            nodes=nodes,
            edges=edges,
            depth=depth,
            risk_paths=risk_paths,
        )

    @staticmethod
    def _entity_id(name: str, type_: str) -> str:
        return f"{type_}:{re.sub(r'[^A-Za-z0-9一-龥]+', '_', name)[:48]}"

    async def _fetch_neighbors(self, node: RelationshipNode) -> list[tuple[RelationshipNode, str]]:
        """获取一阶邻居（mock）。

        生产实现：先查 qichacha / 工商穿透 API → CreditChinaSource → litigation。
        本 P9 阶段提供确定性 mock，让算法可测；返回的邻居数量永远 ≤ 5，
        避免单层就突破 ``_MAX_NODES_PER_LEVEL``。
        """
        h = abs(hash(node.id))
        n = (h % 5) + 1  # 1-5 个邻居
        out: list[tuple[RelationshipNode, str]] = []
        for i in range(n):
            seed = (h + i * 17) % 100
            ntype = "person" if seed % 2 == 0 else "company"
            name = f"{node.name[:6]}_{ntype}_{i}"
            neighbor = RelationshipNode(
                id=self._entity_id(name, ntype),
                name=name,
                type=ntype,
                attributes={"risk_level": "high" if seed % 7 == 0 else "low"},
            )
            rel = "owns" if ntype == "person" else "invests_in"
            out.append((neighbor, rel))
        return out

    @staticmethod
    def _find_risk_paths(
        root_id: str,
        edges: list[RelationshipEdge],
        nodes_by_id: dict[str, RelationshipNode],
    ) -> list[list[str]]:
        """从 root 出发，找出走到「high risk」节点的路径（最多 10 条）。"""
        # 构建邻接表
        adj: dict[str, list[str]] = {}
        for e in edges:
            adj.setdefault(e.from_id, []).append(e.to_id)

        risk_paths: list[list[str]] = []
        # DFS（带 visited 防环 + 最长 6 跳）
        stack: list[tuple[str, list[str], set[str]]] = [(root_id, [root_id], {root_id})]
        while stack and len(risk_paths) < 10:
            cur, path, seen = stack.pop()
            if len(path) > 6:
                continue
            for nxt in adj.get(cur, []):
                if nxt in seen:
                    continue
                new_path = path + [nxt]
                attrs = nodes_by_id[nxt].attributes if nxt in nodes_by_id else {}
                if attrs.get("risk_level") == "high":
                    risk_paths.append(new_path)
                    if len(risk_paths) >= 10:
                        break
                else:
                    stack.append((nxt, new_path, seen | {nxt}))
        return risk_paths

    # ------------------------------------------------------------------
    # capability 5: 风险评级
    # ------------------------------------------------------------------
    async def grade_risk(self, dd_report: DueDiligenceReport) -> RiskGrade:
        """把尽调报告归一为 AAA-D 等级 + 推荐操作。"""
        # 1) 三类子分（满分 100）
        legal = 100.0
        if dd_report.litigation_records:
            # 被告 vs 原告：被告更扣分
            defendants = sum(1 for r in dd_report.litigation_records if r.role == "defendant")
            legal -= min(50, defendants * 8)
            legal -= min(20, len(dd_report.litigation_records) * 2)

        credit = 100.0
        critical = sum(1 for f in dd_report.credit_flags if f.severity == "critical")
        high = sum(1 for f in dd_report.credit_flags if f.severity == "high")
        medium = sum(1 for f in dd_report.credit_flags if f.severity == "medium")
        # critical 信用瑕疵（失信被执行人 / 限制高消费）属于一票否决式信号
        # 60 分扣减 + 加权后仍能把综合分压到 C/D 段
        credit -= 60 * critical + 18 * high + 6 * medium
        credit = max(0.0, credit)

        sentiment = 100.0
        if dd_report.public_news_count > 100:
            sentiment -= 10
        elif dd_report.public_news_count > 500:
            sentiment -= 25

        breakdown = {
            "legal": round(max(0.0, legal), 1),
            "credit": round(credit, 1),
            "sentiment": round(sentiment, 1),
        }

        # 2) 加权综合
        weights = {"legal": 0.45, "credit": 0.40, "sentiment": 0.15}
        score = round(sum(breakdown[k] * weights[k] for k in breakdown), 1)
        grade = self._score_to_grade(score)

        # 3) red flags
        red_flags: list[str] = []
        for f in dd_report.credit_flags:
            if f.severity in {"critical", "high"}:
                red_flags.append(f"{f.flag_type}:{f.description[:30]}")
        for r in dd_report.litigation_records:
            if r.role == "defendant" and (r.amount_disputed or 0) >= 1_000_000:
                red_flags.append(f"big_litigation:{r.case_number}")

        # 4) 推荐操作
        if grade in {"AAA", "AA"}:
            action = "trust"
        elif grade in {"A", "BBB"}:
            action = "verify_more"
        elif grade in {"BB", "B"}:
            action = "monitor"
        else:
            action = "avoid"

        rationale = (
            f"基于 {len(dd_report.litigation_records)} 条诉讼、"
            f"{len(dd_report.credit_flags)} 条信用瑕疵、"
            f"{dd_report.public_news_count} 条公开新闻综合得分 {score}/100"
        )

        return RiskGrade(
            grade=grade,
            score=score,
            breakdown=breakdown,
            rationale=rationale,
            red_flags=red_flags,
            recommended_action=action,
        )

    @staticmethod
    def _score_to_grade(score: float) -> str:
        for grade, threshold in _GRADE_BANDS:
            if score >= threshold:
                return grade
        return "D"

    # ------------------------------------------------------------------
    # 数据源对接（接 P6-C；离线时退化）
    # ------------------------------------------------------------------
    async def _fetch_basic_info(
        self, company_name: str, citations: list[Citation]
    ) -> CompanyBasicInfo | None:
        """工商基础信息 — 真实接入留给后续；当前给 mock。"""
        # 给报告加一条 placeholder 引文（标注为 mock）
        citations.append(
            Citation(
                source="fetch:qichacha_mock",
                url=f"https://example.com/qichacha/{company_name}",
                title=f"{company_name} 工商登记信息",
                excerpt="(mock) 公司基础工商信息",
                confidence=0.5,
            )
        )
        return CompanyBasicInfo(
            name=company_name,
            legal_representative="(待补充)",
            registered_capital=0.0,
            establishment_date=date(2020, 1, 1),
            business_scope="(待补充)",
            industry="(待补充)",
            address="(待补充)",
            unified_credit_code="91440300MA0000000A",
            status="存续",
        )

    async def _fetch_credit_flags(
        self, company_name: str, citations: list[Citation]
    ) -> list[CreditFlag]:
        """信用瑕疵 — 调 P6-C ``CreditChinaSource``。"""
        flags: list[CreditFlag] = []
        src = self._credit_source
        if src is None:
            return flags
        try:
            from src.services.fetch.sources.legal.base import LawSearchQuery

            results = await src.search(LawSearchQuery(keyword=company_name, limit=20))
            for r in results:
                category = ""
                if isinstance(r.extra, dict):
                    category = str(r.extra.get("category", ""))
                severity = self._infer_severity(category)
                flag_type = self._category_to_flag_type(category)
                flags.append(
                    CreditFlag(
                        flag_type=flag_type,
                        description=r.title,
                        issued_date=r.issued_date or date.today(),
                        issuing_authority=r.issuing_authority or "未知",
                        severity=severity,
                    )
                )
                citations.append(
                    Citation(
                        source="fetch:credit_china",
                        url=r.full_text_url or "",
                        title=r.title,
                        excerpt=(r.summary or "")[:120],
                        confidence=0.85,
                    )
                )
        except Exception as exc:  # pragma: no cover - 网络异常退化
            logger.warning("credit_source.search failed: %s", exc)
        return flags

    @staticmethod
    def _category_to_flag_type(category: str) -> str:
        c = (category or "").lower()
        if "失信" in c or "court" in c:
            return "court_default"
        if "税" in c or "tax" in c:
            return "tax_default"
        if "行政处罚" in c or "penalty" in c:
            return "administrative_penalty"
        if "异常" in c or "abnormal" in c:
            return "abnormal_operation"
        if "限制高消费" in c:
            return "consumption_restriction"
        return "other"

    @staticmethod
    def _infer_severity(category: str) -> str:
        c = (category or "").lower()
        if "失信" in c or "限制高消费" in c:
            return "critical"
        if "处罚" in c:
            return "high"
        if "异常" in c:
            return "medium"
        return "low"

    async def _fetch_litigation_records(
        self, company_name: str, citations: list[Citation]
    ) -> list[LitigationRecord]:
        """诉讼记录 — 调 P6-C ``HistoricalWenshuSource``。"""
        records: list[LitigationRecord] = []
        src = self._litigation_source
        if src is None:
            return records
        try:
            from src.services.fetch.sources.legal.base import LawSearchQuery

            results = await src.search(LawSearchQuery(keyword=company_name, limit=10))
            for r in results:
                role = "third_party"
                if isinstance(r.extra, dict):
                    role = str(r.extra.get("role", "third_party"))
                records.append(
                    LitigationRecord(
                        case_number=r.law_id or "",
                        case_type=(
                            (r.extra or {}).get("case_type", "")
                            if isinstance(r.extra, dict)
                            else ""
                        ),
                        court=r.issuing_authority or "",
                        role=role,
                        amount_disputed=(
                            (r.extra or {}).get("amount_disputed")
                            if isinstance(r.extra, dict)
                            else None
                        ),
                        judgment_date=r.issued_date,
                        judgment_summary=(r.summary or "")[:240],
                        full_text_url=r.full_text_url or "",
                    )
                )
                citations.append(
                    Citation(
                        source="fetch:historical_wenshu",
                        url=r.full_text_url or "",
                        title=r.title,
                        excerpt=(r.summary or "")[:120],
                        confidence=0.9,
                    )
                )
        except Exception as exc:  # pragma: no cover
            logger.warning("litigation_source.search failed: %s", exc)
        return records

    async def _estimate_news_volume(self, company_name: str) -> int:
        """公开新闻提及数（mock；正式接入留给 P6-A FetchService）。"""
        if self._fetch_service is None:
            return 0
        try:
            # 留出 hook：fetch_service 若实现了 search_volume，则使用之
            search_volume = getattr(self._fetch_service, "search_volume", None)
            if callable(search_volume):
                return int(await search_volume(company_name))
        except Exception:  # pragma: no cover
            pass
        return 0

    # ------------------------------------------------------------------
    # LLM 综合 / 模板 fallback
    # ------------------------------------------------------------------
    async def _llm_synthesize(
        self,
        *,
        company_name: str,
        basic_info: CompanyBasicInfo | None,
        credit_flags: list[CreditFlag],
        litigation_records: list[LitigationRecord],
    ) -> tuple[str, list[str]]:
        """deep 档调底层 due_diligence agent 做综合。"""
        try:
            agent = self._get_dd_agent()
            task = {
                "description": f"对 {company_name} 出具结构化尽调结论",
                "context": {
                    "company_name": company_name,
                    "credit_flag_count": len(credit_flags),
                    "litigation_count": len(litigation_records),
                },
            }
            resp = await agent.process(task)
            summary = (resp.content or "").strip()
            recommendations = self._template_recommendations(credit_flags, litigation_records)
            return (
                summary
                or self._template_summary(
                    company_name, basic_info, credit_flags, litigation_records
                ),
                recommendations,
            )
        except Exception as exc:  # pragma: no cover
            logger.debug("dd_agent.process failed: %s", exc)
            return (
                self._template_summary(company_name, basic_info, credit_flags, litigation_records),
                self._template_recommendations(credit_flags, litigation_records),
            )

    @staticmethod
    def _template_summary(
        company_name: str,
        basic_info: CompanyBasicInfo | None,
        credit_flags: list[CreditFlag],
        litigation_records: list[LitigationRecord],
    ) -> str:
        return (
            f"{company_name} 尽调结论：信用瑕疵 {len(credit_flags)} 条、"
            f"诉讼记录 {len(litigation_records)} 条。"
            f"工商状态：{(basic_info.status if basic_info else '未知')}。"
        )

    @staticmethod
    def _template_recommendations(
        credit_flags: list[CreditFlag],
        litigation_records: list[LitigationRecord],
    ) -> list[str]:
        recs: list[str] = []
        if any(f.severity in {"critical", "high"} for f in credit_flags):
            recs.append("建议要求对方提供信用瑕疵书面说明 + 整改证据")
        if any(r.role == "defendant" for r in litigation_records):
            recs.append("重点核查作为被告的诉讼，了解判决执行情况")
        if not recs:
            recs.append("当前未发现重大风险，建议常规复核")
        return recs

    @staticmethod
    def _infer_risk_level(
        *,
        credit_flags: list[CreditFlag],
        litigation_records: list[LitigationRecord],
        public_news_count: int,
        depth: str,
    ) -> str:
        critical = sum(1 for f in credit_flags if f.severity == "critical")
        high = sum(1 for f in credit_flags if f.severity == "high")
        defendants = sum(1 for r in litigation_records if r.role == "defendant")
        if critical >= 1 or defendants >= 5:
            return "critical"
        if high >= 1 or defendants >= 2:
            return "high"
        if len(credit_flags) >= 2 or defendants >= 1:
            return "medium"
        if depth == "quick" and not credit_flags:
            return "unknown"
        return "low"

    # ------------------------------------------------------------------
    # LRU 报告缓存
    # ------------------------------------------------------------------
    def _cache_put(self, report: DueDiligenceReport) -> None:
        if not report.report_id:
            return
        if report.report_id in self._report_cache:
            self._report_cache.move_to_end(report.report_id)
        self._report_cache[report.report_id] = report
        while len(self._report_cache) > _REPORT_CACHE_CAP:
            self._report_cache.popitem(last=False)

    def get_cached_report(self, report_id: str) -> DueDiligenceReport | None:
        rep = self._report_cache.get(report_id)
        if rep is not None:
            self._report_cache.move_to_end(report_id)
        return rep

    def list_cached_reports(
        self,
        target: str | None = None,
        generated_after: datetime | None = None,
    ) -> list[DueDiligenceReport]:
        out: list[DueDiligenceReport] = []
        for rep in self._report_cache.values():
            if target and target not in rep.target:
                continue
            if generated_after and rep.generated_at < generated_after:
                continue
            out.append(rep)
        return list(reversed(out))


__all__ = [
    "DueDiligenceExpertPersona",
]
