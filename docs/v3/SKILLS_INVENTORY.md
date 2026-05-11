# 安心智能助手 V3 — Skills 域结构清单

> Skill 是 V3 的能力原子。本文按 **13 个域** 组织所有 skill，标注：来源 / 描述 / 依赖 / 目标 persona / 阶段 / 实装状态。

> 来源说明：
> - **cowork-anthropic**：Anthropic 官方 cowork skills（直接接入）
> - **Accio**：参考 Alibaba Accio Ecommerce Mind 范式（自研封装）
> - **自建**：基于 V2 已有 services 重构 / 新写
> - **已有项目内**：从现有 21 agents 抽取出来的能力

> 阶段：**P5 起步**（Skills 运行时上线后首批） / **P7 起步**（跨境 + 销售 agent 阶段） / **后续**（Beyond P7）

> **实装状态（2026-04-27）**：
> - ✅ Skills 运行时框架（P5）：[`backend/src/services/skill_registry/`](../../backend/src/services/skill_registry/)（loader / validators / registry，pyyaml + watchdog 热加载）+ [`skill_executor/`](../../backend/src/services/skill_executor/)（装饰器 + executor）+ 6 API
> - ✅ 4 个 office skill（cowork-anthropic 兼容）：[`skills/office/docx`](../../skills/office/docx) · [`skills/office/xlsx`](../../skills/office/xlsx) · [`skills/office/pptx`](../../skills/office/pptx) · [`skills/office/pdf`](../../skills/office/pdf)
> - ✅ FetchService 4 层（`intelligence/fetch` 真实装）：[`backend/src/services/fetch/`](../../backend/src/services/fetch/) — L1 HTTP / L2 crawl4ai / L3 HeadlessX / L4 官方 API
> - 🚧 其余 skill 仍是 yaml 描述 + 服务调用框架，逐步替换为真函数

相关文档：[ARCHITECTURE](./ARCHITECTURE.md) · [AGENT_PERSONAS](./AGENT_PERSONAS.md) · [CAPABILITY_MATRIX](./CAPABILITY_MATRIX.md) · [V3_DELIVERY_SUMMARY](./V3_DELIVERY_SUMMARY.md)

---

## 13 个域速览

| # | 域 | skill 数（首批） | 主要服务 persona |
|---|---|---|---|
| 1 | **legal** | 8 | 法律顾问 / 合同管家 |
| 2 | **tax_finance** | 6 | 财税顾问 |
| 3 | **operations** | 5 | 流程管家 |
| 4 | **research** | 5 | 市场研究员 / 尽调专家 |
| 5 | **marketing** | 4 | 获客猎手 / 内容总监 |
| 6 | **content** | 6 | 内容总监 |
| 7 | **design** | 4 | 内容总监 |
| 8 | **office** | 7 | 全部 |
| 9 | **ecommerce** | 8 | 跨境电商助手 |
| 10 | **sales** | 5 | 获客猎手 |
| 11 | **intelligence** | 7 | 安心助理 / 尽调专家 / 市场研究员 |
| 12 | **decision** | 4 | 获客猎手 / 跨境电商助手 |
| 13 | **system** | 7 | 安心助理（基础设施） |

**合计 76 个 skill**（首批），后续按需扩展。

---

## 1. legal — 法律域

| skill | 描述 | 来源 | 依赖 | 目标 persona | 阶段 |
|---|---|---|---|---|---|
| `legal/regulation-search` | 法律法规检索（北大法宝 / 威科） | 已有项目内 | 北大法宝 / 威科 OAuth | 法律顾问 / 合同管家 | P5 起步 |
| `legal/case-search` | 判例 / 文书检索（33,102 条 + 裁判文书网） | 已有项目内 | 内部知识库 | 法律顾问 / 尽调专家 | P5 起步 |
| `legal/contract-draft` | 合同起草（200+ 模板） | 已有项目内 | template-librarian | 合同管家 | P5 起步 |
| `legal/contract-review` | 合同逐条审查 | 已有项目内 | LLM + clause-extract | 合同管家 | P5 起步 |
| `legal/clause-extract` | 关键条款抽取 | 已有项目内 | LLM | 合同管家 | P5 起步 |
| `legal/redline-suggest` | 红线 + 修改建议（轨道修订） | 自建 | docx-track-changes | 合同管家 | P5 起步 |
| `legal/risk-grade` | 5 级风险评级 | 已有项目内 | risk_assessor agent | 法律顾问 | P5 起步 |
| `legal/regulation-monitor` | 法规变更订阅 + 推送 | 已有项目内 | regulatory_monitor agent | 法律顾问 | P5 起步 |
| `legal/template-match` | 智能模板匹配 | 已有项目内 | template_librarian | 合同管家 | P5 起步 |
| `legal/litigation-strategy` | 诉讼策略建议 | 已有项目内 | litigation_strategist | 法律顾问 | 后续 |
| `legal/compliance-check` | 合规自检（行业 / 区域） | 已有项目内 | compliance_officer | 法律顾问 | P5 起步 |

