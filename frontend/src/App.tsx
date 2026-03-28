/**
 * App.tsx - 应用根组件与路由配置
 *
 * ===== [Phase 1] 移除废弃模块 =====
 * 删除了 PRD 不需要的页面：TaxAssets、Sentiment、LegalTools
 * 合同审查已合并到合同管理，智能文档和智能中台已整合到在线协作
 *
 * ===== [Phase 2] 路由懒加载 + 四大业务域路由结构 =====
 * 使用 React.lazy() + Suspense 实现按需加载，减少首屏 bundle 体积
 * 路由按 PRD 四大业务域分组：AI法务、智能协作、信息中心、法律智库
 *
 * ===== [Phase 3] ErrorBoundary + 404 页面 =====
 * 添加全局错误边界，防止子组件崩溃导致白屏
 * 添加 404 兜底路由
 */

import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import Layout from '@/components/Layout'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { PageSkeleton } from '@/components/PageSkeleton'
import { PrivacyProvider } from '@/context/PrivacyContext'
import { ThemeProvider } from '@/components/ThemeProvider'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { AdminRoute } from '@/components/auth/AdminRoute'

// ===== 路由懒加载 =====
// 每个页面只在用户访问时才加载对应的 JS 代码
// 特别是 Knowledge（含 three.js 3D 图形库）和 Collaboration（含 tiptap/yjs）等重型页面

// AI法务
const Chat = lazy(() => import('@/pages/Chat'))

// 智能协作
const Cases = lazy(() => import('@/pages/Cases'))
const CaseDetail = lazy(() => import('@/pages/CaseDetail'))
const Contracts = lazy(() => import('@/pages/Contracts'))
const Collaboration = lazy(() => import('@/pages/Collaboration'))
const Leads = lazy(() => import('@/pages/Leads'))

// 信息中心
const News = lazy(() => import('@/pages/News'))
const DueDiligence = lazy(() => import('@/pages/DueDiligence'))

// 法律智库
const Search = lazy(() => import('@/pages/Search'))
const KnowledgeGraph = lazy(() => import('@/pages/KnowledgeGraph'))
const KnowledgeBase = lazy(() => import('@/pages/KnowledgeBase'))
const Academy = lazy(() => import('@/pages/Academy'))

// 系统
const Settings = lazy(() => import('@/pages/Settings'))
const Tasks = lazy(() => import('@/pages/Tasks'))
const Approvals = lazy(() => import('@/pages/Approvals'))
const FindLawyer = lazy(() => import('@/pages/FindLawyer'))
const ComplianceCheck = lazy(() => import('@/pages/ComplianceCheck'))
const Messages = lazy(() => import('@/pages/Messages'))
const LawyerProfile = lazy(() => import('@/pages/LawyerProfile'))
const AcquisitionDashboard = lazy(() => import('@/pages/AcquisitionDashboard'))
const FirmManagement = lazy(() => import('@/pages/FirmManagement'))
const NotFound = lazy(() => import('@/pages/NotFound'))

// 登录页
const Login = lazy(() => import('@/pages/Login'))

// 后台管理
const AdminLayout = lazy(() => import('@/components/admin/AdminLayout'))
const AdminDashboard = lazy(() => import('@/pages/admin/AdminDashboard'))
const AdminUsers = lazy(() => import('@/pages/admin/AdminUsers'))
const AdminRoles = lazy(() => import('@/pages/admin/AdminRoles'))
const AdminAudit = lazy(() => import('@/pages/admin/AdminAudit'))
const AdminConfig = lazy(() => import('@/pages/admin/AdminConfig'))
const AdminHealth = lazy(() => import('@/pages/admin/AdminHealth'))
const AdminOrgs = lazy(() => import('@/pages/admin/AdminOrgs'))
const AdminFeatureFlags = lazy(() => import('@/pages/admin/AdminFeatureFlags'))

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <PrivacyProvider>
          <BrowserRouter>
            <Toaster position="top-right" richColors />
            <Suspense fallback={<PageSkeleton />}>
              <Routes>
              {/* 登录页（不需要 Layout 和路由守卫） */}
              <Route path="/login" element={<Login />} />

              {/* ===== 后台管理（独立布局 + Admin 权限守卫） ===== */}
              <Route path="/admin" element={<AdminRoute><AdminLayout /></AdminRoute>}>
                <Route index element={<AdminDashboard />} />
                <Route path="users" element={<AdminUsers />} />
                <Route path="roles" element={<AdminRoles />} />
                <Route path="audit" element={<AdminAudit />} />
                <Route path="config" element={<AdminConfig />} />
                <Route path="health" element={<AdminHealth />} />
                <Route path="orgs" element={<AdminOrgs />} />
                <Route path="feature-flags" element={<AdminFeatureFlags />} />
              </Route>

              {/* 受保护的业务路由 */}
              <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                <Route index element={<Navigate to="/chat" replace />} />

                {/* ===== AI法务（仅智能对话） ===== */}
                <Route path="chat" element={<Chat />} />

                {/* ===== 智能协作 ===== */}
                <Route path="cases" element={<Cases />} />
                <Route path="cases/:id" element={<CaseDetail />} />
                <Route path="contracts" element={<Contracts />} />
                <Route path="collaboration" element={<Collaboration />} />
                <Route path="collaboration/:sessionId" element={<Collaboration />} />
                <Route path="find-lawyer" element={<FindLawyer />} />
                <Route path="compliance-check" element={<ComplianceCheck />} />
                <Route path="leads" element={<Leads />} />

                {/* ===== 信息中心 ===== */}
                <Route path="news" element={<News />} />
                <Route path="due-diligence" element={<DueDiligence />} />

                {/* ===== 法律智库 ===== */}
                <Route path="search" element={<Search />} />
                <Route path="knowledge-graph" element={<KnowledgeGraph />} />
                <Route path="knowledge-base" element={<KnowledgeBase />} />
                <Route path="academy" element={<Academy />} />

                {/* ===== IM 即时通讯 ===== */}
                <Route path="messages" element={<Messages />} />

                {/* ===== 获客系统 ===== */}
                <Route path="lawyer/:profileId" element={<LawyerProfile />} />
                <Route path="acquisition" element={<AcquisitionDashboard />} />

                {/* ===== 律所管理 ===== */}
                <Route path="firm" element={<FirmManagement />} />

                {/* ===== 系统（审批已整合进任务中心，系统设置仅保留个人中心） ===== */}
                <Route path="settings" element={<Settings />} />
                <Route path="tasks" element={<Tasks />} />

                {/* ===== 旧路由兼容重定向 ===== */}
                <Route path="knowledge" element={<Navigate to="/knowledge-base" replace />} />
                <Route path="tools" element={<Navigate to="/chat" replace />} />
                <Route path="tax-assets" element={<Navigate to="/chat" replace />} />
                <Route path="sentiment" element={<Navigate to="/chat" replace />} />
                <Route path="contract-review" element={<Navigate to="/contracts" replace />} />
                <Route path="dashboard" element={<Navigate to="/collaboration" replace />} />
                <Route path="documents" element={<Navigate to="/collaboration" replace />} />
                <Route path="experts" element={<Navigate to="/find-lawyer" replace />} />
                <Route path="approvals" element={<Navigate to="/tasks" replace />} />

                {/* ===== 404 兜底 ===== */}
                <Route path="*" element={<NotFound />} />
              </Route>
              </Routes>
            </Suspense>
          </BrowserRouter>
        </PrivacyProvider>
      </ThemeProvider>
    </ErrorBoundary>
  )
}

export default App
