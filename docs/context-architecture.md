# Context 三层架构（C1）

> 时间：2026-05-05
> 关联：[`AGENTS.md`](../AGENTS.md) · [`skills/_template/SKILL.md`](../skills/_template/SKILL.md) · [`memory/`](../../../.claude/projects/-Users-pengchengkeji-Documents-GitHub-Anxin-Smart-Legal-Services/memory/)
> 决策原则：**能写进 Context 的不要训进模型；能写成 Skill 的不要堆在 prompt**

---

## 1. 现状（C1 启动时）

| 现有资产 | 位置 | 数量 | 形态 | 问题 |
|---------|------|-----|------|------|
| Agent prompt | `backend/src/prompts/agents/` | 22 个 `.txt` | 单文件、~50 行 | 工具定义/SOP/检查清单全在 prompt，难维护 |
| Coordinator prompt | `backend/src/prompts/coordinator/` | 4 个 | 同上 | 与 AGENTS.md 红线无对齐机制 |
| 业务领域 skill | `skills/legal/`、`skills/finance/` | 8 个 | frontmatter + Markdown | 与 agent prompt 是两套体系，互不知晓 |
| 项目级 memory | `~/.claude/projects/.../memory/` | ~20 条 | hierarchical-memory | 仓库内不可见，新 contributor 无感 |
| 设计/部署/审计文档 | `docs/` | 30+ 篇 | Markdown | 没有"哪个 agent 应该读哪些"的索引 |

**核心矛盾**：22 个 agent + 8 个 skill + 30+ 文档 = **没有单一真相源**。

---

## 2. 三层标准（本 C1 确立）

```
┌─────────────────────────────────────────────────────┐
│  Layer 1 · 永远加载（Constitution Layer）             │
│   AGENTS.md   — 红线、工作原则、路由表、反 slop       │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│  Layer 2 · 命中触发（Skills Layer）                   │
│   skills/<domain>/<skill>/                          │
│     SKILL.md      ≤80 行  摘要 + 触发 + 入口         │
│     reference.md  详情，progressive disclosure       │
│     checklist.md  检查清单                          │
│     templates/    可复用模板                        │
│     scripts/      可执行脚本                        │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│  Layer 3 · 按需检索（Memory Layer）                   │
│   memory/                                           │
│     user_*.md       用户偏好                        │
│     project_*.md    项目状态                        │
│     feedback_*.md   用户反馈与纠偏                  │
│     reference_*.md  外部资源指针                    │
│     bugfix_*.md     已修 bug 经验（防回归）          │
└─────────────────────────────────────────────────────┘
```

### 加载顺序与 token 预算

| Layer | 加载时机 | 期望体积 | 命中机制 |
|-------|---------|---------|---------|
| AGENTS.md | 每次请求 | ≤ 200 行 / ~3K token | 永远 |
| SKILL.md | 命中 trigger | 每个 ≤ 80 行 / ~1.2K token | trigger keyword + intent classifier |
| reference / checklist | agent 主动 read | 不限 | progressive disclosure |
| memory | 每次请求查询 | top-N 命中 | 关键词检索 + recency |

总体目标：**典型对话首包 ≤ 8K 上下文 token**（Layer 1 + 1-2 个 SKILL.md）。

---

## 3. 字段约定（SKILL.md frontmatter）

| 字段 | 必填 | 用途 |
|------|:---:|------|
| `name` | ✅ | 唯一 ID，匹配文件夹名 |
| `description` | ✅ | 一句话给 coordinator 路由用 |
| `version` | ✅ | semver |
| `type` | ✅ | `agent` / `domain` / `utility` |
| `owner` | ✅ | 维护团队 |
| `triggers` | ✅ | 命中关键词 |
| `risk_level` | ✅ | `low / medium / high` → policy_engine 默认放行/审批 |
| `data_classification` | ✅ | `public / internal / confidential / top_secret` → 三态模式可用性 |
| `modes` | ✅ | `local / hybrid / cloud` 子集 |
| `required_tools` | ⭕ | 关联 tool_registry，缺失则降级 |
| `optional_references` | ⭕ | progressive disclosure 文件清单 |

