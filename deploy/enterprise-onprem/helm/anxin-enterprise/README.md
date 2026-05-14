# anxin-enterprise · Helm Chart

> 私有化 / 内网 K8s 部署 chart。配套设计：[docs/v3/enterprise-cluster-design.md §5](../../../../docs/v3/enterprise-cluster-design.md) + [deploy/enterprise-onprem/README.md](../../README.md)。

## 包含资源

- `backend-deployment.yaml` —— FastAPI 主服务 (Deployment + Service)
- `worker-deployment.yaml` —— Celery worker
- `postgres.yaml` —— in-cluster PostgreSQL StatefulSet（可关闭，改用外部）
- `redis.yaml` —— in-cluster Redis（可关闭，改用外部）
- `ldap-sync-cronjob.yaml` —— LDAP / AD 周期同步（K8s 原生 CronJob，默认关闭）
- `ingress.yaml` —— Ingress 入口
- `networkpolicy.yaml` —— default-deny + 白名单（默认关闭）
- `secret.yaml` —— 数据库 / Redis / JWT / Skill 签名公钥 / LDAP 绑定密码

## 快速开始

```bash
# Lint
helm lint deploy/enterprise-onprem/helm/anxin-enterprise

# Dry-run 渲染
helm template anxin deploy/enterprise-onprem/helm/anxin-enterprise \
  --set postgres.password=replace-me \
  --set redis.password=replace-me \
  --set backend.jwtSecret=$(openssl rand -base64 32) \
  --set backend.secretKey=$(openssl rand -base64 32)

# 安装
helm install anxin deploy/enterprise-onprem/helm/anxin-enterprise \
  --namespace anxin --create-namespace \
  -f my-values.yaml
```

建议把 secrets 放在 `my-values.yaml` 或外部 Secret Manager（Sealed Secrets / External Secrets Operator）注入。

## 升级路径

```bash
helm upgrade anxin deploy/enterprise-onprem/helm/anxin-enterprise \
  --namespace anxin -f my-values.yaml \
  --atomic --timeout 5m

# 执行 alembic 迁移（Job 形式）
kubectl exec -n anxin deploy/anxin-backend -- alembic upgrade head

# 回填脚本（首次升级到 045 之后）
kubectl exec -n anxin deploy/anxin-backend -- python scripts/migrate-user-department.py
```

## 关键安全默认

- `AUTH_REDIS_FAIL_CLOSED=true` —— Redis 不可用时认证接口直接 503
- `runAsNonRoot=true` / `runAsUser=65534` —— Pod 以 nobody 运行
- `capabilities.drop=ALL` —— 容器无任何 Linux capability
- `allowPrivilegeEscalation=false` —— 与 Skill 沙箱 T3 默认对齐
- `networkPolicy` 模板就绪 —— 启用后 default-deny + 仅放行 ingress 与同 ns 后端依赖

## 与 docker-compose 的关系

`docker-compose.onprem.yml` 适合**单 host all-in-one**，Helm chart 适合**多节点 + 高可用**。两者读取的环境变量名一致，可平滑过渡。

## 待补（P2+）

- HPA / VPA（按 CPU、QPS 自动扩缩）
- ServiceMonitor → Prometheus（待 observability operator 接入）
- MinIO StatefulSet（当前 values 占位但未渲染）
- 备份 CronJob（`pg_dump` 自动归档到对象存储）
- T4 Skill 沙箱专属 Worker 池
