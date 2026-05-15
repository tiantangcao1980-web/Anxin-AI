# 安心智能助手 · 连接器目录（CONNECTORS.md）

> 本文档列出 Anxin AI 全 10 个 persona 插件可对接的 MCP server / 第三方 API / 本地数据源。
> 设计参考 Anthropic [`claude-for-legal`](https://github.com/anthropics/claude-for-legal) 和
> [`claude-for-financial-services`](https://github.com/anthropics/claude-for-financial-services) 的 `CONNECTORS.md`，并按中国大陆业务场景作了重排。

任何 persona 启用某个 connector 前都必须：

1. 在该 persona 的 `CLAUDE.md` 执业画像里声明（启用 / 禁用 / 默认账号）；
2. 通过统一的 KMS 加密 OAuth token 走 P4 落地的 `backend/src/oauth/`；
3. 在 `.env` 中提供 endpoint / credentials；模板见 `.env.example`。

---

## 一、协作 IM（默认必装）

| Connector | Endpoint | 适用 persona | 用途 |
|---|---|---|---|
| 飞书 Lark | `https://open.feishu.cn/open-apis` | **全部** | 卡片推送 / 文件读写 / 群消息 / 审批拉取 |
| 钉钉 DingTalk | `https://api.dingtalk.com` | **全部** | 通讯录 / 待办 / 日志 / 审批 / 群机器人 |
| 企业微信 | `https://qyapi.weixin.qq.com/cgi-bin/` | 全部 | 客户群 / 朋友圈营销 / 应用消息 |
| Slack（外资客户） | `https://slack.com/api` | growth / cross-border | 频道读写 |

OAuth 框架已经在 P4 落地。新增 connector → 在 `backend/src/oauth/providers/` 新增 provider 即可。

## 二、办公 / 知识库

| Connector | 适用 persona | 用途 |
|---|---|---|
| 飞书云文档 | 全部 | docs / sheets / bitable 读写 |
| Notion | 全部 | 数据库 / 页面 / 评论 |
| 钉钉文档 / 云盘 | 全部 | 表格 / 文件读写 |
| 语雀 | 全部 | 知识库读写 |
| Google Drive | growth / cross-border | docs / sheets / slides |
| OneDrive / SharePoint | 全部 | M365 套件 |
| Egnyte | dd-expert / contract-steward | 企业级 DMS |
| iManage | contract-steward / dd-expert | 法务专用 DMS |

## 三、法务 / 合规

| Connector | 适用 persona | 用途 |
|---|---|---|
| 中国裁判文书网 | legal-advisor / dd-expert / contract-steward | 判决书检索 |
| 国家法律法规数据库 | legal-advisor | 现行法规检索 |
| 信用中国 | dd-expert | 企业失信 / 行政处罚 |
| 企查查 / 天眼查 API | dd-expert / lead-hunter | 工商 / 司法 / 风险 |
| 国家知识产权局公示 | legal-advisor / dd-expert | 商标 / 专利 / 版权 |
| 中国海关 / 商务部公告 | cross-border-ecom / legal-advisor | 进出口合规 |
| CourtListener（美国） | cross-border-ecom + legal-advisor | 跨境诉讼 |
| 国务院政策文件库 | regulation-monitor cookbook | 政策爬取 |

## 四、财税 / ERP

| Connector | 适用 persona | 用途 |
|---|---|---|
| 国家税务总局电子发票 | finance-tax-advisor | 发票真伪查验 |
| 增值税发票综合服务平台 | finance-tax-advisor | 进项 / 销项 |
| 用友 U8 / NC / YonSuite | finance-tax-advisor / process-steward | ERP 数据 |
| 金蝶 K3 / 星空 / 云星辰 | finance-tax-advisor / process-steward | ERP 数据 |
| SAP S/4HANA OData | finance-tax-advisor / process-steward | ERP 数据（外资 / 上市公司） |
| 银行直联（CMB / ICBC / BOC） | finance-tax-advisor | 余额 / 流水 |
| 网易七鱼 / 钉钉 CRM | lead-hunter / process-steward | 客户主数据 |

## 五、增长 / 市场研究

| Connector | 适用 persona | 用途 |
|---|---|---|
| SearXNG（本地部署） | market-researcher | 元搜索（已在 `searxng/` 内置） |
| 百度指数 / 微信指数 | market-researcher | 中国搜索趋势 |
| 抖音开放平台 | content-director / lead-hunter | 短视频投放 / DM |
| 公众号开放接口 | content-director | 推文 / 菜单 |
| 小红书蒲公英 | content-director / lead-hunter | KOC 投放 |
| LinkedIn Sales Navigator | lead-hunter | 海外线索 |
| SEMRush / Ahrefs | market-researcher / content-director | SEO 与竞品 |
| Crunchbase API | market-researcher / dd-expert | 海外公司情报 |
| Aiera / MT Newswires | market-researcher | 财经资讯（如启用） |

## 六、跨境电商

| Connector | 适用 persona | 用途 |
|---|---|---|
| Amazon SP-API | cross-border-ecom | listing / 订单 / 库存 / 广告 |
| Shopify Admin API | cross-border-ecom / content-director | 独立站全功能 |
| eBay Browse API | cross-border-ecom | 竞品 / 销售 |
| Walmart / Mercado Libre | cross-border-ecom | 多平台铺货 |
| TikTok Shop Partner | content-director / cross-border-ecom | TikTok 电商 |
| Stripe / PayPal | cross-border-ecom / finance-tax-advisor | 收款 / 退款 |
| HMRC VAT / EU OSS | cross-border-ecom / finance-tax-advisor | 欧美 VAT |
| 阿里国际站 / Made-in-China | cross-border-ecom / lead-hunter | B2B 询盘 |

## 七、桌面 / 本地数据（Desktop & NAS）

| Connector | 适用 persona | 用途 |
|---|---|---|
| `tauri-rust-sandbox` | 全部 | 本地文件 / Word / Excel 操作（已在 `desktop/`） |
| SQLCipher 加密本地 DB | 全部 | 私有数据存储 |
| 本地 LLM（Qwen / DeepSeek / 智谱） | 全部 | 隐私模式 |
| Synology NAS（CIFS / WebDAV） | 全部 | 公司本地知识库 |

## 八、Office Skill（已在 `skills/office/`）

| Skill | 用途 | 调用 persona |
|---|---|---|
| `office/docx` | Word 渲染 / 跟踪修订 | contract-steward / process-steward |
| `office/xlsx` | Excel 模板 / 公式 / 透视表 | finance-tax-advisor / cross-border-ecom |
| `office/pptx` | PPT 提案 / 品牌一致性 | content-director / market-researcher |
| `office/pdf` | PDF 拆分 / 合并 / OCR / 抽取 | 全部 |

---

## 新增 Connector 步骤

1. 在 `backend/src/oauth/providers/<name>.py` 新增 OAuth 客户端（参考 `feishu.py`、`shopify.py`）。
2. 在 `backend/src/integrations/<name>/` 加 SDK 封装。
3. 在 `CONNECTORS.md`（本文件）新增一行。
4. 涉及 persona 的 `CLAUDE.md` 增加 `## 5. 集成系统` 字段。
5. 跑 `python3 scripts/claude-plugin-validate.py` 通过。
6. 在 `.env.example` 补 endpoint / scope 模板（不要写真实 secret）。

## 安全守门

- **密钥管理**：所有 OAuth token 走 KMS 加密存储；本地开发用 `.env.local`，禁止入 git。
- **法域**：跨境数据连接器（Amazon / LinkedIn / Stripe）必须显式声明数据出境合规路径（CAC 评估 / SCC）。
- **PII**：连接器返回的个人信息字段在写入知识库前自动脱敏（参考 `backend/src/utils/pii_masking.py`）。
- **限流**：所有外部 API 走 `backend/src/integrations/_rate_limiter.py` 统一限流，避免被封号。
