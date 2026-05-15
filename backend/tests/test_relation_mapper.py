"""P13-B RelationMapper 单元测试。"""

from __future__ import annotations

from src.services.rag.kg.base import (
    Entity,
    EntityType,
    Modality,
    RelationType,
    Segment,
)
from src.services.rag.kg.entity_extractor import EntityExtractor
from src.services.rag.kg.relation_mapper import RelationMapper


def _make_text_seg(seg_id: str, content: str) -> Segment:
    return Segment(segment_id=seg_id, modality=Modality.TEXT.value, content=content)


# ---------------------------------------------------------------------------
# 同模态：合同条款 → 当事人 + 义务 + 法规
# ---------------------------------------------------------------------------


async def test_same_modal_party_obliges_obligation_and_references_regulation():
    seg = _make_text_seg(
        "s1",
        "甲方应当在交付后 7 日内向乙方支付货款，依据《中华人民共和国民法典》第五百零九条。",
    )
    extractor = EntityExtractor(mode="mock")
    entities = await extractor.extract([seg])
    rels = RelationMapper().map(entities, [seg])

    # 至少存在一条 OBLIGES 边（party → obligation）
    obliges = [r for r in rels if r.type == RelationType.OBLIGES]
    assert obliges, "应当生成 party→obligation 的 OBLIGES 边"

    # 至少存在一条 REFERENCES 边（obligation → regulation）
    refs = [r for r in rels if r.type == RelationType.REFERENCES]
    assert refs, "应当生成 obligation→regulation 的 REFERENCES 边"

    # 同模态边不应被标记为 cross_modal
    assert all(not r.cross_modal for r in obliges + refs)


# ---------------------------------------------------------------------------
# 跨模态：text → seal / signature / image / formula
# ---------------------------------------------------------------------------


async def test_cross_modal_text_to_seal():
    text_seg = _make_text_seg(
        "txt_1",
        "甲方应在合同末页加盖公章，乙方签字确认。",
    )
    seal_seg = Segment(
        segment_id="seal_1",
        modality=Modality.SEAL.value,
        content="",
        metadata={"name": "甲方公章"},
    )
    sig_seg = Segment(
        segment_id="sig_1",
        modality=Modality.SIGNATURE.value,
        content="",
        metadata={"name": "乙方签字"},
    )
    extractor = EntityExtractor(mode="mock")
    entities = await extractor.extract([text_seg, seal_seg, sig_seg])
    rels = RelationMapper().map(entities, [text_seg, seal_seg, sig_seg])

    cross = [r for r in rels if r.cross_modal]
    assert cross, "至少有一条跨模态关系"

    attached = [r for r in cross if r.type == RelationType.ATTACHED_TO]
    assert attached, "应当生成 ATTACHED_TO 跨模态边"


async def test_cross_modal_text_to_image_depicts():
    text_seg = _make_text_seg("txt_1", "甲方应当如下图所示安装设备。")
    img_seg = Segment(
        segment_id="img_1",
        modality=Modality.IMAGE.value,
        content="",
        metadata={"caption": "设备安装示意图"},
    )
    extractor = EntityExtractor(mode="mock")
    entities = await extractor.extract([text_seg, img_seg])
    rels = RelationMapper().map(entities, [text_seg, img_seg])

    depicts = [r for r in rels if r.type == RelationType.DEPICTS and r.cross_modal]
    assert depicts


async def test_cross_modal_text_to_formula_depicts():
    text_seg = _make_text_seg(
        "txt_1",
        "甲方应当按下式计算违约金，详见公式。",
    )
    formula_seg = Segment(
        segment_id="f_1",
        modality=Modality.FORMULA.value,
        content="P = R * D * 0.001",
        metadata={"expr": "P = R * D * 0.001"},
    )
    extractor = EntityExtractor(mode="mock")
    entities = await extractor.extract([text_seg, formula_seg])
    rels = RelationMapper().map(entities, [text_seg, formula_seg])

    depicts = [r for r in rels if r.type == RelationType.DEPICTS and r.cross_modal]
    assert depicts


async def test_cross_modal_table_contains_amount():
    text_seg = _make_text_seg(
        "txt_1",
        "支付金额为人民币 100,000 元，明细如下表所示。",
    )
    table_seg = Segment(
        segment_id="tbl_1",
        modality=Modality.TABLE.value,
        content="",
        metadata={"name": "支付明细表", "rows": 5},
    )
    extractor = EntityExtractor(mode="mock")
    entities = await extractor.extract([text_seg, table_seg])
    rels = RelationMapper().map(entities, [text_seg, table_seg])

    contains = [r for r in rels if r.type == RelationType.CONTAINS and r.cross_modal]
    assert contains, "table → amount 应当生成跨模态 CONTAINS 边"


# ---------------------------------------------------------------------------
# SAME_AS（别名等价）
# ---------------------------------------------------------------------------


def test_same_as_relation_from_aliases():
    e1 = Entity(
        entity_id="ent_a",
        type=EntityType.LEGAL_PARTY,
        name="北京安心科技有限公司",
        aliases=["甲方"],
    )
    e2 = Entity(entity_id="ent_b", type=EntityType.LEGAL_PARTY, name="甲方")
    rels = RelationMapper().map([e1, e2], [])
    same_as = [r for r in rels if r.type == RelationType.SAME_AS]
    assert len(same_as) == 1
    pair = sorted([same_as[0].source_entity, same_as[0].target_entity])
    assert pair == sorted(["ent_a", "ent_b"])


# ---------------------------------------------------------------------------
# 边界
# ---------------------------------------------------------------------------


def test_empty_inputs_return_no_relations():
    assert RelationMapper().map([], []) == []
