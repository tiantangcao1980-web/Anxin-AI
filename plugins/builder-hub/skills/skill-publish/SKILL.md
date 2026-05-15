---
name: skill-publish
description: 把自研 skill 发布到 anxin-ai-official 注册表。先跑 skill-scan，再签名 / 推送。
access-level: firm
data-classification: L1
jurisdiction: CN
required-scopes:
  - governance.skill.skill_publish
tool-allowlist:
  - read_only
  - read_write_local
  - shell
lifecycle-stage: PUBLISHED
audit-level: high
pii-handling: mask-before-llm
network-egress: deny
privileged: false
argument-hint: 见执行流程
user-invocable: true
output-format: md
requires-research: false
requires-practice-profile: false
triggers:
  - 发布 skill
  - skill publish
  - 上架 skill
version: 1.0.0
---

# /builder-hub:skill-publish

把自研 skill 发布到 anxin-ai-official 注册表。先跑 skill-scan，再签名 / 推送。

## 执行流程

1. **本地 scan** — 调用 [`skill-scan`](../skill-scan/SKILL.md)；FAIL 直接拒绝。
2. **元信息确认**
   - name / version / license / author 必填
   - changelog 与上一版 diff 摘要
3. **签名**
   - 用 `ANXIN_PUBLISHER_GPG_KEY` 对 SKILL.md 内容做 GPG 签名
   - 签名写入 frontmatter `signature` 字段
4. **推送**
   - 默认目标：`anxin-ai-official` 注册表（参考 `plugin.json:allowlistedRegistries`）
   - 提交方式：通过 `gh pr create` 推到中央仓的 `marketplace/<author>/<skill>/` 目录
5. **审计**
   - `.claude/builder-hub-audit.jsonl` 追加 `{ts, action: publish, skill, version, sig}`

## 撤回

```
/builder-hub:skill-publish --revoke <skill>@<version> --reason "<安全问题描述>"
```

发起后中央仓自动添加 `revoked.json` 条目；所有客户端的 `skill-installer` 会拒绝该版本。

## 风险守门

- 不允许 publish 已 `revoked` 的版本号（必须 bump 版本）
- 不允许 publish access-level=`firm` 的 skill（避免越权）
- license 必须 Apache-2.0 / MIT / BSD
