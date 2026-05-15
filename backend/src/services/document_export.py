"""
合同文档导出服务 - 支持 PDF 和 DOCX 格式
专业法律文书排版标准
"""

import os
import re
from collections.abc import Iterator
from datetime import datetime
from io import BytesIO
from typing import Any, TypeAlias, cast

from loguru import logger

from src.core.ai_labeling import AIContentType, AILabelingService

MarkdownSection: TypeAlias = dict[str, str]
RiskItems: TypeAlias = list[dict[str, Any]]


class ExportSizeLimitError(ValueError):
    """导出源内容或生成文件超过大小限制。"""


class ContractExportService:
    """合同文档导出服务 - 专业法律文书排版"""

    DEFAULT_MAX_EXPORT_BYTES = 50 * 1024 * 1024
    ABSOLUTE_MAX_EXPORT_BYTES = 200 * 1024 * 1024
    STREAM_CHUNK_SIZE = 64 * 1024

    # 中文字体路径候选列表
    _FONT_PATHS = [
        "/System/Library/Fonts/PingFang.ttc",  # macOS
        "/System/Library/Fonts/STHeiti Medium.ttc",  # macOS 备选
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Linux
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Linux 备选
        "C:\\Windows\\Fonts\\msyh.ttc",  # Windows
        "C:\\Windows\\Fonts\\simsun.ttc",  # Windows 备选
    ]

    @staticmethod
    def _get_max_export_bytes() -> int:
        try:
            configured = int(os.getenv("CONTRACT_EXPORT_MAX_BYTES", ""))
        except ValueError:
            configured = ContractExportService.DEFAULT_MAX_EXPORT_BYTES

        if configured <= 0:
            configured = ContractExportService.DEFAULT_MAX_EXPORT_BYTES
        return min(configured, ContractExportService.ABSOLUTE_MAX_EXPORT_BYTES)

    @staticmethod
    def _ensure_export_size(label: str, value: str | bytes | BytesIO) -> None:
        if isinstance(value, BytesIO):
            current_position = value.tell()
            value.seek(0, os.SEEK_END)
            size = value.tell()
            value.seek(current_position)
        elif isinstance(value, bytes):
            size = len(value)
        else:
            size = len(value.encode("utf-8"))

        max_size = ContractExportService._get_max_export_bytes()
        if size > max_size:
            raise ExportSizeLimitError(f"{label}超过导出大小限制（最大 {max_size} 字节）")

    @staticmethod
    def iter_bytes(output: BytesIO, chunk_size: int | None = None) -> Iterator[bytes]:
        output.seek(0)
        chunk_size = chunk_size or ContractExportService.STREAM_CHUNK_SIZE
        while chunk := output.read(chunk_size):
            yield chunk

    @staticmethod
    def _find_chinese_font() -> str | None:
        """查找可用的中文字体路径"""
        for font_path in ContractExportService._FONT_PATHS:
            if os.path.exists(font_path):
                return font_path
        return None

    @staticmethod
    def _parse_markdown_to_sections(text: str) -> list[MarkdownSection]:
        """
        解析 Markdown 格式的合同文本为结构化段落列表。
        返回 [{"type": "h1"|"h2"|"h3"|"p"|"blank"|"sign"|"hr", "text": str}, ...]
        """
        sections: list[MarkdownSection] = []
        lines = text.split("\n")

        for line in lines:
            stripped = line.strip()

            if not stripped:
                sections.append({"type": "blank", "text": ""})
                continue

            # 分隔线
            if re.match(r"^[-─═*]{3,}$", stripped):
                sections.append({"type": "hr", "text": ""})
                continue

            # Markdown 标题
            if stripped.startswith("### "):
                sections.append({"type": "h3", "text": stripped[4:].strip()})
            elif stripped.startswith("## "):
                sections.append({"type": "h2", "text": stripped[3:].strip()})
            elif stripped.startswith("# "):
                sections.append({"type": "h1", "text": stripped[2:].strip()})
            # 签署区域检测
            elif any(
                kw in stripped
                for kw in ["甲方（盖章）", "乙方（盖章）", "签字：", "日期：", "法定代表人"]
            ):
                sections.append({"type": "sign", "text": stripped})
            # 带编号的条款标题（如"第一条"、"第X条"）
            elif re.match(r"^第[一二三四五六七八九十百零\d]+条", stripped):
                sections.append({"type": "h2", "text": stripped})
            # 普通段落
            else:
                # 清理 Markdown 加粗标记
                clean = re.sub(r"\*\*(.*?)\*\*", r"\1", stripped)
                sections.append({"type": "p", "text": clean})

        return sections

    @staticmethod
    def _risk_level(risk: dict[str, Any]) -> str:
        raw_level = risk.get("risk_level", risk.get("level", "medium"))
        return raw_level if isinstance(raw_level, str) else str(raw_level)

    @staticmethod
    def export_docx(
        title: str,
        text: str,
        contract_number: str | None = None,
        risk_level: str | None = None,
        risk_score: float | None = None,
        review_summary: str | None = None,
        risks: RiskItems | None = None,
    ) -> BytesIO:
        """
        导出为专业法律文书 DOCX 格式

        排版标准：
        - A4纸张，页边距上下2.54cm，左右3.17cm
        - 合同标题：小二号（18pt）黑体，居中
        - 条款标题：小四号（12pt）黑体，加粗
        - 正文：小四号（12pt）宋体，1.5倍行距
        - 签署区：独立排版
        """
        ContractExportService._ensure_export_size("导出源内容", text)

        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Cm, Pt, RGBColor

        doc = Document()

        # ===== 页面设置 =====
        section = doc.sections[0]
        section.page_width = Cm(21.0)  # A4 宽
        section.page_height = Cm(29.7)  # A4 高
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(3.17)
        section.right_margin = Cm(3.17)

        # ===== 默认样式 =====
        style = doc.styles["Normal"]
        font = style.font
        font.name = "宋体"
        font.size = Pt(12)  # 小四号
        pf = style.paragraph_format
        pf.line_spacing = Pt(22)  # 1.5倍行距近似
        pf.space_before = Pt(0)
        pf.space_after = Pt(4)

        # ===== 解析 Markdown 内容 =====
        sections = ContractExportService._parse_markdown_to_sections(text)

        for sec in sections:
            if sec["type"] == "h1":
                # 合同标题：小二号（18pt），居中，加粗
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(24)
                p.paragraph_format.space_after = Pt(18)
                run = p.add_run(sec["text"])
                run.font.size = Pt(18)
                run.font.bold = True
                run.font.name = "黑体"

            elif sec["type"] == "h2":
                # 条款标题：四号（14pt），加粗，左对齐
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.space_before = Pt(12)
                p.paragraph_format.space_after = Pt(6)
                run = p.add_run(sec["text"])
                run.font.size = Pt(14)
                run.font.bold = True
                run.font.name = "黑体"

            elif sec["type"] == "h3":
                # 子标题：小四号（12pt），加粗
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(8)
                p.paragraph_format.space_after = Pt(4)
                run = p.add_run(sec["text"])
                run.font.size = Pt(12)
                run.font.bold = True
                run.font.name = "黑体"

            elif sec["type"] == "sign":
                # 签署区：不缩进，较大间距
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(6)
                run = p.add_run(sec["text"])
                run.font.size = Pt(12)
                run.font.name = "宋体"

            elif sec["type"] == "hr":
                # 分隔线
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(8)
                p.paragraph_format.space_after = Pt(8)
                run = p.add_run("─" * 40)
                run.font.size = Pt(10)
                run.font.color.rgb = RGBColor(180, 180, 180)

            elif sec["type"] == "blank":
                # 空行
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                run = p.add_run("")
                run.font.size = Pt(6)

            else:
                # 正文段落：首行缩进2字符
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY  # 两端对齐
                p.paragraph_format.first_line_indent = Pt(24)  # 首行缩进2字符
                p.paragraph_format.line_spacing = Pt(22)
                run = p.add_run(sec["text"])
                run.font.size = Pt(12)
                run.font.name = "宋体"

        # ===== 审查报告附录（如有） =====
        if risks:
            cast(Any, doc).add_page_break()

            # 审查报告标题
            heading_p = doc.add_paragraph()
            heading_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            heading_p.paragraph_format.space_after = Pt(12)
            heading_run = heading_p.add_run("合同审查报告 — 风险点详情")
            heading_run.font.size = Pt(16)
            heading_run.font.bold = True
            heading_run.font.name = "黑体"

            # 审查信息摘要
            if contract_number or risk_level or risk_score is not None:
                info_p = doc.add_paragraph()
                info_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                if contract_number:
                    run = info_p.add_run(f"合同编号：{contract_number}\n")
                    run.font.size = Pt(10)
                    run.font.bold = True
                run = info_p.add_run(f"审查日期：{datetime.now().strftime('%Y年%m月%d日')}\n")
                run.font.size = Pt(10)
                if risk_level:
                    risk_level_map = {
                        "low": "低风险",
                        "medium": "中风险",
                        "high": "高风险",
                        "critical": "严重风险",
                    }
                    run = info_p.add_run(
                        f"风险等级：{risk_level_map.get(risk_level, risk_level)}\n"
                    )
                    run.font.size = Pt(10)
                if risk_score is not None:
                    run = info_p.add_run(f"风险评分：{risk_score:.2f}\n")
                    run.font.size = Pt(10)

            if review_summary:
                sum_p = doc.add_paragraph()
                sum_p.paragraph_format.space_before = Pt(8)
                sr = sum_p.add_run("审查摘要：")
                sr.font.bold = True
                sr.font.size = Pt(11)
                sum_p.add_run(review_summary).font.size = Pt(11)

            # 分隔线
            sep_p = doc.add_paragraph()
            sep_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            sep_run = sep_p.add_run("─" * 40)
            sep_run.font.color.rgb = RGBColor(180, 180, 180)

            risk_level_colors = {
                "low": RGBColor(46, 125, 50),  # 绿色
                "medium": RGBColor(245, 124, 0),  # 橙色
                "high": RGBColor(211, 47, 47),  # 红色
                "critical": RGBColor(139, 0, 0),  # 深红色
            }

            risk_level_cn = {"low": "低", "medium": "中", "high": "高", "critical": "严重"}

            for i, risk in enumerate(risks, 1):
                level = ContractExportService._risk_level(risk)
                color = risk_level_colors.get(level, RGBColor(0, 0, 0))

                # 风险标题
                risk_p = doc.add_paragraph()
                risk_p.paragraph_format.space_before = Pt(10)
                risk_p.paragraph_format.space_after = Pt(4)
                title_run = risk_p.add_run(f"风险 {i}：{risk.get('title', '未知风险')}")
                title_run.font.size = Pt(12)
                title_run.font.bold = True
                title_run.font.color.rgb = color

                # 风险详情
                detail_p = doc.add_paragraph()
                detail_p.paragraph_format.left_indent = Pt(24)

                for label, key in [
                    ("类型", "risk_type"),
                    ("类型", "type"),
                    ("等级", None),
                    ("描述", "description"),
                    ("法律依据", "legal_basis"),
                    ("修改建议", "suggestion"),
                ]:
                    val = None
                    if key:
                        val = risk.get(key)
                    elif label == "等级":
                        val = risk_level_cn.get(level, level)

                    if val:
                        label_run = detail_p.add_run(f"{label}：")
                        label_run.font.bold = True
                        label_run.font.size = Pt(10)
                        val_run = detail_p.add_run(f"{val}\n")
                        val_run.font.size = Pt(10)

                status = "已解决" if risk.get("is_resolved") else "待处理"
                s_run = detail_p.add_run("状态：")
                s_run.font.bold = True
                s_run.font.size = Pt(10)
                detail_p.add_run(f"{status}\n").font.size = Pt(10)

        # ===== AI内容标识（GB 45438-2025合规） =====
        footer_text = AILabelingService.get_document_footer(AIContentType.DOCUMENT)
        footer_lines = footer_text.split("\n")
        doc.add_paragraph("")  # 空行
        for line in footer_lines:
            fp = doc.add_paragraph()
            fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            fr = fp.add_run(line)
            fr.font.size = Pt(8)
            fr.font.color.rgb = RGBColor(150, 150, 150)
            fr.font.name = "宋体"

        # 设置文件属性元数据
        meta = AILabelingService.get_export_metadata(AIContentType.DOCUMENT)
        doc.core_properties.author = meta.get("creator", "")
        doc.core_properties.comments = meta.get("comments", "")
        doc.core_properties.keywords = meta.get("keywords", "")
        doc.core_properties.category = meta.get("category", "")

        # ===== 保存 =====
        output = BytesIO()
        doc.save(output)
        ContractExportService._ensure_export_size("导出文件", output)
        output.seek(0)
        return output

    @staticmethod
    def export_pdf(
        title: str,
        text: str,
        contract_number: str | None = None,
        risk_level: str | None = None,
        risk_score: float | None = None,
        review_summary: str | None = None,
        risks: RiskItems | None = None,
    ) -> BytesIO:
        """
        导出为 PDF 格式

        优先使用 reportlab，备选 fpdf2。
        """
        ContractExportService._ensure_export_size("导出源内容", text)

        try:
            return ContractExportService._export_pdf_reportlab(
                title, text, contract_number, risk_level, risk_score, review_summary, risks
            )
        except ImportError:
            logger.warning("reportlab 不可用，使用 fpdf2 作为备选方案")
            return ContractExportService._export_pdf_fpdf2(
                title, text, contract_number, risk_level, risk_score, review_summary, risks
            )

    @staticmethod
    def _export_pdf_reportlab(
        title: str,
        text: str,
        contract_number: str | None = None,
        risk_level: str | None = None,
        risk_score: float | None = None,
        review_summary: str | None = None,
        risks: RiskItems | None = None,
    ) -> BytesIO:
        """使用 reportlab 导出专业法律文书 PDF"""
        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm, mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

        # 注册中文字体
        font_path = ContractExportService._find_chinese_font()
        font_name = "ChineseFont"

        if font_path:
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
            except Exception as e:
                logger.warning(f"注册中文字体失败: {e}，使用默认字体")
                font_name = "Helvetica"
        else:
            logger.warning("未找到中文字体文件，使用默认字体")
            font_name = "Helvetica"

        output = BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=3.17 * cm,
            leftMargin=3.17 * cm,
            topMargin=2.54 * cm,
            bottomMargin=2.54 * cm,
        )

        # 定义专业法律文书样式
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "LegalTitle",
            parent=styles["Title"],
            fontName=font_name,
            fontSize=18,
            leading=28,
            spaceAfter=18,
            spaceBefore=24,
            alignment=1,  # 居中
        )

        h2_style = ParagraphStyle(
            "LegalH2",
            parent=styles["Heading2"],
            fontName=font_name,
            fontSize=14,
            leading=22,
            spaceBefore=12,
            spaceAfter=6,
        )

        h3_style = ParagraphStyle(
            "LegalH3",
            parent=styles["Heading3"],
            fontName=font_name,
            fontSize=12,
            leading=20,
            spaceBefore=8,
            spaceAfter=4,
        )

        body_style = ParagraphStyle(
            "LegalBody",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=12,
            leading=22,  # 1.5倍行距
            spaceAfter=4,
            firstLineIndent=24,  # 首行缩进
            alignment=4,  # 两端对齐
        )

        sign_style = ParagraphStyle(
            "LegalSign",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=12,
            leading=20,
            spaceAfter=6,
            spaceBefore=6,
        )

        info_style = ParagraphStyle(
            "LegalInfo",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=10,
            textColor=HexColor("#555555"),
            spaceAfter=2,
        )

        elements = []

        # 解析文本
        sections = ContractExportService._parse_markdown_to_sections(text)

        for sec in sections:
            escaped = (
                (sec["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
                if sec["text"]
                else ""
            )

            if sec["type"] == "h1":
                elements.append(Paragraph(escaped, title_style))
            elif sec["type"] == "h2":
                elements.append(Paragraph(escaped, h2_style))
            elif sec["type"] == "h3":
                elements.append(Paragraph(escaped, h3_style))
            elif sec["type"] == "sign":
                elements.append(Paragraph(escaped, sign_style))
            elif sec["type"] == "hr":
                elements.append(Spacer(1, 6 * mm))
            elif sec["type"] == "blank":
                elements.append(Spacer(1, 3 * mm))
            else:
                if escaped:
                    elements.append(Paragraph(escaped, body_style))

        # 审查报告附录
        if risks:
            elements.append(PageBreak())

            report_title_style = ParagraphStyle(
                "ReportTitle",
                parent=title_style,
                fontSize=16,
                spaceAfter=12,
            )
            elements.append(Paragraph("合同审查报告 — 风险点详情", report_title_style))

            if contract_number:
                elements.append(Paragraph(f"合同编号：{contract_number}", info_style))
            elements.append(
                Paragraph(f"审查日期：{datetime.now().strftime('%Y年%m月%d日')}", info_style)
            )
            if risk_level:
                risk_level_map = {
                    "low": "低风险",
                    "medium": "中风险",
                    "high": "高风险",
                    "critical": "严重风险",
                }
                elements.append(
                    Paragraph(f"风险等级：{risk_level_map.get(risk_level, risk_level)}", info_style)
                )
            if risk_score is not None:
                elements.append(Paragraph(f"风险评分：{risk_score:.2f}", info_style))
            elements.append(Spacer(1, 6 * mm))

            if review_summary:
                elements.append(Paragraph("审查摘要", h2_style))
                elements.append(
                    Paragraph(
                        review_summary.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;"),
                        body_style,
                    )
                )
                elements.append(Spacer(1, 4 * mm))

            risk_level_cn = {"low": "低", "medium": "中", "high": "高", "critical": "严重"}
            risk_colors = {
                "low": "#2E7D32",
                "medium": "#F57C00",
                "high": "#D32F2F",
                "critical": "#8B0000",
            }

            for i, risk in enumerate(risks, 1):
                level = ContractExportService._risk_level(risk)
                color = risk_colors.get(level, "#000000")

                risk_title_style = ParagraphStyle(
                    f"RiskTitle_{i}",
                    parent=body_style,
                    fontSize=12,
                    textColor=HexColor(color),
                    spaceBefore=10,
                    spaceAfter=4,
                    firstLineIndent=0,
                )
                elements.append(
                    Paragraph(f"风险 {i}：{risk.get('title', '未知风险')}", risk_title_style)
                )

                detail_style = ParagraphStyle(
                    f"RiskDetail_{i}",
                    parent=body_style,
                    fontSize=10,
                    leading=18,
                    leftIndent=24,
                    firstLineIndent=0,
                )

                for label, key in [
                    ("类型", "risk_type"),
                    ("类型", "type"),
                    ("等级", None),
                    ("描述", "description"),
                    ("法律依据", "legal_basis"),
                    ("建议", "suggestion"),
                ]:
                    val = None
                    if key:
                        val = risk.get(key)
                    elif label == "等级":
                        val = risk_level_cn.get(level, level)
                    if val:
                        safe_val = (
                            str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        )
                        elements.append(Paragraph(f"<b>{label}：</b>{safe_val}", detail_style))

                status = "已解决" if risk.get("is_resolved") else "待处理"
                elements.append(Paragraph(f"<b>状态：</b>{status}", detail_style))
                elements.append(Spacer(1, 4 * mm))

        doc.build(elements)
        ContractExportService._ensure_export_size("导出文件", output)
        output.seek(0)
        return output

    @staticmethod
    def _export_pdf_fpdf2(
        title: str,
        text: str,
        contract_number: str | None = None,
        risk_level: str | None = None,
        risk_score: float | None = None,
        review_summary: str | None = None,
        risks: RiskItems | None = None,
    ) -> BytesIO:
        """使用 fpdf2 作为备选导出 PDF"""
        from fpdf import FPDF
        from fpdf.enums import XPos, YPos

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=25.4)
        pdf.set_margins(31.7, 25.4, 31.7)
        pdf.add_page()

        # 注册中文字体
        font_path = ContractExportService._find_chinese_font()
        if font_path:
            try:
                pdf.add_font("Chinese", "", font_path)
                pdf.set_font("Chinese", size=12)
            except Exception as e:
                logger.warning(f"fpdf2 注册中文字体失败: {e}")
                pdf.set_font("Helvetica", size=12)
        else:
            pdf.set_font("Helvetica", size=12)

        # 解析并渲染
        sections = ContractExportService._parse_markdown_to_sections(text)

        for sec in sections:
            if sec["type"] == "h1":
                pdf.set_font_size(18)
                pdf.cell(0, 14, sec["text"], new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
                pdf.ln(8)
            elif sec["type"] == "h2":
                pdf.set_font_size(14)
                pdf.ln(4)
                pdf.cell(0, 10, sec["text"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(2)
                pdf.set_font_size(12)
            elif sec["type"] == "h3":
                pdf.set_font_size(12)
                pdf.ln(3)
                pdf.cell(0, 8, sec["text"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(1)
            elif sec["type"] == "sign":
                pdf.set_font_size(12)
                pdf.cell(0, 8, sec["text"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            elif sec["type"] == "hr":
                pdf.ln(4)
            elif sec["type"] == "blank":
                pdf.ln(3)
            elif sec["text"]:
                pdf.set_font_size(12)
                pdf.multi_cell(0, 7, sec["text"])

        # 审查报告
        if risks:
            pdf.add_page()
            pdf.set_font_size(16)
            pdf.cell(
                0, 12, "合同审查报告 — 风险点详情", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C"
            )
            pdf.ln(6)

            pdf.set_font_size(10)
            if contract_number:
                pdf.cell(0, 6, f"合同编号：{contract_number}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.cell(
                0,
                6,
                f"审查日期：{datetime.now().strftime('%Y年%m月%d日')}",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            if risk_level:
                risk_level_map = {
                    "low": "低风险",
                    "medium": "中风险",
                    "high": "高风险",
                    "critical": "严重风险",
                }
                pdf.cell(
                    0,
                    6,
                    f"风险等级：{risk_level_map.get(risk_level, risk_level)}",
                    new_x=XPos.LMARGIN,
                    new_y=YPos.NEXT,
                )
            if risk_score is not None:
                pdf.cell(0, 6, f"风险评分：{risk_score:.2f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(5)

            risk_level_cn = {"low": "低", "medium": "中", "high": "高", "critical": "严重"}

            for i, risk in enumerate(risks, 1):
                level = ContractExportService._risk_level(risk)
                pdf.set_font_size(12)
                pdf.cell(
                    0,
                    8,
                    f"风险 {i}：{risk.get('title', '未知风险')}",
                    new_x=XPos.LMARGIN,
                    new_y=YPos.NEXT,
                )
                pdf.set_font_size(10)
                if risk.get("type") or risk.get("risk_type"):
                    pdf.cell(
                        0,
                        6,
                        f"  类型：{risk.get('risk_type') or risk.get('type', '未知')}",
                        new_x=XPos.LMARGIN,
                        new_y=YPos.NEXT,
                    )
                pdf.cell(
                    0,
                    6,
                    f"  等级：{risk_level_cn.get(level, level)}",
                    new_x=XPos.LMARGIN,
                    new_y=YPos.NEXT,
                )
                if risk.get("description"):
                    pdf.multi_cell(0, 6, f"  描述：{risk.get('description', '')}")
                if risk.get("legal_basis"):
                    pdf.multi_cell(0, 6, f"  法律依据：{risk.get('legal_basis')}")
                if risk.get("suggestion"):
                    pdf.multi_cell(0, 6, f"  建议：{risk.get('suggestion')}")
                status = "已解决" if risk.get("is_resolved") else "待处理"
                pdf.cell(0, 6, f"  状态：{status}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(3)

        output = BytesIO()
        pdf.output(output)
        ContractExportService._ensure_export_size("导出文件", output)
        output.seek(0)
        return output
