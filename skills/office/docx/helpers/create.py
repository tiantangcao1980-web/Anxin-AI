# -*- coding: utf-8 -*-
"""创建 .docx 文档.

核心入口 :func:`create_docx`，按 ``sections`` 列表声明式创建 Word 文档。

每个 section 是一个 dict，``type`` 字段决定具体写法：

============  =============================================
type          额外字段
============  =============================================
paragraph     text, bold?, italic?, align? (left|center|right|justify)
heading       text, level (1-9)
table         header (list[str]), rows (list[list[str]]),
              header_bold? (默认 True)
image         path, width_cm? (默认 12)
page_break    无
toc           depth? (默认 3)，插入 TOC 字段
header        text，文档级页眉
footer        text? 或 page_number? (bool)
============  =============================================

所有 helper 都安全处理空值；若 ``python-docx`` 未安装，导入时即抛
``ImportError``，由调用方/SkillExecutor 转译为友好提示。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from docx.shared import Cm, Pt
except ImportError as exc:  # pragma: no cover - 显式提示
    raise ImportError(
        "python-docx 未安装。请在 backend 环境执行: pip install 'python-docx>=1.1'"
    ) from exc


# ---------------------------------------------------------------------------
# 中文字体支持
# ---------------------------------------------------------------------------

_DEFAULT_BODY_FONT = "SimSun"   # 宋体
_DEFAULT_HEAD_FONT = "SimHei"   # 黑体


def _apply_chinese_font(run, font_name: str) -> None:
    """让 run 在中文字符上使用指定字体（python-docx 默认只设西文字体）。"""
    run.font.name = font_name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:eastAsia", "w:ascii", "w:hAnsi", "w:cs"):
        rFonts.set(qn(attr), font_name)


# ---------------------------------------------------------------------------
# 段落 / 标题
# ---------------------------------------------------------------------------

_ALIGN_MAP = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}


def _add_paragraph(doc, section: Mapping[str, Any]) -> None:
    p = doc.add_paragraph()
    align = section.get("align")
    if align in _ALIGN_MAP:
        p.alignment = _ALIGN_MAP[align]
    text = str(section.get("text", ""))
    run = p.add_run(text)
    if section.get("bold"):
        run.bold = True
    if section.get("italic"):
        run.italic = True
    font = section.get("font", _DEFAULT_BODY_FONT)
    _apply_chinese_font(run, font)
    if "size_pt" in section:
        run.font.size = Pt(int(section["size_pt"]))


def _add_heading(doc, section: Mapping[str, Any]) -> None:
    level = int(section.get("level", 1))
    level = max(1, min(level, 9))
    text = str(section.get("text", ""))
    h = doc.add_heading(level=level)
    run = h.add_run(text)
    _apply_chinese_font(run, section.get("font", _DEFAULT_HEAD_FONT))


# ---------------------------------------------------------------------------
# 表格
# ---------------------------------------------------------------------------

def _add_table(doc, section: Mapping[str, Any]) -> None:
    header: list[str] = list(section.get("header") or [])
    rows: list[list[str]] = list(section.get("rows") or [])
    header_bold = bool(section.get("header_bold", True))

    n_cols = len(header) if header else (len(rows[0]) if rows else 1)
    n_rows = (1 if header else 0) + len(rows)
    if n_rows == 0:
        return
    table = doc.add_table(rows=n_rows, cols=n_cols)
    table.style = section.get("style", "Table Grid")

    row_offset = 0
    if header:
        for j, cell_text in enumerate(header):
            cell = table.rows[0].cells[j]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(cell_text))
            run.bold = header_bold
            _apply_chinese_font(run, _DEFAULT_HEAD_FONT)
        row_offset = 1

    for i, row in enumerate(rows):
        for j, cell_text in enumerate(row[:n_cols]):
            cell = table.rows[i + row_offset].cells[j]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(cell_text))
            _apply_chinese_font(run, _DEFAULT_BODY_FONT)


# ---------------------------------------------------------------------------
# 图片 / 分页
# ---------------------------------------------------------------------------

def _add_image(doc, section: Mapping[str, Any]) -> None:
    path = section.get("path")
    if not path:
        return
    img_path = Path(path)
    if not img_path.exists():
        raise FileNotFoundError(f"图片不存在: {img_path}")
    width_cm = float(section.get("width_cm", 12))
    doc.add_picture(str(img_path), width=Cm(width_cm))


def _add_page_break(doc, _section: Mapping[str, Any]) -> None:
    doc.add_page_break()


# ---------------------------------------------------------------------------
# 目录字段（TOC field）
# ---------------------------------------------------------------------------

def _add_toc_field(doc, section: Mapping[str, Any]) -> None:
    depth = int(section.get("depth", 3))
    p = doc.add_paragraph()
    run = p.add_run()

    fld_char_begin = OxmlElement("w:fldChar")
    fld_char_begin.set(qn("w:fldCharType"), "begin")

    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = f'TOC \\o "1-{depth}" \\h \\z \\u'

    fld_char_separate = OxmlElement("w:fldChar")
    fld_char_separate.set(qn("w:fldCharType"), "separate")

    placeholder = OxmlElement("w:t")
    placeholder.text = "（请在 Word 中按 F9 更新目录）"

    fld_char_end = OxmlElement("w:fldChar")
    fld_char_end.set(qn("w:fldCharType"), "end")

    run._element.append(fld_char_begin)
    run._element.append(instr_text)
    run._element.append(fld_char_separate)
    run._element.append(placeholder)
    run._element.append(fld_char_end)


# ---------------------------------------------------------------------------
# 页眉 / 页脚 / 页码
# ---------------------------------------------------------------------------

def _set_header(doc, text: str) -> None:
    section = doc.sections[0]
    header = section.header
    p = header.paragraphs[0]
    p.text = ""
    run = p.add_run(text)
    _apply_chinese_font(run, _DEFAULT_HEAD_FONT)


def _set_footer(doc, *, text: str | None = None, page_number: bool = False) -> None:
    section = doc.sections[0]
    footer = section.footer
    p = footer.paragraphs[0]
    p.text = ""
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if text:
        run = p.add_run(text)
        _apply_chinese_font(run, _DEFAULT_BODY_FONT)
    if page_number:
        run = p.add_run()
        _apply_chinese_font(run, _DEFAULT_BODY_FONT)
        run.add_text("第 ")
        _add_simple_field(run, "PAGE")
        run.add_text(" 页 共 ")
        _add_simple_field(run, "NUMPAGES")
        run.add_text(" 页")


def _add_simple_field(run, instr: str) -> None:
    """在 run 中追加一个 Word 字段，如 PAGE / NUMPAGES。"""
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = instr
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._element.append(fld_begin)
    run._element.append(instr_text)
    run._element.append(fld_end)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

_DISPATCH = {
    "paragraph": _add_paragraph,
    "heading": _add_heading,
    "table": _add_table,
    "image": _add_image,
    "page_break": _add_page_break,
    "toc": _add_toc_field,
}


def create_docx(
    path: str | Path,
    sections: Iterable[Mapping[str, Any]],
    *,
    title: str | None = None,
    author: str | None = None,
) -> Path:
    """按 sections 创建 .docx 并返回输出路径.

    :param path: 输出文件路径（覆盖写入）
    :param sections: 见模块 docstring 的结构化声明
    :param title: 写入 core_properties.title
    :param author: 写入 core_properties.author
    :returns: 输出文件 Path
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()

    # 元数据
    if title:
        doc.core_properties.title = title
    if author:
        doc.core_properties.author = author

    # 设置默认正文字体（影响 Normal 样式）
    style = doc.styles["Normal"]
    style.font.name = _DEFAULT_BODY_FONT
    rpr = style.element.get_or_add_rPr()
    rFonts = rpr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rpr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), _DEFAULT_BODY_FONT)

    for section in sections:
        if not isinstance(section, Mapping):
            continue
        stype = section.get("type")
        if stype == "header":
            _set_header(doc, str(section.get("text", "")))
            continue
        if stype == "footer":
            _set_footer(
                doc,
                text=section.get("text"),
                page_number=bool(section.get("page_number", False)),
            )
            continue
        handler = _DISPATCH.get(stype)
        if handler is None:
            # 未知类型直接跳过，避免阻断长流水线
            continue
        handler(doc, section)

    doc.save(str(out))
    return out