---

## 2. tax_finance — 税务财务域

| skill | 描述 | 来源 | 依赖 | 目标 persona | 阶段 |
|---|---|---|---|---|---|
| `tax_finance/tax-plan` | 税务筹划方案对比 | 已有项目内 | tax_compliance | 财税顾问 | P5 起步 |
| `tax_finance/tax-check` | 税务合规自检 | 已有项目内 | tax_compliance | 财税顾问 | P5 起步 |
| `tax_finance/legal-calc` | 法律计算（赔偿/加班/工伤） | 已有项目内 | legal_calculator | 财税顾问 / 法律顾问 | P5 起步 |
| `tax_finance/financial-analysis` | 财务报表关键指标解读 | 自建 | LLM + 财务数据接入 | 财税顾问 | P7 起步 |
| `tax_finance/audit-warning` | 高频稽查指标预警 | 自建 | tax_compliance + 政策库 | 财税顾问 | P7 起步 |
| `tax_finance/cross-border-tax` | 跨境税务（VAT / 关税） | 自建 | Xero / QB / 海关数据 | 跨境电商助手 / 财税顾问 | P7 起步 |

---

## 3. operations — 运营 / 流程域

| skill | 描述 | 来源 | 依赖 | 目标 persona | 阶段 |
|---|---|---|---|---|---|
| `operations/okr-plan` | OKR 制定 + 拆解 + 跟进 | 自建 | 飞书 OKR / Notion | 流程管家 | P5 起步 |
| `operations/approval-flow` | 审批流配置 + 智能预警 | 自建 | 飞书 / 钉钉审批 | 流程管家 | P5 起步 |
| `operations/meeting-minutes` | 会议录音 → 转写 → 纪要 → 待办 | 自建 | office/transcribe | 流程管家 | P5 起步 |
| `operations/weekly-report` | 周报自动起草 | 自建 | 多源聚合（OKR/IM/日历） | 流程管家 | P5 起步 |
| `operations/calendar-coordinate` | 多人日程协调 | 自建 | 飞书 / Outlook / Google 日历 | 流程管家 / 安心助理 | P5 起步 |

---

## 4. research — 调研域

| skill | 描述 | 来源 | 依赖 | 目标 persona | 阶段 |
|---|---|---|---|---|---|
| `research/deeptutor-mode` | DeepTutor 深度阅读模式 | Accio + 自建 | RAG-Anything + MinerU | 法律顾问 / 市场研究员 / 尽调专家 | P7 起步 |
| `research/multi-source-synthesize` | 多源信息综合 | 自建 | LLM + cross-search | 市场研究员 / 安心助理 | P5 起步 |
| `research/citation-trace` | 引文追踪 + 锚点跳转 | Accio + 自建 | DeepTutor + RAG | 全部 | P7 起步 |
| `research/competitive-monitor` | 竞品监控 + 异动报警 | 自建 | intelligence/fetch + 调度 | 市场研究员 | P5 起步 |
| `research/industry-report` | 行业研究报告生成 | 自建 | deeptutor + content/article | 市场研究员 | P7 起步 |

---

## 5. marketing — 营销域

| skill | 描述 | 来源 | 依赖 | 目标 persona | 阶段 |
|---|---|---|---|---|---|
| `marketing/ad-optimize` | 广告投放优化（多 agent） | Accio + 自建 | decision/multi-agent-vote | 获客猎手 / 跨境电商助手 | P7 起步 |
| `marketing/audience-target` | 受众包定位 + 优化 | 自建 | LLM + 标签库 | 获客猎手 | P7 起步 |
| `marketing/landing-page` | 落地页 A/B 生成 | cowork-anthropic + 自建 | web-artifacts-builder | 获客猎手 / 内容总监 | P7 起步 |
| `marketing/email-campaign` | 邮件营销活动 | 自建 | Outlook / Mailchimp | 获客猎手 | 后续 |

---

## 6. content — 内容域

