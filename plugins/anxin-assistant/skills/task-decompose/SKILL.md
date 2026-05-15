---
name: task-decompose
description: 复杂任务拆解为 persona-skill DAG；产出可执行计划与并行/串行依赖图。
access-level: practice
data-classification: L2
jurisdiction: CN
required-scopes:
  - skill.anxin-assistant.task_decompose
tool-allowlist:
  - read_only
  - llm_call
lifecycle-stage: PUBLISHED
audit-level: medium
pii-handling: mask-before-llm
network-egress: deny
privileged: false
argument-hint: 见执行流程 §1，按对话提示提供输入
user-invocable: true
output-format: md
requires-research: false
requires-practice-profile: true
triggers:
  - 任务拆解
  - decompose
version: 1.0.0
---

# /anxin-assistant:task-decompose

复杂任务拆解为 persona-skill DAG；产出可执行计划与并行/串行依赖图。

> **执业画像依赖**：本 skill 在执行前会读取 [`plugins/anxin-assistant/CLAUDE.md`](../../CLAUDE.md) 中的术语、红线、升级阈值。**未跑过 [`/anxin-assistant:cold-start-interview`](../cold-start-interview/SKILL.md) 前禁用本 skill。**

## 执行流程

1. **输入校验** — 检查必备字段、附件格式、个人信息脱敏。
2. **调用底层能力** — 调用对应的 specialized agent (`backend/src/agents/specialized/`) 或 LLM 直接生成。
3. **应用执业画像** — 套用 `CLAUDE.md` 的术语、文风、升级阈值。
4. **草稿产出** — 渲染成 `md` 草稿，写入 `.claude/drafts/anxin-assistant/task-decompose-<ts>.md`。
5. **人工守门** — 默认 **不外发 / 不签发**；返回草稿 + 风险摘要 + Confirm 链接。

## 风险守门

- **Draft-only** — 本 skill 永远只产出草稿；签发 / 外发 / 上架 / 转账动作必须人工 confirm。
- **Source attribution** — 所有引用必附数据源（URL + 抓取时间戳 / 法规第 X 条）。
- **Jurisdiction transparency** — 涉及法域时显式声明；默认中国大陆；跨境强制人工复核。
- **No PII leak** — 个人身份号 / 银行卡 / 手机号在外发前自动脱敏。

## 后端实现链接

- Persona class: `backend/src/agents/personas/anxin_assistant.py`
- Skill registry: `backend/src/skills/registry.py` (entry `task-decompose`)
- 单元测试: `backend/tests/test_personas_anxin_assistant_task_decompose.py`

## 修改本 skill

直接编辑本文件；改完跑 `python3 scripts/claude-plugin-validate.py plugins/anxin-assistant` 校验。
