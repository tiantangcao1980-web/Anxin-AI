# 安心AI法务 - 安全部署指南

## 部署架构

```
本地开发 → git push → GitHub (私有仓库) → GitHub Actions → SSH → 阿里云服务器
                                                              ↓
                                                    git pull + docker compose up
```

**核心原则：所有密钥只存在于服务器本地 `.env`，绝不通过 Git 传输。**

当前生产目录：`/opt/anxin-smart-legal-services`

---

## 第一步：轮换已泄露的密钥（紧急）

以下密钥曾出现在 Git 历史中，**必须立即轮换**：

| 密钥 | 操作 |
|---|---|
| 通义千问 API Key (`sk-5c4abb...`) | 阿里云控制台 → 通义千问 → 撤销旧 Key → 生成新 Key |
| LiveKit Secret | LiveKit 控制台重新生成 |
| LLM 加密密钥 | `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| JWT Secret | `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` |

**注意：** LLM 加密密钥更换后，数据库中已加密的 LLM 配置将无法解密，需要重新配置。

## 第二步：在阿里云服务器上配置 .env

```bash
# SSH 到服务器
ssh root@<服务器IP>
cd /opt/anxin-smart-legal-services

# 创建 .env 文件（此文件不通过 Git 管理）
cat > .env << 'ENVEOF'
# ===== 基础配置 =====
ENVIRONMENT=production
DEBUG=false
DEV_MODE=false
CORS_ORIGINS=https://anxinfawu.com,https://www.anxinfawu.com

# ===== LLM 配置 =====
LLM_PROVIDER=qwen
LLM_API_KEY=<新的通义千问API Key>
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-max
EMBEDDING_API_KEY=<新的Embedding Key>
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v3

# ===== 安全密钥 =====
JWT_SECRET_KEY=<生成的JWT密钥>
LLM_ENCRYPTION_KEY=<生成的Fernet密钥>

# ===== 数据库（使用强密码） =====
POSTGRES_PASSWORD=<强密码-至少16位>
DATABASE_URL=postgresql://postgres:<同上密码>@postgres:5432/legal_agent_db
REDIS_PASSWORD=<强密码-至少16位>
REDIS_URL=redis://:<同上密码>@redis:6379/0
NEO4J_AUTH=neo4j/<强密码>
NEO4J_PASSWORD=<同上密码>
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=<强密码>
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=<同上MinIO密码>
MINIO_ENDPOINT=minio:9000

# ===== 向量数据库 =====
QDRANT_URL=http://qdrant:6333

# ===== Grafana =====
GRAFANA_PASSWORD=<强密码>

# ===== 其他 =====
LOG_LEVEL=INFO
ENVEOF

# 设置文件权限（仅 root 可读写）
chmod 600 .env

# 同步到 backend 目录
cp .env backend/.env
chmod 600 backend/.env
```

## 第三步：配置 LiveKit

```bash
# 在服务器上创建 livekit.yaml
cp livekit.yaml.example livekit.yaml

# 编辑，填入新的密钥
vim livekit.yaml
# 修改 keys 部分为新生成的密钥

chmod 600 livekit.yaml
```

## 第四步：防止 git pull 覆盖 .env

部署脚本已自动处理（使用 `git update-index --skip-worktree`）。

手动确认：
```bash
# 确认 .env 不被 git 管理
git status  # 应该不显示 .env 相关变更
```

## 第五步：重启服务

```bash
# 重建并重启所有服务
docker compose down
docker compose up -d --build

# 检查服务状态
docker compose ps
docker compose logs --tail=50 backend
curl -sf http://127.0.0.1:8001/health
```

## 第六步：验证安全配置

```bash
# 1. 验证 .env 未被 git 追踪
git ls-files --cached | grep -E '\.env|livekit\.yaml$'
# 应该没有输出

# 2. 验证旧 API Key 已失效
# 用旧的 sk-5c4abb... 调用 API，应该返回认证失败

# 3. 验证新 Key 工作正常
docker compose logs --tail=20 backend | grep -i "error\|fail"

# 4. 验证公网仅保留 80/443
ss -lntup | egrep ':(80|443|8001|5432|6379|6333|6334|7474|7687|9000|9001)\b'
# 应只看到 80/443 为公网监听；8001 应仅绑定 127.0.0.1，其余端口不应对公网开放
```

## 第七步：主机 Nginx + HTTPS（推荐）

```bash
apt update
apt install -y nginx certbot python3-certbot-nginx

# 使用仓库内 nginx.conf 作为基础模板，然后按实际回环端口校正 upstream
cp /opt/anxin-smart-legal-services/nginx.conf /etc/nginx/conf.d/anxin.conf

# 申请并部署证书
certbot --nginx -d anxinfawu.com -d www.anxinfawu.com

nginx -t
systemctl reload nginx
```

完成后应满足：

- `http://anxinfawu.com` 与 `http://www.anxinfawu.com` 自动 301 到 HTTPS
- `https://anxinfawu.com` 与 `https://www.anxinfawu.com` 返回 `200`
- Docker 内部服务不需要额外公网端口放行

## 第八步：阿里云安全组最小开放面

只保留入方向：

- `22`：SSH
- `80`：HTTP
- `443`：HTTPS

如果暂未启用 LiveKit，不要开放：

- `7880-7881/TCP`
- `50000-60000/UDP`

---

## 日常安全维护

### 密钥轮换周期

| 密钥类型 | 建议周期 | 备注 |
|---|---|---|
| JWT Secret | 90 天 | 轮换时旧 token 自然过期 |
| API Key | 180 天 | 或怀疑泄露时立即更换 |
| 数据库密码 | 180 天 | 需同时更新 .env 和数据库 |
| LLM 加密密钥 | 仅在泄露时 | 更换后需重新配置所有 LLM |

### Git 推送前检查

本项目 CI 已集成 TruffleHog 密钥扫描，每次 push 到 main 分支时会自动检测泄露的密钥。

### 服务器安全加固

```bash
# 防火墙仅开放必要端口
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable

# 数据库端口不对外暴露（docker-compose 中已限制为内网）
# 确认 5432、6379、7687 等端口不在公网监听
ss -tlnp | grep -E '5432|6379|7687|9000'
```

---

## 可选：清理 Git 历史中的密钥

由于是私有仓库，风险较低，但建议在合适的时机清理：

```bash
# 使用 git-filter-repo（推荐）
pip install git-filter-repo

# 备份仓库
cp -r . ../Anxin-backup

# 清理所有 .env 文件的历史
git filter-repo --invert-paths \
  --path .env \
  --path backend/.env \
  --path backend/.env.local \
  --path frontend/.env \
  --path frontend/.env.tauri \
  --path livekit.yaml

# 强制推送（所有协作者需重新 clone）
git push origin --force --all
```

**警告：** `git filter-repo` 会重写所有提交历史，所有协作者需要重新 clone 仓库。建议在团队协调后执行。
