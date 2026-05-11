# -*- coding: utf-8 -*-
"""LayoutPreserver 单测（P13-A 法律层级正则）。

覆盖：
- 空 / 纯空白
- 章 → 条 → 款 → 项 全栈
- 跨章节弹栈
- 阿拉伯数字 + 中文数字混用
- 普通正文挂到最深节点 ``text``
"""

from __future__ import annotations

import textwrap

import pytest

from src.services.rag.ingest.multimodal import LayoutPreserver


@pytest.fixture
def preserver() -> LayoutPreserver:
    return LayoutPreserver()


def test_empty_returns_empty_root(preserver: LayoutPreserver) -> None:
    tree = preserver.extract("")
    assert tree == {"type": "root", "children": []}


def test_whitespace_only_returns_empty(preserver: LayoutPreserver) -> None:
    tree = preserver.extract("   \n  \n\t\n")
    assert tree["type"] == "root"
    assert tree["children"] == []


def test_chapter_article_clause(preserver: LayoutPreserver) -> None:
    text = textwrap.dedent(
        """
        第一章 总则
        第一条 为规范双方权利义务订立本合同。
        （一）甲方信息
        （二）乙方信息
        第二条 合同期限自签订日起一年。
        """
    ).strip()
    tree = preserver.extract(text)
    chapters = tree["children"]
    assert len(chapters) == 1
    chap = chapters[0]
    assert chap["type"] == "chapter"
    assert chap["label"] == "第一章"
    assert chap["title"] == "总则"
    articles = chap["children"]
    assert len(articles) == 2
    assert articles[0]["label"] == "第一条"
    clauses = articles[0]["children"]
    assert len(clauses) == 2
    assert clauses[0]["label"] == "（一）"
    assert clauses[0]["text"] == "甲方信息"


def test_pop_back_to_higher_level(preserver: LayoutPreserver) -> None:
    text = textwrap.dedent(
        """
        第一章 总则
        第一条 X
        第二章 合作内容
        第二条 Y
        """
    ).strip()
    tree = preserver.extract(text)
    chapters = tree["children"]
    assert len(chapters) == 2
    assert chapters[0]["label"] == "第一章"
    assert chapters[1]["label"] == "第二章"
    # 第二条挂在第二章下，不挂第一条下
    assert chapters[1]["children"][0]["label"] == "第二条"


def test_arabic_numbers(preserver: LayoutPreserver) -> None:
    text = "第 1 章 概述\n第 2 条 范围\n（1）适用对象"
    tree = preserver.extract(text)
    chap = tree["children"][0]
    assert chap["label"] == "第1章"
    article = chap["children"][0]
    assert article["label"] == "第2条"
    clause = article["children"][0]
    assert clause["label"] == "（1）"


def test_section_between_chapter_and_article(preserver: LayoutPreserver) -> None:
    text = textwrap.dedent(
        """
        第一章 通则
        第一节 立法目的
        第一条 为规范市场秩序。
        """
    ).strip()
    tree = preserver.extract(text)
    chap = tree["children"][0]
    section = chap["children"][0]
    assert section["type"] == "section"
    assert section["label"] == "第一节"
    article = section["children"][0]
    assert article["label"] == "第一条"


def test_freeform_text_attaches_to_deepest(preserver: LayoutPreserver) -> None:
    text = textwrap.dedent(
        """
        第一条 内容
        以下是普通正文说明。
        继续说明。
        """
    ).strip()
    tree = preserver.extract(text)
    article = tree["children"][0]
    assert article["type"] == "article"
    assert "普通正文说明" in article["text"]
    assert "继续说明" in article["text"]


def test_unrelated_text_attaches_to_root(preserver: LayoutPreserver) -> None:
    tree = preserver.extract("仅一段说明文字。\n再来一句。")
    # 没有任何法律层级 → 都挂到 root.text
    assert "仅一段说明文字" in tree["text"]
