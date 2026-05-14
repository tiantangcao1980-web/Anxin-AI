# 自愈闭环（O2）

> 时间：2026-05-05
> 依赖：T1（cluster_id 落盘）+ T2（trace→test 通道）+ O1（4 reviewer gate）

---

## 1. 闭环全图

```
   生产/测试环境
        │
        ▼
   ┌─────────┐    Sentry / CloudWatch / 自家 audit_log
   │ 信号采集 │
   └────┬────┘
        ▼
   ┌─────────┐    T1 cluster_id（同 cluster_id 自动聚合）
   │  聚类    │
   └────┬────┘
        ▼
   ┌─────────────────┐    O2 严重度评分：occurrence_count + affected_users + 业务面
   │  风险分级 + 指派 │
   └────┬────────────┘
        ├─ low/medium ──► agent 自愈队列
        ├─ high       ──► agent 自愈 + 人 review
        └─ critical   ──► 仅 oncall 人，不自动修
        │
        ▼ （low/medium/high 路径）
   ┌─────────────┐    T2 trace→test：先有失败用例
   │  生成 issue  │    issue 模板：trace_id / cluster_id / 复现 / 假设根因
   └────┬────────┘
        ▼
   ┌─────────────────┐    Ralph Loop 模式：修 → 跑 H1 验证 → 跑 E1 → PASS 才发 PR
   │  agent 修复循环  │
   └────┬────────────┘
        ▼
   ┌─────────────────┐    O1 4 reviewer + agent eval gate
   │  PR Gate 全跑    │
   └────┬────────────┘
        │
        ├─ block ──► 退回 agent loop（最多 N 次）→ 升级人
        └─ pass  ──► 等待 1 名 human reviewer 签字（永不 auto-merge）
                  │
                  ▼
            ┌────────┐
            │  部署   │（按现有 CI/CD 路径）
            └───┬────┘
                ▼
            ┌────────┐
            │  复查   │ 24h 观察期：同 cluster_id 是否再现
            └───┬────┘
                ├─ 无再现 ──► trace_clusters.status = FIXED + 关闭 issue
                └─ 再现   ──► reopen + 风险升级
```

---

## 2. 严重度评分（在 T1 已定义的基础上加业务面）

| 因子 | 权重 | 说明 |
|------|:---:|------|
| `occurrence_count / hour` | 0.30 | T1 提供 |
| `affected_users` | 0.30 | distinct user_id |
| `business_surface` | 0.20 | 路由命中 chat/contract/payment 等核心 → 加权 |
| `error_class` | 0.20 | LLM 调用失败 / DB / Network / 业务逻辑 |

阈值：
- `score > 0.8` → critical
- `0.5 < score ≤ 0.8` → high
- `0.2 < score ≤ 0.5` → medium
- 其它 → low

**禁止自愈的领域**（无论分数多高）：
- 认证、支付、退款、电签、模式切换、数据库迁移
- 这些只生成 issue 给人，**不**派 agent

---

## 3. Agent 修复循环（Ralph Loop 模式）

每轮 fix → verify → ship 流程：

```
loop while iter < MAX_ITER:
    1. 读 issue（含 trace_id, cluster_id, suspected_files）
    2. agent 提建议补丁 → 写到独立 branch
    3. 跑 H1 强制接入测试（pytest -k harness）
    4. 跑 E1 baseline（python -m evals._lib.runner --all --compare-baseline）
    5. 如果 4 个都过 → 发 PR + 自动指派 4 reviewer
    6. 如果失败 → iter++，更新 issue 评论，进入下一轮
    7. iter == MAX_ITER → 升级，转人，添加 needs-human 标签
```

**约束**：
- MAX_ITER = 3
- branch 命名：`auto/heal/cluster-<id>-<iter>`
- 自动 PR 默认 draft，需要等 4 reviewer + 1 human dismiss draft
- agent 不能改 CODEOWNERS、不能改 .github/workflows/、不能改 AGENTS.md

---

## 4. Issue 模板

见 `.github/ISSUE_TEMPLATE/auto-self-heal.md`。

---

## 5. 触发方式

### 5.1 定时触发（GitHub Actions cron）

每 30 分钟扫一次 `trace_clusters` 表（来自 T1）：
- 状态为 `OPEN` + 严重度 ∈ {low, medium, high}
- 未在禁止列表（auth/payment/...）
- 拉到本地 → 走自愈循环

### 5.2 实时触发（webhook）

如果 cluster 突然 occurrence > 100/h → critical → 直接 oncall 人，不走 agent。

---

## 6. 文件清单（本任务交付）

| 文件 | 状态 |
|------|:---:|
| `docs/audit/harness/05-self-heal-design.md` | ✅ 本文件 |
| `backend/scripts/self_heal/severity.py` | ✅ 严重度评分（纯函数 + 测试） |
| `backend/scripts/self_heal/dispatcher.py` | ✅ 决策"派 agent / 派人 / 拒绝"（纯函数 + 测试） |
| `.github/ISSUE_TEMPLATE/auto-self-heal.md` | ✅ Issue 模板 |
| `.github/workflows/self-heal.yml` | ✅ cron + manual dispatch 骨架 |
| `backend/tests/test_self_heal.py` | ✅ 单元测试 |

**未交付（后续 PR）**：
- 真正的 cron 任务消费 `trace_clusters` 表（依赖 T1 alembic 迁移）
- agent loop 真接入（依赖 H1 P0 followup 全部完成）
- 24h 复查的 cluster status 翻转（依赖 T1 数据落地）

---

## 7. 风险护栏（写进每个组件）

| 风险 | 缓解 |
|------|------|
| Agent 改了不该改的（CODEOWNERS / workflow / AGENTS.md） | dispatcher 默认拒绝；workflow 路径白名单 |
| Critical 误判触发 agent | 严重度评分双阈值 + 业务面禁列 |
| 自动 PR 被自动 merge | 永远 draft + CODEOWNERS 强制 1 名 human |
| Agent 改坏未触发回归（沉默错误）| O1 + E1 + H1 三道 gate |
| 24h 内重启/部署造成 cluster 假性恢复 | 复查窗口 ≥ 24h，且必须有正常请求量基数 |
