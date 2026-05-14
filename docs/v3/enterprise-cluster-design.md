# 企业内网集群（组织 / 部门 / 成员 / 权限继承）设计

> 文档状态：**Draft v1**（2026-05-14）
> 关联：[architecture.md](./architecture.md) · `backend/src/core/deps.py` · `backend/src/models/user.py`
> 责任人：Backend Platform

> 注：本文「集群」语义对齐**飞书 / 企业微信**等内部协同产品 —— **企业（租户）→ 部门 → 成员 → 角色 → 权限**的层级模型，以及内网 / 私有化部署模式。**不**指分布式计算集群（那部分参见 `architecture.md §扩展性`）。

## 1. 现状 & 缺口

现状（见 `core/deps.py` + `models/user.py`）：

- `User.role`（9 种角色 enum）、`User.department`（**字符串字段，无表**）、`User.org_id` → `Organization`
- `Organization` 只有 name/description/logo —— **没有部门、组、岗位**
- `ROLE_PERMISSIONS` 静态字典做角色→权限映射 —— **不支持跨部门、不支持单点临时授权**
- `TenantContext` 仅捕获 `org_id`

缺口：

1. **部门树**（树形 + 跨部门）
2. **成员关系**（一个用户可同时属于多个部门，有"主部门"概念）
3. **角色绑定的作用域**（平台 / 企业 / 部门 / 用户）
4. **权限继承**（部门 → 子部门、企业 → 部门 → 用户）
5. **岗位（Position）/ 用户组（UserGroup）**（飞书的"自定义群体"，跨部门授权常用）
6. **私有化 / 内网部署** 规范（LDAP 同步、SSO、组织数据导入导出）

## 2. 领域模型

### 2.1 ER 概念图

```
Organization (企业/租户) ─┐
       │                  │ 1:N
       │ 1:N              ▼
       │            Department (部门，树形 parent_id)
       │                  │ M:N
       │                  ▼
       └──► User ◄──► Membership ◄──► Department
                          │
                          ▼
                    PositionAssignment
                          │
                          ▼
                       Position (岗位)
                          │
                          ▼
                    RoleBinding (主体 × 角色 × 作用域)
                          │
                          ▼
                       Role + Permission

UserGroup (自定义群体) ─M:N─ User
       │
       └─ 可被 RoleBinding 作为主体
```

### 2.2 表结构（PostgreSQL，沿用 `GUID` + TimestampMixin）

