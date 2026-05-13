# -*- coding: utf-8 -*-
"""示例 3：从合同模板批量生成定制合同 + 单元格补丁。

流程：
1. 读取 templates/contract_template.docx.md 模板（markdown）
2. 用 markdown_to_docx 渲染为 .docx
3. 调用 find_replace 把所有占位符替换为真实甲方/乙方信息
4. 调用 update_table_cell 修正合同金额表格中某一项

运行：
    python skills/office/docx/examples/edit_with_search_replace.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from skills.office.docx.helpers.convert import markdown_to_docx
from skills.office.docx.helpers.edit import find_replace, update_table_cell


def main(out_path: str = "/tmp/contract_filled.docx") -> Path:
    tpl_path = ROOT / "skills" / "office" / "docx" / "templates" / "contract_template.docx.md"
    md = tpl_path.read_text(encoding="utf-8")
    out = Path(out_path)
    markdown_to_docx(md, out)

    mapping = {
        "{{合同编号}}": "AX-2026-0426-001",
        "{{签订日期}}": "2026-04-26",
        "{{签订地点}}": "北京市海淀区",
        "{{甲方}}": "北京安心科技有限公司",
        "{{甲方信用代码}}": "91110108MA00ABCDE1",
        "{{甲方法人}}": "陈安心",
        "{{甲方地址}}": "北京市海淀区中关村大街 1 号",
        "{{乙方}}": "上海智策咨询有限公司",
        "{{乙方信用代码}}": "91310115MA1XYZ4567",
        "{{乙方法人}}": "李智策",
        "{{乙方地址}}": "上海市浦东新区张江高科技园区",
        "{{服务内容描述}}": "提供 安心智能助手二次开发与运维支持",
        "{{合同金额}}": "120,000",
        "{{首付款}}": "60,000",
        "{{尾款}}": "60,000",
        "{{合同终止日}}": "2027-04-25",
        "{{保密期限}}": "三",
        "{{仲裁机构}}": "北京仲裁委员会",
    }
    n = find_replace(out, mapping)
    print(f"占位符替换完成，共 {n} 处。")

    # 修正合同金额表的"含税"备注（如果模板里默认是"含税"，演示原地改成"含 6% 增值税"）
    if update_table_cell(out, table_idx=0, row=1, col=2, value="含 6% 增值税"):
        print("合同金额表 row=1 col=2 已更新。")

    return out


if __name__ == "__main__":
    out = main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/contract_filled.docx")
    print(f"已生成: {out}")
