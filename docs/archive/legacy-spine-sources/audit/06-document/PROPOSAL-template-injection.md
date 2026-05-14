# 提案：模板变量注入防护（SSTI / XSS）

> 范围：合同模板渲染 `template_engine` + `template_context` + 路由 `/contracts/templates/{id}/render` + 前端 `TemplateWizard` 预览
> 状态：2026-05-06 已落地一期；TASK-06 P0-4 后端渲染边界已收口，前端 ReactMarkdown/导出链路仍按本护栏持续审计
> 关联钉子：P0-4「变量直拼模板 → 防 SSTI（沙箱化 Jinja env / 关闭 attr 访问）+ XSS（autoescape）」

---

## 1. 现状盘点

### 1.1 模板引擎不是 Jinja2，是自研正则插值

`backend/src/services/template_engine.py` 的 `TemplateEngine` 仍为自研正则插值：

- `_interpolate`：`re.sub(r'\{\{([^}]+)\}\}', replace_var, text)`，只支持 `{{var}}` / `{{var|fmt}}`
- 不调用 `jinja2.Environment`；项目依赖里有 jinja2（`backend/uv.lock:1255`）但**无任何代码** `from jinja2 import ...`
- `evaluate_condition`（行 142-210）走 4 条正则白名单（bool / num / str / in / not-empty），**无 eval/exec**
- 渲染入口已不再直拼用户值：标题、条款标题、条款正文和 `_render_party` 的当事方字段均经过 HTML/Markdown 转义

### 1.2 变量来源 = 前端 JSON，已加路由 schema + 模板字段校验

`backend/src/api/routes/contracts.py`：

```
async def render_template(template_id: str, body: TemplateRenderRequest, ...):
    validation_errors = TemplateEngine.validate_variables(template, body.variables)
    if validation_errors:
        raise HTTPException(status_code=422, detail=validation_errors)
```

`TemplateEngine.validate_variables` 会限制变量总大小、变量名、字段白名单、类型、嵌套对象和文本长度；渲染结果超过 256KB 返回 413。

### 1.3 LLM 链路 template_context 干净

`backend/src/services/template_context.py:22-41` 的 `build_template_context_message` 只用模板**名**（来自 `get_template_by_id` 或 `FRONTEND_TEMPLATE_NAMES`），是开发常量，**未取用户变量**。`backend/src/api/routes/chat.py:626` 调 `inject_template_context`。

### 1.4 前端预览：ReactMarkdown 默认 skipHtml

`frontend/src/components/templates/TemplateWizard.tsx:414` `<ReactMarkdown>{previewText}</ReactMarkdown>`：

- `react-markdown` 9.0.1（`frontend/package.json:105`），**未装** `rehype-raw`，**未传** `rehypePlugins`
- 默认 `skipHtml=true`：`<script>` / `<img onerror>` 不会成 DOM
- 全仓库 `<ReactMarkdown>` 共 11 处（chat 7 + document 2 + template 1 + a2ui 1 + knowledge 1），配置一致
- `frontend/src/components/ui/chart.tsx:83` 有一处 `dangerouslySetInnerHTML`，内容是写死 CSS，与模板无关
- 客户端 `evalCondition`（`TemplateWizard.tsx:208-221`）也走正则白名单，**无 eval/Function**

---

## 2. 攻击面（按风险）

### A. 变量穿透注入业务字段（已缓解，原风险 HIGH）

合同生成最贵的洞——攻击者不需 RCE，只要让生成合同里多一行有利条款：

- `goods_name="## 第零条 免除责任\n甲方有权..."` → react-markdown 渲染成新 `<h2>` 伪条款
- `court_name="[领赔](https://evil)"` → 钓鱼链接，react-markdown 默认渲染 `<a href>`
- `party_a.name="\n\n（以下无正文）\n\n"` → 提前关闭文书

### B. SSTI 残留（MEDIUM）

