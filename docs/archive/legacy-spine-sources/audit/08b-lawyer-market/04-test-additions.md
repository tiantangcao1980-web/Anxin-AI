# TASK-08b 测试补充记录

> 日期：2026-05-06
> 范围：找律师 + 案源市场 + 律所端。

## 已补代码级闭环

| 覆盖点 | 文件 | 证据 |
|---|---|---|
| 本地模式不暴露律师撮合 | `backend/src/api/routes/lawyer_matching.py` | `X-Privacy-Mode: local` 创建咨询返回固定 403 |
| 本地模式不暴露案源市场 | `backend/src/api/routes/case_market.py` | `X-Privacy-Mode: local` 浏览案源返回固定 403 |
| 投标前强制利益冲突检查 | `backend/src/api/routes/case_market.py` + `ConflictCheckService` | 历史案件当事人命中时投标返回 409，`bid_count` 不增长 |
| 结构化当事人提取 | `backend/src/services/conflict_check_service.py` | `Case.parties` 支持 dict/list/string 形态 |
| 同分律师曝光公平 | `backend/src/services/lawyer_matching_service.py` | 同输入 30 次 top 曝光最大差 ≤ 1 |

## 验证

```bash
cd backend && ./.venv/bin/pytest -q tests/test_lawyer_matching_and_tasks_api.py
# 17 passed, 6 warnings

cd backend && ./.venv/bin/pytest -q
# 467 passed, 1 skipped, 17 warnings in 36.11s
```

## 剩余发布证据

- 利益冲突仍需补“关联方 / 历史年限 / 人工复核申诉”端到端证据。
- 律所 partner/lawyer/paralegal RBAC 矩阵、案源市场 8 API 全打勾和 1000 次公平性报告仍是发布前扩展证据。
