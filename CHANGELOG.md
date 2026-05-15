# 变更日志

> 本项目遵循 [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/) 与 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### Added — Governance & Plugin Marketplace（2026-05-14 / 15，9 轮升级）

**架构骨架**
- `.claude-plugin/marketplace.json` — 11 plugin（10 persona + builder-hub）+ 4 cookbook 注册表
- `plugins/` — 11 个 persona 插件目录：`anxin-assistant / legal-advisor / contract-steward / dd-expert / finance-tax-advisor / process-steward / market-researcher / lead-hunter / content-director / cross-border-ecom / builder-hub`
- 每 plugin 含 `plugin.json` + `CLAUDE.md` 执业画像 + `cold-start-interview` skill；共 **34 个 SKILL.md**（全部含治理 frontmatter）
- `managed-agent-cookbooks/` — 4 个无人值守 cookbook（regulation-monitor / contract-renewal-watcher / ar-aging-watcher / cross-border-pricing-radar）；**全部接入真实数据源**

**治理三层体系**
- `docs/governance/` — 6 份 doctrine：`README / SKILL-LIFECYCLE / AUTHZ-MODEL / DATA-BOUNDARY / AUDIT-LOG-SPEC / TRUST-LEVELS / HANDOVER`
- `policy/` — 7 份 yaml policy-as-code：`access-matrix / trust-levels / data-classification / jurisdiction-rules / tool-allowlist / pii-redaction / skill-lifecycle`
- `backend/src/services/governance/` — 15 个治理模块：`policy_loader / authz (PDP) / audit / data_classifier / tool_scope / trust / skill_lifecycle / deps / confirm_inbox / external_send_gate / shadow_runner / builder_hub_installer / realtime / connectors/{feishu,dingtalk,email}`

**治理后台**
- `backend/src/models/governance.py` — 3 张 ORM 表：`confirm_tickets / audit_events / shadow_runs`
- `backend/alembic/versions/045_add_governance_tables.py` — 表 migration
- `backend/src/api/routes/governance.py` — 13 个 API endpoint + 1 个 WebSocket `/api/v1/governance/ws`
- `backend/src/services/im_gateway/governed_sender.py` — IM 外发统一治理入口
- `backend/src/services/app_authorization/providers/amazon_sp_oauth.py` — Amazon SP-API LWA OAuth provider（已 `@register_provider`）
- `backend/src/services/task_orchestrator/managed_agents/` — 4 个 cookbook 真实数据源实现 + `audit_reconcile` + `confirm_expire` 周期任务 + `__init__` beat schedule

**治理 Dashboard 前端**
- `frontend/src/pages/admin/AdminGovernance{,Policy,Audit,Tickets,Revoked}.tsx` — 5 个治理后台页面
- `frontend/src/hooks/useGovernanceWS.ts` — 实时 WS hook（指数退避自动重连）
- `frontend/src/pages/admin/adminGovernanceModel.ts` — 共享纯函数模块

**Agent / Persona / Workforce 治理接入**
- `BaseLegalAgent.process_governed()` — 21+ specialized agent 全自动继承 PDP+审计能力（向后兼容）
- `BasePersonaAgent._call_specialized_governed()` — Persona→Specialized 调用链路治理；7 个调用点已迁移（legal_advisor × 4 / due_diligence_expert × 2 / contract_steward × 1）
- `Workforce.process_task_governed()` — DAG 编排入口治理包装；**10 个 service 调用点已迁移**（case / chat / contract / document / due_diligence × 6）
- `SkillExecutor.execute()` — `ExecutionContext.role/clearance/jurisdiction` 字段；调用前 PDP，向后兼容
- `DocumentGenerationService.generate(subject=...)` — 律师函/起诉状自动 L4，普通文书 L3

**校验 / 运维脚本**
- `scripts/governance-lint.py` — frontmatter / policy schema / scope / tool / jurisdiction / lifecycle 全校验
- `scripts/audit-replay.py` — 审计事件按条件重放 + fingerprint 自校
- `scripts/audit-reconcile.py` — JSONL↔DB 双向对账（4 类 incident 检测；可飞书告警；可 backfill）
- `scripts/access-matrix-diff.py` — PR 时 role×scope 变更可视化
- `scripts/claude-plugin-validate.py` — 11 plugin + 4 cookbook 结构校验
- `scripts/sync-plugins-to-backend.py` — `_plugin_index.py` 自动生成（CI 守门）
- `scripts/claude-orchestrate.py` + `scripts/deploy-managed-agent.sh` — managed agent 本地/云端部署

**CI**
- `.github/workflows/governance.yml` — 4 job：policy-and-plugin-lint / 治理 pytest（71 case）/ 治理 Vitest（24 case）/ audit-fingerprint-check

