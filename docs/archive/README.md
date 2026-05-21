# 文档归档（已清空）

> 日期：2026-05-13
> 状态：已彻底清空。所有历史档案已从工作树移除。

## 历史档案的去向

为遵循"彻底清理过时文件，避免被错误引用"原则，**2026-05-13** 清理了以下历史档案：

| 原目录 | 内容 | 处理 |
|---|---|---|
| `legacy-root-docs/` | 27 篇 2026-03 / 2026-04 旧规划/审计/方案 | **已 git rm** |
| `superpowers-implemented/` | 11 篇已实施的内部规划 | **已 git rm** |
| `wiki-snapshot-2026-05-06/` | 9 个 Codex 旧 wiki 文件 | **已 git rm** |
| `docs/references/legacy/` | 7 篇早期 README / DEPLOY / ROADMAP | **已 git rm** |

**总计 54 个文件**已从工作树移除。

## 2026-05-22 归档批次

`2026-05-22-pre-blueprint/` 归档了**蓝图升级前的过时大文档**（不再作为权威）：

| 原路径 | 文件 | 取代者 |
|---|---|---|
| `/PROJECT_STATUS.md` | 73KB 状态快照 | `docs/audit/summary.md` + `CHANGELOG.md` |
| `/PRODUCT_ROADMAP.md` | 多端产品路线（旧） | `docs/plans/2026-05-22-product-blueprint.md` |
| `/ROADMAP.md` | 工程路线（旧） | `docs/v3/roadmap.md` |
| `docs/plans/2026-05-09-workstation-admin-ia-boundary.md` | 旧 IA 边界 | `docs/plans/2026-05-22-product-blueprint.md` §3 |

依据：[docs/plans/2026-05-22-product-blueprint.md §5.1](../plans/2026-05-22-product-blueprint.md)。

## 如何追溯历史

所有历史文档**永久保留在 git history 中**，需要追溯时：

```bash
# 查看历史快照（清理前的最后一个 commit）
git show 07632ab9:docs/archive/legacy-root-docs/2026-04-18-ui-audit-and-optimization-plan.md

# 列出当时存在的所有历史档案
git ls-tree -r 07632ab9 -- docs/archive

# 恢复单个文件到当前（不推荐，除非有明确理由）
git checkout 07632ab9 -- docs/archive/legacy-root-docs/<filename>
```

## 当前权威入口

不再使用任何 archive 内容作为开发依据。当前权威：

- **[../00-project-execution-map.md](../00-project-execution-map.md)** — 当前权威导航总入口
- **[../strategy/](../strategy/)** — 产品策略
- **[../openspec/](../openspec/)** — 平台合同 + 商业交付 + 测试规范
- **[../v3/](../v3/)** — V3 智能助手实施
- **[../audit/](../audit/)** — 当前执行计划
- **[../adr/](../adr/)** — 架构决策记录
- **[../standards/](../standards/)** — 开发规范

## 规则

- ❌ **禁止** 将本目录或 git history 中的归档内容作为新开发的依据
- ❌ **禁止** 引用已删除文件的旧路径作为参考
- ✅ 历史决策的"当时背景"可通过 git show 追溯
- ✅ 已实施方案的"成果"看代码 + 当前文档，不看旧规划

## 维护

如未来需要归档新文档：

1. 文档头部加 `> ⚠️ 已弃用：<日期>，被 [新文档](路径) 取代`
2. `git mv` 到本目录（按时间命名子目录）
3. 全仓 grep 引用并更新指针
4. 更新 [../../CHANGELOG.md](../../CHANGELOG.md)

参考：[ADR-002](../adr/002-documentation-and-naming-standards.md)
