# 安心法务 — AI 智能法务平台

> 通过 AI 能力 + 一键触达律师，为律师、中小企业和个人提供专业、便捷的法律服务。

## 产品定位

**安心法务**是一个以 AI 为核心驱动的智能法务平台，致力于让每个人都能便捷地获得专业法律服务。

- **守护** — 为企业经营保驾护航，降低法律风险
- **放心** — 数据私有化部署，信息安全可控
- **专业** — 21 个专业 AI 智能体 + 一键匹配真人律师

## 🏗️ V2 架构（进行中）

本产品正在进行 V2 架构升级，核心变革：

### 双客户端分离
- **需求方端（app.anxinfawu.com）** — 面向个人/企业用户，解决法律问题
- **服务方端（pro.anxinfawu.com）** — 面向律师/律所，获客与案件管理
- 同一账号体系，独立注册流程、独立品牌、独立体验

### 三态运行模式
| 模式 | 数据边界 | AI 来源 | 订阅要求 |
|------|----------|---------|----------|
| **本地** | 数据不出设备 | 用户自配本地 LLM | 免费 |
| **混合** | 敏感本地、其余上云 | 本地 + 云端 | 订阅 |
| **云端** | 全云端 | 云端 | 订阅 |

**模式限制**：
- 舆情监测、找律师、IM 通讯 → 必须混合或云端
- 法律智库、通用模板 → 本地需先在联网模式下载数据包

详见 [docs/ARCHITECTURE_V2.md](docs/ARCHITECTURE_V2.md)

## 核心功能

### AI 法务能力
- **AI-native 工作台** — 合规风控、法律检索、找律师、尽调等核心入口统一在聊天页内通过对话 + A2UI 动态工作台完成，无需跳页
- **工作台 / 文档双模式** — 右侧面板支持在“多智能体工作台”和“文档编辑器”之间无缝切换，文档可归档回工作台文档库
- **智能法律咨询** — 多智能体协同，支持思维链可视化和 RAG 引用
- **合同全生命周期** — AI 审查 → 风险识别 → 修改建议 → 电子签署 → 归档
- **知识库研究模式** — 在聊天输入区可直接勾选多个知识库，按知识域限定回答来源并回传引用
- **尽职调查** — 企业调查请求支持意图识别 + 公司名抽取 + 强路由，优先返回结构化尽调摘要与 A2UI 卡片
- **知识图谱** — 法律概念和案例关联的 2D/3D 可视化，支持亮暗主题自适应、自动旋转、重置视角与类型筛选

### 智能协作
- **案件管理** — 立案、进度追踪、时间线、文档关联
- **实时协作编辑** — 基于 CRDT 的多人文档协同
- **审批工作流** — 合同审批、费用审批、自定义流程
- **律师精英库** — 按专业领域匹配律师资源

### 信息中心
- **司法资讯** — 法律法规更新、行业动态
- **智慧搜索** — 全文 + 语义混合搜索

## 技术架构

```
┌─────────────────────────────────────────────┐
│           客户端层                            │
│  Web (React) · 小程序 · Desktop · Mobile     │
├─────────────────────────────────────────────┤
│           API 层 (FastAPI)                   │
│  认证 · 路由 · 限流 · 统一响应               │
├─────────────────────────────────────────────┤
│           业务服务层                          │
│  AI Agent(21) · 服务(44) · A2UI 协议        │
├─────────────────────────────────────────────┤
│           数据层                              │
│  PostgreSQL · Redis · Qdrant · Neo4j · MinIO │
└─────────────────────────────────────────────┘
```

**技术栈：**

| 层 | 技术 |
|---|---|
| 前端 | React 18 + TypeScript + Vite + Shadcn/UI + Tailwind CSS |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 (Async) |
| AI | OpenAI + Anthropic + CAMEL-AI + MCP 协议 |
| 存储 | PostgreSQL + Redis + Qdrant + Neo4j + MinIO |
| 部署 | Docker + docker-compose + GitHub Actions |

## 快速开始

### 环境要求
- Python >= 3.11
- Node.js >= 18
- PostgreSQL 15+
- Redis 7+

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/your-org/Anxin-Smart-Legal-Services.git
cd Anxin-Smart-Legal-Services

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填写必要配置

