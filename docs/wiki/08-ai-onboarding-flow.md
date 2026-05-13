---
name: AI 智能体上手流程
description: 新 AI 接手项目的 5 步流程（不知从哪开始时读这里）
audience: AI agents · 第一次接手
last_updated: 2026-05-14
---

# 08 · AI 上手流程

> "我刚接手这个项目，第一件事做什么？" — 按本文 5 步走，3 分钟到位。

---

## Step 1 · 识别身份与作用域（30 秒）

**先读** [README.md](../../README.md) 顶部 + [wiki/01-project-snapshot](01-project-snapshot.md)。

回答（在心里）：
- ✅ 这是 "安心智能助手 / Anxin AI" — 中国中小制造企业的全链路 AI 助理
- ✅ 多端：桌面（Tauri）+ 移动（Expo）+ 小程序（Taro）+ Web（React）+ API（FastAPI）
- ✅ V3 P0-P7 已交付，P8-P13 进行中

---

## Step 2 · 同步当前进度（1 分钟）

**读** [wiki/03-current-state.md](03-current-state.md)。

回答：
- ✅ 现在到哪一步？
- ✅ 阻断项有哪些？
- ✅ 下一步顺序是什么？

⚠️ 这是 Wiki 中**最常更新**的文件，每次接手必读。

---

## Step 3 · 理解你将操作的领域（1 分钟）

按用户的任务类型，**只读相关 Spine + Standards**：

| 用户任务 | 必读 |
|---|---|
| 加 API 路由 | [02-quick-context §API](02-quick-context.md) + [docs/standards/api-design.md](../standards/api-design.md) + [docs/standards/backend-standard.md](../standards/backend-standard.md) |
| 加 / 改 Agent | [AGENTS.md](../../AGENTS.md) + [skills/_template/](../../skills/_template/) + [04-architecture-map §Harness](04-architecture-map.md) |
| 改前端 UI | [DESIGN.md](../../DESIGN.md) + [docs/standards/frontend-standard.md](../standards/frontend-standard.md) + 注意：图标只从 `@/lib/icons` 导入 |
| 改桌面（Tauri） | [docs/desktop/](../desktop/) + Tauri 2 文档 |
| 改数据库 | [docs/standards/database-standard.md](../standards/database-standard.md) + ⚠️ Alembic 双 head |
| 写测试 | [docs/standards/testing-standard.md](../standards/testing-standard.md) |
| 安全相关 | [docs/standards/security-standard.md](../standards/security-standard.md) + [SECURITY.md](../../SECURITY.md) |
| 改 Harness | [docs/audit/harness/README.md](../audit/harness/README.md) + [03-h1-followups](../audit/harness/03-h1-followups.md) |
| 文档 / 命名 | [docs/standards/documentation-standard.md](../standards/documentation-standard.md) + [docs/standards/naming-convention.md](../standards/naming-convention.md) |

⚠️ 别一次读完所有 Spine — 只读相关的那个。

---

## Step 4 · 检查陷阱（30 秒）

**扫一遍** [wiki/07-common-pitfalls.md](07-common-pitfalls.md) 的相关章节。

特别注意：
- **品牌**：新代码不要写"安心法务"
- **CAMEL-AI**：不要 import camel
- **图标**：前端只从 `@/lib/icons`
- **Alembic**：双 head 状态，加 migration 前先 merge head
- **Git**：commit type 英文 + 描述中文
- **测试**：变更需配套测试

---

## Step 5 · 干活 → 验证 → 提交（按需）

### 5.1 写代码

按 Step 3 的 standards 写。**写完先自查**：

```bash
# 后端
cd backend && uv run --no-sync ruff check src/
cd backend && uv run --no-sync pytest <相关测试>

# 前端
cd frontend && npm run lint
cd frontend && npm run build  # 含 tsc

# 桌面
cd desktop && cargo clippy
cd desktop && cargo test

# 移动
cd mobile && npm run typecheck && npm run test
```

### 5.2 提交

