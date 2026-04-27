---
name: docx
display_name: Word 文档处理
version: 1.0.0
description: 创建/读取/编辑 .docx 文件，含格式化文本、表格、图片、目录、页码
category: office
type: tool
author: cowork
license: MIT
triggers:
  - 创建 word 文档
  - 编辑 docx
  - word 文档生成
  - 添加表格
  - .docx 文件
  - 写一份合同
  - 生成会议纪要
  - 输出报告
  - docx 模板
  - markdown 转 word
personas:
  - anxin_assistant
  - doc_secretary
  - legal_advisor
  - contract_steward
  - content_director
requires_apps: []
dependencies:
  - python-docx
keywords:
  - office
  - document
  - microsoft-word
  - word
  - docx
  - report
  - contract
  - meeting-minutes
---

# Word 文档处理（docx）

> 从 cowork docx skill 移植到「安心智能助手」V3，并按本仓 SkillRegistry / SkillExecutor 的 frontmatter schema 适配。
> 适用于所有需要生产 .docx 文件的工作流：合同起草、会议纪要、项目报告、汇报材料、对外公文等。

---

## 场景说明

**1. 法务/合同起草场景**
合同律师、合规专员、合同管家在起草甲乙丙三方协议、补充协议、保密协议时，
需要在已有合同模板基础上做"查找替换"（甲方名称、签约金额、生效日期）、
插入条款、修改表格金额，并保留合同原有格式（页眉公司 LOGO、页脚页码、目录）。
这个 skill 提供 `helpers.edit.find_replace` / `helpers.edit.update_table_cell` 直接覆盖这个工作流。

**2. 会议/汇报材料生成场景**
文档秘书、内容总监、项目经理需要把"会议要点"或"周报"快速结构化为标准 .docx，
含一级/二级标题、要点列表、行动项表格、签名页，并自动插入页码与目录。
通过 `helpers.create.create_docx(sections=[...])` 用结构化数据一次生成。

**3. 跨格式转换场景**
当上游 Agent 已经产出 Markdown 内容（如 LLM 总结的会议纪要、知识库导出文章），
而下游交付方需要 .docx 时，使用 `helpers.convert.markdown_to_docx` 一键转换；
反向场景（解析客户提供的 .docx 让 Agent 处理）使用 `helpers.convert.docx_to_markdown`。

---

## 核心能力清单

- 创建空白 .docx 并按结构化 sections 一次性写入（段落 / 标题 / 表格 / 图片 / 分页 / 页眉 / 页脚 / 目录字段）
- 中文字体智能切换（默认正文 SimSun 宋体、标题 SimHei 黑体，可覆盖）
- 表格生成支持表头加粗、单元格对齐、自适应列宽
- 图片插入支持指定宽度（厘米/英寸）并保持纵横比
- 自动插入 TOC 字段（Word 打开时按 F9 更新即可生成目录）
- 页码自动注入（页脚右对齐"第 X 页 共 Y 页"）
- 读取整个文档的纯文本流、所有表格的二维数组、文件元数据（作者/创建/修改时间）
- 查找替换支持精确字符串与多字段映射 dict，且不破坏现有 run 的格式
- 在指定锚点段落后插入新段落
- 按 (table_idx, row, col) 精确更新单元格
- Markdown ↔ docx 双向互转（支持标题、列表、表格、代码块、加粗/斜体）

---

## 快速示例

### 创建一个简单文档

```python
from skills.office.docx.helpers.create import create_docx

create_docx(
    "/tmp/hello.docx",
    sections=[
        {"type": "heading", "level": 1, "text": "项目周报"},
        {"type": "paragraph", "text": "本周完成情况如下："},
        {"type": "table", "header": ["任务", "负责人", "状态"],
         "rows": [["P5-A SkillRegistry", "张三", "进行中"],
                  ["P5-B docx skill 移植", "李四", "已完成"]]},
        {"type": "page_break"},
        {"type": "heading", "level": 2, "text": "下周计划"},
        {"type": "paragraph", "text": "继续推进 P5 阶段。"},
    ],
)
```

