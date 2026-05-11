# 跨境电商数据源（P6-D）

本目录提供 5 个跨境电商平台的统一数据源插件，归属 `fetch.sources.ecommerce`：

| Source ID      | 平台         | 真实接入 | OAuth 复用                    |
|----------------|--------------|----------|-------------------------------|
| `shopify`      | Shopify      | ✅ 真实   | P4-E `ShopifyOAuthProvider`   |
| `amazon_sp`    | Amazon SP-API| 🟡 mock   | LWA + AWS SigV4（未来阶段）    |
| `alibaba_1688` | 阿里 1688    | 🟡 mock   | ISV 接入（未来阶段）           |
| `shopee`       | Shopee       | 🟡 mock   | Shopee Partner（未来阶段）     |
| `tiktok_shop`  | TikTok Shop  | 🟡 mock   | TikTok Partner（未来阶段）     |

## 统一接口（`base.py`）

```python
class BaseEcommerceSource(ABC):
    source_id: ClassVar[str]
    display_name: ClassVar[str]
    requires_oauth: ClassVar[bool] = True

    async def search_products(query, oauth_token=None) -> list[Product]: ...
    async def get_product(sku, oauth_token=None) -> Product | None: ...
    async def list_orders(oauth_token, since=None, limit=50) -> list[Order]: ...
    async def update_inventory(sku, qty, oauth_token) -> bool: ...
    async def health_check(oauth_token=None) -> bool: ...
```

数据模型 `Product` / `Order` / `ProductSearchQuery` 是平台无关的；具体平台
原始字段进 `raw` 给前端做差异化展示。

## Shopify 多租户 shop 域名怎么穿过来？

P4-E 已经把 shop 域名持久化到 `OAuthTokenBundle.raw["shop"]`，落库到
`app_tokens.<encrypted...>` 同一行的 raw JSON 里。P6-A `FetchService` 解密 token
时同时取出 `raw["shop"]`，按下面方式注入：

```python
# P6-A FetchService 内部（伪代码）
bundle = await app_auth_service.get_decrypted_bundle(user_id, "shopify")
source = ShopifyEcommerceSource(
    shop=bundle.raw["shop"],          # ← 多租户 shop 域名
    api_version=settings.SHOPIFY_API_VERSION,
)
return await source.search_products(query, oauth_token=bundle.access_token)
```

source 自身**不读 DB、也不持有用户态**。如果调用方忘了传 shop，会抛
`OAuthRequiredError("Shopify shop 域名缺失（应从 OAuth token store 的 raw['shop'] 读出）")`。

## mock source 何时升真？

| Source         | 真实接入复杂度 | 主要门槛                                                    | 计划阶段 |
|----------------|----------------|-------------------------------------------------------------|----------|
| Amazon SP-API  | ⭐⭐⭐⭐⭐         | LWA + AWS SigV4 签名 + STS AssumeRole + RDT（PII）           | P7+      |
| 阿里 1688      | ⭐⭐⭐⭐           | ISV 资质审核 + 能力包签约（商品/订单需分别申请）               | P7+      |
| Shopee         | ⭐⭐⭐            | Partner 平台审核 + HMAC sign + region endpoint 区分          | P7+      |
| TikTok Shop    | ⭐⭐⭐            | Partner Center 审核 + HMAC sign + shop_cipher 管理           | P7+      |

mock 阶段保持 **接口契约稳定** —— 真实接入只改方法体，不改签名，
所以前端联调代码无需重写。

## 配置

10 个新字段在 `core.config.Settings`（见 `config.py` 注释）：

```python
AMAZON_SP_LWA_CLIENT_ID, AMAZON_SP_LWA_CLIENT_SECRET, AMAZON_SP_REFRESH_TOKEN, AMAZON_SP_REGION
ALIBABA_1688_APP_KEY, ALIBABA_1688_APP_SECRET
SHOPEE_PARTNER_ID, SHOPEE_PARTNER_KEY
TIKTOK_SHOP_APP_KEY, TIKTOK_SHOP_APP_SECRET
```

Shopify 凭据复用 P4-E 已有的 `SHOPIFY_API_KEY` / `SHOPIFY_API_SECRET` /
`SHOPIFY_API_VERSION`，本目录不重复定义。
