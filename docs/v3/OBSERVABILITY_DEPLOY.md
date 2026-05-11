# 安心智能助手 V3 - 可观测性部署 (P19-C)

> 与 P19-A (后端 metrics) + P19-B (前端 Sentry) 协同。本文聚焦 Prometheus + Grafana + Alertmanager 部署侧。

## 1. 整体架构

```
                 ┌────────────────────────────────────────────┐
                 │          安心 V3 后端 (FastAPI:8001)         │
                 │     /metrics  → 19 个 anxin_* metric        │
                 └─────────────────────┬──────────────────────┘
                                       │ pull 10s
   ┌───────────────────────────────────┼───────────────────────────────┐
   │                          ┌────────▼────────┐                      │
   │  node-exporter ─────────►│                 │                      │
   │     (host)               │   Prometheus    │── eval 15s ── alerts │
   │  postgres-exporter ─────►│   :9090         │──┐                   │
   │     (PG xact/conn)       │  retention 30d  │  │                   │
   │  redis-exporter ────────►│  WAL 20G cap    │  │                   │
   │     (cache + queue)      └────────┬────────┘  │                   │
   │                                   │ remote read                   │
   │                          ┌────────▼────────┐  │                   │
   │                          │    Grafana      │  │                   │
   │                          │    :3000        │  │                   │
   │                          │ 4 dashboards    │  │                   │
   │                          │ provisioning    │  │                   │
   │                          └─────────────────┘  │                   │
   │                                               ▼                   │
   │                                      ┌─────────────────┐          │
   │                                      │  Alertmanager   │          │
   │                                      │     :9093       │          │
   │                                      │ route + silence │          │
   │                                      └────┬─────┬──────┘          │
   │                                           │     │                 │
   │                                ┌──────────▼─┐ ┌─▼────────┐       │
   │                                │ PagerDuty  │ │  飞书机器人  │       │
   │                                │ (critical) │ │ (warning) │       │
   │                                └────────────┘ └──────────┘       │
   └─────────────────────────────────────────────────────────────────────┘
```

## 2. Scrape 拓扑

| Job             | 目标                          | Interval | 标签 |
|-----------------|-----------------------------|----------|------|
| prometheus      | localhost:9090              | 30s      | 自监控 |
| anxin-backend   | host.docker.internal:8001/metrics | 10s | service=anxin-backend, tier=api |
| node-exporter   | node-exporter:9100          | 15s      | service=host, tier=infra |
| postgres-exporter | postgres-exporter:9187    | 30s      | service=postgres, tier=data |
| redis-exporter  | redis-exporter:9121         | 30s      | service=redis, tier=data |
| alertmanager    | alertmanager:9093           | 30s      | self-monitor |

`external_labels: {cluster: anxin-v3, env: ${ENV}}` 注入所有时间序列，方便多集群 Thanos 聚合。

## 3. 告警路由树

```
route (default-feishu)
├─ severity=critical ──► pagerduty-critical (10s wait, 30m repeat)
│                  └──► feishu-critical    (双发，确保到达)
├─ severity=warning  ──► feishu-warning   (2h repeat)
└─ severity=info     ──► log-only

inhibit:
  critical ─░░─► warning   (同 team+alertname)
  BackendDown ─░░─► slo=*  (同 cluster)
  DatabaseDown ─░░─► Slow* (同 cluster)
```

11 条规则覆盖：
- 5 SLO 告警 (HighErrorRateAuth/Chat, SlowAuth/Chat, TaskQueueBacklog)
- 6 基础设施告警 (DatabaseDown / RedisDown / BackendDown / DiskSpaceLow / HighMemoryUsage / HighCpuUsage)

## 4. Dashboard 总览

| #  | 名称        | UID            | Panel | 用途 |
|----|-----------|----------------|-------|------|
| 01 | 全局概览    | anxin-overview | 7     | RPS / 错误率 / SLO 灯 / 5 端流量 / Top 路由错误 / P50-95-99 |
| 02 | Persona 详情 | anxin-personas | 7     | 10 persona 调用量、平均时长、错误率、24h Top10 饼图、P99 |
| 03 | 任务系统    | anxin-tasks    | 8     | 队列长度 / 任务状态 / persona 维度积压 / 失败率 / 做梦次数 |
| 04 | 基础设施    | anxin-infra    | 9     | CPU/内存/磁盘/网络 + Postgres + Redis + 应用连接池 |

