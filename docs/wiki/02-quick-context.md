---
name: AI 最小上下文
description: 给 LLM 的最小可工作上下文（核心概念 + 文件位置 + 命令）
audience: AI agents
last_updated: 2026-05-14
---

# 02 · 最小上下文

> 想直接开始干活？把本文 + [03-current-state](03-current-state.md) 加载到上下文就够了。

## 工作目录结构

```
anxin-ai/                          # 根
├── AGENTS.md                      # Agent 行为单一真相源（必读）
├── DESIGN.md                      # 视觉/UI 单一真相源
├── README.md                      # 项目入口
├── CHANGELOG.md / CONTRIBUTING.md / SECURITY.md
│
├── docs/
│   ├── wiki/                      # ← 你正在这里（LLM 入口）
│   ├── REQUIREMENTS.md            # Spine 1：需求
│   ├── ARCHITECTURE.md            # Spine 2：架构
│   ├── ROADMAP.md                 # Spine 3：路线图
│   ├── DEVELOPMENT_PLAN.md        # Spine 4：开发计划
│   ├── RELEASE_GATE.md            # Spine 5：发布门禁
│   ├── 00-project-execution-map.md # 总导航
│   ├── 01-core-docs.md            # 三核心文档索引
│   ├── standards/                 # 13 份开发规范
│   ├── audit/harness/             # 六层框架审计文档
│   └── archive/                   # 历史归档（仅追溯用，不作权威）
│
├── backend/                       # FastAPI · Python 3.11+
│   ├── src/
│   │   ├── api/routes/            # 75 个 HTTP 路由
│   │   ├── agents/                # 22 persona + 21 specialized
│   │   ├── services/              # 业务服务层
│   │   ├── harness/               # 六层框架核心 8 模块
│   │   ├── core/                  # 配置 / 数据库 / Schemas
│   │   └── models/                # SQLAlchemy 2.0 async ORM
│   ├── tests/                     # pytest 543+
│   ├── evals/                     # 25 case + 4 维度打分（Eval 层）
│   └── alembic/                   # 数据库迁移（当前双 head：030/044）
│
├── frontend/                      # React 18 · Vite 7 · TS 5
│   ├── src/
│   │   ├── pages/                 # 路由页面
│   │   ├── components/            # 共享组件
│   │   ├── lib/icons/             # ⭐ 唯一图标导入入口
│   │   └── lib/api/               # API 客户端
│   └── tests/                     # vitest
│
├── desktop/                       # Tauri 2 · Rust Edition 2021
│   ├── src-tauri/
│   ├── src/                       # 桌面前端
│   └── tests/                     # cargo test
│
├── mobile/                        # Expo 52 · React Native 0.76
│   └── src/
│
├── apps/uni-mobile/               # UniApp Vue3 跨端
├── mini-program/                  # Taro 3.6 微信小程序
│
├── skills/                        # Agent Skills 配置（C2 标准化）
│   ├── _template/                 # skill 骨架模板
│   └── agents/                    # 5 agent 的 SKILL.md
│
├── scripts/                       # 运维 / 发布 / 验证脚本
│   ├── commercial-readiness-gate.sh
│   ├── release-worktree-inventory.py
│   ├── self_heal/                 # 自愈闭环
│   └── trace_to_test/             # T2 trace→test 转换
│
├── eval/                          # 顶层评估目录
├── .github/workflows/             # CI（5 端 + 4 reviewer + AI Review）
└── PROJECT_STATUS.md              # 进度快照（每次开发后更新）
```

## 核心概念（必懂）

| 概念 | 含义 | 文件 |
|---|---|---|
| **Persona** | 用户可见的智能体（10 个：法律/合同/财税/市场/获客/内容/跨境/流程/尽调/安心助理） | `backend/src/agents/personas/` |
| **Specialized Agent** | persona 内部的专业子 agent（21 个） | `backend/src/agents/specialized/` |
| **Harness** | 六层 Agent 治理框架的"骨架层"：trace/policy/cost/validator/tool/capability/context/task 8 模块 | `backend/src/harness/` |
| **Skill** | Agent 可加载的能力包（docx/xlsx/pptx/pdf 4 office + 域 skill） | `skills/` |
| **MCP** | Model Context Protocol，Agent 调用工具的标准协议 | 检查 `_check_mcp_tool_policy` |
| **三态运行** | 本地 / 混合 / 云端 三档隐私模式 | `docs/ARCHITECTURE.md` |
| **配对授权** | 桌面 ↔ 移动远控的 24h 限时授权机制 | `backend/src/services/im_pairing*` |
| **Trace** | Agent 执行轨迹，含 PII scrub（8 类）+ cluster_id 稳定签名 | `backend/src/services/trace_sink.py` |
| **AI Review Gate** | PR 4 reviewer 并行（code/security/dep/regression） | `.github/workflows/ai-review.yml` |
| **Eval baseline** | 25 case × 4 维度评测集 + PR Gate compare | `backend/evals/` |

## 常用命令

```bash
# 后端
cd backend && uv run --no-sync pytest             # 全测试
cd backend && uv run --no-sync ruff check src/    # 静态检查
cd backend && uv run --no-sync mypy src/          # 类型检查

# 前端
cd frontend && npm run lint                       # ESLint
cd frontend && npm run build                      # 含 tsc 类型检查
cd frontend && npm run test                       # vitest

# 桌面
cd desktop && cargo clippy --all-targets
cd desktop && cargo test

# 移动
cd mobile && npm run typecheck && npm run test

# 发布门禁（关键命令）
bash scripts/commercial-readiness-gate.sh --quick
python3 scripts/release-worktree-inventory.py --json --fail-on-unknown
node scripts/validate-commercial-delivery-checklist.cjs
node scripts/validate-commercial-delivery-lanes.cjs
bash scripts/release-evidence-secret-scan.sh

# Harness 相关测试
cd backend && uv run --no-sync pytest tests/test_harness*.py tests/test_chat.py
```

## API 入口速查

| 用途 | 路径 |
|---|---|
| 聊天主路径（H1 enforcement 已接入） | `POST /api/v3/chat` → [chat.py](../../backend/src/api/routes/chat.py) |
| 异步任务编排 | `/api/v3/agent_tasks/*` |
| OAuth 应用授权 | `/api/v3/app_authorizations/*` |
| IM 配对授权 | `/api/v3/im_pairing/*` |
| Skills 运行时 | `/api/v3/skills/*` |
| RAG | `/api/v3/rag_ingest /rag_kg /rag_query` |
| 10 persona 子路由 | `/api/v3/personas/{persona_id}/*` |
| 健康度 | `/api/health` + `/api/v3/health` |

## LLM Provider

LiteLLM 统一封装。支持：OpenAI / Anthropic / 通义 / 混元 / DeepSeek / Ollama（本地）。

## 数据栈

| 用途 | 选型 |
|---|---|
| 关系库 | PostgreSQL（云端）/ SQLCipher（桌面本地加密） |
| 向量 | Qdrant 1.12 |
| 图 | Neo4j 5.15 |
| 缓存 | Redis 7 |
| 对象存储 | MinIO（S3 兼容） |
| 任务队列 | Celery |

## 时间锚点

- **2026-04-27** V3 启动
- **2026-04-27 → 2026-05-08** P0-P7 完成
- **2026-05-12** V3 合并进商业交付主线
- **2026-05-14** ← 今天，六层框架基线 + 文档大整合
