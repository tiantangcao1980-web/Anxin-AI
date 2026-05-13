# 贡献指南

> 欢迎贡献安心智能助手项目。请在提交代码前完整阅读本文档。

## 开始之前

1. **阅读权威导航**：[docs/00-project-execution-map.md](docs/00-project-execution-map.md)
2. **阅读规范体系**：[docs/standards/](docs/standards/)（5 份核心规范）
3. **确认当前任务**：[docs/audit/plan.md](docs/audit/plan.md) 中的 11 任务波次
4. **环境准备**：`make init` 一键初始化

## 工作流

### 1. 创建分支

按 [git-workflow.md §2](docs/standards/git-workflow.md) 命名分支：

```bash
git fetch origin
git checkout -b feat/<short-desc> origin/integration/v3-merge-20260512
```

### 2. 开发

- 代码符合 [code-style.md](docs/standards/code-style.md)
- 命名符合 [naming-convention.md](docs/standards/naming-convention.md)
- 测试覆盖见 [code-style.md §7](docs/standards/code-style.md#7-测试覆盖目标)

### 3. 提交

按 [commit-convention.md](docs/standards/commit-convention.md) 写 commit 消息：

```bash
git commit -m "feat(persona): 新增市场研究员 DeepResearch 算法"
```

### 4. 推送 + PR

```bash
git push origin feat/<short-desc>
gh pr create --base integration/v3-merge-20260512
```

PR 描述模板见 [git-workflow.md §3](docs/standards/git-workflow.md#3-pull-request-规范)。

### 5. 自查

对照 [review-checklist.md](docs/standards/review-checklist.md) 全部勾选后请求评审。

## 本地验证

每次提交前必跑：

```bash
# 后端
cd backend
ruff check . && mypy . && pytest -q

# 前端
cd frontend
npm run lint && npm run typecheck && npm run test && npm run build

# 桌面（如改了 desktop/）
cd desktop
cargo clippy --all-targets && cargo test

# 移动（如改了 mobile/）
cd mobile
npm run typecheck && npm run test
```

或使用一键命令：

```bash
make verify-frontend
make verify-backend
```

## 文档贡献

新增/修改文档：

- 命名按 [naming-convention.md](docs/standards/naming-convention.md)
- 头部 5 行模板按 [documentation-standard.md §2](docs/standards/documentation-standard.md#2-文档头部模板)
- 位置按 [documentation-standard.md §1](docs/standards/documentation-standard.md#1-文档分层)

## 安全

发现安全漏洞，**不要**开 public issue，请按 [SECURITY.md](SECURITY.md) 流程私信报告。

## 行为准则

- **专业**：技术讨论对事不对人
- **简洁**：commit/PR/issue 表达清晰
- **互助**：新人提问值得耐心回答
- **诚实**：测试不通过就标失败，不伪造 evidence

## 接手项目第一周

| Day | 任务 |
|---|---|
| 1 | 读 README + docs/00-project-execution-map.md + docs/standards/ |
| 2 | 跑通本地开发环境（`make init && make up`） |
| 3 | 跑通测试套件，理解 CI 流程 |
| 4 | 选一个 [docs/audit/_tasks/task-*.md](docs/audit/_tasks/) 内的小任务作为入门 |
| 5 | 提交第一个 PR，对照 [review-checklist.md](docs/standards/review-checklist.md) 自查 |

## 联系方式

- 项目 issue tracker（GitHub）
- 内部沟通：见团队飞书 / 钉钉空间
