---
name: pptx
display_name: PowerPoint 演示文稿
version: 1.0.0
description: 创建/读取/编辑 .pptx 文件，含布局、图表、SmartArt、动画备注
category: office
type: tool
author: cowork
license: MIT
triggers:
  - 创建 ppt
  - 编辑 pptx
  - 演示文稿
  - 制作幻灯片
  - 路演 ppt
  - .pptx 文件
personas:
  - anxin_assistant
  - doc_secretary
  - market_researcher
  - lead_hunter
  - content_director
  - ecommerce_assistant
requires_apps: []
dependencies:
  - python-pptx
keywords:
  - office
  - presentation
  - slides
---

# PowerPoint 演示文稿技能（pptx）

> Cowork pptx skill 的安心智能助手 V3 移植版本，在 `python-pptx` 之上提供
> 中文友好的「创建 / 读取 / 编辑 / 主题切换」全套能力，并附带 4 个开箱即用的
> 业务模板。

## 一、典型场景

| 场景 | 触发词示例 | 输出 |
|------|-----------|------|
| 路演 / Pitch | "做一份天使轮路演 PPT" | `pitch_deck.md` 模板渲染 |
| 新品发布 | "Q3 新品发布会 PPT" | `product_launch.md` 模板渲染 |
| 公司介绍 | "我要去客户那讲公司 PPT" | `company_intro.md` 模板渲染 |
| 季度回顾 | "Q1 季度复盘 PPT" | `quarterly_review.md` 模板渲染 |
| 单点编辑 | "把第 3 页换成新数据" | `helpers.edit.replace_text` |
| 主题统一 | "把所有 PPT 换成商务风" | `helpers.theme.apply_theme` |

适用 personas：

- `anxin_assistant`（安心助手主入口，识别意图后调用本技能）
- `doc_secretary`（文档秘书，批量生成与编辑）
- `market_researcher`（市场调研报告 PPT）
- `lead_hunter`（销售线索路演材料）
- `content_director`（内容运营幻灯片）
- `ecommerce_assistant`（电商运营周报 / 复盘）

## 二、能力清单

### 1. 创建 `helpers.create`

```python
from skills.office.pptx.helpers.create import create_pptx

create_pptx(
    "out.pptx",
    slides=[
        {"layout": "title_only", "title": "公司路演"},
        {"layout": "title_content", "title": "市场",
         "content": ["TAM 1000 亿", "SAM 300 亿", "SOM 30 亿"]},
        {"layout": "title_content", "title": "增长",
         "chart": {"type": "bar", "categories": ["Q1","Q2","Q3","Q4"],
                   "series": [("营收", [10,15,22,30])]}},
    ],
)
```

支持 6 种布局：

| layout | 用途 |
|--------|------|
| `title_only` | 单一大标题 / 章节扉页 |
| `title_content` | 标题 + 正文（bullet list / chart / image） |
| `two_content` | 左右分栏 |
| `comparison` | 对比（含两侧标题 + 内容） |
| `picture_with_caption` | 图片 + 解说 |
| `blank` | 空白页（自由排版） |

内嵌图表类型：`bar` / `line` / `pie` / `scatter`。

### 2. 读取 `helpers.read`

```python
from skills.office.pptx.helpers.read import read_slides, read_metadata

slides = read_slides("deck.pptx")
# slides[i] = {"index", "layout", "title", "texts", "shapes", "notes"}
meta = read_metadata("deck.pptx")
# meta = {"slide_count", "title", "author", "created", "modified"}
```

### 3. 编辑 `helpers.edit`

```python
from skills.office.pptx.helpers.edit import (
    replace_text, reorder_slides, add_slide, remove_slide,
)

replace_text("deck.pptx", {"2025": "2026", "Q1": "Q2"})
reorder_slides("deck.pptx", [0, 2, 1, 3])
add_slide("deck.pptx", layout="title_content",
          content={"title": "致谢", "content": ["谢谢观看"]}, position=-1)
remove_slide("deck.pptx", index=4)
```

### 4. 主题 `helpers.theme`

```python
from skills.office.pptx.helpers.theme import apply_theme, set_master_font

apply_theme("deck.pptx", "商务")           # 「专业」/「商务」/「极简」
set_master_font("deck.pptx", title_font="SimHei", body_font="SimSun")
```

## 三、4 个内置模板

| 模板文件 | 用途 | 页数 | 关键页 |
|----------|------|------|--------|
| `templates/pitch_deck.md` | 投融资路演 | 10 | 问题 / 方案 / 市场 / 团队 / Ask |
| `templates/product_launch.md` | 新品发布 | 6 | 卖点 / 功能 / 差异化 / 价格 |
| `templates/company_intro.md` | 公司介绍 | 6 | 使命 / 团队 / 客户 / 数据 |
| `templates/quarterly_review.md` | 季度回顾 | 4 | 业绩 / 亮点 / 挑战 / 计划 |

模板为 Markdown 描述格式，由 `helpers.create.create_pptx_from_template`
解析后渲染为真实 .pptx。

## 四、字体与中文适配

中文 PPT 在跨平台时最常见的坑就是字体回退。本技能做了三处兜底：

1. **默认中文字体**：标题 `SimHei`、正文 `SimSun`，老版本 Office / WPS 均原生可用。
2. **Theme 切换时同步重置**：`apply_theme` 内部调用 `set_master_font`，确保
   主题色变化的同时字体不丢失。
3. **可覆盖**：`set_master_font(title_font=..., body_font=...)` 支持
   传入 `Microsoft YaHei` / `PingFang SC` / `Source Han Sans` 等任意字体名。

⚠️ 字体本身需在打开 PPT 的机器上已安装；本技能只负责写入字体名声明，不嵌入字体文件。

## 五、限制与边界

- 不支持复杂动画（路径动画 / 触发器 / 计时序列）；只支持基础切换。
- 不支持 SmartArt 的「图形 → 文本」反向解析（`python-pptx` 上游限制）。
- 嵌入图表使用 `python-pptx` 原生 `XL_CHART_TYPE`，复杂组合图请改用 matplotlib
  生成图片后用 `picture_with_caption` 布局插入。
- 视频 / 音频元素仅支持读取识别，不支持生成时插入。

## 六、与 P5-A 衔接

本技能与 P5-A `skills/office/docx/`（Word 文档）共享相同的目录骨架与
模板渲染思路：

- 同样的 `helpers/{create,read,edit,theme}.py` 四件套；
- 模板均使用 Markdown 描述，便于 LLM 直接生成 / 修改；
- 中文字体策略一致（标题 SimHei / 正文 SimSun），跨技能视觉风格统一；
- 后续 `personas.doc_secretary` 可在「调研报告」场景同时调用 docx + pptx，
  自动产出「Word 报告 + 路演 PPT」配套交付物。

## 七、安装与依赖

依赖已在 `backend/pyproject.toml` 声明（`python-pptx>=1`）：

```bash
cd backend && pip install -e .
```

测试：

```bash
pytest skills/office/pptx/tests -v
```
