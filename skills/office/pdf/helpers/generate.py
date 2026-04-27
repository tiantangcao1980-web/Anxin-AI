# -*- coding: utf-8 -*-
"""PDF 生成（基于 reportlab）。

- markdown_to_pdf: Markdown → PDF（中文友好）
- html_to_pdf: 简单 HTML → PDF（基础标签）
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path


def _register_cjk_font(font_name: str = "SimSun"):
    """注册中文字体。优先使用系统 STSong-Light（reportlab 内置 CID）。

    若指定 font_name 找不到，会回退到 STSong-Light（CID 字体）。
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    try:
        pdfmetrics.registerFont(UnicodeCIDFont(font_name))
        return font_name
    except Exception:
        # 回退
        try:
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
            return "STSong-Light"
        except Exception:
            return "Helvetica"


def markdown_to_pdf(md_text: str, out_path, font: str = "STSong-Light") -> Path:
    """把 Markdown 渲染成 PDF。

    支持：标题(#~######)、段落、无序/有序列表、代码块、加粗*斜体（基本）。
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import (
        ListFlowable,
        ListItem,
        Paragraph,
        Preformatted,
        SimpleDocTemplate,
        Spacer,
    )

    actual_font = _register_cjk_font(font)
    styles = getSampleStyleSheet()

    base = ParagraphStyle(
        "CJKBody",
        parent=styles["BodyText"],
        fontName=actual_font,
        fontSize=11,
        leading=18,
    )
    h_styles = {
        i: ParagraphStyle(
            f"CJKH{i}",
            parent=styles[f"Heading{min(i, 4)}"],
            fontName=actual_font,
            fontSize=22 - i * 2,
            leading=28 - i * 2,
            spaceAfter=8,
        )
        for i in range(1, 7)
    }

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out), pagesize=A4, title="Generated PDF")

    story: list = []
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # 代码块
        if line.startswith("```"):
            j = i + 1
            buf: list[str] = []
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(lines[j])
                j += 1
            story.append(Preformatted("\n".join(buf), base))
            story.append(Spacer(1, 6))
            i = j + 1
            continue

        # 标题
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            story.append(Paragraph(m.group(2), h_styles[level]))
            i += 1
            continue

        # 列表
        if re.match(r"^\s*[-*]\s+", line):
            items: list = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(
                    ListItem(Paragraph(re.sub(r"^\s*[-*]\s+", "", lines[i]), base))
                )
                i += 1
            story.append(ListFlowable(items, bulletType="bullet"))
            story.append(Spacer(1, 4))
            continue
        if re.match(r"^\s*\d+\.\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(
                    ListItem(Paragraph(re.sub(r"^\s*\d+\.\s+", "", lines[i]), base))
                )
                i += 1
            story.append(ListFlowable(items, bulletType="1"))
            story.append(Spacer(1, 4))
            continue

        # 空行
        if not line.strip():
            story.append(Spacer(1, 6))
            i += 1
            continue

        # 段落 — 简单的 **加粗** 和 *斜体*
        text = line
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
        story.append(Paragraph(text, base))
        i += 1

    doc.build(story)
    return out


class _SimpleHTMLToFlowables(HTMLParser):
    def __init__(self, base_style, h_styles):
        super().__init__()
        self.story: list = []
        self.base = base_style
        self.h = h_styles
        self._buf: list[str] = []
        self._cur_tag: str | None = None
        self._list_items: list = []
        self._in_list: str | None = None

    def _flush(self):
        from reportlab.platypus import Paragraph

        if not self._buf:
            return
        text = "".join(self._buf).strip()
        self._buf = []
        if not text:
            return
        tag = self._cur_tag or "p"
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            self.story.append(Paragraph(text, self.h[level]))
        else:
            self.story.append(Paragraph(text, self.base))

    def handle_starttag(self, tag, attrs):
        from reportlab.platypus import ListItem, Paragraph

        if tag in {"ul", "ol"}:
            self._in_list = tag
            self._list_items = []
            return
        if tag == "li":
            self._buf = []
            self._cur_tag = "li"
            return
        if tag == "br":
            self._buf.append("<br/>")
            return
        if tag in {"b", "strong"}:
            self._buf.append("<b>")
            return
        if tag in {"i", "em"}:
            self._buf.append("<i>")
            return
        self._flush()
        self._cur_tag = tag

    def handle_endtag(self, tag):
        from reportlab.platypus import ListFlowable, ListItem, Paragraph

        if tag in {"ul", "ol"}:
            if self._list_items:
                bt = "bullet" if tag == "ul" else "1"
                self.story.append(ListFlowable(self._list_items, bulletType=bt))
            self._in_list = None
            self._list_items = []
            return
        if tag == "li":
            text = "".join(self._buf).strip()
            self._buf = []
            self._list_items.append(ListItem(Paragraph(text or " ", self.base)))
            return
        if tag in {"b", "strong"}:
            self._buf.append("</b>")
            return
        if tag in {"i", "em"}:
            self._buf.append("</i>")
            return
        self._flush()

    def handle_data(self, data):
        self._buf.append(data)


def html_to_pdf(html_text: str, out_path, font: str = "STSong-Light") -> Path:
    """简单 HTML → PDF（仅支持 h1-h6/p/br/ul/ol/li/b/i/strong/em）。"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate

    actual_font = _register_cjk_font(font)
    styles = getSampleStyleSheet()
    base = ParagraphStyle(
        "CJKBody",
        parent=styles["BodyText"],
        fontName=actual_font,
        fontSize=11,
        leading=18,
    )
    h_styles = {
        i: ParagraphStyle(
            f"CJKH{i}",
            parent=styles[f"Heading{min(i, 4)}"],
            fontName=actual_font,
            fontSize=22 - i * 2,
            leading=28 - i * 2,
            spaceAfter=8,
        )
        for i in range(1, 7)
    }

    parser = _SimpleHTMLToFlowables(base, h_styles)
    parser.feed(html_text)
    parser._flush()

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out), pagesize=A4, title="Generated PDF")
    doc.build(parser.story or [])
    return out
