# 命名规约

> 强制规范。所有新建/重命名文件、目录、代码符号必须遵守。

## 1. 文件名

| 文件类型 | 规则 | 示例 |
|---|---|---|
| **项目级 markdown**（仓库根） | `SCREAMING_SNAKE_CASE.md` | `README.md` `CONTRIBUTING.md` `SECURITY.md` `CHANGELOG.md` `LICENSE` |
| **docs/ 内所有 markdown** | `kebab-case.md` 全小写 | `architecture-v2.md` `deployment-desktop.md` |
| **审计任务文件** | `task-NN-domain.md` 全小写 | `task-01-auth.md` `task-08a-case-task.md` |
| **架构决策记录 (ADR)** | `NNN-decision-title.md` | `001-v3-merge-strategy.md` |
| **配置文件** | 沿用工具惯例（小写） | `.env.example` `docker-compose.yml` `tauri.conf.json` |
| **Shell 脚本** | `kebab-case.sh` | `commercial-readiness-gate.sh` |
| **Windows 批处理** | `kebab-case.bat` | `start-dev.bat` `setup.bat` |
| **Python 文件** | `snake_case.py` | `chat_service.py` `legal_advisor.py` |
| **TS/JS 组件** | `PascalCase.tsx` | `ChatCanvas.tsx` `AdminLayout.tsx` |
| **TS/JS 工具/hook** | `camelCase.ts` 或 `useXxx.ts` | `useChatHistory.ts` `formatCurrency.ts` |
| **Rust 文件** | `snake_case.rs` | `remote_control.rs` `sync_engine.rs` |
| **测试文件** | `test_<被测>.py` / `<被测>.test.ts` / `<场景>.spec.ts` | `test_chat_service.py` `api.test.ts` `auth.spec.ts` |

## 2. 目录名

| 规则 | 示例 |
|---|---|
| **全小写 `kebab-case`** | `docs/v3/` `frontend/src/components/document-workbench/` |
| **绝对禁止中文** | ❌ `docs/references/千问UI移动端风格参考/`<br>✅ `docs/references/qwen-mobile-ui-refs/` |
| **绝对禁止空格** | ❌ `docs/design refs/`<br>✅ `docs/design-refs/` |
| **下划线前缀**仅用于"元数据/隐藏"目录 | `docs/audit/_tasks/` `docs/audit/_pr/`（约定俗成） |

## 3. 日期前缀（受限）

**仅在以下两类文档允许日期前缀**：

| 允许场景 | 格式 | 示例 |
|---|---|---|
| `docs/archive/legacy-root-docs/` 归档 | `YYYY-MM-DD-topic.md` | `2026-04-18-ui-audit-and-optimization-plan.md` |
| 审计快照 / UI 走查 | `topic-YYYY-MM-DD.md` | `ui-ux-audit-2026-05-08.md` |
| ADR | `NNN-title.md`（不带日期，用编号） | `001-v3-merge.md` |

**其他所有场景禁止日期前缀**。原因：日期是"何时写"而非"是什么"，违反"文件名说明用途"原则。

## 4. 代码符号

| 类型 | Python | TypeScript | Rust |
|---|---|---|---|
| 类名 | `PascalCase` | `PascalCase` | `PascalCase` |
| 函数/变量 | `snake_case` | `camelCase` | `snake_case` |
| 常量 | `UPPER_SNAKE` | `UPPER_SNAKE` | `UPPER_SNAKE` |
| 模块/文件 | `snake_case.py` | `camelCase.ts` 或 `PascalCase.tsx`（组件） | `snake_case.rs` |
| 私有 | `_leading` | 无强制（用 `_` 表意） | `pub(crate)` 或不暴露 |

## 5. Git 分支

| 类型 | 格式 | 示例 |
|---|---|---|
| 功能开发 | `feat/<short-desc>` | `feat/v3-anxin-assistant` |
| Bug 修复 | `fix/<short-desc>` | `fix/login-token-refresh` |
| 重构 | `refactor/<short-desc>` | `refactor/chat-page-split` |
| 文档 | `docs/<short-desc>` | `docs/v3-roadmap-sync` |
| 整合分支 | `integration/<topic-YYYYMMDD>` | `integration/v3-merge-20260512` |
| 发布分支 | `release/vX.Y.Z` | `release/v1.0.0` |
| 临时实验 | `wip/<short>` | `wip/test-llm-router` |

**禁止**使用：
- `claude/<adjective-name>` 之类自动生成的临时分支作为长期分支
- 仓库 owner 私人名前缀（`pengcheng/xxx`）
- worktree 临时分支保留过 1 周

## 6. 环境变量

`UPPER_SNAKE_CASE`，按域分组：

```env
# 数据库
DATABASE_URL=
DATABASE_POOL_SIZE=
# Redis
REDIS_URL=
# LLM
LLM_PROVIDER=
LLM_API_KEY=
```

## 7. Docker / K8s 资源

- **服务名**：`anxin-<role>`（如 `anxin-backend` `anxin-frontend`）
- **镜像 tag**：`semver`（`v1.0.0`）或 `git-sha`
- **网络名**：`anxin-net`

## 8. 不规范命名修正流程

发现不规范时：

1. **新增**：直接按规范命名，无需评审
2. **重命名 < 5 文件**：在 PR 中直接 `git mv`
3. **重命名 ≥ 5 文件 / 跨模块**：先发 issue + ADR，评审通过后批量执行
4. **第三方文件**：保持原名（如 `node_modules/` 内部）

## 9. 速查表

```
✅ docs/v3/architecture.md
✅ docs/audit/_tasks/task-01-auth.md
✅ docs/standards/naming-convention.md
✅ frontend/src/components/ChatCanvas.tsx
✅ backend/src/services/chat_service.py
✅ scripts/windows/start-dev.bat

❌ docs/ARCHITECTURE.md       (顶层文档应 kebab-case)
❌ docs/audit/_tasks/TASK-01.md   (审计任务应小写)
❌ frontend/src/Chat_Canvas.tsx   (组件应 PascalCase 无下划线)
❌ docs/references/千问UI参考/    (目录禁止中文)
❌ start_dev.bat                  (Windows 脚本应 kebab-case)
❌ docs/2026-04-15-new-feature.md (日期前缀仅 archive 允许)
```
