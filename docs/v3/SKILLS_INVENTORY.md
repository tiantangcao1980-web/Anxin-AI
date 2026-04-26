# 安心智能助手 V3 — Skills 域结构清单

> Skill 是 V3 的能力原子。本文按 **13 个域** 组织所有 skill，标注：来源 / 描述 / 依赖 / 目标 persona / 阶段。

> 来源说明：
> - **cowork-anthropic**：Anthropic 官方 cowork skills（直接接入）
> - **Accio**：参考 Alibaba Accio Ecommerce Mind 范式（自研封装）
> - **自建**：基于 V2 已有 services 重构 / 新写
> - **已有项目内**：从现有 21 agents 抽取出来的能力

> 阶段：**P5 起步**（Skills 运行时上线后首批） / **P7 起步**（跨境 + 销售 agent 阶段） / **后续**（Beyond P7）

相关文档：[ARCHITECTURE](./ARCHITECTURE.md) · [AGENT_PERSONAS](./AGENT_PERSONAS.md) · [CAPABILITY_MATRIX](./CAPABILITY_MATRIX.md)

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

| skill | 描述 | 来源 | 依赖 | 目标 persona | 阶段 |
|---|---|---|---|---|---|
| `office/docx-read` | Word 读取 | cowork-anthropic | anthropic-skills:docx | 全部 | P5 起步 |
| `office/docx-write` | Word 生成 + 模板 | cowork-anthropic | anthropic-skills:docx | 合同管家 / 内容总监 | P5 起步 |
| `office/docx-track-changes` | Word 轨道修订 | cowork-anthropic | anthropic-skills:docx | 合同管家 | P5 起步 |
| `office/xlsx` | Excel 读 / 写 / 计算 | cowork-anthropic | anthropic-skills:xlsx | 财税顾问 / 流程管家 | P5 起步 |
| `office/pdf-report-gen` | PDF 报告生成 | cowork-anthropic | anthropic-skills:pdf | 全部 | P5 起步 |
| `office/pptx` | PPT 生成 | cowork-anthropic | anthropic-skills:pptx | 内容总监 / 流程管家 | P7 起步 |
| `office/transcribe` | 录音 / 视频转写 | 自建 | Whisper / 通义千问 ASR | 流程管家 | P5 起步 |
| `office/email-extract` | 邮件正文 / 附件提取 | 自建 | Outlook / Gmail | 合同管家 / 流程管家 | P5 起步 |

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
| `intelligence/fetch` | 智能抓取（API / HTTP / crawl4ai / HeadlessX 自动选型） | 自建 | HeadlessX self-host + 代理池 | 全部 | P5 起步（P6 完整） |
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

| skill | 描述 | 来源 | 依赖 | 目标 persona | 阶段 |
|---|---|---|---|---|---|
| `system/intent-router` | 意图识别 + 路由到 persona | 自建 | LLM + 路由表 | 安心助理 | P5 起步 |
| `system/task-graph` | 任务 DAG 拆解 + 并行编排 | 自建 | TaskOrchestrator | 安心助理 | P2 起步 |
| `system/consensus` | 多 agent 协商基础设施 | 自建 | consensus_agent | 安心助理 | P7 起步 |
| `system/template-render` | 模板渲染（Jinja2 / Handlebars） | 自建 | - | 全部 | P5 起步 |
| `system/oauth-bridge` | OAuth 统一桥接 + 凭证刷新 | 自建 | KMS | 全部 | P4 起步 |
| `system/notification-route` | 多通道通知路由（桌面 / 推送 / IM / 邮件） | 自建 | - | 全部 | P3 起步 |
| `system/memory-recall` | 分层记忆调用（V2 已有） | 已有项目内 | hierarchical-memory | 全部 | P5 起步 |
| `system/audit-log` | 全链路审计 | 自建 | OpenTelemetry | 全部 | P2 起步 |
| `system/workflow-canvas` | 可视化工作流编辑器（后续） | 自建 | React Flow | 安心助理 / 流程管家 | 后续 |

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

### Phase: P5 起步（Skills 运行时上线后首批）

> **重头戏，~46 个 skill 一起上**：legal/8 + tax_finance/3 + operations/5 + research/3 + content/3 + design/3 + office/7 + intelligence/8 + decision/2 + system/4 (除 task-graph/notification/oauth/audit-log 外)

### Phase: P7 起步（跨境 + 销售 agent 阶段）

> **~26 个 skill 一起上**：tax_finance/3 + research/2 + marketing/4 + content/3 + ecommerce/8 + sales/5 + decision/1 + system/1 + intelligence/2

### Phase: 后续（Beyond P7）

> **~4 个**：legal/litigation-strategy / design/figma-export / sales/customer-segment / decision/scenario-analysis / system/workflow-canvas / ecommerce/customs-policy / marketing/email-campaign

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

上次更新：2026-04-26
