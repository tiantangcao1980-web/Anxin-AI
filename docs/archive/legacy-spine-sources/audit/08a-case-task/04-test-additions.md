# TASK-08a 测试补充记录

> 日期：2026-05-06
> 范围：案件 + 任务。

## 已补代码级闭环

| 覆盖点 | 文件 | 证据 |
|---|---|---|
| 案件非法状态跳转 | `backend/src/services/case_service.py` | `pending → completed` 被拒 |
| 案件终态只读 | `backend/src/services/case_service.py` | `closed/cancelled` 修改业务字段被拒 |
| 状态变更事件 | `backend/src/services/case_service.py` | 合法状态变更写 `status_change` 事件 |
| 时间线实际发生时间 | `CaseEvent.event_time` / `add_event(event_at=...)` | 插入顺序与发生时间不一致时，按发生时间倒序 |
| 任务 owner/assignee/admin 过滤 | `backend/src/services/task_service.py` | 同组织非 owner/非 assignee 列表不可见、更新返回 404 |

## 验证

```bash
cd backend && ./.venv/bin/pytest -q tests/test_case_service.py tests/test_lawyer_matching_and_tasks_api.py
# 46 passed, 6 warnings
```

## 剩余发布证据

- 本轮未做 schema 迁移；现有 `CaseEvent.event_time` 作为 `event_at` 语义承载。
- 5×6×4 全矩阵与 Playwright 案件创建 → 分派 → 提交 → 审核 → 归档仍可作为后续扩展证据。
