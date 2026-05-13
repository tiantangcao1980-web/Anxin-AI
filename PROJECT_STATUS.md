# 安心智能助手 — 项目开发进度

> 本文件用于跨设备/跨智能体协作时快速了解项目状态，每次开发后更新。
> 2026-05-12 品牌升级：安心法务 → 安心智能助手（V3 scope 合并进商业交付主线）。
>
> 🧭 **当前权威执行计划** → [docs/00-project-execution-map.md](docs/00-project-execution-map.md) · [docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md) · [docs/RELEASE_GATE.md](docs/RELEASE_GATE.md)
> 本文件**仅作历史快照与进度回顾**，与权威 Spine（REQUIREMENTS / ARCHITECTURE / ROADMAP / DEVELOPMENT_PLAN / RELEASE_GATE）冲突时以 Spine 为准。

---

## 2026-05-14（下午）文档单一信源化（5 Spine + 9 Wiki + 101 归档）

### 本轮目标

执行用户指令"项目只保留一套完整的文档，其余的全部清理掉" — 完成 **A1–A6 六阶段**，把项目从 170+ 个分散源文档收敛为 **5 份 Spine（人类协作主干）+ 9 份 LLM Wiki（AI 智能体接手副本）+ 三大单一真相源**，并把 101 份被取代的源文档归档至 `docs/archive/legacy-spine-sources/`。

### 6 阶段时间线（在原 H1 基线之上又领先 `origin/main` 至少 4 个 commit）

| Phase | 内容 | Commits |
|---|---|---|
| **A1 审计** | Explore agent 全文档梳理（Sources / Outline / Conflicts / Stale） | （研究产出，无单独 commit） |
| **A2 LLM Wiki** | 9 文件高密度 Wiki — AI 智能体 30 秒接手 + 5 步 onboarding | `e2303507` |
| **A3 5 Spine** | REQUIREMENTS / ARCHITECTURE / ROADMAP / DEVELOPMENT_PLAN / RELEASE_GATE + .gitignore 旧规则清理 | `04a53809` |
| **A4 归档** | 101 份源文档 `git mv` 至 `docs/archive/legacy-spine-sources/` + 归档 README | `5ddf1a3e` |
| **A5 导航重写** | README / 00-execution-map / 01-core-docs / standards 等 9 个活跃文档全部指向新 Spine | `8425d2cc` |
| **A6 一致性验证** | JSON/script 路径修正、Gate 全部通过、89 测试通过 | （本 commit） |

### 文档新结构

```
docs/
├── REQUIREMENTS.md            ← Spine 1
├── ARCHITECTURE.md            ← Spine 2
├── ROADMAP.md                 ← Spine 3
├── DEVELOPMENT_PLAN.md        ← Spine 4
├── RELEASE_GATE.md            ← Spine 5
├── 00-project-execution-map.md   ← 总入口
├── 01-core-docs.md               ← 三大核心层索引
├── wiki/                          ← LLM Wiki（9 文件 1342 行）
│   ├── README.md
│   ├── 01-project-snapshot.md
│   ├── 02-quick-context.md
│   ├── 03-current-state.md
│   ├── 04-architecture-map.md
│   ├── 05-domain-glossary.md
│   ├── 06-decision-log.md
│   ├── 07-common-pitfalls.md
│   └── 08-ai-onboarding-flow.md
├── adr/ audit/harness/ design/ desktop/ mobile/ v3/ release/ standards/ references/   ← 活跃领域
└── archive/                       ← 历史源文档（仅供溯源）
    ├── legacy-spine-sources/      ← 101 份被 Spine 取代的源文档
    │   ├── openspec/ strategy/ v3/(3 文件) architecture/(v2)
    │   ├── audit/(summary/plan/README/_tasks/_pr/13 模块子目录)
    │   ├── plans/(3 文件)
    │   └── release/(48-hour/readiness/goal-contract/completion-audit)
    ├── legacy-root-roadmaps/      ← 根目录 ROADMAP / PRODUCT_ROADMAP
    └── legacy-root-docs/          ← 早期"AI法务智能体系统"年代文档
```

### A6 一致性 Gate 通过情况

| Gate | 命令 | 结果 |
|---|---|---|
| 文档失效链接（主干） | `grep -rE "docs/openspec\|docs/strategy\|docs/audit/_tasks\|..." docs/standards docs/release/README.md PROJECT_STATUS.md` | ✅ 所有活跃主干文档已修正 |
| Worktree inventory | `python3 scripts/release-worktree-inventory.py --json --fail-on-unknown` | ✅ unknown=0 |
| Evidence 脱敏扫描 | `bash scripts/release-evidence-secret-scan.sh` | ✅ PASS |
| 发布清单 | `node scripts/validate-commercial-delivery-checklist.cjs` | ✅ 9 criteria OK |
| 发布 lane | `node scripts/validate-commercial-delivery-lanes.cjs` | ✅ 8 lanes OK |
| 外部资源需求 | `node scripts/validate-external-resource-requirements.cjs` | ✅ 7 resources OK |
| Product status 一致性 | `node scripts/validate-product-status-consistency.cjs` | ✅ OK（PRODUCT_ROADMAP 路径已更新至归档） |
| 商业 quick gate | `bash scripts/commercial-readiness-gate.sh --quick` | ✅ 文档段 OK（业务态仍为 not_ready — 等真机/沙箱证据） |
| 后端 H1 路径 | `pytest tests/test_chat.py tests/test_harness*.py` | ✅ 89 用例全过 |

### A6 还修复的脚本路径

