# -*- coding: utf-8 -*-
"""示例：给 PDF 加文字水印 + AES-256 加密。

用法:
    python add_watermark.py input.pdf "机密 · 仅供内部审阅" output.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from skills.office.pdf.helpers.watermark import (  # noqa: E402
    add_text_watermark,
    encrypt,
)


def main(in_path: str, text: str, out_path: str, password: str = "Anxin@2026") -> None:
    tmp = Path(out_path).with_suffix(".wm.pdf")
    add_text_watermark(in_path, text, tmp, opacity=0.25, angle=30, font_size=42)
    encrypt(tmp, password, out_path)
    tmp.unlink(missing_ok=True)
    print(f"已加水印并加密 → {out_path} (密码: {password})")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print('用法: python add_watermark.py <in.pdf> "<水印文字>" <out.pdf>')
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
