---
name: company-dd
description: 公司 360° 尽职调查：工商 / 司法 / 失信 / 知识产权 / 舆情五维体检。
access-level: practice
data-classification: L3
jurisdiction: CN
required-scopes:
  - skill.dd-expert.company_dd
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
output-format: xlsx
requires-research: true
requires-practice-profile: true
triggers:
  - 尽职调查
  - 尽调
  - company dd
  - due diligence
version: 1.0.0
---

# /dd-expert:company-dd

公司 360° 尽职调查：工商 / 司法 / 失信 / 知识产权 / 舆情五维体检。

> **执业画像依赖**：本 skill 在执行前会读取 [`plugins/dd-expert/CLAUDE.md`](../../CLAUDE.md) 中的术语、红线、升级阈值。**未跑过 [`/dd-expert:cold-start-interview`](../cold-start-interview/SKILL.md) 前禁用本 skill。**

## 执行流程

1. **输入校验** — 检查必备字段、附件格式、个人信息脱敏。
2. **调用底层能力**
     - 复用 [`skills/legal/due-diligence/SKILL.md`](../../../../skills/legal/due-diligence/SKILL.md) 中定义的底层算法 / 规则集 / Prompt 模板。
3. **应用执业画像** — 套用 `CLAUDE.md` 的术语、文风、升级阈值。
4. **草稿产出** — 渲染成 `xlsx` 草稿，写入 `.claude/drafts/dd-expert/company-dd-<ts>.xlsx`。
5. **人工守门** — 默认 **不外发 / 不签发**；返回草稿 + 风险摘要 + Confirm 链接。

## 风险守门

- **Draft-only** — 本 skill 永远只产出草稿；签发 / 外发 / 上架 / 转账动作必须人工 confirm。
- **Source attribution** — 所有引用必附数据源（URL + 抓取时间戳 / 法规第 X 条）。
- **Jurisdiction transparency** — 涉及法域时显式声明；默认中国大陆；跨境强制人工复核。
- **No PII leak** — 个人身份号 / 银行卡 / 手机号在外发前自动脱敏。

## 后端实现链接

- Persona class: `backend/src/agents/personas/dd_expert.py`
- Skill registry: `backend/src/skills/registry.py` (entry `company-dd`)
- 单元测试: `backend/tests/test_personas_dd_expert_company_dd.py`

## 修改本 skill

直接编辑本文件；改完跑 `python3 scripts/claude-plugin-validate.py plugins/dd-expert` 校验。