| skill | 描述 | 来源 | 依赖 | 目标 persona | 阶段 |
|---|---|---|---|---|---|
| `content/article-write` | 公众号 / 知乎 / 小红书 多平台图文 | 自建 | LLM + 模板 | 内容总监 | P5 起步 |
| `content/headline-generate` | 标题 / 钩子矩阵生成 | 自建 | LLM | 内容总监 | P5 起步 |
| `content/seo` | SEO 关键词 + 元数据 | 自建 | Google Search Console | 内容总监 / 跨境电商助手 | P7 起步 |
| `content/video-script` | 短视频脚本 + 分镜 | 自建 | LLM | 内容总监 | P7 起步 |
| `content/remotion-render` | Remotion 自动剪辑成片 | cowork-anthropic + 自建 | Remotion runtime | 内容总监 | P7 起步 |
| `content/multilingual` | 多语言改写（中 → 英 / 西 / 阿） | 自建 | LLM | 内容总监 / 跨境电商助手 | P7 起步 |

---

## 7. design — 设计域

| skill | 描述 | 来源 | 依赖 | 目标 persona | 阶段 |
|---|---|---|---|---|---|
| `design/poster` | 海报 / 封面 / Banner | cowork-anthropic | canvas-design | 内容总监 | P5 起步 |
| `design/canvas-design` | 静态视觉（PDF / PNG） | cowork-anthropic | anthropic-skills | 内容总监 | P5 起步 |
| `design/web-artifacts-builder` | 落地页 / Demo 页 | cowork-anthropic | anthropic-skills | 内容总监 / 安心助理 | P5 起步 |
| `design/figma-export` | Figma 设计稿读取 + 导出 | 自建 | Figma OAuth | 内容总监 | 后续 |

---

## 8. office — 办公文档域

| skill | 描述 | 来源 | 实装路径 | 目标 persona | 状态 |
|---|---|---|---|---|---|
| `office/docx-*` | Word 读 / 写 / 模板 / 轨道修订 / helpers | cowork-anthropic | [`skills/office/docx/`](../../skills/office/docx) (helpers + 3 模板 + 5 测试) | 合同管家 / 内容总监 | ✅ 已实装（P5） |
| `office/xlsx` | Excel 读 / 写 / 计算 / helpers | cowork-anthropic | [`skills/office/xlsx/`](../../skills/office/xlsx) (helpers + 3 模板 + 5 测试) | 财税顾问 / 流程管家 | ✅ 已实装（P5） |
| `office/pptx` | PPT 生成 + 4 模板 | cowork-anthropic | [`skills/office/pptx/`](../../skills/office/pptx) (4 模板 + 5 测试) | 内容总监 / 流程管家 | ✅ 已实装（P5） |
| `office/pdf-report-gen` | PDF 报告生成 + OCR | cowork-anthropic | [`skills/office/pdf/`](../../skills/office/pdf) (OCR + 4 模板 + 5 测试) | 全部 | ✅ 已实装（P5） |
| `office/transcribe` | 录音 / 视频转写 | 自建 | Whisper / 通义千问 ASR | 流程管家 | 🚧 P9+ |
| `office/email-extract` | 邮件正文 / 附件提取 | 自建 | Outlook / Gmail | 合同管家 / 流程管家 | 🚧 P9+ |

---

## 9. ecommerce — 电商域

| skill | 描述 | 来源 | 依赖 | 目标 persona | 阶段 |
|---|---|---|---|---|---|
| `ecommerce/product-selection` | 选品分析（Accio Ecommerce Mind） | Accio + 自建 | LLM + 平台数据 | 跨境电商助手 | P7 起步 |
| `ecommerce/keyword-research` | 关键词调研（多平台） | Accio + 自建 | Helium 10 / Google Keyword | 跨境电商助手 / 内容总监 | P7 起步 |
| `ecommerce/store-setup` | Shopify 主题 / 商品页 / 落地页 | 自建 | Shopify OAuth | 跨境电商助手 | P7 起步 |
| `ecommerce/listing-optimize` | Listing 优化（标题 / 图 / 描述） | Accio + 自建 | LLM + 平台规则 | 跨境电商助手 | P7 起步 |
| `ecommerce/oversea-compliance` | 出海合规（GDPR / VAT / 商标） | 自建 | legal_researcher + 法务知识库 | 跨境电商助手 / 法律顾问 | P7 起步 |
| `ecommerce/logistics-plan` | 跨境物流方案推荐 | 自建 | 物流商 API | 跨境电商助手 | P7 起步 |
| `ecommerce/pricing-strategy` | 跨境定价策略 | 自建 | 多 agent + 汇率 | 跨境电商助手 | P7 起步 |
| `ecommerce/platform-data-pull` | 平台数据拉取（Shopify / Amazon / TikTok / Shopee） | 自建 | 各平台 OAuth | 跨境电商助手 | P7 起步 |
| `ecommerce/customs-policy` | 海关政策订阅 + 关税计算 | 自建 | 海关公开数据 | 跨境电商助手 / 财税顾问 | 后续 |

