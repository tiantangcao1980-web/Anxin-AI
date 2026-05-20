# -*- coding: utf-8 -*-
"""
LdapSyncService —— LDAP / AD 同步

设计见 docs/v3/enterprise-cluster-design.md §5.3 与
deploy/enterprise-onprem/LDAP_SYNC.md。

为了不强依赖 ``ldap3``，实际 LDAP I/O 由 ``LdapClient`` 协议封装：
    - 生产用 ``Ldap3Client`` 实装（lazy import ``ldap3``）
    - 测试可注入 ``InMemoryLdapClient``（无 LDAP 也能跑）

同步流程（每次 ``sync_once``）::

    1. 拉部门 OU 列表 → diff vs ``departments`` 表
       - 新增 / 更新 / 软删（消失的标记 is_active=False，ext_source='ldap'）
       - 重建 path（一次 build_tree）
    2. 拉用户列表 → diff vs ``users`` 表
       - 按 email 匹配；新邮箱 → 自动建 user
       - 已存在的 user：刷新 name / external_id（按 strategy）
       - 消失的 user → is_active=False
    3. 同步 user 所属 OU → ``department_memberships``（is_primary=True）
    4. 落 ``audit_log{event_type=ldap_sync}``
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Protocol
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enterprise_directory import Department, DepartmentMembership
from src.models.user import User

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LDAP client 协议（解耦 ldap3）
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class LdapDeptRecord:
    """LDAP 中的一个组织单元（OU）。"""

    dn: str                       # 完整 DN，"OU=后端组,OU=技术中心,DC=corp,DC=example"
    name: str                     # 简单名 (ou)
    parent_dn: str | None         # 父 OU 的 DN；None 表示根
    code: str | None = None       # 可选：description 字段


@dataclass(slots=True)
class LdapUserRecord:
    """LDAP 中的一个用户。"""

    dn: str                       # 完整 DN
    email: str                    # 主键
    name: str                     # displayName
    external_id: str              # uid / sAMAccountName
    department_dn: str | None     # 用户所在 OU 的 DN（可推断主部门）


class LdapClient(Protocol):
    """LDAP 拉取协议。"""

    def fetch_departments(self) -> list[LdapDeptRecord]: ...
    def fetch_users(self) -> list[LdapUserRecord]: ...


# ---------------------------------------------------------------------------
# 内存实现 —— 测试 / dry-run 时注入
# ---------------------------------------------------------------------------


class InMemoryLdapClient:
    """单测用，注入预置数据即可，无须真 LDAP server。"""

    def __init__(
        self,
        departments: list[LdapDeptRecord] | None = None,
        users: list[LdapUserRecord] | None = None,
    ) -> None:
        self._departments = list(departments or [])
        self._users = list(users or [])

    def fetch_departments(self) -> list[LdapDeptRecord]:
        return list(self._departments)

    def fetch_users(self) -> list[LdapUserRecord]:
        return list(self._users)


# ---------------------------------------------------------------------------
# 同步报告
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class LdapSyncReport:
    """每次同步返回的统计。"""

    org_id: str
    dry_run: bool
    departments_created: int = 0
    departments_updated: int = 0
    departments_deactivated: int = 0
    users_created: int = 0
    users_updated: int = 0
    users_deactivated: int = 0
    memberships_created: int = 0
    memberships_removed: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "org_id": self.org_id,
            "dry_run": self.dry_run,
            "departments_created": self.departments_created,
            "departments_updated": self.departments_updated,
            "departments_deactivated": self.departments_deactivated,
            "users_created": self.users_created,
            "users_updated": self.users_updated,
            "users_deactivated": self.users_deactivated,
            "memberships_created": self.memberships_created,
            "memberships_removed": self.memberships_removed,
            "errors": list(self.errors),
        }


# ---------------------------------------------------------------------------
# 服务
# ---------------------------------------------------------------------------


class LdapSyncService:
    """LDAP / AD → 本地企业目录同步。

    冲突策略由 ``conflict_strategy`` 控制：
        - ``ldap-wins``（默认）：本地非 LDAP 字段保留；LDAP 字段每次覆盖
        - ``local-wins``：仅在首次创建时写；之后不动
        - ``merge``：本期不实装，回退到 ldap-wins
    """

    EXT_SOURCE = "ldap"

    def __init__(
        self,
        session: AsyncSession,
        *,
        org_id: str,
        client: LdapClient,
        conflict_strategy: str = "ldap-wins",
        deactivate_missing: bool = True,
        default_user_role: str = "member",
        audit_hook: Any = None,  # callable(payload: dict) -> None
    ) -> None:
        if conflict_strategy not in {"ldap-wins", "local-wins", "merge"}:
            raise ValueError(f"未知 conflict_strategy: {conflict_strategy!r}")
        self.session = session
        self.org_id = org_id
        self.client = client
        self.conflict_strategy = conflict_strategy
        self.deactivate_missing = deactivate_missing
        self.default_user_role = default_user_role
        self.audit_hook = audit_hook

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def sync_once(self, *, dry_run: bool = False) -> LdapSyncReport:
        """跑一次全量同步。

        所有写库通过 session.flush（不 commit；commit 由调用方决定，便于测试回滚）。
        """
        report = LdapSyncReport(org_id=self.org_id, dry_run=dry_run)

        try:
            dept_records = self.client.fetch_departments()
        except Exception as exc:
            report.errors.append(f"fetch_departments 失败: {exc}")
            self._audit(report)
            return report

        try:
            user_records = self.client.fetch_users()
        except Exception as exc:
            report.errors.append(f"fetch_users 失败: {exc}")
            self._audit(report)
            return report

        # 1) 同步部门
        dn_to_dept = await self._sync_departments(dept_records, report, dry_run)

        # 2) 同步用户
        email_to_user = await self._sync_users(user_records, report, dry_run)

        # 3) 同步用户-部门关系（主部门）
        await self._sync_memberships(
            user_records,
            email_to_user,
            dn_to_dept,
            report,
            dry_run,
        )

        self._audit(report)
        return report

    # ------------------------------------------------------------------
    # 部门
    # ------------------------------------------------------------------

    async def _sync_departments(
        self,
        records: list[LdapDeptRecord],
        report: LdapSyncReport,
        dry_run: bool,
    ) -> dict[str, Department]:
        """同步部门，返回 ``{dn: Department}`` 映射，path 已重建。"""
        # 拉本地已有
        local = await self.session.execute(
            select(Department).where(Department.org_id == self.org_id)
        )
        by_external_id: dict[str, Department] = {}
        for d in local.scalars().all():
            if d.external_id:
                by_external_id[d.external_id] = d

        # 拓扑排序：父 OU 先处理
        records_sorted = sorted(records, key=lambda r: r.dn.count(","))
        dn_to_dept: dict[str, Department] = {}

        for rec in records_sorted:
            existing = by_external_id.get(rec.dn)
            parent = dn_to_dept.get(rec.parent_dn) if rec.parent_dn else None
            parent_path = (parent.path or f"/{parent.id}") if parent is not None else ""

            if existing is None:
                # 新建
                dept_id = str(uuid4())
                new_dept = Department(
                    id=dept_id,
                    org_id=self.org_id,
                    parent_id=parent.id if parent else None,
                    name=rec.name,
                    code=rec.code,
                    path=f"{parent_path}/{dept_id}" if parent_path else f"/{dept_id}",
                    is_active=True,
                    external_id=rec.dn,
                    ext_source=self.EXT_SOURCE,
                )
                if not dry_run:
                    self.session.add(new_dept)
                    await self.session.flush()
                by_external_id[rec.dn] = new_dept
                dn_to_dept[rec.dn] = new_dept
                report.departments_created += 1
            else:
                # 已存在：按策略更新
                dn_to_dept[rec.dn] = existing
                changed = False
                if self.conflict_strategy != "local-wins":
                    if existing.name != rec.name:
                        existing.name = rec.name
                        changed = True
                    if existing.code != rec.code:
                        existing.code = rec.code
                        changed = True
                    new_parent_id = parent.id if parent else None
                    if existing.parent_id != new_parent_id:
                        existing.parent_id = new_parent_id
                        existing.path = (
                            f"{parent_path}/{existing.id}"
                            if parent_path
                            else f"/{existing.id}"
                        )
                        changed = True
                # 复活
                if not existing.is_active:
                    existing.is_active = True
                    changed = True
                if changed:
                    if not dry_run:
                        await self.session.flush()
                    report.departments_updated += 1

        # 软删消失的部门
        if self.deactivate_missing:
            present = {r.dn for r in records}
            for dn, dept in list(by_external_id.items()):
                if dept.ext_source != self.EXT_SOURCE:
                    continue
                if dn not in present and dept.is_active:
                    dept.is_active = False
                    if not dry_run:
                        await self.session.flush()
                    report.departments_deactivated += 1

        return dn_to_dept

    # ------------------------------------------------------------------
    # 用户
    # ------------------------------------------------------------------

    async def _sync_users(
        self,
        records: list[LdapUserRecord],
        report: LdapSyncReport,
        dry_run: bool,
    ) -> dict[str, User]:
        """同步用户。返回 ``{email: User}``。

        强制 ``users.org_id == self.org_id``；跨租户的 email 冲突按策略：
        本期严格租户隔离 —— 若邮箱已在其它 org 存在，记 error，不动。
        """
        # 拉本地 org 内所有 user
        local = await self.session.execute(
            select(User).where(User.org_id == self.org_id)
        )
        by_email: dict[str, User] = {u.email: u for u in local.scalars().all()}

        # 跨租户冲突检测
        ldap_emails = {r.email for r in records}
        cross = await self.session.execute(
            select(User).where(
                User.email.in_(ldap_emails),
                User.org_id != self.org_id,
            )
        )
        cross_emails = {u.email for u in cross.scalars().all()}
        for e in cross_emails:
            report.errors.append(
                f"email={e} 已在其它租户存在，跳过同步以避免接管"
            )

        for rec in records:
            if rec.email in cross_emails:
                continue
            existing = by_email.get(rec.email)
            if existing is None:
                # 新建
                new_user = User(
                    id=str(uuid4()),
                    email=rec.email,
                    name=rec.name,
                    hashed_password="!ldap!",  # LDAP 用户走 bind，不走本地密码
                    org_id=self.org_id,
                    role=self.default_user_role,
                    is_active=True,
                    login_type="ldap",
                )
                # external_id 字段如果存在
                if hasattr(new_user, "external_id"):
                    setattr(new_user, "external_id", rec.external_id)
                if not dry_run:
                    self.session.add(new_user)
                    await self.session.flush()
                by_email[rec.email] = new_user
                report.users_created += 1
            else:
                # 更新
                changed = False
                if self.conflict_strategy != "local-wins":
                    if existing.name != rec.name:
                        existing.name = rec.name
                        changed = True
                if not existing.is_active:
                    existing.is_active = True
                    changed = True
                if changed:
                    if not dry_run:
                        await self.session.flush()
                    report.users_updated += 1

        # 消失的 LDAP 用户停用
        if self.deactivate_missing:
            ldap_present = {r.email for r in records}
            for email, user in list(by_email.items()):
                if user.login_type != "ldap":
                    continue
                if email not in ldap_present and user.is_active:
                    user.is_active = False
                    if not dry_run:
                        await self.session.flush()
                    report.users_deactivated += 1

        return by_email

    # ------------------------------------------------------------------
    # 用户 × 部门
    # ------------------------------------------------------------------

    async def _sync_memberships(
        self,
        records: list[LdapUserRecord],
        email_to_user: dict[str, User],
        dn_to_dept: dict[str, Department],
        report: LdapSyncReport,
        dry_run: bool,
    ) -> None:
        for rec in records:
            user = email_to_user.get(rec.email)
            if user is None:
                continue
            if not rec.department_dn:
                continue
            dept = dn_to_dept.get(rec.department_dn)
            if dept is None:
                report.errors.append(
                    f"user={rec.email} 引用未知 dept={rec.department_dn}"
                )
                continue

            # 找现有 membership
            existing = await self.session.execute(
                select(DepartmentMembership).where(
                    DepartmentMembership.user_id == user.id,
                    DepartmentMembership.department_id == dept.id,
                )
            )
            m = existing.scalar_one_or_none()
            if m is None:
                # 清掉旧的 is_primary（如果有别的）
                if not dry_run:
                    await self.session.execute(
                        update(DepartmentMembership)
                        .where(
                            DepartmentMembership.user_id == user.id,
                            DepartmentMembership.is_primary.is_(True),
                        )
                        .values(is_primary=False)
                    )
                if not dry_run:
                    self.session.add(
                        DepartmentMembership(
                            id=str(uuid4()),
                            user_id=user.id,
                            department_id=dept.id,
                            is_primary=True,
                            joined_at=datetime.now(timezone.utc),
                        )
                    )
                    await self.session.flush()
                report.memberships_created += 1

    # ------------------------------------------------------------------
    # 审计
    # ------------------------------------------------------------------

    def _audit(self, report: LdapSyncReport) -> None:
        if self.audit_hook is None:
            return
        try:
            self.audit_hook(report.as_dict())
        except Exception:
            logger.exception("ldap_sync audit_hook 失败")


# ---------------------------------------------------------------------------
# ldap3 真实装（lazy import）
# ---------------------------------------------------------------------------


class LdapNotAvailable(RuntimeError):
    """ldap3 库未安装或连接失败。"""


@dataclass(slots=True)
class Ldap3Config:
    url: str
    bind_dn: str
    bind_password: str
    user_base_dn: str
    dept_base_dn: str
    use_ssl: bool = True
    paged_size: int = 500


class Ldap3Client:
    """基于 ``ldap3`` 库的真实拉取客户端。

    生产部署时把 ``Ldap3Config`` 注入即可；本地无 ldap3 时仍可 import 本模块。
    """

    def __init__(self, config: Ldap3Config) -> None:
        self.config = config

    def _connect(self) -> Any:
        try:
            import ldap3
        except ImportError as exc:
            raise LdapNotAvailable(
                "需要安装 ldap3：pip install ldap3"
            ) from exc

        server = ldap3.Server(self.config.url, use_ssl=self.config.use_ssl)
        conn = ldap3.Connection(
            server,
            user=self.config.bind_dn,
            password=self.config.bind_password,
            auto_bind=True,
        )
        return conn

    def fetch_departments(self) -> list[LdapDeptRecord]:
        conn = self._connect()
        try:
            conn.search(
                self.config.dept_base_dn,
                "(objectClass=organizationalUnit)",
                attributes=["ou", "description"],
                paged_size=self.config.paged_size,
            )
            out: list[LdapDeptRecord] = []
            for entry in conn.entries:
                dn = str(entry.entry_dn)
                ou_val = (
                    entry.ou.value if "ou" in entry.entry_attributes else None
                )
                if not ou_val:
                    continue
                parent = self._parent_dn(dn)
                desc = (
                    entry.description.value
                    if "description" in entry.entry_attributes
                    else None
                )
                out.append(
                    LdapDeptRecord(
                        dn=dn,
                        name=str(ou_val),
                        parent_dn=parent if parent != self.config.dept_base_dn else None,
                        code=str(desc) if desc else None,
                    )
                )
            return out
        finally:
            try:
                conn.unbind()
            except Exception:
                pass

    def fetch_users(self) -> list[LdapUserRecord]:
        conn = self._connect()
        try:
            conn.search(
                self.config.user_base_dn,
                "(objectClass=person)",
                attributes=["mail", "displayName", "uid", "sAMAccountName"],
                paged_size=self.config.paged_size,
            )
            out: list[LdapUserRecord] = []
            for entry in conn.entries:
                attrs = entry.entry_attributes_as_dict
                email = attrs.get("mail", [None])[0]
                if not email:
                    continue
                name = (attrs.get("displayName") or [email])[0]
                ext_id = (
                    attrs.get("uid")
                    or attrs.get("sAMAccountName")
                    or [str(entry.entry_dn)]
                )[0]
                dn = str(entry.entry_dn)
                parent_dn = self._parent_dn(dn)
                out.append(
                    LdapUserRecord(
                        dn=dn,
                        email=email,
                        name=name,
                        external_id=str(ext_id),
                        department_dn=parent_dn,
                    )
                )
            return out
        finally:
            try:
                conn.unbind()
            except Exception:
                pass

    @staticmethod
    def _parent_dn(dn: str) -> str | None:
        """从 DN 取父 DN（去掉第一段 RDN）。"""
        if "," not in dn:
            return None
        return dn.split(",", 1)[1].strip()


__all__ = [
    "InMemoryLdapClient",
    "Ldap3Client",
    "Ldap3Config",
    "LdapClient",
    "LdapDeptRecord",
    "LdapNotAvailable",
    "LdapSyncReport",
    "LdapSyncService",
    "LdapUserRecord",
]
