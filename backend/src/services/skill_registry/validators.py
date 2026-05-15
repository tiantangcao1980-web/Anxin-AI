"""
SkillRegistry 静态校验器

职责：在加载完一批 ``Skill`` 后做一次性体检，给出可读错误列表，
而不是在运行时报错。典型用途：

    - 启动时 `load_directory` → `validate_all` → 把错误打到日志
    - CI 中跑一遍，阻止格式不合规的 SKILL.md 合入
    - API ``/skills/upload`` 在写入前做 dry-run 校验
"""

from __future__ import annotations

from collections.abc import Iterable

from src.services.skill_registry.models import Skill

REQUIRED_FIELDS: tuple[str, ...] = ("name", "description")


def validate_skill(skill: Skill) -> list[str]:
    """单条 ``Skill`` 静态校验，返回错误信息列表（空 = OK）。"""
    errors: list[str] = []

    if not skill.name or not skill.name.strip():
        errors.append("name 不能为空")
    elif " " in skill.name:
        errors.append(f"name 不应包含空格: {skill.name!r}")

    if not skill.description or not skill.description.strip():
        errors.append("description 不能为空")

    if skill.dependencies and skill.name in skill.dependencies:
        errors.append(f"自依赖：{skill.name} 在 dependencies 中引用自己")

    # trigger 内部去重检查（同一 skill 内重复 trigger 是配置错误）
    seen: dict[str, int] = {}
    for trig in skill.triggers:
        key = trig.strip().lower()
        if not key:
            errors.append("triggers 包含空字符串")
            continue
        seen[key] = seen.get(key, 0) + 1
    dup_inside = [k for k, n in seen.items() if n > 1]
    if dup_inside:
        errors.append(f"triggers 内部重复: {dup_inside}")

    return errors


def validate_all(skills: Iterable[Skill]) -> list[str]:
    """对一组 ``Skill`` 做整体校验：

    1. 单条字段校验
    2. trigger 跨 skill 冲突（同一 trigger 被多个 skill 注册）
    3. 依赖完整性（dependencies 引用了不存在的 skill name）
    4. 依赖循环检测（DFS 着色法）
    """
    items = list(skills)
    errors: list[str] = []

    # 1. 单条
    for s in items:
        for err in validate_skill(s):
            errors.append(f"[{s.name or '<unnamed>'}] {err}")

    # 2. trigger 跨 skill 冲突
    by_trigger: dict[str, list[str]] = {}
    for s in items:
        for trig in s.triggers:
            key = trig.strip().lower()
            if not key:
                continue
            by_trigger.setdefault(key, []).append(s.name)
    for trig, owners in by_trigger.items():
        if len(set(owners)) > 1:
            errors.append(f"trigger 冲突: {trig!r} 被多个 skill 注册: {sorted(set(owners))}")

    # 3. 依赖完整性
    name_set = {s.name for s in items if s.name}
    for s in items:
        for dep in s.dependencies:
            if dep not in name_set:
                errors.append(f"[{s.name}] 依赖不存在的 skill: {dep}")

    # 4. 循环依赖（白/灰/黑三色 DFS）
    by_name = {s.name: s for s in items if s.name}
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(by_name, WHITE)
    cycles: list[list[str]] = []

    def dfs(node: str, path: list[str]) -> None:
        color[node] = GRAY
        path.append(node)
        for dep in by_name[node].dependencies:
            if dep not in by_name:
                continue
            if color[dep] == GRAY:
                # 找到回边
                idx = path.index(dep)
                cycles.append(path[idx:] + [dep])
            elif color[dep] == WHITE:
                dfs(dep, path)
        path.pop()
        color[node] = BLACK

    for n in list(by_name):
        if color[n] == WHITE:
            dfs(n, [])

    seen_cycle: set[tuple[str, ...]] = set()
    for cyc in cycles:
        # 规范化（最小字典序起点）便于去重
        if not cyc:
            continue
        rotated = min(
            tuple(cyc[i:] + cyc[:i]) for i in range(len(cyc) - 1)
        ) if len(cyc) > 1 else tuple(cyc)
        if rotated in seen_cycle:
            continue
        seen_cycle.add(rotated)
        errors.append(f"循环依赖: {' -> '.join(cyc)}")

    return errors


__all__ = ["REQUIRED_FIELDS", "validate_skill", "validate_all"]
