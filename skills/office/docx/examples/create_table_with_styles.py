# -*- coding: utf-8 -*-
"""示例 2：创建一份含目录、二级标题、表格、分页的项目周报。

演示中文字体、表格表头加粗、TOC 字段插入、页码注入等能力。

运行：
    python skills/office/docx/examples/create_table_with_styles.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from skills.office.docx.helpers.create import create_docx


def main(out_path: str = "/tmp/weekly.docx") -> Path:
    sections = [
        {"type": "header", "text": "安心智能助手 项目周报"},
        {"type": "footer", "page_number": True},
        {"type": "heading", "level": 1, "text": "项目周报（2026-W17）"},
        {"type": "paragraph", "text": "本文档由「安心智能助手」自动生成。"},
        {"type": "toc", "depth": 3},
        {"type": "page_break"},
        {"type": "heading", "level": 2, "text": "一、本周关键指标"},
        {
            "type": "table",
            "header": ["指标", "本周", "上周", "变化"],
            "rows": [
                ["新增对话", "1,284", "1,108", "+16%"],
                ["付费转化", "37", "31", "+19%"],
                ["平均响应延迟", "1.2s", "1.5s", "-20%"],
            ],
        },
        {"type": "heading", "level": 2, "text": "二、进展与里程碑"},
        {"type": "paragraph", "text": "P5-A SkillRegistry 已完成原型；P5-B docx skill 完成移植。"},
        {"type": "heading", "level": 2, "text": "三、下周计划"},
        {
            "type": "table",
            "header": ["计划", "负责人", "截止日"],
            "rows": [
                ["P5-C SkillExecutor 联调", "张三", "2026-04-30"],
                ["P5-D 前端 Skill 市场页", "李四", "2026-05-05"],
            ],
        },
    ]
    return create_docx(out_path, sections, title="项目周报", author="anxin_assistant")


if __name__ == "__main__":
    out = main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/weekly.docx")
    print(f"已生成: {out}")
