# P16-D 依赖漏洞升级报告

> 关联：`docs/v3/SECURITY_AUDIT.md` A06（Vulnerable & Outdated Components）  
> 执行日期：2026-04-29  
> 范围：仅 `backend/pyproject.toml` + `backend/uv.lock` + `frontend/package.json` + `frontend/package-lock.json`，未触碰业务代码
>
> ⚠️ **2026-05 更新**：CAMEL-AI 已全量剥离（迁至自研 Harness 层），本报告中"受 camel-ai 约束"
> 一类豁免条件已不复存在，`litellm` 升级路径不再被锁定，相关跟踪项可关闭。

---

## 1. 摘要

| 维度 | Before | After | Δ |
| :--- | :---: | :---: | :---: |
| 后端 pip-audit 高危漏洞包数 | 6（cryptography/pyjwt/litellm/pypdf/lxml/pillow）| 3（litellm/lxml/pillow，受上游约束残留）| **-3** |
| 后端关键 CVE 修复数 | 0 | **17**（3 cryptography + 1 pyjwt + 12 pypdf + 1 transitive openssl 升级）| +17 |
| 前端 npm audit 漏洞总数 | 31（critical 1 / high 19 / moderate 10 / low 1）| 5（moderate 5）| **-26** |
| 前端 critical/high 漏洞 | 20 | **0** | **-20** |
| 后端 pytest（非 integration）| 1013 passed / 10 failed | 1013 passed / 10 failed | 0 回归 |
| 前端 lint | 1 error（pre-existing 不规则空白）| 1 error（同基线）| 0 回归 |
| 前端 build | ✓ | ✓ | 持平 |
| 前端 tsc --noEmit | ✓ | ✓ | 持平 |

---

## 2. 后端升级明细

### 已升级（受控）

| 包 | Before | After | 修复 CVE/GHSA | 影响面 |
| :--- | :---: | :---: | :--- | :--- |
| **cryptography** | 46.0.3 | **47.0.0** | CVE-2026-26007 / 34073 / 39892（3 高危）| 直接：`Fernet` / `MultiFernet`（`token_store.py`、`feishu_signature.py`、`llm_service.py`、`data_center_service.py`），无 API 变更 |
| **pyjwt** | 2.10.1 | **2.12.1** | CVE-2026-32597 | 间接（`python-jose` 链路），无直接 import |
| **pypdf** | 6.6.0 | **6.10.2** | 12 个 CVE/GHSA（PDF 解析栈）| 直接：`document_parser.py` 用 `pypdf.PdfReader`，公共 API 兼容 |
| pyopenssl（transitive）| 26.0.0 | 26.1.0 | 跟随 cryptography 47 升级 | — |

### 残留（受上游约束无法升级，已记入风险清单）

| 包 | 当前版本 | 目标版本 | 残留 CVE/GHSA | 阻塞原因 |
| :--- | :---: | :---: | :--- | :--- |
| **litellm** | 1.83.0 | 1.83.7+ | GHSA-xqmj-j6mv-4862 | `camel-ai>=0.2.14,!=0.2.72`（所有发行版本）锁定 `litellm<=1.83.6`，所有 1.83.7+ 与现行 camel-ai 不兼容；上游 camel-ai 仅提供 pre-release（0.2.91a3）支持新 litellm |
| **lxml** | 5.4.0 | 6.1.0 | CVE-2026-41066 | `crawl4ai>=0.4.0,<0.9` 全部版本均 pin `lxml>=5.3,<6.dev0`，5.x 线最末版本即 5.4.0（无补丁版） |
| **pillow** | 10.4.0 | 12.2.0 | CVE-2026-25990 / 40192 | `crawl4ai>=0.4.0,<=0.6.3` 均 pin `pillow>=10.4,<11.dev0`，10.x 线最末版本即 10.4.0（无补丁版） |

