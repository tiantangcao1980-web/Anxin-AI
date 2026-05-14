# Trace 落盘 + 失败聚类 + Dashboard（T1 设计）

> 时间：2026-05-05
> 前置：H0 已完成（trace_context.py 在主路径真接入但仅在内存）
> 后续：H1 把 sink 真正 hook 进 `end_trace()`；T2 基于落盘数据自动转测试

---

## 1. 决策（ADR）

### 1.1 存储引擎：PostgreSQL JSONB

| 候选 | 优点 | 缺点 | 决策 |
|------|------|------|:---:|
| **PostgreSQL JSONB**（已有） | 复用基础设施 / GIN 索引 / 跨服务 join 用户/会话 | 高 QPS 时压力大 | ✅ 选 |
| ClickHouse | 高吞吐分析友好 | 引入新依赖 / 部署成本 | ❌ 不选 |
| 单独 SQLite | 桌面端可复用 | 跨服务汇聚困难 | ❌ 不选（桌面端单独走本地表，云端用 PG） |

### 1.2 写入策略：Fire-and-Forget Queue

- **不阻塞主路径**：`end_trace()` 只 enqueue 摘要 dict，不做 DB IO
- **批量落盘**：worker 每 500ms 或满 50 条 flush 一次
- **降级**：队列满（默认 10K）丢弃最早的；同时 sentry/log 报警
- **PII 脱敏**：进队列前过 `pii_service.scrub()`（trace 里禁止落 PII）

### 1.3 数据模型分两表

- `traces` — 一条对应一次完整请求（粗粒度，主索引 trace_id）
- `trace_spans` — 子操作（agent / tool / LLM 调用），高基数

不做"一行 JSONB 装 spans"——查询/聚合性能太差。

### 1.4 跨设备（Web / Desktop / Mobile / 小程序）

- 客户端在请求 header 带 `X-Client-Trace-Id`（客户端生成的 client_trace_id）
- 后端 `start_trace` 接受 client_trace_id，落盘字段 `client_trace_id` + `client_type`
- 这样桌面端的失败可以和云端的失败被同一个查询命中

---

## 2. 数据模型

### 2.1 `traces` 表

| 列 | 类型 | 索引 | 说明 |
|---|------|:---:|------|
| `id` | UUID PK | — | trace_id |
| `client_trace_id` | String(32) | idx | 客户端生成，跨端聚合用 |
| `client_type` | Enum | idx | web / desktop / mobile / miniapp |
| `user_id` | UUID FK | idx | 关联 users |
| `org_id` | UUID FK | idx | 组织维度查询 |
| `conversation_id` | UUID | idx | 关联会话 |
| `route` | String(64) | idx | chat / contract / dd / ... |
| `agent_used` | String(64) | idx | 命中聚类 |
| `started_at` | DateTime | idx | 时间范围查询 |
| `elapsed_ms` | Float | — | |
| `total_tokens` | Integer | — | |
| `total_cost_usd` | Numeric(10,6) | — | |
| `span_count` | Integer | — | |
| `error_count` | Integer | idx | 失败筛选 |
| `cluster_id` | String(64) | idx | 失败聚类 ID（见 §3） |
| `status` | Enum | idx | success / partial / failed |
| `mode` | Enum | idx | local / hybrid / cloud |
| `summary` | JSONB | GIN | 完整 to_summary() 结果 |

### 2.2 `trace_spans` 表

| 列 | 类型 | 索引 | 说明 |
|---|------|:---:|------|
| `id` | UUID PK | — | span_id |
| `trace_id` | UUID FK | idx | 关联 traces |
| `parent_span_id` | UUID | — | 树结构 |
| `operation` | String(128) | idx | coordinator.analyze / agent.X.chat / tool.Y |
| `agent_name` | String(64) | idx | |
| `tool_name` | String(64) | idx | |
| `started_at` | DateTime | — | |
| `latency_ms` | Float | — | |
| `status` | Enum | idx | started / success / error / timeout |
| `error_type` | String(64) | idx | 聚类用 |
| `error_msg` | Text | — | 已脱敏 |
| `prompt_tokens` | Integer | — | |
| `completion_tokens` | Integer | — | |
| `metadata` | JSONB | — | 杂项 |

### 2.3 `trace_clusters` 表（聚类输出，T2 也用）