```sql
-- 已有：organizations(id, name, description, logo_url, is_active, ...)
-- 已有：users(id, org_id, role, department[字符串], ...)

-- 新增 1: 部门
CREATE TABLE departments (
  id            UUID PRIMARY KEY,
  org_id        UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  parent_id     UUID REFERENCES departments(id) ON DELETE CASCADE,
  name          VARCHAR(200) NOT NULL,
  code          VARCHAR(100),           -- 同 org 内唯一，便于 LDAP/SCIM 同步
  path          VARCHAR(1024),          -- "/root/技术中心/后端组"，触发器维护
  order_idx     INT DEFAULT 0,
  leader_id     UUID REFERENCES users(id),
  is_active     BOOLEAN DEFAULT TRUE,
  external_id   VARCHAR(200),           -- 来自 LDAP/飞书/钉钉同步
  ext_source    VARCHAR(50),            -- 'ldap' | 'feishu' | 'dingtalk' | 'manual'
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (org_id, code)
);
CREATE INDEX idx_departments_org_parent ON departments(org_id, parent_id);
CREATE INDEX idx_departments_path ON departments(path text_pattern_ops);

-- 新增 2: 成员-部门关系（一人多部门）
CREATE TABLE department_memberships (
  id              UUID PRIMARY KEY,
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  department_id   UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
  is_primary      BOOLEAN DEFAULT FALSE,    -- 主部门：组织架构页面显示
  position_title  VARCHAR(200),             -- "高级法务"等字面岗位
  joined_at       TIMESTAMPTZ DEFAULT NOW(),
  left_at         TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (user_id, department_id)
);
CREATE INDEX idx_dept_memberships_user ON department_memberships(user_id);
CREATE INDEX idx_dept_memberships_dept ON department_memberships(department_id);

-- 新增 3: 用户组（飞书"群体"）
CREATE TABLE user_groups (
  id            UUID PRIMARY KEY,
  org_id        UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name          VARCHAR(200) NOT NULL,
  description   TEXT,
  group_type    VARCHAR(50) DEFAULT 'static',   -- static | dynamic
  rule          JSONB,                          -- dynamic 时的过滤规则
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (org_id, name)
);

CREATE TABLE user_group_members (
  group_id      UUID NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  joined_at     TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (group_id, user_id)
);

-- 新增 4: 岗位（可选，用于"研发-后端-P6"型职级体系）
CREATE TABLE positions (
  id            UUID PRIMARY KEY,
  org_id        UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name          VARCHAR(200) NOT NULL,
  code          VARCHAR(100),
  level         INT DEFAULT 0,
  description   TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (org_id, code)
);

-- 新增 5: 角色绑定（核心 —— 主体 × 角色 × 作用域）
CREATE TABLE role_bindings (
  id              UUID PRIMARY KEY,
  org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  -- 主体
  subject_type    VARCHAR(20) NOT NULL,   -- 'user' | 'department' | 'group' | 'position'
  subject_id      UUID NOT NULL,
  -- 角色（沿用 UserRole 字符串）
  role            VARCHAR(50) NOT NULL,
  -- 作用域
  scope_type      VARCHAR(20) NOT NULL,   -- 'org' | 'department'
  scope_id        UUID NOT NULL,          -- org_id 或 department_id
  -- 生命周期
  granted_by      UUID REFERENCES users(id),
  granted_at      TIMESTAMPTZ DEFAULT NOW(),
  expires_at      TIMESTAMPTZ,            -- 临时授权
  is_active       BOOLEAN DEFAULT TRUE,
  reason          TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (subject_type, subject_id, role, scope_type, scope_id)
);
CREATE INDEX idx_role_bindings_subject ON role_bindings(subject_type, subject_id);
CREATE INDEX idx_role_bindings_scope ON role_bindings(scope_type, scope_id);
```

> 在 `User.department` 字符串字段不删除（向后兼容），但视为 deprecated；通过迁移把现有字符串映射成 `department_memberships`。

### 2.3 路径（path）维护

部门树深度通常 ≤ 6 层；用 **materialized path**（`/root_id/.../dept_id`）方便：

- 后代查询：`WHERE path LIKE '/r/p/d/%'`
- 上溯：split path 后逐级 `IN`
- 移动：父节点变更时批量 update children 的 path

触发器/Service 任选；本期由 Service 层维护（简单可控）。

## 3. 权限解析（核心算法）

### 3.1 概念

**有效权限（effective_permissions）= 用户在某一作用域下能行使的全部 Permission 集合**。计算时遵循：

```
effective(user, scope=dept_d) =
   ROLE_PERMISSIONS[user.role]                                   # 兼容旧字段（fallback）
 ∪ Σ ROLE_PERMISSIONS[r] for r in role_bindings(user, scope=dept_d 及其祖先)
 ∪ Σ ROLE_PERMISSIONS[r] for r in role_bindings(user_groups(user), scope ⊇ dept_d)
 ∪ Σ ROLE_PERMISSIONS[r] for r in role_bindings(user_departments(user), scope ⊇ dept_d)
```

**继承方向**：父部门的角色绑定**向下继承**到所有后代部门；反之不成立。

**显式 deny**：本期不实现 deny-list；如确需收紧权限，应**降低角色**或**移出部门**，避免双重否定语义。

### 3.2 服务层

新建 `backend/src/services/enterprise_directory/`：

```
enterprise_directory/
├── __init__.py
├── models.py             # Pydantic DTO
├── department_service.py # CRUD + 树维护
├── membership_service.py # 加入/移出部门、主部门切换
├── group_service.py      # UserGroup CRUD
├── role_binding_service.py
├── permission_resolver.py  # ★ 核心：effective_permissions(user, scope)
└── ldap_sync.py          # P2：LDAP / SCIM 同步
```

`permission_resolver.resolve(user, scope) -> set[Permission]`：