**总 panel 数 = 7 + 7 + 8 + 9 = 31 个**

所有 PromQL 基于 P19-A 命名规范的 `anxin_*` metric：
- `anxin_http_requests_total{persona,route,status,client}`
- `anxin_http_request_duration_seconds_bucket{persona,route}`
- `anxin_persona_invocations_total{persona}` / `anxin_persona_duration_seconds_*` / `anxin_persona_errors_total`
- `anxin_task_queue_length{persona}` / `anxin_task_count{status}` / `anxin_task_duration_seconds_*`
- `anxin_task_completed_total` / `anxin_task_failed_total`
- `anxin_active_investigations` / `anxin_ai_calls_total` / `anxin_knowledge_searches_total`
- `anxin_dream_consolidations_total` / `anxin_experience_extractions_total`
- `anxin_db_pool_size/checkedin/checkedout` / `anxin_process_memory_bytes` / `anxin_process_cpu_percent`

## 5. 容量规划

Prometheus tsdb 经验值：
- 单 sample 大小 ~1.3 byte（Snappy 压缩）
- 单 series ingest 频率 = 1 / scrape_interval
- 估算公式：`disk = retention_seconds × series_count × ingest_rate × 1.3 byte`

按 1500 active series（业务 + 三个 exporter）+ 30 天 + 平均 15s 抓取：
```
30d × 86400s × 1500 × (1/15) × 1.3 byte ≈ 13.5 GB
```
配 20G WAL 上限 + 50G SSD（含 WAL/checkpoint/blocks 重写）即可，留 30% buffer。

## 6. 灾备 + 备份

| 组件          | 备份策略                                   | RPO / RTO |
|-------------|----------------------------------------|----------|
| Prometheus  | snapshot API → S3 每日 00:30；保留 14 天     | 24h / 30m |
| Grafana     | grafana-data volume rsync + dashboard JSON 提交 git | 已 git 化 / 5m |
| Alertmanager| alertmanager.yml + silence 状态导出（amtool） | 1h / 5m |
| Postgres exporter / Redis exporter | 无状态，重启即恢复 | 0 / 1m |

snapshot 命令：
```bash
curl -XPOST http://localhost:9090/api/v1/admin/tsdb/snapshot
# 写到 prometheus-data/snapshots/<ts>/，再 rsync 到对象存储
```

## 7. 与生产部署的注意点

1. **持久化卷**：3 个 named volume 必须落到独立磁盘（避免与应用日志同盘 IO 抢占）。
2. **反向代理 + TLS**：三个 UI 端点统一通过 nginx 暴露在 `*.anxinagent.com`，启用 `client-cert` 或 OAuth2-proxy。
3. **鉴权**：禁用 Grafana 匿名 + 强口令；Prometheus 与 Alertmanager 不直接对外。
4. **网络隔离**：`obs-net` 桥接网络与业务网络分离，仅 backend `/metrics` 可被 Prometheus 拉取。
5. **环境变量**：`.env` 不入 git，由配置中心或 Vault 注入。
6. **滚动升级**：Prometheus / Alertmanager 支持配置热加载（`--web.enable-lifecycle` + `curl -XPOST /-/reload`），避免重启丢窗口。
7. **告警噪音治理**：上线初期 24h 通过 `amtool silence` 静默非 critical，再逐步打开。
8. **监控即代码**：dashboard JSON + alert_rules + prometheus.yml 全部 git 化，禁止 UI 直改后未回写。

## 8. 与 P19-A / P19-B 的边界

- **P19-A**：后端注入 `prometheus_client.Histogram/Counter`，定义 19 个 metric 命名规范。
- **P19-B**：前端用 Sentry SDK，错误进 Sentry，不进 Prometheus。
- **P19-C (本工程)**：只消费 P19-A 暴露的 metric，不动业务代码；Sentry 与 Alertmanager 平行运行（Sentry 收前端错，Alertmanager 收后端 SLO）。

## 9. 后续 (P19-D 提案)

- 接入 OpenTelemetry traces → Tempo/Jaeger，与 metrics 关联
- 前端 RUM (Real User Monitoring) → 自建 OTel Collector 或继续 Sentry Performance
- 日志收集：Loki + Promtail，dashboard 内做 metric ↔ log 跳转
