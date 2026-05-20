# Commit 消息规范
> ⚠️ **2026-05-20 路线纠正**：本文档涉及的 uni-app / apps/uni-mobile 技术链路已**彻底放弃**。
> 当前移动端路线 = mobile/ (Expo + RN) + mini-program/ (Taro)，详见 PROJECT_STATUS.md 和 PRODUCT_ROADMAP.md。
> 以下内容保留为历史决策上下文，不代表当前实施方向。

> 强制规范。所有 commit 必须符合 [Conventional Commits 1.0.0](https://www.conventionalcommits.org/) 扩展约定。

## 1. 格式

```
<type>(<scope>): <description>

<body 可选>

<footer 可选>
```

## 2. Type（必填）

| Type | 含义 | 示例 |
|---|---|---|
| `feat` | 新功能 | `feat(persona): 新增市场研究员 DeepResearch 算法` |
| `fix` | Bug 修复 | `fix(auth): 修复 token 刷新偶发 401` |
| `refactor` | 重构（不改行为） | `refactor(chat): Chat.tsx 拆分到 5 个 hooks` |
| `perf` | 性能优化 | `perf(llm): 引入 httpx 连接池` |
| `docs` | 文档 | `docs(v3): 同步 P8 完成进度到 ROADMAP` |
| `test` | 测试 | `test(rag): 补 full50 黄金集 5 个用例` |
| `chore` | 构建 / 工具 / 清理 | `chore(repo): 大规模清理 desktop/target 缓存` |
| `style` | 仅格式化（无代码逻辑改动） | `style(frontend): prettier 全仓格式化` |
| `build` | 构建系统 / 外部依赖 | `build(deps): 升级 fastapi 至 0.115` |
| `ci` | CI 配置 | `ci(github): 新增 mobile e2e workflow` |
| `security` | 安全相关 | `security(auth): refresh token 切 HttpOnly Cookie` |
| `revert` | 回滚 | `revert(persona): 回滚 deep-research-v2，性能回退严重` |

## 3. Scope（推荐）

`<type>(<scope>)` 中 scope 描述影响域：

- **后端**：`auth` `persona` `chat` `rag` `harness` `payment` `esign` `im`
- **前端**：`chat` `admin` `pro` `editor` `a2ui` `design`
- **端**：`desktop` `mobile` `mini-program` `uni-mobile`
- **基础设施**：`docker` `nginx` `monitoring` `deps`
- **跨域**：`repo` `docs` `ci` `release`

## 4. Description（必填）

- **中文为主**，技术术语用英文
- **现在时祈使句**：`新增...` `修复...`，不是 `已经新增了...`
- **首字母小写**（中文不适用），**末尾不加句号**
- **长度 ≤ 72 字符**

## 5. Body（可选）

- 解释 **WHY**（为什么改），而不是 WHAT（改了什么 —— diff 已经说了）
- 与 description 之间空一行
- 每行 ≤ 100 字符

## 6. Footer（可选）

| 用途 | 格式 |
|---|---|
| 关联 issue | `Closes #123` 或 `Refs #456` |
| 关联 ADR | `ADR: 007` |
| 共同作者 | `Co-Authored-By: Name <email>` |
| Breaking change | `BREAKING CHANGE: <说明>` |

## 7. 完整示例

```
feat(persona): 新增市场研究员 DeepResearch 迭代算法

引入 5 步迭代检索-提炼-验证流程，替换原单步 RAG：
- 减少幻觉率从 18% 降至 6%
- 支持自动补充多源交叉验证
- 单次研究耗时从 12s 增至 25s（可接受）

性能对比详见 docs/v3/p7-baseline.md。

Closes #142
ADR: 003
Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

## 8. 反面教材

| ❌ 反例 | 问题 | ✅ 正例 |
|---|---|---|
| `更新` | 无 type、无 scope、无信息 | `fix(chat): 修复多轮对话上下文丢失` |
| `修复bug` | 同上 | `fix(auth): 修复 refresh token cookie SameSite 配置` |
| `Add new feature` | type 不规范 | `feat(rag): add multi-source citation tracking` |
| `WIP` | 不应出现在 main / integration | `wip(feature): xxx`（仅限 feature 分支临时） |
| `feat: 修复 bug` | type 与内容矛盾 | `fix(...)` |
| `feat: 一次性新增 12 个 persona + 41 个 API + 28 个测试` | 应拆分多个 commit | 按域分多个 commit |

## 9. 工具支持

推荐配置：

```bash
# 安装 commitlint（可选）
npm install -g @commitlint/cli @commitlint/config-conventional

# pre-commit hook 验证
cat > .git/hooks/commit-msg << 'EOF'
#!/bin/sh
commitlint --edit "$1"
EOF
chmod +x .git/hooks/commit-msg
```

## 10. 历史 commit 治理

- 本项目历史存在大量 `更新` `修复 bug` 之类无信息 commit（git log 可见）
- **从今往后**全部按本规范执行
- 不强制改写历史（risk > benefit）
- CI 应配置 commitlint 拦截不规范新 commit