---

## 10. sales — 销售域

| skill | 描述 | 来源 | 依赖 | 目标 persona | 阶段 |
|---|---|---|---|---|---|
| `sales/lead-mining` | 线索挖掘（B2B 信号识别） | 自建 | LinkedIn / 工商数据 | 获客猎手 | P7 起步 |
| `sales/vibe-selling` | Vibe Selling（情境销售） | Accio + 自建 | LLM + 客户上下文 | 获客猎手 | P7 起步 |
| `sales/follow-up` | 客户跟进策略（基于阶段） | 自建 | CRM 集成 | 获客猎手 | P7 起步 |
| `sales/quotation-draft` | 报价单 / 提案起草 | 自建 | template + LLM | 获客猎手 / 安心助理 | P7 起步 |
| `sales/customer-segment` | 客户分层（RFM + 行为） | 自建 | CRM 数据 | 获客猎手 | 后续 |

---

## 11. intelligence — 情报 / 数据采集域

| skill | 描述 | 来源 | 依赖 | 目标 persona | 阶段 |
|---|---|---|---|---|---|
| `intelligence/fetch` | 智能抓取（API / HTTP / crawl4ai / HeadlessX 自动选型） — ✅ **真实装** [`backend/src/services/fetch/`](../../backend/src/services/fetch/) | 自建 | HeadlessX self-host + 代理池 | 全部 | ✅ P6 完成 |
| `intelligence/cross-search` | 跨数据源联合检索 | 自建 | RAG 向量库 + 倒排索引 | 安心助理 / 市场研究员 | P5 起步 |
| `intelligence/news-aggregate` | 新闻聚合（多源去重 + 分类） | 自建 | 各新闻源 API | 市场研究员 / 尽调专家 | P5 起步 |
| `intelligence/social-listen` | 社媒舆情监听 | 自建 | Reddit / X / LinkedIn | 市场研究员 / 获客猎手 | P5 起步 |
| `intelligence/sentiment-score` | 情感打分（中 + 英） | 已有项目内 | sentiment_agent | 尽调专家 / 获客猎手 | P5 起步 |
| `intelligence/litigation-search` | 诉讼 / 失信检索 | 已有项目内 | 裁判文书网 / 信用中国 | 尽调专家 | P5 起步 |
| `intelligence/company-profile` | 工商档案 / 股权图谱 | 自建 | 企查查 / 天眼查 | 尽调专家 | P5 起步 |
| `intelligence/recruit-signal` | 招聘信号识别（暗示业务方向） | 自建 | LinkedIn / 拉勾 / Boss | 市场研究员 / 获客猎手 | P7 起步 |
| `intelligence/competitor-monitor` | 竞品官网 + 公众号定时监控 | 自建 | fetch + 调度 | 市场研究员 | P5 起步 |
| `intelligence/citation-trace` | 通用引文追踪（DeepTutor 范式） | Accio + 自建 | RAG-Anything | 全部 | P7 起步 |

---

## 12. decision — 决策域

| skill | 描述 | 来源 | 依赖 | 目标 persona | 阶段 |
|---|---|---|---|---|---|
| `decision/multi-agent-vote` | 多 agent 投票决策（AI-Trader 范式） | Accio + 自建 | consensus_agent + Hermes | 获客猎手 / 跨境电商助手 / 安心助理 | P7 起步 |
| `decision/risk-cost-tradeoff` | 风险 / 成本 权衡分析 | 自建 | LLM + 公式库 | 法律顾问 / 财税顾问 | P5 起步 |
| `decision/scenario-analysis` | 多情景沙盘推演 | 自建 | LLM + 模拟器 | 全部 | 后续 |
| `decision/escalate-to-human` | 高风险升级到人工 | 自建 | 通知 + 审批流 | 全部 | P5 起步 |

---

## 13. system — 系统 / 基础设施域

