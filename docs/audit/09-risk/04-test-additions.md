# TASK-09 测试补充记录

> 日期：2026-05-06
> 范围：合规 / 风险 / 尽调 / 舆情 / 资讯收口。

## 已新增或确认的回归

| 覆盖点 | 测试 | 当前结果 |
|---|---|---|
| 尽调模式 + 订阅守卫 | `backend/tests/test_mode_subscription_guards.py` | 组合回归通过 |
| 匿名聊天双 token 拆分 | `backend/tests/test_anonymous_chat_token_split.py` | 组合回归通过 |
| 尽调缓存 org 隔离 | `backend/tests/test_investigation_cache_org_scope.py` | `3 passed` |
| 风险评分确定性与解释契约 | `backend/tests/test_risk_scoring_engine.py` | `2 passed` |
| 爬虫白名单 / robots / UA / host 频控 | `backend/tests/test_crawler_compliance.py` | `4 passed` |
| 调查意图强路由 + 企业名抽取 | `backend/tests/test_due_diligence_intent.py` + `backend/tests/test_chat_due_diligence_routing.py` + `backend/tests/eval/investigation_routing_eval.jsonl` | 组合 `13 passed`；200 条评测样本 |

## 意图路由评测

- 数据集：`backend/tests/eval/investigation_routing_eval.jsonl`
- 样本数：200
- 意图类别：`due_diligence`、`sentiment`、`regulatory_monitoring`、`general_search`
- 当前评测：`intent_accuracy=1.000`
- 含企业名样本：150
- 当前企业名抽取：`company_accuracy=1.000`
- 门槛：意图命中率 ≥ 0.85，企业名抽取准确率 ≥ 0.85
- 实际路由：尽调走 `due_diligence` 专用流程，舆情走 `legal_researcher`，法规监测走 `regulatory_monitor`。

## 全量门禁

```bash
cd backend && ./.venv/bin/pytest -q
# 467 passed, 1 skipped, 17 warnings in 36.11s

cd frontend && npm run lint
# exit 0

cd frontend && npx tsc --noEmit
# exit 0
```

## 剩余发布证据

- 本机 DNS 将部分法定域名解析到 `198.18.0.0/15` 测试网段，真实外网 dry-run 被 SSRF 防护拒绝；发布前必须在预发网络复跑 crawler dry-run。
- 意图路由评测集为脱敏/合成样本；上线后需对真实 query 分布做抽样复核，避免训练集风格过窄。
