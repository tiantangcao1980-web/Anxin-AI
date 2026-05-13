# Day 3 部署验收清单

**日期**：2026-05-13  
**目标**：阿里云生产环境部署 + 演示数据准备

---

## 部署进度跟踪

### ✅ 已完成
- [x] 生产环境 Docker Compose 配置（docker-compose.prod.yml）
- [x] Nginx HTTPS 反向代理配置（nginx/conf.d/anxinai.conf）
- [x] 一键部署脚本（scripts/deploy-prod.sh）
- [x] 演示数据生成脚本（backend/scripts/seed_demo_data.py）
- [x] 环境配置模板（.env.prod.example）
- [x] 阿里云服务器环境检查（14GB 内存，99GB 硬盘）
- [x] 代码克隆到服务器（/root/anxin-smart-legal-services）
- [x] .env 配置文件创建（DeepSeek API + 强密码）
- [x] 前端构建完成（56.6s，dist 目录生成）

### ⏳ 进行中
- [ ] Docker 镜像拉取（Postgres + Redis + Chroma）
- [ ] 后端容器构建和启动
- [ ] 数据库迁移（alembic upgrade head）
- [ ] Let's Encrypt HTTPS 证书申请
- [ ] Nginx + Certbot 启动

### 📋 待完成
- [ ] 演示数据导入（3 个账号 + 示例对话 + 合同样本）
- [ ] 生产环境冒烟测试
- [ ] 演示脚本最终确认

---

## 部署配置摘要

### 服务器信息
- **IP**: 8.134.83.168
- **域名**: anxinai.com（已解析）
- **系统**: Ubuntu 6.8.0，Docker 29.3.1，Docker Compose v5.1.1
- **资源**: 14GB 内存（可用 12GB），99GB 硬盘（可用 78GB）

### 应用配置
- **数据库密码**: `b1fa59cc12aa58db47e8832bf51b9a7e`
- **JWT 密钥**: `eab805ac8a6f7d64025842b7fb44f66b6dfd899c722ddd607efc17095141775a`
- **AI 模型**: DeepSeek Chat（https://api.deepseek.com/v1）
- **管理员密码**: `Admin@2026`

### 演示账号（待导入）
1. **管理员**: admin@anxinai.com / Admin@2026
2. **律师**: lawyer@anxinai.com / Lawyer@2026
3. **企业用户**: demo@anxinai.com / Demo@2026

---

## 验收测试清单

### 1. 基础设施验收
- [ ] 所有容器正常运行（docker compose ps）
- [ ] Postgres 健康检查通过
- [ ] Redis 健康检查通过
- [ ] Chroma 健康检查通过
- [ ] 后端 API 健康检查通过（/health）

### 2. HTTPS 验收
- [ ] HTTP 自动重定向到 HTTPS
- [ ] Let's Encrypt 证书有效
- [ ] SSL Labs 评级 A 或以上
- [ ] 浏览器无证书警告

### 3. 前端验收
- [ ] https://anxinai.com 可访问
- [ ] 首页 10 个 persona 卡片正常显示
- [ ] 登录页面正常
- [ ] 静态资源加载正常（CSS/JS/图片）

### 4. 后端 API 验收
- [ ] GET /api/v1/health 返回 200
- [ ] POST /api/v1/auth/login 登录成功
- [ ] GET /api/v1/personas 返回 10 个 persona
- [ ] POST /api/v1/chat/send 对话接口正常

### 5. 演示数据验收
- [ ] 3 个演示账号可登录
- [ ] 每个 persona 有 2-3 个示例对话
- [ ] 5 个合同样本已导入
- [ ] 对话历史正常显示

### 6. 全端体验验收
- [ ] Web 端：桌面浏览器访问正常
- [ ] H5 端：手机浏览器响应式布局正常
- [ ] 桌面端：unsigned 安装包可运行（本地测试）
- [ ] 小程序：微信开发者工具编译通过（本地测试）

---

## 部署后操作

### 立即执行
1. 导入演示数据：
   ```bash
   ssh root@8.134.83.168
   cd /root/anxin-smart-legal-services
   docker compose -f docker-compose.prod.yml exec backend python scripts/seed_demo_data.py
   ```

2. 验证服务状态：
   ```bash
   docker compose -f docker-compose.prod.yml ps
   docker compose -f docker-compose.prod.yml logs --tail=50
   ```

3. 测试 HTTPS 访问：
   ```bash
   curl -I https://anxinai.com
   ```

### 5/14 上午执行
1. 完整冒烟测试（Web + H5 + 桌面 + 小程序）
2. 演示脚本彩排（10 分钟完整流程）
3. 准备备用方案（录屏视频，防止网络故障）

### 5/15 演示前执行
1. 清空浏览器缓存
2. 提前登录演示账号
3. 检查网络连接（4G/5G 备用）
4. 准备投影设备（HDMI 线）

---

## 故障排查

### 如果部署失败
1. 查看日志：`docker compose -f docker-compose.prod.yml logs`
2. 检查容器状态：`docker compose -f docker-compose.prod.yml ps`
3. 重启服务：`bash scripts/deploy-prod.sh restart`

### 如果 HTTPS 证书申请失败
1. 检查域名解析：`nslookup anxinai.com`
2. 检查 80 端口：`curl http://anxinai.com/.well-known/acme-challenge/test`
3. 手动申请证书：
   ```bash
   docker compose -f docker-compose.prod.yml run --rm certbot certonly \
     --webroot --webroot-path=/var/www/certbot \
     --email tiantangcao1980@gmail.com \
     --agree-tos --no-eff-email \
     -d anxinai.com -d www.anxinai.com
   ```

### 如果数据库迁移失败
1. 检查 Postgres 连接：
   ```bash
   docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d legal_agent_db -c "SELECT version();"
   ```
2. 手动运行迁移：
   ```bash
   docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
   ```

---

## 联系方式

- **部署负责人**: Claude Opus 4.7
- **服务器**: root@8.134.83.168
- **域名**: anxinai.com
- **紧急联系**: tiantangcao1980@gmail.com

---

**当前状态**: 部署进行中（前端构建完成，Docker 镜像拉取中）  
**预计完成时间**: 5-10 分钟  
**下一步**: 等待部署完成 → 导入演示数据 → 冒烟测试
