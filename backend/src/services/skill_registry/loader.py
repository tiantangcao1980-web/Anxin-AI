# -*- coding: utf-8 -*-
"""
SkillLoader —— 从 SKILL.md 加载技能

兼容 cowork / Anthropic Skills 格式：
    - YAML frontmatter（``---`` 包裹）+ markdown body
    - 必须字段：``name``、``description``
    - 可选字段：``version``、``type``、``triggers``、``dependencies``、``requires_apps``

P5 实现要点：
    - 监听文件变更（watchdog）实现热更新
    - 校验 trigger 不冲突；同名后注册覆盖前者并打 WARN
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.services.skill_registry.models import Skill


class SkillParseError(ValueError):
    """SKILL.md 解析失败。"""


# YAML frontmatter 正则：开头三横线 + 内容 + 三横线
_FRONTMATTER_RE = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n(.*)$",
    re.DOTALL,
)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """切出 frontmatter 与 body。

    P5 实现使用 PyYAML，骨架阶段使用极简手写 parser，
    仅支持 ``key: value`` 与 ``key:\n  - item`` 两种语法。
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise SkillParseError("缺少 YAML frontmatter（应以 --- 开头/结尾）")

    raw_yaml, body = match.group(1), match.group(2)
    meta = _parse_simple_yaml(raw_yaml)
    return meta, body.strip()


def _parse_simple_yaml(raw: str) -> dict[str, Any]:
    """极简 YAML（仅 frontmatter 用），P5 替换为 ``yaml.safe_load``。

    规则：
        - 顶层 ``key: value``
        - 顶层 ``key:`` 后跟若干 ``  - item`` 行 → list
        - 忽略空行 / ``#`` 注释
    """
    result: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] | None = None

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # list item
        if stripped.startswith("- ") and current_key is not None and current_list is not None:
            current_list.append(stripped[2:].strip())
            continue

        # key: value or key:
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if value == "":
                # 进入 list 模式
                current_key = key
                current_list = []
                result[key] = current_list
            else:
                result[key] = value
                current_key = None
                current_list = None
        # 其它格式忽略（骨架阶段不严格）
    return result


class SkillLoader:
    """SKILL.md 加载器。

    用法::

        loader = SkillLoader()
        skill = loader.load_from_file("skills/contract-review/SKILL.md")
        all_skills = loader.load_from_directory("skills/")
    """

    SKILL_FILE_NAMES: tuple[str, ...] = ("SKILL.md", "skill.md")

    def load_from_file(self, path: str | Path) -> Skill:
        """从单个 SKILL.md 文件加载技能。

        参数：
            path: 文件路径

        返回：
            ``Skill`` 实例

        异常：
            ``FileNotFoundError`` / ``SkillParseError``

        阶段：P5（骨架已可用，校验后续加强）。
        """
        file_path = Path(path).resolve()
        if not file_path.is_file():
            raise FileNotFoundError(f"SKILL.md 不存在: {file_path}")

        text = file_path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)

        if "name" not in meta or "description" not in meta:
            raise SkillParseError(
                f"{file_path}: frontmatter 缺少必需字段 name/description"
            )

        triggers = meta.get("triggers") or []
        deps = meta.get("dependencies") or []
        apps = meta.get("requires_apps") or []

        # 容错：value 可能是字符串而非 list
        if isinstance(triggers, str):
            triggers = [triggers]
        if isinstance(deps, str):
            deps = [deps]
        if isinstance(apps, str):
            apps = [apps]

        return Skill(
            name=str(meta["name"]).strip(),
            description=str(meta["description"]).strip(),
            version=str(meta.get("version", "0.0.0")).strip(),
            type=str(meta.get("type", "general")).strip(),
            triggers=[str(t).strip() for t in triggers if str(t).strip()],
            body=body,
            file_path=file_path,
            dependencies=[str(d).strip() for d in deps if str(d).strip()],
            requires_apps=[str(a).strip() for a in apps if str(a).strip()],
        )

    def load_from_directory(self, root: str | Path) -> list[Skill]:
        """递归扫描目录下所有 ``SKILL.md`` / ``skill.md`` 并加载。

        参数：
            root: 根目录

        返回：
            ``Skill`` 列表（解析失败的文件会跳过，由调用方决定是否记录日志）。

        阶段：P5。
        """
        root_path = Path(root).resolve()
        if not root_path.is_dir():
            raise NotADirectoryError(f"非目录: {root_path}")

        skills: list[Skill] = []
        for name in self.SKILL_FILE_NAMES:
            for file_path in root_path.rglob(name):
                try:
                    skills.append(self.load_from_file(file_path))
                except SkillParseError:
                    # P5：换为日志告警；骨架阶段静默跳过，避免单文件坏掉拖整批
                    continue
        return skills