# 3. 启动基础设施 (Docker)
docker-compose up -d postgres redis qdrant minio

# 4. 启动后端
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn src.api.main:app --reload --port 8001

# 5. 启动前端
cd frontend
npm install
npm run dev

# 6. 本地 UI 回归（可选）
npx playwright test -c playwright.local.config.ts
```

### Docker 一键部署

```bash
docker-compose up -d
```

生产环境推荐使用“宿主机 Nginx + Docker Compose 内环回绑定”的部署形态：

- 公网入口：`80` / `443`
- 前端容器：`127.0.0.1:3001 -> 80`
- 后端容器：`127.0.0.1:8001 -> 8001`
- PostgreSQL / Redis / Qdrant / Neo4j / MinIO：仅容器网络内可见，不对公网暴露

本地或服务器健康检查可使用：

```bash
curl -I http://127.0.0.1:3001
curl -I http://127.0.0.1:8001/health
```

## 测试

### 后端定向回归

```bash
cd backend
./.venv/bin/python -m pytest \
  tests/test_auth_roles_permissions.py \
  tests/test_contract_review_workflow.py
```

覆盖内容：
- 注册用户类型到初始角色映射
- 登录失败锁定与权限边界
- 合同审查结果落库、风险保存与建议应用

### 前端角色权限 E2E

```bash
cd frontend
npm run test:e2e -- role-access.spec.ts
```

覆盖内容：
- 企业用户可见“找律师”但不可见“案源管理”
- 非管理员访问后台自动回退到 `/chat`
- 过期 token 访问受保护页面自动跳转 `/login`

说明：
- `frontend/e2e/role-access.spec.ts` 已覆盖桌面端与移动端的多角色权限流。
- `frontend/e2e/helpers/session.ts` 会注入 mock 登录态、API 响应和 WebSocket，避免依赖真实后端启动。

### 前端核心业务动作 E2E

```bash
cd frontend
npm run test:e2e -- business-actions.spec.ts
```

覆盖内容：
- 找律师：问题描述 → 律师匹配 → 确认委托
- 任务中心：任务从“待办”推进到“进行中”
- 合同管理：触发智能审查并展示风险结果
- 文档库：进入“我的文档”并触发 AI 分析

### 当前质量基线

```bash
# 后端全量回归
cd backend
./.venv/bin/pytest -q tests

# 前端静态检查
cd ../frontend
npm run lint
npm run build
```

当前状态：
- 后端全量测试已通过：`172 passed`
- 后端核心授权/业务回归已通过：`42/42`
- 前端 `lint` / `build` 已通过
- 前端多角色访问控制 E2E：`6/6`
- 前端核心业务动作 E2E：`8/8`
- 云端生产迁移已确认到 `027_experience_patterns (head)`，`experience_patterns` 表已创建成功
- 云端生产入口已切换到宿主机 Nginx，`https://anxinfawu.com` 与 `https://www.anxinfawu.com` 均已验证可访问
- 云端生产公网仅保留 `80/443`，`8001/5433/6379/6333/6334/7474/7687/9000/9001` 已收口
- `/documents` 已恢复为真实受保护路由，文档库“我的文档 → AI 分析”链路已纳入回归
- 浏览器 E2E 仍受当前开发机 Chromium 启动权限限制，建议在具备浏览器权限的环境中补跑

### 当前生产部署基线

- 主机目录：`/opt/anxin-smart-legal-services`
- 对外域名：`anxinfawu.com`、`www.anxinfawu.com`
- HTTPS：已通过 Certbot 签发并接入主机 Nginx，HTTP 自动 301 跳转到 HTTPS
- 容器入口：前端 `127.0.0.1:3001`，后端 `127.0.0.1:8001`
- 生产模式：`DEV_MODE=false`
- 生产密钥：JWT、PostgreSQL、Redis 已完成线上随机化轮换

### 本轮收口内容

- 合同模块：详情、审查、风险列表、建议应用、风险处理、保存、下载全部按组织边界收口
- 文档模块：文本创建、元数据更新、内容更新、删除、版本历史、AI 分析全部纳入 API 级授权回归
- 找律师模块：咨询创建、委托前置条件、接单大厅可见性、接单状态推进、评价创建、评价回复已补齐权限与回归
- AI 旁听助手：同一对话仅允许发起人本人复用或停止旁听
- 前端：找律师委托、任务推进、合同审查、文档库分析四条动作流已补齐 E2E

