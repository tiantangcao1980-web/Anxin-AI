# HeadlessX 自托管部署

为「安心智能助手」FetchService 的 **L3 反检测层**提供独立的 Camoufox-based 抓取服务。

上游：<https://github.com/saifyxpro/HeadlessX>

---

## 资源占用估算

| 实例规格        | 并发 | 估算 RAM   | 估算 CPU | 磁盘 (含 Camoufox + Postgres + Redis) |
|-----------------|------|------------|----------|----------------------------------------|
| 最小可用        | 1    | 2 GB       | 1 vCPU   | 5 GB                                   |
| 推荐            | 3    | 4 GB       | 2 vCPU   | 10 GB                                  |
| 高负载          | 8    | 12 GB      | 4 vCPU   | 20 GB                                  |

> **拐点**：Camoufox 单 tab 常驻 ~500MB-1GB；并发数线性增加内存。
> Postgres + Redis 长期占用 ~500MB。

---

## 部署方式 A：docker compose（推荐）

适用：单机 / NAS / 测试环境。

```bash
cd deploy/headlessx
cp .env.example .env
# 编辑 .env：HEADLESSX_API_KEY、HEADLESSX_DB_PASSWORD、MAIN_NETWORK_NAME

# 启动
docker compose -f docker-compose.headlessx.yml --env-file .env up -d

# 查看日志
docker compose -f docker-compose.headlessx.yml logs -f headlessx

# 健康检查
curl -H "x-api-key: $HEADLESSX_API_KEY" http://localhost:3000/health
```

### 与主项目共享网络

主项目的 `docker-compose.yml` 通常会在 networks 段声明默认网络（如 `anxin-net`）。
本 stack 把 `default` 设为 `external: true` 引用该网络，
backend 容器即可通过 `http://headlessx:3000` 直接访问 — **不需要 Nginx 反代**。

### 后端配置

主项目 `backend/.env` 添加：

```ini
HEADLESSX_BASE_URL=http://headlessx:3000
HEADLESSX_API_KEY=<与 deploy/headlessx/.env 中相同>
HEADLESSX_TIMEOUT=60
HEADLESSX_FALLBACK_TIER=l2_crawl4ai
```

---

## 部署方式 B：systemd（裸金属 / VPS）

```ini
# /etc/systemd/system/headlessx.service
[Unit]
Description=HeadlessX scraping service
After=docker.service postgresql.service redis.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=true
WorkingDirectory=/opt/anxin/deploy/headlessx
EnvironmentFile=/opt/anxin/deploy/headlessx/.env
ExecStart=/usr/bin/docker compose -f docker-compose.headlessx.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.headlessx.yml down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now headlessx
sudo systemctl status headlessx
```

---

## 部署方式 C：跨主机 + Nginx 反代

如果 HeadlessX 与 backend 不在同一主机：

1. HeadlessX 主机：用方式 A/B 启动
2. Backend 主机：通过内网 IP 或 VPN 访问
3. 需要公网暴露时，把 `nginx-snippet.conf` `include` 到主 Nginx 配置中
   - 已内置 IP 白名单（10/8、172.16/12、192.168/16）
   - 公网域名生产部署务必同时启用 TLS + Cloudflare 等 WAF

```nginx
server {
    listen 443 ssl http2;
    server_name internal.example.com;

    include /opt/anxin/deploy/headlessx/nginx-snippet.conf;
}
```

---

## 验证

```bash
# 1. 健康检查
curl -H "x-api-key: $KEY" http://headlessx:3000/health
# {"status":"ok","camoufox":"ready","queue":0}

# 2. 简单渲染
curl -XPOST -H "x-api-key: $KEY" -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}' \
  http://headlessx:3000/render | jq '.statusCode, .botScore'

# 3. 后端集成
cd backend && pytest tests/test_l3_headlessx_tier.py -v
```

---

## 监控

| 指标               | 含义                         | 告警阈值        |
|--------------------|------------------------------|-----------------|
| `queue_length`     | 排队中的渲染任务             | > 10 持续 5min  |
| `error_rate`       | /render 5xx 比例             | > 5%            |
| `avg_duration_ms`  | 单次渲染平均耗时             | > 15000ms       |
| `bot_score_p90`    | 90 分位 bot 分数             | > 0.6           |
| `memory_used`      | 容器 RSS                     | > 80% limit     |

`bot_score_p90 > 0.6` 是关键早警信号 — 说明站点正在升级反爬，
该考虑：换代理池 / 升级 Camoufox / 切换抓取策略。

---

## 故障排查

| 现象                      | 可能原因                          | 处理                                    |
|---------------------------|-----------------------------------|-----------------------------------------|
| 401 Unauthorized          | API Key 不一致                    | 比对 `deploy/headlessx/.env` 与 backend|
| 502 from main Nginx       | docker network 未共享              | 检查 `MAIN_NETWORK_NAME`                 |
| 504 渲染超时              | 目标站点慢 / Camoufox 排队        | 调大 `HEADLESSX_DEFAULT_TIMEOUT_MS`     |
| OOM killed                | 并发太高                          | 降低 `HEADLESSX_MAX_CONCURRENT`         |
| bot_score 持续 1.0        | 站点已完全识别                    | 切代理池 / 换 user_agent 池 / 切策略   |
