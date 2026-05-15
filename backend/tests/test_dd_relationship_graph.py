"""DueDiligenceExpertPersona 关系图谱算法测试 (P9-D)。

覆盖：
    - 深度限制 (≤ _MAX_GRAPH_DEPTH)
    - 全图节点上限
    - 单层节点上限
    - 风险路径检测：从 root 走到 high-risk 节点
    - 不变量：所有边的 from/to 都在 nodes 中
"""

from __future__ import annotations

import pytest

from src.agents.personas.dd_models import (
    RelationshipEdge,
    RelationshipNode,
)
from src.agents.personas.due_diligence_expert import (
    _MAX_GRAPH_DEPTH,
    _MAX_NODES_PER_LEVEL,
    _MAX_NODES_TOTAL,
    DueDiligenceExpertPersona,
)


@pytest.mark.asyncio
async def test_graph_depth_clamped_to_max():
    persona = DueDiligenceExpertPersona()
    g = await persona.build_relationship_graph("X", depth=99)
    assert g.depth == _MAX_GRAPH_DEPTH


@pytest.mark.asyncio
async def test_graph_depth_minimum_is_one():
    persona = DueDiligenceExpertPersona()
    g = await persona.build_relationship_graph("X", depth=0)
    assert g.depth == 1
    # 深度=1 时应该只扩一层
    assert len(g.nodes) >= 1


@pytest.mark.asyncio
async def test_graph_total_nodes_under_cap():
    persona = DueDiligenceExpertPersona()
    g = await persona.build_relationship_graph("ACME", depth=3)
    assert len(g.nodes) <= _MAX_NODES_TOTAL


@pytest.mark.asyncio
async def test_graph_root_present_and_unique():
    persona = DueDiligenceExpertPersona()
    g = await persona.build_relationship_graph("RootCo", depth=2)
    root_ids = [n.id for n in g.nodes if n.name == "RootCo"]
    assert len(root_ids) == 1
    # 所有 id 唯一
    ids = [n.id for n in g.nodes]
    assert len(ids) == len(set(ids))


@pytest.mark.asyncio
async def test_graph_edges_reference_existing_nodes():
    persona = DueDiligenceExpertPersona()
    g = await persona.build_relationship_graph("EdgeCo", depth=2)
    node_ids = {n.id for n in g.nodes}
    for e in g.edges:
        assert e.from_id in node_ids
        assert e.to_id in node_ids


@pytest.mark.asyncio
async def test_graph_finds_risk_paths_from_root():
    """构造一个包含 high-risk 节点的图，确认 risk_paths 命中。"""
    persona = DueDiligenceExpertPersona()
    g = await persona.build_relationship_graph("RiskyCo", depth=3)
    # mock _fetch_neighbors 会按 hash 派发部分 high-risk 节点；不强求 risk_paths
    # 一定非空（不同输入 hash 不同），但若有 high-risk 节点，则必须找出至少一条
    high_risk_ids = {n.id for n in g.nodes if n.attributes.get("risk_level") == "high"}
    if high_risk_ids:
        assert g.risk_paths, "存在 high-risk 节点时应至少找到一条 risk_path"
        for path in g.risk_paths:
            assert path[-1] in high_risk_ids
            assert path[0] == g.nodes[0].id  # 第一个 node 是 root


@pytest.mark.asyncio
async def test_find_risk_paths_static_topology():
    """直接调用静态算法，验证路径发现的正确性（不依赖随机 mock）。"""
    nodes_by_id = {
        "company:root": RelationshipNode(
            id="company:root", name="root", type="company", attributes={}
        ),
        "person:alice": RelationshipNode(
            id="person:alice",
            name="alice",
            type="person",
            attributes={"risk_level": "low"},
        ),
        "company:bad": RelationshipNode(
            id="company:bad",
            name="bad",
            type="company",
            attributes={"risk_level": "high"},
        ),
        "company:good": RelationshipNode(
            id="company:good",
            name="good",
            type="company",
            attributes={"risk_level": "low"},
        ),
    }
    edges = [
        RelationshipEdge(from_id="company:root", to_id="person:alice", relationship="owns"),
        RelationshipEdge(from_id="person:alice", to_id="company:bad", relationship="owns"),
        RelationshipEdge(from_id="company:root", to_id="company:good", relationship="invests_in"),
    ]
    paths = DueDiligenceExpertPersona._find_risk_paths("company:root", edges, nodes_by_id)
    assert len(paths) == 1
    assert paths[0] == ["company:root", "person:alice", "company:bad"]


@pytest.mark.asyncio
async def test_graph_layer_growth_bounded():
    """构造 root 的"邻居数"被 _MAX_NODES_PER_LEVEL 钳制（间接通过总节点上限验证）。

    本 mock 单节点最多 5 邻居，远小于 25，因此该测试主要确保 BFS 不出现指数爆炸：
    深度 3，每层 5 邻居 → 上限 1+5+25+125 = 156 < _MAX_NODES_TOTAL 200。
    """
    persona = DueDiligenceExpertPersona()
    g = await persona.build_relationship_graph("BoundedCo", depth=3)
    # 上界（理论 + 1 防越界缓冲）
    assert len(g.nodes) <= 1 + _MAX_NODES_PER_LEVEL * 6  # 留充足余量


@pytest.mark.asyncio
async def test_graph_empty_entity_rejected():
    persona = DueDiligenceExpertPersona()
    with pytest.raises(ValueError):
        await persona.build_relationship_graph("", depth=2)
