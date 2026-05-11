# -*- coding: utf-8 -*-
"""
SkillExecutor 装饰器

``@requires_skill("name")`` 给 agent 方法标注「我依赖某个 skill」。

使用场景：
    1. 启动时扫描所有装饰过的方法，反推出"agent → skills"依赖图
    2. 调用前自动校验 ``SkillRegistry`` 中确实有该 skill 且 enabled
    3. 文档生成 / 权限审计

不会自动执行该 skill —— 只做「契约声明」。
真正执行还是由 agent 内部按业务逻辑调 ``SkillExecutor.execute(...)``。
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from src.services.skill_registry import SkillRegistry

F = TypeVar("F", bound=Callable[..., Any])

# 全局收集表：{agent_method: [skill_name, ...]}
_REGISTERED: dict[Callable[..., Any], list[str]] = {}


def requires_skill(*skill_names: str) -> Callable[[F], F]:
    """声明 agent 方法依赖一组 skill。

    用法::

        class ContractAgent:
            @requires_skill("contract-review")
            async def review(self, text: str): ...

    被装饰函数会带上 ``__required_skills__`` 属性，便于内省。
    """
    if not skill_names:
        raise ValueError("requires_skill 至少需要一个 skill 名")

    def decorator(func: F) -> F:
        existing: list[str] = list(getattr(func, "__required_skills__", []))
        for n in skill_names:
            if n and n not in existing:
                existing.append(n)
        setattr(func, "__required_skills__", existing)
        _REGISTERED[func] = existing

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            registry = SkillRegistry.instance()
            missing = [n for n in existing if registry.get(n) is None]
            if missing:
                # 不抛 —— 只警告，让 agent 自己决定降级；测试可关掉日志
                import logging

                logging.getLogger(__name__).warning(
                    "%s 声明依赖但未注册: %s", func.__qualname__, missing
                )
            return func(*args, **kwargs)

        # 保留属性
        setattr(wrapper, "__required_skills__", existing)
        return wrapper  # type: ignore[return-value]

    return decorator


def get_registered_skills() -> dict[Callable[..., Any], list[str]]:
    """返回 ``{func: [skill_name,...]}`` 的拷贝（调试 / 审计用）。"""
    return {k: list(v) for k, v in _REGISTERED.items()}


__all__ = ["requires_skill", "get_registered_skills"]
