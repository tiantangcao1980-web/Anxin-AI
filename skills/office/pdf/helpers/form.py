# -*- coding: utf-8 -*-
"""PDF 表单读写（基于 pypdf）。

- read_form: 读取表单字段 → dict
- fill_form: 写入字段并扁平化（防止用户修改）
"""

from __future__ import annotations

from pathlib import Path


def _ensure(path) -> Path:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {p}")
    return p


def read_form(path) -> dict[str, str | None]:
    """读出 PDF 表单字段当前值。"""
    from pypdf import PdfReader

    reader = PdfReader(str(_ensure(path)))
    fields = reader.get_form_text_fields() or {}
    # 同时合并复选框等其它字段
    all_fields = reader.get_fields() or {}
    result: dict[str, str | None] = dict(fields)
    for name, info in all_fields.items():
        if name not in result:
            v = info.get("/V") if isinstance(info, dict) else getattr(info, "value", None)
            result[name] = str(v) if v is not None else None
    return result


def fill_form(path, data: dict, out_path) -> Path:
    """填写 PDF 表单。pypdf 4.x: PdfWriter.update_page_form_field_values。"""
    from pypdf import PdfReader, PdfWriter

    src = _ensure(path)
    reader = PdfReader(str(src))
    writer = PdfWriter(clone_from=reader)

    for page in writer.pages:
        try:
            writer.update_page_form_field_values(page, {k: str(v) for k, v in data.items()})
        except Exception:
            # 该页无字段则跳过
            continue

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        writer.write(f)
    writer.close()
    return out