| skill | 描述 | 来源 | 依赖 | 目标 persona | 状态 |
|---|---|---|---|---|---|
| `system/intent-router` | 意图识别 + 路由到 persona | 自建 | LLM + 路由表 | 安心助理 | 🚧 P9+ |
| `system/task-graph` | 任务 DAG 拆解 + 并行编排 — ✅ [`task_orchestrator/`](../../backend/src/services/task_orchestrator/) | 自建 | TaskOrchestrator | 安心助理 | ✅ P2 完成 |
| `system/consensus` | 多 agent 协商基础设施 | 自建 | consensus_agent | 安心助理 | 🚧 P9+ |
| `system/template-render` | 模板渲染（Jinja2 / Handlebars） | 自建 | - | 全部 | 🟡 部分（persona 模板已用） |
| `system/oauth-bridge` | OAuth 统一桥接 + 凭证刷新 — ✅ [`app_authorization/`](../../backend/src/services/app_authorization/) | 自建 | KMS / 加密 token_store | 全部 | ✅ P4 完成 |
| `system/notification-route` | 多通道通知路由（桌面 / 推送 / IM / 邮件） | 自建 | - | 全部 | 🟡 部分（飞书卡片已） |
| `system/memory-recall` | 分层记忆调用（V2 已有） | 已有项目内 | hierarchical-memory | 全部 | ✅ V2 沿用 |
| `system/audit-log` | 全链路审计 — fetch 已带 audit | 自建 | OpenTelemetry | 全部 | 🟡 部分 |
| `system/skill-registry` | Skills 运行时注册 + 热加载 — ✅ [`skill_registry/`](../../backend/src/services/skill_registry/) | 自建 | pyyaml + watchdog | 全部 | ✅ P5 完成 |
| `system/sandbox` | 沙箱执行器（LocalProvider + Docker/E2B/Codex Cloud 占位） — ✅ [`sandbox_executor/`](../../backend/src/services/sandbox_executor/) | 自建 | LocalProvider 可用 | 全部 | ✅ P3 骨架 |
| `system/im-gateway` | IM 通道 gateway + 配对授权 24h — ✅ [`im_gateway/`](../../backend/src/services/im_gateway/) | 自建 | feishu adapter 真 + 4 占位 | 安心助理 | ✅ P3 完成 |
| `system/workflow-canvas` | 可视化工作流编辑器（后续） | 自建 | React Flow | 安心助理 / 流程管家 | 🚧 后续 |

---

## Skill × Persona × Phase 视图（速查）

### Phase: P2 起步（异步任务 MVP 阶段）

| skill | 用途 |
|---|---|
| `system/task-graph` | 任务编排基础 |
| `system/audit-log` | 全链路追踪 |

### Phase: P3 起步（IM 通道阶段）

| skill | 用途 |
|---|---|
| `system/notification-route` | IM / 桌面 / 邮件统一推送 |

### Phase: P4 起步（OAuth 应用市场阶段）

| skill | 用途 |
|---|---|
| `system/oauth-bridge` | OAuth 统一基础 |

### Phase: P5 起步（Skills 运行时上线后首批）— ✅ 框架完成

> **实装情况**：✅ 4 office skill 真实装（docx/xlsx/pptx/pdf），其余 ~46 个仍是 yaml + 服务调用框架，前端 [`SkillsPage.tsx`](../../frontend/src/pages/v3/capabilities/SkillsPage.tsx) 已展示 50+ skill 跨 13 域

### Phase: P7 起步（跨境 + 销售 agent 阶段）— ✅ 主要 skill 已上

> **实装情况**：✅ 5 personas 已实装（市场/获客/内容/出海/流程），各 persona 调用的核心 skill（`research/deep-research` `sales/lead-mining` `content/article-write` `ecommerce/*`）以函数级集成在 persona 文件内；后续会抽出独立 skill 包

### Phase: P8+ 持续

> 真函数化推进：把 yaml 描述的 skill 一个个改写为可调用的 Python 入口，进入 skill_registry 注册；优先级按 persona 真实调用频率

---

## Skill 治理（必读）

| 维度 | 要求 |
|---|---|
| **命名** | `{domain}/{verb-noun}`（小写连字符） |
| **schema** | 必含 input / output / deps / required_oauth / runtime（python/node） |
| **来源标注** | 每个 skill 必标 cowork-anthropic / Accio / 自建 / 已有项目内 |
| **依赖声明** | 显式列出依赖的其他 skill / OAuth / 模型 |
| **沙箱** | 默认在 SandboxExecutor 运行，文件 + 网络白名单 |
| **观测** | 调用次数 / 成功率 / 平均时延 / 成本 上 dashboard |
| **版本** | 语义化版本（major.minor.patch），持久化到注册表 |
| **测试** | 每个 skill 至少 3 个 e2e 用例（常用 / 边界 / 异常） |

---

上次更新：2026-04-27（P5 office skill 实装 + P6 fetch + system 真实装同步）
