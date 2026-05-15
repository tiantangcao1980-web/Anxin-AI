"""法律文档"章 / 条 / 款 / 项"层级保留。

中文法律 / 合同文本通用层级（由粗到细）::

    第X编 → 第X章 → 第X节 → 第X条 → 第X款 → 第X项

实务里最常见的是 ``章 / 条 / 款 / 项``。本模块用纯正则识别，把扁平
文本转成层级 JSON 树（保留 segment 在树上的归属位置，便于 RAG 召回
时回溯到合同第几条第几款）。

输出契约（与 :class:`IngestResult.structure` 对齐）::

    {
      "type": "root",
      "children": [
        {"type": "chapter", "label": "第一章", "title": "总则", "children": [
          {"type": "article", "label": "第一条", "title": "...",  "children": [
            {"type": "clause", "label": "（一）", "text": "..."}
          ]}
        ]}
      ]
    }
"""

from __future__ import annotations

import re
from typing import Any

# 中文数字 + 阿拉伯数字（兼容"第十二条"、"第 1 条"等多种写法）
_CN_NUM = r"[一二三四五六七八九十百千零〇\d]+"

# 各级别正则。注意要把 ``re.MULTILINE`` 加在使用方。
_PATTERN_CHAPTER = re.compile(rf"^\s*第\s*({_CN_NUM})\s*章\s*([^\n]*)$")
_PATTERN_SECTION = re.compile(rf"^\s*第\s*({_CN_NUM})\s*节\s*([^\n]*)$")
_PATTERN_ARTICLE = re.compile(rf"^\s*第\s*({_CN_NUM})\s*条\s*[:：]?\s*([^\n]*)$")
# "款"通常用 "（一）/ （1）" 或 "1." 表示
_PATTERN_CLAUSE = re.compile(r"^\s*[（(]\s*([一二三四五六七八九十\d]+)\s*[)）]\s*(.*)$")
_PATTERN_ITEM = re.compile(r"^\s*([一二三四五六七八九十\d]+)\s*[.、]\s*(.+)$")


_LEVEL_ORDER: dict[str, int] = {
    "chapter": 1,
    "section": 2,
    "article": 3,
    "clause": 4,
    "item": 5,
}


class LayoutPreserver:
    """把扁平中文法律文本切成"章/条/款/项"层级树。

    用法::

        tree = LayoutPreserver().extract(full_text)
        # tree['children'] 即顶层（一般是若干 chapter）
    """

    def extract(self, text: str) -> dict[str, Any]:
        """主入口。返回根节点（``type=root``）。"""
        if not text:
            return {"type": "root", "children": []}

        root: dict[str, Any] = {"type": "root", "children": []}
        # 当前栈：保存 ``(level, node)``，顶部是最深节点
        stack: list[tuple[int, dict[str, Any]]] = [(0, root)]

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            node = self._match_line(line)
            if node is None:
                # 普通正文 → 追加到当前最深节点的 ``text``
                _, current = stack[-1]
                current.setdefault("text_lines", []).append(line)
                continue

            level = _LEVEL_ORDER[node["type"]]
            # 弹出比当前 level 更深 / 同级的节点，挂到合适父节点
            while stack and stack[-1][0] >= level:
                stack.pop()
            if not stack:
                stack.append((0, root))
            parent = stack[-1][1]
            parent.setdefault("children", []).append(node)
            stack.append((level, node))

        # 把 ``text_lines`` 合并成 ``text``
        self._compact(root)
        return root

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    @staticmethod
    def _match_line(line: str) -> dict[str, Any] | None:
        """单行匹配。返回带类型的节点（无 children）。"""
        if m := _PATTERN_CHAPTER.match(line):
            return {
                "type": "chapter",
                "label": f"第{m.group(1)}章",
                "title": m.group(2).strip(),
                "children": [],
            }
        if m := _PATTERN_SECTION.match(line):
            return {
                "type": "section",
                "label": f"第{m.group(1)}节",
                "title": m.group(2).strip(),
                "children": [],
            }
        if m := _PATTERN_ARTICLE.match(line):
            return {
                "type": "article",
                "label": f"第{m.group(1)}条",
                "title": m.group(2).strip(),
                "children": [],
            }
        if m := _PATTERN_CLAUSE.match(line):
            return {
                "type": "clause",
                "label": f"（{m.group(1)}）",
                "text": m.group(2).strip(),
                "children": [],
            }
        if m := _PATTERN_ITEM.match(line):
            # item 仅在已有 article / clause 上下文里才认作 item，
            # 否则当作普通正文。但这里先按形态归类，调用层可裁剪。
            return {
                "type": "item",
                "label": f"{m.group(1)}.",
                "text": m.group(2).strip(),
                "children": [],
            }
        return None

    @staticmethod
    def _compact(node: dict[str, Any]) -> None:
        """递归把 ``text_lines`` 合并为 ``text``。"""
        lines = node.pop("text_lines", None)
        if lines:
            existing = node.get("text", "")
            node["text"] = (existing + "\n" if existing else "") + "\n".join(lines)
        for child in node.get("children", []):
            LayoutPreserver._compact(child)
