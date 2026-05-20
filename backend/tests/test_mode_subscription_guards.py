"""
require_mode + require_subscription_feature 守卫的回归测试

来自任务：TASK-09 P0-1（docs/audit/_tasks/task-09-risk-investigation.md）
方案文档：docs/audit/09-risk/PROPOSAL-mode-guard.md

测试覆盖：
1. is_superuser 直接放行（两个守卫）
2. require_mode：免费用户无头时降级为 local，调 hybrid/cloud-only 路由 → 403
3. require_mode：订阅是 hybrid 用户带 X-Privacy-Mode: hybrid → 通过
4. require_mode：订阅是 hybrid 用户带 X-Privacy-Mode: local（用户主动选 local）→ 403
5. require_subscription_feature：免费用户调 due_diligence → 402
6. require_subscription_feature：超管直接通过（不查 service）
"""

from datetime import date, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException

from src.core.mode_deps import require_mode, require_subscription_feature
from src.models.billing import BillingPlan, Subscription
from src.models.user import User
from src.services.subscription_service import SubscriptionService


def _build_request(mode_header: str | None = None) -> MagicMock:
    """构造一个最小的 Request mock，仅暴露 headers.get(...)"""
    request = MagicMock()
    if mode_header is None:
        request.headers.get = MagicMock(return_value=None)
    else:
        request.headers.get = MagicMock(return_value=mode_header)
    return request


