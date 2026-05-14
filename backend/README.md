# 安心智能助手 — 后端

> Python 3.11 + FastAPI + SQLAlchemy 2.0 (Async) + PostgreSQL + Redis + Qdrant + Neo4j + MinIO
> 关联：[根 README](../README.md) · [AGENTS.md](../AGENTS.md) · [Harness 部署](../docs/DEPLOYMENT_HARNESS.md)

---

## 快速开始

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check src tests
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8001
```

---

## 目录速览

```
backend/
├── src/
│   ├── api/routes/          # 50+ FastAPI 路由
│   ├── services/            # 100+ services（含 trace_sink、context_compressor 等）
│   ├── agents/              # 22 个业务智能体 + Workforce 协调器 + consensus_agent
│   ├── prompts/             # agent / coordinator 系统提示词（C2 阶段逐步迁到 skills/）
│   ├── harness/             # 8 模块 Agent 工程层（见下）
│   ├── models/              # SQLAlchemy 2.0 模型
│   ├── core/                # 安全 / 配置 / 依赖注入
│   ├── middleware/          # 鉴权 / 限流 / CORS
│   └── mcp_server.py        # MCP 协议入口
├── evals/                   # E1 金标准评测集（5 agent × 5 case）
├── scripts/
│   ├── trace_to_test/       # T2 trace → 回归用例转换器
│   └── self_heal/           # O2 自愈严重度评分 + 派发
├── tests/                   # pytest（含 auto/ 自动生成）
└── alembic/                 # 数据库迁移
```

---

## Harness 工程层

本目录是 [六层框架](../docs/audit/harness/README.md) 的 Harness 层实现。`backend/src/harness/` 8 模块：

| 模块 | 职责 | 接入状态（2026-05-14） |
|------|------|:---:|
| `trace_context.py` | trace_id 全链路追踪 + spans | 🟢 真接入 |
| `task_engine.py` | 任务状态机（PENDING→RUNNING→VALIDATING→COMPLETED/FAILED/RETRY） | 🟢 真接入 |
| `cost_tracker.py` | LLM token 用量记录 + 成本聚合 | 🟢 真接入 |
| `output_validator.py` | 输出结构 / 引用 / 风险校验 | 🟢 强接入（H1 通过 [`enforcement.py`](src/harness/enforcement.py)） |
| `policy_engine.py` | Agent + tool 权限白名单 | 🟡 主路径已接（`agents/base.py:_check_mcp_tool_policy`），统一收敛进行中 |
| `context_engine.py` | 统一上下文装配（待与 `services/context_compressor.py` 合并） | 🔴 未接入业务 |
| `tool_registry.py` | 工具注册中心 + 风险分级 | 🔴 未接入业务 |
| `capability_negotiator.py` | 三态模式下的能力可用性判断 | 🔴 未接入业务 |

详见 [接入体检矩阵](../docs/audit/harness/00-integration-matrix.md)。

### Output Validator 强接入（H1）

```python
# backend/src/services/chat_service.py
from src.harness.enforcement import run_validation as harness_validate

response_text, validation_action = await harness_validate(
    response_text=response_text,
    user_query=content,
    agent_name=used_agent,
    route=ctx.route,
)
```

CRITICAL → 替换为统一拒绝消息（**禁止保留原回答**）；FAIL → task RETRY；validator 异常 → ERROR 日志（不再吞 debug）。

---

## Trace 持久化（T1，待 H1 后续 PR 真接入）

- 模型：[`src/models/trace.py`](src/models/trace.py)（traces / trace_spans / trace_clusters 三表）
- Sink：[`src/services/trace_sink.py`](src/services/trace_sink.py)（fire-and-forget queue + PII 8 类 scrub + 稳定 cluster_id）
- 设计：[01-trace-persistence-design.md](../docs/audit/harness/01-trace-persistence-design.md)

---

## Eval Harness（E1）

```bash
# 跑全部
uv run python -m evals._lib.runner --all

# PR Gate（分数低于 baseline-5% 退出 1）
uv run python -m evals._lib.runner --all --compare-baseline --threshold 0.05

# 重置 baseline（仅在主分支稳定后执行）
uv run python -m evals._lib.runner --all --save-baseline
```

5 个 agent × 5 case = 25 金标准用例；4 维度打分：structural / citation / safety / similarity。
详见 [evals/README.md](evals/README.md)。

---

## Self-Heal（O2）

业务禁列（**永远不自愈**）：`auth / payment / billing / refund / esign / mode_switch / alembic_migration`
详见 [05-self-heal-design.md](../docs/audit/harness/05-self-heal-design.md)。

---

## Trace → Test 自动转换（T2）

```bash
uv run python -m scripts.trace_to_test.converter --stdin < trace_dump.ndjson
# 产出：
#   backend/evals/agents/<agent>/auto/cases.jsonl
#   backend/tests/auto/test_cluster_<id>.py
```

PII 双重 scrub 兜底；同 cluster_id 不重复生成 pytest；route 不识别则 skip。

---

## 测试

```bash
# Harness + 强接入回归
uv run pytest tests/test_harness.py tests/test_harness_enforcement.py tests/test_harness_policy_enforcement.py

# trace→test 转换器
uv run pytest tests/test_trace_to_test_converter.py

# 自愈闭环
uv run pytest tests/test_self_heal.py

# Chat 主路径回归
uv run pytest tests/test_chat.py

# 全量
uv run pytest -q tests
```

---

## 后续 P0/P1（六层框架）

详见 [03-h1-followups.md](../docs/audit/harness/03-h1-followups.md)：
- [ ] **P0** policy_engine 主路径统一收敛（合并 `_check_mcp_tool_policy` 与 `policy_enforcement.check_tool_call`）
- [ ] **P0** context_engine vs context_compressor 二选一
- [ ] **P1** cost_tracker 本地 LLM 估算 + 用户配额
- [ ] **P1** task_engine 扩展到合同/尽调/批量
- [ ] **P1** tool_registry 改造（与 C2 协同）
- [ ] **P2** capability_negotiator 统一桌面/前端/服务
