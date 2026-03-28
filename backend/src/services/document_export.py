# -*- coding: utf-8 -*-
"""
合同文档导出服务 - 支持 PDF 和 DOCX 格式
"""

import os
import platform
from io import BytesIO
from datetime import datetime
from typing import Optional

from loguru import logger


class ContractExportService:
    """合同文档导出服务"""

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
    def _find_chinese_font() -> Optional[str]:
        """查找可用的中文字体路径"""
        for font_path in ContractExportService._FONT_PATHS:
            if os.path.exists(font_path):
                return font_path
        return None

    @staticmethod
    def export_docx(
        title: str,
        text: str,
        contract_number: Optional[str] = None,
        risk_level: Optional[str] = None,
        risk_score: Optional[float] = None,
        review_summary: Optional[str] = None,
        risks: list = None,
    ) -> BytesIO:
        """
        导出为 DOCX 格式

        Args:
            title: 合同标题
            text: 合同文本内容
            contract_number: 合同编号
            risk_level: 风险等级
            risk_score: 风险评分
            review_summary: 审查摘要
            risks: 风险点列表

        Returns:
            BytesIO 文件流
        """
        from docx import Document
        from docx.shared import Pt, Inches, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()

        # 设置默认字体
        style = doc.styles["Normal"]
        font = style.font
        font.name = "宋体"
        font.size = Pt(12)

        # 添加标题
        heading = doc.add_heading(title, level=1)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 添加审查信息
        info_paragraph = doc.add_paragraph()
        info_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        if contract_number:
            info_paragraph.add_run(f"合同编号：{contract_number}\n").bold = True
        info_paragraph.add_run(f"导出日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        if risk_level:
            risk_level_map = {
                "low": "低风险",
                "medium": "中风险",
                "high": "高风险",
                "critical": "严重风险",
            }
            info_paragraph.add_run(
                f"风险等级：{risk_level_map.get(risk_level, risk_level)}\n"
            )
        if risk_score is not None:
            info_paragraph.add_run(f"风险评分：{risk_score:.2f}\n")

        # 添加分隔线
        doc.add_paragraph("─" * 50)

        # 添加审查摘要
        if review_summary:
            doc.add_heading("审查摘要", level=2)
            doc.add_paragraph(review_summary)
            doc.add_paragraph("")

        # 添加合同正文
        doc.add_heading("合同内容", level=2)
        # 按段落添加合同文本
        paragraphs = text.split("\n")
        for para_text in paragraphs:
            stripped = para_text.strip()
            if stripped:
                doc.add_paragraph(stripped)
            else:
                doc.add_paragraph("")

        # 添加审查报告章节
        if risks:
            doc.add_page_break()
            doc.add_heading("审查报告 - 风险点详情", level=2)

            risk_level_colors = {
                "low": RGBColor(0, 128, 0),       # 绿色
                "medium": RGBColor(255, 165, 0),   # 橙色
                "high": RGBColor(255, 0, 0),       # 红色
                "critical": RGBColor(139, 0, 0),   # 深红色
            }

            for i, risk in enumerate(risks, 1):
                # 风险标题
                risk_heading = doc.add_heading(level=3)
                run = risk_heading.add_run(f"风险 {i}: {risk.get('title', '未知风险')}")
                level = risk.get("risk_level", "medium")
                color = risk_level_colors.get(level, RGBColor(0, 0, 0))
                run.font.color.rgb = color

                # 风险详情
                details = doc.add_paragraph()
                details.add_run("类型：").bold = True
                details.add_run(f"{risk.get('risk_type', '未知')}\n")
                details.add_run("等级：").bold = True
                risk_level_cn = {
                    "low": "低", "medium": "中", "high": "高", "critical": "严重"
                }
                details.add_run(f"{risk_level_cn.get(level, level)}\n")
                details.add_run("描述：").bold = True
                details.add_run(f"{risk.get('description', '')}\n")

                if risk.get("suggestion"):
                    details.add_run("建议：").bold = True
                    details.add_run(f"{risk.get('suggestion')}\n")

                status = "已解决" if risk.get("is_resolved") else "待处理"
                details.add_run("状态：").bold = True
                details.add_run(f"{status}\n")

                doc.add_paragraph("")  # 空行分隔

        # 保存到 BytesIO
        output = BytesIO()
        doc.save(output)
        output.seek(0)
        return output

    @staticmethod
    def export_pdf(
        title: str,
        text: str,
        contract_number: Optional[str] = None,
        risk_level: Optional[str] = None,
        risk_score: Optional[float] = None,
        review_summary: Optional[str] = None,
        risks: list = None,
    ) -> BytesIO:
        """
        导出为 PDF 格式

        优先使用 reportlab，备选 fpdf2。

        Args:
            title: 合同标题
            text: 合同文本内容
            contract_number: 合同编号
            risk_level: 风险等级
            risk_score: 风险评分
            review_summary: 审查摘要
            risks: 风险点列表

        Returns:
            BytesIO 文件流
        """
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
        contract_number: Optional[str] = None,
        risk_level: Optional[str] = None,
        risk_score: Optional[float] = None,
        review_summary: Optional[str] = None,
        risks: list = None,
    ) -> BytesIO:
        """使用 reportlab 导出 PDF"""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

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
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        # 定义样式
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ChineseTitle",
            parent=styles["Title"],
            fontName=font_name,
            fontSize=18,
            spaceAfter=12,
            alignment=1,  # 居中
        )
        heading_style = ParagraphStyle(
            "ChineseHeading",
            parent=styles["Heading2"],
            fontName=font_name,
            fontSize=14,
            spaceAfter=8,
            spaceBefore=12,
        )
        body_style = ParagraphStyle(
            "ChineseBody",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=10,
            leading=16,
            spaceAfter=4,
        )
        info_style = ParagraphStyle(
            "ChineseInfo",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=9,
            textColor=HexColor("#666666"),
            spaceAfter=2,
        )

        elements = []

        # 标题
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 6 * mm))

        # 审查信息
        if contract_number:
            elements.append(Paragraph(f"合同编号：{contract_number}", info_style))
        elements.append(
            Paragraph(f"导出日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}", info_style)
        )
        if risk_level:
            risk_level_map = {
                "low": "低风险", "medium": "中风险", "high": "高风险", "critical": "严重风险"
            }
            elements.append(
                Paragraph(f"风险等级：{risk_level_map.get(risk_level, risk_level)}", info_style)
            )
        if risk_score is not None:
            elements.append(Paragraph(f"风险评分：{risk_score:.2f}", info_style))

        elements.append(Spacer(1, 6 * mm))

        # 审查摘要
        if review_summary:
            elements.append(Paragraph("审查摘要", heading_style))
            elements.append(Paragraph(review_summary, body_style))
            elements.append(Spacer(1, 4 * mm))

        # 合同正文
        elements.append(Paragraph("合同内容", heading_style))
        paragraphs = text.split("\n")
        for para_text in paragraphs:
            stripped = para_text.strip()
            if stripped:
                # 转义 XML 特殊字符
                escaped = (
                    stripped.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                elements.append(Paragraph(escaped, body_style))
            else:
                elements.append(Spacer(1, 3 * mm))

        # 审查报告
        if risks:
            elements.append(PageBreak())
            elements.append(Paragraph("审查报告 - 风险点详情", heading_style))

            risk_level_cn = {"low": "低", "medium": "中", "high": "高", "critical": "严重"}
            risk_colors = {
                "low": "#008000", "medium": "#FFA500",
                "high": "#FF0000", "critical": "#8B0000",
            }

            for i, risk in enumerate(risks, 1):
                level = risk.get("risk_level", "medium")
                color = risk_colors.get(level, "#000000")

                risk_title_style = ParagraphStyle(
                    f"RiskTitle_{i}",
                    parent=body_style,
                    fontSize=12,
                    textColor=HexColor(color),
                    spaceBefore=8,
                    spaceAfter=4,
                )
                elements.append(
                    Paragraph(f"风险 {i}: {risk.get('title', '未知风险')}", risk_title_style)
                )
                elements.append(
                    Paragraph(f"类型：{risk.get('risk_type', '未知')}", body_style)
                )
                elements.append(
                    Paragraph(f"等级：{risk_level_cn.get(level, level)}", body_style)
                )
                elements.append(
                    Paragraph(f"描述：{risk.get('description', '')}", body_style)
                )
                if risk.get("suggestion"):
                    elements.append(
                        Paragraph(f"建议：{risk.get('suggestion')}", body_style)
                    )
                status = "已解决" if risk.get("is_resolved") else "待处理"
                elements.append(Paragraph(f"状态：{status}", body_style))
                elements.append(Spacer(1, 4 * mm))

        doc.build(elements)
        output.seek(0)
        return output

    @staticmethod
    def _export_pdf_fpdf2(
        title: str,
        text: str,
        contract_number: Optional[str] = None,
        risk_level: Optional[str] = None,
        risk_score: Optional[float] = None,
        review_summary: Optional[str] = None,
        risks: list = None,
    ) -> BytesIO:
        """使用 fpdf2 作为备选导出 PDF"""
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # 注册中文字体
        font_path = ContractExportService._find_chinese_font()
        if font_path:
            try:
                pdf.add_font("Chinese", "", font_path, uni=True)
                pdf.set_font("Chinese", size=12)
            except Exception as e:
                logger.warning(f"fpdf2 注册中文字体失败: {e}")
                pdf.set_font("Helvetica", size=12)
        else:
            pdf.set_font("Helvetica", size=12)

        # 标题
        pdf.set_font_size(18)
        pdf.cell(0, 15, title, ln=True, align="C")
        pdf.ln(5)

        # 审查信息
        pdf.set_font_size(9)
        if contract_number:
            pdf.cell(0, 6, f"合同编号：{contract_number}", ln=True)
        pdf.cell(0, 6, f"导出日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
        if risk_level:
            risk_level_map = {
                "low": "低风险", "medium": "中风险", "high": "高风险", "critical": "严重风险"
            }
            pdf.cell(0, 6, f"风险等级：{risk_level_map.get(risk_level, risk_level)}", ln=True)
        if risk_score is not None:
            pdf.cell(0, 6, f"风险评分：{risk_score:.2f}", ln=True)
        pdf.ln(5)

        # 审查摘要
        if review_summary:
            pdf.set_font_size(14)
            pdf.cell(0, 10, "审查摘要", ln=True)
            pdf.set_font_size(10)
            pdf.multi_cell(0, 6, review_summary)
            pdf.ln(3)

        # 合同正文
        pdf.set_font_size(14)
        pdf.cell(0, 10, "合同内容", ln=True)
        pdf.set_font_size(10)
        paragraphs = text.split("\n")
        for para_text in paragraphs:
            stripped = para_text.strip()
            if stripped:
                pdf.multi_cell(0, 6, stripped)
            else:
                pdf.ln(3)

        # 审查报告
        if risks:
            pdf.add_page()
            pdf.set_font_size(14)
            pdf.cell(0, 10, "审查报告 - 风险点详情", ln=True)
            pdf.ln(3)

            risk_level_cn = {"low": "低", "medium": "中", "high": "高", "critical": "严重"}

            for i, risk in enumerate(risks, 1):
                level = risk.get("risk_level", "medium")
                pdf.set_font_size(12)
                pdf.cell(0, 8, f"风险 {i}: {risk.get('title', '未知风险')}", ln=True)
                pdf.set_font_size(10)
                pdf.cell(0, 6, f"类型：{risk.get('risk_type', '未知')}", ln=True)
                pdf.cell(0, 6, f"等级：{risk_level_cn.get(level, level)}", ln=True)
                pdf.multi_cell(0, 6, f"描述：{risk.get('description', '')}")
                if risk.get("suggestion"):
                    pdf.multi_cell(0, 6, f"建议：{risk.get('suggestion')}")
                status = "已解决" if risk.get("is_resolved") else "待处理"
                pdf.cell(0, 6, f"状态：{status}", ln=True)
                pdf.ln(3)

        output = BytesIO()
        pdf.output(output)
        output.seek(0)
        return output
