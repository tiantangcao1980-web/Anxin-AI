# Harness Engineering 部署指引

## 1. 拉取最新代码

```bash
ssh your-server
cd /path/to/Anxin-AI
git pull origin main
```

## 2. 数据库迁移（新增 experience_patterns 表）

```bash
# Docker 环境
docker compose exec backend alembic upgrade head

# 非 Docker 环境
cd backend && alembic upgrade head

# 验证迁移
docker compose exec postgres psql -U postgres -d anxin_legal -c "\dt experience_patterns"
# 应输出: experience_patterns 表
```

## 3. 重建前端（构建优化已更新 vite.config.ts）

```bash
# Docker 环境（自动重建）
docker compose up -d --build frontend

# 手动构建
cd frontend && npm run build
```

## 4. 重启后端服务

```bash
docker compose restart backend
# 或
docker compose up -d --build backend
```

## 5. 验证清单

### 5.1 Harness API 验证

```bash
# 全局统计
curl -s http://localhost:8001/api/v1/harness/stats | python3 -m json.tool

# 工具列表（应返回 15+ 工具）
curl -s http://localhost:8001/api/v1/harness/tools | python3 -m json.tool

# 权限检查
curl -s "http://localhost:8001/api/v1/harness/policy/check?agent=contract_reviewer&tool=send_email"
# 应返回 {"decision": "deny"}

# 任务统计
curl -s http://localhost:8001/api/v1/harness/tasks | python3 -m json.tool

# 能力协商
curl -s "http://localhost:8001/api/v1/harness/capability/negotiate?platform=desktop&mode=top_secret"
```

### 5.2 功能验证

| 测试项 | 操作 | 预期结果 |
|--------|------|---------|
| 多轮追问 | 输入"帮我起草一份合同" | 追问合同类型等，不直接生成 |
| 模板请求 | 输入"给我合同模板" | 返回模板列表，不走AI生成 |
| 法律咨询 | 输入"试用期最长多久？" | 直接回答，不追问 |
| 输出拦截 | AI如果回复"保证胜诉" | 被 output_validator 拦截 |
| Harness面板 | 访问 /admin/harness | 显示Token/任务/工具/审计统计 |
| 专业模式 | 切换到专业模式后提问 | 跳过引导直接处理 |

### 5.3 CLI 验证

```bash
# 创建 API Key
curl -X POST http://localhost:8001/api/v1/cli/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "test-key", "scopes": ["read", "chat"]}'

# 使用 Key 执行命令
curl -X POST http://localhost:8001/api/v1/cli/execute \
  -H "X-API-Key: anxin_cli_xxx" \
  -H "Content-Type: application/json" \
  -d '{"command": "status"}'

# 查看模板列表
curl -X POST http://localhost:8001/api/v1/cli/execute \
  -H "X-API-Key: anxin_cli_xxx" \
  -d '{"command": "template", "args": {"sub": "list"}}'
```

## 6. 环境变量（可选，OA 集成）

```bash
# 飞书
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret

# 钉钉
DINGTALK_APP_KEY=your_app_key
DINGTALK_APP_SECRET=your_app_secret
DINGTALK_AGENT_ID=your_agent_id

# 企业微信
WECOM_CORP_ID=your_corp_id
WECOM_CORP_SECRET=your_corp_secret
WECOM_AGENT_ID=your_agent_id
```

未配置时 OA 集成自动使用模拟模式（不会报错）。

## 7. 回滚方案

如果部署后出现问题：

```bash
# 回滚代码
git revert HEAD
docker compose up -d --build

# 回滚数据库迁移
docker compose exec backend alembic downgrade -1
```