1. 取 `user.role` 的静态权限（旧 fallback）
2. 查询 `role_bindings` where subject ∈ {user, user 所属部门链, user 所属群组}
3. 过滤 `scope` 在绑定 `scope_type/scope_id` 之下（部门祖先视为有效）
4. 过滤 `is_active AND (expires_at IS NULL OR expires_at > now())`
5. 把命中的所有 role 通过 `ROLE_PERMISSIONS` 展开后并集
6. **缓存 30s**：(user_id, scope_id) → set —— Redis；user 变更/绑定变更时 invalidate

### 3.3 FastAPI 依赖适配

新增 `core/deps.py` 函数（不破坏现有 `require_permission`）：

```python
def require_permission_in_scope(
    *permissions: Permission,
    scope: ScopeLocator,   # 'org' / 'department:{id}' / 'self'
) -> UserDependency:
    """带作用域的权限检查，例如：
       require_permission_in_scope(Permission.WRITE_CASES, scope=Path("department_id"))
    """
```

旧 `require_permission` 在 scope 缺省时**等价于 `scope=org`**，向后兼容。

## 4. API 设计

```
GET    /api/v1/enterprise/organizations/{org_id}                 # 组织详情
GET    /api/v1/enterprise/organizations/{org_id}/tree            # 部门树
POST   /api/v1/enterprise/departments                            # 创建部门
PATCH  /api/v1/enterprise/departments/{dept_id}                  # 改名/移动
DELETE /api/v1/enterprise/departments/{dept_id}                  # 软删
GET    /api/v1/enterprise/departments/{dept_id}/members          # 成员列表

POST   /api/v1/enterprise/departments/{dept_id}/members          # 加入部门
DELETE /api/v1/enterprise/departments/{dept_id}/members/{uid}    # 移出
PUT    /api/v1/enterprise/departments/{dept_id}/members/{uid}/primary  # 设为主部门

POST   /api/v1/enterprise/groups                                 # 用户组 CRUD
POST   /api/v1/enterprise/groups/{gid}/members
DELETE /api/v1/enterprise/groups/{gid}/members/{uid}

POST   /api/v1/enterprise/role-bindings                          # 授权
DELETE /api/v1/enterprise/role-bindings/{id}                     # 撤回
GET    /api/v1/enterprise/role-bindings?subject=...&scope=...    # 查询

GET    /api/v1/enterprise/users/{uid}/effective-permissions?scope=...  # 调试 / 审计
```

权限要求：除查询 `tree` / 自己的 `effective-permissions` 外，全部需要 `ORG_ADMIN` 或 `MANAGE_ORGANIZATION`。

## 5. 私有化 / 内网部署

### 5.1 部署模式

| 模式 | 适用场景 | 关键差异 |
|---|---|---|
| **公有云租户** | 默认 SaaS | 多租户共享 PostgreSQL + Redis，按 `org_id` 行级隔离 |
| **专属云租户** | 大客户 | 独立 schema，但 control plane 共享 |
| **私有化 / 内网** | 政府 / 金融 / 律所合规 | 全栈在客户内网；可选断网 |
| **混合 / NAS** | 单律所 | 已有 `docker-compose.nas.yml`，部署到 NAS 私有节点 |

### 5.2 内网部署清单

[`deploy/enterprise-onprem/`](../../deploy/enterprise-onprem/) 已交付：

- [`docker-compose.onprem.yml`](../../deploy/enterprise-onprem/docker-compose.onprem.yml)：单 host all-in-one
- [`.env.onprem.example`](../../deploy/enterprise-onprem/.env.onprem.example)：环境变量模板
- [`LDAP_SYNC.md`](../../deploy/enterprise-onprem/LDAP_SYNC.md)：OpenLDAP / AD 同步规范
- [`SSO_SAML.md`](../../deploy/enterprise-onprem/SSO_SAML.md)：SAML / OIDC / 飞书钉钉单点接入
- [`BACKUP.md`](../../deploy/enterprise-onprem/BACKUP.md)：组织目录 / role_bindings 定期 dump
- [`AIRGAP.md`](../../deploy/enterprise-onprem/AIRGAP.md)：完全离线场景
- `helm/anxin-enterprise/`：K8s Helm chart（P2 交付）

