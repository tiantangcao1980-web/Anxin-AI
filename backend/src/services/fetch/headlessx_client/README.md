# HeadlessX Python 客户端

FetchService **L3 (反检测层)** 的实现。封装对 self-hosted [HeadlessX](https://github.com/saifyxpro/HeadlessX) (Camoufox-based) 实例的 HTTP 调用。

## 何时使用

- L1 (普通 httpx) 被 403 / 触发 WAF 挑战
- L2 (Crawl4AI / Playwright) 被识别为 bot（如 Cloudflare Turnstile）
- 目标站点有强反爬（JD / 淘宝商品页、企查查、政府公示页）

非以上场景应优先使用 L1/L2，HeadlessX 资源开销大。

## 架构

```
FetchService
    │
    ├── L1: httpx (raw HTTP)
    ├── L2: Crawl4AI / Playwright (browser, 不反检测)
    └── L3: HeadlessXTier ──HTTP──> HeadlessX (Camoufox + WAF bypass)
              │
              └── HeadlessXClient (本目录)
```

## 快速开始

```python
from src.services.fetch.headlessx_client import HeadlessXClient

async with HeadlessXClient(
    base_url="http://headlessx:3000",
    api_key="<from-deploy-env>",
    timeout=60,
) as client:
    # 简单渲染
    result = await client.render("https://example.com")
    print(result.html)
    print(result.bot_score)  # 0.0-1.0；越低越像真人

    # 带等待
    result = await client.render(
        "https://spa.example.com",
        wait_for_selector=".product-info",
        wait_ms=500,
    )

    # 截图
    png = await client.screenshot("https://example.com", full_page=True)

    # PDF
    pdf = await client.pdf("https://example.com")

    # 健康检查
    health = await client.health()
```

## 异常分类

| 异常类                       | HTTP   | 可重试 | 上层动作          |
|------------------------------|--------|--------|-------------------|
| `HeadlessXAuthError`         | 401/403| ✗      | 直接降级 L2，告警 |
| `HeadlessXClientError`       | 4xx    | ✗      | 直接失败          |
| `HeadlessXRateLimitError`    | 429    | ✓      | 退避后重试        |
| `HeadlessXTimeoutError`      | 408/504| ✓      | 退避后重试        |
| `HeadlessXServerError`       | 5xx    | ✓      | 退避后重试        |

## 重试策略

`with_retry` 默认指数退避：base=1s, max=30s, jitter=0.3，最多 3 次。
可注入 `RetryConfig` 自定义。

## bot_score 字段

`RenderResult.bot_score` 是 HeadlessX/Camoufox 自检的"我看起来像 bot"分数：

- `0.0–0.3` 真人级 — 直接采用结果
- `0.3–0.7` 灰色区 — 采用结果但写入审计，必要时换 proxy 重试
- `0.7–1.0` 已被识别 — `result.is_blocked=True`，触发 fallback 链路

`None` 表示 HeadlessX 未启用检测或老版本，按"未知"处理。

## 测试

见 `backend/tests/test_headlessx_client.py` 与 `test_headlessx_client_retry.py`。

```bash
cd backend && pytest tests/test_headlessx_client.py -v
```
