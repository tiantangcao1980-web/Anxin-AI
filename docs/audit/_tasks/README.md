# 任务提示词索引

> 15 份独立任务提示词。可作为：
> 1. 主对话内 spawn 子代理时的 prompt 内容
> 2. 拆分到独立会话执行（建议每个独立 git worktree）
> 3. 团队成员分工执行的工单

每份文件结构统一：
- §1 范围（要碰的文件 / 不要碰的文件）
- §2 必修 P0（带文件:行号 + 期望状态）
- §3 流程（Step 1-N）
- §4 输出（docs/audit/<NN-module>/01..05.md + 代码 PR）
- §5 风险护栏
- §6 完成标准（DoD）

执行前必读：
- `../PLAN.md` 主计划
- `../00-platform/01-prd-reality-gap.md` PRD vs 现实差分
- `../00-platform/03-cross-cutting-gaps.md` 横切系统缺口

| 任务 | 文件 | 波次 | 工时估 |
|---|---|---|---|
| 任务 1 | task-01-auth.md | 波次 1 | 3-4 天 |
| 任务 2 | task-02-mode-llm.md | 波次 1 | 3-4 天 |
| 任务 3 | task-03-agents.md | 波次 2 | 3-5 天 |
| 任务 4 | task-04-a2ui.md | 波次 2 | 2-3 天 |
| 任务 5 | task-05-contract.md | 波次 2 | 4-5 天 |
| 任务 6 | task-06-document.md | 波次 2 | 4-5 天（含对象存储抽象层）|
| 任务 7 | task-07-rag.md | 波次 2 | 3-4 天 |
| 任务 8a | task-08a-case-task.md | 波次 3 | 3-4 天 |
| 任务 8b | task-08b-lawyer-market.md | 波次 3 | 3-4 天 |
| 任务 9 | task-09-risk-investigation.md | 波次 3 | 4-5 天 |
| 任务 10 | task-10-billing-im.md | 波次 3 | 5-6 天（含 webhook 业务回写）|
| 任务 11a | task-11a-desktop-mvp.md | 波次 4 | 5-7 天 |
| 任务 11b | task-11b-sync-engine.md | 波次 4 | 7-10 天（实质从零）|
| 任务 11c | task-11c-mobile-design.md | 波次 4 | 4-5 天 |
| 任务 12 | task-12-agent-control-plane-skill-evolution.md | 波次 5 | 8-12 天 |