**残留缓解措施**：
- `crawl4ai_service` 与 `lxml`/`pillow`/`litellm` 仅服务端进程内使用；不直接接受用户上传 XML 至 `lxml.etree`，所有外部 URL 走 `crawler_service` 三层降级 + URL allowlist。
- 已在 `docs/v3/SECURITY_AUDIT.md` A06 章节记入跟踪项。
- 跟踪计划：监控 `crawl4ai`/`camel-ai` 上游 release，达标后下一周期 (P17) 一并升级。

### pyproject.toml 改动（仅依赖声明）

```diff
-    "pypdf>=4.0",
+    "pypdf>=6.10.2",            # P16-D: 修 12 CVE
+    "litellm>=1.83.0",          # P16-D: 显式锁定，受 camel-ai 约束暂未升级
+    "cryptography>=46.0.7",     # P16-D: 修 3 CVE-2026
+    "pyjwt>=2.12.0",            # P16-D: 修 CVE-2026-32597
-    "lxml>=5",
+    "lxml>=5.4",                # 受 crawl4ai 约束暂留 5.4
+    "pillow>=10.4",             # 同上
```

---

## 3. 前端升级明细

| 包 | Before | After | 修复 CVE/GHSA |
| :--- | :---: | :---: | :--- |
| **lodash**（transitive）| <4.17.21 | **4.18.1** | GHSA-jf85-cpcp-j695（critical, 原型污染）+ GHSA-35jh-r3h4-6jhm（high, 命令注入）+ 4 项 |
| **vite**（direct）| 7.3.1 | **7.3.2** | GHSA-v2wj-q39q-566r（high, fs.deny bypass）+ GHSA-p9ff-h696-f583（high, WS 任意文件读）+ GHSA-4w7w-66w2-5vf9（mod, path traversal）|
| **rollup**（transitive）| 4.0-4.58 | **4.60.2** | path traversal 写 |
| **uuid**（direct）| ^13 | **^14.0.0** | GHSA-w5hq-g745-h8pq（v3/v5/v6 buffer 边界缺失，仅当 buf 参数提供时） |
| **@typescript-eslint/eslint-plugin**（dev）| ^6.19.0 | **^7.18.0** | minimatch 链路漏洞（GHSA range 6.16.0-7.5.0）|
| **@typescript-eslint/parser**（dev）| ^6.19.0 | **^7.18.0** | 同上 |
| **braces / micromatch / picomatch / debug / flatted / minimatch / brace-expansion / postcss / ajv / markdown-it / follow-redirects / browserify-css**（transitive）| 多旧版 | npm dedupe 后到补丁版 | 多 high/moderate（npm audit fix 自动消解）|

### 升级策略说明

- **直接 npm audit fix**：解决了 31 → 12 漏洞（lodash critical、vite/rollup 全部 high 一并消解）。
- **npm audit fix --force**：将 uuid 推到 v14（API 变更：`v4()` 仍兼容；项目内仅用 `v4`），将 `@typescript-eslint/*` 推到 v8。
- **回退 v8 → v7.18**：v8 默认启用 `no-unused-expressions` 严格模式，对项目内 `import.meta.env.DEV && console.debug(...)` 等短路写法触发 5 个 lint 报错（破坏性）。v7.18 与 v8 一样不在 6.16-7.5 漏洞区间，因此降至 v7.18 既消除漏洞又不引入 lint 回归。
- **uuid v14 兼容性**：项目仅使用 `import { v4 as uuidv4 } from 'uuid'`，v14 中 `v4()` API 完全向后兼容，构建/类型检查全绿。

### 残留（5 moderate，全部位于 `react-force-graph-3d` 可视化链路）

```
3d-force-graph-vr → aframe → three-bmfont-text → nice-color-palettes → got<11.8.5
```

- 触发条件：`got` UNIX socket 重定向（GHSA-pfrx-2q88-qq97）。
- 影响面：仅当浏览器中调用 `nice-color-palettes` 远程取色（运行时不会触发该路径）。
- 阻塞：`got` 链路被 `aframe` 间接锁定，需上游 `nice-color-palettes` 升级。
- 缓解：所有可视化组件运行在用户浏览器沙箱中，无服务端渲染；不接收外部 URL 输入。