| 列 | 类型 | 说明 |
|---|------|------|
| `cluster_id` | String(64) PK | hash(error_type + agent + tool + status) |
| `signature` | JSONB | 聚类 key 的可读形式 |
| `first_seen_at` | DateTime | |
| `last_seen_at` | DateTime | |
| `occurrence_count` | Integer | |
| `affected_users` | Integer | distinct user_id |
| `severity` | Enum | low / medium / high / critical |
| `assigned_to` | String(64) | agent / human / queue |
| `status` | Enum | open / triaging / fixed / suppressed |
| `linked_pr_url` | Text | 自愈闭环关联（O2 用） |

---

## 3. 失败聚类规则

```
cluster_key = sha1(
    error_type + "|" +
    agent_name + "|" +
    tool_name + "|" +
    status_code +
    normalize(error_msg_first_line)   # 去 trace_id / 用户 ID / 时间戳
)
```

- 严重度自动评分：
  - **critical**: error_count > 100/h OR affected_users > 50
  - **high**: error_count > 20/h OR affected_users > 10
  - **medium**: error_count > 5/h
  - **low**: 其他
- 自动指派：
  - low / medium → agent 修复 队列
  - high → agent 修复 + 人 review
  - critical → 仅 oncall 人

---

## 4. PII 脱敏（强约束）

落盘前必须过 `pii_service.scrub()`，至少处理：

| 类型 | 处理 |
|------|------|
| 身份证号 | mask 后 4 位 |
| 手机号 | mask 中间 4 位 |
| 邮箱 | mask 用户名 |
| 银行卡 | 整段替换为 `[MASK_CARD]` |
| LLM API Key | 整段替换为 `[MASK_KEY]` |
| 用户密码 | 整段替换为 `[MASK_PWD]` |
| 文件路径 | 保留扩展名，路径替换为 `[PATH]` |
| 客户姓名（可选） | 配置开关；默认开 |

**测试要求**（H1 实施时强制）：
- `tests/harness/test_trace_pii_scrub.py` 必须 100% 覆盖以上类型
- 任何新加 PII 字段必须先扩 scrub 再扩 trace

---

## 5. Admin Dashboard API（新增）

复用现有 `api/routes/harness.py`，新增 4 个端点：

| Method | Path | 用途 | 权限 |
|--------|------|------|:---:|
| GET | `/harness/traces` | 列表查询（user/agent/status/since 过滤） | admin |
| GET | `/harness/traces/{trace_id}` | 完整 trace + spans | admin |
| GET | `/harness/clusters` | 失败聚类列表 | admin |
| POST | `/harness/clusters/{cluster_id}/assign` | 指派给 agent / human | admin |

前端配套：`frontend/src/pages/admin/AdminHarness.tsx` 增加 traces / clusters 两个 tab（已有 AdminHarness 监控页骨架，T1 后期补 UI）。

---

## 6. 落地骨架（本任务产出 stub）

T1 产出 3 个文件，**不修改主路径**（hook 留给 H1）：

| 文件 | 状态 | 说明 |
|------|:---:|------|
| `backend/src/models/trace.py` | ✅ T1 新增 | SQLAlchemy 模型 |
| `backend/src/services/trace_sink.py` | ✅ T1 新增 | 队列 + worker + scrub 接口 |
| 本设计文档 | ✅ T1 新增 | docs/audit/harness/01-... |

H1 阶段会做：
- Alembic 迁移
- 修改 `trace_context.end_trace()` 调用 `trace_sink.enqueue()`
- 实际 hook `pii_service.scrub`
- AdminHarness UI

---

## 7. 验收门槛

T1 设计完成 = 以下都满足：
- ✅ ADR 决策清晰（存储 / 写入策略 / 跨端）
- ✅ 模型字段完整可生成 DDL
- ✅ 聚类规则可由人类在 5 分钟内理解
- ✅ PII 脱敏清单覆盖 8 类
- ✅ Dashboard API 列出 + 权限标注
- ✅ 不动主路径代码

T1 真正"上线" = H1 完成后 + Alembic 迁移成功 + 1 周观察期内 trace 表增长正常 + Dashboard 可用。

---

## 8. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 高 QPS 拖垮 PG | 队列降级 + 落盘批量 + 单独读副本 |
| trace 含 PII 泄漏 | scrub 必过 + 单元测试强制覆盖 + 抽样人工 review |
| 跨端 trace_id 冲突 | client_trace_id 32 字节 UUID + 服务端再加自有 trace_id |
| 旧日志格式不兼容 | 模型字段全可空 + 迁移期 dual write |
| Dashboard 暴露内部信息 | 严格 admin 鉴权 + 二次审计每次访问 |
