---
name: skill-installer
description: 安装一个第三方 skill 到 Anxin AI。强制串行执行：来源校验 → /builder-hub:skill-scan → 用户 confirm → 写入 plugins/<dest>/skills/<name>/。
access-level: firm
data-classification: L1
jurisdiction: CN
required-scopes:
  - governance.skill.skill_installer
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
  - 安装 skill
  - install skill
  - skill installer
version: 1.0.0
---

# /builder-hub:skill-installer

安装一个第三方 skill 到 Anxin AI。强制串行执行：来源校验 → /builder-hub:skill-scan → 用户 confirm → 写入 plugins/<dest>/skills/<name>/。

## 执行流程（不可绕过）

1. **来源校验**
   - 解析 source URL（git / npm / 本地路径）
   - 与 `plugin.json:allowlistedRegistries[]` 比对
   - 不在 allowlist → 默认拒绝；用户加 `--trust-untrusted` 才能继续，并要求二次 confirm
2. **下载到沙箱**
   - 临时目录 `.claude/skill-sandbox/<uuid>/`
   - 解压 / 克隆后 **不读取任何脚本**，只对 markdown 做扫描
3. **调用 [`skill-scan`](../skill-scan/SKILL.md)**
   - 必扫规则不可关；任一 hard-fail 直接拒绝
   - 输出风险报告（OK / WARN / FAIL 三级）
4. **用户 confirm**
   - 展示 scan report + 影响的 persona + 写入路径
   - 显式 [Install] / [Cancel] / [View Diff]
5. **写入目标 persona**
   - 复制到 `plugins/<dest>/skills/<name>/`
   - 更新 `plugins/<dest>/.claude-plugin/plugin.json:skills[]`
   - 跑 `python3 scripts/sync-plugins-to-backend.py` 同步 backend
6. **审计日志**
   - 追加一条到 `.claude/builder-hub-audit.jsonl`：`{ts, action: install, source, scan_result, user}`

## 拒绝场景

- 来源不在 allowlist 且无 `--trust-untrusted`
- scan 出现任一 hard-fail（隐藏内容 / 注入 / 越权 / license 冲突）
- 用户 cancel
- 写入路径已存在且 `--force` 未给

## 风险守门

- 第三方 skill 默认 access-level=`team`，不允许声明 `firm`
- 安装来自 untrusted 源的 skill 后，自动给所有 `/<plugin>:<新 skill>` 调用前置一条 "⚠ 此 skill 来自社区源" 提示，直到用户主动升级它的 trust level
