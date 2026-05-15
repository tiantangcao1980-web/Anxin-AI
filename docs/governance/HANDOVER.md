# 治理体系交付手册（HANDOVER）

> 给合规官 / 法务 / 安全 / 法定代表人的操作手册。
> 不需要懂代码也能跑日常治理工作。

## 一、你能做什么

| 我想… | 在哪里 | 谁能做 |
|---|---|---|
| 看每天 AI 调用了什么 | `/admin/governance/audit` | compliance_officer / org_admin / super_admin |
| 批准一条等待外发的草稿 | `/admin/governance/tickets` | org_admin / compliance_officer / 受指派 reviewer |
| 看当前生效的访问规则 | `/admin/governance/policy` | compliance_officer / org_admin / super_admin |
| 撤回一个有漏洞的 skill | `/admin/governance/revoked` + 走 PR | security_committee / super_admin |
| 改 policy（角色 / 法域 / 阈值） | 修 `policy/*.yaml` + 走 PR | super_admin（双签） |
| 紧急停掉某个 cookbook | 改 cookbook agent.yaml 的 `trigger.cron: "0 0 31 2 *"`（永不触发） | org_admin |
| 查"上周三晚上 9 点谁拒绝了一条 ticket" | 审计时间线筛 trace_id / decision=DENY | compliance_officer |

## 二、上班第一天 30 分钟跑通

1. 登录 → 侧边栏「治理 Dashboard」
2. **总览页**看四个数字：
   - 当前 Policy 快照（`pol_xxx…`）
   - 待 Confirm 工单数
   - Shadow 录制中
   - 已撤回 Skill
3. **审计时间线**：按「事件类型 = `confirm.granted`」搜，确认昨天有正常审批
4. **待 Confirm**：随便挑一条 pending，点开看「资源 / 上下文」
5. 看 `docs/governance/README.md` 5 份 doctrine 文档；本手册只讲操作

## 三、9 个常见日常情境

### 情境 1：突然来一堆待 Confirm，怎么快速分类？

打开 `/admin/governance/tickets`，按 `persona` 过滤：
- `legal-advisor` / `contract-steward` → 法务岗审批
- `finance-tax-advisor` → 财务岗审批
- `cross-border-ecom` → 跨境运营审批

点开任一条看：
- **action** — 是发飞书 / 调 Amazon / 改合同？
- **resource.classification** — L3 普通 / L4 含 PII / L5 律师特权
- **resource.jurisdiction** — CN / EU / US / global？
- **policy_snapshot_id** — 现在生效的 policy 快照

### 情境 2：批准前，要确认什么？

强制三问：

1. **是不是这个人发起的？** 看 `requester_role`（不应该是 `system` 时机不对）
2. **金额对吗？** 看 `context.amount_cny`（超过 100 万必须问老板）
3. **法域对吗？** 跨境（jurisdiction != CN）必须先看是否有 SCC / CAC 备案

任何一条不对 → 点「✗ 拒绝」，必填理由。审计永久留档。

### 情境 3：紧急："这条 skill 有漏洞，全网下架"

**5 分钟内操作**：

```bash
# 路径 1：CLI（推荐 — 自动写 audit + 全 tenant 立即生效）
python3 -c "
from src.services.governance.builder_hub_installer import revoke_skill
revoke_skill(
    skill_id='/legal-advisor:bad-skill',
    version='1.2.3',
    reason='prompt-injection CVE-2026-XXXX',
    revoked_by='usr_security_lead',
    successor_version='1.2.4',
)
"

# 路径 2：UI（向 dev 提工单走 PR；适合非紧急）
```

撤回后：
- `.claude/builder-hub/revoked.json` 自动写入
- 全网客户端下次 `evaluate_trust()` 立即拒绝
- `/admin/governance/revoked` 立刻看到这条
- 主审计 JSONL 有 `lifecycle.change/revoke` 事件

### 情境 4：怀疑审计被篡改

```bash
# 跑对账（默认最近 7 天）
python3 scripts/audit-reconcile.py --json

# 输出关注三个字段：
#   fingerprint_invalid: > 0  → JSONL 被改过（incident）
#   fingerprint_drift  : > 0  → DB 与 JSONL 不一致（incident）
#   missing_in_jsonl   : > 0  → DB 有 JSONL 没有（非法 — 不可能正常出现）
```

