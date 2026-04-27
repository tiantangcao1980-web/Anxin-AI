# 安心智能助手 V3 — 应用授权清单（首批 OAuth 集成）

> 应用市场首批集成清单，按 8 大组分类。**第一批必上 5 个（P4 阶段）**，其余按优先级分布在 P3 / P4 / P5。

> 优先级标识：**P3** = 与 IM 通道并行启动 / **P4** = 应用市场 MVP / **P5** = Skills 运行时之后

> **实装状态（2026-04-27）**：标 ✅ 已实装真 OAuth provider / 🟡 mock 占位（接口已通，真 API 待接） / 🚧 完全未做。

相关文档：[ARCHITECTURE](./ARCHITECTURE.md) · [AGENT_PERSONAS](./AGENT_PERSONAS.md) · [ROADMAP](./ROADMAP.md) · [V3_DELIVERY_SUMMARY](./V3_DELIVERY_SUMMARY.md)

---

## 🎯 第一批必上 5 个（P4 启动 — 已交付 ✅）

| 应用 | 状态 | 实装文件 | 用途 | Persona 受益 |
|---|---|---|---|---|
| **飞书** | ✅ 已实装 | [`feishu_oauth.py`](../../backend/src/services/app_authorization/providers/feishu_oauth.py) + [`feishu_adapter.py`](../../backend/src/services/im_gateway/feishu_adapter.py) | IM + 文档 + 审批一体（含签名验证 + 卡片模板） | 全部 10 个 |
| **钉钉** | ✅ 已实装 | [`dingtalk_oauth.py`](../../backend/src/services/app_authorization/providers/dingtalk_oauth.py) | IM + 审批 + OA | 流程管家 + 法律顾问 |
| **Notion** | ✅ 已实装 | [`notion_oauth.py`](../../backend/src/services/app_authorization/providers/notion_oauth.py) | 文档 + OKR 知识库 | 流程管家 + 市场研究员 |
| **Shopify** | ✅ 已实装 | [`shopify_oauth.py`](../../backend/src/services/app_authorization/providers/shopify_oauth.py) + HMAC 回调验证 | 跨境独立站基础设施 | 跨境电商助手 |
| **Amazon SP-API** | 🟡 mock 占位 | [`amazon_sp.py`](../../backend/src/services/fetch/sources/ecommerce/amazon_sp.py) | 美 / 欧 / 日 主流市场（数据源 mock，OAuth 未接） | 跨境电商助手 |

> **变更说明**：原计划「企业微信」延后到 P5；以 **Amazon SP-API mock** 顶替，先打通跨境数据源。真 OAuth 待 P9+。

**支撑设施**（全部 ✅ 已落地）：
- OAuth 框架: [`backend/src/services/app_authorization/`](../../backend/src/services/app_authorization/) (`base.py` / `oauth_flow.py` / `token_store.py` 加密 / `registry.py`)
- 数据库: Alembic 030 — `app_authorizations` + `app_authorization_tokens`
- API: 6 endpoint，前缀 `/api/v3/app-authorizations`（`providers` / `list` / `authorize` / `callback` / `refresh` / `delete`）
- 前端: [`AppAuthorizationsPage.tsx`](../../frontend/src/pages/v3/capabilities/AppAuthorizationsPage.tsx) — 30+ provider 卡片市场 + 8 分类 + 搜索 + Mock

---

## 📋 完整集成清单（按 8 组）

### 1. 办公协作（IM + 协同）

| # | 应用 | 状态 | 用途 | 所需权限 | 目标 persona | 优先级 |
|---|---|---|---|---|---|---|
| 1 | **飞书 (Lark)** | ✅ | IM + 文档 + 审批 + 日历 + 多维表 | contact:user.id:readonly / calendar:calendar / docx:document / sheets:spreadsheet / drive:drive | 全部 | **P3-P4** ⭐ |
| 2 | **钉钉 (DingTalk)** | ✅ | IM + 审批 + OA + 客户 | openid / Contact.User.Read / Calendar.Read | 流程管家 / 法律顾问 / 合同管家 | **P4** ⭐ |
| 3 | **企业微信** | 🚧 | 客户群 + 朋友圈 + 客户标签 | contact:read / external_contact / message:send | 获客猎手 / 内容总监 | P5 |
| 4 | **Slack** | 🟡 adapter 占位 | 海外团队 IM | chat:write / channels:read / files:read | 出海团队所有 persona | P5 |

### 2. 文档存储（个人 / 企业云盘 + 文档平台）