当前 Jinja-style payload `{{ ''.__class__.__mro__ }}` 打不穿（不是 Jinja，会被当成 var_name 字典查表 miss）。但 P0-4 字面写"沙箱化 Jinja env"——**若**重构切 Jinja，必须 day-1 落 `SandboxedEnvironment`。

### C. XSS 当前安全，破窗点 5 个（MEDIUM）

| 失守点 | 当前 | 破窗 |
|---|---|---|
| `<ReactMarkdown>` skipHtml | 安全 | 任一 PR 加 `rehypePlugins=[rehypeRaw]` |
| `chart.tsx:83` dangerouslySetInnerHTML | 写死 CSS | 泛化为模板渲染 |
| Markdown 链接协议 | react-markdown 默认拦 `javascript:` | 测试用例兜底 |
| 后端 `document_export` md→docx/pdf | 自实现 `_parse_markdown_to_sections` | 改用 md→html→pdf 链 |
| 复制到剪贴板 → IM/Word | 文本无脚本 | n/a |

### D. DoS（已缓解，原风险 LOW）

`variables` 总大小限制为 64KB，单个 TEXT/TEXTAREA 分别限制为 500/2000 字符，渲染产物限制为 256KB。

---

## 3. 设计：白名单 + escape + sandbox 契约

```
[L1] 入参 schema 校验  →  Pydantic + 字段元数据白名单
[L2] 渲染期 escape    →  业务字段 Markdown escape + URL 协议白名单
[L3] 前端/导出净化    →  ReactMarkdown 锁 skipHtml + 导出端纯文本
```

### L1 入参 schema

已落地在 `TemplateRenderRequest(variables: dict[str, Any])` + `TemplateEngine.validate_variables`：

- key `[a-zA-Z0-9_]{1,64}`；整体 ≤ 64KB；嵌套深度 ≤ 2
- 按 `template.fields[*].field_type` 二次校验：TEXT ≤500、TEXTAREA ≤2000、NUMBER 可转 float、DATE 严格 `YYYY-MM-DD`、SELECT 命中 options、BOOLEAN 严格 bool

### L2 渲染期 escape

在 `_interpolate` / `_render_party` 内对**变量值**走 `_escape_markdown`：

