from src.services.a2ui_builder import build_response_a2ui


def component_ids(panel: dict[str, object]) -> list[str]:
    a2ui = panel["a2ui"]
    assert isinstance(a2ui, dict)
    components = a2ui["components"]
    assert isinstance(components, list)
    return [str(component["id"]) for component in components]


def test_build_response_a2ui_extracts_panel_sections():
    content = """
## 合同解除风险分析

根据《民法典》第五百六十三条，解除合同应当满足约定或法定条件。

- 存在违约风险，需要固定催告和履约证据。

### 建议与下一步

1. 建议先发送书面催告并保留送达证据。
2. 应当核对合同解除条款和违约责任。

补充说明：本回复用于生成结构化面板，确保内容长度超过阈值。
"""

    panel = build_response_a2ui("合同审查 Agent", content)

    assert panel is not None
    ids = component_ids(panel)
    assert ids[0] == "agent_info"
    assert {"key_points", "legal_refs", "risk_alerts", "suggestions"}.issubset(ids)


def test_build_response_a2ui_skips_short_content():
    assert build_response_a2ui("Agent", "太短") is None
