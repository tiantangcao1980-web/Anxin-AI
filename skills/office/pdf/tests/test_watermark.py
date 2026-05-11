# -*- coding: utf-8 -*-
"""watermark.py 测试：文字水印 + 加密/解密。"""

from __future__ import annotations

from pypdf import PdfReader

from skills.office.pdf.helpers.watermark import (
    add_text_watermark,
    decrypt,
    encrypt,
)


def test_add_text_watermark(sample_pdf, tmp_path):
    out = tmp_path / "wm.pdf"
    add_text_watermark(sample_pdf, "TEST WM", out, opacity=0.2)
    assert out.exists()
    reader = PdfReader(str(out))
    assert len(reader.pages) == 2


def test_encrypt_decrypt_roundtrip(sample_pdf, tmp_path):
    enc = tmp_path / "enc.pdf"
    dec = tmp_path / "dec.pdf"
    pwd = "Anxin@2026"
    encrypt(sample_pdf, pwd, enc)

    enc_reader = PdfReader(str(enc))
    assert enc_reader.is_encrypted

    decrypt(enc, pwd, dec)
    dec_reader = PdfReader(str(dec))
    assert not dec_reader.is_encrypted
    assert len(dec_reader.pages) == 2
