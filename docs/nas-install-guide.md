# 安心智能助手 · NAS 一键安装指南

面向群晖 (Synology)、威联通 (QNAP) 以及通用 Docker NAS（OMV、TrueNAS Scale、UGREEN）。

> 本指南假设：你的 NAS 已开启 Container Manager / Container Station 等 Docker 能力，
> 并且至少有 2 GB 可用内存（推荐 4 GB）、50 GB 可用存储。

---

## 方案 A · 群晖 (Synology) Container Manager

### A.1 使用 YAML 项目创建（推荐，DSM 7.2+）

1. 打开 **套件中心** 安装 **Container Manager**
2. 进入 **项目 → 新增项目 → 创建 docker-compose.yml**
3. 把 `docker-compose.nas.yml` 完整内容贴入
4. 下载 [`.env.nas.example`](../.env.nas.example)，重命名为 `.env` 贴入同一项目
5. 在 `.env` 里**至少**改三处：
   - `POSTGRES_PASSWORD` —— 生成一个 20+ 位随机串
   - `REDIS_PASSWORD` —— 同上
   - `JWT_SECRET` —— `openssl rand -base64 48`（在 PC 终端运行后复制进来）
6. 点 **构建** —— Container Manager 会自动 pull 4 个镜像并启动
7. 打开浏览器访问 `http://<你的 NAS IP>:3001`

### A.2 使用 Portainer Stack（更灵活，需已装 Portainer）

1. Portainer → Stacks → Add stack
2. 名称填 `anxin-ai`
3. "Build method" 选 `Web editor`，贴入 `docker-compose.nas.yml`
4. "Environment variables" 按 `.env.nas.example` 逐条录入
5. Deploy，等容器 healthy

---

## 方案 B · 威联通 (QNAP) Container Station

1. Container Station 2.x → **应用程序 → 创建**
2. 选 **YAML 导入**
3. 粘贴 `docker-compose.nas.yml`
4. 在环境变量面板覆盖 `.env` 参数
5. 确认存储路径（建议挂到 `/share/Public/anxin-ai`）
6. 创建并启动

---

## 方案 C · 通用 Linux / macOS（Docker Desktop）

```bash
git clone https://github.com/<你的仓库>/anxin-ai.git
cd anxin-ai
cp .env.nas.example .env
# 编辑 .env 替换密码与 JWT_SECRET
docker compose -f docker-compose.nas.yml up -d
# 看启动日志
docker compose -f docker-compose.nas.yml logs -f backend
```

---

## 部署后检查

| 检查项 | 期望结果 |
|---|---|
| 容器 `anxin_backend` 健康 | `docker ps` 列显示 `healthy` |
| `http://<ip>:3001` 首页能打开 | 看到"安心智能助手"登录页 |
| `http://<ip>:8001/api/v1/health` | 返回 `{"status":"ok"}` |
| Chroma `/api/v1/heartbeat` | 返回 JSON 对象 |

## 常见坑

**内存不足：容器频繁重启**
→ 家用 2 GB NAS 请把 `NEO4J_ENABLED=false`、`LIVEKIT_ENABLED=false`（默认已关），
  并在群晖 / QNAP 面板限制每个容器的 memory limit；
  若仍吃紧，改 Chroma 替代 Qdrant 已省 ~300 MB。

**镜像拉取慢**
→ 国内 NAS 在 `docker-compose.nas.yml` 顶部加：
  ```yaml
  x-defaults: &defaults
    image_pull_policy: IfNotPresent
  ```
  同时在 Docker daemon.json 里添加 `https://dockerproxy.com` 等加速源。

**ARM64 镜像**
→ 群晖 DS220+ / 群晖旗舰的 x86_64 机型直接 pull `linux/amd64`；
  DS120j / QNAP TS-251D 等 ARM 机型需要 pull `linux/arm64`。
  本仓库已配置 GitHub Actions `publish-images.yml` 支持双架构 manifest，一条 tag 同时可用。

**端口冲突**
→ 3001（前端）/ 8001（后端）可能被 NAS 自带服务占用；
  修改 `docker-compose.nas.yml` 的 ports 段即可，例如 `"3001:80"` → `"3011:80"`。

**数据备份**
```bash
# Volumes：postgres_data / redis_data / chroma_data / neo4j_data
docker run --rm -v anxin-ai_postgres_data:/src -v $PWD:/dst alpine \
  tar czf /dst/postgres-$(date +%F).tar.gz -C /src .
```

## 升级

```bash
docker compose -f docker-compose.nas.yml pull
docker compose -f docker-compose.nas.yml up -d
```
默认 `image: ghcr.io/anxin/anxin-ai-backend:latest`，pull 即滚动更新。
建议发版后再拉 `:latest`，或 pin 到 `:v1.2.3` 手动升级。

## 下一步

- 连接本地 Ollama：在 `.env` 填 `OLLAMA_BASE_URL=http://host.docker.internal:11434`
- 开启硬件 NPU 加速（RK3588 / Apple Silicon）：参考 `docs/hardware-appliance-protocol.md`
- 离线法规包：`docker compose exec backend python -m src.cli.download_pack regulation-core-v1`
