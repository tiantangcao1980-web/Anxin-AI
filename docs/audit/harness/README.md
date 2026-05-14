# Harness 审计与设计文档索引

> 时间窗口：2026-05-05 ~ 2026-05-06
> 关联：[根 README](../../../README.md) · [PROJECT_STATUS](../../../PROJECT_STATUS.md) · [AGENTS.md](../../../AGENTS.md) · [Harness 部署](../../DEPLOYMENT_HARNESS.md)

---

## 六层框架在本项目的实际坐标

| 层 | 已有 | 本轮新增 |
|----|------|---------|
| **Model** | 多 Provider + 私有 LLM 接入 | — |
| **Harness** | `backend/src/harness/` 8 模块 + `/harness` API | H0 接入体检 + H1 强制接入 + `enforcement.py` |
| **Context** | 散落的 prompt + skills/legal·finance 雏形 + hierarchical-memory | C1 三层标准 + AGENTS.md + skills/_template + C2 5 agent skill |
| **Traces** | `trace_context.py` 仅内存 | T1 落盘设计 + `trace_sink.py` + 模型 + `cluster_id` |
| **Eval** | 172 个 pytest + 11 个 playwright | E1 25 金标准 case + 4 维度打分 + baseline + PR Gate compare |
| **Ops** | docker-compose + CI + healthcheck | O1 4 reviewer gate + CODEOWNERS + O2 自愈骨架 |

---

## 9 任务全部完成 ✅

| # | 文档 | 摘要 |
|---|------|------|
| **H0** | [00-integration-matrix.md](00-integration-matrix.md) | 接入体检三色矩阵：8 模块只 3 真接入、1 软接入、4 仅 admin 端可见 |
| **H1** | [03-h1-followups.md](03-h1-followups.md) | 已完成 + 后续 P0/P1 followup 清单 |
| **C1** | [`AGENTS.md`](../../../AGENTS.md) · [docs/context-architecture.md](../../context-architecture.md) · [skills/_template/SKILL.md](../../../skills/_template/SKILL.md) | 三层 Context 标准 + 模板 |
| **C2** | [04-c2-progress.md](04-c2-progress.md) | 5 核心 agent → skill 迁移进度（legal-advisor 完整示范 + 4 骨架） |
| **T1** | [01-trace-persistence-design.md](01-trace-persistence-design.md) | Trace 持久化设计：模型 + sink + scrub + cluster |
| **T2** | [`backend/scripts/trace_to_test/converter.py`](../../../backend/scripts/trace_to_test/converter.py) | trace → 自动回归用例转换器（PII 兜底 + dedupe） |
| **E1** | [`backend/evals/README.md`](../../../backend/evals/README.md) | 25 case + scorer + baseline + runner |
| **O1** | [02-ai-review-gates-design.md](02-ai-review-gates-design.md) · [`.github/workflows/ai-review.yml`](../../../.github/workflows/ai-review.yml) · [`CODEOWNERS`](../../../CODEOWNERS) | 4 reviewer 并行 PR Gate |
| **O2** | [05-self-heal-design.md](05-self-heal-design.md) · [`backend/scripts/self_heal/`](../../../backend/scripts/self_heal/) · [`.github/workflows/self-heal.yml`](../../../.github/workflows/self-heal.yml) | 自愈闭环：severity + dispatcher + path safety + cron 骨架 |

---

## 关键代码改动

| 文件 | 类型 | 摘要 |
|------|:---:|------|
| [`backend/src/harness/enforcement.py`](../../../backend/src/harness/enforcement.py) | NEW | Output Validator 强接入策略层 |
| [`backend/src/services/trace_sink.py`](../../../backend/src/services/trace_sink.py) | NEW | Fire-and-forget queue + PII scrub + cluster_id |
| [`backend/src/models/trace.py`](../../../backend/src/models/trace.py) | NEW | Trace 持久化模型（traces / trace_spans / trace_clusters） |
| [`backend/src/services/chat_service.py`](../../../backend/src/services/chat_service.py) | EDIT | `941-967` / `988-1005` 改为强接入 + 透出 `harness` 字段 |
| [`backend/src/api/routes/chat.py`](../../../backend/src/api/routes/chat.py) | EDIT | `ChatResponse` 新增 `harness: Optional[dict]` |
| [`backend/scripts/trace_to_test/converter.py`](../../../backend/scripts/trace_to_test/converter.py) | NEW | trace→test 转换 + PII 兜底 |
| [`backend/scripts/self_heal/severity.py`](../../../backend/scripts/self_heal/severity.py) | NEW | 严重度评分 |
| [`backend/scripts/self_heal/dispatcher.py`](../../../backend/scripts/self_heal/dispatcher.py) | NEW | 派发决策 + 路径白名单 |
| [`backend/evals/_lib/{runner,scorer}.py`](../../../backend/evals/_lib/) | NEW | Eval CLI + 4 维度打分 |
| [`AGENTS.md`](../../../AGENTS.md) | NEW | Agent 工作宪章（红线/路由/反 slop） |
| [`CODEOWNERS`](../../../CODEOWNERS) | NEW | 人类 reviewer 兜底 |

## 测试

| 套件 | 用例数 | 覆盖 |
|------|:---:|------|
| `tests/test_harness_enforcement.py` | 14 | enforcement 5 动作 + PII scrub 8 类 + cluster_id 稳定性 |
| `tests/test_trace_to_test_converter.py` | 5 | case+pytest 写入 + PII 兜底 + dedupe + skip 未知 route |
| `tests/test_self_heal.py` | 22 | severity 分级 + dispatcher 决策 + 路径白名单 |
| 全量回归 | 116/116 ✅ | chat / harness / business_agents / authz / dd_routing / ... |

---

## 后续路线（按优先级）

### P0（本周）
- **policy_engine 接入主路径**：在 `agents/base.py` tool 调用前后加门控；接 `approvals` 工作流
- **context_engine vs context_compressor 二选一**：保留 context_engine（包了 memory/experience 整合）+ 删旧 import

### P1（下周）
- **cost_tracker 本地 LLM 估算 + 用户配额**：本地 LLM 不返 `usage` 时按 token 估；超额阻断
- **task_engine 扩展到合同/尽调/批量**：补齐长任务状态机
- **tool_registry 改造**（与 C2 Phase B 协同）：从 prompt 抽到注册式

### P2（视情况）
- **capability_negotiator 统一**：桌面 / 前端 ModeGate / 服务三套合并
- **C2 Phase B 完成**：剩余 17 个 agent + 4 个 coordinator prompt 全量迁移
- **T1 真接入**：alembic 迁移 + `end_trace()` hook + AdminHarness UI

详见 [03-h1-followups.md](03-h1-followups.md)。

---

## 与上一轮 11 模块审计的关系

```
横向（11 模块审计）        纵向（9 能力建设）
做覆盖                     建闭环
一次性                     持续机制

横向找 P0 钉子（密钥/CAPTCHA/webhook/...）
   ↓
纵向把闭环闭上（H1 强接入 / E1 baseline / O1 PR Gate / O2 自愈骨架）
   ↓
下一次横向审计自动享受闭环红利（O1 reviewer 自动看 / E1 自动比 baseline）
```

后续既可继续推进六层（P0/P1/P2 列表）也可启动 11 模块横向（[认证 / 三态 / AI 智能体 / ...](../../audit/)），二者并行不冲突。
