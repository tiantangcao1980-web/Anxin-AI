# C2 进度（5 个核心 Agent → Skill 拆分）

> 时间：2026-05-05
> 阶段：C2 - Phase B（试点 5 个最高频 agent）

---

## 已完成（本轮 C2 第 1 步）

| Agent | SKILL.md | reference.md | checklist.md | templates/ | 状态 |
|-------|:---:|:---:|:---:|:---:|:---:|
| `legal-advisor` | ✅ | ✅ | ✅ | dir 已建 | 🟢 完整示范 |
| `legal-researcher` | ✅ 骨架 | ⏳ | ⏳ | — | 🟡 待 PR 展开 |
| `contract-reviewer` | ✅ 骨架 | ⏳ | ⏳ | — | 🟡 待 PR 展开 |
| `due-diligence` | ✅ 骨架 | ⏳ | ⏳ | — | 🟡 待 PR 展开 |
| `risk-assessor` | ✅ 骨架 | ⏳ | ⏳ | — | 🟡 待 PR 展开 |

**关键约束**：本轮**不**改 `prompt_assembler` 加载逻辑——继续读旧的 `backend/src/prompts/agents/*.txt`。
原因：必须有 E1 baseline 评测后，才敢真正切到 SKILL.md，避免回归。

---

## 下一轮 C2 PR

### PR-1：4 个骨架展开为完整 SKILL（依赖 E1 baseline）
- 把 `legal_researcher.txt` (33L) / `due_diligence.txt` (46L) / `risk_assessor.txt` (57L) / `contract_reviewer.txt` (214L) 内容按 `legal-advisor` 示范结构拆到 reference + checklist + templates
- 控制 SKILL.md ≤ 80 行，详情进 reference

### PR-2：`prompt_assembler` 接入 progressive disclosure
- 加载顺序：`AGENTS.md` + 命中 trigger 的 SKILL.md
- 命中关键词 → agent 主动 read reference 节
- 兜底：SKILL.md 缺失时回退旧 prompt
- E1 评测：每个 agent 5-10 个金标准用例，新旧 prompt 各跑一遍对比

### PR-3：剩余 17 个 agent + 4 个 coordinator prompt 全量迁移
- 每批 5 个，每批跑 E1 baseline，确认不退化才合并

### PR-4：把 `skills/legal/` `skills/finance/` 的"领域知识"重新归类
- `skills/legal/contract-review/` → `skills/domains/legal/contract-review/`
- 与 `skills/agents/contract-reviewer/` 区分清楚

---

## 验收门槛

C2 完成 = 以下都满足：
- ✅ AGENTS.md（C1 已交付）+ skills/_template（C1 已交付）+ docs/context-architecture.md（C1 已交付）
- ✅ 5 个核心 agent 至少有 SKILL.md（本轮 ✅）
- ⏳ 5 个核心 agent reference + checklist 完整
- ⏳ prompt_assembler 接入 progressive disclosure（保留旧路径作回退）
- ⏳ E1 评测：5 个核心 agent 新旧 prompt 对比无退化（≤ 5% 偏差）
- ⏳ 全量 17 个剩余 agent 迁移
