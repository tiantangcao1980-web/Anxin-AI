# 开发规范体系

> 本目录定义安心智能助手项目的**全套开发规范**。所有代码提交、文档新建、PR 审查必须以此为准。

## 规范全集（13 份）

### 通用层（7 份）

| 文档 | 适用对象 | 强制性 |
|---|---|---|
| [naming-convention.md](./naming-convention.md) | 文件名 / 目录名 / 代码符号 / 分支 / 环境变量 | **强制** |
| [documentation-standard.md](./documentation-standard.md) | 所有 markdown 文档 | **强制** |
| [comment-convention.md](./comment-convention.md) | **代码注释规范（中文为主）** | **强制** |
| [git-workflow.md](./git-workflow.md) | 分支 / PR / worktree / 合并 | **强制** |
| [commit-convention.md](./commit-convention.md) | 提交消息格式（Conventional Commits） | **强制** |
| [code-style.md](./code-style.md) | Python / TypeScript / Rust / Shell 通用风格 | **强制** |
| [review-checklist.md](./review-checklist.md) | PR 评审清单（10 大门） | 推荐 |

### 代码层（6 份，按职责细分）

| 文档 | 适用对象 | 强制性 |
|---|---|---|
| [api-design.md](./api-design.md) | 后端 REST / WebSocket / SSE API 设计 | **强制** |
| [backend-standard.md](./backend-standard.md) | FastAPI + SQLAlchemy + Pydantic 后端 | **强制** |
| [database-standard.md](./database-standard.md) | 数据库 schema / ORM / 迁移 / 多租户 | **强制** |
| [frontend-standard.md](./frontend-standard.md) | React / Vue / RN / Taro 前端（含跨端一致性） | **强制** |
| [testing-standard.md](./testing-standard.md) | 单元 / 集成 / E2E / AI 评测 | **强制** |
| [security-standard.md](./security-standard.md) | 鉴权 / 密钥 / 注入 / 隐私 / 智能体治理 | **强制** |

## 何时阅读

| 任务 | 必读 |
|---|---|
| 加入项目 | `naming-convention` + `git-workflow` + `documentation-standard` |
| 开 PR 前 | `review-checklist` 全勾选 |
| 新建文档 | `documentation-standard` |
| 写后端 API | `api-design` + `backend-standard` |
| 改数据库 | `database-standard` |
| 写前端 | `frontend-standard` + `code-style §2` |
| 写测试 | `testing-standard` |
| 涉及安全 / 鉴权 | `security-standard`（必读）+ [../../SECURITY.md](../../SECURITY.md) |
| Commit / Merge | `commit-convention` + `git-workflow` |

## 学习路径（新成员第一周）

| Day | 阅读 | 目标 |
|---|---|---|
| 1 | [naming-convention.md](./naming-convention.md) | 命名 30 条规约 |
| 1 | [documentation-standard.md](./documentation-standard.md) | 文档分层与头部模板 |
| 2 | [git-workflow.md](./git-workflow.md) + [commit-convention.md](./commit-convention.md) | 工作流 + 提交规范 |
| 3 | 按角色读 backend / frontend / database / api-design | 编码规则 |
| 4 | [testing-standard.md](./testing-standard.md) + [security-standard.md](./security-standard.md) | 质量 + 安全 |
| 5 | [review-checklist.md](./review-checklist.md) | 提 PR 前自查 |

## 与其他文档的关系

| 本目录 | 其他文档 |
|---|---|
| **HOW**（如何工作） | [../00-project-execution-map.md](../00-project-execution-map.md) — 当前权威导航（WHAT） |
| 规范 | [../openspec/](../openspec/) — 交付合同（DELIVERABLE） |
| 规范 | [../v3/](../v3/) — V3 智能助手实施细节 |
| 规范 | [../adr/](../adr/) — 架构决策记录 |

## 违规处理

| 严重程度 | 处理 |
|---|---|
| **强制规范违反** | CI 自动拒绝；reviewer 退回；不得合并 |
| **推荐项偏离** | reviewer 请求说明；可有理由通过 |
| **历史代码不符合** | 渐进重构，新增/改动部分必须符合 |

## 规范维护

| 变更类型 | 流程 |
|---|---|
| 小调整（措辞 / 例子） | 直接 PR，1 人 review |
| 新增规范条款 | 评审 + 团队同步 + 加 ADR |
| 重大规范变更 | RFC + 全员评审 + ADR + CHANGELOG |
| 删除规范 | 同上 + 在文档头标注弃用日期与原因 |

规范变更必须在 [../../CHANGELOG.md](../../CHANGELOG.md) 记录。

## 工具支持

| 规范 | 自动化工具 |
|---|---|
| naming-convention | （未来）`scripts/check-naming.sh` 在 CI 拦截 |
| commit-convention | `commitlint` + git hook |
| documentation-standard | （未来）markdown 文件头部校验 |
| code-style | `ruff` `mypy` `eslint` `tsc` `cargo clippy` |
| api-design | OpenAPI schema + 类型生成 |
| database-standard | `alembic check` |
| testing-standard | `pytest --cov` `vitest --coverage` |
| security-standard | `release-evidence-secret-scan.sh` + CI 依赖扫描 |

## 速查

最常被违反的 5 条规则：

1. ❌ `text(f"...{var}...")` SQL 拼接 → ✅ ORM expression
2. ❌ 路由直接 `query` 数据库 → ✅ 走 service 层
3. ❌ 硬编码 `text-white` → ✅ 语义 `text-primary-foreground`
4. ❌ commit `更新` `修复 bug` → ✅ `fix(scope): 描述`
5. ❌ 测试中真实调用 LLM → ✅ pytest-vcr / mock
