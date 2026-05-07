import pytest

from src.services import scenario_simulation as module
from src.services.scenario_simulation import ScenarioSimulationService


@pytest.mark.asyncio
async def test_scenario_simulation_applies_risk_delta():
    service = ScenarioSimulationService()

    result = await service.simulate_scenario(
        "customer_default",
        "安心科技",
        current_risk={"operation_risk": 40, "credit_risk": 80},
    )

    assert result["scenario"] == "主要客户违约"
    assert result["risk_after"]["operation_risk"] == 65
    assert result["risk_after"]["credit_risk"] == 100
    assert "安心科技" in result["overall_assessment"]


@pytest.mark.asyncio
async def test_scenario_stream_emits_ordered_events(monkeypatch):
    async def no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(module.asyncio, "sleep", no_sleep)
    service = ScenarioSimulationService()

    events = [
        event
        async for event in service.simulate_stream(
            "key_person_leave",
            "安心科技",
        )
    ]

    assert events[0] == {"type": "start", "scenario": "核心人员离职"}
    assert events[1]["type"] == "impact_step"
    assert events[1]["event"] == "核心技术或管理能力暂时缺失"
    assert events[-2]["type"] == "recommendations"
    assert events[-1] == {"type": "done", "scenario": "核心人员离职"}
