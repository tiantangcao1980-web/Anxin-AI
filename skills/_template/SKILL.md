---
name: <skill-id>                      # 短横线小写，例如 contract-review
description: <一句话能力描述>          # 进入 routing 用，要让 coordinator 一眼能判断该不该路由到这里
version: 0.1.0
type: agent | domain | utility        # agent=Agent 化身  domain=业务领域知识  utility=工具流程
owner: <team>                         # 负责的小组/人
triggers:                              # 命中任一即加载本 SKILL.md
  - <关键词或意图>
risk_level: low | medium | high       # 影响 policy_engine 默认放行/审批
data_classification: public | internal | confidential | top_secret
modes:                                 # 可在哪些三态模式下使用
  - local
  - hybrid
  - cloud
required_tools:                        # 需要的 tool_registry 工具，没注册则降级
  - <tool_id>
optional_references:                   # progressive disclosure：本 SKILL.md 不展开，按需读
  - reference.md
  - checklist.md
  - templates/
---

# <人类可读的技能名>

## 1. 用途（Purpose）

这个 skill 解决什么问题。**一句话**说清。
不写"本 skill 用于..."这种废话开头。直接说做什么。

## 2. 何时触发（When to use）

- 触发场景 1
- 触发场景 2

**何时不用**：
- 反例 1（防止误触发）
- 反例 2

## 3. SOP（Step-by-step）

1. **第一步**：做什么 → 期望产出
2. **第二步**：……
3. **第三步**：……

> 详细检查清单见 `checklist.md`（按需 read）。
> 模板文件在 `templates/`。
> 复杂可执行逻辑放 `scripts/`。

## 4. 输入 / 输出契约

**输入**：
```json
{
  "field": "..."
}
```

**输出**：
```json
{
  "summary": "...",
  "risk_level": "medium",
  "citations": [{"source": "...", "ref": "..."}],
  "next_actions": []
}
```

## 5. 失败处理

| 触发条件 | 应当怎样失败 |
|---------|-------------|
| 输入缺字段 | 拒绝 + 列出缺失字段 |
| 工具不可用 | 降级方案 |
| 校验未通过 | 返回未通过事件，由 `output_validator` 处理 |

## 6. 关联

- 上游：…
- 下游：…
- 相关 skill：…

---

> 编辑须知：本文件 ≤ 80 行，超出请把内容拆到 `reference.md`。
