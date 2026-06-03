# 第三方集成就绪矩阵（Integration Readiness Matrix）

> 任务 F「诚实化」审计产物 · 2026-06-04
> 目标：杜绝「未实现却显示已实现」「未配置却静默假成功」。
> 每一行均给出 `file:line` 代码依据；fail-fast 风险给出证据与处置。

本仓路径前缀：`backend/`（相对仓库根）。

---

## 一、就绪矩阵（逐集成）

| 集成 | 代码状态 | 未配置时行为 | 激活所需外部输入 | 依据 |
|------|----------|--------------|------------------|------|
| **IM·飞书 (Feishu) adapter** | 完整 | **fail-fast ✅** —— `_get_tenant_access_token` 缺 `app_id/app_secret` 直接 `raise RuntimeError`；webhook 验签 fail-closed | app_id / app_secret / encrypt_key / verify_token（自助填凭据） | `services/im_gateway/feishu_adapter.py:134-135`；验签 `:341-348` |
| **IM·微信 / 钉钉 / Telegram / Slack adapter** | 骨架（占位） | **fail-fast ✅** —— 4 个抽象方法全部 `raise NotImplementedError("P3+ 实现")`，不会假装连上 | 各平台凭据 + 需先做 adapter 真实现（P3+） | `wechat_adapter.py:22-38`、`dingtalk_adapter.py:22-37`、`telegram_adapter.py:22-38`、`slack_adapter.py:22-38` |
| **IM·Discord** | 未实现（仅枚举预留） | **fail-fast ✅** —— registry 未注册，`build("discord")` 抛 `KeyError` | adapter 文件 + 凭据（P3+） | 枚举 `im_gateway/models.py:47`；registry 仅注册 5 个 `registry.py:78-85` |
| **IM 渠道 `/test` 连接自检** | 部分（仅配置完整性自检，**不做真实协议握手**） | **honest ✅** —— 缺字段返 `ok=False`+`missing`；齐全返 `ok=True` 但 message/detail **显式标注「未执行真实协议握手」**，不谎称 connected | 无（自检逻辑就绪）；真实握手属 P3+ | `services/im_gateway/channels_service.py:221-250`（顶部边界声明 `:8-13`）；状态推导 `_derive_status` 缺字段→`UNCONFIGURED` `:86-93` |
| **支付·微信支付 (WeChat Pay v3)** | 完整 | **fail-fast ✅** —— `_ensure_configured` 缺商户配置 `raise PaymentProviderConfigError`；webhook RSA-SHA256 验签 fail-closed | 商户号/证书序列号/商户私钥/平台公钥 + 公网回调域名（**需商务：微信支付商户入驻**） | 配置校验 `services/payment_service.py:336-347`；工厂 `:686-715`；webhook 验签 `routes/payments.py:379-402` |
| **支付·支付宝 (Alipay)** | 完整 | **fail-fast ✅** —— 缺 app_id/公钥 `raise PaymentProviderConfigError`；webhook RSA2 验签 fail-closed | app_id/应用私钥/支付宝公钥/网关（**需商务：支付宝开放平台签约**） | `services/payment_service.py:548-562`；webhook `routes/payments.py:443-462` |
| **支付·Mock 渠道** | 完整（仅开发） | **fail-fast ✅** —— `staging/production` 下选 mock 直接 `raise PaymentProviderConfigError`，禁止假支付上线 | 无（开发用）；生产必须切真实 provider | `services/payment_service.py:696-699` |
| **电签·e签宝 (ESignBao)** | 完整 | **fail-fast ✅** —— `_check_config` 缺 `APP_ID/APP_SECRET` `raise ESignProviderConfigError`，且在每次 `_request` 前调用 | ESIGN_BAO_APP_ID / APP_SECRET（**需商务：e签宝企业认证**） | 校验 `services/esign_service.py:498-502`；`_request` 前置调用 `:513` |
| **电签·法大大 (FaDaDa)** | 完整 | **fail-fast ✅** —— `_check_config` 缺凭据 `raise ESignProviderConfigError`，`_request` 前置 | FADADA_APP_ID / APP_SECRET / ACCESS_TOKEN（**需商务：法大大签约**） | `services/esign_service.py:717-724` |
| **电签·GDCA 广东政务签** | 骨架（placeholder） | **fail-fast ✅** —— 调任意方法立即 `raise ESignProviderConfigError("待接入")` | 凭据 + provider 真实现（**需商务/合作方对接**） | `services/esign_service.py:958-984` |
| **电签·粤企签 / 粤商通 (YueQiQian)** | 骨架（placeholder） | **fail-fast ✅** —— 同上，立即 raise | 凭据 + 真实现（**需商务/合作方**） | `services/esign_service.py:1007-1032` |
| **电签·Mock** | 完整（仅开发） | **fail-fast ✅** —— `staging/production` 选 mock 直接 raise | 无；生产必须切真实 provider | `services/esign_service.py:1083-1084` |
| **OAuth·飞书 / 钉钉 / Notion / Shopify / Amazon SP** | 完整（授权码流程） | **已强化为 fail-fast ✅**（本次修复）—— 未配置 `client_id/client_secret` 时 `start`/`callback` `raise OAuthConfigError`→HTTP 503；**修复前为「假成功 ⚠️」**（见下方风险 §二.1） | 各平台 client_id / client_secret（自助填凭据；钉钉/Notion 需在各自开放平台建应用）+ `OAUTH_TOKEN_ENCRYPTION_KEY` | 守卫 `services/app_authorization/oauth_flow.py:_require_configured`（`start`/`callback` 调用）；路由映射 `routes/app_authorizations.py`（OAuthConfigError→503） |
| **OAuth·token 加密存储 (TokenStore)** | 完整 | **fail-fast ✅** —— `OAUTH_TOKEN_ENCRYPTION_KEY` 未配置 `raise TokenStoreConfigError` | OAUTH_TOKEN_ENCRYPTION_KEY（Fernet key，自助生成） | `services/app_authorization/token_store.py:51-89` |
| **OA 集成·飞书/钉钉/企微 (oa_integration_service)** | 部分（飞书有真实 token 流；审批/同步部分为 mock） | **fail-fast ✅（生产）/ 受控 mock（开发）** —— `_commercial_environment()` 下缺凭据或未接真实 API `raise OAProviderConfigError`，仅 dev 返回 `mock_token`/mock 用户并 `logger.warning` | 各平台 app 凭据（**部分能力需商务对接**） | 守卫 `services/oa_integration_service.py:36-40`、`117-123` |
| **搜索·Web 搜索 (Tavily/Bing/SearXNG/DDG)** | 完整（多源降级链） | **honest 降级 ✅（非假数据）** —— Tavily/Bing 无 key 时该源 `return []` 并跳到下一源；末端 DuckDuckGo 无 key 可用；全失败 `logger.warning` 后返 `[]`，**不伪造结果** | TAVILY_API_KEY / BING_SEARCH_KEY（可选增强；自助） | `services/web_search_service.py:114-115`、降级链 `:60-80` |
| **数据源·企查查/天眼查/爱企查/GSXT（尽调工商）** | 部分（公开端点爬取，无 API-key 集成） | **honest ✅** —— `_fetch_real_company_data` 各源失败 `logger.debug` 跳过，全失败返 `None`（非伪造）；DD persona 明确标注 mock 占位、注「P9 对接 qichacha」 | 若要稳定数据需企查查/天眼查 **商业 API（需商务采购）** | `services/due_diligence_service.py:540-608`；persona 标注 `agents/personas/due_diligence_expert.py:186`、`510` |
| **数据源·威科先行 wkinfo（法律库）** | 骨架（stub，真实调用仅注释） | **假数据 ⚠️（已记录，未改）** —— `WKINFO_API_KEY` 未配置时 `logger.warning` 后返 `_build_mock_results`（伪造结果）；即便配置也走 stub 返 mock | WKINFO_API_KEY + provider 真实现（**需商务采购**） | `services/fetch/sources/legal/wkinfo.py:87-111` |
| **数据源·Amazon SP / Shopee（电商 fetch sources）** | 骨架（纯 mock） | **假数据 ⚠️（已记录，未改）** —— 永远返回 `_build_mock_product`/假订单 | 平台凭据 + 真实现（**需商务对接**） | `services/fetch/sources/ecommerce/amazon_sp.py:184-200`、`shopee.py:174` |

