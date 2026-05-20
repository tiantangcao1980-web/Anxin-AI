# 审计日志规格 Doctrine

> 任何一次 skill 调用 / 数据访问 / policy 决策都必须能在 30 秒内被审计重放。
> 本 doctrine 定义 JSONL 字段、留存策略与可重放性要求。
> 实现 `backend/src/services/governance/audit.py`。

## 一、存储

### 双写

每条审计事件**同时**写两处：

1. **JSONL 文件** — `.claude/audit/YYYY-MM-DD.jsonl`（append-only，不可改）
2. **数据库** — `audit_events` 表（带索引便于查询）

JSONL 是法证级真相源，DB 是性能层。两边对账见 `scripts/audit-reconcile.py`（待落地）。

### 留存

| 事件类型 | 最短留存 | 备份介质 |
|---|---|---|
| 合规相关（法务 / 财税 / 跨境）| 10 年 | NAS + S3 Glacier |
| PII / privileged 数据访问 | 7 年 | NAS + S3 Glacier |
| 普通 skill 调用 | 1 年 | NAS |
| 系统级（authz decision / policy change）| 永久 | NAS + S3 Glacier |
| Dry-run / shadow | 30 天 | 本地 |

## 二、JSONL 字段规格

```json
{
  "ts": "2026-05-14T13:48:35.123Z",
  "event_id": "evt_01JF9X7K8M3P5Q7R9S1T3V5W7Y",
  "event_type": "skill.execute" | "authz.decide" | "data.access" | "policy.change" | "lifecycle.change" | "confirm.granted" | "confirm.denied" | "external.send",
  "trace_id": "trace_abc...",
  "span_id": "span_def...",
  "actor": {
    "type": "user" | "service" | "cookbook" | "agent",
    "id": "usr_...",
    "role": "legal_member",
    "tenant_id": "tnt_..."
  },
  "subject": {
    "tenant_id": "tnt_...",
    "session_id": "sess_...",
    "mfa_recent": true,
    "device_trust": "managed"
  },
  "action": "skill.contract.review",
  "resource": {
    "type": "skill" | "cookbook" | "connector" | "data" | "policy",
    "id": "/contract-steward:review",
    "version": "1.2.0",
    "classification": "confidential",
    "jurisdiction": "CN"
  },
  "context": {
    "ip": "...",
    "user_agent": "...",
    "amount_cny": 0,
    "input_hash": "sha256:...",
    "output_hash": "sha256:...",
    "pii_findings": ["phone:1", "id-card:1"]
  },
  "decision": "ALLOW" | "DENY" | "REQUIRE_STEP_UP" | "REQUIRE_CONFIRM",
  "decision_reasons": [
    { "rule": "role-matrix", "value": "..." },
    { "rule": "classification-gate", "value": "..." }
  ],
  "outcome": "success" | "failure" | "draft-staged" | "user-cancelled",
  "duration_ms": 1234,
  "human_confirm": {
    "required": true,
    "granted_by": "usr_...",
    "granted_at": "...",
    "decision_basis": "manager-approval"
  },
  "fingerprint": "sha256:...",  // 全字段排序后 hash，用于防篡改
  "schema_version": 1
}
```

### 必填字段

`ts / event_id / event_type / actor / action / resource / decision / outcome / fingerprint / schema_version`

### 不要写入

- LLM 完整 prompt（写 `input_hash` 即可，原文走另外的 prompt-archive，按需调取）
- 完整 LLM 输出（写 `output_hash`）
- 解密后的 PII 原文（永远只写脱敏后或 hash）

## 三、Fingerprint 防篡改

```python
fingerprint = sha256(
    canonical_json(event_without_fingerprint_field)
).hexdigest()
```

每日打包成 `YYYY-MM-DD.jsonl.sig` 签名（使用平台 GPG key）。
若任一行被改动 → fingerprint 校验失败 → 触发 incident。

## 四、查询接口

```bash
# 1) 重放某 user 一天内所有 skill 调用
python3 scripts/audit-replay.py --user usr_xxx --date 2026-05-14

# 2) 查所有触发 REQUIRE_CONFIRM 但被拒的事件
python3 scripts/audit-replay.py --decision REQUIRE_CONFIRM --outcome user-cancelled

# 3) 跨境数据访问审计
python3 scripts/audit-replay.py --jurisdiction "CN->EU" --since 2026-04-01

# 4) 重放某次 skill 调用的完整决策路径
python3 scripts/audit-replay.py --trace-id trace_abc...
```

## 五、可重放性（Replay）

每条事件必须满足"30 秒内可重放"：

1. 凭 `trace_id` 找到一组关联事件（authz.decide → skill.execute → external.send → confirm.granted）
2. 凭 `input_hash` 从 prompt-archive 调出原始输入
3. 凭 `policy_snapshot_id` 调出当时生效的 policy 快照
4. 重新跑 `authz.decide()` 得到相同结果

不满足 = 审计不可用 = 视为合规事故。

## 六、Policy 快照

`policy/*.yaml` 每次变更通过 PR merge 时，CI 自动：

1. 计算所有 yaml 的 git tree hash → `policy_snapshot_id`
2. 上传到 S3 + 本地 `.claude/policy-snapshots/<id>/`
3. 后续审计事件携带这个 `policy_snapshot_id`

确保 6 个月前一次决策能用 6 个月前的 policy 重放。

## 七、告警

下列事件实时推送到飞书 #ops-security：

- `decision == DENY` 且 `actor.role >= org_admin`（管理员被拒，可能是错配置）
- `outcome == failure` 且 fingerprint 校验失败（潜在篡改）
- `event_type == policy.change` 且 actor 不在 authorized list
- `event_type == external.send` 且 `human_confirm.granted == false`（绕过 confirm 流出）
- 1 小时内同一 `actor.id` 触发 `DENY > 20` 次（潜在攻击）

## 八、与 backend 衔接

```python
from src.services.governance.audit import audit_log

@audit_log(event_type="skill.execute")
async def run_skill(...):
    ...
```

装饰器自动填 `actor / context / fingerprint`，业务代码只传 `resource / decision / outcome`。
