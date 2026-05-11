# -*- coding: utf-8 -*-
"""
Skill 运行时对象（dataclass）

注意：本模块的 ``Skill`` **不入库**，是进程内运行时对象。
SKILL.md 文件本身就是“持久化层”，热更新时直接 reload 即可。

P5 升级：
    - 新增 ``personas`` / ``category`` / ``enabled`` / ``author`` 字段
    - ``find_by_trigger`` 评分支持（命中关键词数量）
    - 序列化包含全部新字段，便于 API 返回
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Skill:
    """运行时技能对象。

    字段：
        name           : 技能唯一标识（snake/kebab）
        description    : 一句话描述
        version        : 语义化版本，默认 ``0.0.0``
        type           : 旧字段，保留兼容；新接入请用 ``category``
        category       : 领域分类：``legal`` / ``office`` / ``research`` / ``dev`` / ...
        triggers       : 触发词列表（``find_by_trigger`` 召回用）
        body           : 正文 markdown（注入 system prompt）
        file_path      : 来源 SKILL.md 绝对路径（热更新时定位）
        dependencies   : 依赖的其它 skill name
        requires_apps  : 需要的 OAuth 应用授权 ID（如 ``feishu``、``dingtalk``）
        personas       : 哪些 user-facing persona 可调用（如 ``lawyer``、``hr``）
        enabled        : 运行时是否启用（被 toggle 关闭后不会被 ``find_by_trigger`` 召回）
        author         : 作者署名（可选）
    """

    name: str
    description: str
    version: str = "0.0.0"
    type: str = "general"
    category: str = "general"
    triggers: list[str] = field(default_factory=list)
    body: str = ""
    file_path: Path | None = None
    dependencies: list[str] = field(default_factory=list)
    requires_apps: list[str] = field(default_factory=list)
    personas: list[str] = field(default_factory=list)
    enabled: bool = True
    author: str | None = None

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    def matches_trigger(self, text: str) -> bool:
        """判断 ``text`` 是否包含任一触发词（不区分大小写）。"""
        return self.trigger_score(text) > 0

    def trigger_score(self, text: str) -> int:
        """返回 ``text`` 命中触发词的数量。

        简单实现：不区分大小写的子串匹配；
        作为 ``find_by_trigger(top_k)`` 的排序依据。
        """
        if not text or not self.triggers:
            return 0
        lowered = text.lower()
        return sum(1 for t in self.triggers if t and t.lower() in lowered)

    def supports_app(self, app: str) -> bool:
        """判断技能是否适配某客户端；空 ``requires_apps`` 视为通用。"""
        if not self.requires_apps:
            return True
        return app in self.requires_apps

    def supports_persona(self, persona: str) -> bool:
        """判断技能是否对外开放给某 persona；空 ``personas`` 视为全员可用。"""
        if not self.personas:
            return True
        return persona in self.personas

    def to_dict(self) -> dict[str, object]:
        """序列化为可 JSON 编码的字典（管理 UI / 调试用）。"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "type": self.type,
            "category": self.category,
            "triggers": list(self.triggers),
            "dependencies": list(self.dependencies),
            "requires_apps": list(self.requires_apps),
            "personas": list(self.personas),
            "enabled": self.enabled,
            "author": self.author,
            "file_path": str(self.file_path) if self.file_path else None,
            "body_length": len(self.body),
        }
