"""模态加权排序器。

默认权重：

- text     = 1.00
- table    = 0.90
- formula  = 0.85
- image    = 0.70
- seal     = 0.60

按 query 类型动态调整：

- "公章" / "印鉴" / "盖章"  → seal=1.00
- "金额" / "数额" / "总价" / "增值税"  → table=1.00, formula=0.95
- "条款" / "约定" / "义务"   → text=1.00, image=0.50

调用方传入 ``query_overrides`` 可进一步覆盖（query 级别 > 关键词触发 > 默认值）。
"""

from __future__ import annotations

from dataclasses import dataclass

from src.services.rag.query.base import Modality, RetrievedSegment

DEFAULT_MODALITY_WEIGHTS: dict[Modality, float] = {
    Modality.TEXT: 1.00,
    Modality.TABLE: 0.90,
    Modality.FORMULA: 0.85,
    Modality.IMAGE: 0.70,
    Modality.SEAL: 0.60,
}


# 关键词 → 模态权重覆盖
KEYWORD_WEIGHT_OVERRIDES: list[tuple[tuple[str, ...], dict[Modality, float]]] = [
    (
        ("公章", "印鉴", "盖章", "签章", "钢印"),
        {Modality.SEAL: 1.00, Modality.IMAGE: 0.85},
    ),
    (
        ("金额", "数额", "总价", "增值税", "VAT", "费用", "结算"),
        {Modality.TABLE: 1.00, Modality.FORMULA: 0.95},
    ),
    (
        ("条款", "约定", "义务", "权利", "违约", "解除"),
        {Modality.TEXT: 1.00, Modality.IMAGE: 0.50},
    ),
    (
        ("证据", "照片", "现场", "图示"),
        {Modality.IMAGE: 1.00, Modality.SEAL: 0.85},
    ),
    (
        ("公式", "计算", "推导"),
        {Modality.FORMULA: 1.00, Modality.TABLE: 0.90},
    ),
]


@dataclass
class ModalityWeightedRanker:
    """对 :class:`RetrievedSegment` 列表按模态加权重排。

    重排公式::

        final_score = base_score * modality_weight + kg_boost

    其中 ``base_score`` 来自 vector + BM25 混合得分（P13-A 的 hybrid_score），
    ``kg_boost`` 来自 :class:`KGBooster`。
    """

    base_weights: dict[Modality, float] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.base_weights is None:
            self.base_weights = dict(DEFAULT_MODALITY_WEIGHTS)

    # ---- 权重解析 ----

    def resolve_weights(
        self,
        query: str,
        query_overrides: dict[str, float] | None = None,
    ) -> dict[Modality, float]:
        """根据 query 文本 + 显式覆盖产出最终权重表。

        优先级：``query_overrides`` > 关键词触发 > 默认值。
        """
        weights = dict(self.base_weights)

        # 关键词触发
        if query:
            q_lower = query.lower()
            for keywords, override in KEYWORD_WEIGHT_OVERRIDES:
                if any(kw.lower() in q_lower for kw in keywords):
                    for modality, w in override.items():
                        weights[modality] = w

        # 显式覆盖（最强）
        if query_overrides:
            for raw_key, w in query_overrides.items():
                modality = Modality.coerce(raw_key)
                weights[modality] = float(w)

        return weights

    # ---- 重排 ----

    def rerank(
        self,
        segments: list[RetrievedSegment],
        *,
        query: str = "",
        query_overrides: dict[str, float] | None = None,
        kg_boosts: dict[str, float] | None = None,
        top_k: int | None = None,
    ) -> list[RetrievedSegment]:
        """按模态加权 + KG boost 重排，并截断 ``top_k``。

        每个 segment 的 ``breakdown`` 会被填充：
        ``{base_score, modality_weight, kg_boost, final_score}``。
        """
        if not segments:
            return []

        weights = self.resolve_weights(query, query_overrides)
        kg_boosts = kg_boosts or {}

        for seg in segments:
            base = seg.breakdown.get("base_score", seg.score)
            mw = weights.get(Modality.coerce(seg.modality), 1.0)
            boost = float(kg_boosts.get(seg.segment_id, 0.0))
            final = base * mw + boost

            seg.breakdown.update(
                {
                    "base_score": base,
                    "modality_weight": mw,
                    "kg_boost": boost,
                    "final_score": final,
                }
            )
            seg.score = final

        ranked = sorted(segments, key=lambda s: s.score, reverse=True)
        if top_k is not None:
            ranked = ranked[: max(0, top_k)]
        return ranked
