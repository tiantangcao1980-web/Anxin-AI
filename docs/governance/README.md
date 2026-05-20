# 安心智能助手 · 治理与权限边界文档体系

> Skill 治理 + 权限管理边界的**单一真相源**。
> 任何 skill / cookbook / connector / persona 的访问与执行决策都必须能在此处溯源到一条 doctrine + 一条 policy 条目。

## 文档索引

| 文档 | 用途 | 受众 |
|---|---|---|
| [SKILL-LIFECYCLE.md](SKILL-LIFECYCLE.md) | Skill 状态机：DRAFT → REVIEW → PUBLISHED → DEPRECATED → REVOKED | skill 作者 / reviewer |
| [AUTHZ-MODEL.md](AUTHZ-MODEL.md) | 权限模型：subject × action × resource，RBAC + ABAC，scope 命名规范 | 全员（必读） |
| [DATA-BOUNDARY.md](DATA-BOUNDARY.md) | 数据分级 + 法域边界 + 特权数据；跨境 / PII / 律师特权三条红线 | 法务 / 安全 / 后端 |
| [AUDIT-LOG-SPEC.md](AUDIT-LOG-SPEC.md) | 审计日志 JSONL 规格 + 留存 / 重放 / 法证可用性 | 安全 / 运维 |
| [TRUST-LEVELS.md](TRUST-LEVELS.md) | 来源信任矩阵：verified / community / untrusted；Builder Hub 三道关 | 平台 / Builder Hub maintainer |

## 设计原则

1. **Policy as code** — 所有访问策略都在 [`policy/*.yaml`](../../policy/) 而不是散落在 if/else。
2. **PDP / PEP 分离** — Policy Decision Point（`backend/src/services/governance/authz.py`）只负责"判定是否允许"，Policy Enforcement Point（中间件 / decorator）负责"在调用前阻断"。
3. **默认拒绝（Deny by default）** — 任何未显式列入 `policy/access-matrix.yaml` 的访问都拒绝。
4. **可审计性优先** — 任何一次 skill 调用必须能在 30 秒内通过 [`scripts/audit-replay.py`](../../scripts/audit-replay.py) 还原"谁 / 何时 / 用什么数据 / 调了什么 / 产出什么 / 是否人工 confirm"。
5. **三条不可放松红线**：
   - **特权数据**（律师 / 客户特权通讯）禁止写入共享知识库
   - **跨境数据**强制人工复核 + 法域声明
   - **个人敏感信息**外发前必须脱敏

## 与 Anthropic 仓库参考对照

| 维度 | claude-for-legal | claude-for-financial | Anxin AI 落地位置 |
|---|---|---|---|
| Skill 状态 | 未显式 | 未显式 | `policy/skill-lifecycle.yaml` |
| Trust level | legal-builder-hub | n/a | `policy/trust-levels.yaml` + `plugins/builder-hub` |
| Tool scope lint | `scripts/lint-tool-scope.py` | n/a | `policy/tool-allowlist.yaml` + `scripts/governance-lint.py` |
| Privilege handling | 文档守则 | 文档守则 | `policy/data-classification.yaml` + `services/governance/data_classifier.py` |
| Jurisdiction | CLAUDE.md per plugin | 模型限制 | `policy/jurisdiction-rules.yaml` |
| Audit | 未显式 | 未显式 | `docs/governance/AUDIT-LOG-SPEC.md` + `services/governance/audit.py` |

## 决策矩阵：是要 doctrine 还是 policy？

| 我想… | 改哪里 |
|---|---|
| 给某个 skill 加一条访问规则 | `policy/access-matrix.yaml` |
| 把某类数据升级为 confidential | `policy/data-classification.yaml` |
| 新增一个 trust level | 先改 `docs/governance/TRUST-LEVELS.md`（doctrine），再改 `policy/trust-levels.yaml` |
| 增加跨境合规要求 | `policy/jurisdiction-rules.yaml` |
| 引入新概念（如 quorum review） | 先改 `docs/governance/*.md` 写清楚 doctrine，再加 policy + 实现 |

## 一句话

> **Doctrine 解释为什么，Policy 写下到底是什么，Code 在运行时强制它。** 三者一致才算闭环。
