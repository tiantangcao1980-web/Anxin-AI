# LDAP / AD 同步规范

> 关联：[`docker-compose.onprem.yml`](./docker-compose.onprem.yml) (`ldap-sync` service) ·
> [docs/v3/enterprise-cluster-design.md §5.3](../../docs/v3/enterprise-cluster-design.md)

## 1. 用途

把客户内网 LDAP / Active Directory 里的 **用户** + **组织架构（OU 树）** 持续同步到本系统的 `users` + `departments` + `department_memberships`。

适用于：

- 客户拒绝在本系统手工创建用户（人事系统已是 LDAP 唯一真相源）
- 入离职流程要走 AD（停用 AD 账号 → 系统自动停用）
- 跨产品 SSO（同账号体系）

## 2. 数据流

```
  ┌─────────────────┐
  │ AD / OpenLDAP   │
  └────────┬────────┘
           │  (objectClass=person / organizationalUnit)
           ▼
  ┌─────────────────┐
  │  ldap-sync      │   每 LDAP_SYNC_INTERVAL_SEC 秒拉一次
  │  容器（cron）    │   diff 后写库 + audit_log
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ PostgreSQL      │   departments / department_memberships / users
  └─────────────────┘
```

## 3. 字段映射（默认值，可在 service 层覆盖）

| LDAP 属性 | 本系统字段 | 说明 |
|---|---|---|
| `mail` | `users.email` | 主键之一，必填 |
| `uid` / `sAMAccountName` | `users.external_id` | 反查用 |
| `displayName` | `users.name` | 显示名 |
| `ou` (parent) | `departments.path` 推断 | OU 树映射 |
| `objectClass=organizationalUnit`.`ou` | `departments.name` | |
| `objectClass=organizationalUnit`.`description` | `departments.code` | 若有 |
| LDAP DN | `users.external_id` / `departments.external_id` | 完整 DN 用于反查 |

**`ext_source` 字段固定 = `"ldap"`**，便于审计与回滚。

## 4. 冲突策略（按 org 配置）

| 策略 | 含义 |
|---|---|
| `ldap-wins`（默认） | LDAP 是唯一真相源；本地手动改动会被覆盖 |
| `local-wins` | LDAP 仅作首次导入；后续以本地为准 |
| `merge` | 字段级合并：LDAP 改了的字段同步，本地改了的字段保留 |

冲突 + 决策都写 `audit_log{event_type=ldap_sync}`，含 `before` / `after` 两个 JSON 快照。

## 5. 删除处理

LDAP 中 user / OU 消失时，系统**不真删**：

- `users.is_active = false`
- `departments.is_active = false`
- 关联 `department_memberships.left_at = now()`

如果后续 LDAP 又找回了同 DN，系统自动恢复 `is_active = true`。

## 6. 安全要求

1. `LDAP_BIND_PASSWORD` 走 ENV / secret，**禁止**进 git
2. 同步通道必须 `ldaps://` 或 STARTTLS
3. 同步过程产生的 LDIF / 中间文件存放在 `./data/ldap-sync/`，**仅 root 可读**
4. 日志默认脱敏（密码字段、token 字段）
5. 每次 sync 必须落 `audit_log`，含计数和异常 DN 列表

## 7. 故障排查

| 现象 | 排查 |
|---|---|
| 同步容器 CrashLoop | `docker compose logs ldap-sync` |
| 用户没创建 | 看 `audit_log` 里 `event_type=ldap_sync` 的 `errors` 字段 |
| 部门树不对 | 用 `python scripts/ldap_sync_loop.py --dry-run --once` 看预览 |
| 性能不行 | 增大 `LDAP_SYNC_INTERVAL_SEC`，或调小 LDAP `paged size` |

## 8. 路线图

- **P1**（当前）：本规范 + compose service 占位 + audit_log 落库
- **P2**：`scripts/ldap_sync_loop.py` 真实装（基于 `ldap3` 库）
- **P3**：飞书 / 钉钉 / 企业微信 通讯录同步（同抽象）
- **P4**：SCIM 2.0 接收端（IdP push 而非 pull）
