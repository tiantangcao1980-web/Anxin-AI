# -*- coding: utf-8 -*-
"""
enterprise_directory —— 企业内网集群服务层

设计见 docs/v3/enterprise-cluster-design.md §3。

公开 API：
    - DepartmentService     : 部门 CRUD + 树维护
    - MembershipService     : 成员-部门关系管理
    - RoleBindingService    : 角色绑定 CRUD + 过期判断
    - PermissionResolver    : ★ 核心 —— 计算用户在某作用域下的有效权限
    - ScopeLocator          : 作用域定位 DTO
"""

from src.services.enterprise_directory.department_service import (
    DepartmentNotFoundError,
    DepartmentService,
)
from src.services.enterprise_directory.im_directory_clients import (
    DingtalkConfig,
    DingtalkDirectoryClient,
    FeishuConfig,
    FeishuDirectoryClient,
    ImDirectoryUnavailable,
    WecomConfig,
    WecomDirectoryClient,
)
from src.services.enterprise_directory.ldap_sync import (
    InMemoryLdapClient,
    Ldap3Client,
    Ldap3Config,
    LdapClient,
    LdapDeptRecord,
    LdapNotAvailable,
    LdapSyncReport,
    LdapSyncService,
    LdapUserRecord,
)
from src.services.enterprise_directory.membership_service import MembershipService
from src.services.enterprise_directory.permission_resolver import (
    PermissionResolver,
    ScopeLocator,
)
from src.services.enterprise_directory.role_binding_service import (
    RoleBindingService,
    ScopeType,
    SubjectType,
)

__all__ = [
    "DepartmentNotFoundError",
    "DepartmentService",
    "DingtalkConfig",
    "DingtalkDirectoryClient",
    "FeishuConfig",
    "FeishuDirectoryClient",
    "ImDirectoryUnavailable",
    "InMemoryLdapClient",
    "Ldap3Client",
    "Ldap3Config",
    "LdapClient",
    "LdapDeptRecord",
    "LdapNotAvailable",
    "LdapSyncReport",
    "LdapSyncService",
    "LdapUserRecord",
    "MembershipService",
    "PermissionResolver",
    "RoleBindingService",
    "ScopeLocator",
    "ScopeType",
    "SubjectType",
    "WecomConfig",
    "WecomDirectoryClient",
]
