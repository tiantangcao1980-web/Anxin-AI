from types import SimpleNamespace
from typing import Any

from src.middleware.risk_scoring import RiskScoringMiddleware


async def _noop_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    return None


def _request_with_state(**state_values: Any) -> Any:
    return SimpleNamespace(state=SimpleNamespace(**state_values))


def test_hmac_score_maps_security_reasons() -> None:
    middleware = RiskScoringMiddleware(_noop_app)

    assert middleware._score_hmac(_request_with_state()) == 15
    assert middleware._score_hmac(_request_with_state(hmac_result={"skipped": True})) == 0
    assert middleware._score_hmac(_request_with_state(hmac_result={"valid": True})) == 0
    assert (
        middleware._score_hmac(
            _request_with_state(hmac_result={"valid": False, "reason": "nonce_replay"})
        )
        == 30
    )
    assert (
        middleware._score_hmac(
            _request_with_state(hmac_result={"valid": False, "reason": "signature_mismatch"})
        )
        == 25
    )


def test_client_intel_score_is_clamped_and_tolerates_bad_values() -> None:
    middleware = RiskScoringMiddleware(_noop_app)

    assert middleware._score_intel(_request_with_state()) == 0
    assert middleware._score_intel(_request_with_state(intel_result={"risk_score": 40})) == 25
    assert middleware._score_intel(_request_with_state(intel_result={"risk_score": -4})) == 0
    assert middleware._score_intel(_request_with_state(intel_result={"risk_score": "bad"})) == 0
