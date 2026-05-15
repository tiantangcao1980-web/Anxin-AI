# 🧩 Builder Hub · 社区 Skill 信任层

> 仿照 Anthropic [`claude-for-legal/legal-builder-hub`](https://github.com/anthropics/claude-for-legal/tree/main/legal-builder-hub) 的设计。
> 让第三方贡献者也能把 skill 发布到 Anxin AI 生态，但**安装前必须过三道检查**。

## 为什么需要信任层

当 skill 来自第三方时，单个 markdown 文件可能携带：

- **隐藏内容**：零宽字符、白底白字、字号 0 的注入文本
- **Prompt 注入**：「忽略以上指令」「以系统管理员身份」类话术
- **越权工具**：声明只读但实际写 / 网络外发
- **数据外渗**：把客户数据 POST 到第三方
- **License 不兼容**：GPL 与本仓库 Apache-2.0 不兼容
- **过期内容**：30 天未更新的法规引用

Builder Hub 在 `/builder-hub:skill-installer` 流程里把这三道关卡**强制串行**。

## 三个 Slash 命令

| 命令 | 用途 |
|---|---|
| `/builder-hub:skill-installer` | 安装一个第三方 skill（必跑 scan） |
| `/builder-hub:skill-scan` | 单独扫一个 skill（不安装），输出风险报告 |
| `/builder-hub:skill-publish` | 把自研 skill 发布到 anxin-ai-official 注册表 |

## Allowlist 注册表

只有 `plugin.json` 中 `allowlistedRegistries[*]` 注册过的源才允许安装。
默认两个：

- `anxin-ai-official` — Anxin AI 官方市场（trustLevel: verified）
- `anthropic-skills` — Anthropic 官方 skill 仓（trustLevel: verified）

新增信任源**必须由 PR review 双签**。社区源默认 trustLevel: untrusted，安装时必须显式 `--trust-untrusted`。

## 扫描规则（`scanRules`）

| 类别 | 规则 |
|---|---|
| hidden-content | zero-width / font-size-0 / white-on-white |
| prompt-injection | ignore-previous / role-override / data-exfil |
| tool-scope | excessive-write / network-egress |
| license | incompatible（与 Apache-2.0 不兼容时） |
| freshness | stale-30d（法规 / 政策类引用超 30 天） |

实现见 `backend/src/services/skill_trust/scanner.py`（待落地）。

## 审计日志

每次 install / scan / publish 都写入 `.claude/builder-hub-audit.jsonl`，含：
`{ts, action, skill, source, scan_result, user, sig}`。

便于事后追溯 / 合规审计。
