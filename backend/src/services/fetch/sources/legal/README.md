# 法律数据源（P6-C）

本目录是 FetchService 的法律垂直域插件集合。所有 source 实现共同的抽象基类
`BaseLegalSource`，可被 P6-A 的 FetchService 统一编排，亦可独立调用。

## 合规底线（强制）

| 域名 | 状态 | 说明 |
|------|------|------|
| `wenshu.court.gov.cn` | ❌ 禁止 | 走 `historical_wenshu`（已落库 33,102 条）+ `pkulaw` 商业 API |
| `mp.weixin.qq.com` | ❌ 禁止 | 微信公众号文章不得爬 |
| `flk.npc.gov.cn` | ✅ 允许 | 国家法律法规数据库公开 API + 1 req/s 限流 + robots.txt 校验 |
| `creditchina.gov.cn` | ✅ 允许 | 信用中国公开企业信用查询 |
| `api.pkulaw.com` | ✅ 允许 | 北大法宝商业付费 API（需 `PKULAW_API_KEY`） |
| `api.wkinfo.com.cn` | ✅ 允许 | 威科先行商业付费 API（需 `WKINFO_API_KEY`） |

合规校验落点：

1. `base.assert_url_compliant(url)` —— 任何 source 在调 `httpx` 之前**必须**先调用，
   命中黑名单立即抛 `ComplianceError`，无任何降级。
2. `flk_npc_gov.py` 额外做 `robots.txt` 校验。
3. `historical_wenshu.py` 不发 HTTP，但仍对 `query.jurisdiction` 防御性拒绝
   `wenshu.court.gov.cn`，避免上游错误传参。

## 数据源清单

| Source | 类型 | 凭证 | 数据形态 |
|--------|------|------|---------|
| `FlkNpcGovSource` | 政府公开 | 无 | 法律 / 法规 / 司法解释 |
| `CreditChinaSource` | 政府公开 | 无 | 企业失信 / 行政处罚 / 经营异常 |
| `PkuLawSource` | 商业付费 | `PKULAW_API_KEY` | 法律 / 法规 / 案例 |
| `WkInfoSource` | 商业付费 | `WKINFO_API_KEY` | 法律 / 法规 / 案例 |
| `HistoricalWenshuSource` | 已落库 read-only | 无（直连 DB） | 裁判文书 |

## 对接 P6-A FetchService

P6-A 框架（`fetch/service.py`）合并后，建议按"被 service 调"模式集成：

```python
service = FetchService()
service.register_source("legal", FlkNpcGovSource(rate_limiter=service.rate_limiter("flk_npc_gov")))
service.register_source("legal", CreditChinaSource())
service.register_source("legal", PkuLawSource())
service.register_source("legal", WkInfoSource())
service.register_source("legal", HistoricalWenshuSource(engine=service.async_engine))
```

也支持独立运行（不依赖 P6-A），适合 cron / 离线脚本场景。

## 测试

- `tests/test_legal_sources_compliance.py` 黑名单防爬硬拒
- `tests/test_flk_npc_parser.py` mock httpx 验证 search 解析
- `tests/test_credit_china_client.py` mock + USCC 输入校验
- `tests/test_pkulaw_mock_fallback.py` 未配 key 走 mock + log warning
- `tests/test_historical_wenshu_query.py` 内存 SQLite + 假数据查询
