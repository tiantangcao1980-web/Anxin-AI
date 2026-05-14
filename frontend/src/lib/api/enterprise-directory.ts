/**
 * Enterprise Directory API —— 部门 / 成员 / 角色绑定的 REST 包装
 *
 * 后端接口见 backend/src/api/routes/enterprise.py
 * 设计文档 docs/v3/enterprise-cluster-design.md §4
 */

import { API_BASE_URL } from '@/lib/api'

// ===== 数据模型 =====

export interface DepartmentNode {
  id: string
  name: string
  code: string | null
  parent_id: string | null
  path: string | null
  leader_id: string | null
  is_active: boolean
  order_idx: number
  children: DepartmentNode[]
}

export interface DepartmentDetail {
  id: string
  org_id: string
  parent_id: string | null
  name: string
  code: string | null
  path: string | null
  leader_id: string | null
  order_idx: number
  is_active: boolean
}

export interface MembershipRow {
  user_id: string
  department_id: string
  is_primary: boolean
  position_title: string | null
}

export interface RoleBindingRow {
  id: string
  org_id: string
  subject_type: 'user' | 'department' | 'group' | 'position'
  subject_id: string
  role: string
  scope_type: 'org' | 'department'
  scope_id: string
  is_active: boolean
  expires_at: string | null
  granted_at: string | null
  granted_by: string | null
  reason: string | null
}

export interface EffectivePermissions {
  user_id: string
  scope_type: string
  scope_id: string
  permissions: string[]
}

// ===== 内部 request helper（共享 token / 错误处理） =====

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token') || ''
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string> | undefined),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const resp = await fetch(`${API_BASE_URL}${path}`, { ...init, headers })
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`
    try {
      const body = await resp.json()
      detail = body.detail ?? body.message ?? JSON.stringify(body)
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  if (resp.status === 204) return undefined as unknown as T
  return (await resp.json()) as T
}

// ===== 部门 =====

export const enterpriseApi = {
  /** 拉部门树 */
  getTree: (orgId: string) =>
    request<DepartmentNode[]>(`/enterprise/organizations/${orgId}/tree`),

  createDepartment: (body: {
    name: string
    parent_id?: string | null
    code?: string | null
    leader_id?: string | null
    order_idx?: number
  }) =>
    request<DepartmentDetail>(`/enterprise/departments`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  updateDepartment: (
    deptId: string,
    body: { name?: string; parent_id?: string | null }
  ) =>
    request<DepartmentDetail>(`/enterprise/departments/${deptId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  deleteDepartment: (deptId: string) =>
    request<void>(`/enterprise/departments/${deptId}`, { method: 'DELETE' }),

  // 成员
  listMembers: (deptId: string) =>
    request<MembershipRow[]>(`/enterprise/departments/${deptId}/members`),

  addMember: (
    deptId: string,
    body: { user_id: string; is_primary?: boolean; position_title?: string | null }
  ) =>
    request<MembershipRow>(`/enterprise/departments/${deptId}/members`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  removeMember: (deptId: string, uid: string) =>
    request<void>(`/enterprise/departments/${deptId}/members/${uid}`, {
      method: 'DELETE',
    }),

  setPrimary: (deptId: string, uid: string) =>
    request<MembershipRow>(
      `/enterprise/departments/${deptId}/members/${uid}/primary`,
      { method: 'PUT' }
    ),

  // 角色绑定
  grantRole: (body: {
    subject_type: 'user' | 'department' | 'group' | 'position'
    subject_id: string
    role: string
    scope_type: 'org' | 'department'
    scope_id: string
    expires_at?: string | null
    reason?: string | null
  }) =>
    request<RoleBindingRow>(`/enterprise/role-bindings`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  revokeRole: (bindingId: string) =>
    request<void>(`/enterprise/role-bindings/${bindingId}`, {
      method: 'DELETE',
    }),

  effectivePermissions: (params: {
    uid: string
    scopeType: 'org' | 'department'
    scopeId: string
  }) =>
    request<EffectivePermissions>(
      `/enterprise/users/${params.uid}/effective-permissions?scope_type=${params.scopeType}&scope_id=${params.scopeId}`
    ),

  // LDAP 触发
  triggerLdapSync: (dryRun = false) =>
    request<Record<string, unknown>>(
      `/enterprise/ldap-sync/trigger?dry_run=${dryRun}`,
      { method: 'POST' }
    ),
}
