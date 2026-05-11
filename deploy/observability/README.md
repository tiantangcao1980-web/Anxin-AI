# 安心 V3 可观测性 Stack

Prometheus + Grafana + Alertmanager + (node / postgres / redis) exporters，一键部署。

## 目录结构

```
deploy/observability/
├── docker-compose.yml        # 6 服务编排
├── prometheus.yml            # 抓取配置 (6 job)
├── alert_rules.yml           # 11 条告警规则 (5 SLO + 6 基础设施)
├── alertmanager.yml          # 路由树 + 静默规则 + 5 receiver
├── .env.example              # 环境变量样例
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/prometheus.yml   # 数据源自动注入
│   │   └── dashboards/dashboards.yml    # 仪表盘自动加载
│   └── dashboards/
│       ├── 01-overview.json             # 全局概览 (7 panel)
│       ├── 02-personas.json             # Persona 详情 (7 panel)
│       ├── 03-tasks.json                # 任务系统 (8 panel)
│       └── 04-infrastructure.json       # 基础设施 (9 panel)
└── README.md
```

## 一键启动

```bash
cd deploy/observability
cp .env.example .env
# 编辑 .env 设置 GRAFANA_ADMIN_PASSWORD / POSTGRES_EXPORTER_DSN
docker-compose up -d
docker-compose ps
```

## 访问地址

| 服务         | URL                          | 默认账号                            |
|------------|------------------------------|---------------------------------|
| Prometheus | http://localhost:9090        | 无 (生产请挂 nginx + basic auth)     |
| Grafana    | http://localhost:3000        | admin / `${GRAFANA_ADMIN_PASSWORD}` |
| Alertmanager | http://localhost:9093      | 无 (同上)                          |
| Node Exporter | http://localhost:9100/metrics  | 内部 |
| Postgres Exporter | http://localhost:9187/metrics | 内部 |
| Redis Exporter | http://localhost:9121/metrics | 内部 |

## 修改默认密码

首次启动后立刻修改 Grafana 密码（即使已设置环境变量）：

```bash
docker exec -it anxin-grafana grafana cli admin reset-admin-password 新密码
```

## Dashboard 自动加载

Grafana 启动时通过 `provisioning/dashboards/dashboards.yml` 扫描 `/var/lib/grafana/dashboards`，
4 个 dashboard JSON 会自动出现在 "安心 V3" 文件夹下。

## 验证抓取状态

```bash
# Prometheus targets 状态
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job:.labels.job, health:.health, lastScrape:.lastScrape}'

# 重载 Prometheus 配置（无需重启）
curl -X POST http://localhost:9090/-/reload

# Alertmanager 当前活跃告警
curl -s http://localhost:9093/api/v2/alerts | jq '.[] | {alertname:.labels.alertname, severity:.labels.severity, state:.status.state}'
```

## 告警通道占位

`alertmanager.yml` 中以下占位符必须替换为真实地址：
- `REPLACE_FEISHU_CRITICAL_TOKEN` / `REPLACE_FEISHU_WARNING_TOKEN` / `REPLACE_DEFAULT_TOKEN` - 飞书机器人 webhook
- `REPLACE_PAGERDUTY_INTEGRATION_KEY` - PagerDuty Service Integration Key
- `REPLACE_SLACK_WEBHOOK` - Slack Incoming Webhook

## 与生产环境集成 SOP

1. **网络打通**：将 `prometheus.yml` 的 `host.docker.internal:8001` 改为生产后端实际地址（K8s 用 service DNS、ECS 用内网 IP）。
2. **TLS**：用 nginx/Traefik 反代，给三个 UI 端点加 HTTPS + 鉴权。
3. **远端长存储**：retention 默认 30 天，需要更久接 Thanos / Mimir / VictoriaMetrics。
4. **告警静音窗口**：发布时通过 `amtool silence add ...` 主动静默 SLO 告警。
5. **持久化**：3 个 named volume (`prometheus-data` / `grafana-data` / `alertmanager-data`) 必须挂载到可备份磁盘。
6. **资源**：Prometheus 推荐 4C8G + 50G SSD；Grafana 1C2G；Alertmanager 0.5C1G。

## 故障排查

```bash
docker logs anxin-prometheus -f
docker logs anxin-grafana -f
docker logs anxin-alertmanager -f

# 校验配置
docker run --rm -v $PWD/prometheus.yml:/p.yml prom/prometheus:v2.55.0 promtool check config /p.yml
docker run --rm -v $PWD/alert_rules.yml:/r.yml prom/prometheus:v2.55.0 promtool check rules /r.yml
docker run --rm -v $PWD/alertmanager.yml:/a.yml prom/alertmanager:v0.27.0 amtool check-config /a.yml
```