**测试覆盖**
- Backend pytest：47 个（authz / inbox+shadow / phase5 / agent-wrap / im-sender）
- Frontend Vitest：24 个（useGovernanceWS / adminGovernanceModel）

**顶层文档**
- `AI-ASSISTANT-PLAYBOOK.md` — 整体方法论（参考 Anthropic claude-for-legal / financial-services 移植）
- `CONNECTORS.md` — 100+ MCP 与第三方数据源目录
- `docs/governance/HANDOVER.md` — 合规团队操作手册（580 行，9 个日常情境）

### Added — 历史交付

- `docs/standards/` 规范体系（5 份核心：命名 / 文档 / Git / Commit / 代码风格 / 评审清单）
- 顶层 `CONTRIBUTING.md` 贡献指南
- 顶层 `SECURITY.md` 安全策略
- 顶层 `CHANGELOG.md`（本文件）
- 12 个 `docs/` 子目录 README 入口
- `scripts/windows/` Windows 启动器目录（统一 kebab-case 命名）

### Changed
- `docs/` 顶层 SCREAMING_CASE 文件名全部转 `kebab-case`
- `docs/v3/` SCREAMING_CASE → `kebab-case`
- `docs/audit/_tasks/TASK-*.md` → `task-*.md`
- `docs/audit/PLAN.md` / `SUMMARY.md` → 小写
- `docs/architecture/` snake_case → kebab-case
- `docs/references/` 中文目录名 → 英文 kebab-case
- 顶层 `.bat` 启动器迁移到 `scripts/windows/` 并统一 `kebab-case`
- 4 份顶层 markdown（README / PROJECT_STATUS / ROADMAP / PRODUCT_ROADMAP）头部加权威导航指针

### Removed
- `env.example.txt`（与 `.env.example` 重叠）
- 仓库根 `package.json` + `package-lock.json`（与 Makefile 重叠）
- `.env.template`（与 `.env.example` 重叠）
- 17 个前端孤儿组件（`dashboard/` `document-library/` + V2 未集成 4 个）
- 96 个旧分支（72 worktree-agent + 16 已合入语义分支 + 9 早期 claude/* + 3 整理后剩余 + 自身 worktree）
- 76 个 worktree（含 19 GB 临时目录）
- `desktop/target/` Rust 构建缓存（33 GB，已 gitignore 可重建）

### Documentation
- 历史日期文档归档至 `docs/archive/legacy-root-docs/`
- `docs/wiki/` 归档至 `docs/archive/wiki-snapshot-2026-05-06/`
- `docs/superpowers/` 归档至 `docs/archive/superpowers-implemented/`

---

## [v0.9.x] — V2 → V3 合并期（2026-04 至 2026-05）

### Added
- **V3 安心智能助手** 品牌升级（原"安心智能助手" → "安心智能助手"）
- **10 personas**：流程管家 / 市场研究员 / 获客猎手 / 内容总监 / 跨境电商助手 / 法律顾问 / 合同管家 / 尽调专家 / 财税顾问 / 安心助理
- **TaskOrchestrator + Celery** 异步任务编排
- **IM Gateway** 5 渠道适配器（飞书真实装 + 钉钉/企微/Slack/Telegram）+ 24h 配对授权
- **OAuth 应用授权框架** 5 provider（飞书/钉钉/Notion/Shopify/Amazon SP）
- **Skills 运行时** + 4 office skill（docx/xlsx/pptx/pdf）
- **FetchService 4 层** 信息获取栈（HTTP/crawl4ai/HeadlessX/官方 API）
- **法律数据源** 5 个 + **电商数据源** 5 个
- **企业智能体治理**（L0-L5 + 六层校验）
- **可观测性** 三端（Sentry + Prometheus + Grafana + 4 dashboard）
- **CI 流水线** 5 端 GHA workflow + nightly smoke
- 61 个 v3 API endpoint / 100 测试文件 / 543+ pytest

### Changed
- 品牌：安心法务 → 安心智能助手
- 项目定位：法务垂直 → 法/财/税/合规/增长/出海全链路
- 主分支：`integration/v3-merge-20260512` 承载 V2 + V3 合并

### Security
- JWT access token 内存化
- refresh token 切 HttpOnly Cookie
- LLM 配置组织隔离
- Local 模式 fail-closed 默认拒绝出站
- 多渠道 webhook 验签（微信 v3 / 支付宝 RSA2 / e签宝 / 法大大）

---

## [v0.x] — 早期开发（2026-03 之前）

详见 `docs/archive/legacy-root-docs/` 内 2026-03-* 文档。

---

## 维护说明

- 每个 PR 合入 main / integration 必须在 `[Unreleased]` 节加入条目
- 版本发布时把 `[Unreleased]` → `[vX.Y.Z]` 并新建空 `[Unreleased]`
- 分类：`Added` `Changed` `Deprecated` `Removed` `Fixed` `Security` `Documentation`
