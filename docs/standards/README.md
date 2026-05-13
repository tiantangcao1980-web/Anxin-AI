# 开发规范体系

> 本目录定义安心智能助手项目的**全套开发规范**。所有代码提交、文档新建、PR 审查必须以此为准。

## 规范清单

| 文档 | 适用对象 | 强制性 |
|---|---|---|
| [naming-convention.md](./naming-convention.md) | 文件名、目录名、变量名 | **强制** |
| [documentation-standard.md](./documentation-standard.md) | 所有 markdown 文档 | **强制** |
| [git-workflow.md](./git-workflow.md) | 分支、PR、worktree、合并 | **强制** |
| [commit-convention.md](./commit-convention.md) | 提交消息格式 | **强制** |
| [code-style.md](./code-style.md) | Python / TypeScript / Rust 代码风格 | **强制** |
| [review-checklist.md](./review-checklist.md) | PR 审查清单 | 推荐 |

## 何时阅读

- **加入项目** → 先读 `naming-convention.md` + `git-workflow.md`
- **开 PR 前** → 对照 `review-checklist.md` 自查
- **新建文档** → 先看 `documentation-standard.md`
- **写代码** → 按 `code-style.md` 执行（lint 会自动检查）
- **不确定写法** → 优先参考已有同类文件，仍不确定回到本目录

## 与其他文档的关系

- 本目录定义"如何工作"（HOW）
- [../00-project-execution-map.md](../00-project-execution-map.md) 定义"做什么"（WHAT，权威导航）
- [../openspec/](../openspec/) 定义"交付什么"（DELIVERABLE）
- [../v3/](../v3/) 定义"V3 智能助手实施细节"

## 违规处理

任何提交违反**强制规范**且未在 PR 中说明合理理由的，CI 应自动拒绝或 reviewer 退回。

## 维护

- 规范变更必须经评审 + 创建 [../adr/](../adr/) 记录原因
- 本目录文档每次有重大修改需在 [../../CHANGELOG.md](../../CHANGELOG.md) 记录
