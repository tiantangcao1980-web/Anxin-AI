# 数据库规范

> 强制规范。所有数据库 schema 变更、ORM 模型、查询代码必须遵守。

## 1. 数据库选型

| 类型 | 选型 | 用途 |
|---|---|---|
| 主关系库 | PostgreSQL 15+ | 业务数据 + 审计 |
| 缓存 / 任务队列 | Redis 7+ | 缓存 / Celery / 限流 |
| 向量库 | Qdrant 1.12.x（**锁定版本**） | RAG |
| 图数据库 | Neo4j 5.15+ | 知识图谱 |
| 对象存储 | MinIO（S3 兼容） | 文件 / 附件 |
| 桌面本地 | SQLCipher (SQLite + 加密) | 桌面端隔离 |

## 2. 表命名

| 规则 | 示例 |
|---|---|
| **snake_case 复数** | `users` `contracts` `case_events` |
| **关联表用 join 命名** | `user_roles` `case_documents` |
| **历史表加 `_history` 后缀** | `contract_history` |
| **审计表加 `_audit_log` 后缀** | `payment_audit_log` |
| **禁止**保留字 / 缩写 / 大写 | ❌ `User` `Tbl_Users` `usrs` |

## 3. 字段命名

| 规则 | 示例 |
|---|---|
| **snake_case** | `created_at` `user_id` `is_active` |
| **布尔字段加 `is_` / `has_` 前缀** | `is_deleted` `has_signature` |
| **时间字段统一 `_at` 后缀（datetime）** | `created_at` `updated_at` `deleted_at` `expires_at` |
| **日期字段用 `_date` 后缀** | `birth_date` |
| **外键统一 `<table_singular>_id`** | `user_id` `contract_id`（指 `users.id` / `contracts.id`） |
| **枚举字段用单数表意词** | `status` `payment_method`（不用 `payment_methods`） |
| **JSON 字段以 `_data` / `_config` / `_meta` 结尾** | `features_override` `provider_config` |

## 4. 必备字段（公共列）

所有业务表必须包含：

```python
class BaseModel:
    id: UUID = primary_key
    created_at: datetime = server_default(func.now())
    updated_at: datetime = onupdate(func.now())
    deleted_at: datetime | None = nullable  # 软删除
```

主键统一 UUID（`uuid.uuid4()`），**禁止**自增 INT 作主键（除非历史遗留）。

## 5. 索引

### 5.1 必须建索引的场景

- 外键（PG 不自动建）
- WHERE 高频字段
- ORDER BY 字段
- 复合查询用复合索引（最左前缀原则）

### 5.2 命名

| 索引类型 | 命名 |
|---|---|
| 单列 | `idx_<table>_<col>` |
| 复合 | `idx_<table>_<col1>_<col2>` |
| 唯一 | `uq_<table>_<col>` |
| 部分 | `idx_<table>_<col>_<condition>` |

### 5.3 例

```python
__table_args__ = (
    Index('idx_contracts_user_id', 'user_id'),
    Index('idx_contracts_status_created', 'status', 'created_at'),
    UniqueConstraint('email', name='uq_users_email'),
)
```

## 6. 外键

- **必须显式声明 ON DELETE / ON UPDATE 策略**
- 默认：`ON DELETE CASCADE`（业务子表）或 `ON DELETE SET NULL`（弱依赖）
- 跨域弱关联：禁止外键，业务层校验

## 7. SQLAlchemy ORM 规范

### 7.1 模型基类

```python
# backend/src/models/base.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
```

### 7.2 类名

| 规则 | 示例 |
|---|---|
| `PascalCase` 单数 | `class User(Base)` `class CaseEvent(Base)` |
| 关联表用 `XxxYyy` | `class UserRole(Base)` |

### 7.3 关系

```python
class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    user: Mapped["User"] = relationship(back_populates="contracts")
    clauses: Mapped[list["ContractClause"]] = relationship(cascade="all, delete-orphan")
```

### 7.4 查询规则

- **必须 `AsyncSession`**，禁止同步 Session 在 async 上下文
- **禁止 N+1**：用 `selectinload` / `joinedload`
- **不要遍历 + 单查询**：批量用 `IN` 或 `JOIN`
- **不允许字符串拼接 SQL**：参数化全用 SQLAlchemy expression

