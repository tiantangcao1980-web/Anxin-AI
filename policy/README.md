# Policy as Code

> 6 份 YAML 是 Anxin AI 全部访问决策的真相源。变更必须走 PR + 双签，CI 校验通过且生成 policy snapshot 才能合并。
>
> Doctrine 解释 *为什么*，本目录的 yaml 写下 *是什么*，[`backend/src/services/governance/`](../backend/src/services/governance/) 在运行时 *强制*。

| 文件 | 治理 doctrine | 后端模块 |
|---|---|---|
| [`access-matrix.yaml`](access-matrix.yaml) | [AUTHZ-MODEL.md](../docs/governance/AUTHZ-MODEL.md) | `governance/authz.py` |
| [`trust-levels.yaml`](trust-levels.yaml) | [TRUST-LEVELS.md](../docs/governance/TRUST-LEVELS.md) | `governance/trust.py` |
| [`data-classification.yaml`](data-classification.yaml) | [DATA-BOUNDARY.md](../docs/governance/DATA-BOUNDARY.md) | `governance/data_classifier.py` |
| [`jurisdiction-rules.yaml`](jurisdiction-rules.yaml) | [DATA-BOUNDARY.md](../docs/governance/DATA-BOUNDARY.md) | `governance/authz.py` |
| [`tool-allowlist.yaml`](tool-allowlist.yaml) | [AUTHZ-MODEL.md](../docs/governance/AUTHZ-MODEL.md) | `governance/tool_scope.py` |
| [`pii-redaction.yaml`](pii-redaction.yaml) | [DATA-BOUNDARY.md](../docs/governance/DATA-BOUNDARY.md) | `governance/data_classifier.py` |
| [`skill-lifecycle.yaml`](skill-lifecycle.yaml) | [SKILL-LIFECYCLE.md](../docs/governance/SKILL-LIFECYCLE.md) | `governance/skill_lifecycle.py` |

## 修改流程

1. 写改动到对应 yaml（不要绕过 doctrine）
2. 跑 `python3 scripts/governance-lint.py` 校验语法 + schema
3. 跑 `python3 scripts/access-matrix-diff.py` 看 role × scope 变化点
4. 走 PR，至少 1 reviewer（涉及 `governance.*` / `lifecycle.*` 必须 2 reviewer）
5. CI 合并时自动生成 policy snapshot 推送到 `.claude/policy-snapshots/<id>/`
6. 后端 reload — `kill -HUP <gunicorn pid>` 或 `make backend-reload-policy`

## 不要改

- 把 `super_admin` 从 wildcard 里去除（会锁死自己）
- 在 `data-classification.yaml` 把 L5 默认行为放宽
- 在 `tool-allowlist.yaml` 给 `untrusted` skill 加 connector 写权限

这三件事是 doctrine 层的"不变量"。需要打破必须先改 doctrine（社会成本远大于改 yaml）。
