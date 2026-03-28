# 安心法务 — AI 智能法务平台

> 通过 AI 能力 + 一键触达律师，为律师、中小企业和个人提供专业、便捷的法律服务。

## 产品定位

**安心法务**是一个以 AI 为核心驱动的智能法务平台，致力于让每个人都能便捷地获得专业法律服务。

- **守护** — 为企业经营保驾护航，降低法律风险
- **放心** — 数据私有化部署，信息安全可控
- **专业** — 21 个专业 AI 智能体 + 一键匹配真人律师

## 核心功能

### AI 法务能力
- **智能法律咨询** — 多智能体协同，支持思维链可视化和 RAG 引用
- **合同全生命周期** — AI 审查 → 风险识别 → 修改建议 → 电子签署 → 归档
- **尽职调查** — 企业背景调查、司法案件检索、舆情分析、关系图谱
- **知识图谱** — 法律概念和案例关联的 3D 可视化

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
```

### Docker 一键部署

```bash
docker-compose up -d
```

访问 http://localhost:3001

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
│   ├── architecture/        # 架构设计
│   ├── issues/              # 问题反馈与修复记录
│   ├── references/          # 参考资料
│   └── plans/               # 开发计划
├── skills/                  # AI Skills 定义
├── docker-compose.yml       # 生产部署配置
└── docker-compose.dev.yml   # 开发环境配置
```

## 文档导航

| 文档 | 说明 |
|------|------|
| [产品架构文档](docs/2026-03-26_安心法务-产品架构文档.md) | 产品定位、功能全景、技术架构 |
| [开发路线图](docs/2026-03-26_安心法务-开发路线图.md) | 分阶段开发计划和里程碑 |
| [设计系统规范](docs/2026-03-26_安心法务-设计系统规范.md) | 色彩、排版、组件、动效规范 |
| [权限体系设计](docs/2026-03-26_安心法务-权限体系设计.md) | 用户角色、权限矩阵 |
| [部署指南](docs/2026-03-26_安心法务-部署指南.md) | Docker 部署、私有化部署 |
| [系统架构](docs/ARCHITECTURE.md) | 详细技术架构设计 |

## 开源协议

[Apache License 2.0](LICENSE)
