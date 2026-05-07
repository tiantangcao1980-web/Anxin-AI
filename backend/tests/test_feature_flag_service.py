from unittest.mock import Mock

from src.models.feature_flag import FeatureFlag
from src.services.feature_flag_service import FeatureFlagService


def test_evaluate_rejects_disabled_flag():
    service = FeatureFlagService(Mock())
    flag = FeatureFlag(key="demo", name="Demo", enabled=False)

    assert service._evaluate(flag, user_id="u1", role="admin", org_id="org-1") is False


def test_evaluate_applies_role_and_org_targets():
    service = FeatureFlagService(Mock())
    flag = FeatureFlag(
        key="demo",
        name="Demo",
        enabled=True,
        target_roles=["admin"],
        target_org_ids=["org-1"],
    )

    assert service._evaluate(flag, user_id="u1", role="admin", org_id="org-1") is True
    assert service._evaluate(flag, user_id="u1", role="member", org_id="org-1") is False
    assert service._evaluate(flag, user_id="u1", role="admin", org_id="org-2") is False


def test_evaluate_rollout_zero_blocks_user():
    service = FeatureFlagService(Mock())
    flag = FeatureFlag(
        key="rollout",
        name="Rollout",
        enabled=True,
        rollout_percentage=0,
    )

    assert service._evaluate(flag, user_id="u1", role="admin", org_id=None) is False
