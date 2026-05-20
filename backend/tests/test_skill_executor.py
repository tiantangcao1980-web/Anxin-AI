"""
P5-A: SkillExecutor 单元测试

覆盖：
    - execute 成功（mock LLM）
    - execute 失败（LLM 抛异常）
    - execute_batch 并发返回顺序保持
    - skill 不存在 / disabled / persona 不匹配 / 缺 app 授权
    - decorator @requires_skill 标注属性
    - prompt 内容包含 skill body + payload + context
"""

from __future__ import annotations

import asyncio

import pytest

from src.services.skill_executor import (
    ExecutionContext,
    SkillExecutor,
    requires_skill,
)
from src.services.skill_executor.models import SkillExecutionStatus
from src.services.skill_registry import Skill, SkillRegistry


@pytest.fixture
def registry() -> SkillRegistry:
    SkillRegistry.reset_instance()
    yield SkillRegistry.instance()
    SkillRegistry.reset_instance()


@pytest.fixture
def basic_skill(registry: SkillRegistry) -> Skill:
    s = Skill(
        name="echo",
        description="回显技能",
        version="1.0.0",
        category="dev",
        body="按用户输入复述",
        triggers=["echo"],
    )
    registry.register(s)
    return s


@pytest.fixture
def context() -> ExecutionContext:
    return ExecutionContext(user_id="u1", persona="default")


class TestExecute:
    @pytest.mark.asyncio
    async def test_success_with_sync_llm(
        self, registry: SkillRegistry, basic_skill: Skill, context: ExecutionContext
    ) -> None:
        captured: dict[str, str] = {}

        def fake_llm(system: str, user: str) -> str:
            captured["system"] = system
            captured["user"] = user
            return "OK"

        executor = SkillExecutor(registry=registry, llm_callable=fake_llm)
        result = await executor.execute("echo", {"q": "hello"}, context)

        assert result.ok
        assert result.status == SkillExecutionStatus.SUCCESS
        assert result.output == "OK"
        # prompt 应包含技能名 / body / payload
        assert "echo" in captured["system"]
        assert "按用户输入复述" in captured["system"]
        assert "hello" in captured["user"]

    @pytest.mark.asyncio
    async def test_success_with_async_llm(
        self, registry: SkillRegistry, basic_skill: Skill, context: ExecutionContext
    ) -> None:
        async def fake_llm(system: str, user: str) -> str:
            await asyncio.sleep(0)
            return "ASYNC OK"

        executor = SkillExecutor(registry=registry, llm_callable=fake_llm)
        result = await executor.execute("echo", {}, context)
        assert result.ok and result.output == "ASYNC OK"

    @pytest.mark.asyncio
    async def test_skill_not_found(
        self, registry: SkillRegistry, context: ExecutionContext
    ) -> None:
        executor = SkillExecutor(registry=registry, llm_callable=lambda s, u: "x")
        result = await executor.execute("nope", {}, context)
        assert result.status == SkillExecutionStatus.FAILED
        assert "不存在" in (result.error or "")

    @pytest.mark.asyncio
    async def test_disabled_skipped(
        self, registry: SkillRegistry, basic_skill: Skill, context: ExecutionContext
    ) -> None:
        registry.toggle("echo", False)
        executor = SkillExecutor(registry=registry, llm_callable=lambda s, u: "x")
        result = await executor.execute("echo", {}, context)
        assert result.status == SkillExecutionStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_persona_not_allowed(
        self, registry: SkillRegistry, context: ExecutionContext
    ) -> None:
        registry.register(Skill(name="lawyer-only", description="x", personas=["lawyer"]))
        executor = SkillExecutor(registry=registry, llm_callable=lambda s, u: "x")
        # context.persona = "default"
        result = await executor.execute("lawyer-only", {}, context)
        assert result.status == SkillExecutionStatus.SKIPPED
        assert "persona" in (result.error or "")

    @pytest.mark.asyncio
    async def test_missing_app_authorization(
        self, registry: SkillRegistry, context: ExecutionContext
    ) -> None:
        registry.register(
            Skill(
                name="dingtalk-skill",
                description="x",
                requires_apps=["dingtalk"],
            )
        )
        executor = SkillExecutor(registry=registry, llm_callable=lambda s, u: "x")
        result = await executor.execute("dingtalk-skill", {}, context)
        assert result.status == SkillExecutionStatus.SKIPPED
        assert result.metadata.get("missing_apps") == ["dingtalk"]

    @pytest.mark.asyncio
    async def test_app_authorization_ok(self, registry: SkillRegistry) -> None:
        registry.register(
            Skill(
                name="dingtalk-skill",
                description="x",
                requires_apps=["dingtalk"],
            )
        )
        ctx = ExecutionContext(user_id="u1", persona="default", app_authorizations=["dingtalk"])
        executor = SkillExecutor(registry=registry, llm_callable=lambda s, u: "OK")
        result = await executor.execute("dingtalk-skill", {}, ctx)
        assert result.ok

    @pytest.mark.asyncio
    async def test_llm_exception_returns_failed(
        self, registry: SkillRegistry, basic_skill: Skill, context: ExecutionContext
    ) -> None:
        def boom(system: str, user: str) -> str:
            raise RuntimeError("LLM 炸了")

        executor = SkillExecutor(registry=registry, llm_callable=boom)
        result = await executor.execute("echo", {}, context)
        assert result.status == SkillExecutionStatus.FAILED
        assert "炸了" in (result.error or "")

    @pytest.mark.asyncio
    async def test_logs_recorded(
        self, registry: SkillRegistry, basic_skill: Skill, context: ExecutionContext
    ) -> None:
        executor = SkillExecutor(registry=registry, llm_callable=lambda s, u: "OK")
        await executor.execute("echo", {"a": 1}, context)
        await executor.execute("echo", {"a": 2}, context)
        assert len(executor.logs) == 2
        executor.clear_logs()
        assert executor.logs == []


