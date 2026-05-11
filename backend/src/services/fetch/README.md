# FetchService — 信息获取栈 4 层门面（P6-A）

> 安心智能助手 V3 信息获取栈的统一入口。所有「需要从外部网络拿数据」的业务侧调用都应走 `fetch_service`，不要直接调用 httpx / Playwright / crawl4ai。

## 架构

```
                  FetchService (统一门面)
                        │
                        ▼  URL → Tier 路由
        ┌───────────────┼───────────────────────────┐
        │               │                           │
        ▼               ▼                           ▼
   L1 纯 HTTP       L2 crawl4ai             L3 HeadlessX
   httpx +          (现有 service)          (P6-B 实装)
   selectolax/lxml  JS 渲染 + 反检测        反检测 headless
        │               │                           │
        └───────────────┼───────────────────────────┘
                        ▼
                  L4 官方 API (P6-D)
                  Shopify / SP-API / 北大法宝
```

## 5 级分层（CAPABILITY_MATRIX 对齐）

| Tier | 实现 | 适用场景 | 状态 |
|------|------|----------|------|
| L0 | 短路 cache | 已抓过的 URL | TODO（P6-E） |
| L1 | httpx + selectolax/lxml | 政府静态页 / RSS / sitemap | ✅ |
| L2 | crawl4ai | 行业资讯 / JS 渲染 | ✅（包装现有 service） |
| L3 | HeadlessX | 强反爬电商 | ⏳ P6-B |
| L4 | 官方 API | Shopify / Amazon SP-API | ⏳ P6-D |

## 路由规则

`router.route()` 是纯函数，按以下顺序短路：

1. **`tier_hint` 显式覆盖**（除非黑名单）
2. **RSS / atom / sitemap 链接** → L1
3. **强反爬电商域**（amazon / shopify / shopee / 1688 / tiktok / tmall / taobao / jd / lazada）→ L3
4. **政府 / 司法**（`*.gov.cn` 系）→ L1
5. **默认** → L2 crawl4ai

## 合规

### 黑名单（硬拦截，403）

| 域名 / 路径 | 原因 | 替代方案 |
|------------|------|---------|
| `wenshu.court.gov.cn` | 裁判文书网禁机器抓取 | 走最高人民法院司法公开数据 API（P6-C） |
| `mp.weixin.qq.com` | 公众号文章违反运营规范 | 微信开放平台素材管理 API |
| `weixin.qq.com` | 微信域整体禁抓 | 官方开放平台 |
| `*.myshopify.com/admin` | Shopify 后台禁抓 | Admin REST/GraphQL API（P6-D） |
| `*.myshopify.com/api` | 不要绕过 Admin API | Admin API + key |

### 白名单（允许）

`*.gov.cn`（含子域）/ `creditchina.gov.cn` / `1688.com` / `*.myshopify.com` / `people.com.cn` / `xinhuanet.com` / `cctv.com` / `iyiou.com` / `36kr.com`。

未命中白名单不会拒绝，但会在审计日志标注 `_allowlist=False`，便于运营评估扩充。

### 审计

- 每次抓取（含被拒绝的）都写入 `AuditLogger`（90 天保留）
- 字段：`user_id, url, tier_used, status_code, request_ts, duration_ms, blocked_reason, error`
- 默认内存环形缓冲；生产可注入 `persist_callback` 写入独立 `fetch_audit_log` 表

### robots.txt

默认遵守。可在 `FetchService(respect_robots=False)` 关闭（不推荐）。

## 限流

- per-domain 令牌桶，默认 1 QPS、容量 2
- 调用 `rate_limiter.configure("example.com", 5.0)` 调整
- 单实例内存桶；跨实例严格全局限流由 P6-D 接 Redis 替换

## 使用示例

```python
from src.services.fetch import (
    fetch_service,
    FetchRequest,
    ExtractConfig,
    ExtractFormat,
)

# 1. 一站式抓取 + 抽取
resp = await fetch_service.fetch_with_extract(
    url="https://www.court.gov.cn/zixun-xiangqing-12345.html",
    css_selectors={"title": "h1.title", "body": "div.content"},
    user_id="user-123",
)
print(resp.extracted)

# 2. 完全控制
req = FetchRequest(
    url="https://example.com",
    extract=ExtractConfig(
        css_selectors={"links": "a.product"},
        format=ExtractFormat.MARKDOWN,
    ),
    user_id="user-123",
)
resp = await fetch_service.fetch(req)

# 3. 批量
responses = await fetch_service.fetch_batch(
    [FetchRequest(url=u) for u in urls],
    concurrency=5,
)

# 4. 合规检查（不发请求）
fetch_service.check_compliance("https://wenshu.court.gov.cn/abc")
# → {"allowed": True, "blocked": True, "block_reason": {...}}
```

## API

```
POST   /api/v1/fetch                       通用抓取
POST   /api/v1/fetch/batch                 批量
GET    /api/v1/fetch/audit                 审计日志（admin only）
GET    /api/v1/fetch/compliance/check      检查域名合规性
```

## 给 P6-B / P6-C / P6-D 的接入说明

### P6-B（HeadlessX）

1. 替换 `tiers/l3_headlessx.py` 中的 `L3HeadlessXTier`
2. 实装 `fetch()` 方法，处理 device profile / proxy / 反指纹
3. 类属性 `available = True` 让 FetchService 知道可用
4. 失败时**保持** `error` 字段非空 — FetchService 才能自动降级到 L2

### P6-C（法律源）

1. 新建 `backend/src/services/fetch/sources/legal/`
2. 每个源（裁判文书替代 / 北大法宝 / 中国裁判文书 / 国务院公报…）是一个**使用** `fetch_service` 的 client
3. **不要新建 Tier** — sources 只是 fetch_service 的消费者

### P6-D（电商 / 官方 API）

1. 新建 `backend/src/services/fetch/sources/ecommerce/`
2. 如果是官方 API（Shopify Admin / Amazon SP-API / 1688 商品 API）→ 在 `service.py` 新增 `L4OfficialAPITier` 并注册到 `_tiers`
3. 如果是公开商品页（无需 key）→ 直接走 L3，作为 sources 的 client
