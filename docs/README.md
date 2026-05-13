# 安心智能助手 — 文档体系

> 本目录是项目所有文档的统一入口。请按下方分层阅读。

## 🧭 唯一权威导航

**[00-project-execution-map.md](./00-project-execution-map.md)** — 当前权威导航总入口（2026-05-12）

> 列出所有权威文件清单与 12 推进环节。开始任何任务先读这一份。

## 📚 文档分层

| 层级 | 目录 | 角色 | 权威级别 |
|---|---|---|---|
| **L1 战略** | [strategy/](./strategy/) | 产品定位与需求 | ⭐⭐⭐ |
| **L1 规范** | [openspec/](./openspec/) | 产品合同 / 商业交付 / 测试规范 | ⭐⭐⭐ |
| **L1 规范** | [standards/](./standards/) | 开发规范（命名/文档/Git/Commit/代码风格） | ⭐⭐⭐ |
| **L2 实施** | [v3/](./v3/) | V3 智能助手实施细节 | ⭐⭐⭐ |
| **L2 实施** | [audit/](./audit/) | 当前执行计划 + 12 域审计 + 16 TASK | ⭐⭐⭐ |
| **L2 实施** | [release/](./release/) | 发布证据 / 外部资源 / 回滚 | ⭐⭐⭐ |
| **L3 专题** | [architecture/](./architecture/) | 跨域架构设计 | ⭐⭐ |
| **L3 专题** | [desktop/](./desktop/) [mobile/](./mobile/) [design/](./design/) | 端侧工程 | ⭐⭐ |
| **L3 专题** | [plans/](./plans/) | 阶段性专题规划 | ⭐⭐ |
| **L3 决策** | [adr/](./adr/) | 架构决策记录 | ⭐⭐⭐ |
| **L4 参考** | [references/](./references/) | 外部对标与设计参考 | ⭐ |
| **L4 历史** | [archive/](./archive/) | 已归档历史文档 | ⭐ |
| **L4 跟踪** | [issues/](./issues/) | 变更日志与截图 | ⭐ |

## 🎯 不同角色阅读路径

### 新成员第一周

1. [../README.md](../README.md) — 项目门面
2. [00-project-execution-map.md](./00-project-execution-map.md) — 权威导航
3. [standards/](./standards/) — 5 份核心规范
4. [v3/v3-delivery-summary.md](./v3/v3-delivery-summary.md) — V3 一页纸
5. [audit/plan.md](./audit/plan.md) — 当前执行计划

### 产品经理 / 商务

1. [strategy/](./strategy/) — 产品定位
2. [openspec/00-intelligent-assistant-platform-spec.md](./openspec/00-intelligent-assistant-platform-spec.md) — 平台合同
3. [v3/agent-personas.md](./v3/agent-personas.md) — 10 personas 业务定位
4. [v3/capability-matrix.md](./v3/capability-matrix.md) — 能力矩阵

### 后端工程师

1. [v3/architecture.md](./v3/architecture.md) — 后端架构
2. [audit/_tasks/](./audit/_tasks/) — 当前任务
3. [standards/code-style.md](./standards/code-style.md) — 代码规范
4. [architecture/](./architecture/) — 架构专题

### 前端工程师

1. [v3/architecture.md](./v3/architecture.md) — 全栈架构
2. [../DESIGN.md](../DESIGN.md) — 设计唯一源
3. [design/](./design/) — 设计专题
4. [standards/code-style.md §2](./standards/code-style.md#2-typescript--react) — TS 规范

### 桌面 / 移动工程师

1. [desktop/](./desktop/) / [mobile/](./mobile/)
2. [audit/_tasks/task-11a-desktop-mvp.md](./audit/_tasks/task-11a-desktop-mvp.md) / [-11b-sync-engine.md](./audit/_tasks/task-11b-sync-engine.md) / [-11c-mobile-design.md](./audit/_tasks/task-11c-mobile-design.md)
3. [release/](./release/) — 桌面 / 移动 evidence 要求

### 发布 / 运维

1. [release/](./release/) — 发布证据
2. [release/commercial-delivery-readiness.md](./release/commercial-delivery-readiness.md) — Go/No-Go
3. [../SECURITY.md](../SECURITY.md) — 安全策略
4. [deployment-desktop.md](./deployment-desktop.md) / [nas-install-guide.md](./nas-install-guide.md) / [security-deploy-guide.md](./security-deploy-guide.md)

### 评审 / PR Reviewer

1. [standards/review-checklist.md](./standards/review-checklist.md) — 10 大评审门
2. [standards/code-style.md](./standards/code-style.md) — 代码标准
3. [standards/commit-convention.md](./standards/commit-convention.md) — Commit 规范

## 🚀 顶层文档

| 文件 | 主题 |
|---|---|
| [architecture-overview.md](./architecture-overview.md) | 全景架构总览 |
| [architecture-v2.md](./architecture-v2.md) | V2 架构升级规划（已实施） |
| [deployment-desktop.md](./deployment-desktop.md) | 桌面端部署 |
| [deployment-harness.md](./deployment-harness.md) | Harness Engineering 部署 |
| [nas-install-guide.md](./nas-install-guide.md) | NAS 私有化部署 |
| [security-deploy-guide.md](./security-deploy-guide.md) | 安全部署指南 |
| [hardware-appliance-protocol.md](./hardware-appliance-protocol.md) | 硬件设备协议 |
| [day3-deployment-checklist.md](./day3-deployment-checklist.md) | 2026-05-13 部署清单 |
| [demo-script.md](./demo-script.md) | 投资人演示脚本 |

## 📐 命名约定

- docs/ 内所有文件名：`kebab-case.md`
- 子目录：`kebab-case/`，禁止中文
- 顶层 markdown（仓库根）：`SCREAMING_CASE.md`

详见 [standards/naming-convention.md](./standards/naming-convention.md)。

## 🔧 维护

- 新增文档前先看 [standards/documentation-standard.md](./standards/documentation-standard.md)
- 新增子目录必须配 README.md 入口
- 文档归档至 [archive/](./archive/) 而非直接删除
- 重大架构变更必须写 ADR
