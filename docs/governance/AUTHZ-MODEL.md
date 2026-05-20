# 权限管理边界 Doctrine

> 谁能用 *什么 skill* 操作 *哪类数据* 在 *什么场景* 下？
> 本 doctrine 把这个问题拆成 **Subject × Action × Resource × Context**，并定义 Scope 命名规范。
> 实现见 `backend/src/services/governance/authz.py`（PDP）+ `policy/access-matrix.yaml`（policy）。

## 一、决策模型：RBAC + ABAC 混合

```
              ┌──────────────────────────────┐
   subject ─▶ │                              │
   action  ─▶ │   Policy Decision Point      │ ─▶ allow / deny / require_step_up / require_confirm
   resource ▶ │   (services/governance/      │
   context ─▶ │     authz.decide)            │
              └──────────────────────────────┘
                          ▲
                          │
              ┌───────────┴────────────┐
              │  policy/*.yaml         │
              │  (access-matrix /      │
              │   trust-levels /       │
              │   data-classification /│
              │   jurisdiction)        │
              └────────────────────────┘
```

- **RBAC**（粗粒度）：基于 [`UserRole`](../../backend/src/core/deps.py) — `super_admin / admin / org_admin / org_member / contributor / viewer / guest`
- **ABAC**（细粒度）：基于属性约束 — `tenant_id == subject.tenant_id`、`resource.classification ≤ subject.clearance`、`resource.jurisdiction in subject.allowed_jurisdictions`、`time_of_day ∈ business_hours`

## 二、Scope 命名规范

所有权限以 **Scope（字符串原子）** 表达。形式：

```
<resource-type>.<resource>.<action>[.<qualifier>]
```

### 示例

| Scope | 含义 |
|---|---|
| `skill.contract.review` | 调用 `/contract-steward:review` |
| `skill.contract.draft` | 调用 `/contract-steward:draft` |
| `skill.legal.research` | 调用 `/legal-advisor:legal-research` |
| `data.contract.read` | 读合同库 |
| `data.contract.write` | 写合同库 |
| `data.privileged.read` | 读律师特权数据（需 clearance=L4） |
| `connector.feishu.send` | 通过飞书外发消息 |
| `connector.amazon-sp.write` | 调用 Amazon SP-API 修改 listing |
| `cookbook.regulation-monitor.run` | 触发 regulation-monitor cookbook |
| `lifecycle.skill.publish` | 把 skill 从 REVIEW → PUBLISHED |
| `lifecycle.skill.revoke` | REVOKED 状态变更 |
| `governance.policy.write` | 修改 `policy/*.yaml` |
| `audit.log.read` | 读审计日志 |
| `audit.log.replay` | 跨日审计重放 |

### Wildcard

- `skill.*` — 调用任意 skill
- `data.*.read` — 读任意数据
- `connector.feishu.*` — 飞书所有动作

只允许 super_admin / SRE 持有 wildcard。

## 三、Role × Scope 默认矩阵

具体见 [`policy/access-matrix.yaml`](../../policy/access-matrix.yaml)。doctrine 层只声明原则：

| 角色 | 默认能力 |
|---|---|
| `super_admin` | `*.*` — 全集 |
| `admin` (= org_admin) | 组织内除 `governance.policy.write` / `lifecycle.skill.revoke` 外的全集 |
| `compliance_officer` | `audit.*` + `governance.policy.read` + 任何 skill 的 dry-run |
| `legal_member` | `skill.{legal,contract,dd}.*` + `data.contract.read` |
| `finance_member` | `skill.{finance,tax}.*` + `data.{ar,invoice,gl}.read` |
| `growth_member` | `skill.{market,lead,content}.*` + `connector.{wechat,linkedin,seo}.*` |
| `cross_border_member` | `skill.cross-border-ecom.*` + `connector.{amazon,shopify,stripe}.*` |
| `viewer` | `skill.*.dry_run` + `data.*.read`（按 classification 受限） |
| `guest` | 仅 `skill.anxin-assistant.intent-route`（且只读） |

