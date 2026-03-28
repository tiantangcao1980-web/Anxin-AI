/**
 * usePermission — 前端权限控制 Hook
 *
 * 基于用户角色判断功能可见性和操作权限
 * 配合 FeatureFlags 实现功能开关控制
 */

import { useMemo } from 'react';
import { useAuthStore } from '@/lib/store';

// ===== 用户角色定义（与后端 UserRole 对应）=====
export type UserRole =
  | 'super_admin'
  | 'admin'
  | 'org_admin'
  | 'dept_admin'
  | 'partner'
  | 'lawyer'
  | 'paralegal'
  | 'enterprise_user'
  | 'individual_user'
  | 'platform_lawyer'
  | 'member'    // 兼容旧角色
  | 'client'    // 兼容旧角色
  | 'viewer';

// ===== 功能开关状态 =====
export type FeatureStatus = 'hidden' | 'coming_soon' | 'beta' | 'released';

// ===== 功能开关配置 =====
export const FEATURE_FLAGS: Record<string, FeatureStatus> = {
  // 已上线
  ai_chat: 'released',
  contract_review: 'released',
  contract_management: 'released',
  case_management: 'released',
  knowledge_base: 'released',
  document_management: 'released',
  dashboard: 'released',
  due_diligence: 'released',
  news: 'released',
  search: 'released',
  knowledge_graph: 'released',
  academy: 'released',
  experts: 'released',
  leads: 'released',
  collaboration: 'released',
  settings: 'released',

  // Beta
  admin_panel: 'beta',
  approval_workflow: 'beta',
  tasks: 'released',

  // 开发中
  compliance_check: 'released',
  lawyer_matching: 'beta',
  lawyer_onboarding: 'beta',
  lawyer_dashboard: 'beta',
  pricing: 'released',
  my_subscription: 'released',
  customer_acquisition: 'beta',
  collaboration_groups: 'hidden',
  private_deployment: 'released',
  im_messaging: 'beta',
  mini_program: 'hidden',
  billing: 'beta',
  firm_management: 'beta',
  feature_flags_admin: 'beta',
};

// ===== 角色层级（用于判断管理权限）=====
const ADMIN_ROLES: Set<UserRole> = new Set([
  'super_admin', 'admin', 'org_admin',
]);

const MANAGEMENT_ROLES: Set<UserRole> = new Set([
  'super_admin', 'admin', 'org_admin', 'dept_admin', 'partner',
]);

const LAWYER_ROLES: Set<UserRole> = new Set([
  'partner', 'lawyer', 'paralegal', 'platform_lawyer',
]);

// ===== 功能-角色可见性矩阵 =====
const FEATURE_VISIBILITY: Record<string, Set<UserRole> | 'all'> = {
  ai_chat: 'all',
  contract_review: 'all',
  dashboard: new Set([
    'super_admin', 'admin', 'org_admin', 'dept_admin', 'partner', 'lawyer',
    'paralegal', 'enterprise_user', 'member',
  ]),
  case_management: new Set([
    'super_admin', 'admin', 'org_admin', 'dept_admin', 'partner', 'lawyer',
    'paralegal', 'enterprise_user', 'platform_lawyer', 'member',
  ]),
  admin_panel: ADMIN_ROLES,
  approval_workflow: new Set([
    'super_admin', 'admin', 'org_admin', 'dept_admin', 'partner', 'lawyer',
    'paralegal', 'enterprise_user', 'member',
  ]),
  lawyer_matching: new Set([
    'super_admin', 'admin', 'org_admin', 'enterprise_user', 'individual_user',
    'client', 'member',
  ]),
  leads: new Set([
    'super_admin', 'admin', 'org_admin', 'partner', 'lawyer', 'platform_lawyer',
  ]),
  experts: new Set([
    'super_admin', 'admin', 'org_admin', 'partner', 'lawyer', 'enterprise_user',
    'member',
  ]),
};

// ===== Hook =====
export function usePermission() {
  const { user } = useAuthStore();
  const role = (user?.role || 'viewer') as UserRole;

  return useMemo(() => ({
    role,
    isAdmin: ADMIN_ROLES.has(role),
    isManagement: MANAGEMENT_ROLES.has(role),
    isLawyer: LAWYER_ROLES.has(role),

    /** 检查用户是否可以看到某个功能 */
    canAccess(feature: string): boolean {
      // 功能开关检查
      const status = FEATURE_FLAGS[feature];
      if (!status || status === 'hidden') return false;

      // 角色可见性检查
      const visibility = FEATURE_VISIBILITY[feature];
      if (!visibility) return true; // 未配置的功能默认可见
      if (visibility === 'all') return true;
      return visibility.has(role);
    },

    /** 获取功能状态标签 */
    getFeatureStatus(feature: string): FeatureStatus {
      return FEATURE_FLAGS[feature] || 'hidden';
    },

    /** 检查是否有特定权限（简化版，完整版由后端控制） */
    hasPermission(permission: string): boolean {
      if (ADMIN_ROLES.has(role)) return true;
      // 前端做粗粒度判断，细粒度由后端 API 控制
      return true;
    },
  }), [role]);
}

export default usePermission;
