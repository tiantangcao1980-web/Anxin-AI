# 安心智能助手 V3 — 4 横 × 4 纵能力矩阵

> 横向 4 大通用能力 × 纵向 4 大业务域 = 16 个能力单元，每个单元至少 3–5 项 skill / agent / 集成。

> **实装进度（2026-04-27）**：P0–P7 已交付 ✅ 基础设施 + 5 personas + 4 office skill + FetchService 4 层；下表每个 cell 已标注 ✅ 已实装 / 🟡 部分 / 🚧 规划中。

相关文档：[ARCHITECTURE](./ARCHITECTURE.md) · [AGENT_PERSONAS](./AGENT_PERSONAS.md) · [SKILLS_INVENTORY](./SKILLS_INVENTORY.md) · [V3_DELIVERY_SUMMARY](./V3_DELIVERY_SUMMARY.md)

---

## 横向：4 大通用能力（Cross-cutting Capabilities）

| 编号 | 能力 | 一句话 | 主要技术参考 |
|---|---|---|---|
| ① | **信息获取** | 把世界上能拿到的信息都拿过来 | HTTP+BS4+lxml / crawl4ai / HeadlessX 反检测 / 官方 API |
| ② | **调研分析** | 把信息变成洞察，每个结论可溯源 | DeepTutor 模式 + RAG-Anything (HKUDS) + MinerU + 引文追踪 |
| ③ | **设计开发** | 从想法到可看可用的成品 | canvas-design + web-artifacts-builder + Tauri + Remotion |
| ④ | **销售决策** | 多 agent 协商出最优策略 | Vibe Selling + AI-Trader 决策范式 + Hermes-Agent 协商 |

## 纵向：4 大业务域（Business Verticals）

| 编号 | 业务域 | 关联 personas |
|---|---|---|
| 🛡 | **合规经营**（法/税/财/管理） | 法律顾问 / 合同管家 / 尽调专家 / 财税顾问 / 流程管家 |
| 📈 | **增长获客**（调研/获客/推广/内容） | 市场研究员 / 获客猎手 / 内容总监 |
| 🌍 | **出海跨境**（全链路） | 跨境电商助手（+ 跨域协作） |
| 🎯 | **综合协调**（跨域编排） | 安心助理（+ 多 persona 协作） |

---

## 完整 4 × 4 矩阵（每格 3–5 项 + 实装状态）

> **图例**：✅ 已实装（P0-P7） / 🟡 部分实装 / 🚧 规划中

### 🛡 合规经营 × 4 横

| | ① 信息获取 | ② 调研分析 | ③ 设计开发 | ④ 销售决策 |
|---|---|---|---|---|
| **状态** | 🟡 部分（P6 4 法律源已接） | 🟡 部分（21 agent 可调，persona 待包） | 🟡 部分（office docx/pdf 已实装） | 🚧 规划中（P9+） |
| **agents** | regulatory_monitor / contract_investigator / legal_researcher（21 agent 可用） | legal_advisor / risk_assessor / compliance_officer（21 agent 可用） | document_drafter / template_librarian / contract_steward（21 agent 可用） | risk_assessor / consensus_agent / litigation_strategist（21 agent 可用） |
| **skills** | `legal/regulation-search` `legal/case-search` `intelligence/litigation-search` `legal/regulation-monitor` `office/email-extract` | `legal/contract-review` `legal/clause-extract` `tax_finance/tax-check` `research/deeptutor-mode` `intelligence/citation-trace` | `legal/contract-draft` `legal/template-match` `legal/redline-suggest` ✅`office/docx-track-changes` ✅`office/pdf-report-gen` | `legal/risk-grade` `tax_finance/tax-plan` `decision/risk-cost-tradeoff` `decision/multi-agent-vote` `legal/litigation-strategy` |
| **集成** | ✅ pkulaw / ✅ wkinfo / ✅ flk_npc_gov / ✅ credit_china / ✅ historical_wenshu | 北大法宝 / 法大大附件 / 内部合同库 | 法大大 / e签宝 / 飞书文档 / Word | 飞书审批 / 钉钉审批 / 内部 BPM |