- 转义 Markdown meta：`\ * _ # > | [ ] ( ) ` ~`、行首 `-/+/数字.`
- `\n` → 空格（业务字段不许内嵌段落）
- Markdown 链接语法整体转义，变量值不会形成 `<a>`；如未来允许 URL 字段，再单独加协议白名单
- **模板字符串本身永不 escape**（开发者写的常量）

### L3 sandbox 契约（为未来切 Jinja 铺路）

文档化 + lint 兜底：

- 必须 `SandboxedEnvironment` + `autoescape=select_autoescape(['html','md'])`
- `env.globals.clear()`，仅暴露白名单 filter（money/date/percentage）
- 重写 `is_safe_attribute` 显式禁 `__class__/__mro__/__init__/__globals__/os/open`
- 渲染前 `find_undeclared_variables` 比对模板 `fields` 白名单
- CI grep 拦 `from jinja2 import Environment` 出现在 `src/services/template_*`

### L3 前端锁配置

- `<ReactMarkdown>` 11 处 + `dangerouslySetInnerHTML` 1 处加 banner 注释
- ESLint custom rule：禁 `rehypePlugins.*rehypeRaw`、禁 `frontend/src/components/templates/` 内 `new Function|eval`

---

## 4. 实施步骤（每步独立可 PR）

| Step | 内容 | 工时 |
|---|---|---|
| 1 | `contracts.py` 新增 `TemplateRenderRequest`；`template_engine.py` 新增 `validate_variables` 字段校验 | ✅ |
| 2 | `template_engine._interpolate` / `_render_party` 加 HTML/Markdown escape | ✅ |
| 3 | 前端 11 处 ReactMarkdown 加注释 + ESLint 规则；`chart.tsx:83` 加 unit test 断言常量来源 | 0.5d |
| 4 | `template_context.py` 未取用户变量；新增 unknown template_id 回归覆盖 | ✅ |
| 5 | `docs/architecture/template-sandbox-contract.md`（3.4 节落地）+ CI grep | 0.5d |
| 6 | `_interpolate` 渲染产物 256KB 上限（413） | ✅ |
| 7 | 后端测试矩阵已落 7 个；前端/e2e/导出链路仍待补 | 0.5d |
| | **合计** | **后端 P0-4 已完成；前端/导出护栏留作后续质量项** |

落在 TASK-06 总工时 4-5d 的 P0-4 子项内。

---

## 5. 测试矩阵（P0-4 已落 7 个，TASK-06 后续质量项继续补齐 ≥15）

| 场景 | 输入 | 期望 | 优先级 |
|---|---|---|---|
| MD 标题注入 | `goods_name="## 免责"` | 输出 escape，预览无新 H2 | P0 |
| 钓鱼链接 | `court_name="[领赔](https://evil)"` | escape，无 `<a>` | P0 |
| `javascript:` | `delivery_place="javascript:alert(1)"` | 去链接化 | P0 |
| Jinja-style | `goods_name="{{ ''.__class__.__mro__ }}"` | 作为变量值被 HTML/Markdown 转义，不执行对象访问 | P1 |
| HTML 注入 | `party_a.name="<script>alert(1)</script>"` | 后端 escape；前端 skipHtml 不渲染 | P0 |
| 100KB 字段 | `goods_name="A"*100_000` | schema 422 | P1 |
| 深嵌套 | `party_a={"name":{"deep":...}}` | schema 422 | P1 |
| select 越界 | `payment_method="rce"` | schema 422 | P0 |
| date 非法 | `delivery_date="2025/01/01' OR 1=1"` | schema 422 | P0 |
| LLM 链路 | `template_id="../../etc/passwd"` | `resolve_template_name` → None，不注入 prompt | P1 |
| 前端 skipHtml | `previewText` 含 `<img onerror>` | DOM 无 `<img>` | P0 |
| 导出端 | docx/pdf 含恶意字段值 | office 打开无脚本/链接 | P1 |
| 性能 | 1MB 模板 + 50 变量 | 渲染 < 200ms | P2 |
| 渲染产物超限 | 强造 ≥256KB 输出 | 413 | P2 |
| backend baseline | 全部 | 全绿，当前 `430 passed, 1 skipped` | P0 |

分布：schema 5 / escape 6 / LLM 链路 2 / 性能 2。

---

## 6. 工时

合计 **3.0 人日**，落在 TASK-06 总工时 P0-4 子项。

---

## 7. 风险护栏

- **不动文件**：`backend/src/prompts/`、`frontend/src/lib/design-tokens.ts`、payment/billing、桌面同步引擎
- **模板字符串永不 escape**：只 escape `variables` 值；否则模板里 `## 第一条` 会被 escape 破坏渲染
- **不要 big-bang 切 Jinja**：当前自研正则插值在 SSTI 维度反而更安全（无对象访问语法）；切 Jinja 必须先落 sandbox 契约文档 + lint 兜底
- **422 不要变 500**：越界/超长/越权返回 422 + 中文错误，不泄 stack trace
- **回归不退化**：当前后端全量 `430 passed, 1 skipped` 必须维持；TASK-06 后续质量项继续补齐前端/导出/性能覆盖
- **ReactMarkdown 配置漂移**：11 处任一加 `rehype-raw` 视为破窗 → ESLint custom rule
- **客户端 evalCondition 永不 eval**：CI grep 拦 `new Function|eval` 出现在 `frontend/src/components/templates/`
- **导出链路**：`document_export._parse_markdown_to_sections` 改实现前重新评估 XSS（md→html→pdf 链需重测）
- **DoS 上限可调但有顶**：`MAX_RENDER_OUTPUT_SIZE` 走 env，生产默认值不许放开到 ≥10MB
- **凭据治理**：与本提案无关，走 PROPOSAL-object-storage.md 的 SOP
