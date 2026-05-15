"""公式识别（P13-A 占位）。

真实接入路径
============

- **mathpix-ocr**：图像 → LaTeX，付费 SaaS API。
- **nougat**（Meta）：本地模型，PDF → markdown + LaTeX，依赖 PyTorch。
- **MinerU 内置 formula 块**：MinerU 已切出 formula bbox + LaTeX 字符串，
  本模块只做"清洗 + 包 \\(...\\) / $$...$$"。

本阶段仅做接口契约 + 简单清洗。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FormulaResult:
    """公式识别结果。"""

    latex: str
    plain: str  # 退化的纯文本（fallback 给不支持 LaTeX 的 chunk）
    confidence: float


class FormulaRecognizer:
    """公式识别器（mock 占位）。"""

    @staticmethod
    def normalize_latex(raw: str) -> str:
        """简单清洗：合并多余空白，去除前后 ``$`` / ``\\(`` / ``\\)``。"""
        text = raw.strip()
        for prefix in ("\\(", "\\[", "$$", "$"):
            if text.startswith(prefix):
                text = text[len(prefix) :]
                break
        for suffix in ("\\)", "\\]", "$$", "$"):
            if text.endswith(suffix):
                text = text[: -len(suffix)]
                break
        return " ".join(text.split())

    def from_text(self, text: str) -> FormulaResult:
        """直接从已是 LaTeX 的文本构造 :class:`FormulaResult`。"""
        latex = self.normalize_latex(text)
        return FormulaResult(latex=latex, plain=latex, confidence=0.95 if latex else 0.0)

    async def from_image(self, _image_bytes: bytes) -> FormulaResult:
        """TODO(p13a-real): 接 mathpix / nougat。"""
        raise NotImplementedError("公式 OCR 待 P13-A.2")
