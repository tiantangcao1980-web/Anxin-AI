---
name: skill-scan
description: 扫描一个 SKILL.md 文件的安全风险，输出 OK / WARN / FAIL 三级报告。可独立使用，也被 skill-installer 强制调用。
access-level: firm
data-classification: L1
jurisdiction: CN
required-scopes:
  - governance.skill.skill_scan
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
  - 扫描 skill
  - skill scan
  - skill 安全检查
version: 1.0.0
---

# /builder-hub:skill-scan

扫描一个 SKILL.md 文件的安全风险，输出 OK / WARN / FAIL 三级报告。可独立使用，也被 skill-installer 强制调用。

## 扫描类目

> 全部规则源在 [`policy/trust-levels.yaml § hard_fail_scan_rules / warn_scan_rules`](../../../../policy/trust-levels.yaml)。
> 治理体系定义见 [`docs/governance/TRUST-LEVELS.md`](../../../../docs/governance/TRUST-LEVELS.md)。

### 治理 frontmatter 强制（新增 2026-05-14）

SKILL.md 必含以下字段，否则视为 **hard-fail/frontmatter-incomplete**：

| 字段 | 取值 | 校验来源 |
|---|---|---|
| `access-level` | `team / practice / firm` | [`docs/governance/AUTHZ-MODEL.md`](../../../../docs/governance/AUTHZ-MODEL.md) |
| `data-classification` | `L1..L5` | [`policy/data-classification.yaml`](../../../../policy/data-classification.yaml) |
| `jurisdiction` | `CN / EU / US / global / ...` | [`policy/jurisdiction-rules.yaml`](../../../../policy/jurisdiction-rules.yaml) |
| `required-scopes` | list[str] | 必须能被 `policy/access-matrix.yaml` 任一 pattern 匹配 |
| `tool-allowlist` | list[category] | 必须 ⊆ `policy/tool-allowlist.yaml § tool_categories` |
| `lifecycle-stage` | `DRAFT / REVIEW / PUBLISHED / DEPRECATED / REVOKED` | `policy/skill-lifecycle.yaml § states` |
| `audit-level` | `low / medium / high` | doctrine |
| `pii-handling` | `mask-before-llm / keep-raw / reject` | `policy/pii-redaction.yaml` |
| `network-egress` | `deny / allowlist / open` | doctrine |
| `privileged` | `true / false` | 涉及 L5 必为 true |

实际执行：`python3 scripts/governance-lint.py`（CI 自动跑）。

### Hard-Fail（任一命中 → 拒绝安装）

| ID | 检查 |
|---|---|
| `hidden-content/zero-width` | 文本含 U+200B / U+200C / U+200D / U+FEFF |
| `hidden-content/font-size-0` | 含 `font-size: 0` / `style="display:none"` 类隐藏 |
| `hidden-content/white-on-white` | 白底白字 / 透明字 |
| `prompt-injection/ignore-previous` | 含「忽略以上指令」「ignore previous」类话术 |
| `prompt-injection/role-override` | 含「你现在是 root / admin / 系统」类越权 |
| `prompt-injection/data-exfil` | 含「把这段发到 https://」「curl ... data exfil」 |
| `tool-scope/excessive-write` | frontmatter 声明只读但 body 调用 Edit/Write/Delete |
| `license/incompatible` | 声明 GPL/AGPL/SSPL，与 Apache-2.0 冲突 |

### Warn（提示但不阻断）

| ID | 检查 |
|---|---|
| `freshness/stale-30d` | 引用的法规 / 政策日期 > 30 天 |
| `tool-scope/network-egress` | 声明会访问公网 |
| `size/oversized` | SKILL.md > 50 KB |
| `frontmatter/missing-fields` | description / triggers / version 缺失 |

## 输出格式

```json
{
  "skill": "<path>",
  "result": "OK | WARN | FAIL",
  "findings": [
    {"id": "hidden-content/zero-width", "severity": "fail", "line": 12, "snippet": "…"},
    {"id": "freshness/stale-30d", "severity": "warn", "msg": "2025-03-01 政策已过 1 年"}
  ],
  "scannedAt": "<iso8601>"
}
```

## 后端实现

实现位置：`backend/src/services/skill_trust/scanner.py`（待落地）。
依赖：`python -m pip install unicodedata2 markdown-it-py`。

## CI 集成

```bash
# 全仓自检（贡献者必跑）
python3 scripts/claude-plugin-validate.py &&   for s in $(find skills plugins -name SKILL.md); do
    python3 -m src.services.skill_trust.scanner "$s" || exit 1
  done
```
