---
name: cold-start-interview
description: 首次使用 尽调专家 前必跑的执业画像访谈 — 学习你的团队规模 / 行业 / SOP / 风险偏好，并写入 plugins/dd-expert/CLAUDE.md。
access-level: practice
data-classification: L3
jurisdiction: CN
required-scopes:
  - skill.dd-expert.cold_start_interview
tool-allowlist:
  - read_only
  - read_write_local
  - llm_call
lifecycle-stage: PUBLISHED
audit-level: high
pii-handling: mask-before-llm
network-egress: deny
privileged: false
argument-hint: 直接调用，无需参数；会逐步对话
user-invocable: true
output-format: markdown
requires-research: false
requires-practice-profile: false
triggers:
  - 冷启动
  - 执业画像
  - cold start
  - dd-expert 初始化
version: 1.0.0
---

# 尽调专家 冷启动访谈

## 目标

为新接入的团队建立 **尽调专家** 专属执业画像（`plugins/dd-expert/CLAUDE.md`）。此后所有 skill 都会从该文件读取你的行业、口径、红线、术语，避免输出像通用 ChatGPT 一样空泛。

> **重要**：在没有跑过本访谈前，所有 `/dd-expert:*` 命令都会输出风险提示并尽量保守。这与 Anthropic 在 *Claude for Legal* 与 *Claude for Financial Services* 中的 cold-start 设计同源。

## 执行步骤

按顺序、用对话的方式问完下面 6 块；每块结束做一次「我理解你说的是 X，对吗？」的回放确认。

### Block 1 · 团队基线
1. 公司名称、所在行业 / 子赛道
2. 团队规模（人数 / 年营收区间）
3. 现有 SOP / 模板存放位置（飞书云文档 / Notion / 本地）

### Block 2 · 法域与监管
1. 业务覆盖国家 / 地区
2. 是否涉及特许行业（医疗 / 食品 / 金融 / 出版）
3. 是否涉及个人敏感信息 / 跨境数据传输

### Block 3 · 术语与文风
1. 你公司「必须用」的 3–5 个核心术语
2. 你公司「禁用」的 3–5 个术语
3. 对外文档的文风：正式严谨 / 商务友好 / 口语化

### Block 4 · 升级阈值（Escalation Threshold）
按金额 / 风险 / 法域三个维度，让用户给出「自动 / 提醒 / 强制升级」的边界。

### Block 5 · 集成系统
1. IM：飞书 / 钉钉 / 企微（appid / corpid）
2. ERP / CRM / OA 产品名与是否需要本插件直读
3. 知识库位置（语雀 / 飞书 / 本地 RAG）

### Block 6 · 模板上传
请用户上传 3–5 份代表性文档（合同 / 报告 / 邮件），AI 提炼模板结构与口径，写入 `CLAUDE.md` 的「自定义模板」节。

## 产出

写入 `plugins/dd-expert/CLAUDE.md`，并在 `MEMORY.md` 增加一条记忆指针 `- [dd-expert practice profile](plugins/dd-expert/CLAUDE.md) — Cold-start 完成于 {date}`。

## 风险守门

- 不要把任何客户提供的「敏感原文」直接写入 CLAUDE.md；只摘要结构、用语、阈值。
- 个人信息脱敏：身份证号 → `XXX****XXX`，手机号 → `1XX****XXXX`。
- 冷启动结束后**显式告知**用户：「画像已建立，但任何对外输出仍需你复核签字。」
