# Harness Engineering 部署指引

## 1. 拉取最新代码

```bash
ssh your-server
cd /path/to/Anxin-Smart-Legal-Services
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

---

## 8. 2026-05-05 六层框架落地补充

> 关联：[docs/audit/harness/README.md](audit/harness/README.md) · [AGENTS.md](../AGENTS.md)

### 8.1 接入率现状（H0 三色矩阵）

H0 体检证伪了"阶段 1-3 已完成"的乐观叙事。8 模块的真实接入率：

| 模块 | 状态 | 主接入点 |
|------|:---:|---------|
| trace_context | 🟢 真接入 | `chat_service.py:865/970` |
| task_engine | 🟢 真接入 | `chat_service.py:876/884/937/962` |
| cost_tracker | 🟢 真接入 | `agents/base.py:517` |
| output_validator | 🟢 强接入 ✨ | `enforcement.py`（H1 升级） |
| context_engine | 🔴 未接入业务 | 仅 `__init__.py` 导出（与旧版 `context_compressor` 并存） |
| policy_engine | 🔴 未接入业务 | 仅 admin API（H1 P0 followup 接入中） |
| tool_registry | 🔴 未接入业务 | 仅 admin API |
| capability_negotiator | 🔴 未接入业务 | 仅 admin API |

详见 [audit/harness/00-integration-matrix.md](audit/harness/00-integration-matrix.md)。

### 8.2 Output Validator 强接入语义（H1）

旧实现：`try/except` 吞异常 + 失败仅 log warning + CRITICAL 加免责声明继续发。

新实现（[`backend/src/harness/enforcement.py`](../backend/src/harness/enforcement.py)）：

| 校验结果 | 动作 | 响应 |
|---------|------|------|
| `pass` | 原样返回 | `harness.validation_action="pass"` |
| `WARNING` | 末尾追加免责声明 | `harness.validation_action="warned"` |
| `FAIL` | task → RETRY，前端可见 `validation_failed=true` | `harness.validation_action="retry"` |
| `CRITICAL` | **替换为统一拒绝消息**（禁止保留原回答） | `harness.validation_action="rejected"` |
| validator 自身异常 | 视同 rejected（保守默认）+ ERROR 日志（不再吞 debug） | `harness.validation_action="validator_error"` |

### 8.3 Trace 落盘 + 失败聚类（T1 设计）

- 模型：[`backend/src/models/trace.py`](../backend/src/models/trace.py)（traces / trace_spans / trace_clusters 三表）
- Sink：[`backend/src/services/trace_sink.py`](../backend/src/services/trace_sink.py)（fire-and-forget 队列 + PII 8 类 scrub + cluster_id 稳定签名）
- 设计：[audit/harness/01-trace-persistence-design.md](audit/harness/01-trace-persistence-design.md)
- **状态**：模型与 sink 已就绪，alembic 迁移与 `end_trace()` hook 待 H1 后续 PR

### 8.4 Eval Harness（E1）

- 入口：`python -m evals._lib.runner --all [--compare-baseline] [--save-baseline]`
- 5 个核心 agent × 5 金标准用例 = 25 case
- 4 维度打分：structural / citation / safety / similarity
- baseline.json 已 git tracked
- PR Gate：分数低于 baseline-5% 退出 1（待接入 `.github/workflows/`）

### 8.5 AI Review Gates（O1）

4 reviewer 并行：
- 🧑‍💻 Code Reviewer（claude-sonnet-4-6）
- 🔐 Security Reviewer（claude-sonnet-4-6）
- 📦 Dependency Reviewer（claude-haiku-4-5）— 仅在依赖文件变更时触发
- 🧪 Regression Reviewer（claude-sonnet-4-6）— 仅在测试文件变更时触发

详见 [audit/harness/02-ai-review-gates-design.md](audit/harness/02-ai-review-gates-design.md)。

### 8.6 自愈闭环（O2）

`backend/scripts/self_heal/`：
- `severity.py` — 4 因子评分 → 4 级（low/medium/high/critical）
- `dispatcher.py` — 决策"派 agent / 派人 / 拒绝"+ 路径白名单
- 业务禁列：auth/payment/billing/refund/esign/mode_switch/alembic_migration → 永远不自愈
- `.github/workflows/self-heal.yml` — cron 30min + manual dispatch（当前仅 dry-run）

详见 [audit/harness/05-self-heal-design.md](audit/harness/05-self-heal-design.md)。

### 8.7 部署前检查清单（叠加在原 §1-7 之上）

- [ ] AGENTS.md 已 review，红线对齐当前业务
- [ ] `pytest backend/tests/test_harness_enforcement.py` 通过
- [ ] `python -m evals._lib.runner --all --compare-baseline --threshold 0.05` 不退化
- [ ] `.github/workflows/ai-review.yml` 在 GitHub 已注册 `ANTHROPIC_API_KEY` secret
- [ ] CODEOWNERS 中的 owner 仍是当前维护者