### 5.3 LDAP / SCIM 同步规范

1. **入口**：cron 每 5 min 拉 LDAP `(objectClass=person)` + 部门 `(objectClass=organizationalUnit)`
2. **映射**：`ou` → `Department`，`uid` / `mail` → `User`
3. **冲突策略**：本地优先 / LDAP 优先 由 org 配置；删除标记 soft-delete（不真删）
4. **审计**：每次 sync 写 `audit_log{event_type=ldap_sync}`，记录 added/updated/deleted 计数

### 5.4 数据隔离强约束

- **所有租户表必须含 `org_id`** —— 已用 `tenant_id` / `org_id` 命名规范
- ORM 层加 **强制 filter**：`select().where(Model.org_id == ctx.org_id)`，缺失时 unit test 失败
- 跨租户访问 = 越权，**必须**经过 `super_admin` + audit_log 双重记录

## 6. 与现有 `Team` / `firm_management` 的关系

`firm_management.Team` 当前用于"律所内项目团队"语义（短期、动态组合），与本设计的"部门"（长期组织架构）正交：

- **Department**：人事意义上的归属，对接 HR、考勤、汇报线
- **Team**：业务意义上的临时组合（如"XX 案件项目组"）

→ **Team 通过 `RoleBinding.subject_type='group'` + 后续把 Team 视作动态 UserGroup**，复用同一套权限解析。本期不强制改 Team 表结构，作为 P2 收敛。

## 7. 缓存与一致性

| 数据 | TTL | invalidate 触发 |
|---|---|---|
| `permission_resolver` 结果 | 30s | role_binding / membership / user.role 变更 |
| 部门树 | 5 min | dept 增删改 |
| 用户组成员列表 | 1 min | group / member 变更 |

invalidate 走 `event_bus` Pub/Sub —— 多 worker 一致。

## 8. 迁移与回填

- **DB**：Alembic migration `xxxx_enterprise_directory.py`（新建 5 张表）
- **回填脚本** `scripts/migrate-user-department.py`：扫 `users.department` 字符串字段 → 自动建 `Department` + `department_memberships`
- **回退**：保留 `users.department` 字段 1 个版本（v3.1 删除）

## 9. 路线图

| 阶段 | 里程碑 | 交付 |
|---|---|---|
| **P1**（本期） | 模型 + 解析器 + API + 单测 | 5 张表 / DepartmentService / PermissionResolver / 接口 + 单测 |
| **P2** | LDAP / AD 同步 | `ldap_sync.py` + cron + 审计 |
| **P3** | SAML / OAuth SSO + 飞书/钉钉单点 | 复用 [auth-tool] |
| **P4** | 自定义群体动态规则 | `user_groups.group_type=dynamic` + rule DSL |
| **P5** | UI 组织架构图 | apps/web 管理后台 |

## 10. 安全核对清单

- [ ] 所有新表都带 `org_id` 且建立索引
- [ ] permission_resolver 默认 fail-closed
- [ ] 跨租户查询是否在 ORM 层有强制 guard（grep test）
- [ ] LDAP 同步密码字段是否在日志里被脱敏
- [ ] 角色绑定过期是否被解析器尊重（`expires_at`）
- [ ] role-binding 审计是否记录 granted_by + reason

---

**附录 A：与 `core/deps.UserRole` 的关系**

本设计**不替换**现有 `UserRole` 枚举与 `ROLE_PERMISSIONS` 静态映射；它把这些角色作为**绑定结果**的字符串，挂在 `role_bindings.role` 字段上。这样可以：

- 平滑迁移：旧代码继续读 `user.role`（视为"在 org 作用域的默认角色绑定"）
- 灵活扩展：新角色可以只在数据库里出现，不需要立刻动 enum（待沉淀后再固化）

**附录 B：与隐私 / 数据分级的关系**

`security_config` 中的数据分级（PUBLIC..TOP_SECRET）独立于本设计；权限解析器只决定"用户能不能做"，分级决定"做的对象敏不敏感"。两者在 `CapabilityPolicyEngine` 的同一次决策中各占一项。