> 字段标准与 `harness/policy_engine` 和 `harness/capability_negotiator` 保持一致——这样 H1 强制接入时不需要再迁移一次。

---

## 4. 迁移路径（不是本任务，是 C2 的输入）

### Phase A · 已就绪（C1 完成）
- ✅ `AGENTS.md` 项目级宪章
- ✅ `skills/_template/` 标准模板
- ✅ 本架构文档

### Phase B · 试点（C2 第 1 批，2 周内）
迁移**最高频的 5 个 agent**（占 chat 调用量 ~70%）：
- `legal_advisor` → `skills/agents/legal-advisor/`
- `legal_researcher` → `skills/agents/legal-researcher/`
- `contract_reviewer` → `skills/agents/contract-reviewer/`
- `due_diligence` → `skills/agents/due-diligence/`
- `risk_assessor` → `skills/agents/risk-assessor/`

每个迁移必须：
1. 在 `skills/agents/<id>/SKILL.md` 写入 ≤ 80 行的摘要 + 触发 + SOP
2. 把当前 prompt 的"详细 SOP / 工具定义 / 检查清单"拆到 `reference.md` / `checklist.md` / `templates/`
3. 保留旧 `backend/src/prompts/agents/<id>.txt` 一个 release，作为回退
4. `prompt_assembler` 按 trigger 加载 SKILL.md，命中关键词再 read reference
5. 跑一次 E1 baseline 评测，确保不退化

### Phase C · 全量（C2 第 2 批，4 周内）
剩余 17 个 agent + 4 个 coordinator prompt 全部迁移完毕。

### Phase D · 与现有 skills/ 的合并
现有 `skills/legal/` `skills/finance/` 是**领域知识**，不是 agent 化身：
- 重命名：`skills/legal/contract-review/` → `skills/domains/legal/contract-review/`
- 新增：`skills/agents/<agent_id>/` 用于 agent 化身
- 新增：`skills/utilities/<util_id>/` 用于跨 agent 公共流程

---

## 5. 与已有体系的对齐

| 关注点 | 对齐对象 | 怎么对齐 |
|-------|---------|---------|
| 红线 | `CLAUDE.md` 全局规则 | AGENTS.md §2 红线引用 CLAUDE.md 的安全条款 |
| 设计 | `DESIGN.md` | AGENTS.md 不涉及视觉，仅引用关键交互原则 |
| Harness | `backend/src/harness/policy_engine` | SKILL.md 的 `risk_level` / `data_classification` 字段是 policy 输入 |
| 三态 | `frontend/.../mode/ModeGate` | SKILL.md 的 `modes` 字段是 ModeGate 的真相源（H1 后） |
| Memory | `hierarchical-memory` | AGENTS.md §4 写明检索时机；不复制内容到仓库 |

---

## 6. 反模式（明确禁止）

- ❌ 把"红线"复制到每个 SKILL.md（应只在 AGENTS.md 一处）
- ❌ SKILL.md > 80 行（用 reference.md 拆）
- ❌ 在 prompt 里硬编码工具定义（应走 tool_registry）
- ❌ 在 SKILL.md 里写历史 changelog（git log 已经有了）
- ❌ 创建 `skills/<某个 agent 名>/` 但不写 frontmatter（破坏自动加载）

---

## 7. 验收门槛

C1 完成 = 以下三个文件存在且通过 lint：
- ✅ `AGENTS.md`（≤ 200 行）
- ✅ `skills/_template/SKILL.md`（≤ 80 行 SKILL.md 主体）
- ✅ `docs/context-architecture.md`（本文件）

C2 完成 = 5 个核心 agent 迁移到新结构 + E1 baseline 不退化。

---

## 8. 后续

- **C2** 启动时输入：本文件 §4 Phase B 的 5 个 agent 列表
- **H1** 启动时输入：本文件 §3 frontmatter 字段（policy_engine 直接消费）
- **E1** 启动时输入：本文件 §4 Phase B 的 5 个 agent → 各 5 个金标准用例