---

## 二、fail-fast 风险点（「未配置却静默假成功」）与处置

### 2.1 【已修复】OAuth provider 未配置 client_id 仍返回「假绿」授权 URL — 真实「假绿」

- **证据（修复前）**：`OAuthFlowService.start` → `provider.authorize_url(...)` 直接拼 URL，**未校验** `client_id` 是否非空。各 provider 的 `authorize_url` 同样不校验（如 `providers/dingtalk_oauth.py:182-192` 把 `"client_id": self.client_id`（可能为空串）写进 URL）。
- **后果**：未在后台/环境变量配置钉钉/Notion 等凭据时，`POST /app-authorizations/{id}/start` 仍 **HTTP 200** 返回一个 `client_id=` 为空的死链接，前端表现为「已发起授权」——典型「未配置却显示已实现」。`callback` 亦会用空凭据去换 token（失败但报错语义为模糊的 provider 5xx）。
- **处置（不削弱已有安全语义）**：在 `OAuthFlowService` 新增 `OAuthConfigError` + `_require_configured(provider_id, provider)`，在 `start` 与 `callback` 生成 URL / 换 token **之前** 校验 `client_id`/`client_secret`，缺失即 `raise OAuthConfigError`；路由层映射为 **HTTP 503**（带明确「该应用尚未配置凭据」文案）。state CSRF 一次性校验、Shopify HMAC、飞书验签等既有安全语义 **保持不变**。
- **回归锁定**：`tests/test_oauth_flow.py`
  - `test_start_unconfigured_provider_fails_fast` —— 未配置 provider `start` 必 `raise OAuthConfigError` 且不生成死链接。
  - `test_callback_unconfigured_provider_fails_fast` —— 未配置时 `callback` 同样 fail-fast。
  - 既有 Stub provider 补注入测试凭据以代表「已配置」态（`test_oauth_flow.py` / `test_app_authorizations_api.py`），全部仍通过。

