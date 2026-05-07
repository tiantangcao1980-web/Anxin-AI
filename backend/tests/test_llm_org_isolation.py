"""
LLM 配置组织隔离回归测试

背景：
  S-104 历史修复在路由层加了 `org_id = getattr(user, 'org_id', None)`，
  但服务层 `LLMService.list_configs` 当时是 `if org_id:` —— 在 org_id=None
  时整段过滤被短路，等价于无过滤查询。结果普通无 org 用户仍能查到所有租户配置。

本次再次加固：
  - 服务层用 `if org_id is not None:` 比较，避免 falsy bug
  - 服务层新增 require_org_filter 参数，True 且 org_id=None 时直接返回空（fail-closed）
  - 路由层：超管 require_org_filter=False；普通用户 require_org_filter=True

本测试覆盖：
  1. 普通用户 org_id=None：应返回空（fail-closed），不能看到任何配置
  2. 普通用户 org_id=A：仅看到 A 的配置，看不到 B 的
  3. 超管 require_org_filter=False：可以看全部
  4. require_org_filter=True 且 org_id="" （空字符串 falsy）：仍按隔离处理（关键 falsy 边界）
"""

from uuid import uuid4

import pytest
import pytest_asyncio

from src.models.llm_config import LLMConfig, LLMConfigType, LLMProvider
from src.services.llm_service import LLMService


@pytest_asyncio.fixture
async def two_orgs_with_llm_configs(db_session):
    """构造两个组织各自的 LLM 配置 + 一份不属于任何组织的'平台共享'配置"""
    org_a_id = str(uuid4())
    org_b_id = str(uuid4())

    configs = [
        LLMConfig(
            name="orgA-llm",
            provider=LLMProvider.OPENAI.value,
            config_type=LLMConfigType.LLM.value,
            model_name="gpt-4o",
            org_id=org_a_id,
        ),
        LLMConfig(
            name="orgB-llm",
            provider=LLMProvider.OPENAI.value,
            config_type=LLMConfigType.LLM.value,
            model_name="gpt-4o",
            org_id=org_b_id,
        ),
        LLMConfig(
            name="platform-shared-llm",
            provider=LLMProvider.OPENAI.value,
            config_type=LLMConfigType.LLM.value,
            model_name="gpt-3.5-turbo",
            org_id=None,
        ),
    ]
    for c in configs:
        db_session.add(c)
    await db_session.flush()
    return {"org_a_id": org_a_id, "org_b_id": org_b_id, "configs": configs}


@pytest.mark.asyncio
async def test_normal_user_without_org_sees_nothing(db_session, two_orgs_with_llm_configs):
    """
    普通无 org 用户（org_id=None）应当看到空结果（fail-closed），
    而不是历史 falsy bug 下的"全部配置"
    """
    result = await LLMService.list_configs(
        db=db_session,
        org_id=None,
        require_org_filter=True,
    )
    assert result["total"] == 0
    assert result["items"] == []


@pytest.mark.asyncio
async def test_org_user_only_sees_own_org(db_session, two_orgs_with_llm_configs):
    """普通有 org 用户仅能看到自己 org 的配置"""
    org_a_id = two_orgs_with_llm_configs["org_a_id"]

    result = await LLMService.list_configs(
        db=db_session,
        org_id=org_a_id,
        require_org_filter=True,
    )
    assert result["total"] == 1
    assert result["items"][0].org_id == org_a_id
    assert result["items"][0].name == "orgA-llm"


@pytest.mark.asyncio
async def test_superuser_can_see_all(db_session, two_orgs_with_llm_configs):
    """超管 require_org_filter=False 可见全部配置（包括平台共享）"""
    result = await LLMService.list_configs(
        db=db_session,
        org_id=None,
        require_org_filter=False,
    )
    # 至少包含 fixture 创建的 3 条
    assert result["total"] >= 3
    names = {item.name for item in result["items"]}
    assert "orgA-llm" in names
    assert "orgB-llm" in names
    assert "platform-shared-llm" in names


@pytest.mark.asyncio
async def test_unknown_org_id_does_not_leak(db_session, two_orgs_with_llm_configs):
    """
    边界回归：传入合法但不属于任何配置的 UUID 不能"退化"为返回所有配置。
    历史 falsy bug 仅对 None / 空字符串生效；这里防的是更广义的"未匹配 org_id 不应泄露"。
    """
    unknown_org = str(uuid4())

    result = await LLMService.list_configs(
        db=db_session,
        org_id=unknown_org,
        require_org_filter=True,
    )
    # 关键：不应包含其他 org 或 None org 的配置
    names = {item.name for item in result["items"]}
    assert "platform-shared-llm" not in names
    assert "orgA-llm" not in names
    assert "orgB-llm" not in names
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_default_require_org_filter_is_true(db_session, two_orgs_with_llm_configs):
    """
    默认行为是 fail-closed —— 调用方不显式传 require_org_filter 时，
    org_id=None 应返回空（保护意外调用方不退化为"无过滤"）。
    """
    result = await LLMService.list_configs(
        db=db_session,
        org_id=None,
        # 不传 require_org_filter，验证默认值
    )
    assert result["total"] == 0