| # | 应用 | 状态 | 用途 | 所需权限 | 目标 persona | 优先级 |
|---|---|---|---|---|---|---|
| 5 | **Notion** | ✅ | 文档 + OKR + 知识库 | （Notion OAuth 不使用 scope，按 Workspace 授予） | 流程管家 / 市场研究员 / 内容总监 | **P4** ⭐ |
| 6 | **Outlook / Office 365** | 🚧 | 邮件 + Word + Excel + Teams | Mail.Read / Files.ReadWrite / Calendars.Read | 流程管家 / 合同管家 | P9+ |
| 7 | **Google Workspace** | 🚧 | Gmail + Drive + Docs + Sheets + Calendar | gmail.readonly / drive.file / calendar | 出海团队 | P9+ |
| 8 | **百度网盘** | 🚧 | 国内大文件存储 | netdisk:read+write | 内容总监（素材库） | P9+ |
| 9 | **Dropbox** | 🚧 | 国际团队文件协同 | files.content.read+write / sharing | 跨境电商助手 / 出海团队 | P9+ |

### 3. CRM 销售

| # | 应用 | 状态 | 用途 | 所需权限 | 目标 persona | 优先级 |
|---|---|---|---|---|---|---|
| 10 | **Salesforce** | 🚧 | 国际 / 大客户 CRM | api / refresh_token / read+write Lead/Opportunity/Account | 获客猎手 | P9+ |
| 11 | **HubSpot** | 🚧 | 中端市场 CRM + 营销 | contacts / deals / marketing-events | 获客猎手 / 内容总监 | P9+ |
| 12 | **Zoho CRM** | 🚧 | 国内中小企业 CRM | ZohoCRM.modules.ALL / users.READ | 获客猎手 | P9+ |
| 13 | **Pipedrive** | 🚧 | 销售管线管理 | deals:read+write / contacts:read+write | 获客猎手 | P9+ |

> **现状**：lead_hunter persona 已实装 `sync-crm` API，前端可通过 mock 走完流程；真实 OAuth 待 P9+。

### 4. 法务合规

| # | 应用 | 状态 | 用途 | 所需权限 | 目标 persona | 优先级 |
|---|---|---|---|---|---|---|
| 14 | **法大大** | 🚧 | 电子合同签署 | contract:create+sign+download / sealtype:read | 合同管家 / 法律顾问 | P9+ |
| 15 | **e签宝** | 🚧 | 电子合同签署（国内 Top 2） | sign / file:upload / template | 合同管家 | P9+ |
| 16 | **北大法宝** | 🟡 数据源已接 | 法律法规 + 案例库 | search / fetch_full_text | 法律顾问 / 合同管家 / 尽调专家 | P9+ OAuth |
| 17 | **威科先行 (Wolters Kluwer)** | 🟡 数据源已接 | 法律 + 合规 + 税务 | search / digest / alert | 法律顾问 / 财税顾问 | P9+ OAuth |
| 18a | **国家法律法规库** (`flk.npc.gov.cn`) | ✅ 抓取 | 中央 + 地方公开法规 | 公开访问，受 robots / 频控 | 法律顾问 | — |
| 18b | **信用中国** (`creditchina.gov.cn`) | ✅ 抓取 | 失信被执行人 / 行政处罚 | 公开访问 | 尽调专家 | — |
| 18c | **历史文书库** (`historical_wenshu`) | ✅ 抓取 | 33,102 条文书归档 + 增量 | 内部数据 | 法律顾问 / 尽调专家 | — |

### 5. 跨境电商

| # | 应用 | 状态 | 用途 | 所需权限 | 目标 persona | 优先级 |
|---|---|---|---|---|---|---|
| 18 | **Shopify** | ✅ OAuth + 数据源 | 独立站 + 商品 + 订单 + 物流 + HMAC 回调验证 | read_products / write_products / read_orders / write_themes | 跨境电商助手 / 内容总监 | **P4** ⭐ |
| 19 | **Shopee** | 🟡 mock | 东南亚 + 拉美电商 | mp.product / mp.order / mp.logistics | 跨境电商助手 | P9+ 真 API |
| 20 | **TikTok Shop** | 🟡 mock | 短视频电商 | products / orders / promotion / fulfillment | 跨境电商助手 / 内容总监 | P9+ 真 API |
| 21 | **Amazon SP-API** | 🟡 mock | 美 / 欧 / 日 主流市场 | sellingpartnerapi: catalog / orders / inventory / advertising | 跨境电商助手 | P9+ 真 API |
| 22 | **1688 开放平台** | 🟡 mock | 国内供应链 / 国际站 | item:get / order:get / postage / supplier | 跨境电商助手 | P9+ 真 API |

