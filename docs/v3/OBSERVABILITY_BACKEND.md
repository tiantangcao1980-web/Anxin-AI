# 安心智能助手 V3 — 后端可观测层 (P19-A)

> **范围**：FastAPI 主进程 + Celery worker + 5 端基础设施（Postgres / Redis / Neo4j / Qdrant / Celery）。
> **配套**：P19-B 前端监控、P19-C Prometheus / Grafana 部署、P19-D CI 注入 SENTRY_RELEASE。
> **不在本文档**：业务指标的具体阈值告警（由 Alertmanager 规则文件管理，见 P19-C）。

---

## 1. SLO 矩阵

| Domain | 描述 | p99 延迟 | 错误率 | 月度可用性 | endpoint pattern | 备注 |
|--------|------|---------|--------|-----------|------------------|------|
| **auth** | 登录 / 注册 / Token 刷新 | **500 ms** | **0.1%** | **99.9%** | `/api/v1/auth/.*` | 用户进入系统的第一站，最严 |
| **chat** | AI 对话（流式 / 非流式 / persona） | **3 s** | **1%** | **99.5%** | `/api/v1/(chat\|personas/.*)` | 受上游 LLM 影响，适度放宽 |
| **tasks** | 任务列表 / 详情 / 创建 / 状态 | **100 ms** | **0.5%** | **99.9%** | `/api/v1/(tasks\|agent-tasks)/.*` | 同步轻量 API，应低延迟 |
| **fetch** | 抓取栈 L1~L4 | **30 s** | **5%** | **99%** | `/api/v1/fetch/.*` | 外部依赖密集，最宽松 |
| **oauth** | OAuth 回调（5 个 provider） | **2 s** | **0.5%** | **99.9%** | `/api/v1/(oauth\|app-authorizations)/.*` | 失败直接影响第三方上线率 |

错误预算计算：`error_budget = total_requests × (1 - availability)`。
告警分两档：
- **fast burn**：1h 内消耗 ≥2% 月度预算 → P1 寻呼
- **slow burn**：6h 内消耗 ≥5% 月度预算 → P2 工单

代码源：`backend/src/services/monitoring/slo_definitions.py::SLO_MATRIX`。

---

## 2. Metrics 字典（19 项业务 + 进程内置）

> 业务 metric 注册到独立 `CollectorRegistry`，避免污染全局。
> 暴露端点：`GET /api/v1/metrics`（合并应用通用 + 业务级）和 `GET /api/v1/metrics/business`（仅业务级，admin 鉴权）。

| Metric | 类型 | Labels | 含义 | 用例 | 告警阈值建议 |
|--------|------|--------|------|------|------------|
| `anxin_http_requests_total` | counter | method, endpoint, status | HTTP 请求总数 | 流量 / 错误率分母 | 5xx 比例 > 1% (1 min)|
| `anxin_http_request_duration_seconds` | histogram | method, endpoint | 请求耗时 | p50/p95/p99 延迟 | p99 超 SLO 持续 5 min |
| `anxin_agent_tasks_total` | counter | persona, status | Agent 任务执行总数 | persona 维度成功率 | failed 占比 > 5% |
| `anxin_agent_task_duration_seconds` | histogram | persona | Agent 任务耗时 | persona 性能基线 | p99 > 60s |
| `anxin_oauth_callback_total` | counter | provider, result | OAuth 回调结果 | provider 维度成功率 | success 占比 < 95% |
| `anxin_webhook_received_total` | counter | source, result | Webhook 接收 | 第三方对接健康 | signature_invalid > 0 |
| `anxin_fetch_requests_total` | counter | tier, result | 抓取栈使用率 | L1~L4 fallback 健康 | l1 success < 80% |
| `anxin_db_query_duration_seconds` | histogram | operation | DB 查询耗时 | 慢查询定位 | p99 > 200ms |
| `process_*` | 内置 | - | CPU/RSS/fd/start_time | 进程级健康 | RSS > 1.5GB |
| `python_*` | 内置 | - | Python 版本 / GC | 平台元信息 | - |

`endpoint` label 已 `normalize_endpoint` 处理（数字 ID → `{id}`，UUID → `{uuid}`），避免 cardinality 爆炸。

---

## 3. Sentry 配置 SOP

### 3.1 环境变量
```bash
SENTRY_DSN=https://xxxxx@o000000.ingest.sentry.io/000000
SENTRY_ENVIRONMENT=production         # development / staging / production
SENTRY_TRACES_SAMPLE_RATE=0.1         # 10% trace 采样
SENTRY_RELEASE=anxin@1.0.0+sha.abcd1234   # 由 P19-D CI 注入
```

### 3.2 集成清单（自动加载）
- `FastApiIntegration(transaction_style="endpoint")`
- `SqlalchemyIntegration()`
- `CeleryIntegration()` — 可选
- `RedisIntegration()` — 可选
- `HttpxIntegration()` — 可选

### 3.3 PII / 敏感字段过滤（before_send）
代码：`backend/src/services/monitoring/sentry_setup.py::sanitize_event`

