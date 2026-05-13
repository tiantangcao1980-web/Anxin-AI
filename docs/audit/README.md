# 审计与任务执行

> 权威级别：⭐⭐⭐ 执行权威
> 角色：当前执行计划 + 12 域审计实证 + 16 个并行任务

## 顶层入口

| 文件 | 角色 |
|---|---|
| [plan.md](./plan.md) | **当前权威执行计划**（v2.0，2026-05-04）：11 任务波次 + M-A/B/C/D 里程碑 |
| [summary.md](./summary.md) | 状态摘要（2026-05-07）：目标到证据清单、已收口高风险面、阻断项 |
| [ui-ux-audit-2026-05-08.md](./ui-ux-audit-2026-05-08.md) | UI/UX 审计：移动/小程序/桌面问题清单与优化方案 |

## 12 个领域审计子目录

每个域包含 `00-prd-reality-gap.md`（PRD vs 现实差分）+ `01-coverage` + `02-issues` + `03-fixes` + `04-test-additions` + `05-followups`（部分含 `PROPOSAL-*.md` 提案）：

| 目录 | 域 |
|---|---|
| [00-platform/](./00-platform/) | 平台基础（密钥、CI、扫描、GitNexus） |
| [01-auth/](./01-auth/) | 认证、token、CAPTCHA |
| [04-a2ui/](./04-a2ui/) | A2UI 协议、动作授权 |
| [05-contract/](./05-contract/) | 合同生命周期、电子签 |
| [06-document/](./06-document/) | 文档管理、协作、对象存储 |
| [07-rag/](./07-rag/) | RAG 召回质量、引用 |
| [08a-case-task/](./08a-case-task/) | 案件、任务 |
| [08b-lawyer-market/](./08b-lawyer-market/) | 律师匹配、案源 |
| [09-risk/](./09-risk/) | 风险、合规、尽调、舆情 |
| [10-billing-im/](./10-billing-im/) | 计费、支付、IM/RTC |
| [11b-sync-engine/](./11b-sync-engine/) | 桌面同步引擎 |
| [11c-mobile-design/](./11c-mobile-design/) | 移动端 + 设计系统 |

## 16 个并行任务

详见 [_tasks/README.md](./_tasks/README.md)。每个 `task-NN-<domain>.md` 是可独立分配执行的提示词文件。

## PR 工作流

- [_pr/](./_pr/) 存放阶段 PR 草案
- [_pr/wave-1-batch-1-2.md](./_pr/wave-1-batch-1-2.md) 当前最新 PR 集合

## 阅读路径

1. **新人/接手** → 先读 [plan.md](./plan.md) + [summary.md](./summary.md)
2. **领域开发** → 进对应域子目录，从 `00-prd-reality-gap.md` 开始
3. **PR 准备** → 找对应 `task-NN-*.md` 与 `03-fixes.md`
4. **发布前** → 对照 [../release/](../release/) 与 [../openspec/](../openspec/)

## 维护

- 每完成一个领域子任务，更新对应 `05-followups.md`
- 审计周期结束，结论汇总到 [summary.md](./summary.md)
- 旧审计文档归档至 [../archive/](../archive/) 不再更新
