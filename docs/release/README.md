# 发布证据与运行手册

> 权威级别：⭐⭐⭐ 执行权威
> 角色：商业发布前的证据采集、外部资源对接、回滚预案

## 顶层入口

| 文件 | 角色 |
|---|---|
| [48-hour-commercial-delivery-plan.md](./48-hour-commercial-delivery-plan.md) | 短期战术：48 小时冲刺计划、lane 分配、completion gate |
| [commercial-delivery-readiness.md](./commercial-delivery-readiness.md) | **Go/No-Go 判定**：缺口清单、证据要求 |
| [commercial-delivery-checklist.json](./commercial-delivery-checklist.json) | prompt-to-artifact 成功标准 |
| [commercial-delivery-lanes.json](./commercial-delivery-lanes.json) | 多智能体/多人并行执行的写入范围 + completion gate |
| [completion-audit.md](./completion-audit.md) | 核心能力完成度审计与验收标准 |
| [test-evidence.md](./test-evidence.md) | 已有测试、未补证据、新增测试要求 |
| [security-and-privacy-checklist.md](./security-and-privacy-checklist.md) | 发布前安全/隐私/密钥/权限/治理清单 |

## 外部资源对接

| 文件 | 角色 |
|---|---|
| [external-resource-handoff.md](./external-resource-handoff.md) | 支付/电签/爬虫渠道凭据、真机、证书交付清单 |
| [external-inputs-checklist.md](./external-inputs-checklist.md) | 第三方配置、env、webhook、证书同步检查表 |
| [external-resource-requirements.json](./external-resource-requirements.json) | 资源需求结构化清单 |
| [third-party-api-preparation.md](./third-party-api-preparation.md) | 支付、电签、爬虫、地图 API 沙箱准备 |
| [goal-contract-commercial-readiness.md](./goal-contract-commercial-readiness.md) | 桌面 MVP / RAG / 案件市场真实证据要求（2026-05-09） |

## 运行手册

| 文件 | 角色 |
|---|---|
| [evidence-collection-runbook.md](./evidence-collection-runbook.md) | 证据采集 SOP |
| [rollback-runbook.md](./rollback-runbook.md) | 回滚应急预案 |
| [mobile-error-state-release-notes.md](./mobile-error-state-release-notes.md) | 移动端错误态 release note |

## 证据子目录

[evidence/](./evidence/) 含：
- `static-quality-baseline.md` — 代码质量基线
- `rag-full50-live-baseline.md` — RAG 内建法律 50 例基线（recall@10: 1.000）
- `payment-sandbox.md` / `esign-sandbox.md` — 支付/电签沙箱预检
- `agent-governance-smoke.md` — 智能体治理烟测
- `desktop-runtime-smoke.md` / `mobile-device-smoke.md` — 桌面/移动 smoke
- `artifacts/` — 26+ JSON 证据 artifact

## 阅读路径

1. **想知道能否发布** → [commercial-delivery-readiness.md](./commercial-delivery-readiness.md)
2. **准备采集证据** → [evidence-collection-runbook.md](./evidence-collection-runbook.md)
3. **外部资源未到位** → [external-resource-handoff.md](./external-resource-handoff.md)
4. **应急回滚** → [rollback-runbook.md](./rollback-runbook.md)

## 商业门禁脚本

```bash
# 快速门禁（不跑真机/沙箱）
bash scripts/commercial-readiness-gate.sh --quick

# 完整门禁（含本地测试）
bash scripts/commercial-readiness-gate.sh --with-local-tests
```

## 维护

- evidence/* 的 `Status: pending/complete` 必须实事求是
- mock / 伪造结果不计入 release evidence
- 资源到位后及时更新 [external-inputs-checklist.md](./external-inputs-checklist.md)
