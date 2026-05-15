---
name: email-outreach
description: 外呼邮件 / 短信生成：A/B 模板 + 个性化片段，遵守 CAN-SPAM / GDPR。
access-level: practice
data-classification: L2
jurisdiction: CN
required-scopes:
  - skill.lead-hunter.email_outreach
tool-allowlist:
  - read_only
  - network_egress
  - llm_call
lifecycle-stage: PUBLISHED
audit-level: medium
pii-handling: mask-before-llm
network-egress: allowlist
privileged: false
argument-hint: 见执行流程 §1，按对话提示提供输入
user-invocable: true
output-format: md
requires-research: false
requires-practice-profile: true
triggers:
  - 邮件触达
  - 外呼
  - email outreach
version: 1.0.0
---

# /lead-hunter:email-outreach

外呼邮件 / 短信生成：A/B 模板 + 个性化片段，遵守 CAN-SPAM / GDPR。

> **执业画像依赖**：本 skill 在执行前会读取 [`plugins/lead-hunter/CLAUDE.md`](../../CLAUDE.md) 中的术语、红线、升级阈值。**未跑过 [`/lead-hunter:cold-start-interview`](../cold-start-interview/SKILL.md) 前禁用本 skill。**

## 执行流程

1. **输入校验** — 检查必备字段、附件格式、个人信息脱敏。
2. **调用底层能力** — 调用对应的 specialized agent (`backend/src/agents/specialized/`) 或 LLM 直接生成。
3. **应用执业画像** — 套用 `CLAUDE.md` 的术语、文风、升级阈值。
4. **草稿产出** — 渲染成 `md` 草稿，写入 `.claude/drafts/lead-hunter/email-outreach-<ts>.md`。
5. **人工守门** — 默认 **不外发 / 不签发**；返回草稿 + 风险摘要 + Confirm 链接。

## 风险守门

- **Draft-only** — 本 skill 永远只产出草稿；签发 / 外发 / 上架 / 转账动作必须人工 confirm。
- **Source attribution** — 所有引用必附数据源（URL + 抓取时间戳 / 法规第 X 条）。
- **Jurisdiction transparency** — 涉及法域时显式声明；默认中国大陆；跨境强制人工复核。
- **No PII leak** — 个人身份号 / 银行卡 / 手机号在外发前自动脱敏。

## 后端实现链接

- Persona class: `backend/src/agents/personas/lead_hunter.py`
- Skill registry: `backend/src/skills/registry.py` (entry `email-outreach`)
- 单元测试: `backend/tests/test_personas_lead_hunter_email_outreach.py`

## 修改本 skill

直接编辑本文件；改完跑 `python3 scripts/claude-plugin-validate.py plugins/lead-hunter` 校验。
