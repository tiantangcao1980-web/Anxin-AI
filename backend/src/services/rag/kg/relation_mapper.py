"""
关系映射器

输入：
- entities：:class:`EntityExtractor` 产出
- segments：P13-A 多模态切片

输出：
- list[Relation]，含 ``cross_modal=True`` 的跨模态边

策略：
1. **同模态**：在同一 segment 内，按"主语 → 谓语 → 宾语"启发式建链
   - LEGAL_PARTY 与 OBLIGATION/RIGHT 同段共现 → OBLIGES
   - 文本提及 REGULATION → REFERENCES
2. **跨模态**：
   - 文本段提及 SEAL/SIGNATURE → ATTACHED_TO（cross_modal=True）
   - 文本段提及金额且邻近段为 TABLE → CONTAINS（cross_modal=True）
   - 文本段提及"如下图/见图" → DEPICTS 邻近 IMAGE（cross_modal=True）
   - 文本段提及公式且邻近段为 FORMULA → DEPICTS（cross_modal=True）
3. **别名等价**：实体名 ⊆ 另一实体的 aliases → SAME_AS

不依赖 LLM，纯启发式（任务卡的 mock 友好要求）；后续可由调用方注入更强的关系抽取
器（例如 LLM-based 二次精炼）替换 ``map`` 行为。
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from src.services.rag.kg.base import (
    Entity,
    EntityType,
    Modality,
    Relation,
    RelationType,
    Segment,
    SegmentLikeProtocol,
)

SEAL_MENTION_KEYWORDS = ("公章", "印章", "盖章", "签章")
SIGNATURE_MENTION_KEYWORDS = ("签字", "签名", "落款")
IMAGE_MENTION_KEYWORDS = ("如图", "见图", "下图", "上图", "附图", "示意图")
FORMULA_MENTION_KEYWORDS = ("公式", "如下式", "见下式", "计算式")


class RelationMapper:
    """同模态 + 跨模态关系映射。"""

    def map(
        self,
        entities: list[Entity],
        segments: Iterable[SegmentLikeProtocol],
    ) -> list[Relation]:
        seg_list = [Segment.from_protocol(s) for s in segments]
        seg_by_id = {s.segment_id: s for s in seg_list}

        # 把 entities 按 segment 分桶（一个实体可能出现在多个段）
        ent_by_segment: dict[str, list[Entity]] = {}
        for ent in entities:
            seen_segs = set()
            for m in ent.mentions:
                sid = m.get("segment_id")
                if not sid or sid in seen_segs:
                    continue
                seen_segs.add(sid)
                ent_by_segment.setdefault(sid, []).append(ent)

        relations: list[Relation] = []

        # ------------- 1. 同模态关系 -------------
        for seg in seg_list:
            seg_entities = ent_by_segment.get(seg.segment_id, [])
            if not seg_entities:
                continue

            parties = [e for e in seg_entities if e.type == EntityType.LEGAL_PARTY]
            obligations = [e for e in seg_entities if e.type == EntityType.OBLIGATION]
            rights = [e for e in seg_entities if e.type == EntityType.RIGHT]
            regulations = [e for e in seg_entities if e.type == EntityType.REGULATION]
            amounts = [e for e in seg_entities if e.type == EntityType.AMOUNT]

            # party → obligation
            for p in parties:
                for o in obligations:
                    relations.append(
                        self._make_rel(
                            RelationType.OBLIGES,
                            p.entity_id,
                            o.entity_id,
                            properties={"segment_id": seg.segment_id},
                            confidence=0.75,
                        )
                    )
                # party → right (借用 OBLIGES，但加 sub_type 区分)
                for r in rights:
                    relations.append(
                        self._make_rel(
                            RelationType.OBLIGES,
                            p.entity_id,
                            r.entity_id,
                            properties={
                                "segment_id": seg.segment_id,
                                "sub_type": "right",
                            },
                            confidence=0.75,
                        )
                    )

            # 任何条款 → REFERENCES → regulation
            for reg in regulations:
                # 把段内所有非 regulation 实体都视作引用方（保守：只挂到义务/权利上）
                for src in obligations + rights:
                    relations.append(
                        self._make_rel(
                            RelationType.REFERENCES,
                            src.entity_id,
                            reg.entity_id,
                            properties={"segment_id": seg.segment_id},
                            confidence=0.85,
                        )
                    )

            # 义务 / 权利 → CONTAINS → 金额（同段共现）
            for src in obligations + rights:
                for amt in amounts:
                    relations.append(
                        self._make_rel(
                            RelationType.CONTAINS,
                            src.entity_id,
                            amt.entity_id,
                            properties={"segment_id": seg.segment_id},
                            confidence=0.7,
                        )
                    )

        # ------------- 2. 跨模态关系 -------------
        relations.extend(self._cross_modal(entities, seg_list, seg_by_id, ent_by_segment))

        # ------------- 3. SAME_AS（别名等价）-------------
        relations.extend(self._same_as(entities))

        return relations

    # ------------------------------------------------------------------
    # 跨模态
    # ------------------------------------------------------------------

    def _cross_modal(
        self,
        entities: list[Entity],
        seg_list: list[Segment],
        seg_by_id: dict[str, Segment],
        ent_by_segment: dict[str, list[Entity]],
    ) -> list[Relation]:
        relations: list[Relation] = []

        # 拿所有非文本实体
        non_text_entities_by_modality: dict[str, list[Entity]] = {}
        for ent in entities:
            for m in ent.mentions:
                modality = m.get("modality")
                if modality and modality != Modality.TEXT.value:
                    non_text_entities_by_modality.setdefault(modality, []).append(ent)
                    break  # 取一个就够了

        # 对每个文本段：找其中提及"图章/签字/图/公式"等关键词，连接到相邻或元数据指向的非文本段
        for idx, seg in enumerate(seg_list):
            if seg.modality and seg.modality != Modality.TEXT.value:
                continue
            text = seg.content or ""
            if not text:
                continue
            seg_entities = ent_by_segment.get(seg.segment_id, [])

            # 取文本段中"主语候选"——优先 OBLIGATION/RIGHT 条款，其次 LEGAL_PARTY
            subject_candidates = [
                e
                for e in seg_entities
                if e.type in (EntityType.OBLIGATION, EntityType.RIGHT, EntityType.LEGAL_PARTY)
            ]
            if not subject_candidates:
                # 没有合适主语时退化为"段本身"——构造一个虚拟 doc anchor 不在此处做，
                # 直接把 IMG/SEAL 等独立 attached_to document（在 belongs_to_chain 层处理）
                pass

            mentions_seal = any(kw in text for kw in SEAL_MENTION_KEYWORDS)
            mentions_signature = any(kw in text for kw in SIGNATURE_MENTION_KEYWORDS)
            mentions_image = any(kw in text for kw in IMAGE_MENTION_KEYWORDS)
            mentions_formula = any(kw in text for kw in FORMULA_MENTION_KEYWORDS)
            has_amount = any(e.type == EntityType.AMOUNT for e in seg_entities)

            neighbors = self._neighbor_segments(idx, seg_list, window=2)

            # SEAL
            if mentions_seal:
                seal_targets = self._pick_neighbor_or_global(
                    neighbors, non_text_entities_by_modality, modality=Modality.SEAL.value
                )
                for tgt in seal_targets:
                    src_id = subject_candidates[0].entity_id if subject_candidates else tgt.entity_id
                    if src_id == tgt.entity_id:
                        continue
                    relations.append(
                        self._make_rel(
                            RelationType.ATTACHED_TO,
                            tgt.entity_id,
                            src_id,
                            properties={"segment_id": seg.segment_id, "via": "text_mention"},
                            confidence=0.8,
                            cross_modal=True,
                        )
                    )

            # SIGNATURE
            if mentions_signature:
                sig_targets = self._pick_neighbor_or_global(
                    neighbors, non_text_entities_by_modality, modality=Modality.SIGNATURE.value
                )
                for tgt in sig_targets:
                    src_id = subject_candidates[0].entity_id if subject_candidates else tgt.entity_id
                    if src_id == tgt.entity_id:
                        continue
                    relations.append(
                        self._make_rel(
                            RelationType.ATTACHED_TO,
                            tgt.entity_id,
                            src_id,
                            properties={"segment_id": seg.segment_id, "via": "text_mention"},
                            confidence=0.8,
                            cross_modal=True,
                        )
                    )

            # IMAGE → DEPICTS
            if mentions_image:
                img_targets = self._pick_neighbor_or_global(
                    neighbors, non_text_entities_by_modality, modality=Modality.IMAGE.value
                )
                for tgt in img_targets:
                    src_id = subject_candidates[0].entity_id if subject_candidates else tgt.entity_id
                    if src_id == tgt.entity_id:
                        continue
                    relations.append(
                        self._make_rel(
                            RelationType.DEPICTS,
                            tgt.entity_id,
                            src_id,
                            properties={"segment_id": seg.segment_id},
                            confidence=0.7,
                            cross_modal=True,
                        )
                    )

            # FORMULA → DEPICTS
            if mentions_formula:
                f_targets = self._pick_neighbor_or_global(
                    neighbors, non_text_entities_by_modality, modality=Modality.FORMULA.value
                )
                for tgt in f_targets:
                    src_id = subject_candidates[0].entity_id if subject_candidates else tgt.entity_id
                    if src_id == tgt.entity_id:
                        continue
                    relations.append(
                        self._make_rel(
                            RelationType.DEPICTS,
                            tgt.entity_id,
                            src_id,
                            properties={"segment_id": seg.segment_id},
                            confidence=0.7,
                            cross_modal=True,
                        )
                    )

            # TABLE → CONTAINS（金额 / 数据点）
            if has_amount:
                table_neighbors = [n for n in neighbors if n.modality == Modality.TABLE.value]
                if table_neighbors:
                    amount_entities = [
                        e for e in seg_entities if e.type == EntityType.AMOUNT
                    ]
                    for tn in table_neighbors:
                        # 在 tn 上挂的 TABLE_DATA 实体
                        tbl_entities = ent_by_segment.get(tn.segment_id, [])
                        for tbl_ent in tbl_entities:
                            if tbl_ent.type != EntityType.TABLE_DATA:
                                continue
                            for amt in amount_entities:
                                relations.append(
                                    self._make_rel(
                                        RelationType.CONTAINS,
                                        tbl_ent.entity_id,
                                        amt.entity_id,
                                        properties={
                                            "src_segment": seg.segment_id,
                                            "table_segment": tn.segment_id,
                                        },
                                        confidence=0.65,
                                        cross_modal=True,
                                    )
                                )

        return relations

    @staticmethod
    def _neighbor_segments(idx: int, seg_list: list[Segment], window: int = 2) -> list[Segment]:
        lo = max(0, idx - window)
        hi = min(len(seg_list), idx + window + 1)
        return [seg_list[i] for i in range(lo, hi) if i != idx]

    @staticmethod
    def _pick_neighbor_or_global(
        neighbors: list[Segment],
        non_text_entities_by_modality: dict[str, list[Entity]],
        modality: str,
    ) -> list[Entity]:
        """优先选择邻接段命中的实体；没有则退化为全局该 modality 实体。"""
        neighbor_seg_ids = {s.segment_id for s in neighbors if s.modality == modality}
        global_pool = non_text_entities_by_modality.get(modality, [])
        if not global_pool:
            return []
        if not neighbor_seg_ids:
            return global_pool[:1]  # 取第一个，避免边爆炸

        narrowed: list[Entity] = []
        for ent in global_pool:
            for m in ent.mentions:
                if m.get("segment_id") in neighbor_seg_ids:
                    narrowed.append(ent)
                    break
        return narrowed or global_pool[:1]

    # ------------------------------------------------------------------
    # 别名等价
    # ------------------------------------------------------------------

    def _same_as(self, entities: list[Entity]) -> list[Relation]:
        relations: list[Relation] = []
        # 名字 → entity_id 索引
        name_index: dict[str, str] = {}
        for ent in entities:
            name_index[ent.name] = ent.entity_id

        # 若 A.alias == B.name → SAME_AS
        seen_pairs: set[tuple[str, str]] = set()
        for ent in entities:
            for alias in ent.aliases:
                tgt_id = name_index.get(alias)
                if tgt_id and tgt_id != ent.entity_id:
                    key = tuple(sorted([ent.entity_id, tgt_id]))
                    if key in seen_pairs:
                        continue
                    seen_pairs.add(key)
                    relations.append(
                        self._make_rel(
                            RelationType.SAME_AS,
                            ent.entity_id,
                            tgt_id,
                            properties={"alias": alias},
                            confidence=0.9,
                        )
                    )
        return relations

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    @staticmethod
    def _make_rel(
        rtype: RelationType,
        source: str,
        target: str,
        *,
        properties: dict | None = None,
        confidence: float = 0.8,
        cross_modal: bool = False,
    ) -> Relation:
        rid_seed = f"{rtype.value}::{source}::{target}::{properties or {}}"
        rid = "rel_" + hashlib.md5(rid_seed.encode("utf-8")).hexdigest()[:16]
        return Relation(
            relation_id=rid,
            type=rtype,
            source_entity=source,
            target_entity=target,
            properties=dict(properties or {}),
            confidence=confidence,
            cross_modal=cross_modal,
        )


__all__ = ["RelationMapper"]
