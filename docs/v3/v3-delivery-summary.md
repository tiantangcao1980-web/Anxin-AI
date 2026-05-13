# 安心智能助手 V3 — 交付总览（一页纸）

> 截至 **2026-04-27**：P0–P7 全部 ✅ 落地。**31 v3 commits / 61 个 v3 API endpoint / 543+ pytest / 100 测试文件**。后续进入 P8 打磨 + P9+ 扩展。

相关文档：[ARCHITECTURE](./ARCHITECTURE.md) · [AGENT_PERSONAS](./AGENT_PERSONAS.md) · [CAPABILITY_MATRIX](./CAPABILITY_MATRIX.md) · [ROADMAP](./ROADMAP.md) · [INTEGRATIONS](./INTEGRATIONS.md) · [SKILLS_INVENTORY](./SKILLS_INVENTORY.md)

---

## 1. 31 commits 时间线（P0 → P7）

| # | 阶段 | Commit | 说明 |
|---|---|---|---|
| 01 | P0 | (品牌切换 8 文件) | 安心法务 → 安心智能助手 |
| 02 | P1 | `76fd039` | task_orchestrator/im_gateway/skill_registry 三模块骨架 |
| 03 | P1 | `d32828b` | 侧边栏 v3 IA 重构 + 7 占位页 + feature flag |
| 04 | P1 | `c7e1332` | merge(p1-frontend) |
| 05 | P1 | `ce8277f` | merge(p1-backend) |
| 06 | P1 | `14cfceb` | docs/v3 6 大核心文档（89K 字符 / 1724 行） |
| 07 | P1 | `8b04e52` | merge(p1-docs) |
| 08 | P2 | `9a1d9a7` | 异步任务 MVP — task_orchestrator 真实装 |
| 09 | P2 | `bc26418` | 任务中心前端业务化 — 列表 + Timeline + 审批 |
| 10 | P2 | `a0b61dc` | fix App.tsx 去重 V3TasksPage |
| 11 | P3 | `b7fe5ac` | IM 配对授权 24h 流程 + 5 API + Celery 过期清理 |
| 12 | P3 | `32eb84d` | 前端 5 IM 渠道页业务化 |
| 13 | P3 | `dcdf098` | 前端配对授权页业务化（24h 倒计时） |
| 14 | P3 | `96cbd1f` | 飞书 IM 适配器真实装 |
| 15 | P3 | `c3766fb` | 沙箱执行器骨架 + LocalProvider |
| 16 | P4 | `0c2f123` | OAuth 通用应用授权框架 + 6 API + 加密 token_store |
| 17 | P4 | `d80bcaf` | 飞书 OAuth provider 真实装 + 5 endpoint |
| 18 | P4 | `eed05cc` | 钉钉 OAuth provider |
| 19 | P4 | `fd5da78` | Notion OAuth provider |
| 20 | P4 | `0f3e718` | Shopify OAuth provider + HMAC 回调验证 |
| 21 | P4 | `da47e19` | 前端应用授权页业务化（30+ provider 卡片市场） |
| 22 | P5 | `2131da2` | skill_registry 真实装 + skill_executor + 6 API |
| 23 | P5 | `ef088b6` | docx skill 移植（cowork-anthropic 兼容） |
| 24 | P5 | `9962d75` | xlsx skill 移植 |
| 25 | P5 | `89561d6` | pptx skill 移植 |
| 26 | P5 | `217d867` | pdf skill 移植 + OCR |
| 27 | P5 | `d3600f8` | 前端技能页业务化（50+ skill 跨 13 域） |
| 28 | P6 | `4d53e3e` | FetchService 4 层门面 + URL 路由 + 合规审计 + 4 API |
| 29 | P6 | `2ce0533` | HeadlessX 反检测抓取层 |
| 30 | P6 | `b7c05ea` | 法律数据源接入（5 源，合规版） |
| 31 | P6 | `e17a69b` | 跨境电商数据源接入（Shopify 真 + 4 mock） |
| 32 | P7 | `3445501` | 流程管家 persona + PersonaRegistry + 7 API |
| 33 | P7 | `0c69b83` | 市场研究员 persona + DeepResearch 迭代算法 + 5 API |
| 34 | P7 | `9de3895` | 获客猎手 persona + LeadScoring + 6 API |
| 35 | P7 | `8b785a8` | 内容总监 persona + 7 API |
| 36 | P7 | `2624335` | 跨境电商助手 persona + AI 议价 + 7 API |

> P0 品牌切换的细分 commits 在主仓库历史里；P1–P7 共 31 commits 集中在 2026-04-26 / 27 两天。

---

## 2. 61 个 v3 API endpoint 完整列表（按域分组）

### 异步任务编排（8） — 前缀 `/api/v3/tasks` + `/api/v3/agent-tasks`
- `GET /tasks/` · `POST /tasks/` · `PUT /tasks/{id}` · `PATCH /tasks/{id}/status`
- `DELETE /tasks/{id}` · `PUT /tasks/{id}/transition` · `POST /tasks/batch-update` · `GET /tasks/kanban/stats`