### 📈 增长获客 × 4 横

| | ① 信息获取 | ② 调研分析 | ③ 设计开发 | ④ 销售决策 |
|---|---|---|---|---|
| **状态** | 🟡 部分（lead 挖掘 ✅，社媒抓取 待 P9+ 接入真 API） | ✅ 已实装（P7 市场研究员 + DeepResearch 算法） | ✅ 已实装（P7 内容总监 + office skill） | ✅ 已实装（P7 获客猎手 + LeadScoring） |
| **agents** | sentiment_agent / evidence_analyst / ✅ lead_hunter persona | ✅ market_researcher persona / sentiment_agent / evidence_analyst | ✅ content_director persona / design_agent (规划) / video_agent (规划) | ✅ lead_hunter persona / consensus_agent / ad_optimizer (规划) |
| **skills** | `intelligence/competitor-monitor` `intelligence/social-listen` `intelligence/news-aggregate` ✅`sales/lead-mining` `intelligence/recruit-signal` | ✅`research/deeptutor-mode` ✅`research/competitive-monitor` `research/multi-source-synthesize` `intelligence/sentiment-score` `marketing/audience-target` | ✅`content/article-write` `design/poster` `design/canvas-design` `design/web-artifacts-builder` `content/remotion-render` | ✅`sales/vibe-selling` ✅`sales/follow-up` `marketing/ad-optimize` `decision/multi-agent-vote` ✅`sales/quotation-draft` |
| **集成** | 🚧 Reddit / X / LinkedIn（OAuth 待接） / YouTube / TikTok / 巨量 / 艾瑞 | 艾瑞 / 易观 / 内部 PDF 库 / DeepTutor 引擎 | Figma / Canva / Higgsfield / Remotion / cowork canvas-design | 🚧 Salesforce / HubSpot / Zoho / Pipedrive / 巨量引擎 |

### 🌍 出海跨境 × 4 横

| | ① 信息获取 | ② 调研分析 | ③ 设计开发 | ④ 销售决策 |
|---|---|---|---|---|
| **状态** | ✅ 已实装（FetchService 4 层 + 5 电商源 1 真 4 mock） | ✅ 已实装（P7 跨境助手 analyze-niche / verify-supplier） | ✅ 已实装（P7 setup-store / list-to-platforms） | ✅ 已实装（P7 AI 议价 + VAT 指引） |
| **agents** | ✅ ecommerce_assistant persona / sentiment_agent / regulatory_monitor | ✅ ecommerce_assistant persona（含 selection 能力）/ risk_assessor | ✅ ecommerce_assistant persona / document_drafter / listing 能力（内置） | tax_compliance / consensus_agent / 自建 pricing_agent (内置 negotiate) |
| **skills** | ✅`ecommerce/platform-data-pull` `ecommerce/keyword-research` `ecommerce/customs-policy` `intelligence/social-listen` `office/api-call` | ✅`ecommerce/product-selection` `research/deeptutor-mode` ✅`ecommerce/oversea-compliance` `intelligence/citation-trace` `tax_finance/cross-border-tax` | ✅`ecommerce/store-setup` ✅`ecommerce/listing-optimize` `design/canvas-design` `design/web-artifacts-builder` `content/multilingual` | ✅`ecommerce/pricing-strategy` `marketing/ad-optimize` `decision/multi-agent-vote` `ecommerce/logistics-plan` `sales/vibe-selling` |
| **集成** | 🟡 ✅ Shopify 真 / 🟡 Shopee/TikTok Shop/Amazon SP-API/1688 mock / 🚧 Reddit / Helium 10 | TikTok / Reddit 趋势 / 海关数据 / GDPR / IPO 数据库 | ✅ Shopify / Higgsfield / Canva / WordPress / Webflow | 🚧 Stripe / PayPal / 万里汇 / Meta / Google / TikTok Ads |

### 🎯 综合协调 × 4 横

