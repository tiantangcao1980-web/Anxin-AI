# 私有化备份策略

> 关联：[`README.md`](./README.md) · [`docker-compose.onprem.yml`](./docker-compose.onprem.yml)

## 备份内容

| 数据 | 卷 / 表 | 频率 | 保留 | 工具 |
|---|---|---|---|---|
| **PostgreSQL** 全库 | `./data/postgres` | 每日 02:00 | 30 天滚动 + 每月归档 | `pg_dump` |
| **组织目录**（关键，需独立逻辑备份） | `departments` / `department_memberships` / `role_bindings` 等 6 张表 | 每小时 | 7 天 | `pg_dump -t` |
| **MinIO** 对象存储 | `./data/minio` | 每日 03:00 | 30 天 | `mc mirror` 或 `restic` |
| **Redis** 持久化 | `./data/redis/appendonly.aof` | 每日 | 7 天 | `cp` |
| **审计日志** `audit_logs` | 表 | 每日 + 归档冷存 | **永久**（合规要求） | WAL 归档 + 离线介质 |
| **Skill 包** | `./data/skills` | 每周 | 永久 | tar + sha256 |

## pg_dump 模板

```bash
#!/bin/bash
set -euo pipefail
DATE=$(date +%Y%m%d-%H%M)
BACKUP_DIR=/backup/anxin/$DATE
mkdir -p $BACKUP_DIR

# 全库
docker compose exec -T postgres pg_dump -U anxin anxin_enterprise \
  | gzip > $BACKUP_DIR/full.sql.gz

# 组织目录（高频，仅热表）
docker compose exec -T postgres pg_dump -U anxin anxin_enterprise \
  -t departments -t department_memberships -t user_groups \
  -t user_group_members -t positions -t role_bindings \
  | gzip > $BACKUP_DIR/directory.sql.gz

sha256sum $BACKUP_DIR/*.gz > $BACKUP_DIR/SHA256SUMS
```

## 恢复

```bash
# 恢复全库
gunzip -c full.sql.gz | docker compose exec -T postgres psql -U anxin -d anxin_enterprise

# 只恢复组织目录（增量恢复）
docker compose exec -T postgres psql -U anxin -d anxin_enterprise -c \
  "TRUNCATE departments, department_memberships, role_bindings CASCADE;"
gunzip -c directory.sql.gz | docker compose exec -T postgres psql -U anxin -d anxin_enterprise
```

## 异地副本

- 内网 NAS / SAN：必备
- 物理介质（蓝光 / 磁带）：合规归档建议
- 跨数据中心：**不建议**走公网；用专线或物理搬运

## 验收清单

- [ ] 每周演练一次恢复（拉一个干净环境，把昨晚的 dump 还原）
- [ ] sha256 与原值一致
- [ ] 恢复后跑 `alembic current` 验证版本
- [ ] 跑 `python scripts/migrate-user-department.py --dry-run` 校验回填可重入