### 2.2 【已记录·未改】vendor fetch sources（wkinfo / amazon_sp / shopee）未配置静默返回 mock

- **证据**：`fetch/sources/legal/wkinfo.py:87-92`（无 key→mock）、`:111`（即便有 key 也走 stub mock）；`ecommerce/amazon_sp.py`、`shopee.py` 纯 mock。
- **判定**：属真实「假数据」行为，但：(a) 代码与日志**明确自标 mock/stub**，非冒充已实现；(b) 这些 source **未注册进 live fetch 路由**（tiers 仅 L1-L3 通用 HTTP/crawl，见 `fetch/tiers/`），也未被任何 API route 直接暴露；(c) 仅 DD persona 引用且 persona 已显式标注 mock 占位。
- **建议（后续，本次不改以免在无测试覆盖路径上引入回归）**：对接前，给这三个 source 加 `_commercial_environment()` 守卫（参照 `oa_integration_service` 模式），生产环境未配置 key 时 `raise *ConfigError` 而非返回 mock。

### 2.3 复核为「无风险」的项

- 飞书 IM adapter / 微信支付 / 支付宝 / e签宝 / 法大大 / GDCA / 粤企签 / TokenStore / OA 集成（生产）：**均已 fail-fast**（见矩阵依据列）。
- IM `/test` 自检、web 搜索降级、企查查公开爬取：**诚实降级**，不伪造、不谎称 connected。

---

## 三、激活分类：「还差什么才能上线」

### A. 可自助激活（填凭据 / 配环境变量即可，无需对外签约）

| 集成 | 关键配置项 |
|------|-----------|
| IM·飞书 | `FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_ENCRYPT_KEY` / `FEISHU_VERIFY_TOKEN`（飞书自建应用，企业自助创建） |
| OAuth·飞书 / 钉钉 / Notion / Shopify / Amazon SP | 各平台 `client_id` / `client_secret`（在各自开放平台自助建应用）+ `OAUTH_TOKEN_ENCRYPTION_KEY`（Fernet key 自助生成）+ `APP_AUTH_REDIRECT_BASE_URL` |
| 搜索增强·Tavily / Bing | `TAVILY_API_KEY` / `BING_SEARCH_KEY`（可选；不配则用免费 DDG 降级） |

### B. 需商务对接 / 合作方 / 平台签约（不只是填凭据）

| 集成 | 需要的外部动作 |
|------|---------------|
| 支付·微信支付 | 微信支付商户号入驻 + 申请商户证书 + 配置公网回调域名 |
| 支付·支付宝 | 支付宝开放平台应用签约 + 上传应用公钥 / 换取支付宝公钥 |
| 电签·e签宝 | e签宝企业实名认证 + 开通 API + 申请 APP_ID/SECRET |
| 电签·法大大 | 法大大企业签约 + 申请 APP_ID/SECRET + ACCESS_TOKEN |
| 电签·GDCA / 粤企签 | 政务/省级电签平台对接（需合作方），并完成 provider 真实现（当前 placeholder） |
| IM·微信/钉钉/Telegram/Slack/Discord | 先完成 adapter 真实现（P3+），再各平台建应用并配置凭据 |
| 数据源·企查查 / 天眼查 | 采购商业 API（按调用量计费），替换当前公开端点爬取 |
| 数据源·威科先行 wkinfo | 采购法律数据库 API + 完成 provider 真实现（当前 stub-mock） |
| 数据源·Amazon SP / Shopee | 平台开发者账号 + SP-API/Open API 授权 + 完成真实现（当前纯 mock） |

---

## 四、本次代码改动清单

1. `backend/src/services/app_authorization/oauth_flow.py` —— 新增 `OAuthConfigError` 异常 + `_require_configured()` 守卫，并在 `start` / `callback` 前置校验 client_id/client_secret。
2. `backend/src/services/app_authorization/__init__.py` —— 导出 `OAuthConfigError`。
3. `backend/src/api/routes/app_authorizations.py` —— `start_authorize` / `oauth_callback` 捕获 `OAuthConfigError` → HTTP 503（须置于 `OAuthFlowError` 之前）。
4. `backend/tests/test_oauth_flow.py` —— 新增 2 个 fail-fast 回归测试；Stub provider 注入测试凭据。
5. `backend/tests/test_app_authorizations_api.py` —— Stub provider 注入测试凭据（适配新守卫）。

**门禁**：`ruff check src tests` 全过；`pytest -q` = **2085 passed, 45 skipped**（在 2083 基线上 +2 新增 fail-fast 测试，无回归）。