自动 redact：
- key 命中 `password / secret / token / api_key / authorization / cookie / session / id_card / mobile / phone / bank_card / jwt / bearer / refresh_token`
- 字符串值匹配高熵 regex（≥20 char、`[A-Za-z0-9_\-+/=.]`）
- 字符串内嵌中国手机号、18 位身份证

`send_default_pii=False`（不发 IP / cookies 默认）。

### 3.4 Issue 聚类
通过 `ErrorClassifier` 生成 `(exception_type, first_user_frame, endpoint)` fingerprint，避免同类错误风暴。

---

## 4. Health 端点契约

| 端点 | 用途 | K8s probe | 鉴权 | 状态码 |
|------|------|-----------|------|--------|
| `GET /health` | liveness | livenessProbe | 否 | 总是 200 |
| `GET /health/ready` | readiness | readinessProbe | 否 | 200 / 503 |
| `GET /health/detailed` | 详细 | - | `X-Metrics-Token` header | 200 / 403 |

**核心组件**（DOWN ⇒ overall=unhealthy ⇒ 503）：postgres, redis
**可选组件**（DOWN ⇒ overall=degraded ⇒ 200）：neo4j, qdrant, celery

设计依据：依赖故障不应触发 liveness 重启（重启不修 Postgres，反而中断在做的请求）；只把 pod 从 readiness 摘除即可。

---

## 5. 故障调查 runbook

### 5.1 auth p99 延迟突增
1. Grafana → Auth dashboard → 看 `anxin_http_request_duration_seconds{endpoint=~"/api/v1/auth/.*"}` p99
2. `/api/v1/metrics` curl → 验证不是单 endpoint 抖动
3. `/api/v1/health/ready` → 看 postgres latency_ms（PG 慢必影响 auth）
4. Sentry → 按 endpoint=`/api/v1/auth/login` filter → fingerprint top 1 看是否新错误模式
5. 若 Redis DOWN → JWT blacklist / refresh token 验证退化为同步阻塞 → 临时关 `RATE_LIMIT_ENABLED`

### 5.2 chat error rate 飙升
1. 看 `anxin_agent_tasks_total{status="failed"}` 是否同步飙升 → LLM 上游问题
2. `/api/v1/metrics/business` → 区分 persona（`persona="legal"` vs `persona="market"`）
3. Sentry → tag `slow_request=true` + endpoint 模式 → 看是否单 persona 出问题
4. 真上游故障 → 触发 `LLM_PROVIDER` 故障转移（OpenAI → Anthropic 或本地 Ollama）

### 5.3 tasks 5xx 率 > 0.5%
1. 错误聚类 top 10：`from src.services.monitoring import error_classifier; error_classifier.top_errors(10)`
2. 同 fingerprint count > 100/min → 立即 rollback 最近 deploy
3. 检查 `db_query_duration_seconds{operation="select"}` p99 — 慢查询导致超时？
4. 看 Celery 队列堆积（worker 容量）

### 5.4 fetch L1 success rate 跌至 < 80%
1. `anxin_fetch_requests_total{tier="l1_static"}` success vs (timeout/blocked/error)
2. blocked 多 → 目标站升级反爬，立即把流量切到 L2 (crawl4ai) 或 L3 (HeadlessX)
3. 看 `HEADLESSX_BASE_URL` 是否健康 → `curl /api/v1/health/detailed` 看不到 HeadlessX 时直接走 L4 SearXNG

### 5.5 OAuth callback 失败潮
1. `anxin_oauth_callback_total{result="state_mismatch"}` > 5/min → 前端 / Redis state 存储有问题
2. `result="token_error"` → provider 凭据过期或被吊销
3. Sentry breadcrumb 链 → 找到首个失败的 request_id → 沿链 trace
4. 无法快速恢复时：通过 `feature_flags` 关闭对应 provider 入口，让用户走其它登录方式

---

## 6. 与 P19-B / P19-C / P19-D 的衔接

| 工件 | 由谁产生 | 由谁消费 |
|------|---------|---------|
| `/api/v1/metrics` exposition | **P19-A 后端** | **P19-C Prometheus** scrape（job=anxin-backend） |
| `/api/v1/health/ready` 503 | **P19-A 后端** | K8s readiness + **P19-C** Alertmanager probe |
| `SENTRY_RELEASE` env var | **P19-D CI** build job | **P19-A** sentry init 在 startup 读取 |
| frontend Sentry events | **P19-B 前端** | 同一 Sentry org，通过 release 关联前后端 trace |
| Grafana SLO dashboard | **P19-C** | 数据来自 P19-A 业务 metric + SLO 矩阵 |

---

## 7. 测试覆盖

```bash
cd backend
pytest tests/test_health_endpoint.py \
       tests/test_prometheus_metrics.py \
       tests/test_observability_middleware.py \
       tests/test_error_classifier.py -v
```

19 个用例，覆盖：
- 4 health 端点（liveness / readiness / readiness-503 / detailed-403 + dev 放行 + enum sanity = 6）
- 9 prometheus（6 metric + normalize_endpoint + exposition + registry isolation）
- 4 middleware（request_id 生成 / 透传 / counter / WARN / breadcrumb = 5）
- 5 error classifier（同 fingerprint / 不同 endpoint / 不同 type / 稳定性 / top_n）
