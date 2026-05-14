# 需求规范 — 单一真相源

> **状态**：本文是 V3「安心智能助手」需求规范的**单一权威来源**。
> **版本**：2026-05-14 · V3 P0-P7 已交付后冻结的基线
> **历史来源**：本文合并自 `docs/openspec/00-intelligent-assistant-platform-spec.md` + `docs/openspec/01-commercial-delivery-spec.md` + `docs/openspec/02-commercial-delivery-test-spec.md` + `docs/strategy/product-architecture-and-requirements-2026-05-08.md`。原文已归档到 [docs/archive/legacy-spine-sources/](archive/legacy-spine-sources/)。
> **更新规则**：仅当核心需求合同发生变更时更新，预期年度 1 次。日常变更见 [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)。

---

## 目录

1. [平台使命与定位](#1-平台使命与定位)
2. [用户与服务对象](#2-用户与服务对象)
3. [平台能力合同](#3-平台能力合同)
4. [当前实装基线](#4-当前实装基线)
5. [商业交付定义](#5-商业交付定义)
6. [发布验收门槛](#6-发布验收门槛)
7. [三态运行模式边界](#7-三态运行模式边界)
8. [非功能需求与红线](#8-非功能需求与红线)

---

## 1. 平台使命与定位

**安心智能助手 (Anxin AI)** 为中国成长型制造企业（中小为主）提供"**一个 App 搞定法务 / 财税 / 合规 / 经营 / 调研获客 / 内容产出 / 出海跨境**"的全链路 AI 经营助理。

### 1.1 核心价值

| 价值 | 含义 |
|---|---|
| 🛡 **合规经营** | 法律 / 财税 / 合规 / 经营管理一站式 AI 辅助 |
| 📈 **增长获客** | 市场研究 / 获客 / 内容产出 / 数据驱动决策 |
| 🌍 **出海跨境** | 海外选品 / 供应链 / 跨境合规 / 多语言运营 |
| 🎯 **综合协调** | 多 persona 协同 + 桌面/移动远控 |

### 1.2 与通用 AI 助手的差异

| 维度 | 通用 AI（ChatGPT / Claude / 通义） | 安心智能助手 |
|---|---|---|
| **行业纵深** | 通用知识 | 中国法规 / 税务 / 合规深度 + 5 法律源 + 5 电商源 |
| **桌面 / 远控** | 仅 Web / 移动 | 桌面工作站（Tauri 2 + 本地 LLM + 远控配对授权 24h） |
| **可信会话** | 黑盒回答 | 来源链路 + 工具调用透明 + 智能体治理（六层 Harness） |
| **多 persona 协同** | 单一 chat | 22 personas（10 用户可见 + 12 内部）+ 21 specialized agent |
| **隐私分级** | 全云端 | 本地 / 混合 / 云端 三态运行 + SQLCipher + TopSecret guard |
| **企业级治理** | 个人订阅 | 多租户 + 六层校验 + L0-L5 智能体治理 |

---

## 2. 用户与服务对象

### 2.1 用户矩阵

| 用户类型 | 角色 | 典型规模 | 痛点 |
|---|---|---|---|
| **付费方** | 中小制造企业老板 / 高管 | 50-500 人 / 年营收 5000 万-5 亿 | 法务/财税/合规分散，专业服务昂贵 |
| **使用方** | 行政 / 财务 / 法务兼岗人员 | 1-3 人专职 | 知识盲区 + 时间不足 |
| **生态方** | 律师 / 税务师 / 财务顾问 | 个人 / 小工作室 | 客户获取成本高，工具碎片化 |

### 2.2 试点场景

- **政府试点**：高可信门槛（数据不出 / 全审计 / 本地 LLM）
- **中小企业试点**：合规 + 经营双引擎，先 1-2 行业垂直突破（如先做制造业，再扩展）

---

## 3. 平台能力合同

### 3.1 桌面主工作站

- **形态**：Tauri 2（Rust Edition 2021）应用
- **核心**：
  - 系统托盘 + 全局快捷键
  - SQLCipher 加密本地存储
  - OS Keyring 管理密钥
  - 本地 LLM（Ollama 集成）
  - 离线模式（数据 0 出设备）
- **验收**：签名 + 公证（macOS / Windows）+ unsigned runtime smoke 已通过

### 3.2 移动随身助手与桌面远控

- **形态**：Expo 52 / RN 0.76 + UniApp Vue3 跨端 + 微信小程序（Taro 3.6）
- **核心**：
  - 桌面 ↔ 移动**配对授权 24h 限时**
  - 推送通知
  - 生物识别
  - 离线缓存
- **验收**：iOS / Android 真机 transcript + 小程序 build smoke

### 3.3 任意模型 / Skills / MCP

- **模型支持**：LiteLLM 封装 — OpenAI / Anthropic / 通义 / 混元 / DeepSeek / Ollama
- **Skills**：watchdog 热加载，按域分组（office 4 + 法律 13 + 电商 N）
- **MCP**：Model Context Protocol 标准协议，工具调用统一治理
- **验收**：`_check_mcp_tool_policy` 主路径强制执行（P0 待统一到 `harness/policy_engine.py`）

### 3.4 独立知识库与本地安全

- **形态**：每租户独立向量库（Qdrant）+ 图（Neo4j）+ 多模态（MinerU）
- **核心**：
  - RAG-Anything 新版多模态（P10 规划）
  - 引用链路完整可追溯
  - 本地 / 混合 / 云端三态可配
- **验收**：RAG full50 baseline + 引用准确率 ≥ 阈值

### 3.5 专业服务、舆情与获客

- **形态**：5 法律源 + 5 电商源 + FetchService 4 层架构（HTTP / crawl4ai / HeadlessX / 官方 API）
- **覆盖业务**：
  - 法律咨询 / 合同审查 / 尽调（5 法务 persona，P9 包装）
  - 财税合规 / 税务筹划（财税顾问 persona）
  - 市场研究 / Lead Scoring（获客猎手 persona）
  - 跨境合规 / 选品 / VAT（跨境电商助手 persona）
- **验收**：每域至少 1 个 evidence collection runbook

### 3.6 通用工作助手、软件原型设计

- **流程管家**：OKR / 周报 / 会议纪要
- **内容总监**：公众号 / 短视频脚本 / 海报
- **桌面原型**：Skills 协同 office 4（docx / xlsx / pptx / pdf）

### 3.7 企业智能体治理（L0-L5）

| 级别 | 治理对象 | 验收 |
|---|---|---|
| L0 | 用户身份与租户 | RBAC / 多租户隔离 |
| L1 | 订阅与计费 | 配额阻断 |
| L2 | 角色与权限 | 六层校验：subscription + role + permission + risk + privacy + device |
| L3 | 风险评级 | 高敏数据 → 本地模式强制 |
| L4 | 隐私上下文 | privacy_context 8 类 PII scrub |
| L5 | 设备与端点 | 配对授权 + 设备指纹 |

### 3.8 协作式多智能体控制面

- **核心**：AgentManager + Team + Worker
- **22 个 Agent persona**（10 用户可见 + 12 内部）
- **21 specialized agent**（如 LegalResearcher / RiskAssessor / ContractDrafter）
- **AGENTS.md**：单一真相源（运行时行为 + 红线 + 反 slop + 路由 + 协作约定）

### 3.9 可信会话体验与 Skills 进化

- **可信会话**：
  - 来源链路（每条 AI 回复可点击展开"用了哪些工具 / 查了哪些来源"）
  - 工具调用透明（用户可中断 / 拒绝）
  - 引用链路（RAG 必带 source）
- **Skills 进化**：
  - watchdog 热加载（不重启服务）
  - eval baseline（25 case + 4 维度打分 + PR Gate compare）
  - Skills 试点反馈循环

---

## 4. 当前实装基线（2026-05-14）

### 4.1 已交付（V3 P0-P7 + Harness H0-O2 ✅）

| 域 | 实装 | 数量 |
|---|---|---|
| 后端 API endpoint | v3 | 61 |
| 后端 pytest | full | 543+ |
| Agent persona（用户可见） | 全部 | 10 |
| Agent persona（含内部） | 全部 | 22 |
| Specialized agent | 全部 | 21 |
| Office skill | docx/xlsx/pptx/pdf | 4 |
| 法律源 | 5 |  |
| 电商源 | 5 |  |
| OAuth provider | 飞书/钉钉/Notion/Shopify/Amazon SP | 5 |
| IM 真接入 | 飞书 | 1 |
| IM 占位 | 钉钉/企微/Slack/Telegram | 4 |
| 六层框架 | H0-O2 + H1 | 9 |
| 前端测试文件 | - | 100+ |
| 文档规范 | - | 13 |

### 4.2 进行中 / 待启动（P8-P13）

详见 [ROADMAP.md](ROADMAP.md) + [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)。

### 4.3 当前阻断

| 阻断 | 影响 | 当前优先级 |
|---|---|---|
| Apple Developer / Windows 代码签名 | 桌面签名证据 | P0 (核心交付仍需) |
| GDCA 政务签 商务对接 | 政务客户合同签发 | P2 (代码 placeholder ✅, 待业务推动) |
| 粤企签 / 粤商通 开发者权限 | 中小企业轻量签约 | P2 (代码 placeholder ✅, 待业务推动) |
| 商业化支付凭证 (微信 / 支付宝 / Stripe) | 订阅收费 | ⏬ P3 (2026-05-14 降级, PMF 后启动) |
| 商业化电签凭证 (e签宝 / 法大大) | 第三方电签 | ⏬ P3 (2026-05-14 降级, PMF 后启动) |
| 真机预约 | iOS / Android 真机 transcript | P1 |
| Alembic 三 head | ✅ 已合并 (T5-prep + T5 主体) | — |

---

## 5. 商业交付定义

### 5.1 候选版定义

**"商业候选版"** = 满足以下**全部**条件：

1. ✅ V3 P0-P7 已交付（实装 + 测试）
2. ✅ 六层框架 H0-O2 + H1 落地
3. ✅ 13 份开发规范有效
4. 🚧 UI/UX 优化 P0（假成功修复）完成
5. 🚧 5 维度发布门禁通过（后端 / 前端 / 桌面 / 移动 / 证据）
6. 🚧 桌面签名 + 公证（阻断中）
7. 🚧 支付 / 电签 live（阻断中）
8. 🚧 真机 transcript（阻断中）

> 当前状态：✅ 前 3 项已完成；🚧 后 5 项进行中。

### 5.2 阶段目标

| 阶段 | 目标 | 评估窗口 |
|---|---|---|
| **冲刺阶段（now）** | 完成 P8 UI/UX + 桌面签名 + 支付/电签 live | 2-3 周 |
| **政府试点 v1.0** | 1 政府客户落地（高可信门槛全过）| 1 季度 |
| **中小企业试点 v1.5** | 5-10 中小企业落地（合规 + 经营双引擎） | 1 季度 |
| **生态扩展 v2.0** | 律师 / 税务师 / 财务顾问入驻 | 2 季度 |

### 5.3 统一开发规则

- 所有变更通过 PR + 4 reviewer 并行（code / security / dep / regression）
- 所有 Agent 行为变更必须更新 eval baseline
- 商业发布前必跑 `commercial-readiness-gate.sh`
- 详见 [docs/standards/](standards/) 13 份规范

---

## 6. 发布验收门槛

### 6.1 验收域表（必须全过）

| 域 | 验收点 | 命令 / 文件 |
|---|---|---|
| **后端** | ruff + mypy + pytest 全过 | `make verify-backend` |
| **前端** | lint + tsc + vitest + build | `make verify-frontend` |
| **桌面** | cargo clippy + test + unsigned smoke | `cd desktop && cargo test` |
| **移动** | typecheck + jest + Expo build | `cd mobile && npm run typecheck` |
| **小程序** | Taro build + smoke | 见 `docs/mobile/` |
| **API 路由** | OpenAPI 生成无错 | `make openapi` |
| **数据库迁移** | alembic upgrade head 干净 | 当前双 head ⚠️ |
| **安全** | trufflehog + npm audit + Bandit + secret-scan | `bash scripts/release-evidence-secret-scan.sh` |
| **AI Review** | 4 reviewer 全过（code/security/dep/regression）| `.github/workflows/ai-review.yml` |
| **Eval baseline** | 25 case 4 维度，下降 ≥ 5% 阻断 | `cd backend && uv run pytest evals/` |
| **RAG baseline** | full50 准确率 ≥ 阈值 | `backend/evals/rag_full50.py` |
| **桌面签名** | Apple notarization + Windows code sign | 等账号 |
| **真机证据** | iOS / Android transcript | 等真机 |
| **支付/电签 live** | preflight + 真单成功 | 等沙箱 |

详见 [RELEASE_GATE.md](RELEASE_GATE.md)。

### 6.2 Go/No-Go 判定

- **Go 条件**：上表 14 项**全部** ✅（含阻断解除）
- **No-Go 条件**：任意一项 🚫 或证据不齐
- **当前判定**：🚫 No-Go（3 项阻断中）

---

## 7. 三态运行模式边界

| 模式 | 数据出设备 | LLM 位置 | 验收点 | 适用场景 |
|---|---|---|---|---|
| **本地** | ❌ | Ollama 本地 | SQLCipher + TopSecret guard 必经 | 高敏感（合同 / 法务 / 政府试点） |
| **混合** | ✅ 脱敏后 | 云端 + 本地协同 | privacy_context 8 类 PII scrub | 一般业务 |
| **云端** | ✅ 全云 | 云端 LLM | 用户**显式同意** + 审计日志 | 通用助手 |

切换规则：
- 用户可在桌面 / 移动 / Web 三端自由切换模式
- 切换后下个会话生效
- 高敏数据自动强制本地模式（L3 风险评级触发）

实现：[backend/src/services/privacy_context.py](../backend/src/services/privacy_context.py) + 桌面 `desktop/src-tauri/` 隐私门。

---

## 8. 非功能需求与红线

### 8.1 性能

| 指标 | 目标 | 当前 |
|---|---|---|
| API P95 延迟 | < 2 秒 | ~ 1.5 秒（实测） |
| Agent 任务排队延迟 | < 5 秒 | ~ 3 秒 |
| 桌面冷启动 | < 3 秒 | 待优化 |
| 移动配对授权 | < 10 秒 | ~ 8 秒 |

### 8.2 可靠性

- **可用性**：99.5%（试点期）→ 99.9%（GA）
- **数据持久化**：每日全量 + 每小时增量
- **回滚**：每次发布有 rollback runbook（见 `docs/release/`）

### 8.3 安全红线（绝不可破）

- ❌ 跨租户数据泄漏
- ❌ 密钥提交到 git
- ❌ 跳过 `_check_mcp_tool_policy` 工具调用
- ❌ 高敏数据非本地模式处理
- ❌ 用户输入直接喂 LLM（无 output_validator）
- ❌ 桌面包未签名发布
- ❌ 测试覆盖率倒退（>5%）

### 8.4 合规

- 中国《网络安全法》《数据安全法》《个人信息保护法》全合规
- 跨境数据流转走标准合同条款
- 行业特殊合规（金融 / 医疗 / 政府）按试点客户要求加强

### 8.5 Agent 行为红线（详见 [AGENTS.md](../AGENTS.md)）

- ❌ 不能伪造来源
- ❌ 不能编造法条
- ❌ 不能跳过 output_validator
- ❌ 不能跨 persona 越权
- ❌ 不能输出敏感个人信息

---

## 附录 · 引用与归档

- **原 openspec/00 平台合同**：[docs/archive/legacy-spine-sources/openspec/](archive/legacy-spine-sources/openspec/)
- **原 openspec/01 商业交付**：同上
- **原 openspec/02 测试规范**：同上 + 全部测试矩阵详见 [RELEASE_GATE.md](RELEASE_GATE.md)
- **原 strategy 产品架构 1409 行**：[docs/archive/legacy-spine-sources/strategy/](archive/legacy-spine-sources/strategy/)
- **ADR 决策记录**：[docs/adr/](adr/) — V3 升级（ADR 001）+ 文档命名标准（ADR 002）
- **关键设计决策**：[docs/wiki/06-decision-log.md](wiki/06-decision-log.md)

---

> **维护提示**：本文是冻结基线。若发现与代码不一致，先检查是否已纳入 [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) 待办；若未纳入，提 issue 而非直接改本文。
