# 文档规范

> 强制规范。所有新建/修改 markdown 文档必须遵守。

## 1. 文档分层

| 层级 | 位置 | 角色 | 写谁看 |
|---|---|---|---|
| L1 入口 | `README.md`（仓库根） | 30 秒了解项目 | 任何人 |
| L1 导航 | `docs/00-project-execution-map.md` | 当前权威导航总入口 | 所有 contributor |
| L2 规范 | `docs/standards/*` | 如何工作（HOW） | 所有 contributor |
| L2 规范 | `docs/openspec/*` | 交付什么（DELIVERABLE） | 产品 + 工程 + 验收 |
| L2 战略 | `docs/strategy/*` | 长期定位与需求 | 产品 + 高层 |
| L3 实施 | `docs/v3/*` | V3 智能助手实施细节 | 工程 |
| L3 实施 | `docs/architecture/*` `docs/desktop/*` `docs/mobile/*` `docs/design/*` | 工程领域专题 | 对应领域工程师 |
| L3 执行 | `docs/audit/*` `docs/release/*` `docs/plans/*` | 当前任务、审计、发布证据 | 执行团队 |
| L4 历史 | `docs/archive/*` | 历史决策与已实施方案，不作当前事实来源 | 追溯 |
| L4 参考 | `docs/references/*` | 外部资料与设计参考 | 设计 + 工程 |

## 2. 文档头部模板

**所有 docs/ 内 markdown 文档必须以下面 5 行开头**（最少满足前 3 行）：

```markdown
# <标题>

> 日期：YYYY-MM-DD
> 状态：草稿 | 规划中 | 实施中 | 已完成 | 已归档
> 适用范围：<谁、什么场景需要看>
> 权威级别：⭐⭐⭐ 执行权威 | ⭐⭐ 工程参考 | ⭐ 历史快照
```

## 3. 标题层级

- `#` H1：仅文档标题，**每个文件唯一一个**
- `##` H2：主要章节
- `###` H3：子章节
- 不使用 H4 以下（如必须用，考虑拆文档）

## 4. 代码块

强制带语言标识：

```markdown
✅ ```bash
   docker-compose up -d
   ```

❌ ```
   docker-compose up -d
   ```
```

## 5. 链接

| 场景 | 写法 |
|---|---|
| 仓库内 markdown 互链 | 相对路径：`[名](../audit/plan.md)` |
| 文件引用 | 带行号：`[chat.py:123](../../backend/src/api/routes/chat.py#L123)` |
| 外部链接 | 完整 URL，避免短链 |
| 图片 | 相对路径，置于 `docs/<topic>/assets/` 内 |

## 6. 表格规范

- 表头明确，避免空表头
- 数字列右对齐
- 状态用 emoji（✅ ⏳ ❌ 🟡 🔴 🟢）+ 文字双写

## 7. 中英文混排

- **中文优先**，技术术语用英文（不翻译）：`pytest`、`worktree`、`provider`
- 中英之间无空格（除非术语保留原形）：`完成 P0` 而非 `完成 P 0`
- 数字前后建议留 1 空格：`耗时 30 分钟`

## 8. 弃用文档处理

文档过时或被覆盖：

1. 先在文档头部加：
   ```markdown
   > ⚠️ 已弃用：<日期>，被 [新文档](../path/to/new.md) 取代
   ```
2. PR 中 `git mv` 到 `docs/archive/legacy-root-docs/`
3. 全仓 grep 引用，更新所有指针
4. 更新 [docs/00-project-execution-map.md](../00-project-execution-map.md)

## 9. 文档新建前检查

新建 markdown 前，按顺序确认：

- [ ] 是否已有同类文档可以补充而非新建？
- [ ] 文件名符合 [naming-convention.md](./naming-convention.md)？
- [ ] 位置正确（按文档分层表）？
- [ ] 头部 5 行模板已填？
- [ ] 是否需要在 [docs/00-project-execution-map.md](../00-project-execution-map.md) 加入索引？

## 10. 文档 5 个最常见反模式

| 反模式 | 改进 |
|---|---|
| ❌ 一份文档同时是规划+实施+回顾 | 拆为三个：plan / spec / retrospective |
| ❌ 日期 + 主题混名（`2026-04-15-new-feature.md`） | 主题命名 `<feature>.md`，日期在头部 |
| ❌ 内容 1000 行的"大杂烩" | 按主题拆分，每篇 ≤ 500 行 |
| ❌ 无更新日期，无法判断时效 | 强制头部带日期 + 状态 |
| ❌ 用 markdown 模拟 PPT（大量 emoji+表情） | 信息密度优先于视觉装饰 |
