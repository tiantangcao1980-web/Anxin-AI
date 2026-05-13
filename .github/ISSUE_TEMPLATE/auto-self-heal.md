---
name: 🤖 Auto Self-Heal
about: 由自愈闭环（O2）自动创建，记录从 trace cluster 到修复尝试的完整链路
labels: auto-self-heal, harness
---

## 来源
- **Cluster ID**：`{cluster_id}`
- **首发 trace_id**：`{trace_id}`
- **首发时间**：{first_seen_at}
- **最近发生**：{last_seen_at}
- **累计次数**：{occurrence_count}
- **影响用户数**：{affected_users}

## 严重度
- **评分**：{score}
- **等级**：{severity}
- **派发对象**：{assignee}
- **业务面**：{routes}
- **理由**：{reason}

## 假设根因
{hypothesis}

## 复现路径
1. ……（由 T2 自动生成的 pytest 用例：`backend/tests/auto/test_cluster_{cluster_id}.py`）

## 自愈循环约束
- 最大迭代次数：{max_iterations}
- Agent 路径白名单：见 `backend/scripts/self_heal/dispatcher.py::AGENT_FORBIDDEN_PATHS`
- PR 必须经过：O1 4 reviewer + H1 强制 harness 测试 + E1 baseline 比对

## 关闭条件
- ✅ 24 小时复查窗口内无同 cluster_id 再现
- 或 ✅ 人工 reviewer 确认修复有效

## 升级规则
- 迭代 ≥ {max_iterations} 次仍失败 → 自动加 `needs-human` 标签 + 通知 oncall
- 任何对禁列路径的修改尝试 → 自动 reject + 告警
