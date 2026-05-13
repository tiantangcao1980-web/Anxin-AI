---
name: 业务 / 技术术语表
description: 看到不认识的名词时查这里
audience: AI agents
last_updated: 2026-05-14
---

# 05 · 术语表

## 业务域

| 术语 | 含义 |
|---|---|
| **中小制造企业** | 项目核心用户，年营收 5000 万-5 亿，员工 50-500 人 |
| **合规经营** | 法务 + 财税 + 监管合规一站式服务（产品三大价值之一） |
| **增长获客** | 市场研究 + Lead Scoring + 内容产出（产品三大价值之二） |
| **出海跨境** | 海外选品 + 跨境合规 + 多语言运营（产品三大价值之三） |
| **综合协调** | 多 persona 协同 + 桌面/移动远控（产品第四价值，2026 加入） |
| **可信会话** | 显示来源链路 + 工具调用透明 + 用户可干预的 AI 交互 |
| **试点（政府/中小）** | 商业化落地路径，需"高可信"门槛（数据不出 / 全审计） |

## Persona（用户可见智能体）

| Persona | 中文 | 业务域 | 状态 |
|---|---|---|---|
| `anxin_assistant` | 安心助理 | 综合协调（意图识别 + 多 persona 编排） | ✅ |
| `legal_advisor` | 法律顾问 | 合规经营 | 🚧 |
| `contract_steward` | 合同管家 | 合规经营 | 🚧 |
| `due_diligence_expert` | 尽调专家 | 合规经营 | 🚧 |
| `tax_finance_advisor` | 财税顾问 | 合规经营 | 🚧 |
| `process_steward` | 流程管家 | 综合协调 | ✅ |
| `market_researcher` | 市场研究员 | 增长获客 | ✅ |
| `lead_hunter` | 获客猎手 | 增长获客 | ✅ |
| `content_director` | 内容总监 | 增长获客 | ✅ |
| `ecommerce_assistant` | 跨境电商助手 | 出海跨境 | ✅ |

## 技术架构

| 术语 | 含义 |
|---|---|
| **Harness 层** | Agent 治理框架的"骨架"，对应 Harrison Chase 6 层中的 L1 |
| **Specialized Agent** | persona 内部的专业子 agent，21 个（如 LegalResearcher / RiskAssessor） |
| **Skill** | Agent 可加载的能力包，按域分组（office 4 + 法律 13 + 电商 N） |
| **MCP** | Model Context Protocol，Anthropic 推的工具调用协议 |
| **AGENTS.md** | Agent 行为单一真相源（22 个 Agent 的红线 / 路由 / 反 slop / 协作约定） |
| **Context 三层** | AGENTS.md（系统级）+ skills/（能力级）+ memory/（会话级） |
| **PII Scrub 8 类** | 手机/邮箱/身份证/银行卡/姓名/地址/IP/统一社会信用代码 |
| **cluster_id** | trace 的稳定签名，用于聚类相同失败模式 |
| **Eval baseline** | 评测集冻结快照，PR 阻断基线下降 ≥ 5% |
| **AI Review Gate** | PR 4 reviewer 并行（code/security/dep/regression） |
| **Self-Heal** | 失败 trace 自动 dispatch 修复 PR / Issue 化 |

## 三态 / 双客户端

| 术语 | 含义 |
|---|---|
| **三态运行** | 本地 / 混合 / 云端 三档隐私模式（详见 [04 §三态](04-architecture-map.md#三态运行模式)） |
| **双客户端** | "需求方"（企业老板）+ "服务方"（律师/税务顾问）两套登录入口 |
| **配对授权** | 桌面 ↔ 移动远控的 24h 限时授权 |
| **TopSecret guard** | 顶级敏感数据的边界守卫，本地模式必经 |
| **privacy_context** | 请求级隐私上下文，决定数据是否可出设备 |

## 工程基础设施

| 术语 | 含义 |
|---|---|
| **alembic 双 head** | 当前数据库迁移有两个 head（030_app_authorization / 044_skill_connector_configs），需 merge head 后再加 028_incidents |
| **commercial-readiness-gate** | 发布门禁脚本，5 维度判定 |
| **release-worktree-inventory** | 工作树清单检查，未知文件 / 未追踪文件归类 |
| **release-evidence-secret-scan** | 发布证据中的密钥扫描（trufflehog 模式） |
| **48-hour-commercial-delivery-plan** | 商业发布冲刺 48 小时倒排计划 |
| **uv** | Python 包管理器，本项目 backend 使用（替代 pip/poetry） |
| **Tauri 2** | Rust 桌面框架，替代 Electron |
| **LiteLLM** | LLM provider 统一封装 |
| **trufflehog** | 密钥扫描工具 |

## 命名约定（来自 standards/naming-convention）

| 类型 | 约定 | 示例 |
|---|---|---|
| 文件 / 目录 | kebab-case | `agent-personas.md`, `chat_service.py`（Python snake_case 例外） |
| Python 变量 / 函数 | snake_case | `output_validator`, `run_validation` |
| Python 类 | PascalCase | `TaskOrchestrator`, `ChatService` |
| TS 变量 / 函数 | camelCase | `ChatResponse`, `useChat` |
| TS 类型 / 组件 | PascalCase | `ChatMessage`, `PersonaCard` |
| Commit type | 英文 | `feat`, `fix`, `chore`, `docs`, `refactor`, `test` |
| Commit 描述 | 中文 | `feat(harness): 引入六层框架基线` |
| 分支 | `<author>/<descriptive>` | `claude/vigorous-wiles-5a3fb3` |

## 缩写表

| 缩写 | 全称 |
|---|---|
| KB | Knowledge Base（知识库） |
| KG | Knowledge Graph（Neo4j） |
| RAG | Retrieval-Augmented Generation |
| IA | Information Architecture |
| IM | Instant Messaging（飞书/钉钉等） |
| RBAC | Role-Based Access Control |
| ADR | Architecture Decision Record |
| OWASP | Open Web Application Security Project |
| CTF | Capture The Flag |
| TDD | Test-Driven Development |
| OAuth | Open Authorization |
| KMS | Key Management Service |
| VAT | Value Added Tax（跨境业务） |
| SP | Selling Partner（Amazon SP API） |
| VLM | Vision-Language Model |
| SSE | Server-Sent Events |
| WS | WebSocket |
| GHA | GitHub Actions |
| SSRF | Server-Side Request Forgery |