任一 > 0 → 立刻：
1. 冻结相关账号（在 `/admin/users` 禁用）
2. 写 incident report 给安全负责人
3. 飞书 #ops-security 已自动告警（配置 `ANXIN_OPS_FEISHU_WEBHOOK` 后）

### 情境 5：法务问 "上周老王的合同审查跑了多少次"

```
/admin/governance/audit
  → actor_id = usr_lao_wang_id
  → event_type = skill.execute
  → since = 2026-05-07
```

点开任一条看：
- `policy_snapshot_id` → 当时生效的 policy
- `decision_reasons` → 为什么 ALLOW / DENY
- `fingerprint` → 防篡改指纹

CLI 高级查询：
```bash
python3 scripts/audit-replay.py --user usr_xxx --since 2026-05-07 --verify-fingerprint
```

### 情境 6：跨境数据访问要怎么走流程

业务侧（写 code 的同事）调用任何含跨境 connector 时，PDP 自动判定 `REQUIRE_CONFIRM` 或 `REQUIRE_STEP_UP`。

合规官审批前确认：
- **目的地国家** — 看 `resource.jurisdiction` 是否在 `policy/jurisdiction-rules.yaml § cross_border` 已声明的路径
- **法务前置条件** — 检查 PIPL SCC 是否已备案；EU→CN 需 GDPR Art.46 SCC + TIA
- **数据类目** — 重要数据 / 国家秘密 / 生物特征 → 走 DENY（拒绝），需要单独走 CAC 评估
- **审批人不能是请求人本人**（SoD 自动校验）

### 情境 7：周一发现待 Confirm 累积了 200 条

可能是周末某个 cookbook 跑了好多次。按 `cookbook_name` 过滤：

```
/admin/governance/tickets
  → persona = ALL
  → status = pending
  → 看 cookbook_name 列
```

如果是 `regulation-monitor` 一天产生 1 条以上，说明它出 bug：

```bash
# 看 cookbook 最近运行的 staged draft
ls -lt .claude/managed-agent-runs/regulation-monitor/ | head -10

# 紧急停掉（编辑 agent.yaml）
# managed-agent-cookbooks/regulation-monitor/agent.yaml
#   trigger:
#     type: schedule
#     cron: "0 0 31 2 *"   # 2 月 31 日永不触发
```

旧 ticket 批量处理：
- `decision_note: "周末堆积，统一拒绝"` → 全选 ✗
- 或调 CLI `confirm_inbox.expire_overdue()` 等 72h 自动过期

### 情境 8：法定代表人要做"合规评审"

每季度跑一次：

```bash
# 1. Skill 全量盘点（含撤回历史）
cat .claude/builder-hub/revoked.json   # 看撤回了哪些

# 2. Policy 变更历史
ls -lt .claude/policy-snapshots/ | head -20
python3 scripts/access-matrix-diff.py --base HEAD~365  # 一年内 access-matrix 变更

# 3. 审计统计
python3 scripts/audit-replay.py --since $(date -v-90d +%F) --verify-fingerprint > /tmp/q-audit.txt
# 关注：DENY 数量 / 跨境数 / REQUIRE_STEP_UP 通过率

# 4. Shadow 通过率
# /admin/governance/revoked → 看 shadow runs 表
# 若 review_errors / total > 5% 多次 → 说明发布质量门没起作用
```

### 情境 9：新员工首次登录后看到的样子

新员工 role 默认 `viewer`，可访问：
- `/admin/governance` 总览（只读）
- `/admin/governance/audit` 审计时间线（只能查自己相关）
- `/admin/governance/policy` 看 policy 但不能 reload

不能访问：
- 任何 `*.write` / `*.send` / `*.publish`
- 涉及 L3+ 数据的查看（按 `clearance_by_role: viewer=L2` 卡）

需要升级 role → `/admin/users` 由 super_admin 改。

## 四、不该做的事

