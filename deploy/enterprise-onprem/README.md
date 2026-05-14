# 企业私有化 / 内网部署（On-prem）

> 适用：政府 / 金融 / 大型律所 / 国央企等合规要求高、需要全栈在客户内网运行的场景。
> 关联设计：[docs/v3/enterprise-cluster-design.md §5](../../docs/v3/enterprise-cluster-design.md)

## 部署矩阵

| 场景 | 文件 | 主要差异 |
|---|---|---|
| **单机 all-in-one** | [`docker-compose.onprem.yml`](./docker-compose.onprem.yml) | 一台 host 包全栈，~8GB RAM |
| **K8s 多节点** | `helm/anxin-enterprise/`（P2 交付） | 高可用 / 水平扩展 |
| **离线 / 完全断网** | [`AIRGAP.md`](./AIRGAP.md) | 镜像离线导入 + 模型离线包 |

## 启动（all-in-one）

```bash
cp .env.onprem.example .env
docker compose -f deploy/enterprise-onprem/docker-compose.onprem.yml up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/migrate-user-department.py
```

## 关键差异 vs SaaS

- **数据库**：PostgreSQL **强制本地化**（不允许远端托管）
- **对象存储**：MinIO 私有桶；也可挂载 NFS / Ceph
- **LLM**：默认走 [本地推理网关](./AIRGAP.md#llm)，模型由客户自备
- **认证**：可对接 LDAP / AD / SAML —— 见 [`LDAP_SYNC.md`](./LDAP_SYNC.md) 与 [`SSO_SAML.md`](./SSO_SAML.md)
- **网络**：默认 backend 仅监听内网 IP；nginx 仅 80/443 对外
- **可观测性**：Prometheus + Grafana 默认启用，可对接客户自有 SOC

## 备份与运维

参见 [`BACKUP.md`](./BACKUP.md) —— 包含数据库、对象存储、Redis、组织目录的备份策略。
