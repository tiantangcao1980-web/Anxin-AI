import re
from pathlib import Path

import pytest

from src.services.a2ui_intent_handler import handle_a2ui_event


@pytest.mark.asyncio
async def test_generated_a2ui_actions_are_all_handled():
    source = (
        Path(__file__)
        .resolve()
        .parent.parent.joinpath("src/services/a2ui_intent_handler.py")
        .read_text(encoding="utf-8")
    )
    generated_actions = sorted(set(re.findall(r'actionId":\s*"([^"]+)"', source)))

    missing = []
    for action_id in generated_actions:
        result = await handle_a2ui_event(
            action_id=action_id,
            component_id="coverage-component",
            payload={},
            form_data={},
        )
        if result is None or not result.get("components"):
            missing.append(action_id)

    assert not missing, f"Uncovered A2UI actions found: {missing}"


@pytest.mark.asyncio
async def test_common_a2ui_actions_return_non_empty_response():
    sample_actions = [
        ("view_more_lawyers", {}),
        ("go_back", {}),
        ("paste_contract", {}),
        ("view_full_report", {}),
        ("assess_compliance", {}),
        ("view_engagement_detail", {}),
    ]

    for action_id, payload in sample_actions:
        result = await handle_a2ui_event(
            action_id=action_id,
            component_id="smoke-component",
            payload=payload,
            form_data={},
        )
        assert result is not None, f"{action_id} returned no response"
        assert result["type"] == "a2ui_message"
        assert result["components"], f"{action_id} returned empty components"