| 动作 | 为什么不能做 | 后果 |
|---|---|---|
| 直接改 `.claude/audit/*.jsonl` | 这是法证真相源；改了 fingerprint 校验失败 | 触发 incident 告警；signed 后无法掩盖 |
| 删 `.claude/policy-snapshots/` | 6 个月后无法 replay 当时决策 | 审计不可用 = 合规事故 |
| 自己批准自己提的 ticket（高敏 action） | SoD 强制；自动拒绝 | API 抛 PermissionError |
| 把 `super_admin` 的 wildcard 删了 | 锁死自己 | 没人能恢复；走 DB 紧急救援 |
| 给社区源 `--trust-untrusted` 后忘了改回 | 全网容易被注入 | 安全风险 |
| 把 `data-classification.yaml` 的 L5 默认行为放宽 | doctrine 不变量 | PR review 会拒绝（双签拦截） |

## 五、紧急联系链

| 类型 | 第一响应 | 备份 |
|---|---|---|
| 审计被篡改 | 安全负责人 → 飞书 #ops-security | 法定代表人 |
| 数据外泄 / 越权 | 安全 + 法务 → 24h 内 CAC 报告（涉个人信息） | 法定代表人签字 |
| Skill 被恶意安装 | super_admin 调 `revoke_skill()` | builder-hub maintainer |
| Policy 被错改 | super_admin `kill -HUP <pid>` 回滚到旧 snapshot | dev 上一次 commit |
| Cookbook 错跑 | org_admin 改 cookbook cron 到永不触发 | 联系 dev |

## 六、命令速查

```bash
# 校验
python3 scripts/governance-lint.py                # 治理 frontmatter + policy schema
python3 scripts/access-matrix-diff.py --base main # PR 时 role × scope diff

# 审计
python3 scripts/audit-replay.py --user U --since YYYY-MM-DD --verify-fingerprint
python3 scripts/audit-reconcile.py --json         # JSONL ↔ DB 对账（cron 已每小时一次）
python3 scripts/audit-reconcile.py --backfill     # 把 JSONL 缺的写回 DB（用于补丢失）

# Policy
# 改完 yaml 后：
curl -X POST -H "Authorization: Bearer $TOKEN" $API/api/v1/governance/policy/reload
# 或 kill -HUP <gunicorn pid>

# Cookbook 单次手动跑
python3 scripts/claude-orchestrate.py regulation-monitor --dry-run
```

## 七、季度复盘清单

每季度对以下 7 项打勾：

- [ ] 审计 fingerprint 全期校验通过（脚本输出 0 invalid / 0 drift）
- [ ] revoked.json 与上季度 diff 已记入 governance changelog
- [ ] policy snapshots 数量 ≥ 季度内 PR 数（说明每次 PR 都生成快照）
- [ ] 跨境数据访问条目数符合预期（异常增长要追问）
- [ ] DENY 占比 < 5% 且呈下降趋势（如果上升说明权限误配）
- [ ] shadow runs 通过率 ≥ 95%（低于说明 REVIEW 质量门不严）
- [ ] confirm-tickets expired 占比 < 10%（高于说明 inbox 没人盯）

## 八、文档导航

| 文档 | 受众 | 用途 |
|---|---|---|
| 本文 HANDOVER.md | 合规官 / 法务 | 日常操作（不需懂代码） |
| [SKILL-LIFECYCLE.md](SKILL-LIFECYCLE.md) | dev + reviewer | Skill 5 状态机守门 |
| [AUTHZ-MODEL.md](AUTHZ-MODEL.md) | dev + 安全 | RBAC+ABAC + scope 命名 |
| [DATA-BOUNDARY.md](DATA-BOUNDARY.md) | 法务 + 安全 | 5 级分类 + 跨境 + PII |
| [AUDIT-LOG-SPEC.md](AUDIT-LOG-SPEC.md) | 安全 + 运维 | JSONL 字段 + replay |
| [TRUST-LEVELS.md](TRUST-LEVELS.md) | builder-hub maintainer | 三级矩阵 |
| `policy/*.yaml` | super_admin | 具体规则源 |
| [AI-ASSISTANT-PLAYBOOK.md](../../AI-ASSISTANT-PLAYBOOK.md) | 全员 | 整体方法论 |

## 九、版本

- 版本 1.0 — 2026-05-14 首次发布
- 适用 policy schema_version = 1
- 适用 backend governance 服务（`backend/src/services/governance/`）
