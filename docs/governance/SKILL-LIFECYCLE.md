# Skill 生命周期 Doctrine

> Skill 是 Anxin AI 的"原子能力"。它的发布、变更、撤回不能像普通代码改一样随手提交。
> 本 doctrine 定义 5 状态机 + 7 个守门，并对照 [`policy/skill-lifecycle.yaml`](../../policy/skill-lifecycle.yaml) 实现。

## 状态机

```
                    ┌──────────────────────────────────────────────┐
                    │                                              │
   ┌─────────┐    ┌────────┐    ┌──────────┐    ┌────────────┐    │
   │  DRAFT  │───▶│ REVIEW │───▶│PUBLISHED │───▶│ DEPRECATED │───┤
   └─────────┘    └────────┘    └────┬─────┘    └────────────┘    │
        ▲              │              │                            │
        │              ▼              ▼                            ▼
        │         ┌─────────┐    ┌─────────┐                  ┌─────────┐
        └─────────│REJECTED │    │ REVOKED │◀─────────────────│  any    │
                  └─────────┘    └─────────┘                  └─────────┘
                                  (security)
```

### 状态定义

| 状态 | 谁可调用 | 落库 | 审计粒度 |
|---|---|---|---|
| `DRAFT` | 仅作者本人 | 不进入 skill_registry | 仅本地 |
| `REVIEW` | 仅 reviewer dry-run | shadow 模式 | 100% 录制 |
| `PUBLISHED` | 按 `policy/access-matrix.yaml` | 正式注册 | 抽样 + 高敏全量 |
| `DEPRECATED` | 已有调用方继续；不再分配给新 user | 标记 + 提示 | 100% 录制 |
| `REVOKED` | **禁止任何调用** | 移出 registry | 历史调用归档 |

### 状态迁移守门

| 迁移 | 守门 | 决策点 |
|---|---|---|
| `DRAFT → REVIEW` | governance-lint 通过 + 单测覆盖率 ≥ 80% + frontmatter 完整 | `scripts/governance-lint.py` |
| `REVIEW → PUBLISHED` | 至少 1 reviewer 双签 + 安全 scan 0 hard-fail + shadow 24h 无异常 | Builder Hub `skill-publish` |
| `REVIEW → REJECTED` | reviewer 显式拒绝；理由必填 | PR review |
| `PUBLISHED → DEPRECATED` | 给出替代 skill + 12 周缓冲期 | maintainer 提案 |
| `PUBLISHED → REVOKED` | 安全事件 / 合规事件触发；< 24h 决策 | 安全应急委员会 |
| `DEPRECATED → REVOKED` | 缓冲期满 or 调用量 = 0 | 自动 + 通知 |

## 七道守门（与上图对应）

| # | 守门 | 实现位置 |
|---|---|---|
| 1 | **Frontmatter 完整** | `scripts/governance-lint.py` § validate_frontmatter |
| 2 | **Tool scope 合法** | `policy/tool-allowlist.yaml` + lint |
| 3 | **数据分级 / 法域 / PII 字段已声明** | `policy/data-classification.yaml` |
| 4 | **单测覆盖 ≥ 80%** | CI `pytest --cov` |
| 5 | **Builder Hub scan 0 hard-fail** | `plugins/builder-hub/skills/skill-scan` |
| 6 | **Reviewer 双签** | GitHub PR review |
| 7 | **Shadow run 24h 无异常** | `services/governance/shadow_runner.py`（待 P12） |

## 版本与撤回

- **Semver**：`major.minor.patch` 写在 frontmatter `version` 字段
  - **major bump**：行为不兼容（如新增必填参数）
  - **minor bump**：行为兼容新增（新可选参数 / 新输出字段）
  - **patch bump**：bug fix / 文档 / prompt 微调
- **撤回**：通过 `/builder-hub:skill-publish --revoke <skill>@<version> --reason "..."`；中央仓写 `revoked.json`，全网客户端拒绝该版本。
- **回滚**：永远新发版本（如 `1.2.4`）而不是回退已发版本；保留 audit trail。

## 弃用通知（Deprecation Notice）

skill 进入 DEPRECATED 时必须：

1. 在 SKILL.md 顶部加 `> **⚠ Deprecated since vX.Y.Z**` Banner
2. 注明替代 skill 与迁移指南
3. `governance/audit_log` 写 `lifecycle_change` 条目
4. 缓冲期内**每次调用**前置一段"该 skill 将在 YYYY-MM-DD 后停用"提示

## 与 policy 的对应

具体阈值（覆盖率 80% / shadow 24h / 缓冲 12 周）都写在 [`policy/skill-lifecycle.yaml`](../../policy/skill-lifecycle.yaml)。
本 doctrine 解释 *为什么*；policy 写下 *是什么*；代码在 *运行时强制*。