| | ① 信息获取 | ② 调研分析 | ③ 设计开发 | ④ 销售决策 |
|---|---|---|---|---|
| **状态** | ✅ 已实装（IM gateway + 飞书 + 邮件） | 🟡 部分（cross-search 框架就位，跨域 RAG 待 P10） | ✅ 已实装（P2 task_orchestrator + P3 配对授权 + P5 模板渲染） | 🟡 部分（多 agent 协商待 P9+ 抽象） |
| **agents** | coordinator / workforce / requirement_analyst（21 agent） | coordinator / consensus_agent / evidence_analyst（21 agent） | coordinator / workforce / template_librarian（21 agent） | coordinator / consensus_agent / workforce（21 agent） |
| **skills** | `intelligence/cross-search` `system/intent-router` `office/inbox-aggregate` `office/calendar-coordinate` ✅`system/oauth-bridge` | `intelligence/cross-search` `research/multi-source-synthesize` ✅`system/task-graph` `intelligence/citation-trace` `system/memory-recall` | ✅`system/task-graph` `system/template-render` ✅`office/pdf-report-gen` `system/workflow-canvas` `system/notification-route` | `decision/multi-agent-vote` `system/consensus` `decision/risk-cost-tradeoff` `system/escalate-to-human` `system/audit-log` |
| **集成** | ✅ 飞书 / ✅ 钉钉 (OAuth) / 企微 / Slack / WhatsApp / 邮件 | 内部知识库 / 经验库 / Evolver | 桌面通知中心 / 移动推送 / ✅ IM 卡片（飞书） | 飞书审批 / 内部 BPM / 钉钉智能填表 |

---

## 横向能力的「域适配」补充说明

### ① 信息获取栈分级

| 优先级 | 方式 | 适用 | 例子 |
|---|---|---|---|
| P1 | **官方 API** | 最稳、最合规 | 企查查 / Shopify / 飞书 / 国务院政策库 |
| P2 | **HTTP + BeautifulSoup4 + lxml** | 静态页 | 北大法宝详情页、政府公告 |
| P3 | **crawl4ai** | 动态 SPA、无强反爬 | 行业资讯站、Reddit |
| P4 | **HeadlessX self-host** | 反检测、登录态、人机验证 | LinkedIn、X、TikTok 个人页 |
| P5 | **官方提供的 Webhook** | 实时推送 | 飞书消息事件、Stripe 支付事件 |

> **合规底线**：robots.txt + 频率限制 + UA 标识 + 不抓个人隐私 + 商业站点签 ToS。

### ② 调研分析的「DeepTutor 闭环」

```
PDF / 网页 / 视频
       ↓
MinerU 解析（表 / 图 / 公式 / 段落）
       ↓
RAG-Anything 索引（多模态向量库）
       ↓
DeepTutor 提问 + 引文跳转
       ↓
经验沉淀（Evolver）
```

### ③ 设计开发的「分层选型」

| 层 | 工具 | 何时用 |
|---|---|---|
| 静态视觉 | canvas-design (cowork-anthropic) | 海报 / 封面 / 单图 |
| 动态网页 | web-artifacts-builder (cowork-anthropic) | 落地页 / Demo / 演示 |
| 视频 | Remotion + 模板 | 30s 短视频 / 数据可视化 |
| 本地应用 | Tauri + React | 桌面工具 / 离线办公 |
| 文档 | docx / pptx / pdf (anthropic-skills) | Word / PPT / PDF 报告 |

### ④ 销售决策的「多 agent 协商范式」

```
任务（如：广告预算调整）
       ↓
Persona 启动多 agent（保守 / 激进 / 数据派 / 历史派 / 用户派）
       ↓
各 agent 独立分析 + 出方案
       ↓
consensus_agent 投票 / 加权 / 仲裁
       ↓
高风险时 escalate-to-human
       ↓
执行 + 复盘 + 经验沉淀
```

---

## 4 × 4 矩阵的「优先级热力图」

> 颜色含义：🔥 P0 必备 / 🟡 P3-P4 阶段 / 🟢 P5+ 后续

