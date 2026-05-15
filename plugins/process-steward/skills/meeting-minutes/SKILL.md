---
name: meeting-minutes
description: 会议纪要：音视频转写 → 结构化纪要 → 行动项分派到飞书待办。
access-level: practice
data-classification: L2
jurisdiction: CN
required-scopes:
  - skill.process-steward.meeting_minutes
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
  - 会议纪要
  - 会议记录
  - meeting minutes
version: 1.0.0
---

# /process-steward:meeting-minutes

会议纪要：音视频转写 → 结构化纪要 → 行动项分派到飞书待办。

> **执业画像依赖**：本 skill 在执行前会读取 [`plugins/process-steward/CLAUDE.md`](../../CLAUDE.md) 中的术语、红线、升级阈值。**未跑过 [`/process-steward:cold-start-interview`](../cold-start-interview/SKILL.md) 前禁用本 skill。**

## 执行流程

1. **输入校验** — 检查必备字段、附件格式、个人信息脱敏。
2. **调用底层能力** — 调用对应的 specialized agent (`backend/src/agents/specialized/`) 或 LLM 直接生成。
3. **应用执业画像** — 套用 `CLAUDE.md` 的术语、文风、升级阈值。
4. **草稿产出** — 渲染成 `md` 草稿，写入 `.claude/drafts/process-steward/meeting-minutes-<ts>.md`。
5. **人工守门** — 默认 **不外发 / 不签发**；返回草稿 + 风险摘要 + Confirm 链接。

## 风险守门

- **Draft-only** — 本 skill 永远只产出草稿；签发 / 外发 / 上架 / 转账动作必须人工 confirm。
- **Source attribution** — 所有引用必附数据源（URL + 抓取时间戳 / 法规第 X 条）。
- **Jurisdiction transparency** — 涉及法域时显式声明；默认中国大陆；跨境强制人工复核。
- **No PII leak** — 个人身份号 / 银行卡 / 手机号在外发前自动脱敏。

## 后端实现链接

- Persona class: `backend/src/agents/personas/process_steward.py`
- Skill registry: `backend/src/skills/registry.py` (entry `meeting-minutes`)
- 单元测试: `backend/tests/test_personas_process_steward_meeting_minutes.py`

## 修改本 skill

直接编辑本文件；改完跑 `python3 scripts/claude-plugin-validate.py plugins/process-steward` 校验。