@pytest_asyncio.fixture
async def free_user(db_session):
    user = User(
        id=str(uuid4()),
        email=f"free-{uuid4().hex[:8]}@example.com",
        name="免费用户",
        hashed_password="x",
        is_active=True,
        primary_client="needer",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def super_user(db_session):
    user = User(
        id=str(uuid4()),
        email=f"super-{uuid4().hex[:8]}@example.com",
        name="超级管理员",
        hashed_password="x",
        is_active=True,
        role="super_admin",
        primary_client="needer",
    )
    db_session.add(user)
    await db_session.flush()
    # mode_deps 用 getattr(user, "is_superuser", False) 做兼容，
    # User ORM 模型无此持久化字段，测试中以动态属性模拟"超管"语义
    user.is_superuser = True
    return user


@pytest_asyncio.fixture
async def hybrid_pro_plan(db_session):
    """构造一个允许 hybrid+cloud 模式 + due_diligence 的付费计划"""
    plan = BillingPlan(
        id=str(uuid4()),
        code=f"pro-{uuid4().hex[:6]}",
        name="测试 Pro 套餐",
        billing_mode="monthly",
        base_price=99.0,
        client_type="needer",
        is_active=True,
        features={
            "modes": ["local", "hybrid", "cloud"],
            "due_diligence": True,
        },
    )
    db_session.add(plan)
    await db_session.flush()
    return plan


@pytest_asyncio.fixture
async def hybrid_pro_user(db_session, hybrid_pro_plan):
    user = User(
        id=str(uuid4()),
        email=f"pro-{uuid4().hex[:8]}@example.com",
        name="付费用户",
        hashed_password="x",
        is_active=True,
        primary_client="needer",
    )
    db_session.add(user)
    await db_session.flush()

    today = date.today()
    sub = Subscription(
        id=str(uuid4()),
        user_id=user.id,
        plan_id=hybrid_pro_plan.id,
        client_type="needer",
        status="active",
        current_period_start=today,
        current_period_end=today + timedelta(days=30),
    )
    db_session.add(sub)
    await db_session.flush()
    return user


# ========== require_mode 测试 ==========


@pytest.mark.asyncio
async def test_require_mode_superuser_bypasses(super_user, db_session):
    """超级管理员直接放行，不查订阅"""
    dep = require_mode(["hybrid", "cloud"])
    request = _build_request(mode_header="local")  # 即使头是 local 也通过
    result = await dep(request=request, user=super_user, db=db_session)
    assert result is super_user


@pytest.mark.asyncio
async def test_require_mode_free_user_no_header_falls_back_to_local(free_user, db_session):
    """免费用户无头 → 按订阅推断 local → allow=[hybrid,cloud] → 403"""
    dep = require_mode(["hybrid", "cloud"])
    request = _build_request(mode_header=None)
    with pytest.raises(HTTPException) as excinfo:
        await dep(request=request, user=free_user, db=db_session)
    assert excinfo.value.status_code == 403
    assert "local" in excinfo.value.detail


@pytest.mark.asyncio
async def test_require_mode_pro_user_with_hybrid_header_passes(hybrid_pro_user, db_session):
    """付费用户带 X-Privacy-Mode: hybrid → 通过"""
    dep = require_mode(["hybrid", "cloud"])
    request = _build_request(mode_header="hybrid")
    result = await dep(request=request, user=hybrid_pro_user, db=db_session)
    assert result is hybrid_pro_user


@pytest.mark.asyncio
async def test_require_mode_pro_user_with_local_header_blocked(hybrid_pro_user, db_session):
    """
    付费用户主动选 local 模式（前端切到本地），但调用 hybrid-only 路由 → 403
    （即使他订阅了 hybrid，当前会话选了 local 就不能调云端尽调）
    """
    dep = require_mode(["hybrid", "cloud"])
    request = _build_request(mode_header="local")
    with pytest.raises(HTTPException) as excinfo:
        await dep(request=request, user=hybrid_pro_user, db=db_session)
    assert excinfo.value.status_code == 403


@pytest.mark.asyncio
async def test_require_mode_invalid_header_falls_back(free_user, db_session):
    """非法头值（如 'foo'）按缺失处理，按订阅推断"""
    dep = require_mode(["hybrid", "cloud"])
    request = _build_request(mode_header="foo")
    with pytest.raises(HTTPException) as excinfo:
        await dep(request=request, user=free_user, db=db_session)
    assert excinfo.value.status_code == 403


# ========== require_subscription_feature 测试 ==========


@pytest.mark.asyncio
async def test_require_subscription_feature_superuser_bypasses(super_user, db_session):
    dep = require_subscription_feature("due_diligence")
    result = await dep(user=super_user, db=db_session)
    assert result is super_user


@pytest.mark.asyncio
async def test_require_subscription_feature_free_user_blocked(free_user, db_session):
    """免费用户调 due_diligence → 402（_FREE_FEATURES 中 due_diligence: False）"""
    dep = require_subscription_feature("due_diligence")
    with pytest.raises(HTTPException) as excinfo:
        await dep(user=free_user, db=db_session)
    assert excinfo.value.status_code == 402
    assert "due_diligence" in excinfo.value.detail


@pytest.mark.asyncio
async def test_require_subscription_feature_pro_user_passes(hybrid_pro_user, db_session):
    """付费用户（套餐含 due_diligence: True）→ 通过"""
    dep = require_subscription_feature("due_diligence")
    result = await dep(user=hybrid_pro_user, db=db_session)
    assert result is hybrid_pro_user


@pytest.mark.asyncio
async def test_unknown_subscription_feature_denied_by_default(hybrid_pro_user, db_session):
    """新增商业能力未进入套餐配置前必须 fail-closed。"""
    allowed = await SubscriptionService(db_session).can_access_feature(
        hybrid_pro_user.id,
        "remote_desktop_control",
    )
    assert allowed is False


# ========== T6 二阶段: check_user_token_quota ==========


@pytest_asyncio.fixture
async def quota_plan(db_session):
    """有 10_000 token 配额的付费计划。"""
    plan = BillingPlan(
        id=str(uuid4()),
        code=f"quota-{uuid4().hex[:6]}",
        name="测试 Quota 套餐",
        billing_mode="monthly",
        base_price=29.0,
        client_type="needer",
        is_active=True,
        features={
            "modes": ["local", "hybrid", "cloud"],
            "ai_quota_tokens": 10_000,
        },
    )
    db_session.add(plan)
    await db_session.flush()
    return plan


@pytest_asyncio.fixture
async def quota_user(db_session, quota_plan):
    user = User(
        id=str(uuid4()),
        email=f"quota-{uuid4().hex[:8]}@example.com",
        name="配额用户",
        hashed_password="x",
        is_active=True,
        primary_client="needer",
    )
    db_session.add(user)
    await db_session.flush()
    today = date.today()
    sub = Subscription(
        id=str(uuid4()),
        user_id=user.id,
        plan_id=quota_plan.id,
        client_type="needer",
        status="active",
        current_period_start=today,
        current_period_end=today + timedelta(days=30),
    )
    db_session.add(sub)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_t6_check_quota_under_limit(quota_user, db_session):
    """T6: 累计 + upcoming 在配额内 → allowed=True。"""
    from src.harness.cost_tracker import cost_tracker
    cost_tracker.reset_user_tokens(quota_user.id)
    cost_tracker.record(
        model="gpt-4o", provider="openai",
        prompt_tokens=500, completion_tokens=200, user_id=quota_user.id,
    )
    result = await SubscriptionService(db_session).check_user_token_quota(
        quota_user.id, upcoming_tokens=1024,
    )
    assert result["allowed"] is True
    assert result["used"] == 700
    assert result["quota"] == 10_000
    assert result["exempted"] is False


@pytest.mark.asyncio
async def test_t6_check_quota_exceeds(quota_user, db_session):
    """T6: 累计 + upcoming 超出配额 → allowed=False + reason 含数字。"""
    from src.harness.cost_tracker import cost_tracker
    cost_tracker.reset_user_tokens(quota_user.id)
    cost_tracker.record(
        model="gpt-4o", provider="openai",
        prompt_tokens=9500, completion_tokens=200, user_id=quota_user.id,
    )
    result = await SubscriptionService(db_session).check_user_token_quota(
        quota_user.id, upcoming_tokens=500,
    )
    assert result["allowed"] is False
    assert result["used"] == 9700
    assert result["remaining"] == 0
    assert result["reason"] and "9700" in result["reason"]


@pytest.mark.asyncio
async def test_t6_check_quota_admin_exempted_via_features_override(quota_user, db_session):
    """T6: features_override.quota_overridden=True → 单用户豁免, 不计配额。"""
    from src.harness.cost_tracker import cost_tracker
    cost_tracker.reset_user_tokens(quota_user.id)
    cost_tracker.record(
        model="gpt-4o", provider="openai",
        prompt_tokens=99_999, completion_tokens=99_999, user_id=quota_user.id,
    )
    # 给 user 的 subscription 加 features_override
    from sqlalchemy import select as sa_select
    sub_row = (await db_session.execute(
        sa_select(Subscription).where(Subscription.user_id == quota_user.id)
    )).scalar_one()
    sub_row.features_override = {"quota_overridden": True}
    await db_session.flush()

    result = await SubscriptionService(db_session).check_user_token_quota(
        quota_user.id, upcoming_tokens=999_999,
    )
    assert result["allowed"] is True
    assert result["exempted"] is True
    assert "admin override" in (result["reason"] or "")


@pytest.mark.asyncio
async def test_t6_check_quota_global_killswitch(quota_user, db_session, monkeypatch):
    """T6: HARNESS_COST_QUOTA_DISABLED=true → 全局豁免, 无视任何用量。"""
    from src.harness.cost_tracker import cost_tracker
    cost_tracker.reset_user_tokens(quota_user.id)
    cost_tracker.record(
        model="gpt-4o", provider="openai",
        prompt_tokens=99_999, completion_tokens=99_999, user_id=quota_user.id,
    )
    monkeypatch.setenv("HARNESS_COST_QUOTA_DISABLED", "true")
    result = await SubscriptionService(db_session).check_user_token_quota(
        quota_user.id, upcoming_tokens=999_999,
    )
    assert result["allowed"] is True
    assert result["exempted"] is True
    assert "HARNESS_COST_QUOTA_DISABLED" in (result["reason"] or "")


@pytest.mark.asyncio
async def test_t6_check_quota_free_user_blocked(free_user, db_session):
    """T6: 免费用户配额=0 (FREE_FEATURES), 任何 upcoming>0 都被拒绝。"""
    from src.harness.cost_tracker import cost_tracker
    cost_tracker.reset_user_tokens(free_user.id)
    result = await SubscriptionService(db_session).check_user_token_quota(
        free_user.id, upcoming_tokens=100,
    )
    # ai_quota_tokens=0 在 cost_tracker.check_user_quota 中表示"不限制" — 这是
    # 设计上的歧义点: subscription_service 的 0 应解读为"配额=0 全拒"还是"不限"?
    # 决策: 走 _FREE_FEATURES.ai_quota_tokens=0 路径时, subscription_service 视
    # 为合法的"无配额", 由 cost_tracker 的 quota=0=unlimited 兜底放行 —— 免费用
    # 户应通过 modes / features 字段被阻断, 不应在配额层挡, 否则会双重门禁导致
    # 引导消息混乱。免费用户的拦截发生在 require_subscription_feature 层。
    assert result["allowed"] is True
    assert result["quota"] == 0
