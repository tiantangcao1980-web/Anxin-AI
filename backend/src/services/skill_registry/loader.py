# -*- coding: utf-8 -*-
"""
SkillLoader —— 从 SKILL.md 加载技能（P5 真实装版）

兼容 cowork / Anthropic Skills 格式：
    - YAML frontmatter（``---`` 包裹）+ markdown body
    - 必须字段：``name``、``description``
    - 可选字段：``version``、``type``、``category``、``triggers``、
      ``dependencies``、``requires_apps``、``personas``、``enabled``、``author``

P5 升级要点：
    - 用 ``yaml.safe_load`` 替换骨架手写 parser，全面支持嵌套 list/dict
    - 字段名兼容 cowork 的多种拼写（``trigger``/``triggers``、``apps``/``requires_apps``）
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from src.services.skill_registry.models import Skill


class SkillParseError(ValueError):
    """SKILL.md 解析失败。"""


# YAML frontmatter 正则：开头三横线 + 内容 + 三横线
_FRONTMATTER_RE = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n?(.*)$",
    re.DOTALL,
)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """切出 frontmatter 与 body。

    使用 ``yaml.safe_load``，全面支持 list、dict、嵌套结构、
    多行字符串（``|`` / ``>``）等 YAML 1.1 子集。
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise SkillParseError("缺少 YAML frontmatter（应以 --- 开头/结尾）")

    raw_yaml, body = match.group(1), match.group(2)
    try:
        meta = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError as exc:
        raise SkillParseError(f"YAML frontmatter 解析失败: {exc}") from exc

    if not isinstance(meta, dict):
        raise SkillParseError("frontmatter 必须是 mapping（key: value）")

    return meta, body.strip()


def _coerce_str_list(value: Any) -> list[str]:
    """容错地把任意值转成 ``list[str]``。

    - ``None`` / 空 → ``[]``
    - 单个字符串 → ``[value]``
    - list → 逐项 ``str().strip()`` 并去空
    """
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = [value]
    out: list[str] = []
    for item in items:
        if item is None:
            continue
        s = str(item).strip()
        if s:
            out.append(s)
    return out


def _coerce_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in {"true", "yes", "y", "1", "on", "enabled"}:
        return True
    if s in {"false", "no", "n", "0", "off", "disabled"}:
        return False
    return default


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

        # 字段兼容：trigger/triggers，apps/requires_apps
        triggers = meta.get("triggers")
        if triggers is None:
            triggers = meta.get("trigger")
        deps = meta.get("dependencies")
        if deps is None:
            deps = meta.get("depends_on")
        apps = meta.get("requires_apps")
        if apps is None:
            apps = meta.get("apps")
        personas = meta.get("personas")
        if personas is None:
            personas = meta.get("persona")

        category = meta.get("category") or meta.get("type") or "general"
        type_ = meta.get("type") or category

        author = meta.get("author")
        if author is not None:
            author = str(author).strip() or None

        sandbox_raw = meta.get("sandbox")
        if sandbox_raw is not None and not isinstance(sandbox_raw, dict):
            raise SkillParseError(
                f"{file_path}: frontmatter.sandbox 必须是 mapping，得到 {type(sandbox_raw).__name__}"
            )

        return Skill(
            name=str(meta["name"]).strip(),
            description=str(meta["description"]).strip(),
            version=str(meta.get("version", "0.0.0")).strip(),
            type=str(type_).strip(),
            category=str(category).strip(),
            triggers=_coerce_str_list(triggers),
            body=body,
            file_path=file_path,
            dependencies=_coerce_str_list(deps),
            requires_apps=_coerce_str_list(apps),
            personas=_coerce_str_list(personas),
            enabled=_coerce_bool(meta.get("enabled"), default=True),
            author=author,
            sandbox_raw=sandbox_raw,
        )

    def load_from_directory(self, root: str | Path) -> list[Skill]:
        """递归扫描目录下所有 ``SKILL.md`` / ``skill.md`` 并加载。

        参数：
            root: 根目录

        返回：
            ``Skill`` 列表（解析失败的文件会跳过，由调用方决定是否记录日志）。
        """
        root_path = Path(root).resolve()
        if not root_path.is_dir():
            raise NotADirectoryError(f"非目录: {root_path}")

        skills: list[Skill] = []
        # 用 (st_dev, st_ino) 去重，跨大小写不敏感文件系统也安全
        seen_ino: set[tuple[int, int]] = set()
        for name in self.SKILL_FILE_NAMES:
            for file_path in root_path.rglob(name):
                try:
                    st = file_path.stat()
                except OSError:
                    continue
                key = (st.st_dev, st.st_ino)
                if key in seen_ino:
                    continue
                seen_ino.add(key)
                try:
                    skills.append(self.load_from_file(file_path))
                except SkillParseError:
                    # 单文件坏掉不应拖垮整批；调用方决定是否打日志
                    continue
        return skills
