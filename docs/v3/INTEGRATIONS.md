# 安心智能助手 V3 — 应用授权清单（首批 OAuth 集成）

> 应用市场首批集成清单，按 8 大组分类。**第一批必上 5 个（P4 阶段）**，其余按优先级分布在 P3 / P4 / P5。

> 优先级标识：**P3** = 与 IM 通道并行启动 / **P4** = 应用市场 MVP / **P5** = Skills 运行时之后

相关文档：[ARCHITECTURE](./ARCHITECTURE.md) · [AGENT_PERSONAS](./AGENT_PERSONAS.md) · [ROADMAP](./ROADMAP.md)

---

## 🎯 第一批必上 5 个（P4 启动 = 8 周内）

| 应用 | 用途 | Persona 受益 | 难度 |
|---|---|---|---|
| 🟢 **飞书** | IM + 文档 + 审批一体 | 全部 10 个 | 中 |
| 🟢 **钉钉** | IM + 审批 + OA | 流程管家 + 法律顾问 + 全部 | 中 |
| 🟢 **企业微信** | 客户管理 + 群运营 | 获客猎手 + 内容总监 | 中 |
| 🟢 **Notion** | 文档 + OKR 知识库 | 流程管家 + 市场研究员 | 易 |
| 🟢 **Shopify** | 跨境独立站基础设施 | 跨境电商助手 | 中 |

> 这 5 个覆盖：国内办公（3）+ 知识管理（1）+ 出海起步（1），是 V3 价值闭环最低门槛。

---

## 📋 完整集成清单（按 8 组）

### 1. 办公协作（IM + 协同）

| # | 应用 | 用途 | 所需权限 | 目标 persona | 优先级 |
|---|---|---|---|---|---|
| 1 | **飞书 (Lark)** | IM + 文档 + 审批 + 日历 + 多维表 | message:send / docs:read+write / approval / calendar / bitable | 全部 | **P3-P4** ⭐ |
| 2 | **钉钉 (DingTalk)** | IM + 审批 + OA + 客户 | im:send / workflow / contact / cspace | 流程管家 / 法律顾问 / 合同管家 | **P4** ⭐ |
| 3 | **企业微信** | 客户群 + 朋友圈 + 客户标签 | contact:read / external_contact / message:send | 获客猎手 / 内容总监 | **P4** ⭐ |
| 4 | **Slack** | 海外团队 IM | chat:write / channels:read / files:read | 出海团队所有 persona | P5 |

### 2. 文档存储（个人 / 企业云盘 + 文档平台）

| # | 应用 | 用途 | 所需权限 | 目标 persona | 优先级 |
|---|---|---|---|---|---|
| 5 | **Notion** | 文档 + OKR + 知识库 | databases:read+write / pages:read+write | 流程管家 / 市场研究员 / 内容总监 | **P4** ⭐ |
| 6 | **Outlook / Office 365** | 邮件 + Word + Excel + Teams | Mail.Read / Files.ReadWrite / Calendars.Read | 流程管家 / 合同管家 | P4 |
| 7 | **Google Workspace** | Gmail + Drive + Docs + Sheets + Calendar | gmail.readonly / drive.file / calendar | 出海团队 | P5 |
| 8 | **百度网盘** | 国内大文件存储 | netdisk:read+write | 内容总监（素材库） | P5 |
| 9 | **Dropbox** | 国际团队文件协同 | files.content.read+write / sharing | 跨境电商助手 / 出海团队 | P5 |

### 3. CRM 销售

| # | 应用 | 用途 | 所需权限 | 目标 persona | 优先级 |
|---|---|---|---|---|---|
| 10 | **Salesforce** | 国际 / 大客户 CRM | api / refresh_token / read+write Lead/Opportunity/Account | 获客猎手 | P5 |
| 11 | **HubSpot** | 中端市场 CRM + 营销 | contacts / deals / marketing-events | 获客猎手 / 内容总监 | P5 |
| 12 | **Zoho CRM** | 国内中小企业 CRM | ZohoCRM.modules.ALL / users.READ | 获客猎手 | P5 |
| 13 | **Pipedrive** | 销售管线管理 | deals:read+write / contacts:read+write | 获客猎手 | P5 |

### 4. 法务合规

| # | 应用 | 用途 | 所需权限 | 目标 persona | 优先级 |
|---|---|---|---|---|---|
| 14 | **法大大** | 电子合同签署 | contract:create+sign+download / sealtype:read | 合同管家 / 法律顾问 | P4 |
| 15 | **e签宝** | 电子合同签署（国内 Top 2） | sign / file:upload / template | 合同管家 | P4 |
| 16 | **北大法宝** | 法律法规 + 案例库 | search / fetch_full_text | 法律顾问 / 合同管家 / 尽调专家 | P4 |
| 17 | **威科先行 (Wolters Kluwer)** | 法律 + 合规 + 税务 | search / digest / alert | 法律顾问 / 财税顾问 | P5 |

### 5. 跨境电商

| # | 应用 | 用途 | 所需权限 | 目标 persona | 优先级 |
|---|---|---|---|---|---|
| 18 | **Shopify** | 独立站 + 商品 + 订单 + 物流 | read_products / write_products / read_orders / write_themes | 跨境电商助手 / 内容总监 | **P4** ⭐ |
| 19 | **Shopee** | 东南亚 + 拉美电商 | mp.product / mp.order / mp.logistics | 跨境电商助手 | P5 |
| 20 | **TikTok Shop** | 短视频电商 | products / orders / promotion / fulfillment | 跨境电商助手 / 内容总监 | P5 |
| 21 | **Amazon SP-API** | 美 / 欧 / 日 主流市场 | sellingpartnerapi: catalog / orders / inventory / advertising | 跨境电商助手 | P5 |
| 22 | **1688 开放平台** | 国内供应链 / 国际站 | item:get / order:get / postage / supplier | 跨境电商助手 | P5 |