class TestExecuteBatch:
    @pytest.mark.asyncio
    async def test_batch_returns_in_order(
        self, registry: SkillRegistry, context: ExecutionContext
    ) -> None:
        for n in ["a", "b", "c"]:
            registry.register(Skill(name=n, description=n))

        async def fake_llm(system: str, user: str) -> str:
            await asyncio.sleep(0)
            return system.split("\n")[0]  # 第一行带 skill name

        executor = SkillExecutor(registry=registry, llm_callable=fake_llm)
        results = await executor.execute_batch(
            [("a", {}), ("b", {}), ("c", {})], context, concurrency=2
        )
        assert [r.skill_name for r in results] == ["a", "b", "c"]
        assert all(r.ok for r in results)

    @pytest.mark.asyncio
    async def test_batch_partial_failure(
        self, registry: SkillRegistry, context: ExecutionContext
    ) -> None:
        registry.register(Skill(name="ok", description="x"))
        # "missing" 不注册，应返回 FAILED 而不抛
        executor = SkillExecutor(registry=registry, llm_callable=lambda s, u: "OK")
        results = await executor.execute_batch([("ok", {}), ("missing", {})], context)
        assert results[0].ok
        assert results[1].status == SkillExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_empty_batch(self, registry: SkillRegistry, context: ExecutionContext) -> None:
        executor = SkillExecutor(registry=registry, llm_callable=lambda s, u: "x")
        assert await executor.execute_batch([], context) == []


class TestRequiresSkillDecorator:
    def test_attaches_attribute(self) -> None:
        @requires_skill("foo", "bar")
        def f():
            return "x"

        assert f.__required_skills__ == ["foo", "bar"]

    def test_dedupes_when_stacked(self) -> None:
        @requires_skill("foo")
        @requires_skill("bar")
        def f():
            return "x"

        attrs = f.__required_skills__
        assert "foo" in attrs and "bar" in attrs

    def test_call_passthrough(self) -> None:
        @requires_skill("anything")
        def f(x):
            return x * 2

        assert f(3) == 6

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            requires_skill()  # type: ignore[call-arg]


class TestExecutionContext:
    def test_to_prompt_block_includes_authz_and_extra(self) -> None:
        ctx = ExecutionContext(
            user_id="u1",
            persona="lawyer",
            app_authorizations=["dingtalk", "feishu"],
            org_id="org-9",
            extra={"case_id": "case-1"},
        )
        block = ctx.to_prompt_block()
        assert "u1" in block
        assert "lawyer" in block
        assert "dingtalk" in block and "feishu" in block
        assert "org-9" in block
        assert "case_id" in block
