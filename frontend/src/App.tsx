/**
 * App.tsx - 应用根组件与路由配置
 *
 * ===== [Phase 1] 移除废弃模块 =====
 * 删除了 PRD 不需要的页面：TaxAssets、Sentiment、LegalTools
 * 合同审查已合并到合同管理，智能文档和智能中台已整合到在线协作
 *
 * ===== [Phase 2] 路由懒加载 + 四大业务域路由结构 =====
 * 使用 React.lazy() + Suspense 实现按需加载，减少首屏 bundle 体积
 * 路由按 PRD 四大业务域分组：AI法务、智能协作、智能调查、法律智库
 *
 * ===== [Phase 3] ErrorBoundary + 404 页面 =====
 * 添加全局错误边界，防止子组件崩溃导致白屏
 * 添加 404 兜底路由
 */

import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import Layout from '@/components/Layout'
// ModuleLayout is used inside Layout.tsx based on current route
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { PageSkeleton } from '@/components/PageSkeleton'
import { PrivacyProvider } from '@/context/PrivacyContext'
import { ThemeProvider } from '@/components/ThemeProvider'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { AdminRoute } from '@/components/auth/AdminRoute'
import AdminLayout from '@/components/admin/AdminLayout'

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

// 智能调查
// const News = lazy(() => import('@/pages/News'))  // v2.0 版本启用
const DueDiligence = lazy(() => import('@/pages/DueDiligence'))

// 法律智库
const KnowledgeGraph = lazy(() => import('@/pages/KnowledgeGraph'))
const KnowledgeBase = lazy(() => import('@/pages/KnowledgeBase'))

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
const LawyerOnboarding = lazy(() => import('@/pages/LawyerOnboarding'))
const LawyerDashboard = lazy(() => import('@/pages/LawyerDashboard'))
const Pricing = lazy(() => import('@/pages/Pricing'))
const MySubscription = lazy(() => import('@/pages/MySubscription'))
const AIAssistantSettings = lazy(() => import('@/pages/AIAssistantSettings'))
const PrivateLLMSetup = lazy(() => import('@/pages/PrivateLLMSetup'))
const ConversationInsights = lazy(() => import('@/pages/ConversationInsights'))
const AgentWorkflow = lazy(() => import('@/pages/AgentWorkflow'))
const NotFound = lazy(() => import('@/pages/NotFound'))

// 登录页
const Login = lazy(() => import('@/pages/Login'))

// 后台管理（AdminLayout 静态引入，避免 Vite 动态 import 偶发 Failed to fetch module）
const AdminDashboard = lazy(() => import('@/pages/admin/AdminDashboard'))
const AdminUsers = lazy(() => import('@/pages/admin/AdminUsers'))
const AdminRoles = lazy(() => import('@/pages/admin/AdminRoles'))
const AdminAudit = lazy(() => import('@/pages/admin/AdminAudit'))
const AdminConfig = lazy(() => import('@/pages/admin/AdminConfig'))
const AdminHealth = lazy(() => import('@/pages/admin/AdminHealth'))
const AdminOrgs = lazy(() => import('@/pages/admin/AdminOrgs'))
const AdminFeatureFlags = lazy(() => import('@/pages/admin/AdminFeatureFlags'))
const AdminLawyerVerify = lazy(() => import('@/pages/admin/AdminLawyerVerify'))
const AdminBilling = lazy(() => import('@/pages/admin/AdminBilling'))
const AdminFirm = lazy(() => import('@/pages/admin/AdminFirm'))
const AdminEnterprise = lazy(() => import('@/pages/admin/AdminEnterprise'))
const AdminAcquisition = lazy(() => import('@/pages/admin/AdminAcquisition'))

function App() {
  // 全局监听 auth:redirect 事件，统一处理页面跳转
  // 在 Tauri 桌面端可替换为 Tauri 路由方式，Web 端保持 window.location 行为
  useEffect(() => {
    const handler = (e: CustomEvent) => {
      window.location.href = e.detail
    }
    window.addEventListener('auth:redirect', handler as EventListener)
    return () => window.removeEventListener('auth:redirect', handler as EventListener)
  }, [])

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
                <Route path="lawyer-verify" element={<AdminLawyerVerify />} />
                <Route path="billing" element={<AdminBilling />} />
                <Route path="firm" element={<AdminFirm />} />
                <Route path="enterprise" element={<AdminEnterprise />} />
                <Route path="acquisition" element={<AdminAcquisition />} />
              </Route>

              {/* 受保护的业务路由 */}
              <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                <Route index element={<Navigate to="/chat" replace />} />

                {/* ===== AI法务（仅智能对话） ===== */}
                <Route path="chat" element={<Chat />} />

                {/* ===== 智能协作 ===== */}
                <Route path="cases" element={<ProtectedRoute feature="case_management"><Cases /></ProtectedRoute>} />
                <Route path="cases/:id" element={<ProtectedRoute feature="case_management"><CaseDetail /></ProtectedRoute>} />
                <Route path="contracts" element={<Contracts />} />
                <Route path="collaboration" element={<Collaboration />} />
                <Route path="collaboration/:sessionId" element={<Collaboration />} />
                <Route path="find-lawyer" element={<ProtectedRoute feature="lawyer_matching"><FindLawyer /></ProtectedRoute>} />
                <Route path="compliance-check" element={<ComplianceCheck />} />
                <Route path="leads" element={<ProtectedRoute feature="leads"><Leads /></ProtectedRoute>} />

                {/* ===== 智能调查 ===== */}
                {/* <Route path="news" element={<News />} /> */}{/* v2.0 版本启用 */}
                <Route path="due-diligence" element={<DueDiligence />} />
                <Route path="due-diligence/:section" element={<DueDiligence />} />

                {/* ===== 法律智库 ===== */}
                <Route path="knowledge-graph" element={<KnowledgeGraph />} />
                <Route path="knowledge-base" element={<KnowledgeBase />} />

                {/* ===== IM 即时通讯 ===== */}
                <Route path="messages" element={<Messages />} />

                {/* ===== 律师资料 ===== */}
                <Route path="lawyer/:profileId" element={<LawyerProfile />} />

                {/* ===== 律师入驻 ===== */}
                <Route path="lawyer-onboarding" element={<LawyerOnboarding />} />
                <Route path="lawyer-dashboard" element={<LawyerDashboard />} />

                {/* ===== 计费系统 ===== */}
                <Route path="pricing" element={<Pricing />} />
                <Route path="my-subscription" element={<MySubscription />} />

                {/* ===== AI 配置已迁移到后台管理 ===== */}
                <Route path="ai-assistant-settings" element={<Navigate to="/admin/ai-config" replace />} />
                <Route path="private-llm" element={<Navigate to="/admin/ai-config" replace />} />
                <Route path="conversation-insights" element={<Navigate to="/admin" replace />} />
                <Route path="agent-workflow" element={<Navigate to="/admin" replace />} />

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
                <Route path="search" element={<Navigate to="/due-diligence" replace />} />
                <Route path="academy" element={<Navigate to="/knowledge-base" replace />} />
                <Route path="firm" element={<Navigate to="/admin/firm" replace />} />
                <Route path="acquisition" element={<Navigate to="/admin/acquisition" replace />} />

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
