# -*- coding: utf-8 -*-
"""示例 1：创建一份最简 PPT（封面 + 三页内容 + 致谢）。"""

from __future__ import annotations

from pathlib import Path

from skills.office.pptx.helpers.create import create_pptx


def main() -> str:
    out = Path(__file__).parent / "output_simple_deck.pptx"
    return create_pptx(
        str(out),
        slides=[
            {"layout": "title_only", "title": "安心智能助手 — 产品介绍"},
            {
                "layout": "title_content",
                "title": "我们是谁",
                "content": [
                    "面向中小企业的法律 + 财务 AI 助手",
                    "覆盖 60+ 业务场景",
                    "PaaS + 订阅模式",
                ],
                "notes": "重点强调 PaaS",
            },
            {
                "layout": "two_content",
                "title": "核心能力",
                "content": ["法律咨询 / 文书生成 / 合同审查", "税务合规 / 资产追踪 / 财务诊断"],
            },
            {"layout": "title_only", "title": "Thank You"},
        ],
    )


if __name__ == "__main__":
    print(main())
