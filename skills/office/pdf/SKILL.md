---
name: pdf
display_name: PDF 文档处理
version: 1.0.0
description: 读取/合并/拆分/生成/OCR/水印/加密 PDF 文件
category: office
type: tool
author: cowork
license: MIT
triggers:
  - 处理 pdf
  - 合并 pdf
  - 拆分 pdf
  - 提取 pdf 文本
  - 扫描件识别
  - pdf 加水印
  - .pdf 文件
personas:
  - anxin_assistant
  - doc_secretary
  - legal_advisor
  - contract_steward
  - due_diligence_expert
  - market_researcher
requires_apps: []
dependencies:
  - pypdf
  - reportlab
  - pdfplumber
  - pytesseract     # 系统需装 tesseract-ocr
keywords:
  - office
  - document
  - pdf
  - ocr
---

# PDF 文档处理技能

> 移植自 cowork 官方 `skills/pdf`，针对「安心智能助手 V3」的法务/尽调/调研场景做了本地化适配。

## 一、典型场景

| 场景 | 涉及能力 | 推荐 persona |
|------|---------|--------------|
| **合同审查**：从扫描合同里提取正文，做风险点识别，最后输出带水印的修订版 | extract / ocr / watermark | `legal_advisor` / `contract_steward` |
| **发票批处理**：把一批月度发票 PDF 合并成单一附件，再加密发给会计 | manipulate.merge / watermark.encrypt | `doc_secretary` |
| **扫描件识别**：把法院送达的扫描件 PDF 转成可检索文本 | ocr.ocr_pdf（chi_sim+eng） | `legal_advisor` |
| **调研报告生成**：把 markdown 调研稿一键打印为带页眉页脚的 PDF | generate.markdown_to_pdf | `market_researcher` |
| **尽调材料归档**：拆分超长尽调 PDF 为按章节文件，再批量提取表格 | manipulate.split / extract.extract_tables | `due_diligence_expert` |
| **证书签发**：从证书模板生成获奖证书 PDF | generate + templates/certificate.md | `anxin_assistant` |

## 二、能力清单

### `helpers/extract.py` — 内容提取（基于 pdfplumber）
- `extract_text(path, pages=None) -> str` 提取纯文本（可指定页范围）
- `extract_tables(path) -> list[list[list[str]]]` 提取表格三维数组
- `extract_images(path, out_dir) -> list[Path]` 抽出全部内嵌图片
- `extract_metadata(path) -> dict` 标题/作者/页数/创建时间等

### `helpers/manipulate.py` — 页面操作（基于 pypdf）
- `merge(paths, out_path)` 多文件合并
- `split(path, ranges, out_dir)` 按页范围拆分
- `rotate(path, page, degrees, out_path)` 单页旋转（90/180/270）
- `reorder(path, new_order, out_path)` 页面重排

### `helpers/generate.py` — PDF 生成（基于 reportlab）
- `markdown_to_pdf(md_text, out_path, font='SimSun')` 中文友好（自动注册字体）
- `html_to_pdf(html_text, out_path)` 支持基本标签 + 段落

### `helpers/ocr.py` — 扫描件识别（基于 pytesseract + Pillow）
- `ocr_pdf(path, lang='chi_sim+eng') -> str` 整文档 OCR
- `ocr_image(image_path, lang='chi_sim+eng') -> str` 单张图 OCR
- 系统依赖：`brew install tesseract tesseract-lang` 或 `apt install tesseract-ocr tesseract-ocr-chi-sim`
- 验证语言包：`tesseract --list-langs` 必须包含 `chi_sim`

### `helpers/watermark.py` — 水印与加密（基于 pypdf + reportlab）
- `add_text_watermark(path, text, out_path, opacity=0.3, angle=45)`
- `add_image_watermark(path, image_path, out_path)`
- `encrypt(path, password, out_path)` AES-256 强加密（pypdf 4.x 默认）
- `decrypt(path, password, out_path)` 解密

### `helpers/form.py` — 表单填写（基于 pypdf）
- `read_form(path) -> dict[field_name, value]`
- `fill_form(path, data, out_path)` 写入字段并扁平化

## 三、快速示例

### 1. 提取合同正文
```python
from skills.office.pdf.helpers.extract import extract_text
text = extract_text("contract.pdf", pages=(1, 5))
print(text[:200])
```

### 2. 合并发票
```python
from skills.office.pdf.helpers.manipulate import merge
merge(["inv-202504-01.pdf", "inv-202504-02.pdf"], "invoices-2025-04.pdf")
```

### 3. 扫描件 OCR（中英混合）
```python
from skills.office.pdf.helpers.ocr import ocr_pdf
text = ocr_pdf("scanned-judgement.pdf", lang="chi_sim+eng")
```

### 4. 加文字水印 + 加密
```python
from skills.office.pdf.helpers.watermark import add_text_watermark, encrypt
add_text_watermark("draft.pdf", "机密 · 仅供内部审阅", "draft-wm.pdf")
encrypt("draft-wm.pdf", "S3cret!", "draft-final.pdf")
```

### 5. 调研稿 → PDF
```python
from skills.office.pdf.helpers.generate import markdown_to_pdf
markdown_to_pdf(open("research.md").read(), "research.pdf")
```

## 四、模板（`templates/`）

| 文件 | 用途 | 占位符示例 |
|------|------|-----------|
| `contract.md` | 通用商业合同骨架 | `{{party_a}}` `{{party_b}}` `{{amount}}` |
| `invoice.md` | 简洁发票样式 | `{{invoice_no}}` `{{items}}` `{{total}}` |
| `research.md` | 调研/尽调骨架（report 同义） | `{{title}}` `{{author}}` `{{sections}}` |
| `certificate.md` | 证书/奖状 | `{{recipient}}` `{{achievement}}` `{{issue_date}}` |

模板均为 Markdown 格式，可与 `generate.markdown_to_pdf()` 直接配合渲染。

## 五、加密强度

- pypdf 4.x 默认采用 **AES-256**（PDF 2.0 规范），等价于命令行 `qpdf --encrypt`。
- 兼容旧 PDF 阅读器时可降级为 RC4-128，但本 skill 默认开启 AES-256，请妥善保管密码（**忘记无法找回**）。
- 法律建议：发往外部的合同/裁判文书 PDF 推荐统一加密 + 水印双保护。

## 六、与其它 skill 的衔接

- 与 `skills/legal/contract-review` 协同：先用本 skill 的 `ocr` + `extract` 把扫描合同转文本，再交给合同审查 skill 出风险报告。
- 与 `skills/legal/due-diligence` 协同：尽调材料用 `manipulate.split` 按章节拆分后建索引。
- 与 P5-A 的「office 文档套件」共用 reportlab/pdfplumber 依赖，避免重复安装。

## 七、限制

1. OCR 准确率依赖 tesseract 模型，复杂版式建议预先做 deskew 处理。
2. 对加密 PDF 的提取/合并需先 `decrypt`。
3. `html_to_pdf` 仅支持基础标签（h1-h6、p、ul/ol、table），复杂 CSS 请改用 weasyprint。