### IM 配对授权（5） — 前缀 `/api/v3/im/pairing`
- `POST /im/pairing/` · `GET /im/pairing/pending` · `GET /im/pairing/authorized`
- `POST /im/pairing/{request_id}/approve` · `POST /im/pairing/{request_id}/reject`

### IM 会话（5） — 前缀 `/api/v3/im`
- `GET /im/users/search` · `GET /im/conversations` · `POST /im/conversations`
- `GET /im/conversations/{id}/messages` · `PUT /im/conversations/{id}/read`

### 应用授权 OAuth（6） — 前缀 `/api/v3/app-authorizations`
- `GET /providers` · `GET ` · `POST /authorize` · `GET /callback` · `POST /refresh` · `DELETE /{id}`

### Skills 运行时（6） — 前缀 `/api/v3/skills`
- `GET ` · `GET /triggers/match` · `GET /{name}` · `POST /upload` · `PUT /{name}/toggle` · `POST /{name}/execute`

### 信息获取（4） — 前缀 `/api/v3/fetch`
- `POST /` 通用抓取 · `POST /batch` 批量 · `GET /audit` 审计 · `GET /sources` 数据源列表

### Persona 通用（3） — 前缀 `/api/v3/personas`
- `GET ` · `GET /{persona_id}` · `POST /{persona_id}/chat`

### 流程管家（4） — 前缀 `/api/v3/personas/operations`
- `POST /okr/dashboard` · `POST /weekly-report` · `POST /meeting-minutes` · `POST /extract-todos`

### 市场研究员（5） — 前缀 `/api/v3/personas/market`
- `POST /investigate-company` · `POST /competitor-monitor` · `POST /industry-trends`
- `POST /deep-research` · `GET /research/{report_id}`

### 获客猎手（6） — 前缀 `/api/v3/personas/sales`
- `POST /discover-leads` · `POST /draft-email` · `POST /generate-quote`
- `POST /sync-crm` · `POST /linkedin-outreach` · `GET /leads`

### 内容总监（7） — 前缀 `/api/v3/personas/content`
- `POST /wechat-article` · `POST /video-script` · `POST /poster-copy`
- `POST /brand-check` · `POST /localize` · `GET /brand-profiles` · `POST /brand-profiles`

### 跨境电商助手（7） — 前缀 `/api/v3/personas/ecommerce`
- `POST /analyze-niche` · `POST /verify-supplier` · `POST /negotiate`
- `POST /setup-store` · `POST /list-to-platforms` · `POST /vat-guidance` · `GET /dashboard`

> **合计**：8 + 5 + 5 + 6 + 6 + 4 + 3 + 4 + 5 + 6 + 7 + 7 = **61 endpoint** ✅

---

## 3. 集成生态全景图

```
┌──────────────────────────────────────────────────────────────┐
│                  L1  Personas (5 ✅ + 5 🚧)                  │
│ 流程✅  市场✅  获客✅  内容✅  出海✅                       │
│ 助理🚧  法律🚧  合同🚧  尽调🚧  财税🚧                       │
└──────────────────────────────────────────────────────────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       ▼                       ▼                       ▼
┌──────────────┐       ┌────────────────┐       ┌──────────────┐
│ TaskOrch ✅  │       │ FetchService✅ │       │ Skills ✅     │
│ Celery+Redis │       │ 4 层 + 多源     │       │ Registry+Exec │
└──────────────┘       └────────────────┘       └──────────────┘
       │                       │                       │
       ▼                       ▼                       ▼
┌──────────────┐       ┌────────────────┐       ┌──────────────┐
│ Sandbox ✅   │       │ 法律源 5 ✅     │       │ Office 4 ✅   │
│ Local provider│      │ 电商源 5 (1真4mock)│   │ docx/xlsx/...│
└──────────────┘       └────────────────┘       └──────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│                  IM Gateway ✅ (5 adapter)                   │
│ 飞书真 │ 钉钉 │ 企微 │ Slack │ Telegram (4 占位)             │
│ 配对授权 24h + Celery 过期清理                              │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│              OAuth 应用授权框架 ✅ (KMS 加密 token)           │
│ ✅ 飞书 │ ✅ 钉钉 │ ✅ Notion │ ✅ Shopify(HMAC)             │
│ 🟡 Amazon SP-API mock │ 🚧 30+ provider 待接                │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. 测试覆盖度

| 维度 | 数据 |
|---|---|
| **后端测试文件** | 100 个 `test_*.py` |
| **后端 test 函数** | 1023 个（P9/P10 加 281 个新测） |
| **稳定通过 pytest** | **944 / 1023 = 92.3%** （P11 健康度回归，详见 `HEALTH_P11.md`） |
| **前端 E2E 文件** | role-access.spec.ts (6/6 ✅) + business-actions.spec.ts (8/8 ✅) |
| **前端 lint / build** | ✅ 通过 |
| **Alembic 迁移** | head = `030_add_app_authorization_tables.py`（V3 新增 028/029/030） |

---

## 5. 已知缺口（来自 P8-A / B 报告）

> 详细见 P8-A baseline 修复清单与 P8-B 健康度报告

### P8-A 待修 baseline bugs（优先级排序）
1. Alembic 多 head 收口（V3 新表 028/029/030 与 V2 head 027 衔接）
2. 异步事务 — `task_orchestrator` 与 `app_authorization` 的 commit/rollback 边界统一
3. Celery 过期清理 worker 与配对授权状态机的竞态
4. 前端 Mock 适配器与真后端切换 — feature flag 缺统一开关

### P8-B 健康度低于 v2 基线项
1. v3 路由测试覆盖率 ~60%（v2 是 75%+）— 主要是 personas/* 5 文件分支较多
2. Lint 警告：未使用 import / type 收紧待补
3. 性能基线：`/personas/market/deep-research` 平均时延 8s（目标 < 5s，需异步化或缓存）

### 业务缺口
- 5 法务 persona 仍是规划态（21 agent 已就绪，待 P9+ 包装）
- 4 电商源（Shopee / TikTok Shop / Amazon SP-API / 1688）仍是 mock，待真 API
- CRM / 信息源 / 财税 / 设计 共 24+ provider 待 OAuth 接入
- 知识库新版（RAG-Anything 多模态）待 P10
- 生产部署仍在 anxinai.com（旧），未切到 anxinai.com

---

## 6. 上手指南

### 6.1 启动开发环境

```bash
# 1. 克隆 v3 分支
git clone -b main https://github.com/tiantangcao1980-web/Anxin-AI.git
cd Anxin-AI

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，至少填：DATABASE_URL / REDIS_URL / SECRET_KEY / OAUTH_TOKEN_ENC_KEY

