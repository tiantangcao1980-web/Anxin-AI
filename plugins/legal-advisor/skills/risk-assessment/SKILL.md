---
name: risk-assessment
description: 针对具体业务场景做合规风险评估，输出风险矩阵 + 缓解建议。
access-level: practice
data-classification: L3
jurisdiction: CN
required-scopes:
  - skill.legal-advisor.risk_assessment
  - data.legal.read
tool-allowlist:
  - read_only
  - llm_call
lifecycle-stage: PUBLISHED
audit-level: high
pii-handling: mask-before-llm
network-egress: deny
privileged: false
argument-hint: 见执行流程 §1，按对话提示提供输入
user-invocable: true
output-format: md
requires-research: false
requires-practice-profile: true
triggers:
  - 风险评估
  - 合规风险
  - 风险矩阵
version: 1.0.0
---

# /legal-advisor:risk-assessment

针对具体业务场景做合规风险评估，输出风险矩阵 + 缓解建议。

> **执业画像依赖**：本 skill 在执行前会读取 [`plugins/legal-advisor/CLAUDE.md`](../../CLAUDE.md) 中的术语、红线、升级阈值。**未跑过 [`/legal-advisor:cold-start-interview`](../cold-start-interview/SKILL.md) 前禁用本 skill。**

## 执行流程

1. **输入校验** — 检查必备字段、附件格式、个人信息脱敏。
2. **调用底层能力** — 调用对应的 specialized agent (`backend/src/agents/specialized/`) 或 LLM 直接生成。
3. **应用执业画像** — 套用 `CLAUDE.md` 的术语、文风、升级阈值。
4. **草稿产出** — 渲染成 `md` 草稿，写入 `.claude/drafts/legal-advisor/risk-assessment-<ts>.md`。
5. **人工守门** — 默认 **不外发 / 不签发**；返回草稿 + 风险摘要 + Confirm 链接。

## 风险守门

- **Draft-only** — 本 skill 永远只产出草稿；签发 / 外发 / 上架 / 转账动作必须人工 confirm。
- **Source attribution** — 所有引用必附数据源（URL + 抓取时间戳 / 法规第 X 条）。
- **Jurisdiction transparency** — 涉及法域时显式声明；默认中国大陆；跨境强制人工复核。
- **No PII leak** — 个人身份号 / 银行卡 / 手机号在外发前自动脱敏。

## 后端实现链接

- Persona class: `backend/src/agents/personas/legal_advisor.py`
- Skill registry: `backend/src/skills/registry.py` (entry `risk-assessment`)
- 单元测试: `backend/tests/test_personas_legal_advisor_risk_assessment.py`

## 修改本 skill

直接编辑本文件；改完跑 `python3 scripts/claude-plugin-validate.py plugins/legal-advisor` 校验。
