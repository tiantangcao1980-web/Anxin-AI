# 文档归档索引

> 日期：2026-05-08
> 说明：本目录保存已过时或已被新规范取代的历史文档。归档不是删除，目的是保留追溯能力，同时避免后续开发误用旧口径。

## 当前权威入口

请优先阅读：

- `docs/00-project-execution-map.md`
- `docs/strategy/product-architecture-and-requirements-2026-05-08.md`
- `docs/openspec/00-intelligent-assistant-platform-spec.md`
- `docs/openspec/01-commercial-delivery-spec.md`
- `docs/openspec/02-commercial-delivery-test-spec.md`
- `docs/audit/SUMMARY.md`
- `docs/audit/current-state-ui-ux-audit-2026-05-08.md`

## 已归档根目录文档

| 原类型 | 归档文件 | 替代依据 |
|---|---|---|
| 早期升级方案 | `legacy-root-docs/2026-03-10-ai-legal-agent-final-upgrade-plan.md` | `docs/strategy/product-architecture-and-requirements-2026-05-08.md` |
| 早期检查/维护计划 | `legacy-root-docs/2026-03-15-ai-legal-agent-inspection-report.md`、`legacy-root-docs/2026-03-15-ai-legal-agent-maintenance-upgrade-plan.md` | `docs/audit/SUMMARY.md`、`docs/audit/_tasks/README.md` |
| 早期前端优化 | `legacy-root-docs/2026-03-25-frontend-unified-optimization-plan.md` | `docs/audit/current-state-ui-ux-audit-2026-05-08.md`、`docs/frontend-design-governance.md` |
| 早期产品/路线/权限/设计/部署 | `legacy-root-docs/2026-03-26-*.md` | `docs/openspec/*`、`docs/release/*`、`docs/ARCHITECTURE_V2.md` |
| 早期性能分析 | `legacy-root-docs/2026-03-31-*.md` | 当前 release/test evidence 和任务文档 |
| 早期安全审计 | `legacy-root-docs/2026-04-03-*.md` | `docs/release/security-and-privacy-checklist.md`、`docs/audit/00-platform/*` |
| 早期 UI/功能/发版审计 | `legacy-root-docs/2026-04-18-*.md` | `docs/audit/current-state-ui-ux-audit-2026-05-08.md`、`docs/release/commercial-delivery-readiness.md` |
| 早期全端就绪报告 | `legacy-root-docs/2026-04-21-cross-platform-delivery-readiness.md` | `docs/release/commercial-delivery-readiness.md`、`docs/release/test-evidence.md` |

## 使用规则

- 可以引用归档文档解释历史决策。
- 不要用归档文档作为当前开发范围、测试门禁或发布 Go/No-Go 的依据。
- 如果归档文档中的能力重新进入当前路线，必须先同步到 OpenSpec、任务文档和 release evidence。