### 6. 信息源（仅抓取，不发布）

| # | 应用 | 用途 | 所需权限 | 目标 persona | 优先级 |
|---|---|---|---|---|---|
| 23 | **Reddit** | 社区舆情 + 趋势 | identity / read | 市场研究员 / 跨境电商助手 | P5 |
| 24 | **X (Twitter)** | 社交舆情 + 大 V 跟踪 | tweet.read / users.read / list.read | 市场研究员 / 获客猎手 | P5 |
| 25 | **LinkedIn** | B2B 线索 + 公司动态 + 招聘信号 | r_liteprofile / r_emailaddress / r_organization_admin | 获客猎手 / 尽调专家 | P5 |
| 26 | **YouTube** | 视频内容信号 + 关键词 | youtube.readonly / youtubeAnalytics.readonly | 市场研究员 / 内容总监 | P5 |
| 27 | **TikTok**（仅抓取） | 短视频趋势 + #标签 | open.user.info / open.video.list | 市场研究员 / 跨境电商助手 | P5 |

### 7. 税务财务

| # | 应用 | 用途 | 所需权限 | 目标 persona | 优先级 |
|---|---|---|---|---|---|
| 28 | **金蝶云** | 国内财务 / ERP | finance:read / customer:read / supplier:read | 财税顾问 / 流程管家 | P5 |
| 29 | **用友 (Yonyou)** | 国内财务 / ERP | nccloud:gl / ar / ap | 财税顾问 / 流程管家 | P5 |
| 30 | **Xero** | 跨境财务（英美澳） | accounting.transactions / accounting.contacts | 跨境电商助手 / 财税顾问 | P5 |
| 31 | **QuickBooks** | 跨境财务（北美） | accounting.read+write | 跨境电商助手 / 财税顾问 | P5 |

### 8. 设计创作

| # | 应用 | 用途 | 所需权限 | 目标 persona | 优先级 |
|---|---|---|---|---|---|
| 32 | **Figma** | 设计稿 + 协作 | files:read / images:read | 内容总监 | P5 |
| 33 | **Canva** | 模板 + 出图 | brand:read / design:read+write | 内容总监 / 跨境电商助手 | P5 |
| 34 | **Higgsfield** | AI 视频 / 创意素材 | api:render / asset:read | 内容总监 | P5 |

---

## 集成框架要点（统一约定）

所有集成必须满足：

| 维度 | 要求 |
|---|---|
| **凭证** | KMS 加密存储；access_token + refresh_token 分离；tenant_id 隔离 |
| **授权范围** | 最小授权；按 persona / 任务申请；用户可看到「正在使用 X 权限」 |
| **失效处理** | refresh_token 自动刷新；过期后 UI 引导重新授权；任务可恢复 |
| **数据回流** | 增量同步优先；全量回流要明确告知用户 |
| **审计** | 每次调用记录：tenant / user / persona / scope / endpoint / 时间 |
| **降级** | 第三方服务故障 → persona 提示 + 建议替代方案 |
| **成本** | 按集成统计调用量 + 成本，Top 5 上 dashboard |

---

## Roadmap 视角（按阶段）

### P3 阶段（W6-W7）— 与 IM 通道一起

- 1 飞书（机器人 + 数据 OAuth 一并）

### P4 阶段（W8-W9）— OAuth 应用市场 MVP

- 2 钉钉
- 3 企业微信
- 5 Notion
- 18 Shopify
- 14 法大大（视谈判进度）

### P5 阶段（W12+）— 后续按业务需求批量上

- 6 Outlook / 7 Google / 10 Salesforce / 11 HubSpot
- 21 Amazon SP-API / 23 Reddit / 25 LinkedIn
- 28 金蝶 / 30 Xero
- 32 Figma / 33 Canva
- 其余按客户需求排队

---

## 集成 × Persona 反向矩阵（速查）

| Persona ↓ / 集成组 → | IM | 文档 | CRM | 法务 | 跨境 | 信息源 | 税财 | 设计 |
|---|---|---|---|---|---|---|---|---|
| 🤖 安心助理 | 飞书/钉钉/企微 | 全部 | - | - | - | 全部 | - | - |
| ⚖️ 法律顾问 | 飞书 | Notion/Outlook | - | 北大法宝/威科 | - | - | - | - |
| 📜 合同管家 | 飞书/钉钉 | Outlook/Notion | - | 法大大/e签宝 | - | - | - | - |
| 🔍 尽调专家 | 飞书 | Notion | - | 北大法宝 | - | LinkedIn/X/Reddit | - | - |
| 💰 财税顾问 | 飞书 | Outlook | - | 威科 | - | - | 金蝶/用友/Xero/QB | - |
| 📋 流程管家 | 全 IM | Notion/Outlook/Google | - | - | - | - | - | - |
| 📊 市场研究员 | 飞书 | Notion | - | - | - | 全部 | - | - |
| 🎯 获客猎手 | 企微/飞书 | - | 全部 CRM | - | - | LinkedIn/X | - | - |
| ✍️ 内容总监 | 企微 | Notion/百度网盘 | HubSpot | - | - | YouTube/TikTok | - | Figma/Canva/Higgsfield |
| 🌍 跨境电商助手 | Slack | Dropbox/Google | - | - | 全部 | Reddit/X/TikTok | Xero/QB | Canva/Higgsfield |

---

上次更新：2026-04-26
