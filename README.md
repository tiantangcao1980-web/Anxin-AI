# 安心智能助手 (Anxin Smart Assistant)

> **面向中国成长型制造企业的全链路 AI 智能经营助理。** 一个 App 搞定 法务 / 财务 / 税务 / 合规 / 经营管理 / 调研获客 / 内容产出 / 出海跨境。

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Branch](https://img.shields.io/badge/branch-integration%2Fv3--merge--20260512-green.svg)]()
[![V3 P0-P7](https://img.shields.io/badge/V3-P0--P7%20%E2%9C%85-success)]()

---

## 🧭 当前权威导航

| 入口 | 用途 |
|---|---|
| [docs/00-project-execution-map.md](docs/00-project-execution-map.md) | **当前权威导航总入口**（任务起点） |
| [docs/standards/](docs/standards/) | 13 份开发规范（命名 / 文档 / Git / 代码 / API / DB / 前端 / 后端 / 测试 / 安全） |
| [docs/v3/](docs/v3/) | V3 智能助手实施细节（架构 / 路线图 / 10 personas） |
| [docs/openspec/](docs/openspec/) | 平台合同 + 商业交付 + 测试规范 |
| [docs/audit/](docs/audit/) | 当前执行计划 + 12 域审计 + 16 个 TASK |
| [docs/release/](docs/release/) | 发布证据 + 回滚预案 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南 + 新人第一周清单 |
| [SECURITY.md](SECURITY.md) | 安全策略 + 漏洞报告流程 |
| [CHANGELOG.md](CHANGELOG.md) | 变更日志 |

---

## 📌 产品定位

**目标用户**：中国成长型制造企业（中小为主）的老板 / 高管 / 行政 / 财务 / 法务兼岗人员，以及为他们服务的律师、税务师、财务顾问。

**核心价值**：
- 🛡 **合规经营** — 法律 / 财税 / 合规 / 经营管理一站式 AI 辅助
- 📈 **增长获客** — 市场研究 / 获客 / 内容产出 / 数据驱动决策
- 🌍 **出海跨境** — 海外选品 / 供应链 / 跨境合规 / 多语言运营
- 🎯 **综合协调** — 多 persona 协同 + 桌面/移动 远控

**与通用 AI 助手的差异**：行业领域专业化 + 桌面工作站 + 本地隐私 + 中国合规深度。

---

## 🚀 V3 已交付（P0-P7 主体骨架，2026-04-27）

> **31 v3 commits / 61 个 v3 API endpoint / 100 测试文件 / 543+ pytest**

| 阶段 | 交付 | 状态 |
|---|---|---|
| **P0** 品牌升级 | 原"安心法务"v1/v2 升级为"安心智能助手"V3 | ✅ |
| **P1** IA + 后端骨架 | 10 personas 侧边栏 + 后端 3 核心模块 + 6 篇核心文档 | ✅ |
| **P2** 异步任务 MVP | `TaskOrchestrator` + Celery + 8 个 endpoint | ✅ |
| **P3** IM 通道 + 沙箱 | 飞书 IM 真实装 + 4 占位适配器 + 配对授权 24h + Sandbox LocalProvider | ✅ |
| **P4** OAuth 应用授权 | 通用框架 + 5 provider（飞书/钉钉/Notion/Shopify/Amazon SP）+ KMS 加密 token | ✅ |
| **P5** Skills 运行时 | `skill_registry` + `skill_executor` + 4 office skill（docx/xlsx/pptx/pdf） | ✅ |
| **P6** 信息获取栈 | FetchService 4 层（HTTP / crawl4ai / HeadlessX / 官方 API） + 5 法律源 + 5 电商源 | ✅ |
| **P7** 5 个业务 persona | 流程管家 / 市场研究员 / 获客猎手 / 内容总监 / 跨境电商助手 | ✅ |

详见 [docs/v3/v3-delivery-summary.md](docs/v3/v3-delivery-summary.md)。

### V3 进行中与排期

- 🚧 **P8** baseline 打磨 + 健康度 + 前端集成 + 文档同步
- 🔜 **P9** 5 法务 persona 上层包装（21 个 specialized agent 已就绪）
- 🔜 **P10** 知识库新版（RAG-Anything + MinerU 多模态）
- 🔜 **P11** 团队协作 / 多租户 / RBAC 可视化
- 🔜 **P12** 5 personas × 三端 E2E 全覆盖
- 🔜 **P13** 切换到 `anxinassistant.com` 域名

---

## 🧠 10 Personas（智能体阵列）

| 编号 | Persona | 业务域 | 状态 |
|---|---|---|---|
| 🎯 | **安心助理** | 综合协调（意图识别 / 多 persona 编排） | ✅ |
| ⚖️ | **法律顾问** | 合规经营 — 法律咨询 / 风险评估 | 🚧 |
| 📄 | **合同管家** | 合规经营 — 合同审查 / 起草 / 生命周期 | 🚧 |
| 🔍 | **尽调专家** | 合规经营 — 企业 / 供应商尽调 | 🚧 |
| 💰 | **财税顾问** | 合规经营 — 财务 / 税务 / 合规 | 🚧 |
| 📋 | **流程管家** | 综合协调 — OKR / 周报 / 会议纪要 | ✅ |
| 📊 | **市场研究员** | 增长获客 — 行业 / 竞品 / DeepResearch | ✅ |
| 🎯 | **获客猎手** | 增长获客 — Lead Scoring / 邮件 / 报价 | ✅ |
| ✍️ | **内容总监** | 增长获客 — 公众号 / 短视频脚本 / 海报 | ✅ |
| 🌍 | **跨境电商助手** | 出海跨境 — 选品 / 验厂 / AI 议价 / VAT | ✅ |

详见 [docs/v3/agent-personas.md](docs/v3/agent-personas.md)。

---

## 🏗 多端架构

```
┌────────────────────────────────────────────────────────────┐
│         桌面工作站（Tauri 2 + Rust）                         │
│  系统托盘 · 全局快捷键 · 本地 LLM · SQLCipher 加密 · 远控     │
├────────────────────────────────────────────────────────────┤
│   移动端（Expo RN）  ·  UniApp 跨端  ·  微信小程序（Taro）    │
│   桌面远控配对授权 · 离线缓存 · 推送通知 · 生物识别            │
├────────────────────────────────────────────────────────────┤
│         Web 端（React 18 + Vite + Tailwind）                │
│  10 personas 工作台 · 知识库 · 协作编辑 · 后台管理 (18 页)   │
├────────────────────────────────────────────────────────────┤
│         API 层（FastAPI · 75 路由 · 61 个 v3 endpoint）      │
│  双客户端（需求方 / 服务方）· 三态模式（本地/混合/云端）       │
│  六层校验：subscription + role + permission + risk + privacy + device │
├────────────────────────────────────────────────────────────┤
│         智能体层（22 personas + 21 specialized agents）      │
│  AgentManager · Team · Worker · Harness 治理 · MCP 协议      │
├────────────────────────────────────────────────────────────┤
│         数据层                                               │
│  PostgreSQL · Redis · Qdrant · Neo4j · MinIO · SQLCipher    │
└────────────────────────────────────────────────────────────┘
```

详见 [docs/v3/architecture.md](docs/v3/architecture.md) + [docs/architecture-v2.md](docs/architecture-v2.md)。

---

## 🛠 技术栈

| 层 | 选型 |
|---|---|
| **后端** | Python 3.11+ · FastAPI · SQLAlchemy 2.0 async · Pydantic 2 · Alembic |
| **AI** | OpenAI / Anthropic / 通义 / 混元 / DeepSeek / Ollama · CAMEL-AI · MCP |
| **向量 / 图** | Qdrant 1.12 · Neo4j 5.15 |
| **任务 / 缓存** | Celery · Redis 7 |
| **对象存储** | MinIO（S3 兼容） |
| **Web 前端** | React 18 · Vite 7 · TypeScript 5 · Tailwind 3 · shadcn/Radix · Zustand · Tiptap |
| **桌面** | Tauri 2 · Rust (Edition 2021) · SQLCipher · OS Keyring |
| **移动** | Expo 52 · React Native 0.76（`mobile/`） + UniApp Vue3（`apps/uni-mobile/`） |
| **小程序** | Taro 3.6 + React |
| **音视频** | LiveKit |
| **可观测** | Sentry · Prometheus · Grafana · OpenTelemetry |
| **部署** | Docker Compose · Nginx · GitHub Actions |

---

## 🚀 快速开始

```bash
# 1. 克隆
git clone <repo-url>
cd anxin-smart-assistant

# 2. 初始化（依赖 + 数据库 + 配置）
make init

# 3. 启动全栈
make up

# 4. 健康检查
make health

# 5. 访问
# Web: http://localhost:3001
# API 文档: http://localhost:8001/docs
# Grafana: http://localhost:3000
```

**Windows 开发者**：见 [scripts/windows/](scripts/windows/)。

详细环境与命令见 [DEV_GUIDE.md](DEV_GUIDE.md) 与 [Makefile](Makefile)。

---

## 🧪 验证

```bash
# 后端
make verify-backend           # ruff + mypy + pytest

# 前端
make verify-frontend          # lint + tsc + vitest + build

# 桌面
cd desktop && cargo clippy --all-targets && cargo test

# 移动
cd mobile && npm run typecheck && npm run test

# 商业发布门禁
bash scripts/commercial-readiness-gate.sh --quick
```

完整测试体系见 [docs/standards/testing-standard.md](docs/standards/testing-standard.md)。

---

## 📐 开发规范

所有贡献必须遵守 [docs/standards/](docs/standards/) 的 13 份规范：

| 规范 | 内容 |
|---|---|
| naming-convention | 文件 / 目录 / 代码符号 / 分支 / env 命名 |
| documentation-standard | 文档分层、头部模板 |
| git-workflow | 分支策略 / PR / worktree |
| commit-convention | Conventional Commits + 中文描述 |
| code-style | 各语言通用风格 |
| api-design | REST / WS / SSE 设计 |
| backend-standard | FastAPI 三层架构 |
| database-standard | Schema / ORM / 迁移 / 多租户 |
| frontend-standard | React / RN / Taro / UniApp 四端 |
| testing-standard | 单元 / 集成 / E2E / AI 评测 |
| security-standard | 密钥 / 鉴权 / 注入 / 隐私 / 治理 |
| comment-convention | **中文注释规范**（强制） |
| review-checklist | PR 评审 10 大门 |

PR 提交前自查 [docs/standards/review-checklist.md](docs/standards/review-checklist.md)。

---

## 📜 项目历史

- **v1 / v2**："安心法务"，法律垂直 SaaS，曾上线 anxinfawu.com
- **v3**（当前）："安心智能助手"，全链路升级，目标域名 anxinassistant.com
- 详见 [docs/adr/001-v3-anxin-assistant-upgrade.md](docs/adr/001-v3-anxin-assistant-upgrade.md)

---

## 🤝 贡献

欢迎贡献。提交代码前阅读：

1. [CONTRIBUTING.md](CONTRIBUTING.md) — 贡献流程 + 新人第一周
2. [docs/standards/](docs/standards/) — 13 份开发规范
3. [docs/00-project-execution-map.md](docs/00-project-execution-map.md) — 权威导航

发现安全漏洞请按 [SECURITY.md](SECURITY.md) 流程报告。

---

## 📄 License

[Apache License 2.0](LICENSE)
