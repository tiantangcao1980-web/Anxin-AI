# ADR-002: 建立文档与命名规范体系

> 日期：2026-05-13
> 状态：已采纳
> 决策人：工程团队

## 背景

V2 → V3 合并完成后（commit `a446429e`），仓库累积了：

- 28+ 篇顶层文档命名风格混乱（`SCREAMING_CASE` / `kebab-case` / `snake_case` 混用）
- 中文目录名（`docs/references/千问UI移动端风格参考/`）
- 日期前缀文件散落（`docs/2026-04-18-*.md`）
- 96 个 git 分支 + 76 个 worktree 失控
- 33 GB Rust 构建缓存 + 19 GB 临时 worktree 占用磁盘
- 12 个 docs/ 子目录缺 README 入口
- 缺 CONTRIBUTING / SECURITY / CHANGELOG 等专业文档
- 提交历史大量 `更新` `修复 bug` 之类无信息 commit

无规范导致：新人接手成本高、AI Agent 容易在过时信息中迷失、PR 评审标准不一致。

## 考虑过的方案

### 方案 A：保持现状 + 单次清理
- 优点：工作量小
- 缺点：清理完几个月又会失控

### 方案 B：建立强制规范体系 + 单次清理 + CI 兜底
- 优点：长期可维护，新人有据可依，AI Agent 有锚点
- 缺点：前期工作量大

### 方案 C：换工具链（如换 Nx / Turborepo）
- 优点：现代化
- 缺点：迁移成本巨大，与本项目实际诉求不匹配

## 决策

**采纳方案 B**。建立 5 份强制规范文档：

| 文档 | 覆盖范围 |
|---|---|
| [naming-convention.md](../standards/naming-convention.md) | 文件名 / 目录名 / 代码符号 / Git 分支 / 环境变量 |
| [documentation-standard.md](../standards/documentation-standard.md) | 文档分层 / 头部模板 / 链接 / 反模式 |
| [git-workflow.md](../standards/git-workflow.md) | 分支模型 / PR / worktree 治理 / 合并策略 |
| [commit-convention.md](../standards/commit-convention.md) | Conventional Commits + 中文 description |
| [code-style.md](../standards/code-style.md) | Python / TypeScript / Rust / Shell 风格 |
| [review-checklist.md](../standards/review-checklist.md) | PR 评审 10 大门 |

配套整改：

- 顶层补 `CONTRIBUTING.md` / `SECURITY.md` / `CHANGELOG.md`
- 13 个 docs/ 子目录补 README
- 建立 `docs/adr/`（本文件 = ADR-002）
- 历史不规范文件批量重命名
- 96 个旧分支 + 76 个 worktree 清理

## 影响

### 正面
- 仓库磁盘从 56 GB → 4.7 GB
- 分支从 99 → 3
- worktree 从 77 → 1
- 文档分层清晰，任何人 30 秒可定位权威源
- 新人第一周 onboarding 路径明确
- AI Agent 协作时减少误判

### 负面
- 历史 commit 不规范遗留（不强制改写历史）
- 需要团队习惯新规范
- CI 需补 commitlint / file-naming 检查（后续 PR）

### 后续行动
- ⏳ CI 加 commitlint + 命名校验脚本
- ⏳ 团队培训：1 次 30 分钟规范同步会
- ⏳ 季度复盘规范执行情况

## 参考

- [本次清理 commit 1: 大规模清理与文档治理](../../README.md)
- [本次清理 commit 2: 顶层导航指针]
- [本次清理 commit 3: 前端孤儿组件 + 配置冗余]
- [本次清理 commit 4: 规范体系建立]