| | ① 信息获取 | ② 调研分析 | ③ 设计开发 | ④ 销售决策 |
|---|---|---|---|---|
| 🛡 合规经营 | 🔥 | 🔥 | 🔥 | 🔥 |
| 📈 增长获客 | 🟡 | 🔥 | 🟡 | 🟡 |
| 🌍 出海跨境 | 🟢 | 🟡 | 🟡 | 🟢 |
| 🎯 综合协调 | 🔥 | 🔥 | 🟡 | 🟡 |

> **解读**：合规经营是基本盘（P0 必须做），综合协调是骨架（P0 必须有），增长 + 出海是 P3-P5 的增长曲线。

## 实装状态热力图（2026-04-27 实际版）

> 颜色含义：🟢 已实装 / 🟡 部分实装 / 🔴 待实装

| | ① 信息获取 | ② 调研分析 | ③ 设计开发 | ④ 销售决策 |
|---|---|---|---|---|
| 🛡 合规经营 | 🟢（4 法律源已接） | 🟡（21 agent 可调，persona 待包） | 🟡（office docx/pdf 已实装） | 🔴（P9+） |
| 📈 增长获客 | 🟡（lead_hunter ✅，社媒 OAuth 待接） | 🟢（market_researcher ✅） | 🟢（content_director ✅） | 🟢（lead_hunter + LeadScoring ✅） |
| 🌍 出海跨境 | 🟢（FetchService 4 层 + 5 源） | 🟢（analyze-niche ✅） | 🟢（setup-store ✅） | 🟢（AI 议价 + VAT ✅） |
| 🎯 综合协调 | 🟢（IM gateway + 飞书） | 🟡（cross-search 框架，跨域 RAG 待 P10） | 🟢（task_orchestrator + 配对授权） | 🟡（多 agent 协商待 P9+） |

---

## 能力 × Persona 反向映射（速查 + 实装状态）

> ✅ 已实装 / 🟡 部分（依赖底层就位） / ⚪ 不涉及 / 🚧 P9+ 规划中

| Persona ↓ / 能力 → | ① 信息获取 | ② 调研分析 | ③ 设计开发 | ④ 销售决策 |
|---|---|---|---|---|
| 🤖 安心助理 🚧 | 🚧 跨域聚合 | 🚧 跨域 RAG | 🚧 工作流编排（task_orchestrator 可用） | 🚧 多 agent 协商 |
| ⚖️ 法律顾问 🚧 | 🟡 法规检索（4 法律源已接） | 🚧 案例分析 | ⚪ | 🚧 风险评级 |
| 📜 合同管家 🚧 | 🚧 合同入库 | 🚧 合同审查 | 🟡 起草+红线（office/docx 已实装） | ⚪ |
| 🔍 尽调专家 🚧 | 🟡 多源抓取（FetchService 已可用） | 🚧 DD 分析 | 🟡 报告导出（office/pdf 已实装） | 🚧 综合评级 |
| 💰 财税顾问 🚧 | 🚧 政策订阅 | 🚧 财务分析 | 🟡 方案表（office/xlsx 已实装） | 🚧 节税决策 |
| 📋 流程管家 ✅ | ✅ 多端聚合 | ⚪ | ✅ 报告 / 看板 | ✅ 审批决策 |
| 📊 市场研究员 ✅ | ✅ 多源抓取 | ✅ 深度研读（DeepResearch 算法） | ✅ 摘要 / 图表 | ⚪ |
| 🎯 获客猎手 ✅ | ✅ 线索挖掘 | ✅ 客户画像（LeadScoring） | ✅ 销售物料（邮件模板） | ✅ 多 agent 投放（待 P9+ 完整） |
| ✍️ 内容总监 ✅ | ✅ 素材抓取 | ⚪ | ✅ 设计核心 | ⚪ |
| 🌍 跨境电商助手 ✅ | ✅ 平台数据（5 源） | ✅ 选品 / 趋势 | ✅ 独立站 / 商品页 | ✅ 出价（AI 议价） |

---

上次更新：2026-04-27（P0-P7 实装状态同步）
