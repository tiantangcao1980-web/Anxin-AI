# -*- coding: utf-8 -*-
"""
Skill 运行时对象（dataclass）

注意：本模块的 ``Skill`` **不入库**，是进程内运行时对象。
SKILL.md 文件本身就是"持久化层"，热更新时直接 reload 即可。
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
        type           : 领域：``legal`` / ``office`` / ``research`` / ``dev`` / ...
        triggers       : 触发词列表（``find_by_trigger`` 召回用）
        body           : 正文 markdown（注入 system prompt）
        file_path      : 来源 SKILL.md 绝对路径（热更新时定位）
        dependencies   : 依赖的其它 skill name
        requires_apps  : 适配的客户端：``desktop`` / ``web`` / ``mobile`` / ``mp`` / ``im``
    """

    name: str
    description: str
    version: str = "0.0.0"
    type: str = "general"
    triggers: list[str] = field(default_factory=list)
    body: str = ""
    file_path: Path | None = None
    dependencies: list[str] = field(default_factory=list)
    requires_apps: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    def matches_trigger(self, text: str) -> bool:
        """判断 ``text`` 是否包含任一触发词（不区分大小写）。

        骨架阶段使用简单子串匹配；P5 升级为分词 + embedding 相似度。
        """
        if not text or not self.triggers:
            return False
        lowered = text.lower()
        return any(t.lower() in lowered for t in self.triggers)

    def supports_app(self, app: str) -> bool:
        """判断技能是否适配某客户端；空 ``requires_apps`` 视为通用。"""
        if not self.requires_apps:
            return True
        return app in self.requires_apps

    def to_dict(self) -> dict[str, object]:
        """序列化为可 JSON 编码的字典（管理 UI / 调试用）。"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "type": self.type,
            "triggers": list(self.triggers),
            "dependencies": list(self.dependencies),
            "requires_apps": list(self.requires_apps),
            "file_path": str(self.file_path) if self.file_path else None,
            "body_length": len(self.body),
        }