### 当前已知遗留

- 仓库历史中的真实密钥轮换与 Git 历史清理尚未完成
- 前端 `access_token` / `refresh_token` 仍持久化在 `localStorage`
- 验证码 / 找回密码链路仍使用 6 位数字码，额外上下文绑定与更强校验尚未完成
- 两步验证目前仅提供状态说明与邮箱验证引导，尚未接入真实短信 / TOTP
- 云端私有助手目前为规划态入口，已提供“查看企业方案”跳转，但尚未开放申请
- 律师入驻当前支持图片 URL 提交认证资料，尚未接入站内真实文件上传链路
- 匿名聊天公开创建与 token 设计仍需重构
- e 签宝、法大大、部分支付/通知渠道仍保留占位实现
- LiveKit 仍未纳入当前生产启用范围，如需音视频需单独开放端口并补做验收

## 项目结构

```
├── backend/                 # Python 后端服务
│   ├── src/
│   │   ├── agents/          # 21 个 AI 智能体
│   │   ├── api/routes/      # 24 个 API 路由模块
│   │   ├── core/            # 配置、安全、数据库
│   │   ├── models/          # 19 个数据模型
│   │   └── services/        # 44 个业务服务
│   ├── alembic/             # 数据库迁移
│   └── tests/               # 测试套件
├── frontend/                # React 前端应用
│   └── src/
│       ├── pages/           # 25 个页面
│       ├── components/      # 164 个组件
│       ├── hooks/           # 自定义 Hook
│       └── lib/             # API、Store、设计令牌
├── docs/                    # 项目文档
│   ├── 00-project-execution-map.md  # 当前推进总索引
│   ├── openspec/            # 权威产品/商业/测试规范
│   ├── strategy/            # 当前产品架构与需求规划
│   ├── architecture/        # 架构设计
│   ├── audit/               # 代码级审计与任务拆分
│   ├── release/             # 发布证据、门禁、Go/No-Go
│   ├── design/              # 跨端设计与 UI/UX 资料
│   ├── references/          # 参考资料
│   └── archive/             # 旧版历史文档归档
├── skills/                  # AI Skills 定义
├── docker-compose.yml       # 生产部署配置
└── docker-compose.dev.yml   # 开发环境配置
```

## 文档导航

| 文档 | 说明 |
|------|------|
| [项目推进总索引](docs/00-project-execution-map.md) | 后续设计、开发、测试、发布的 12 环节入口 |
| [项目状态](PROJECT_STATUS.md) | 最新开发进度、近期变更与下一步计划 |
| [产品架构与需求规划](docs/strategy/product-architecture-and-requirements-2026-05-08.md) | 当前产品定位、端侧能力、企业智能体治理和实施影响 |
| [全设备智能助手 OpenSpec](docs/openspec/00-intelligent-assistant-platform-spec.md) | 上层产品合同，定义桌面/移动/本地模型/Skills/MCP/治理目标 |
| [商业交付规范](docs/openspec/01-commercial-delivery-spec.md) | 商业候选版必须满足的交付定义和阶段门槛 |
| [商业交付测试规范](docs/openspec/02-commercial-delivery-test-spec.md) | 各任务、端侧和发布前的必跑测试矩阵 |
| [审计摘要](docs/audit/SUMMARY.md) | 真实开发状态、阻断项和下一步顺序 |
| [UI/UX 审计与优化方案](docs/audit/current-state-ui-ux-audit-2026-05-08.md) | 移动端、小程序、桌面端的 UI/UX 问题和优化路线 |
| [任务提示词索引](docs/audit/_tasks/README.md) | TASK-01..12 的并行开发任务入口 |
| [发布就绪评估](docs/release/commercial-delivery-readiness.md) | Go/No-Go 判定、真实证据缺口和发布前命令 |
| [归档文档索引](docs/archive/README.md) | 已过时根目录文档的归档说明 |

## 开源协议

[Apache License 2.0](LICENSE)
