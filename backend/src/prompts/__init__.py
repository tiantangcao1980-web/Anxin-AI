"""
Prompt 模板管理模块

支持：
1. 从 .txt 文件加载 prompt 模板
2. 变量插值（{variable_name} 格式）
3. 带 TTL 的内存缓存（开发时修改文件后自动刷新）
4. 兼容回退：文件不存在时使用内联默认值
"""

import os
from pathlib import Path
from typing import Any

from loguru import logger

# 模板文件根目录
_PROMPTS_DIR = Path(__file__).parent

# 缓存：{文件路径: (内容, 文件修改时间)}
_cache: dict[str, tuple[str, float]] = {}


def load_prompt(
    relative_path: str,
    fallback: str = "",
    **kwargs: Any,
) -> str:
    """
    加载 prompt 模板文件并进行变量插值。

    Args:
        relative_path: 相对于 prompts/ 目录的路径，如 "agents/legal_advisor.txt"
        fallback: 文件不存在时的回退内容
        **kwargs: 模板变量，用于替换 {variable_name}

    Returns:
        渲染后的 prompt 字符串
    """
    file_path = _PROMPTS_DIR / relative_path

    # 尝试从缓存加载（基于文件修改时间的自动刷新）
    content = _load_from_cache(str(file_path))
    if content is None:
        if file_path.exists():
            try:
                content = file_path.read_text(encoding="utf-8")
                mtime = file_path.stat().st_mtime
                _cache[str(file_path)] = (content, mtime)
            except Exception as e:
                logger.warning(f"读取 prompt 文件失败 {relative_path}: {e}")
                content = fallback
        else:
            if fallback:
                content = fallback
            else:
                logger.warning(f"Prompt 文件不存在: {relative_path}")
                return ""

    # 变量插值
    if kwargs:
        try:
            content = content.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Prompt 模板变量缺失 {relative_path}: {e}")

    return content


def _load_from_cache(file_path: str) -> str | None:
    """基于文件修改时间的缓存检查"""
    if file_path not in _cache:
        return None

    cached_content, cached_mtime = _cache[file_path]

    try:
        current_mtime = os.path.getmtime(file_path)
        if current_mtime > cached_mtime:
            # 文件已更新，清除缓存
            del _cache[file_path]
            return None
    except OSError:
        del _cache[file_path]
        return None

    return cached_content


def invalidate_cache(relative_path: str | None = None) -> None:
    """手动清除缓存（用于测试或管理页面触发刷新）"""
    if relative_path:
        file_path = str(_PROMPTS_DIR / relative_path)
        _cache.pop(file_path, None)
    else:
        _cache.clear()