### 读取已有文档

```python
from skills.office.docx.helpers.read import read_text, read_tables, read_metadata

text = read_text("/tmp/hello.docx")
tables = read_tables("/tmp/hello.docx")
meta = read_metadata("/tmp/hello.docx")
print(meta["author"], meta["created"], len(tables))
```

### 查找替换 + 单元格更新

```python
from skills.office.docx.helpers.edit import find_replace, update_table_cell

find_replace(
    "/tmp/contract.docx",
    {"{{甲方}}": "北京安心科技有限公司",
     "{{签约日期}}": "2026-04-26",
     "{{合同金额}}": "人民币壹拾贰万元整"},
)
update_table_cell("/tmp/contract.docx", table_idx=0, row=2, col=1, value="50,000")
```

---

## 模板列表

模板以 `*.docx.md`（Markdown 源）形式存放在 `templates/`，运行时通过
`helpers.convert.markdown_to_docx` 转成 .docx，便于在 git 中可读 diff。

| 模板文件 | 适用场景 |
|---------|---------|
| `templates/contract_template.docx.md` | 标准服务合同（甲乙双方、标的、价款、违约、争议解决） |
| `templates/report_template.docx.md` | 项目周报/月报（封面、目录、章节、行动项表格） |
| `templates/meeting_minutes.docx.md` | 会议纪要（与会人、议题、决议、行动项、签名页） |

调用示例：

```python
from pathlib import Path
from skills.office.docx.helpers.convert import markdown_to_docx

md = Path("skills/office/docx/templates/contract_template.docx.md").read_text(encoding="utf-8")
md = md.replace("{{甲方}}", "安心科技").replace("{{乙方}}", "客户公司")
markdown_to_docx(md, "/tmp/contract.docx")
```

---

## 限制与注意

- **仅支持 .docx（OOXML）**，不支持老版 .doc 二进制格式；如需读取 .doc 请先用 LibreOffice/Word 转换为 .docx。
- **TOC 字段更新**：python-docx 只能"插入 TOC 字段"，实际目录文本需要在 Word 客户端打开后按 F9 生成；服务端无 Word 时可保留字段，下游打开即更新。
- **复杂图表保留度有限**：嵌入的 Excel 图表、SmartArt、批注样式在编辑保存后可能丢失部分外观；建议这些场景下走"模板套用"而非二次编辑。
- **中文字体依赖客户端**：默认 SimSun/SimHei 在 Windows/Office 全平台可用；macOS 上若缺字体会回退至系统中文字体，不影响内容只影响外观。
- **图片必须在文件系统中存在**：插图传入的是路径，远程 URL 请先下载到本地。
- **Markdown 转换覆盖度**：`markdown_to_docx` 支持标题、段落、有序/无序列表、表格、代码块、`**粗体**` `*斜体*`；不支持行内 HTML、复杂嵌套引用、脚注。

---

## 依赖与许可

- 运行依赖：`python-docx>=1.1.0`（已写入 `backend/pyproject.toml`）
- 可选依赖：`markdown>=3.5`（仅 `convert.markdown_to_docx` 使用，未安装时会回退到内置极简解析器）
- 来源：本 skill 移植自 cowork [anthropics/skills/skills/docx](https://github.com/anthropics/skills/tree/main/skills/docx)
- 许可：MIT（继承 cowork 上游）

---

## 与 SkillRegistry 衔接

本 SKILL.md 的 frontmatter 完全遵循 P5-A 约定的 schema：
- `name` 唯一 ID，与目录名一致
- `triggers` 用于关键词路由
- `personas` 限定可调用此 skill 的 user-facing 角色
- `dependencies` 用于运行时检查（缺包时 SkillExecutor 应给出友好提示）
- `category=office`、`type=tool` 让上层可按门类组织 UI

新增 persona 或 trigger 时直接在本文件 frontmatter 维护即可。