> 实装文件：[`backend/src/services/fetch/sources/ecommerce/`](../../backend/src/services/fetch/sources/ecommerce/)（shopify 真 / 其他 mock）；OAuth provider：[`shopify_oauth.py`](../../backend/src/services/app_authorization/providers/shopify_oauth.py)。

### 6. 信息源（仅抓取，不发布）

| # | 应用 | 状态 | 用途 | 所需权限 | 目标 persona | 优先级 |
|---|---|---|---|---|---|---|
| 23 | **Reddit** | 🚧 | 社区舆情 + 趋势 | identity / read | 市场研究员 / 跨境电商助手 | P9+ |
| 24 | **X (Twitter)** | 🚧 | 社交舆情 + 大 V 跟踪 | tweet.read / users.read / list.read | 市场研究员 / 获客猎手 | P9+ |
| 25 | **LinkedIn** | 🚧 | B2B 线索 + 公司动态 + 招聘信号 | r_liteprofile / r_emailaddress / r_organization_admin | 获客猎手 / 尽调专家 | P9+ |
| 26 | **YouTube** | 🚧 | 视频内容信号 + 关键词 | youtube.readonly / youtubeAnalytics.readonly | 市场研究员 / 内容总监 | P9+ |
| 27 | **TikTok**（仅抓取） | 🚧 | 短视频趋势 + #标签 | open.user.info / open.video.list | 市场研究员 / 跨境电商助手 | P9+ |

> **现状**：底层 FetchService 4 层（HTTP / crawl4ai / HeadlessX / 官方 API）已就绪，可承接以上信息源；OAuth 待 P9+。

### 7. 税务财务

| # | 应用 | 状态 | 用途 | 所需权限 | 目标 persona | 优先级 |
|---|---|---|---|---|---|---|
| 28 | **金蝶云** | 🚧 | 国内财务 / ERP | finance:read / customer:read / supplier:read | 财税顾问 / 流程管家 | P9+ |
| 29 | **用友 (Yonyou)** | 🚧 | 国内财务 / ERP | nccloud:gl / ar / ap | 财税顾问 / 流程管家 | P9+ |
| 30 | **Xero** | 🚧 | 跨境财务（英美澳） | accounting.transactions / accounting.contacts | 跨境电商助手 / 财税顾问 | P9+ |
| 31 | **QuickBooks** | 🚧 | 跨境财务（北美） | accounting.read+write | 跨境电商助手 / 财税顾问 | P9+ |

### 8. 设计创作

| # | 应用 | 状态 | 用途 | 所需权限 | 目标 persona | 优先级 |
|---|---|---|---|---|---|---|
| 32 | **Figma** | 🚧 | 设计稿 + 协作 | files:read / images:read | 内容总监 | P9+ |
| 33 | **Canva** | 🚧 | 模板 + 出图 | brand:read / design:read+write | 内容总监 / 跨境电商助手 | P9+ |
| 34 | **Higgsfield** | 🚧 | AI 视频 / 创意素材 | api:render / asset:read | 内容总监 | P9+ |

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

### P3 阶段 — 与 IM 通道一起 ✅ 已交付

- ✅ 1 飞书（机器人 + 数据 OAuth 一并 + 卡片模板 + 签名验证）

### P4 阶段 — OAuth 应用市场 MVP ✅ 已交付（5 个）

- ✅ 1 飞书（P3 已上）
- ✅ 2 钉钉
- ✅ 5 Notion
- ✅ 18 Shopify（含 HMAC 回调验证）
- 🟡 21 Amazon SP-API（数据源 mock，OAuth 待 P9+）
- 🚧 3 企业微信 / 14 法大大 — 延后到 P9+

### P9+ 阶段 — 后续按业务需求批量上

- 真 OAuth：3 企业微信 / 6 Outlook / 7 Google / 10 Salesforce / 11 HubSpot
- 真 API（替换 mock）：19 Shopee / 20 TikTok Shop / 21 Amazon SP-API / 22 1688
- 信息源：23 Reddit / 24 X / 25 LinkedIn / 26 YouTube / 27 TikTok
- 法务签约：14 法大大 / 15 e签宝
- 财务：28 金蝶 / 29 用友 / 30 Xero / 31 QuickBooks
- 设计：32 Figma / 33 Canva / 34 Higgsfield
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

上次更新：2026-04-27（P3-P4 实装状态同步）
