# 安心法务 — 部署指南

> 版本：1.0 | 日期：2026-03-26

## 1. 部署方式概览

| 方式 | 适用场景 | 复杂度 |
|------|---------|--------|
| Docker Compose 一键部署 | 生产环境、私有化部署 | 低 |
| 开发环境 | 本地开发调试 | 中 |
| 手动部署 | 定制化需求 | 高 |

## 2. 环境要求

### 2.1 硬件要求

| 配置 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核+ |
| 内存 | 4 GB | 8 GB+ |
| 磁盘 | 20 GB | 50 GB+ SSD |
| 网络 | 1 Mbps | 10 Mbps+ |

### 2.2 软件要求

| 软件 | 版本要求 |
|------|---------|
| Docker | 20.10+ |
| Docker Compose | 2.0+ |
| Python | 3.11+ (手动部署) |
| Node.js | 18+ (手动部署) |
| PostgreSQL | 15+ |
| Redis | 7+ |

## 3. Docker Compose 一键部署（推荐）

### 3.1 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/your-org/Anxin-Smart-Legal-Services.git
cd Anxin-Smart-Legal-Services

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，至少设置以下项：
# - JWT_SECRET_KEY（必须修改为随机字符串）
# - DATABASE_URL
# - QWEN_API_KEY 或其他 LLM API Key

# 3. 启动所有服务
docker-compose up -d

# 4. 初始化数据库
docker-compose exec backend alembic upgrade head

# 5. 导入初始数据（可选）
docker-compose exec backend python scripts/seed_all.py
```

推荐生产拓扑：

- 宿主机 Nginx 监听公网 `80/443`
- 前端容器绑定 `127.0.0.1:3001 -> 80`
- 后端容器绑定 `127.0.0.1:8001 -> 8001`
- PostgreSQL / Redis / Qdrant / Neo4j / MinIO 仅容器网络可见，不对公网暴露

### 3.2 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| 宿主机 Nginx | 80 / 443 | 公网入口，处理 HTTPS 与反向代理 |
| 前端容器 | 127.0.0.1:3001 | 仅宿主机本地可访问 |
| 后端 API | 127.0.0.1:8001 | 仅宿主机本地可访问 |
| PostgreSQL | 容器网络内 5432 | 数据库，不对公网暴露 |
| Redis | 容器网络内 6379 | 缓存，不对公网暴露 |
| Qdrant | 容器网络内 6333/6334 | 向量数据库，不对公网暴露 |
| Neo4j | 容器网络内 7474/7687 | 图数据库，不对公网暴露 |
| MinIO | 容器网络内 9000/9001 | 对象存储，不对公网暴露 |

### 3.3 健康检查

```bash
# 检查所有服务状态
docker-compose ps

# 检查后端 API 健康
curl http://127.0.0.1:8001/health

# 检查前端
curl http://127.0.0.1:3001

# 检查公网入口
curl -I https://anxinfawu.com
curl -I https://www.anxinfawu.com
```

### 3.4 HTTPS（推荐）

推荐使用 Certbot 为主机 Nginx 签发证书：

```bash
apt update
apt install -y nginx certbot python3-certbot-nginx
certbot --nginx -d anxinfawu.com -d www.anxinfawu.com
nginx -t
systemctl reload nginx
```

完成后应满足：

- `http://anxinfawu.com` → 301 跳转到 HTTPS
- `http://www.anxinfawu.com` → 301 跳转到 HTTPS
- `https://anxinfawu.com` → 200
- `https://www.anxinfawu.com` → 200

## 4. 开发环境部署

```bash
# 1. 启动基础设施
docker-compose -f docker-compose.dev.yml up -d

# 2. 启动后端（支持热重载）
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn src.api.main:app --reload --port 8001

# 3. 启动前端（支持 HMR）
cd frontend
npm install
npm run dev
```

## 5. 私有化部署

### 5.1 部署特点

- **完全免费**：企业版和律所版均支持免费私有化部署
- **数据私有**：所有数据存储在客户自己的服务器，不上传云端
- **一键安装**：Docker Compose 一条命令完成部署
- **自主升级**：支持增量升级，不影响业务数据

### 5.2 私有化部署步骤

```bash
# 1. 在客户服务器上安装 Docker
curl -fsSL https://get.docker.com | sh

# 2. 下载部署包
wget https://releases.anxin-legal.com/latest/deploy.tar.gz
tar -xzf deploy.tar.gz
cd anxin-deploy

# 3. 运行安装向导
./install.sh
# 向导将引导配置：
# - 数据库密码
# - JWT 密钥
# - LLM API Key
# - 域名和 SSL 证书

# 4. 启动服务
docker-compose up -d
```

### 5.3 数据备份

```bash
# 数据库备份
docker-compose exec postgres pg_dump -U postgres anxin_legal > backup_$(date +%Y%m%d).sql

# 文件备份
tar -czf minio_backup_$(date +%Y%m%d).tar.gz ./data/minio/

# 恢复
docker-compose exec -T postgres psql -U postgres anxin_legal < backup_20260326.sql
```

## 6. 环境变量说明

| 变量 | 必填 | 说明 | 默认值 |
|------|------|------|--------|
| `JWT_SECRET_KEY` | 是 | JWT 签名密钥（生产必须修改） | — |
| `DATABASE_URL` | 是 | PostgreSQL 连接串 | `postgresql+asyncpg://...` |
| `REDIS_URL` | 是 | Redis 连接串 | `redis://localhost:6379` |
| `QWEN_API_KEY` | 是 | 通义千问 API Key | — |
| `DEV_MODE` | 否 | 开发模式（生产必须 false） | `false` |
| `CORS_ORIGINS` | 否 | 允许的跨域源 | `http://localhost:3001` |
| `QDRANT_HOST` | 否 | Qdrant 向量库地址 | `localhost` |
| `NEO4J_URI` | 否 | Neo4j 图数据库地址 | `bolt://localhost:7687` |
| `MINIO_ENDPOINT` | 否 | MinIO 对象存储地址 | `localhost:9000` |

## 7. 安全注意事项

- **必须** 修改 `JWT_SECRET_KEY` 为随机字符串
- **必须** 在生产环境设置 `DEV_MODE=false`
- **必须** 限制 `CORS_ORIGINS` 为实际域名
- **必须** 将 PostgreSQL / Redis / Qdrant / Neo4j / MinIO 保持为非公网暴露
- **推荐** 使用宿主机 Nginx + Certbot 接管 HTTPS
- **推荐** 定期更换 API Key 和数据库密码
- **推荐** 开启数据库定期备份

## 8. 故障排查

| 问题 | 排查方法 |
|------|---------|
| 服务无法启动 | `docker-compose logs <service>` |
| 数据库连接失败 | 检查 `DATABASE_URL` 和 PostgreSQL 服务状态 |
| API 返回 401 | 检查 JWT 配置和 Token 有效期 |
| 前端白屏 | 检查 API 代理配置和后端服务状态 |
| 向量搜索异常 | 检查 Qdrant 服务和 Embedding 模型配置 |