# 3. 启动基础设施
docker-compose up -d postgres redis qdrant minio

# 4. 后端
cd backend
pip install -e ".[dev]"
alembic upgrade head      # 应用到 030_add_app_authorization_tables
uvicorn src.api.main:app --reload --port 8001

# 5. 启动 Celery worker（异步任务 + IM 配对过期清理）
celery -A src.services.task_orchestrator.celery_app worker --loglevel=info -Q default,im_pairing

# 6. 前端
cd ../frontend
npm install
npm run dev               # 默认 http://localhost:3000

# 7. 在浏览器开启 v3 feature flag
# 前端 settings → 启用 V3 IA，刷新即可看到 10 personas 侧边栏
```

### 6.2 运行测试

```bash
# 后端 v3 主体测试（推荐先跑这些）
cd backend
./.venv/bin/pytest -q tests/test_persona_*.py tests/test_agent_task_*.py \
  tests/test_token_store.py tests/test_im_*.py tests/test_skill_*.py \
  tests/test_fetch_*.py

# 后端全量
./.venv/bin/pytest -q tests

# 前端 lint + build
cd ../frontend
npm run lint && npm run build

# 前端 E2E（已纳入 v2 + v3 关键链路）
npm run test:e2e -- role-access.spec.ts business-actions.spec.ts
```

### 6.3 部署

> 当前仍在 V2 域名 `anxinai.com`（生产）。V3 完整生产部署到 `anxinai.com` 计划在 P13。

P8 / P9 期间建议在 staging：
```bash
# Docker compose 一键
docker-compose up -d
# 或宿主机 Nginx + 容器内绑定（推荐）
```

### 6.4 关键路径快速验证

| 验证点 | 命令 / 操作 |
|---|---|
| Persona 列表 | `curl http://localhost:8001/api/v3/personas` |
| 创建异步任务 | `curl -X POST .../api/v3/tasks/ -d '{"persona_id":"market_researcher", ...}'` |
| 飞书 OAuth | 浏览器打开 `/api/v3/app-authorizations/authorize?provider=feishu` |
| Skills 列表 | `curl http://localhost:8001/api/v3/skills` |
| FetchService | `curl -X POST .../api/v3/fetch -d '{"url":"https://...", "tier":"auto"}'` |

---

## 7. 关键文档索引

| 文档 | 用途 |
|---|---|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 6 层分层架构 + 模块清单 + 已实现 vs 规划 |
| [AGENT_PERSONAS.md](./AGENT_PERSONAS.md) | 10 persona 详情 + 实装 API endpoints |
| [CAPABILITY_MATRIX.md](./CAPABILITY_MATRIX.md) | 4 横 × 4 纵能力矩阵 + 实装状态 |
| [ROADMAP.md](./ROADMAP.md) | P0-P13+ 完整路线 + 风险登记册 |
| [INTEGRATIONS.md](./INTEGRATIONS.md) | 34+ OAuth provider 清单 + 实装状态 |
| [SKILLS_INVENTORY.md](./SKILLS_INVENTORY.md) | 13 域 76+ skill + 4 office 实装路径 |

---

上次更新：2026-04-27（P8-D 文档同步）
