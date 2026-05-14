# 变更日志

> 本项目遵循 [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/) 与 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### Added — 企业级 AI 平台底座（PR #3）

#### Skills 沙箱（T0-T4）
- `backend/src/services/skill_sandbox/` —— manifest 解析 / 信任分级 / 权限闸门 / 配额跟踪 / ed25519 签名校验
- 完整实装 `DockerProvider`：cap-drop=ALL / read-only / no-new-privileges / network=none / 资源限额
- `E2BProvider` / `CodexCloudProvider` 可配置 HTTP 骨架（lazy SDK）
- 新端点：`POST /api/v1/skills/{name}/sandbox-execute` · `POST /api/v1/skills/preview`
- 新端点：`/api/v1/skill-sandbox/quota/tenants/{id}` GET/PUT 配额管理

#### 企业内网集群（飞书 / 企业微信式）
- 6 张新表（部门 / 成员 / 用户组 / 岗位 / 角色绑定）+ Alembic 045
- materialized path 部门树 + 一人多部门 + 角色绑定向下继承
- `PermissionResolver` 六层权限解析 + 跨租户隔离
- 11 个 REST 端点：`/api/v1/enterprise/*`
- 回填脚本：`scripts/migrate-user-department.py`（幂等）

#### LDAP / IM 通讯录同步
- `LdapSyncService` + `Ldap3Client` + `InMemoryLdapClient`
- 飞书 / 钉钉 / 企业微信三家通讯录客户端（同一 LdapClient 协议）
- 守护进程：`scripts/ldap_sync_loop.py` · `scripts/im_directory_sync_loop.py`
- Helm CronJob：LDAP + IM（多 provider 数组）

#### OIDC SSO
- `core/oidc.py`：discovery + JWKS 缓存 + RS256 验签 + ±5min 时钟容忍
- 端点：`POST /api/v1/auth/oidc/callback` · `GET /api/v1/auth/oidc/metadata`
- 前端登录页"企业 SSO 登录"按钮 + `/login/oidc/callback` 回调页

#### 公开官网（marketing site）
- 11 个公开页面：Home / Features / Personas / Pricing / Security / About / Contact / Cases / Blog / Privacy / Terms
- `RootGate`：未登录 → `/site`，已登录 → `/chat`
- SEO：完整 meta + OG + Twitter Card + `useDocumentMeta` 按页切换
- `public/robots.txt` + `public/sitemap.xml`（11 URLs）

#### Admin Enterprise UI（4 个新 Tab）
- `DepartmentTreePanel`：递归部门树（折叠 / 选中 / 新建子部门 / 软删 / LDAP dry-run）
- `RoleBindingPanel`：授权 / 撤回 / 有效权限查询
- `SkillInstallDialog` + `SecureSkillInstallButton`：Skill 安装授权弹窗
- `SkillQuotaPanel`：T0-T4 当日使用量 + 进度条 + T2-T4 上限编辑

#### 私有化部署
- `deploy/enterprise-onprem/docker-compose.onprem.yml` + `.env.onprem.example`
- Helm chart `anxin-enterprise`：完整 templates + secret + NetworkPolicy
- 3 套 values 预设：`values-production.yaml` / `values-staging.yaml` / `values-airgap.yaml`
- 5 份运维手册：README / LDAP_SYNC / AIRGAP / BACKUP / SSO_SAML

#### 文档
- `docs/v3/skills-sandbox-design.md` —— Skills 沙箱完整设计
- `docs/v3/enterprise-cluster-design.md` —— 企业内网集群完整设计
- `docs/v3/security-whitepaper.md` —— 客户向安全架构白皮书
- `docs/v3/compliance-dengbao-mapping.md` —— 等保 2.0 + GB/T 35273 全条对照清单

#### 测试
- 后端：113 个新测试，全部通过；既有 74 个零回归
- 前端 `tsc --noEmit` 全绿
- preview 实测公开官网 + admin UI 视觉确认

### Added — 早前
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