## 四、决策结果

`authz.decide()` 返回四种结果之一：

| 结果 | 含义 | PEP 行为 |
|---|---|---|
| `ALLOW` | 通过 | 直接放行 |
| `DENY` | 拒绝 | 抛 403；写 audit 失败记录 |
| `REQUIRE_STEP_UP` | 需要二次认证 | 触发 MFA / 短信 / passkey |
| `REQUIRE_CONFIRM` | 需要人工 confirm | 草稿模式 + 推送到 inbox |

> **重要**：写动作 / 外发动作 / 特权数据 / 跨境 / > 阈值金额 **永远** 是 `REQUIRE_CONFIRM` 而不是 `ALLOW`。

## 五、Context 字段（ABAC 输入）

`decide(subject, action, resource, context)` 中的 `context` 必含：

```python
{
    "tenant_id": "...",
    "now": "<iso8601>",
    "ip": "...",
    "device_trust": "trusted" | "managed" | "byod",
    "session_age_seconds": 1234,
    "mfa_recent": True | False,
    "jurisdiction": "CN" | "EU" | "US",
    "amount_cny": 1234567,  # 仅金钱类操作
    "data_classification": "public" | "internal" | "confidential" | "restricted" | "privileged",
}
```

## 六、PEP 落地点（按优先级）

1. **API route 入口** — FastAPI dependency `require_scope("skill.contract.review")`
2. **Skill executor 入口** — `services/skill_executor/executor.py` 调用前先 PDP
3. **Tool 调用入口** — sandbox provider 内做 tool_allowlist 二次校验
4. **外发动作前置** — feishu / email / amazon-sp / stripe 等 connector 前置 `REQUIRE_CONFIRM`
5. **Managed agent cookbook 触发** — Celery worker 启动前 PDP

任何一层缺失都视为治理漏洞。

## 七、Step-up 升级触发

下列任一命中 → `REQUIRE_STEP_UP`：

- `subject.mfa_recent == False` 且 `action.severity ≥ HIGH`
- `subject.device_trust == "byod"` 且 `resource.classification ≥ confidential`
- `context.session_age_seconds > 3600`
- 跨境数据访问 `EU → CN` 或 `CN → US`

## 八、人工 Confirm 触发

下列任一命中 → `REQUIRE_CONFIRM`（即"草稿 + 推送 inbox 等签"）：

- 任何 `*.write` / `*.send` / `*.publish` / `*.revoke`
- `amount_cny > 100000`（按 plugin CLAUDE.md 升级阈值微调）
- `data_classification == "privileged"`
- `jurisdiction != subject.primary_jurisdiction`
- skill 状态 = `DEPRECATED`

## 九、决策可解释性

每次 `decide()` 必须返回 `(decision, reasons[])`。`reasons[]` 包含：

```json
[
  {"rule": "role-matrix", "value": "legal_member has skill.contract.review"},
  {"rule": "classification-gate", "value": "resource.classification=confidential, subject.clearance=L3, OK"},
  {"rule": "jurisdiction", "value": "resource.jurisdiction=CN matches subject.primary"},
  {"rule": "confirm-required", "value": "action ends with .write → REQUIRE_CONFIRM"}
]
```

写入审计日志；用户在 inbox / 错误响应中能看到。

## 十、与现有 backend 的衔接

| 现状 | 升级后 |
|---|---|
| `UserRole` enum 7 角色 | 不变；映射到新 scope 矩阵 |
| FastAPI auth via `core/deps.py` | 增加 `require_scope(scope: str)` dependency |
| `skill_executor` 直接调用 | 调用前先过 `governance.authz.decide()` |
| `app_authorization` OAuth | 不变；connector 调用前过 `decide()` |
| 无审计日志 | 引入 JSONL audit + DB 双写 |

迁移路径 → 见 [SKILL-LIFECYCLE.md § 集成路线](SKILL-LIFECYCLE.md)。
