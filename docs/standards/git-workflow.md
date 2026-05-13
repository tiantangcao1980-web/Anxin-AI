# Git 工作流规范

> 强制规范。覆盖分支策略、PR 流程、worktree 治理、合并规则。

## 1. 分支模型

```
main                                    # 生产分支，永远可发布
 └── integration/v3-merge-20260512      # 集成分支，当前 V3 主线
      ├── feat/<topic>                  # 功能分支（短命）
      ├── fix/<topic>                   # 修复分支（短命）
      ├── refactor/<topic>              # 重构分支
      └── docs/<topic>                  # 文档分支
```

- **main** 永远保持可部署
- **integration/v3-merge-20260512** 当前承载 V3 智能助手合并工作
- 所有功能分支从 **integration/v3-merge-20260512** 切，PR 合回 integration
- 整合分支稳定后通过 release 流程合入 main

## 2. 分支命名

严格按 [naming-convention.md §5](./naming-convention.md#5-git-分支) 执行：

| 类型 | 格式 |
|---|---|
| 功能 | `feat/<short-desc>` |
| 修复 | `fix/<short-desc>` |
| 重构 | `refactor/<short-desc>` |
| 文档 | `docs/<short-desc>` |
| 整合 | `integration/<topic-YYYYMMDD>` |
| 发布 | `release/vX.Y.Z` |

**禁止**：
- 自动生成临时名（`claude/peaceful-xxx` 长期保留）
- 私人名前缀（`pengcheng/xxx`）
- 含空格、中文、大写、下划线

## 3. Pull Request 规范

### PR 标题

`<type>(<scope>): <description>` —— 与 commit 规范一致

### PR 描述模板

```markdown
## 改动概述
一句话说明做了什么、为什么做。

## 改动范围
- [ ] 后端：…
- [ ] 前端：…
- [ ] 桌面：…
- [ ] 移动：…
- [ ] 文档：…

## 测试
- [ ] 单元测试通过：`pytest`、`vitest`、`cargo test`
- [ ] 集成测试通过
- [ ] 手动验证步骤：…

## 审查清单
对照 [review-checklist.md](./review-checklist.md) 自查通过

## 关联
- Closes #<issue>
- 相关 ADR：…
- 相关文档：…
```

### PR 大小

- **小**：< 200 行变更（鼓励）
- **中**：200-1000 行（正常）
- **大**：> 1000 行（必须在描述说明为什么不能拆）

## 4. Worktree 治理（关键！）

本项目历史上出现过 80+ 临时 worktree 失控的情况，必须严格治理：

| 规则 | 强制性 |
|---|---|
| worktree 使用完毕必须 `git worktree remove` | 强制 |
| 同名分支与 worktree 一起删 | 强制 |
| 1 周内未活动的 worktree 必须清理 | 强制 |
| 不允许在 `.claude/worktrees/` 长期保留 agent 临时分支 | 强制 |
| 每月跑 `git worktree prune` + `git worktree list` 复核 | 推荐 |

清理脚本：

```bash
# 一键清理已合并的 worktree
git worktree list | awk '$3 ~ /^\[.*\]/ {print $1}' | while read d; do
  branch=$(git -C "$d" branch --show-current)
  if git branch --merged integration/v3-merge-20260512 | grep -q "^[* ] $branch$"; then
    git worktree remove --force "$d"
    git branch -D "$branch"
  fi
done
```

## 5. 合并策略

| 场景 | 策略 |
|---|---|
| feat/fix → integration | **Squash merge**（保持 integration 历史干净） |
| integration → main | **Merge commit**（保留集成历史） |
| release → main + tag | **Merge commit + tag** |
| hotfix → main | **Cherry-pick** 到 integration |

## 6. 禁止行为

| ❌ 禁止 | 原因 |
|---|---|
| `git push --force` 到 main / integration | 破坏共享历史 |
| `git commit --amend` 已 push 的提交 | 同上 |
| 跳过 hook（`--no-verify`） | CI 设防是有原因的 |
| 提交 `.env` / secrets / `node_modules` | 安全 + 体积 |
| 直接 push 到 main（必须走 PR） | 评审是质量门 |
| 命名违规分支 | 见上 |

## 7. 远程仓库

| Remote | URL | 用途 |
|---|---|---|
| `origin` | `github.com/tiantangcao1980-web/Anxin-Smart-Legal-Services.git` | 主仓 |
| `v3` | `github.com/tiantangcao1980-web/Anxin-Smart-Assistant.git` | V3 独立仓（已合并完毕） |

## 8. Commit 频率

- **小步提交**：每个逻辑改动一个 commit
- **WIP 允许**：标 `wip:` 前缀，最终 squash
- **不允许**：一个 commit 包含数十个无关改动

## 9. 大文件治理

- 仓库**禁止**入库 > 10 MB 的二进制
- 设计稿、参考资料等大资源用外部存储 + 链接
- 历史误入大文件用 `git filter-repo` 清理（先备份）

## 10. 故障恢复

| 场景 | 命令 |
|---|---|
| 误删本地分支 | `git reflog` 找回 commit hash → `git branch <name> <hash>` |
| 误合并 | `git revert -m 1 <merge-commit>` |
| 误强推 | 找 remote 历史 + 申请 unprotect |
| 想看任意分支的某文件 | `git show <branch>:<path>` |