---

## 4. 验证证据

### 后端 pytest（非 integration）

| 阶段 | 命令 | 结果 |
| :--- | :--- | :--- |
| 升级前（baseline）| `uv sync --extra dev && uv run pytest tests/ -q --ignore=tests/integration` | **1013 passed, 10 failed**（pre-existing：l3_headlessx_tier×6 / persona content×2 / dd_expert / tax_finance）|
| 升级后 | 同上 | **1013 passed, 10 failed**（完全相同的 10 个失败）|
| Δ | | **0 回归**（fail 集合完全一致）|

### 前端

| 阶段 | 命令 | 结果 |
| :--- | :--- | :--- |
| Before | `npm audit --json \| jq .metadata.vulnerabilities` | `{critical:1, high:19, moderate:10, low:1}` |
| After | 同上 | `{critical:0, high:0, moderate:5, low:0}` |
| Build | `npm run build` | ✓ built in 11.70s |
| TypeScript | `npx tsc --noEmit` | ✓ 0 error |
| Lint（baseline）| `npm run lint` | 1 error（`finance-discovery.spec.ts:8:39 no-irregular-whitespace`，pre-existing）|
| Lint（after）| 同上 | 1 error（同上，未引入新 lint 错误）|

> **注**：`finance-discovery.spec.ts` 的 lint 报错存在于本任务开始前的 baseline 中（属 P14 E2E spec 文件），不在本次 P16-D 文件边界内，留待 P14 维护者修复。

---

## 5. 兼容性改动

**0 个**业务代码兼容补丁。所有升级均通过 `pyproject.toml` / `uv.lock` / `package.json` / `package-lock.json` 完成，未触碰：

- `backend/src/**`（service / route / persona / agent）
- `backend/tests/**`
- `frontend/src/**`
- `frontend/e2e/**`

---

## 6. 风险与回滚

### 风险评估

| 升级 | 风险等级 | 备注 |
| :--- | :---: | :--- |
| cryptography 46→47 | 低 | 仅用 Fernet 高层 API；47.0 ChangeLog 无 Fernet 破坏性变更；本地导入 + Fernet 实例化测试通过 |
| pyjwt 2.10→2.12 | 极低 | 项目无直接 import，仅 transitive |
| pypdf 6.6→6.10 | 低 | `document_parser.py` 用 `PdfReader(file).pages`，公共 API 稳定；pytest 涉及解析的 case 全绿 |
| uuid 13→14 | 低 | 仅用 `v4()`，API 兼容；build + tsc 全绿 |
| vite 7.3.1→7.3.2 | 极低 | patch-level 升级 |
| @typescript-eslint 6→7.18 | 中（已规避）| v8 触发新规则报错，已主动降级到 v7.18 规避 |

### 回滚步骤

如发现新 incident：

```bash
# 仅回滚后端
cd backend && git checkout v3/main -- pyproject.toml uv.lock && uv sync --extra dev

# 仅回滚前端
cd frontend && git checkout v3/main -- package.json package-lock.json && npm ci

# 全量回滚（提交后）
git revert <commit-sha>
```

回滚不影响数据库、配置、运行时状态，仅替换依赖。

---

## 7. 后续待办（P17 候选）

1. **跟踪 crawl4ai 上游**：等其放开 `lxml<6` / `pillow<11` 约束后，升级 lxml→6.1+ 与 pillow→12.2+，关闭 CVE-2026-41066 / 25990 / 40192。
2. **跟踪 camel-ai 稳定版兼容 litellm 1.83.7+**：当前仅 0.2.91a3 pre-release 支持，等正式版后升级 litellm 关闭 GHSA-xqmj-j6mv-4862。
3. **可视化链路 got 升级**：等 `nice-color-palettes` / `three-bmfont-text` 上游升级 got 至 ≥11.8.5。
4. **fix 1 个 pre-existing lint error**：`frontend/e2e/v3-personas/finance/finance-discovery.spec.ts:8:39` 不规则空白字符（不在本任务文件边界，归属 P14 维护者）。