```bash
# 1. 看差异
git diff
git status

# 2. 密钥扫描
bash scripts/release-evidence-secret-scan.sh

# 3. 工作树清单
python3 scripts/release-worktree-inventory.py --json --fail-on-unknown

# 4. Commit（type 英文 + 描述中文）
git add <specific-files>  # 不要 git add -A
git commit -m "$(cat <<'EOF'
feat(域): 中文描述

详细说明...

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

### 5.3 关键节点 push

```bash
# 用户要求：阶段任务或关键任务前后做 push
git push origin <branch>
```

---

## 📌 速查卡（贴在心里）

```
┌────────────────────────────────────────────┐
│ 我接手了什么 → 01-project-snapshot          │
│ 现在到哪步 → 03-current-state               │
│ 文件在哪里 → 02-quick-context               │
│ 架构是什么 → 04-architecture-map           │
│ 不懂的词 → 05-domain-glossary              │
│ 为什么这样 → 06-decision-log                │
│ 别踩这些坑 → 07-common-pitfalls            │
│ 不知从哪开始 → 本文                         │
└────────────────────────────────────────────┘

权威长文（Spine）按需深入：
- 需求 → REQUIREMENTS.md
- 架构 → ARCHITECTURE.md
- 路线图 → ROADMAP.md
- 开发计划 → DEVELOPMENT_PLAN.md
- 发布门禁 → RELEASE_GATE.md
```

---

## 🎯 常见接手场景

### 场景 A：用户说"实现 X 功能"

```
1. 读 03-current-state 找 X 是否在 P 级路线图
2. 读对应 Spine 的需求章节
3. 读 04-architecture-map 找 X 应该放在哪层
4. 写代码（按 Step 3 选 standards）
5. 写测试（必须）
6. 自查 + commit + push
```

### 场景 B：用户说"修 X bug"

```
1. 复现 bug（必须，否则修错地方）
2. 查 06-decision-log 看相关决策
3. 查 git log 看 X 最近改动
4. 修 + 加回归测试
5. 自查 + commit + push
```

### 场景 C：用户说"清理 / 重构 X"

```
1. 先盘点 X 的范围（grep / 文件清单）
2. 设计目标结构（写下来）
3. 大变更前先 commit 一次（保存"重构前"状态）
4. 分阶段重构，每阶段一个 commit
5. 每阶段后跑测试
6. 完成后更新 Wiki + Spine 相关引用
```

### 场景 D：用户问"项目现在怎么样？"

```
直接答：
- 读 03-current-state 给数字
- 读 PROJECT_STATUS.md 给时间线
- 不要去翻 git log / 大堆文档（浪费 token）
```

### 场景 E：用户给一个未明确范围的任务（如本轮的"清理无关文档"）

```
1. 先做 inventory（盘点现状）
2. 提议方案 → 等用户确认（或在 Auto Mode 下直接做并明示）
3. 关键节点 commit + push
4. 验证 + 交接报告
```

---

## ⏱ 时间分配建议

| 阶段 | 占比 | 备注 |
|---|---|---|
| 上下文识别 | 5% | Step 1-2 |
| 任务理解 | 10% | 读相关 Spine |
| 编码 | 50% | 主体工作 |
| 测试 | 25% | 必须有 |
| 自查 + commit | 10% | 别省 |

⚠️ 如果"上下文识别"超过 15%，说明 Wiki 设计有问题，更新 Wiki 让下个 AI 更快。

---

## 🚨 不要做的事

- ❌ 不要一上来就读 docs/audit/ 89 个文件（归档了，按需查）
- ❌ 不要假设你看过项目（即使似曾相识，先读 Wiki）
- ❌ 不要在不读 06-decision-log 的情况下推翻已有架构决策
- ❌ 不要在 Auto Mode 下做"删除数据/分支" 类高破坏性操作（即使 Auto Mode）
- ❌ 不要省略测试或自查
- ❌ 不要在 commit 里堆砌 5 个不相关主题

---

## ✅ 接手清单（自查）

接手时勾一遍：

- [ ] 读了 [wiki/01-project-snapshot](01-project-snapshot.md)
- [ ] 读了 [wiki/03-current-state](03-current-state.md)
- [ ] 看了 [PROJECT_STATUS.md](../../PROJECT_STATUS.md) 最新 entry
- [ ] 知道当前在哪个 P 级
- [ ] 知道阻断项有哪些
- [ ] 知道本次任务属于哪个 Lane / 域
- [ ] 读了相关 standards
- [ ] 扫了相关 pitfalls
- [ ] 准备好了第一个 commit 的 message

✅ 全部勾上 → 开干。
