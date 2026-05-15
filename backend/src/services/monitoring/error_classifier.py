"""
错误聚类（P19-A）

按 (exception type, first user-frame, endpoint) 三元组生成稳定 hash，
便于：
1. Sentry 自定义 fingerprint（同类错误归入一个 issue，避免 issue 风暴）
2. 自建 dashboard 按 fingerprint 聚合 top-N 错误
3. 重复发生计数（结合 prometheus / kvstore）

设计要点：
- first user-frame 排除 site-packages / 标准库，专注业务代码
- endpoint 已 normalize（{id}/{uuid}），避免 cardinality 爆炸
- hash 使用 sha256[:16]，64-bit 足以保证生产期内无碰撞
- module-level _SEEN dict 记录 fingerprint→count 用于 SDK 内置去重（线程安全 dict）
"""

from __future__ import annotations

import hashlib
import os
import sys
import threading
import traceback
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ErrorFingerprint:
    fingerprint: str
    exception_type: str
    first_user_frame: str
    endpoint: str
    count: int = 1
    last_message: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "exception_type": self.exception_type,
            "first_user_frame": self.first_user_frame,
            "endpoint": self.endpoint,
            "count": self.count,
            "last_message": self.last_message,
            **self.extra,
        }


class ErrorClassifier:
    """模块级错误聚类器（线程安全）。

    用法：
        classifier = ErrorClassifier()
        fp = classifier.classify(exc, endpoint="/api/v1/auth/login")
        # fp.fingerprint -> "a3c1...8f2d" 稳定 hash
        # fp.count -> 同一 fingerprint 总次数
    """

    # 默认排除的库路径前缀（不视为 user frame）
    DEFAULT_EXCLUDE_PREFIXES: tuple[str, ...] = (
        "site-packages",
        "/usr/lib/python",
        "/Library/Frameworks/Python",
        "<frozen ",
        "asgiref/",
        "uvicorn/",
        "fastapi/",
        "starlette/",
        "anyio/",
        "asyncio/",
    )

    def __init__(self, exclude_prefixes: tuple[str, ...] | None = None):
        self.exclude_prefixes = exclude_prefixes or self.DEFAULT_EXCLUDE_PREFIXES
        self._seen: dict[str, ErrorFingerprint] = {}
        self._lock = threading.Lock()

    # ===== 公开 API =====
    def classify(
        self,
        exc: BaseException,
        endpoint: str = "unknown",
        message: str | None = None,
    ) -> ErrorFingerprint:
        exc_type = type(exc).__name__
        first_frame = self._extract_first_user_frame(exc)
        fingerprint = self._compute_fingerprint(exc_type, first_frame, endpoint)

        with self._lock:
            if fingerprint in self._seen:
                fp = self._seen[fingerprint]
                fp.count += 1
                if message:
                    fp.last_message = message
                else:
                    fp.last_message = str(exc)[:200]
                return fp
            fp = ErrorFingerprint(
                fingerprint=fingerprint,
                exception_type=exc_type,
                first_user_frame=first_frame,
                endpoint=endpoint,
                count=1,
                last_message=(message or str(exc))[:200],
            )
            self._seen[fingerprint] = fp
            return fp

    def top_n(self, n: int = 10) -> list[ErrorFingerprint]:
        with self._lock:
            return sorted(self._seen.values(), key=lambda f: f.count, reverse=True)[:n]

    def reset(self) -> None:
        """测试用：清空已观察的指纹。"""
        with self._lock:
            self._seen.clear()

    def total_unique(self) -> int:
        with self._lock:
            return len(self._seen)

    def total_events(self) -> int:
        with self._lock:
            return sum(f.count for f in self._seen.values())

    # ===== 内部工具 =====
    def _is_user_frame(self, filename: str) -> bool:
        """判断是否业务代码（非依赖库）。"""
        if not filename:
            return False
        norm = filename.replace("\\", "/")
        return not any(prefix in norm for prefix in self.exclude_prefixes)

    def _extract_first_user_frame(self, exc: BaseException) -> str:
        """提取首个业务栈帧 — 形如 'src/services/foo.py:42:do_thing'。

        若 exc 无 traceback（某些被 raise from 的链式异常），回退到 traceback module。
        """
        tb = exc.__traceback__
        if tb is None:
            # 同步上下文 fallback
            try:
                stack = traceback.extract_stack(sys._getframe(1))
            except Exception:
                stack = []
            for frame in reversed(stack):
                if self._is_user_frame(frame.filename):
                    return self._format_frame(frame.filename, frame.lineno or 0, frame.name or "?")
            return "<no-frame>"

        # 直接遍历 traceback chain
        frames: list[tuple[str, int, str]] = []
        cur = tb
        while cur is not None:
            f = cur.tb_frame
            frames.append((f.f_code.co_filename, cur.tb_lineno, f.f_code.co_name))
            cur = cur.tb_next

        # 优先取第一个业务 frame（若全是库代码，回退到最后一个 frame）
        for filename, lineno, name in frames:
            if self._is_user_frame(filename):
                return self._format_frame(filename, lineno, name)
        if frames:
            filename, lineno, name = frames[-1]
            return self._format_frame(filename, lineno, name)
        return "<no-frame>"

    def _format_frame(self, filename: str, lineno: int, name: str) -> str:
        # 仅保留 src/... 之后的路径，避免 cwd 差异影响 hash
        norm = filename.replace("\\", "/")
        if "/src/" in norm:
            norm = "src/" + norm.split("/src/", 1)[1]
        else:
            norm = os.path.basename(norm)
        return f"{norm}:{lineno}:{name}"

    def _compute_fingerprint(self, exc_type: str, frame: str, endpoint: str) -> str:
        raw = f"{exc_type}|{frame}|{endpoint}".encode()
        return hashlib.sha256(raw).hexdigest()[:16]


# ===== 模块级单例（业务代码 / Sentry before_send 共用） =====
_default_classifier = ErrorClassifier()


def classify_error(
    exc: BaseException,
    endpoint: str = "unknown",
    message: str | None = None,
) -> ErrorFingerprint:
    """便捷函数：使用默认 classifier。"""
    return _default_classifier.classify(exc, endpoint, message)


def top_errors(n: int = 10) -> list[dict[str, Any]]:
    return [f.to_dict() for f in _default_classifier.top_n(n)]


def reset_default_classifier() -> None:
    _default_classifier.reset()