| 脚本 | 旧路径 | 新路径 |
|---|---|---|
| `release/commercial-delivery-checklist.json` | openspec/* + release 4 个 + audit/_tasks/* | Spine + 归档 |
| `release/commercial-delivery-lanes.json` | 同上 | 同上 |
| `scripts/commercial-readiness-gate.sh` | audit/SUMMARY + openspec + release 4 个 | Spine + 归档 |
| `scripts/desktop-mvp-local-gate.sh` | audit/11a-desktop-mvp/* + release/readiness | archive/* |
| `scripts/release-worktree-inventory.py` | openspec/ strategy/ | + 5 Spine 文件 + standards/ |
| `scripts/validate-product-status-consistency.cjs` | plans/ release/4 个 audit/00-platform/ PRODUCT_ROADMAP | archive/* |

### 下一步（Phase B 开发）

按 [`docs/DEVELOPMENT_PLAN.md §4.1`](docs/DEVELOPMENT_PLAN.md) 顺序：
1. **T1** 图标体系收口（80 文件 `lucide-react` → `@/lib/icons`，4 批次 ≤20 文件）
2. **T2** Harness P0 — `policy_engine` 主路径接入（`_check_mcp_tool_policy` → `backend/src/harness/policy_engine.py`）
3. **T3** Harness P0 — `context_engine` vs `context_compressor` 二选一
4. **T4** UI/UX P0 — 假成功修复（按 `audit/ui-ux-audit-2026-05-08.md`）

---

## 2026-05-14 worktree `vigorous-wiles-5a3fb3` 清理与基线收尾（交接快照）

### 本轮目标
在动手开发前先做一次清理整理，**避免再次被错误引用过时/冗余/错误的信息和代码**，并把六层框架基线、品牌收口、设计规范单一真相源、三大核心文档索引一并落到位。

### 6 阶段 / 9 commits 时间线（领先 `origin/main` 9 个 commit）

| Phase | 内容 | Commits |
|---|---|---|
| **1. 并行审计** | 全仓代码/分支/文档/规范/可继承收益四线并行扫描 | （审计产出，无单独 commit） |
| **2.1 CAMEL 剥离** | 移除 CAMEL-AI 残留 import / 死引用 | `248735c0` |
| **2.2 死文件清理** | 6 个无引用前端页面 / 本地 SQLite / .gitignore 补强 | `9d85e0af` |
| **2.3 jovial-greider 合并** | 六层框架基线 + AGENTS.md/AI-Review/Self-Heal/Evals + chat 主路径接 enforcement | `56137019` + `9b902494` |
| **2.4 peaceful-goodall 评估** | CREAO Slice 1 评估后**延后**合并（alembic 3-way head 冲突） | `bbcb04b6`（记录原因） |
| **3. 设计规范单一真相源** | 三大单一真相源澄清（AGENTS.md / DESIGN.md / standards/）+ 图标体系缺口 | `d8c07cf1` |
| **4. 三大核心文档索引** | `docs/01-core-docs.md`（需求/架构/开发计划，**索引非重复**） | `fdd060da` |
| **5. 品牌字符串收尾** | mock fixtures + collect_all + eval 残留品牌一次性收口 | `8597b1e2` |
| **6. 一致性验证** | 全部 Gate 复跑 / 89 测试通过 / 本交接报告 | （文档更新） |

### 一致性 Gate 通过情况（Phase 6）

| Gate | 命令 | 结果 |
|---|---|---|
| 品牌泄漏 | `rg "安心智能法律服务平台\|Anxin Smart Legal Services\|安心法律"` | ✅ No files found（仅保留 README 历史叙事 + nginx.conf 部署项 + 历史文档） |
| CAMEL 残留 | `rg "from camel\|import camel\|CamelModel\b"` | ✅ 仅 4 处 intentional 历史注释（schemas.py 兼容别名 / p16 / ci-pipeline / pyproject 注释） |
| 后端 H1 路径 | `pytest tests/test_chat.py tests/test_harness*.py` | ✅ 89 用例全过（chat 33 + harness 56） |
| 模块 import | `python -c "from src.api.routes import chat; from src.services import chat_service"` | ✅ 导入成功 |
| 发布清单 | `node scripts/validate-commercial-delivery-checklist.cjs` | ✅ 9 criteria OK |
| 发布 lane | `node scripts/validate-commercial-delivery-lanes.cjs` | ✅ 8 lanes OK |
| Worktree 卫生 | `python3 scripts/release-worktree-inventory.py --json --fail-on-unknown` | ✅ tracked_changes=0, unknown=0 |
| 密钥扫描 | `bash scripts/release-evidence-secret-scan.sh` | ✅ PASS |

### 本轮**未做**（明确延后给后续 PR）

| 项目 | 优先级 | 原因 | 计划 |
|---|---|---|---|
| peaceful-goodall（CREAO 自愈 Slice 1）合并 | P1 | alembic 3-head（028/030/044）+ 8 个非平凡修改依赖 | P0 policy_engine 统一收敛后单独 PR |
| `lucide-react` → `@/lib/icons` 80 文件迁移 | P1 | 47% 已迁移；剩余 80 文件需分批 | 每批 ≤ 20 文件 + `no-direct-lucide-import` lint |
| nginx.conf `anxinfawu.com` → `anxinai.com` | P1 | 涉及 DNS/证书切换，属 V3 P13 | 与 P13 域名切换一起做 |
| H1 followups: policy_engine / context_engine 主路径接入 | P0 | 已在 `docs/audit/harness/03-h1-followups.md` 登记 | 下一开发周期 |
| 全量 pytest（543+ 用例）+ 全栈 e2e | - | 本轮仅 H1 相关 89 用例 + gate 脚本通过；全量验证属常规 CI 范畴 | 推到 CI 流水线 |

### 后续"正式开发"路径

按 [docs/00-project-execution-map.md](docs/00-project-execution-map.md) §2 的 12 环节，**当前状态**：
- 环节 1-3（目标/需求/设计） **已冻结**（V3 scope 已合并）
- 环节 4（UI/UX）**进行中**，参见 [docs/audit/ui-ux-audit-2026-05-08.md](docs/audit/ui-ux-audit-2026-05-08.md)（原 plans/2026-05-13-ui-ux-optimization-roadmap.md 已合并入 `docs/DEVELOPMENT_PLAN.md`）
- 环节 5-7（架构/任务拆分/开发）**有基线**：六层框架 H0-O2 全部 ✅，可在 Harness 之上接续 P0/P1 followups
- 环节 8-12（测试/UI 验收/证据/门禁/试点）按 `docs/release/` 推进

**建议下一动作**：从 `docs/audit/harness/03-h1-followups.md` 选一个 P0（推荐 `policy_engine` 主路径接入，因 main 已有 `_check_mcp_tool_policy` 可融合）切单独 PR；CREAO Slice 1 在其后做。

---

## 2026-05-14 六层框架基线引入（Model/Harness/Context/Traces/Eval/Ops）

### 总体方向
从 `claude/jovial-greider-7843d2` 分支抽取并适配为单 commit `56137019`，把 Agent 能力拆成 Model / Harness / Context / Traces / Eval / Ops 六个可演化对象。本轮**不**重做模块审计，而是**纵向建能力**，让审计成为持续机制。详见 [docs/audit/harness/README.md](docs/audit/harness/README.md)。

### 落地清单

| # | 层 | 任务 | 关键产出 |
|---|----|------|---------|
| **H0** | Harness | 接入体检 | [docs/audit/harness/00-integration-matrix.md](docs/audit/harness/00-integration-matrix.md) |
| **H1** | Harness | 强制接入主路径 | [enforcement.py](backend/src/harness/enforcement.py) — `output_validator` 软→强；CRITICAL→拒发；FAIL→retry；异常→ERROR |
| **C1** | Context | 三层标准化 | [AGENTS.md](AGENTS.md) + [skills/_template/](skills/_template/) + [docs/context-architecture.md](docs/context-architecture.md) |
| **C2** | Context | 5 Agent → skill | [skills/agents/legal-advisor/](skills/agents/legal-advisor/) 完整示范 + 4 骨架 |
| **T1** | Traces | 落盘 + 聚类 | [trace_sink.py](backend/src/services/trace_sink.py) + [models/trace.py](backend/src/models/trace.py) — PII 8 类 scrub + cluster_id 稳定签名 |
| **T2** | Traces | trace→test | [trace_to_test/converter.py](backend/scripts/trace_to_test/converter.py) |
| **E1** | Eval | 金标准评测集 | [backend/evals/](backend/evals/) — 25 case + 4 维度打分 + baseline + PR Gate compare |
| **O1** | Ops | 4 reviewer gate | [.github/workflows/ai-review.yml](.github/workflows/ai-review.yml) + [CODEOWNERS](CODEOWNERS) |
| **O2** | Ops | 自愈闭环 | [self_heal/](backend/scripts/self_heal/) — severity + dispatcher + path safety + cron 骨架 |

### 关键质量提升

| 维度 | Before | After |
|------|--------|-------|
| Output Validator | CRITICAL 仍发原文，异常吞 debug | CRITICAL→拒发；异常→ERROR；FAIL→retry |
| Trace | 仅内存 | 持久化设计 + PII 8 类 scrub + cluster_id |
| Agent 评测 | 0 agent 级 eval | 25 case + baseline + PR Gate compare |
| PR Review | 仅 trufflehog | 4 reviewer 并行（code/security/dep/regression）+ CODEOWNERS |

### 测试覆盖
- 新增 `tests/test_harness_enforcement.py` 14 用例
- 新增 `tests/test_harness_policy_enforcement.py` 8 用例
- 新增 `tests/test_self_heal.py` 22 用例
- 新增 `tests/test_trace_to_test_converter.py` 5 用例
- 上述 49 + test_chat 6 全部通过

### 已知后续 P0/P1（详见 [03-h1-followups.md](docs/audit/harness/03-h1-followups.md)）
- [ ] **P0** policy_engine 真接入主路径 tool 调用（当前 main 已有 `_check_mcp_tool_policy`，需统一）
- [ ] **P0** context_engine vs context_compressor 二选一
- [ ] **P1** cost_tracker 本地 LLM 估算 + 用户配额阻断
- [ ] **P1** task_engine 扩展到合同/尽调/批量文档
- [ ] **P1** tool_registry 改造（与 C2 协同）
- [ ] **P2** capability_negotiator 统一桌面/前端/服务

### 已知设计规范执行缺口（P1 followup）

- **图标体系收口未完成**：DESIGN.md §4 Icon System 要求"全站唯一图标库 `lucide-react`，统一从 `@/lib/icons` 导入"，但当前仍有 80 个文件直接 `import { X } from 'lucide-react'`（vs 72 个文件已迁移至 `@/lib/icons`，约 47% 完成）。
  - **影响**：DESIGN.md §4 中定义的 5 档尺寸 / 5 种状态色 / 图标按钮 44px 触达区等规则无法稳定生效。
  - **计划**：作为 P1 followup 单独起 PR，分批迁移；每批 ≤ 20 文件 + lint 强制 `no-direct-lucide-import`。
- **DESIGN.md ↔ frontend-standard.md 关系澄清**：本轮已在两文件顶部交叉引用，并在 `docs/standards/README.md` 增加"三大单一真相源分工"说明（AGENTS.md / DESIGN.md / standards/）。

### 已审查但本轮不合并的分支
- `old-legal-services/claude/peaceful-goodall-d26ff1` — **CREAO 自愈闭环 Slice 1**（incidents 收集层）：18 文件 1666 行，含 alembic migration `028_incidents`、`incident_collector.py`、`/admin/incidents` UI 与 ErrorBoundary 上报。**延后原因**：当前 alembic 已有双 head（`030_app_authorization` / `044_skill_connector_configs`），引入 `028_incidents` 需先 merge head，且依赖于 jovial-greider 中 `output_validator.py` 的 43 行追加（已在本轮合并）。**计划**：在 P0 followup（policy_engine 统一收敛）落地后，单独起 PR 合并 CREAO Slice 1，再继续 Slice 2 triage 与 Slice 3 GitHub Issue 化。

---

## 2026-05-12 V3 合并进商业交付主线

### 背景
独立演进的 `v3/main` 分支（远程 `v3` / 161 commits）已完整合并进 `codex/commercial-readiness-hardening-20260508` 集成分支 `integration/v3-merge-20260512`。商业交付 scope 从 V2「安心法务」正式扩展为 V3「安心智能助手」。

### 合并规模
- 891 文件 / +132,433 行 / −15,139 行
- 735 个 staged 文件进 merge commit `a446429e`
- 合并策略：`git merge --no-commit --no-ff v3/main`，逐区解决 26 个冲突
- 备份 tag：`backup/pre-v3-merge-20260512`（指向 pre-merge HEAD `7aa87e59`）

### V3 新增能力进商业 scope
- 10 个 user-facing persona（流程/市场/获客/内容/跨境电商/安心助理/法律/合同/尽调/财税）
- 61 个 v3 API（agent_tasks / im_pairing / app_authorizations / skills / fetch / personas / 9 persona 子路由 / rag_ingest / rag_kg / rag_query / client_errors）
- 异步任务编排（TaskOrchestrator + Celery + `agent_tasks` 表）
- IM 通道（飞书真 + 5 渠道占位 + 24h 配对授权 + LocalProvider 沙箱）
- OAuth 框架（5 provider + Fernet 加密 token_store）
- Skills 运行时（watchdog 热加载 + docx/xlsx/pptx/pdf 4 office skill）
- FetchService 4 层抓取门面 + 法律 5 源 + 电商源
- 多模态 RAG（MinerU + 跨模态 KG + VLM + Dashboard）
- 可观测性（Sentry + Prometheus + Grafana + 5 端 GHA workflow）
- 安全加固（P16 SSRF / 飞书签名 / webhook replay Redis SETNX fail-closed / CVE 升级）

### 合并后验证
- `backend/src/api/routes/__init__.py` 626 路由全量 import OK
- `frontend tsc --noEmit` 0 error
- 核心回归 12 tests passed（`test_auth_roles_permissions` + `test_contract_review_workflow`）
- 全量 backend pytest：`1766 passed / 25 failed / 1 skipped`（vs v3/main 原始 59 failed / 37 errors，实际改善）
- 25 failed 归因：~15 V3 pre-existing 实现与测试脱节（`FetchRequest.wait_for_selector`、`ContentDirectorAgent.manifest()` 等），~8 需要真 Postgres:5433 / Redis:6379 服务，~2 合并融合需要小修

### 合并融合关键决策
- 后端路由 `__init__.py`：合并 54 个路由（V2 53 + V3 新增）
- esign/payments webhook：保留 HEAD 的官方验签（微信 v3 RSA + 支付宝 RSA2 + e签宝/法大大 HMAC），采用 v3 的 `WebhookSecurity.verify` async 签名
- metrics：保留 HEAD webhook metrics + 追加 V3 P19-A `prometheus_client` 业务暴露 + `/metrics/business` 端点
- health：采用 v3 P19-A `HealthChecker` 聚合器（liveness/readiness/detailed 三层）
- webhook_security：采用 v3 Redis SETNX + fail-closed replay cache（P16-C）
- config：合并 HEAD 严格 JWT 生产校验 + V3 新增 feishu/oauth/dingtalk/shopify/amazon/shopee/tiktok 凭据字段
- frontend App.tsx：保留 HEAD AdminLayout 静态 import + 挂 V3 IA 占位页 + V3 layout feature flag（`VITE_V3_NAV=true` 启用）
- mobile/mini-program：采用 v3 版（P17/P21 已重写基础层）

### 合并后立即待办
1. V3 pre-existing 测试失败修复（`FetchRequest` 字段补全、`manifest()` classmethod 补全等）
2. `backend/pyproject.toml` 锁定 `prometheus_client` / `sentry-sdk` / `watchdog` 版本
3. `scripts/commercial-readiness-gate.sh` 扩展 V3 新 scope 门禁
4. `README.md` + `docs/00-project-execution-map.md` 同步 V3 品牌和 10 persona 能力版图
5. 回填 `docs/v3/` 权威文档链接（ARCHITECTURE / AGENT_PERSONAS / CAPABILITY_MATRIX / ROADMAP / INTEGRATIONS / SKILLS_INVENTORY / V3_DELIVERY_SUMMARY / SECURITY_AUDIT / CI_PIPELINE 等 16 个）
6. 真实 sandbox 凭据到位后，按 `sandbox-evidence-runner.py` 补 61 个 v3 API 的 live contract smoke

### 不变的商业交付阻断项
- 支付/电签真实商户沙箱 7 天回归
- 桌面 signed/notarized installer + signed runtime 性能
- 移动真实 iOS/Android + DCloud 云打包
- 跨端连续会话真机
- 企业 Agent 治理 runtime evidence
- 仓库历史 `.env` 真实密钥轮换 + Git 历史清理
- 前端 access_token/refresh_token 从 localStorage 迁出

---

## 2026-05-09 商业交付状态纠偏

当前目标不是“已有代码即可上线”，而是尽可能接近商业交付。最新事实源如下：

- **总体状态**：尚未达到商业交付完成态。`scripts/commercial-readiness-gate.sh --quick` 仍按预期失败，剩余阻断为 release docs not ready、支付沙箱、电签沙箱、桌面 runtime smoke、移动/小程序真机 smoke、企业 Agent 治理 runtime evidence pending。
- **桌面优先**：后续功能开发先聚焦桌面端本地可执行能力与治理门禁；移动端/小程序随后按 uni-app 统一端路线推进。
- **桌面 MVP 11a**：窗口 chrome、Quick Query、文件拖入 SQLCipher 离线队列、WebView drop、工作站配置/配置档 CRUD、运行状态 SQLCipher `app_settings` 镜像、Keychain 进程内 key cache、PrivacyContext 对齐、远控 host safe-probe 控制面已有代码/浏览器/本地门禁证据；仍缺 signed packaged runtime、macOS/Windows 截图/视频、快捷键 P95 < 200ms、托盘 drop P95 < 500ms、真实 local model、真实 approved connector 和真机远控证据。
- **桌面同步 11b**：Rust-owned SQLCipher/keyring、本地/unsigned release packaged-profile smoke、packaged-binary sync code smoke、unsigned release loopback push/pull/conflict/retry 和跨设备续接代码级 rehearsal 已有；仍缺 signed/notarized packaged-profile、signed runtime 性能、共享预发后端 transcript、交互式 conflict/human-intervention UI transcript 和真机跨设备连续会话。
- **移动/小程序路线**：旧 `mobile/` Expo 与 `mini-program/` Taro 目录作为 legacy/回归参考保留；新移动端和小程序能力优先进入 `apps/uni-mobile/`，当前 uni-app base smoke 已通过 H5/微信小程序构建，但 DCloud App 云打包/签名、真实 iOS/Android、交互式微信开发者工具和共享预发账号证据仍缺。
- **外部 API 策略**：支付、电签、LLM/embedding、MCP/Skills connector 等先保留 sandbox/live runner、contract test、env manifest 和脱敏 artifact 槽位；真实密钥、商户后台、签名身份和真机由外部输入后再联调。
- **后端启动/登录可靠性**：PostgreSQL 旧库缺 `users.department` 等登录查询列时，启动兼容层已覆盖用户登录相关增量列；`init_db()` 失败现在会阻止 API 启动，不再带着坏 schema 继续运行到登录阶段才报错。

---

## 2026-04-16 V2 架构升级启动

### 总体方向
本次升级是产品架构层面的三大根本性变革，详见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)（原 architecture-v2.md 内容已合并入新 Spine）：

1. **双客户端分离** — 需求方（C端）与服务方（B端律师律所）独立客户端
2. **三态运行模式** — 本地/混合/云端，各自独立的数据边界与功能边界
3. **订阅商业化** — 非本地模式需订阅，建立可持续商业模型

### Phase 1 — 已完成 ✅
- [x] 架构升级规划文档（原 `docs/architecture-v2.md`，2026-05-14 已合并入 `docs/ARCHITECTURE.md`，源文档归档至 `docs/archive/legacy-spine-sources/architecture/`）
- [x] README / PROJECT_STATUS / MEMORY 同步更新
- [x] User 表新增 `primary_client` 字段 + 自动迁移 + 老用户推断
- [x] 后端 API 返回 `primary_client`（register/me）
- [x] 前端路由拆分 `/pro/*` 服务方端 + `/pro/login` 独立入口
- [x] Login.tsx 按 `?role=provider` 分流注册类型 + 登录后按身份路由
- [x] ModeGate 组件（4 种门控策略：any/hybrid_or_cloud/cloud_only/local_ok_with_download）
- [x] 舆情/知识库/找律师/IM 包裹 ModeGate

### Phase 2 — 已完成 ✅
- [x] ProLayout 服务方端独立布局（侧边栏：工作台/案件/合同/案源/消息/工具/认证/账单）
- [x] Subscription 模型扩展（client_type/allowed_modes/features_override/trial_ends_at）
- [x] BillingPlan 新增 client_type 字段
- [x] SubscriptionService V2 鉴权方法（get_effective_features/can_access_feature/can_use_mode/create_trial）
- [x] database.py 自动补齐所有 V2 新增字段

### Phase 3 — 已完成 ✅
- [x] 订阅 V2 API（/billing/v2/features, /v2/can-access, /v2/can-use-mode, /v2/trial）
- [x] Pricing 页双端 Tab 切换（个人/企业 vs 律师/律所）
- [x] PrivacyContext 模式切换与订阅联动（requestModeSwitch 检查订阅）
- [x] OfflineResourceManager 离线资源管理组件（7 个资源包分类下载）

### Phase 4 — 已完成 ✅
- [x] 案源市场 MVP（CaseRequest + LawyerBid 模型 + 8 个 API：发布/浏览/投标/接受/评价）
- [x] 利益冲突检查（ConflictCheckService，投标时自动扫描历史案件当事人）
- [x] 律所内部分级（案件列表按角色过滤：合伙人看全部/律师看自己的）
- [x] 订阅价值感可视化（ValueDashboard 组件）

### Phase 5 — 已完成 ✅
- [x] V2 订阅购买 API（/billing/v2/subscribe，连接支付系统，年付 8 折）
- [x] 老用户 V2 迁移引导（V2MigrationGuide 组件，按用户类型定制引导）
- [x] 合规审计日志增强（export_audit_report 方法 + /admin/audit-logs/export API）

### 完成度统计
- **Phase 1-5 共计 45+ 子任务全部完成**
- V2 架构核心基础设施已就绪；**不等于商业可上线完成态**
- 后续为商业交付收口：支付/电签真实沙箱、桌面 signed runtime、跨模式/跨设备数据同步、企业 Agent 治理 runtime、移动/小程序真机与 uni-app 发布链路

### 关键决策
- **账号体系不分离**：同一 users 表，通过 `primary_client` 字段区分默认客户端
- **律师可兼作需求方用户**：支持同账号切换两端（类似淘宝/千牛）
- **本地模式的核心卖点**：数据绝对不出设备，律所安全合规首选
- **订阅与客户端独立计费**：兼职律师可同时订阅 Pro + Lawyer Pro

### Phase 完成后的预期效果
- 律师打开 App 看到的是获客/案源/账单，用户看到的是咨询/找律师
- 高保密律所可纯本地模式运行，零数据泄露
- 普通用户有试用期，订阅后享受完整 AI 能力
- 舆情等需要云端的功能在本地模式下给出明确引导

---

## 2026-04-03 安全审计（进行中）

### 当前仍待处理的高风险问题
- [ ] 仓库中存在已提交的真实密钥：`.env` 已被 Git 跟踪，需立即轮换并评估历史清理
- [ ] 邮箱验证码 / 密码重置码仍为 6 位数字，且重置链路未绑定额外上下文
- [ ] Redis 故障时虽已改本地回退，但认证安全边界仍未做到严格 fail-closed
- [ ] 支付与电子签 Webhook 仍未切到各渠道官方签名协议
- [ ] 前端将 access token / refresh token 持久化到 `localStorage`
- [ ] LLM 配置接口缺少组织隔离，普通已登录用户可能看到不应暴露的模型配置
- [ ] LIC 抓取与 `sync` 目前仍是最小安全实现，后续还需继续做正式化增强

### 当前仍待处理的边界与设计遗留
- [ ] 匿名聊天创建接口公开，且单次返回双方 token，设计上允许单方模拟双边身份
- [ ] IM 仍存在 URL token 使用场景，尚未统一切到首包认证或短期 ticket
- [ ] 上传入口校验策略尚未统一到共享校验器
- [ ] 协作列表可见性、数据中心 org 维度、尽调缓存相关边界仍有继续细化空间
- [ ] CAPTCHA 目前主要覆盖登录/注册/忘记密码，重发验证码和重置密码等入口仍可继续统一
- [ ] 文档与实现需要持续同步，避免状态偏差再次出现

### 已收口的代表性问题
- [x] 协作编辑未鉴权 HTTP 备用接口已加登录和成员校验
- [x] 第二套协作 WebSocket 已改为 token 鉴权，不再信任 query `user_id/nickname`
- [x] 文档、知识库、案件归属校验已收口
- [x] RTC 参与者授权、IM 组织过滤已收口
- [x] LIC 任务状态和 WebSocket 进度流已按 owner 限制
- [x] 公开健康检查端点已收敛为最小化 `status` 响应
- [x] OA 集成接口已绑定当前登录用户，不能再代他人发通知或发起审批
- [x] MCP 工具列表已限制为平台管理员可见
- [x] AI 旁听记录已按发起人校验
- [x] 获客分析、订阅报表、功能开关、审批列表/详情、舆情、尽调详情/报告等核心越权面已收口

### 已完成沉淀
- [x] 审计记录已写入 `docs/archive/legacy-root-docs/2026-04-03-security-audit-record.md`
- [x] 整改矩阵已写入 `docs/archive/legacy-root-docs/2026-04-03-security-remediation-matrix.md`
- [x] OMX working memory / project memory 已记录当前发现与后续检查方向

### 已开始落地（Batch 1）
- [x] 协作主 WebSocket 改为首包 token 鉴权，移除 query 参数身份信任
- [x] 协作 HTTP 备用接口增加登录与成员校验
- [x] 协作会话详情/成员/快照/提交接口增加成员访问限制
- [x] 文档详情/更新/删除/版本历史增加组织归属校验
- [x] 知识库详情/文档/搜索/导出等接口开始传递 user/org 上下文到服务层
- [x] 案件关联文档增加文档组织归属校验

### 已开始落地（Batch 2）
- [x] AI 旁听记录按发起人校验读取与关联权限
- [x] 获客分析默认收口到当前组织，非平台管理员不可跨组织查询
- [x] 订阅创建与订阅报表增加组织范围限制
- [x] 数据中心列表按 owner 收口，存储接口限制用户可设置的 access_level
- [x] 审批列表与详情增加当前用户/当前组织范围过滤
- [x] 功能开关后台列表对 ORG_ADMIN 增加组织过滤
- [x] 舆情模块监控/记录/预警详情与操作接口增加组织归属校验

### 已开始落地（Batch 3）
- [x] `forgot-password` 增加频率限制
- [x] OAuth 回调增加 `state` 校验
- [x] Token 黑名单与限流在 Redis 不可用时改为本地回退控制
- [x] LIC 抓取接口增加 localhost/私网/保留地址拦截
- [x] `sync` 占位接口增加登录要求并统一返回 503
- [x] 新增认证/外联面安全回归：`backend/tests/test_auth_surface_hardening.py`

### 已开始落地（Batch 4）
- [x] RTC 房间创建 / 加入 token / 结束房间 / 房间列表增加 IM 参与者授权
- [x] IM 用户搜索默认限制为同组织用户
- [x] 新增实时面安全回归：`backend/tests/test_realtime_authorization_guards.py`

### 已开始落地（Batch 5）
- [x] 微信支付 / 支付宝 / 电签 webhook 增加基础签名校验
- [x] OA 审批发起人绑定当前登录用户
- [x] LIC 任务状态查询与 WebSocket 进度流增加 owner 校验
- [x] 新增外部入口安全回归：`backend/tests/test_external_surface_guards.py`

### 已开始落地（Batch 6）
- [x] 后端新增 Turnstile 验证能力
- [x] 登录 / 注册 / 忘记密码在开启 CAPTCHA 时要求 `captcha_token`
- [x] 登录页动态加载 Turnstile 并在敏感认证表单展示安全验证

### 已开始落地（Batch 7）
- [x] 支付 / 电签 webhook 升级为时间戳 + HMAC 校验，并增加简单防重放缓存
- [x] LIC 抓取支持显式域白名单 `LIC_ALLOWED_HOSTS`

### 已开始落地（Batch 8）
- [x] 审批通过 / 驳回要求当前有效审批人
- [x] 尽调详情 / 报告 / 趋势 / 快照对比按所有权收口
- [x] 尽调缓存状态与缓存失效对普通用户默认关闭
- [x] 律师评价增加重复评价拦截
- [x] `sync` 升级为按用户和设备隔离的最小安全实现

### 已开始落地（Batch 9）
- [x] OA 通知接口忽略客户端 `user_id`，统一绑定当前登录用户
- [x] MCP 工具列表改为仅平台管理员可见
- [x] 公网 `/health` 响应锁定为最小化 `status` 字段

### 当前遗留问题摘要
- [ ] 需要完成真实密钥轮换和 Git 历史治理
- [ ] 需要把重置密码从 6 位码升级为高熵单次 token
- [ ] 需要决定 Redis 故障下认证链路的更严格策略
- [ ] 需要把 webhook 从通用 HMAC 升级到各渠道官方协议
- [ ] 需要处理前端 token 存储方案
- [ ] 需要补齐 LLM 配置组织隔离、匿名聊天、URL token 和统一上传校验

### 已验证
- [x] 后端回归：`pytest backend/tests/test_security_authorization_guards.py backend/tests/test_case_service.py -q`
- [x] 后端回归：`pytest backend/tests/test_chat.py -q`
- [x] 后端回归：`pytest backend/tests/test_security_authorization_guards.py backend/tests/test_case_service.py backend/tests/test_chat.py backend/tests/test_sentiment.py -q`
- [x] 后端回归：`pytest backend/tests/test_auth_surface_hardening.py backend/tests/test_auth_roles_permissions.py backend/tests/test_security_authorization_guards.py backend/tests/test_case_service.py backend/tests/test_chat.py backend/tests/test_sentiment.py -q`
- [x] 后端回归：`pytest backend/tests/test_realtime_authorization_guards.py backend/tests/test_auth_surface_hardening.py backend/tests/test_security_authorization_guards.py backend/tests/test_chat.py -q`
- [x] 后端回归：`pytest backend/tests/test_external_surface_guards.py -q`
- [x] 后端回归：`pytest backend/tests/test_auth_surface_hardening.py backend/tests/test_auth_roles_permissions.py -q`
- [x] 后端回归：`pytest backend/tests/test_external_surface_guards.py -q`（重放/白名单增强后复验）
- [x] 后端回归：`pytest backend/tests/test_external_surface_guards.py -q`（OA/MCP/health 收口后复验）
- [x] 后端回归：`pytest backend/tests/test_business_authorization_guards.py backend/tests/test_review_authorization_api.py -q`
- [x] 后端回归：`pytest backend/tests/test_sync_api_security.py backend/tests/test_auth_surface_hardening.py -q`
- [x] 前端构建：`cd frontend && npm run build`
- [x] 新增安全回归测试：`backend/tests/test_security_authorization_guards.py`
- [x] 新增安全回归测试：`backend/tests/test_auth_surface_hardening.py`
- [x] 新增安全回归测试：`backend/tests/test_realtime_authorization_guards.py`
- [x] 新增安全回归测试：`backend/tests/test_external_surface_guards.py`
- [x] 当前已知非阻断告警：前端构建仍有 `lottie-web` 的 `eval` 告警，和本轮安全收口无直接关联

---

## 当前版本

**v0.9.8-beta** | 预计v1.0上线：2026-06-30（详见ROADMAP.md）

## 2026-04-03 ~ 2026-04-04 质量收口（已完成）

### 本轮验证结果
- [x] 后端全量回归：`cd backend && ./.venv/bin/pytest -q tests` → `172 passed`
- [x] 后端核心授权/业务回归：`42/42`（认证/合同/文档/找律师/任务/评价/旁听助手）
- [x] 前端静态检查：`cd frontend && npm run lint`
- [x] 前端构建验证：`cd frontend && npm run build`
- [x] 前端多角色访问控制 E2E：`6/6`
- [x] 前端核心业务动作 E2E：`8/8`
- [x] 云端迁移核验：`docker compose exec -T backend alembic current` → `027_experience_patterns (head)`
- [x] 云端表结构核验：`experience_patterns` 已在 `legal_agent_db` 创建成功
- [x] 云端公网暴露核验：`80/443` 之外的 `8001/5433/6379/6333/6334/7474/7687/9000/9001` 已收口
- [x] 云端域名与 HTTPS 核验：`https://anxinai.com`、`https://www.anxinai.com` 返回 `200`

### 本轮已完成的高优先级真实化修复
- [x] 前端默认 API 地址改为相对 `/api/v1`，避免绕过代理导致本地登录/联调失败
- [x] 业务页与后台页补齐 feature / token 守卫，降低“直接输 URL 仍可访问”的偏差
- [x] `ClientPortal` 移除伪造案件/文档/账单，改为真实接入态空状态
- [x] `TemplateGallery` 取消假模板 fallback，模板接口失败时改为真实空状态
- [x] AI 文书编辑器改为真正受控编辑，不再写死 demo 文书
- [x] 律师入驻 Step 2 改为真实图片 URL 提交认证资料
- [x] 团队管理改为真实后端链路：团队创建/编辑/删除、负责人指定、成员添加/移除、成员列表展示
- [x] `/documents` 恢复为真实受保护路由，文档库“我的文档 → AI 分析”用户路径重新可达
- [x] 本地私有助手改为“复制安装说明 + 我已完成部署”的诚实流程
- [x] 两步验证入口升级为安全状态摘要 + 说明弹窗 + 邮箱验证下一步动作
- [x] 云端私有助手入口补充“查看企业方案”真实 CTA

### 本轮后端稳定性修复
- [x] 非法 `conversation_id` / `case_id` 不再直接击穿数据库 UUID 类型层
- [x] 聊天 / 案件详情错误语义统一回到真实 4xx 响应
- [x] `sentiment_service` / `case_service` / `graph_service` 等模块补齐测试替身与资源回收入口
- [x] 进化系统、记忆系统、缓存服务补齐兼容层，旧测试与新实现不再长期分叉
- [x] Neo4j 图数据库在测试环境下显式降级，清除第三方 driver 析构 warning

### 本轮生产部署收口
- [x] 阿里云 ECS 项目目录确认：`/opt/anxin-ai`
- [x] Compose 生产拓扑收敛为“主机 Nginx + 容器回环绑定”
- [x] 前端容器绑定为 `127.0.0.1:3001 -> 80`
- [x] 后端容器绑定为 `127.0.0.1:8001 -> 8001`
- [x] PostgreSQL / Redis / Qdrant / Neo4j / MinIO 改为仅容器网络访问，不再暴露公网端口
- [x] 主机 Nginx 上游切换为前端 `127.0.0.1:3001`、后端 `127.0.0.1:8001`
- [x] Certbot 已签发并接入 `anxinai.com` 与 `www.anxinai.com` 的 HTTPS
- [x] 生产环境变量已修正：`DEV_MODE=false`，JWT / PostgreSQL / Redis 密钥已轮换

### 当前剩余问题（已收敛为长尾）
- [ ] 浏览器 E2E 仍受当前开发机 Chromium 启动权限限制，无法完整执行真实 UI 自动化流程
- [ ] 仓库历史中的真实密钥轮换与 Git 历史清理尚未完成
- [ ] 前端 token 仍持久化于 `localStorage`
- [ ] 验证码 / 找回密码链路仍使用 6 位数字码，额外上下文绑定尚未完成
- [ ] 两步验证仍未接入真实短信 / TOTP 后端能力，当前仅为诚实接入态
- [ ] 云端私有助手仍为规划态入口，虽已补企业方案跳转，但尚未开放申请/开通
- [ ] 律师入驻仍未接入站内真实文件上传，仅支持图片 URL 提交认证资料
- [ ] 匿名聊天公开创建与 token 设计仍需重构
- [ ] e 签宝 / 法大大 / 部分支付与通知渠道仍为占位实现
- [ ] LiveKit 仍未纳入当前生产启用与验收范围，如需音视频需单独开放端口和完成回归

## 最近更新（2026-04-03 Sprint 5/6 + 全局质量加固）

### 自动化测试补强
- [x] 新增后端认证/权限测试：`backend/tests/test_auth_roles_permissions.py`
- [x] 新增后端合同业务流测试：`backend/tests/test_contract_review_workflow.py`
- [x] 新增后端找律师/任务 API 测试：`backend/tests/test_lawyer_matching_and_tasks_api.py`
- [x] 新增后端合同权限边界测试：`backend/tests/test_contract_authorization_api.py`
- [x] 新增后端评价授权测试：`backend/tests/test_review_authorization_api.py`
- [x] 新增后端文档授权测试：`backend/tests/test_document_authorization_api.py`
- [x] 新增后端旁听助手授权测试：`backend/tests/test_meeting_assistant_authorization_api.py`
- [x] 新增前端角色会话注入与 API/WebSocket mock 辅助：`frontend/e2e/helpers/session.ts`
- [x] 新增前端多角色访问控制 E2E：`frontend/e2e/role-access.spec.ts`
- [x] 新增前端核心业务动作 E2E：`frontend/e2e/business-actions.spec.ts`
- [x] 验证通过：后端新增 pytest 10/10、前端角色权限 E2E 桌面端 3/3 + 移动端 3/3
- [x] 验证通过：后端扩展回归 pytest 42/42（认证/合同业务/合同权限/文档/找律师/任务/评价/旁听助手）
- [x] 验证通过：前端核心业务动作 E2E 8/8（桌面端+移动端，含文档库分析）
- [x] 静态检查通过：`ruff check` + `eslint`

### 自动化测试当前覆盖边界
- [x] 认证安全边界：注册角色映射、重复失败锁定、受限接口权限校验
- [x] 合同核心业务：审查结果落库、风险等级计算、建议应用回写、高风险词补充
- [x] 合同权限边界：详情、审查、风险列表、建议应用、风险处理、保存、下载均按组织范围收口
- [x] 文档权限边界：文本创建、元数据更新、内容更新、删除、版本历史、AI 分析均有 API 级授权回归
- [x] 找律师后端链路：咨询创建、委托前置条件、委托状态更新
- [x] 找律师后端链路：接单大厅只暴露待接单咨询，接单成功后写入匹配律师与状态
- [x] 任务后端链路：`todo → in_progress → done` 状态流转校验
- [x] 评价后端链路：必须绑定真实咨询/委托，且评价人与律师关系一致
- [x] 评价后端链路：只有归属律师本人可以回复评价
- [x] 旁听助手后端链路：只有发起人本人可以复用/停止同一对话的旁听记录
- [x] 前端多角色交互：企业用户导航可见性、后台越权回退、过期 token 重定向
- [x] 前端关键动作流：找律师委托、任务推进、合同审查结果展示
- [x] 前端关键动作流：文档库入口恢复，可直接触发“我的文档”AI 分析
- [x] 移动端专属权限断言已补齐（协作页导航可见性、“更多”菜单后台权限）
- [x] 文档与项目状态文档已同步到当前收口结果，并补记遗留问题

### 一致性修正
- [x] 修复 `TaskService.transition_status()` 与前端任务状态枚举不一致问题
- [x] 兼容旧状态别名：`pending -> todo`、`completed -> done`
- [x] 修复 `TaskService.transition_status()`/`batch_update_status()` 组织过滤缺失问题，阻断跨组织任务状态流转

### 用户角色感知+认证引导系统
- [x] UserProfile 角色图标：emoji 全部替换为 lucide-react SVG 图标（遵循设计系统规范）
- [x] 13种角色中文映射 + SVG 图标（Shield/Settings/Building/Scale/User等）
- [x] 认证状态横幅：邮箱未验证/律师待认证/企业待认证/已认证/个人升级提示
- [x] 后端 UserResponse 新增 user_type 字段，/auth/me 返回完整用户类型

### 编辑器高级扩展
- [x] Callout 扩展：5种类型（信息/注意/风险提示/重要条款/修改说明）
- [x] Toggle 扩展：可折叠/展开内容块，自定义标题
- [x] DiffMark 扩展：合同修订对比高亮（新增/删除/修改三种样式）
- [x] Mention 扩展：@提及功能，标注团队成员审阅

### 安全加固（P0）
- [x] .env 从 git 追踪中移除（git rm --cached）
- [x] 创建 .env.example 安全模板（所有密钥替换为占位符）
- [x] MOCK 数据添加 DEV_MODE 环境开关防护（尽调/支付/电签）
- [x] console.log 调试输出清理（A2UI注释+Chat/History改为DEV条件输出）

### 记忆系统CRUD完善（P2）
- [x] 语义记忆 update/delete 实现（通过向量库删除+重新插入）
- [x] 情景记忆 update/delete 实现
- [x] MOCK律师数据标注TODO替换提示

---

## 更早的更新（2026-04-03 记忆系统全链路集成）

### 记忆系统 → 实际业务流程全链路集成
- [x] **Chat 对话流集成**（chat_service.py `_prepare_chat_context`）
  - 每次对话前自动注入用户法律画像 + 经验上下文到 system prompt
  - 用户消息自动缓冲到 MemoryLayer（Memobase flush 思路）
  - 经验引擎上下文注入：相关历史经验 + 置信度加权排序
- [x] **引文追踪 → 对话流集成**（chat_service.py `_finalize_response`）
  - 每条 AI 回复自动提取法律引文（法条/案号/司法解释）
  - 验证引文准确性 → 自动沉淀到知识图谱
- [x] **做梦机制 → 对话流集成**
  - 每次 `_finalize_response` 后 `record_activity(user_id, "chat_*")`
  - 累计 5 次活动 + 距上次 24h → 自动触发后台记忆巩固
- [x] **做梦机制 → 调查流程集成**（investigation_orchestrator.py `_save_investigation`）
  - 每次调查完成后 `record_activity(user_id, "investigation")`

### 集成后的完整闭环
```
用户发消息 → _prepare_chat_context
  ├→ memory_layer.build_enriched_context (画像+时效事件 注入 prompt)
  ├→ experience_engine.build_experience_context (经验 注入 prompt)
  └→ memory_layer.buffer_message (缓冲到记忆层)
        ↓
LLM 生成回复 → _finalize_response
  ├→ citation_tracker.track_and_enrich (提取引文 → 图谱沉淀)
  └→ auto_dream_engine.record_activity (做梦计数 +1)
        ↓
达到门控(24h+5次) → AutoDream 后台巩固
  → Orient → Gather → Consolidate → Prune
  → 用户画像演化 + 图谱扩充 + 缓存清理
```

## 最近更新（2026-04-03 记忆系统 + 自学习进化 + Token优化）

### 四层渐进式上下文压缩（灵感：Claude Code 四层压缩策略）
- [x] 新建 `backend/src/services/context_compressor.py` — 法律场景特化压缩器
  - Tier 1 MicroCompact (80%): 外科手术式清理旧工具输出，零API调用，法条/案号永远保留
  - Tier 2 AutoCompact (85%): LLM 驱动结构化摘要，保留用户纠正和法律引用
  - Tier 3 SessionCompact (92%): 持久化到记忆层后激进缩减
  - Tier 4 ReactiveCompact (98%): 最后手段纯截断
  - 压缩后保留 ~50K token 工作区

### 经验积累与持续学习引擎（灵感：Claude Code continuous-learning + AutoDream Phase 2）
- [x] 新建 `backend/src/services/experience_engine.py` — 五类模式自动检测
  - 检测类型：error_resolution / user_corrections / legal_patterns / workflow_optimizations / domain_knowledge
  - 置信度生命周期：创建(0.6) → 确认(+0.15) → 日常衰减(-0.005/天) → 矛盾降级(-0.3) → 淘汰(<0.3)
  - 会话结束自动提取（min 10条消息触发）
  - 经验上下文注入 prompt（相关经验 + 置信度加权排序）
  - 反馈闭环：confirm/contradict 端点持续优化经验准确性

### 新增 API 端点（8 个，累计 35+ 端点）
- `POST /context/compress` + `GET /context/compress/stats` — 上下文压缩
- `POST /experience/extract` — 从会话提取经验
- `GET /experience/search` — 搜索相关经验
- `POST /experience/{id}/confirm` + `POST /experience/{id}/contradict` — 经验反馈
- `GET /experience/stats` — 经验统计

### AutoDream 做梦机制（灵感：Claude Code autoDream）
- [x] 新建 `backend/src/services/auto_dream.py` — 后台记忆巩固引擎
  - 双门触发系统：时间门控(24h) + 活动门控(5次操作)
  - 四阶段巩固：Orient(扫描记忆现状) → Gather(收集近期信号) → Consolidate(巩固记忆) → Prune(修剪过期)
  - 信号识别：高风险模式、重复搜索企业、跨会话任务模式
  - 自动沉淀：调查发现 → 知识图谱实体、用户偏好 → 风险维度权重
  - 后台异步执行，不阻塞用户请求

### 分层记忆演化系统（融合 Mem0 + Memobase + OpenViking）
- [x] 新建 `backend/src/services/memory_layer.py` — 三级记忆 + L0/L1/L2 分层加载
  - **三级记忆**：User Memory(跨会话画像) + Session Memory(单次上下文) + Agent Memory(推理链)
  - **用户法律画像**：自动演化的结构化画像（企业类型/行业/法律需求/风险关注/交互模式）
  - **L0/L1/L2 上下文分层**：
    - L0(~10 token): 一句话摘要，快速筛选
    - L1(~500 token): 关键信息概要，用于决策
    - L2(完整): 原始内容，按需加载
  - **法律文档特化 L0**: 合同(类型+双方+日期)、案件(案号+案由)、法规(名称+生效)
  - **Buffer 批量处理**：缓冲消息达阈值后批量提取偏好（Memobase flush 思路）
  - **法律时效时间线**：合同到期、诉讼时效、法规变更等事件追踪
  - **增强上下文构建**：融合用户画像+会话记忆+时效事件，注入 system prompt

### 精确引文追踪系统（灵感：DeepTutor）
- [x] 新建 `backend/src/services/citation_tracker.py` — 法律引文提取与验证
  - 三类引文提取：法条引用(《XX法》第X条X款X项)、案号引用、司法解释引用
  - 引文验证：查向量知识库确认引文准确性
  - 引文关系图：共引关系自动建模
  - 图谱自动沉淀：引文实体+共引关系 → 知识图谱

### 新增 API 端点（7 个）
- [x] `GET /memory/status` — 记忆系统综合状态（做梦+画像+上下文预览）
- [x] `POST /memory/dream` — 手动触发做梦（记忆巩固）
- [x] `GET /memory/profile` — 获取用户法律画像
- [x] `GET /memory/context` — 获取增强上下文（注入 prompt）
- [x] `GET /memory/upcoming-events` — 法律时效事件查询
- [x] `POST /citations/extract` — 法律引文提取与追踪

### Sprint 5+6 推进（2026-04-03）

#### Sprint 2.3 法律语料基础设施
- [x] 创建 `backend/data/legal_corpus/` 目录结构（laws/interpretations/cases/templates）
- [x] 创建语料目录 README.md（数据格式、导入方式说明）

#### Sprint 5.1 编辑器高级扩展（补充 Diff + @提及）
- [x] `LegalExtensions.tsx` 新增 DiffMark 扩展（合同修订对比高亮：新增/删除/修改三色标注）
- [x] `LegalExtensions.tsx` 新增 Mention 扩展（@提及团队成员，不可编辑标签，user/team/role 三种类型）
- [x] 累计4个法律编辑器扩展：Callout + Toggle + DiffMark + Mention

#### Sprint 5.2 律所知识管理平台
- [x] 新建 `backend/src/services/knowledge_management.py`
  - 案例经验库：10大法律领域分类 + 6种案件结果标签
  - 经验搜索：关键词+分类+结果多维筛选
  - 智能推荐：根据当前任务推荐相关经验+模板+法条
  - 自定义模板管理：律所自有模板 CRUD
  - 知识沉淀：从合同审查结果自动提取可复用经验

#### Sprint 5.3 客户门户
- [x] 新建 `frontend/src/pages/ClientPortal.tsx`
  - 案件进度追踪（进度条+里程碑时间线，可展开详情）
  - 共享文档列表（律师分享的文件，支持下载）
  - 费用账单（汇总卡片+明细列表，已支付/待支付/处理中）
  - 在线沟通入口（待集成 IM）
- [x] 路由注册：`/client-portal`

#### Sprint 6.2 安全加固
- [x] 新建 `backend/src/core/security_config.py`
  - 数据分类分级（5级：公开/内部/机密/敏感/绝密）
  - 字段级数据分级映射（20+ 字段）
  - API 安全策略（CORS+限流+认证）
  - 敏感操作审计清单（11类操作）
  - 输入验证规则（SQL注入/XSS防护模式）
  - 密钥轮换策略

#### Sprint 6.3 部署配置
- [x] 新建 `nginx.conf` — 生产环境反向代理
  - HTTPS + SSL（TLS 1.2/1.3）
  - 安全头（X-Frame-Options, CSP, HSTS）
  - Gzip 压缩
  - API 限流（30r/s 通用，5r/s 认证）
  - WebSocket 代理（IM+协作+LiveKit）
  - SSE 支持（proxy_buffering off，300s 超时）
  - 静态资源缓存（1年，immutable）
  - 敏感路径屏蔽

#### 智能调查搜索引擎三级架构升级（2026-04-08）
- [x] **Phase 1: Crawl4AI 集成** — LLM 友好网页爬取
  - 新建 `crawl4ai_service.py`（250行）：自动 JS 渲染 + 反检测 + Markdown 输出
  - 延迟初始化（首次使用才加载），未安装时自动降级到 httpx
  - 并发控制（Semaphore）+ 缓存 + 结构化提取
  - pyproject.toml 新增 `crawl4ai>=0.4.0` 依赖
- [x] **Phase 2: SearXNG 集成** — 自建隐私搜索引擎
  - docker-compose.yml 新增 searxng 服务容器
  - 新建 `searxng/settings.yml`（Google+Bing+Baidu+DDG+Wikipedia 五引擎聚合）
  - web_search_service.py 新增 `_search_searxng()` 方法
  - config.py 新增 SEARXNG_ENABLED/URL/TIMEOUT/MAX_RESULTS 配置
- [x] **Phase 3: Open-WebSearch 集成** — 免费降级兜底
  - web_search_service.py 新增 `_search_open_websearch()` 方法
  - config.py 新增 OPEN_WEBSEARCH_ENABLED/URL/ENGINES/TIMEOUT 配置
  - 搜索链升级为四级：SearXNG → Tavily/Bing → Open-WebSearch → DuckDuckGo
- [x] **Phase 4: 搜索结果去重+质量评分**
  - 新建 `search_dedup_service.py`（200行）
  - URL 去重 + 标题相似度去重
  - 30+ 域名可信度分级（gov.cn=1.0, 法律平台=0.85, 媒体=0.7, 社交=0.3）
  - RRF 多源结果融合排序 + 质量加权

#### 智能调查核心优化：数据驱动风险评估（2026-04-08）
- [x] **新建 `risk_scoring_engine.py`** — 数据驱动五维风险评分引擎
  - 基于真实采集数据（执行案件/失信记录/行政处罚/裁判文书）计算风险分
  - LLM 估算仅作为补充（打 5-7 折，标注为"AI 估算"）
  - 每维输出：分数 + 标签 + 依据 + 数据来源 + 数据质量等级
  - 整体数据质量判定：real(≥3维真实) / public(≥3维公开) / estimated
- [x] **集成到 `quick_investigate()`** — 第七步"数据驱动风险重算"
  - 替代 LLM 直接输出的风险评分
  - 保留 LLM 的 risk_points 和 recommendations（合并去重）
- [x] **新增第四数据源：国家企业信用信息公示系统 (GSXT)**
  - `gsxt.gov.cn` 搜索接口，获取统一社会信用代码等权威工商数据
- [x] **前端数据质量透明度标识**
  - InvestigationOverview 显示数据质量徽章（真实数据/公开数据/AI估算）
  - InvestigationOverview 显示数据来源列表
  - SentimentAnalysis 根据数据质量动态显示描述文案

#### Sprint 6.1 监控基础设施
- [x] docker-compose.yml 新增 Prometheus + Grafana 服务容器
- [x] 创建 `monitoring/prometheus.yml`（4个抓取目标）
- [x] Grafana 数据源自动配置（provisioning）
- [x] 新建 `backend/src/api/routes/metrics.py` — Prometheus 拉取端点
- [x] 路由注册

#### 任务中心看板拖拽
- [x] Tasks.tsx 重写：HTML5 原生拖拽（零新依赖，乐观更新+失败回滚）
- [x] API 新增：`tasksApi.transition()` + `batchUpdate()` + `kanbanStats()`

#### 知识管理 API 路由
- [x] 新建 `backend/src/api/routes/knowledge_management.py`（11个端点）
- [x] 路由注册（`/knowledge-mgmt`）

### 参考项目研究成果
- ClawCode/autoDream → 做梦机制（四阶段记忆巩固）
- DeepTutor → 精确引文系统 + 双循环推理 + 增量知识图谱
- Mem0 → 三级记忆结构 + Graph Memory
- Memobase → 结构化用户画像 + 批量处理 + 事件时间线
- OpenViking → L0/L1/L2 上下文分层加载（token 成本降低 91%）
- BettaFish/MindSpider/MiroFish → 已在上一轮集成

## 最近更新（2026-04-02 Sprint 1: 合规基础 + 引用溯源 + 智能模板）

### AI内容标识合规（GB 45438-2025）
- [x] 新建 `backend/src/core/ai_labeling.py` — AI内容标识服务
  - 三级标识：显式文本、元数据、内容指纹
  - 支持4种内容类型（text/document/analysis/suggestion）
  - 文档导出自动添加GB 45438-2025合规声明
  - DOCX/PDF文件属性嵌入AI标识元数据
- [x] DOCX导出集成AI标识页脚声明

### 法律引用溯源服务
- [x] 新建 `backend/src/services/legal_citation.py` — 法条引用解析
  - 支持《法律名称》第XXX条（第X款/第X项）格式
  - 法律简称→全称映射（20+部核心法律）
  - 最高法司法解释引用识别
  - 国家法律法规数据库链接生成
  - 自动增强审查结果：为每个风险点附加结构化引用
- [x] 合同审查Agent集成引用溯源（review结果自动解析法条）

### 智能条件合同模板引擎
- [x] 新建 `backend/src/services/template_engine.py` — 模板渲染引擎
  - 条件分支评估（支持布尔/数值比较/字符串/包含判断）
  - 变量插值（{{variable}}语法，支持|money|date|percentage管道格式化）
  - 金额自动大写转换（number_to_chinese）
  - 当事方信息动态渲染
  - 条件条款过滤（根据用户选择动态包含/排除条款）
- [x] 预置买卖合同模板（15字段+12条件条款）
- [x] 预置房屋租赁合同模板（11字段+9条件条款）
- [x] 模板API三个端点：列表/详情/渲染

### 前端AI标识组件库
- [x] 新建 `frontend/src/components/ai/AILabel.tsx`
  - AIBadge：AI标识徽章（紫色，4种类型）
  - AIDisclaimer：AI免责声明（完整/紧凑两种模式）
  - LegalCitationCard：法条引用卡片（蓝色，可点击跳转）
  - CitationList：引用列表
  - MissingClausesAlert：缺失条款琥珀色警示面板

### 项目规划
- [x] 创建 ROADMAP.md — 3个月6个Sprint实施路线图
  - 基于行业深度分析（竞品研究+用户痛点+法规要求）
  - 6个Sprint覆盖：合规→RAG→双循环审查→电签支付→协作→上线

---

### Sprint 2: RAG知识检索 + 法律语料库（2026-04-03）
- [x] `legal_corpus_loader.py` — 民法典合同编25条+劳动合同法13条核心法条
- [x] `agent_rag_service.py` — Agent RAG增强服务（向量+关键词双模式）
- [x] 合同审查/文书起草Agent集成RAG前置检索
- [x] `TemplateWizard.tsx` — 前端模板向导（分步表单+条件字段+实时预览）
- [x] `legal_rag.py` — LightRAG 法律 Hybrid 检索服务（2026-04-03 补充）
  - 四种查询模式：local(精确法条) / global(主题概览) / hybrid(默认混合) / naive(降级向量)
  - 关键词倒排索引 + 向量语义检索(Qdrant) + 知识图谱关系推理(Neo4j)
  - RRF 多路结果融合排序（local 0.4 + global 0.3 + vector 0.3）
  - 增量索引：新法律文档自动切分条文并更新索引
  - Agent 适配：根据 agent_type 自动选择检索模式

### Sprint 3: 双循环审查架构 + 文书质量验证（2026-04-03）
- [x] `contract_investigator.py` — 合同调查Agent（要素提取+法条匹配）
- [x] `review_checker.py` — 审查验证Agent（法条准确性+覆盖完整性验证）
- [x] `document_validator.py` — 文书质量验证器（结构/内容/引用/格式多维检查）
- [x] `review_memory.py` — 审查记忆服务（经验保存+复用+薄弱环节分析）
- [x] Workforce DAG升级：合同审查改为三阶段管线（调查→审查→验证）
- [x] 文书起草集成质量验证：评分<50%自动补充修正
- [x] Agent总数从22个增至24个

---

## 更早的更新（2026-04-01 Phase 2 音视频通话 + 实时转录）

### LiveKit 音视频通话 — Phase 2
- [x] **LiveKit Server Docker 部署**：docker-compose.yml 新增 livekit-server 服务 + livekit.yaml 配置
- [x] **RTC 服务 (rtc_service.py)**：房间创建/删除/Token 签发，基于 livekit-api SDK
- [x] **RTC API 路由 (/api/v1/rtc)**：创建房间、获取 Token、结束通话、列出活跃房间
- [x] **转录 Agent (livekit_transcriber.py)**：LiveKit Agents 框架，阿里云 Paraformer 实时 ASR
  - 转录结果自动推送前端字幕 + 复用 Phase 1 AI 分析管道
- [x] **VoiceCall 组件**：LiveKitRoom + 音频渲染 + 参与者头像 + AI 助手面板
- [x] **VideoCall 组件**：LiveKitRoom + VideoConference + AI 助手浮动按钮
- [x] **TranscriptOverlay 组件**：实时字幕覆盖层，显示 ASR 转录文本
- [x] **ChatWindow 集成**：工具栏新增语音/视频通话按钮，点击创建房间并跳转
- [x] **前端路由**：`/call/voice/:roomName` 和 `/call/video/:roomName`

### 部署说明
```bash
# 启动 LiveKit Server
docker-compose up livekit-server

# 安装后端依赖
pip install livekit-api
pip install livekit-agents livekit-plugins-aliyun  # 可选：转录 Agent

# 安装前端依赖
npm install @livekit/components-react @livekit/components-styles livekit-client

# 启动转录 Agent（独立进程）
cd backend && python -m src.services.livekit_transcriber console

# .env 配置
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=anxin_livekit_key
LIVEKIT_API_SECRET=<见 livekit.yaml>
DASHSCOPE_API_KEY=<阿里云百炼 API Key>
```

---

## 更早的更新（2026-04-01 AI 旁听助手 Phase 1）

### AI 智能旁听助手 — Phase 1 文字对话
- [x] **MeetingRecord 数据模型**：会议记录表，存储对话文本、AI分析、纪要、待办事项
- [x] **meeting_assistant_service.py**：AI 旁听核心服务
  - 消息缓冲器：累积 3 条或 30 秒触发一次批量 LLM 分析
  - 实时法律要点提取：风险点/法律问题/事实陈述/决策事项分类
  - 对话结束生成结构化纪要（摘要/案情要素/法律分析/风险评估/建议/待办）
  - 复用已有 workforce Agent + RAG 知识库，零新外部依赖
- [x] **API 路由** `/api/v1/assistant`：start/stop/status/insights/summary/records/link-case
- [x] **IM 消息钩子**：im.py + anonymous_chat.py 消息广播后异步触发 AI 分析
- [x] **前端 AIAssistantPanel**：ChatWindow 右侧面板，实时显示法律分析卡片和纪要
- [x] **WebSocket 集成**：AI 分析结果通过 im_manager 实时推送给对话参与者

### Phase 2 规划（LiveKit 音视频）
- 待实施：LiveKit Server 部署 + LiveKit Agents(Python) ASR 管道
- 语音通话 + 实时转录 + AI 旁听分析
- 技术选型：LiveKit + 阿里云百炼 Paraformer ASR

---

## 更早的更新（2026-04-01 核心功能质量优化）

### 文件上传全链路增强
- [x] 后端 document_parser.py 新增 Excel (.xlsx/.xls)、CSV、PPTX 解析支持
- [x] 使用 openpyxl 解析 Excel（多工作表），python-pptx 解析 PPT（含表格文本）
- [x] 前端聊天文件选择器扩展：支持 PDF/Word/Excel/CSV/PPT/TXT/MD/图片（MultiModalInput + ChatInput + Chat.tsx）
- [x] 前端 useChatInput 增加文件大小校验（>10MB 拒绝）和扩展名白名单校验
- [x] 聊天区新增拖拽上传：拖入文件显示蒙层提示，松开自动附加并推断工作流
- [x] **核心**：聊天文件→AI 分析链路打通 — WebSocket 和 ChatService 在收到 document_id 时自动提取文档文本（extracted_text 或实时解析），截取前 8000 字拼接到用户消息中，AI Agent 可直接分析文件内容
- [x] 后端 config.py ALLOWED_FILE_EXTENSIONS 和 documents.py MIME 白名单同步扩展
- [x] 默认主题从 'system' 改为 'light'（深色模式需用户手动开启），增加 persist migrate 兼容存量用户

### 合同审查质量大幅提升
- [x] contract_reviewer.txt 提示词从56行扩充至200+行
- [x] 新增完整法律依据引用（民法典、劳动法、公司法等核心法条）
- [x] 新增三层系统化审查框架（效力审查→核心条款→特殊条款）
- [x] 新增合同类型专项审查指南（买卖/租赁/服务/劳动/投资）
- [x] 新增 missing_clauses 和 legal_basis 字段增强输出结构
- [x] 细化风险等级判断标准（关联具体法律后果）

### 合同/法律文书生成质量提升
- [x] document_drafter.txt 提示词从53行扩充至300+行
- [x] 新增完整的合同标准结构模板（14条+签署页+附件区）
- [x] 新增民事起诉状、律师函等专用格式模板
- [x] 定义严格的内容详实性要求（合同正文不少于3000字）
- [x] 规范编号体系：第X条→X.X→（1）三级编号
- [x] 新增法律文书排版规范和格式要求

### 文档协作编辑器全面升级
- [x] 新增 TipTap 扩展：Underline、TextAlign、TextStyle、Color、Highlight
- [x] 工具栏增强：字体颜色、高亮、文本对齐（左/中/右/两端）、下划线、删除线
- [x] 标题格式下拉选择器（正文/标题1/标题2/标题3）
- [x] 颜色选择器组件（12色快速选取）
- [x] A4页面模拟布局（210mm×297mm，标准页边距）
- [x] 缩放控制（50%-200%）
- [x] 打印功能（专业法律文书打印样式，宋体/1.8行距）
- [x] 快捷键支持（Ctrl+S保存、Ctrl+P打印）
- [x] 图标系统修正：Bold/Italic/Heading等编辑器图标使用正确的lucide-react图标

### 合同审查Agent代码增强
- [x] 新增合同类型专项审查方法 `_get_type_specific_guide()`，覆盖8类合同
- [x] 审查提示词构建增强：要求至少5维度分析、必须引用法律依据、补充missing_clauses
- [x] JSON解析增强：支持```json包裹格式，增加missing_clauses/legal_basis字段兼容
- [x] quick_review方法升级为结构化JSON输出

### 文书起草Agent代码增强
- [x] 新增文书类型结构指南 `_get_structure_guide()`，覆盖合同/诉讼/函件/法律意见
- [x] 起草提示词增强：要求合同不少于3000字、至少10条款、完整签署区
- [x] draft_contract方法增加结构指南和编号体系要求

### DOCX/PDF导出专业化
- [x] DOCX导出：A4纸张、标准页边距(上下2.54cm/左右3.17cm)
- [x] 标题排版：小二号(18pt)黑体居中、条款四号(14pt)黑体、正文小四号(12pt)宋体
- [x] 正文两端对齐、首行缩进2字符、1.5倍行距
- [x] Markdown智能解析：自动识别标题/条款/签署区/分隔线
- [x] PDF导出同步升级排版标准

### Slash命令系统（借鉴docmost）
- [x] 新建 SlashCommandExtension.tsx，18个命令覆盖基本格式+法律文书两大类
- [x] 法律文书专用命令：合同标题区、甲乙方信息、鉴于条款、标准条款、违约责任、争议解决、不可抗力、保密条款、签署区、附件列表
- [x] 输入"/"弹出命令面板，支持关键词搜索、方向键/Enter选择
- [x] 集成到CollaborativeEditor主编辑器

### 前后端数据打通
- [x] 合同审查服务返回 missing_clauses 字段，风险保存合并 legal_basis
- [x] 流式审查新增 missing_clauses、key_terms 事件类型
- [x] 快速审查 prompt 要求引用法律依据和缺失条款
- [x] 文档生成 API prompt 升级为完整起草规范
- [x] 前端审查页新增法律依据蓝色标签 + 缺失条款琥珀色警示面板

### 文档库编辑器 Slash 命令
- [x] Markdown 编辑器支持 "/" 快捷插入（12个法律文书模块）
- [x] 方向键/Enter选择、Esc取消、关键词搜索

### Bug修复
- [x] 修复 AdminConfig.tsx 缺失的 Smartphone 图标
- [x] 修复 Chat.tsx 重复 accept 属性的TS错误
- [x] 补充 icons.ts 缺失的 Play、Square、Video、PhoneOff 映射

---

## 更早的更新（2026-04-01 安全纵深防御 + 功能开关机制）

### 功能开关机制
- [x] 后端 config.py 新增 4 个开关：EMAIL_VERIFY_ENABLED / SMS_ENABLED / OAUTH_WECHAT_ENABLED / OAUTH_ALIPAY_ENABLED
- [x] 邮箱验证默认关闭（EMAIL_VERIFY_ENABLED=False），关闭时注册自动标记 email_verified=True
- [x] OAuth 端点受开关保护，未启用时返回 404
- [x] 后端 GET /auth/features 公开端点供前端查询开关状态
- [x] 前端 Login.tsx 根据开关动态显示微信/支付宝登录按钮
- [x] 前端注册流程：开关关闭时注册后自动登录，开启后跳转验证页
- [x] AdminConfig 安全配置 Tab 新增认证功能开关面板（4 个开关的 UI 控制）

### 安全纵深防御
- [x] 安全响应头：X-Content-Type-Options / X-Frame-Options / X-XSS-Protection / Referrer-Policy / HSTS(生产)
- [x] 文件上传白名单：扩展名 + MIME 类型双重校验（pdf/doc/docx/txt/md/xlsx/xls/csv）
- [x] 匿名聊天加固：消息长度 4096 上限 + 30条/分钟频率限制 + HTML 转义防 XSS
- [x] 验证码端点频率限制：verify-email 10次/5分钟、reset-password 10次/5分钟

---

## 更早的更新（2026-03-31 安全加固 + 认证体系升级）

### 安全加固 — 生产上线标准
- [x] 路由认证加固：contracts/llm/datacenter/documents/chat/collaboration/compliance 全部强制认证
- [x] LLM 配置路由：读取需登录，写入/删除需管理员权限
- [x] 集成 Webhook：添加 X-Integration-Key 密钥校验
- [x] CORS 收紧：allow_headers 改为具体列表

### 认证体系升级
- [x] 邮箱验证完整流程已启用（注册→验证码→通过才能登录）
- [x] 阿里云邮件推送 email_service.py（DirectMail SDK）
- [x] 阿里云短信服务 sms_service.py（Dysmsapi SDK，注册/登录/密码重置）
- [x] OAuth 微信+支付宝代码就绪（填入 AppID/Secret 即可启用）

### 用户类型与权限分层
- [x] 注册四类身份：个人用户/企业用户/律师/律所机构
- [x] 初始权限：个人→individual_user，企业→enterprise_user，律师/律所→viewer（待认证）
- [x] 企业内部分权：org_admin→dept_admin→enterprise_user→member
- [x] 审批流预留：approvals + integrations webhook OA 集成

### 后台管理增强
- [x] AdminConfig 新增短信服务和邮件服务配置 Tab
- [x] OAuth 配置添加官方文档链接

---

## 更早的更新（2026-03-31 续）

### 找律师 — AI 核心能力实现
- [x] 新建 `lawyer_matching_service.py`：AI 案情分析 + 自动脱敏 + 领域识别 + 风险评估 + 法律要素提取
- [x] 文本脱敏引擎：手机号/身份证/邮箱/银行卡/中文姓名/地址/公司名 正则清洗
- [x] 法律领域自动识别：10 大领域关键词匹配 + 置信度评分
- [x] 智能律师匹配算法：领域匹配(40%) + 评分(25%) + 活跃度(20%) + 紧急加权
- [x] LLM 增强分析：调用大模型生成专业匿名案情摘要（失败降级到规则引擎）
- [x] 升级 `create_consultation` 路由：接入 AI 分析服务替代原有占位逻辑
- [x] 升级 `list_lawyers` 路由：支持按领域智能匹配排序

### 合规自检 — 报告生成与 AI 增强
- [x] 新建 `compliance_service.py`：合规报告生成 + AI 增强整改建议 + 历史对比
- [x] HTML 报告模板：评分卡片 + 风险明细表格 + 整改建议列表
- [x] AI 增强整改建议：调用 LLM 为不合规项生成专业整改建议
- [x] 新增 `/compliance-check/report` 端点：生成完整 HTML 报告
- [x] 新增 `/compliance-check/compare` 端点：对比两次检查结果

### 任务中心 — 看板操作增强
- [x] 任务状态机：定义合法状态转换规则（pending→in_progress→completed 等）
- [x] 看板拖拽批量更新：`batch_update_status()` 支持多任务同时状态变更
- [x] 看板统计：`get_kanban_stats()` 各状态任务数量统计
- [x] 新增 `/tasks/{id}/transition` 端点：带校验的状态转换
- [x] 新增 `/tasks/batch-update` 端点：看板拖拽批量操作
- [x] 新增 `/tasks/kanban/stats` 端点：看板统计数据

## 最近更新（2026-03-31）

### 知识图谱 Canvas 文本渲染性能优化
- [x] 新增 `textMeasureCache.ts` 文本测量缓存工具：measureAndCache（宽度缓存）、truncateToWidth（像素级智能截断，替代朴素 slice）、setFontIfChanged（字体指纹比对，避免每帧重复 ctx.font 赋值）、LRU 淘汰防内存泄漏
- [x] 改造 `ForceGraphCanvas.tsx` 2D 渲染回调（nodeCanvasObject / linkCanvasObject）使用缓存，消除 60fps×N 节点的重复 measureText 和字体切换开销
- [x] 改造 `KnowledgeGraphExplorer.tsx` 2D 节点渲染使用缓存，中英文混排标签截断从字符计数升级为像素宽度二分查找
- [x] 借鉴 pretext "预处理+缓存"架构思想，不引入外部依赖，轻量实现

### AI 生成管线性能分析与优化规划
- [x] 深度分析 [chenglou/pretext](https://github.com/chenglou/pretext) 项目架构，验证"几百倍性能提升"属实（Chrome 468x，Safari 1,296x）
- [x] 完成当前 AI 生成管线全链路瓶颈诊断（多 Agent 串行阻塞、3 次串行 LLM、无对话历史等 8 项问题）
- [x] 输出技术分析文档：`docs/archive/legacy-root-docs/2026-03-31-pretext-technical-analysis.md`
- [x] 输出优化方案文档：`docs/archive/legacy-root-docs/2026-03-31-ai-generation-pipeline-performance-plan.md`
- [x] P0 小步落地（第一批）：`LLMService` 默认配置 TTL 缓存（60s）+ Agent 热路径统一自愈入口，避免 `chat/stream_chat` 重复回库
- [x] P0 小步落地（第一批）：聊天入口新增空消息校验，阻断无效请求进入多 Agent/LLM 链路
- [x] P0 小步落地（第二批）：单 Agent 流式链路与 WebSocket 单 Agent 回复补齐最近 10 条历史透传
- [x] 回归基线修复：补充 `backend/tests/test_llm_service_cache.py`，并修正 `backend/tests/test_chat.py` 中与当前接口契约不一致的断言与 mock
- [x] P0 小步落地（第三批）：多 Agent DAG 链路通过 `_task_history_var` contextvars 自动透传对话历史，覆盖 workforce + lifecycle manager 两条执行路径
- [x] P0 小步落地（第四批）：合并意图识别+需求分析为单次 LLM 调用（`CoordinatorAgent.analyze_and_classify`），复杂消息路径减少 1 次串行 LLM
- [x] P0 小步落地（第五批）：单 Agent 意图（11 种）走真流式 `stream_chat` 快速路径，绕过 `process_task` DAG，首 token 延迟从数十秒降到 ~2s
- [x] P1 动态 max_tokens：根据复杂度和意图自动分档（512/2048/4096），`stream_chat` 新增 `max_tokens` 参数
- [x] P1 Prompt 模板化管理：创建 `backend/src/prompts/` 模块（加载器 + 20 个 .txt 模板文件），17 个 Agent + Coordinator 改为文件加载，支持热更新和版本管理
- [x] P2 拆分 WebSocket handler：`websocket_chat` 从 1534 行降到 1040 行，提取 6 个独立 handler 模块（A2UI/工作台/Canvas/尽调/RAG/共享上下文）
- [x] P1 Prompt 模板化管理收尾：Coordinator `merged_intent_analysis` 抽取为模板文件，`requirement_analyst` 路径统一到 `agents/` 目录，全部 Agent + Coordinator prompt 均已模板化
- [x] P2 统一 Service 层消除三重重复：提取 `_ChatContext` + `_decide_route()` + `_prepare_chat_context()` + `_execute_due_diligence()` + `_execute_rag()` + `_finalize_response()` 共享编排层，`chat()` 和 `stream_chat()` 复用同一套路由决策和前后处理
- [x] P0 多 Agent DAG 真流式输出：新增 `LegalWorkforce.process_task_streaming()` 异步生成器，DAG 第一层主 Agent 使用 `stream_chat()` token-by-token 推送，其余 Agent 并行同步执行，后续层级增量追加；`ChatService.stream_chat()` 多 Agent 分支改用新方法消费事件流，首 token 延迟从"等全部完成"降到"主 Agent 开始输出"（~2s）

### 对话入口与研究模式统一
- [x] Chat 请求协议补充 `mode` 与 `knowledge_base_ids`，普通对话、快捷动作和知识库研究模式统一走同一聊天入口
- [x] 聊天输入区新增 `KnowledgeBaseSelector`，支持多知识库勾选、搜索、缓存、刷新和跳转知识库管理页
- [x] `/chat/history` 返回消息级 `sources`，知识库检索与尽调结果可在历史记录中保留来源信息
- [x] 知识库研究模式在 WebSocket 链路中支持按知识库范围检索并回传来源卡片

### 企业尽调强路由与 A2UI 闭环
- [x] 尽调服务新增企业调查意图识别、公司名抽取与结构化摘要格式化能力
- [x] `ChatService.chat` 与 `stream_chat` 新增企业调查强路由，识别到尽调请求后优先返回尽调结果，不再落回通用协调链路
- [x] A2UI 事件新增 `start_due_diligence`，表单提交后可直接返回状态卡、明细列表、风险提示与建议动作
- [x] 尽调意图词扩充到供应商/合作方/交易对手等业务表述，减少“公司调查”类请求漏判

### 右侧面板与工作台文档一体化
- [x] `RightPanel` 升级为 v7.1，正式采用“工作台 / 文档”双模式
- [x] 文档查看、归档、回看完整文档与新建对话入口统一收敛到右侧面板头部与工作台动作区
- [x] 文档列表去重与内容缓存增强，避免关闭文档后重复归档
- [x] 流式文书生成时对系统噪音进行清洗，右侧文档模式展示更稳定

### Chat 与导航交互优化
- [x] QuickActionsBar 支持基于使用频次的个性化排序，始终显示并在处理中置灰
- [x] 快捷动作彻底收敛为“填充输入框”的对话型触发，不再依赖聊天页内部跳转分支
- [x] 侧边栏默认展开，减少新会话和回访时的视图跳变
- [x] 用户面板新增“导航栏显示文字”开关，可切换顶栏动作是否展示文字标签
- [x] 后台管理布局改为静态引入，规避 Vite 动态加载偶发 `Failed to fetch module` 问题

### 知识图谱体验增强
- [x] `ForceGraphCanvas` 暴露 `resetView` / `zoomToFit` 句柄，页面工具栏可直接控制画布
- [x] 图谱 2D/3D 模式补齐自动旋转、标签开关、类型筛选联动
- [x] 图谱和探索器适配亮色 / 暗色主题，标签、连线、背景和光晕按主题切换

### 测试与验证资产补充
- [x] 新增尽调意图识别单测：`test_due_diligence_intent.py`
- [x] 新增尽调强路由单测：`test_chat_due_diligence_routing.py`
- [x] 新增 A2UI 尽调事件单测：`test_a2ui_due_diligence_event.py`
- [x] 前端新增右侧面板双模式 E2E：`frontend/e2e/right-panel.spec.ts`
- [x] 新增后端认证/权限测试：`backend/tests/test_auth_roles_permissions.py`
- [x] 新增后端合同业务测试：`backend/tests/test_contract_review_workflow.py`
- [x] 前端新增多角色访问控制 E2E：`frontend/e2e/role-access.spec.ts`
- [x] 前端新增核心业务动作 E2E：`frontend/e2e/business-actions.spec.ts`
- [x] 前端引入 `@playwright/test` 并补充本地配置：`frontend/playwright.local.config.ts`

## 最近更新（2026-03-28 ~ 03-29）

### 导航架构重构
- [x] 四大模块下拉菜单改为直达链接，各模块有独立左侧导航栏
- [x] 创建通用 `ModuleLayout` 组件（展开200px/收起56px）
- [x] 移除全屏下拉面板（Portal）和所有 hover/click 展开逻辑
- [x] AI 智能助手直达 `/chat`，智能协作→`/cases`，智能调查→`/due-diligence`，法律智库→`/knowledge-graph`

### Chat 页面优化
- [x] 三栏标题栏高度统一为 h-12（48px）
- [x] 添加可拖拽分隔条（对话列表↔聊天区、聊天区↔智能工作台）
- [x] 智能工作台整合文档功能（去掉独立文档Tab，统一面板）

### 后台管理重组
- [x] 15个菜单项重组为4个分组（用户与权限/系统运维/业务管理/安全与合规）
- [x] AdminLayout 侧边栏使用主题系统颜色，统一视觉规范

### 功能模块整合
- [x] 系统设置→后台管理（AI配置/安全设置/功能开关）
- [x] 审批中心+任务中心→任务中心
- [x] 后台管理入口迁移到用户面板（按权限显示）
- [x] 找律师+律师精英合并
- [x] 合同审查→合同管理，文档+工作台→在线协作
- [x] AI 智能助手中的后台功能（AI助手配置/私有LLM等）迁移到后台管理

### 登录页面优化
- [x] 去掉左侧纯色渐变背景，改为 bg-muted/50 适配深浅色
- [x] 添加几何圆环装饰元素和2个形象角色占位框

### 测试账号体系
- [x] 17个测试账号覆盖6大角色（平台管理/律所/律师/员工/企业/个人）
- [x] 统一使用 `@anxinai.com` 域名，简单密码格式

## 功能完成度

| 模块 | 前端 | 后端 | 状态 |
|------|------|------|------|
| AI 智能对话 | 98% | 92% | 可用（已支持知识库研究模式与来源回写） |
| 智能工作台 | 97% | 82% | 可用（工作台 / 文档双模式已落地） |
| 案件管理 | 90% | 95% | 可用 |
| 合同管理 | 85% | 90% | 可用 |
| 在线协作 | 80% | 70% | 基本可用 |
| 找律师 | 80% | 85% | 可用（AI脱敏+智能匹配已实现） |
| 合规自检 | 85% | 80% | 可用（报告生成+AI建议已实现） |
| 智能调查（尽职调查） | 96% | 92% | 可用（支持尽调强路由与 A2UI 表单闭环） |
| 司法资讯 | 80% | 70% | 已隐藏（v2.0启用） |
| 知识图谱 | 85% | 75% | 可用（2D/3D 控制与主题适配增强） |
| 任务中心 | 75% | 70% | 基本可用 |
| 后台管理 | 90% | 85% | 可用 |
| 登录/注册 | 95% | 95% | 可用 |

## 已知问题

1. `conversation_summaries` 表外键类型不匹配（VARCHAR vs UUID），`init_db` 的 `create_all` 会报错但已跳过
2. Qdrant 客户端版本（1.17）与服务端版本（1.12）不兼容，功能性警告
3. 部分页面在后端离线时显示加载错误（正常行为）

## P0 验证完成情况（2026-03-31）

### Alembic 迁移链验证 ✅
- 22 个迁移脚本链完整，无孤立/循环依赖
- 修复了 011/012 文档头与实际 down_revision 不匹配的问题
- 两个 011 文件（approval_chain + notification_preferences）命名冲突但链功能正确

### 后端单测 ✅ 14/14
- `test_due_diligence_intent.py` — 6 个测试全部通过
- `test_chat_due_diligence_routing.py` — 4 个测试全部通过
- `test_a2ui_due_diligence_event.py` — 2 个测试全部通过
- `test_a2ui_action_coverage.py` — 2 个测试全部通过（21 个 actionId 全覆盖）

### 前端 E2E 测试 ✅ 15/16
- 认证流程 4/4、导航结构 4/4、右侧面板 3/3、移动端 3/3 全部通过
- 仅 `新建对话` 间歇性超时（后端响应时序抖动，非代码缺陷）
- 修复了测试断言与 UI 文案不同步的问题（placeholder、nav selectors）

### 深色模式 ✅
- CSS 变量体系完整（浅色 / 深色双套 HSL 色阶）
- ThemeProvider 正确响应 system / dark / light 三种模式
- 主要页面（Chat、知识图谱等）均有 dark: 适配

### 移动端响应式 ✅
- Layout.tsx 使用 lg: (1024px) 断点正确切换桌面/移动布局
- 移动端底部 Tab 栏、顶部二级导航、侧边栏隐藏均正常
- Chat 页面 isMobile 状态与右面板/侧边栏联动正确

### 核心路由可用性 ✅
- `/chat` — AI 对话页正常（欢迎页 + 快捷操作 + 工作台面板）
- `/cases` — 案件管理正常（8 个案件 + 搜索 + 筛选）
- `/contracts` — 合同审查正常（风险评分 + 状态管理）
- `/due-diligence` — 智能调查正常（示例数据 + 五维风险评估）
- `/knowledge-graph` — 知识图谱正常（2D 力导图 + 工具栏）

### 其他修复
- 移除 api.ts 未使用的 `export default` 聚合导出，消除 Vite HMR 循环引用错误
- 前端控制台零错误（重启后验证）

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS + Radix UI |
| 后端 | FastAPI + SQLAlchemy 2.0 + Alembic |
| AI | 自研 Harness 层 (16+ Agent) + OpenAI + Anthropic |
| 数据库 | PostgreSQL + Redis + Qdrant + Neo4j |
| 部署 | Docker + GitHub Actions |

## 端口配置

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端（开发） | 3001 | Vite 开发服务器 |
| 后端（开发） | 8005 | 本地开发 API 服务 |
| 前端（生产） | 127.0.0.1:3001 | 仅宿主机 Nginx 回环访问 |
| 后端（生产） | 127.0.0.1:8001 | 仅宿主机 Nginx 回环访问 |
| PostgreSQL（生产） | 容器网络内 5432 | 不对公网暴露 |
| Redis（生产） | 容器网络内 6379 | 不对公网暴露 |
| Qdrant（生产） | 容器网络内 6333/6334 | 不对公网暴露 |
| Neo4j（生产） | 容器网络内 7474/7687 | 不对公网暴露 |

## 最新更新（2026-03-29 晚）

### P1 智能工作台深化（参考豆包/千问设计）
- [x] 已发送消息编辑重发：用户消息 hover 显示编辑图标，点击进入编辑模式，修改后重新发送（删除旧消息及后续回复）
- [x] 快捷技能栏重构：workflowConfig.ts 统一管理 12 个业务动作，豆包风格紧凑横排（快速咨询 / 合同审查 / 协作起草 / 合规检查 / 尽职调查 / 知识检索 + 更多），附件感知自动切换提示
- [x] 斜杠命令面板：从 workflowConfig 自动生成，按分类分组（核心法务/知识与检索/交付与协作），支持中英文模糊搜索
- [x] 文档管理增强（RightPanel v6）：文档快捷操作栏（生成摘要/翻译全文/AI润色/风险检查）、新建空白文档/合同模板、文档列表历史管理、保存/关闭文档
- [x] store 新增 documentList 文档列表状态管理
- [x] icons.ts 新增 FilePlus、Signal 图标

### 用户反馈迭代（2026-03-29 深夜）
- [x] 品牌欢迎页：千问风格 Logo + 标语 + 4 个能力卡片（合同审查/文书起草/合规检查/尽职调查），点击卡片填充输入框
- [x] 移除重复上传按钮：QuickActionsBar 去掉 "+" 号（输入框左侧已有回形针），只保留功能快捷入口
- [x] 需求确认交互增强（ClarificationBubble v2）：每个问题新增"自己输入"选项 + 自定义文本框 + 可切换重选 + 部分回答也可提交 + 引导提示优化
- [x] AI 生成文书自动推送到工作台：检测法律文书特征（条款/甲乙方/签署日期等），自动设置 Canvas 内容并打开右面板
- [x] 新建对话自动收起右面板：resetWorkspace 后同步 rightPanelOpen=false + chatWidth=100%

### LLM 切换（2026-03-29 下午）
- [x] 本地 LLM 服务（192.168.110.45:1234）不可达，切换到通义千问 DashScope 云端
- [x] `.env` 和数据库 `llm_configs` 表同步更新为 `qwen-plus` 模型
- [x] 对话功能验证通过（法律顾问 Agent 返回专业法律回答）

### Chat 页面优化
- [x] 三个拖拽分隔条样式统一（6px透明区域 + 1px居中线 + grip指示器）
- [x] 输入框高度自适应（拖拽调高时 textarea 跟随填满）
- [x] 输入区宽度自适应（移除 max-w-4xl 限制）
- [x] 附件和发送按钮锚定底部（self-end）

### 导航图标修复
- [x] 消息/任务中心改为图标+文字显示
- [x] Chat 侧边栏收起/展开用 ChevronLeft/ChevronRight 图标
- [x] 所有侧边栏宽度统一 220px/56px

## 最新更新（2026-03-29）

### 智能调查模块全面升级
- [x] "信息中心"更名为"智能调查"，提升为一级模块（直达 `/due-diligence`）
- [x] 司法资讯暂时隐藏，待 v2.0 版本迭代启用
- [x] 仪表板布局：左侧 8 模块导航 + 右侧动态内容区
- [x] 多 Agent 协同调查引擎：采集→交叉验证→辩论综合→报告编制 4 阶段工作流
- [x] 增强 SSE 协议：新增 stage/agent_start/agent_result/conflict/consensus 事件
- [x] 新增 7 个前端组件：InvestigationSidebar/Overview/Progress/SentimentDashboard/InteractiveGraph/ScenarioSimulation/InvestigationReport
- [x] 新增 4 个后端服务：InvestigationOrchestrator/ReportEngine/ScenarioSimulation/Investigation Model
- [x] 交互式关系图谱联动法律智库知识图谱
- [x] 风险场景推演（4 种预设场景 + 影响链可视化 + 雷达对比）
- [x] 调查报告引擎（IR→HTML/PDF，章节导航）
- [x] 修复子组件硬编码：RelationshipGraph 公司名、LegalCases 诉讼数、ComplianceReport 合规项
- [x] 后端新增 8 个 API 端点（协同流式调查/调查历史/报告/场景推演）

## 下一步计划（优先级排序，已按 2026-03-31 最新改动重排）

### P0 — 上线前必须 ✅ 全部通过（2026-04-01）
1. ~~Alembic 迁移验证~~ ✅ 25 个迁移脚本链完整，修复 022 编号冲突（重命名为 023_conversation_star）
2. ~~后端单测回归~~ ✅ 快速单测 11/11 通过（尽调意图/A2UI覆盖/LLM缓存），修复 test_chat_without_auth 断言适配安全加固
3. ~~深色模式+移动端复查~~ ✅ 亮/暗模式 CSS 变量正确切换，移动端(375px)/平板(768px)/桌面端渲染正常，零控制台错误
4. ~~核心路由可用性~~ ✅ 登录页正常渲染，未认证路由正确重定向到 /login

### P1 — 对话工作台闭环强化
5. ~~合规风控 / 法律检索 / 找律师 / 尽调 的后端意图识别与 A2UI 卡片输出稳定化~~ ✅ 新增 FIND_LAWYER 意图+关键词+A2UI配置，扩充合规/法律检索关键词，找律师强路由
6. ~~知识库研究模式增强来源引用、权限校验和空知识库提示~~ ✅ RAG sources 补充 content_snippet，_execute_rag 透传 user_id 权限校验，WebSocket RAG 调用补传 user_id
7. ~~工作台动作与消息流联动补全~~ ✅ 全栈完成：
   - WebSocket 通知 UI：重构 NotificationCenter 使用 Zustand Store（单一数据源），Layout 统一未读计数（移除独立 state+轮询），useIMWebSocket 增强通知 toast 弹窗
   - 文档版本历史：新建 VersionHistory 面板（时间线布局+恢复按钮），集成到 DocumentEditor 工具栏
   - 模板→工作流联动：新建 TemplateSelector（5 个内置法务模板），集成到 QuickActionsBar，选择后自动预填输入框
   - 语音对话 ASR：新建 useSpeechRecognition hook（Web Speech API, zh-CN, 自动停止），VoiceInputButton（录音脉冲+实时转写浮层），集成到 ChatInput 工具栏

### P2 — 体验优化
8. ~~全局样式规范统一~~ ✅ 已建立完整设计系统：`docs/design-system.md` 规范文档、index.css 新增语义状态色/AI色/动效令牌/阴影系统（亮暗双套）、tailwind.config.js 新增 success/warning/info/ai 语义色+排版体系+动效 token+AI 动画、design-tokens.ts 新增 aiStatus/modelSelector/searchBar/starButton Token
9. ~~对话历史搜索和收藏功能~~ ✅ 全栈完成：后端迁移+API+Service + 前端 ChatSidebar 新增搜索输入框（实时过滤）、全部/收藏 Tab 切换、收藏星标按钮
10. ~~多模型切换界面~~ ✅ 全栈完成：后端 model_id 支持+GET /chat/models + 前端 ModelSelector 组件（下拉选择器，显示提供商标签和默认标记）
11. ~~知识图谱性能优化~~ ✅ 前端 searchGraph API 新增 skip/entityType 分页参数、初始加载和搜索限制首批 30 节点加速首次渲染、后端已有分页+节点限制 API

## 设计参考文件

位置：`/Users/pengchengkeji/Desktop/安心智能助手-设计参考/`（37个截图）
- 豆包桌面端：左侧导航 + 文档处理 + 快捷技能栏
- 千问桌面端：深色/浅色模式 + 深度思考 + 文件上传标签

---

*最后更新: 2026-04-01*
