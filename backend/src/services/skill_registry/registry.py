# -*- coding: utf-8 -*-
"""
SkillRegistry —— 进程内运行时技能注册表（P5 真实装）

新增能力（相对 P1 骨架）：
    - ``load_directory(root, recursive=True) -> int``：批量加载目录下 SKILL.md
    - ``watch_directory(root, on_change)``：基于 watchdog 监听文件变更热更
    - ``find_by_trigger(text, top_k=5)``：按命中关键词数量打分排序
    - ``list_by_persona(persona)``：按 frontmatter ``personas`` 字段过滤
    - ``toggle(name, enabled)``：运行时启停（不删文件）
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.services.skill_registry.loader import SkillLoader, SkillParseError
from src.services.skill_registry.models import Skill

logger = logging.getLogger(__name__)


class SkillValidationError(ValueError):
    """E5 (2026-05-14): skill 注册时 required_tools 校验未通过 (strict 模式)。"""


class SkillRegistry:
    """单例运行时技能注册表。

    使用方式（推荐通过 ``SkillRegistry.instance()`` 拿全局实例）::

        registry = SkillRegistry.instance()
        registry.load_directory("skills/")
        candidates = registry.find_by_trigger(user_input, top_k=3)
    """

    _instance: "SkillRegistry | None" = None

    def __init__(self) -> None:
        self._by_name: dict[str, Skill] = {}
        self._loader = SkillLoader()
        # watchdog observer 是“懒启动”的，避免无 watch 需求时也起线程
        self._observer: Any | None = None
        self._watch_handlers: list[Callable[[str, Skill | None], None]] = []
        self._watch_lock = threading.RLock()

    # ------------------------------------------------------------------
    # 单例
    # ------------------------------------------------------------------
    @classmethod
    def instance(cls) -> "SkillRegistry":
        """返回全局单例（懒初始化）。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（仅用于测试）。"""
        if cls._instance is not None:
            cls._instance.stop_watching()
        cls._instance = None

    # ------------------------------------------------------------------
    # 注册 / 查询
    # ------------------------------------------------------------------
    def register(self, skill: Skill) -> None:
        """注册一条技能（同名覆盖）。

        E5 (2026-05-14): 运行时 gate — 如果 skill.required_tools 中有任何
        工具未在 harness.tool_registry 注册, 则:
          - HARNESS_SKILL_STRICT_TOOLS=true → 抛 SkillValidationError 拒绝加载
          - 默认 (false) → 记 WARNING, 自动 disable 该 skill (enabled=False)
        触发词召回 (find_by_trigger) 已经过滤 disabled, 因此自动 disable 效果是
        skill 文件保留 + 不会被 LLM 看到, 不会引起未注册工具的运行时错误.
        """
        if not skill.name:
            raise ValueError("Skill.name 不能为空")

        # E5: required_tools 运行时校验
        if skill.required_tools:
            missing = skill.validate_required_tools()
            if missing:
                import os
                strict = os.environ.get("HARNESS_SKILL_STRICT_TOOLS", "false").lower() in {"true", "1", "yes"}
                if strict:
                    raise SkillValidationError(
                        f"skill {skill.name}: required_tools 中 {missing} 未在 tool_registry 注册"
                    )
                logger.warning(
                    "skill_registry: %s 声明的工具 %s 未在 tool_registry 注册, 自动 disable",
                    skill.name, missing,
                )
                skill.enabled = False

        if skill.name in self._by_name:
            old = self._by_name[skill.name]
            if old.version != skill.version:
                logger.info(
                    "skill_registry: 覆盖 %s（%s → %s）",
                    skill.name, old.version, skill.version,
                )
        self._by_name[skill.name] = skill

    def unregister(self, name: str) -> bool:
        """按 name 注销技能；存在则返回 True。"""
        return self._by_name.pop(name, None) is not None

    def get(self, name: str) -> Skill | None:
        """按 name 精确查询。"""
        return self._by_name.get(name)

    def toggle(self, name: str, enabled: bool) -> Skill | None:
        """运行时启停某 skill；返回更新后的 ``Skill``，若不存在返回 ``None``。"""
        skill = self._by_name.get(name)
        if skill is None:
            return None
        skill.enabled = bool(enabled)
        return skill

    # ------------------------------------------------------------------
    # 召回
    # ------------------------------------------------------------------
    def find_by_trigger(self, text: str, top_k: int = 5) -> list[Skill]:
        """按 trigger 召回，按命中数排序，返回前 ``top_k`` 条。

        过滤掉 ``enabled=False`` 的 skill。
        """
        if not text:
            return []
        scored: list[tuple[int, Skill]] = []
        for s in self._by_name.values():
            if not s.enabled:
                continue
            score = s.trigger_score(text)
            if score > 0:
                scored.append((score, s))
        # 大分在前；相同分按 name 稳定排序
        scored.sort(key=lambda pair: (-pair[0], pair[1].name))
        return [s for _, s in scored[: max(0, top_k)]]

    def list_by_domain(self, domain: str) -> list[Skill]:
        """按 ``type`` / ``category`` 过滤（兼容旧字段）。"""
        return [
            s for s in self._by_name.values()
            if s.type == domain or s.category == domain
        ]

    def list_by_category(self, category: str) -> list[Skill]:
        """按 ``category`` 过滤。"""
        return [s for s in self._by_name.values() if s.category == category]

    def list_by_persona(self, persona: str) -> list[Skill]:
        """按 ``personas`` 过滤；空 personas 视为对所有 persona 可用。"""
        if not persona:
            return list(self._by_name.values())
        return [s for s in self._by_name.values() if s.supports_persona(persona)]

    def all(self) -> list[Skill]:
        """返回所有已注册 skill（拷贝列表）。"""
        return list(self._by_name.values())

    def __len__(self) -> int:
        return len(self._by_name)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._by_name

    # ------------------------------------------------------------------
    # 批量加载
    # ------------------------------------------------------------------
    def load_directory(self, root: str | Path, recursive: bool = True) -> int:
        """加载目录下所有 SKILL.md 并注册。

        参数：
            root: 根目录
            recursive: ``True`` 时递归子目录；``False`` 仅扫描顶层 ``SKILL.md``

        返回：
            实际注册（含覆盖）的 skill 数量
        """
        root_path = Path(root).resolve()
        if not root_path.is_dir():
            raise NotADirectoryError(f"非目录: {root_path}")

        if recursive:
            skills = self._loader.load_from_directory(root_path)
        else:
            skills = []
            # macOS / Windows 大小写不敏感时同一个 inode 可能命中两次（SKILL.md / skill.md）
            seen_ino: set[tuple[int, int]] = set()
            for name in self._loader.SKILL_FILE_NAMES:
                file_path = root_path / name
                if not file_path.is_file():
                    continue
                st = file_path.stat()
                key = (st.st_dev, st.st_ino)
                if key in seen_ino:
                    continue
                seen_ino.add(key)
                try:
                    skills.append(self._loader.load_from_file(file_path))
                except SkillParseError as exc:
                    logger.warning("加载失败 %s: %s", file_path, exc)

        count = 0
        for s in skills:
            try:
                self.register(s)
                count += 1
            except ValueError as exc:
                logger.warning("注册失败 %s: %s", s, exc)
        return count

    # ------------------------------------------------------------------
    # 热更新
    # ------------------------------------------------------------------
    def watch_directory(
        self,
        root: str | Path,
        on_change: Callable[[str, Skill | None], None] | None = None,
    ) -> Any:
        """监听目录下 SKILL.md 变更并热更注册表。

        参数：
            root: 监听根目录（递归）
            on_change: 回调 ``(event_type, skill)``
                event_type: ``"created"`` / ``"modified"`` / ``"deleted"``
                skill: 涉及的 ``Skill``（``deleted`` 时仅 name 有意义，其余字段可空）

        返回：
            底层 watchdog Observer。调用方可保留引用以备 ``stop_watching``；
            该 Observer 也会被注册表持有，进程退出 / ``stop_watching`` 时关闭。

        说明：
            - 首次调用会启动 daemon 线程；测试时务必显式 ``stop_watching``。
            - 单元测试可直接调 ``_handle_fs_event`` 模拟事件，无需真起线程。
        """
        from watchdog.events import FileSystemEventHandler  # 延迟导入
        from watchdog.observers import Observer

        if on_change is not None:
            self._watch_handlers.append(on_change)

        with self._watch_lock:
            if self._observer is not None:
                # 已有 observer，叠加路径即可
                root_path = Path(root).resolve()
                self._observer.schedule(self._build_handler(), str(root_path), recursive=True)
                return self._observer

            handler = self._build_handler()
            observer = Observer()
            observer.daemon = True
            observer.schedule(handler, str(Path(root).resolve()), recursive=True)
            observer.start()
            self._observer = observer
            return observer

    def _build_handler(self):
        """构造 watchdog 事件处理器（延迟导入 watchdog）。"""
        from watchdog.events import FileSystemEventHandler

        registry = self

        class _SkillFileHandler(FileSystemEventHandler):
            def on_created(self, event):  # type: ignore[override]
                if event.is_directory:
                    return
                registry._handle_fs_event("created", event.src_path)

            def on_modified(self, event):  # type: ignore[override]
                if event.is_directory:
                    return
                registry._handle_fs_event("modified", event.src_path)

            def on_deleted(self, event):  # type: ignore[override]
                if event.is_directory:
                    return
                registry._handle_fs_event("deleted", event.src_path)

            def on_moved(self, event):  # type: ignore[override]
                if event.is_directory:
                    return
                registry._handle_fs_event("deleted", event.src_path)
                registry._handle_fs_event("created", event.dest_path)

        return _SkillFileHandler()

    def _handle_fs_event(self, event_type: str, src_path: str) -> None:
        """统一处理文件系统事件 —— 测试也可直接调本方法跳过 watchdog。"""
        path = Path(src_path)
        if path.name not in self._loader.SKILL_FILE_NAMES:
            return

        skill: Skill | None = None
        if event_type in {"created", "modified"} and path.is_file():
            try:
                skill = self._loader.load_from_file(path)
                self.register(skill)
            except (SkillParseError, FileNotFoundError) as exc:
                logger.warning("热更解析失败 %s: %s", path, exc)
                return
        elif event_type == "deleted":
            # 反查哪个 skill 来自这个文件
            target_name: str | None = None
            for name, s in self._by_name.items():
                if s.file_path and s.file_path == path.resolve():
                    target_name = name
                    break
            if target_name:
                skill = self._by_name.pop(target_name)

        for cb in list(self._watch_handlers):
            try:
                cb(event_type, skill)
            except Exception:  # 回调失败不能影响其它回调或注册表
                logger.exception("watch_directory 回调异常")

    def stop_watching(self) -> None:
        """停止 watchdog 观察者并清空回调（测试 / 进程退出用）。"""
        with self._watch_lock:
            obs = self._observer
            self._observer = None
        if obs is not None:
            try:
                obs.stop()
                obs.join(timeout=1.0)
            except Exception:
                logger.exception("stop_watching 异常")
        self._watch_handlers.clear()