```python
# ❌ 禁止
result = await session.execute(text(f"SELECT * FROM users WHERE id={user_id}"))

# ✅ 正确
stmt = select(User).where(User.id == user_id)
result = await session.execute(stmt)
```

### 7.5 事务

```python
async with session.begin():
    session.add(contract)
    audit_log = AuditLog(...)
    session.add(audit_log)
# 自动 commit / rollback
```

**禁止**：业务路径中混合多个独立 session、跨函数传 session（用 dependency injection）。

## 8. Alembic 迁移规范

### 8.1 命名

`backend/alembic/versions/NNN_<topic>.py`

- `NNN` 三位数字递增
- `<topic>` snake_case 简短描述

```
028_add_agent_tasks_table.py
029_add_im_gateway_tables.py
030_add_app_authorization_tables.py
```

### 8.2 必须可逆

每个迁移必须实现 `upgrade()` + `downgrade()`：

```python
def upgrade():
    op.create_table(...)

def downgrade():
    op.drop_table('agent_tasks')
```

### 8.3 大变更分阶段

破坏性变更必须分 N 步：

1. 加新列（nullable）
2. 双写代码上线
3. 数据回填
4. 切读代码上线
5. 删旧列

**禁止**：单次 `ALTER COLUMN TYPE` / `DROP COLUMN`（除非小表）。

### 8.4 验证

```bash
cd backend
alembic upgrade head        # 应用
alembic downgrade -1        # 回滚一步验证可逆
alembic upgrade head        # 再前进
```

每次 autogenerate 必须**审查**版本文件（autogenerate 可能漏 enum / index）。

## 9. 多租户隔离

- 所有业务表必须有 `organization_id` 或 `tenant_id`
- 所有查询必须按 org 过滤（除非平台管理员）
- 查询入口统一在 service 层注入

```python
async def list_contracts(user: User, session: AsyncSession):
    stmt = select(Contract).where(Contract.organization_id == user.org_id)
    if user.role != Role.PLATFORM_ADMIN:
        stmt = stmt.where(Contract.created_by == user.id)
    return await session.execute(stmt)
```

## 10. 软删除

- 业务表用 `deleted_at` 软删除
- 查询默认过滤 `deleted_at IS NULL`（在 base query 加 filter）
- 真删用 cron 定期清理（保留 30 天）

## 11. 审计

- 关键操作（认证 / 支付 / 高风险）必须写 `audit_log`
- `audit_log` 不可修改、不可删除
- 字段：`actor_id` / `action` / `resource_type` / `resource_id` / `metadata` / `created_at`

## 12. 性能基线

- 单查询 < 100 ms（不含 LLM）
- 列表接口必须分页（默认 20，最大 100）
- 大表统计用预聚合 / 物化视图
- 写多读多场景考虑读副本

## 13. 监控

- 慢查询：> 1s 自动告警（Postgres `log_min_duration_statement`）
- 连接池：`asyncpg` `min_size=5 max_size=20`
- 死锁：日志 + Prometheus

## 14. Qdrant 向量库

| 项 | 规则 |
|---|---|
| 客户端版本 | 锁定 `qdrant-client>=1.12,<1.13` 与服务端 v1.12.1 对应 |
| Collection 命名 | `<purpose>_<lang>` 如 `legal_regulations_zh` |
| 向量维度 | 1024（text-embedding-v3） |
| top_k > 50 | 必须 rerank |
| 写入 | 必须带 `payload` 元数据（doc_id / source / version） |

## 15. Redis

- Key 命名：`<domain>:<purpose>:<id>` 如 `ratelimit:login:127.0.0.1`
- 必须设 TTL：避免内存膨胀
- 高频写场景考虑 Pipeline

## 16. 速查反例

```python
# ❌ 禁止 — 同步 Session
def get_user(db: Session, user_id):
    return db.query(User).filter(User.id == user_id).first()

# ✅ 正确 — async + select expression
async def get_user(session: AsyncSession, user_id: UUID) -> User | None:
    stmt = select(User).where(User.id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none()

# ❌ 禁止 — N+1
contracts = await session.execute(select(Contract))
for c in contracts.scalars():
    print(c.user.name)  # 每次都查 DB

# ✅ 正确 — eager load
contracts = await session.execute(
    select(Contract).options(selectinload(Contract.user))
)
```
