# -*- coding: utf-8 -*-
"""
OAuth providers 子包

每个具体 provider 实现放一个独立模块文件，文件名后缀 ``_oauth.py``
（如 ``feishu_oauth.py`` / ``dingtalk_oauth.py`` / ``notion_oauth.py``）。

模块顶层 import 时使用 ``@register_provider`` 装饰器自动注册到全局
``OAuthProviderRegistry``。

P4-A 仅提供框架；P4-B/C/D/E 各自添加具体 provider 文件。
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path


def _autoload_providers() -> None:
    """自动扫描本包下所有 ``*_oauth.py`` 模块并 import 它们。

    被 ``OAuthProviderRegistry.default()`` 在首次实例化时调用。
    """
    package_dir = Path(__file__).parent
    for finder, mod_name, is_pkg in pkgutil.iter_modules([str(package_dir)]):
        # 只加载 *_oauth.py，跳过私有模块 / 子包
        if is_pkg or not mod_name.endswith("_oauth") or mod_name.startswith("_"):
            continue
        importlib.import_module(f"{__name__}.{mod_name}")


__all__ = ["_autoload_providers"]
