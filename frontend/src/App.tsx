/**
 * App.tsx - 应用根组件与路由配置
 *
 * ===== [Phase 1] 移除废弃模块 =====
 * 删除了 PRD 不需要的页面：TaxAssets、Sentiment、LegalTools，以及已被重定向替代的旧业务页
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
import { initLocalDatabase } from '@/lib/api-adapter'
import { getTokenStorage } from '@/lib/platform/storage'
import { useAppModeStore } from '@/lib/store'
import { getAppState, isTauri, saveAuthToken } from '@/lib/tauri-bridge'

// ===== 路由懒加载 =====
// 每个页面只在用户访问时才加载对应的 JS 代码
// 特别是 Knowledge（含 three.js 3D 图形库）和 Collaboration（含 tiptap/yjs）等重型页面

// AI法务
const Chat = lazy(() => import('@/pages/Chat'))

// 智能协作（v3.0 模块合并）
const CaseCenter = lazy(() => import('@/pages/CaseCenter'))
const CaseDetail = lazy(() => import('@/pages/CaseDetail'))
const ManagementCenter = lazy(() => import('@/pages/ManagementCenter'))
const DocumentWorkbench = lazy(() => import('@/pages/DocumentWorkbench'))

// 舆情监测（v3.0 由"智能调查"重构）
const MonitoringCenter = lazy(() => import('@/pages/MonitoringCenter'))
const Investigation = lazy(() => import('@/pages/Investigation'))

// 法律智库
const KnowledgeGraph = lazy(() => import('@/pages/KnowledgeGraph'))
const KnowledgeBase = lazy(() => import('@/pages/KnowledgeBase'))

// 客户门户
const ClientPortal = lazy(() => import('@/pages/ClientPortal'))

// 系统
const Settings = lazy(() => import('@/pages/Settings'))
const FindLawyer = lazy(() => import('@/pages/FindLawyer'))
const Messages = lazy(() => import('@/pages/Messages'))
const VoiceCall = lazy(() => import('@/components/rtc/VoiceCall'))
const VideoCall = lazy(() => import('@/components/rtc/VideoCall'))
const LawyerProfile = lazy(() => import('@/pages/LawyerProfile'))
const AcquisitionDashboard = lazy(() => import('@/pages/AcquisitionDashboard'))
const LawyerOnboarding = lazy(() => import('@/pages/LawyerOnboarding'))
const LawyerDashboard = lazy(() => import('@/pages/LawyerDashboard'))
const Pricing = lazy(() => import('@/pages/Pricing'))
const MySubscription = lazy(() => import('@/pages/MySubscription'))
const PrivateLLMSetup = lazy(() => import('@/pages/PrivateLLMSetup'))
const NotFound = lazy(() => import('@/pages/NotFound'))

// 登录页
const Login = lazy(() => import('@/pages/Login'))

// 后台管理（AdminLayout 静态引入，避免 Vite 动态 import 偶发 Failed to fetch module）
const AdminDashboard = lazy(() => import('@/pages/admin/AdminDashboard'))
const AdminUsers = lazy(() => import('@/pages/admin/AdminUsers'))
const AdminRoles = lazy(() => import('@/pages/admin/AdminRoles'))
const AdminAudit = lazy(() => import('@/pages/admin/AdminAudit'))
const AdminBasic = lazy(() => import('@/pages/admin/AdminBasic'))
const AdminAIConfig = lazy(() => import('@/pages/admin/AdminAIConfig'))
const AdminIntegrations = lazy(() => import('@/pages/admin/AdminIntegrations'))
const AdminSecurity = lazy(() => import('@/pages/admin/AdminSecurity'))
const AdminHealth = lazy(() => import('@/pages/admin/AdminHealth'))
const AdminOrgs = lazy(() => import('@/pages/admin/AdminOrgs'))
const AdminFeatureFlags = lazy(() => import('@/pages/admin/AdminFeatureFlags'))
const AdminLawyerVerify = lazy(() => import('@/pages/admin/AdminLawyerVerify'))
const AdminBilling = lazy(() => import('@/pages/admin/AdminBilling'))
const AdminFirm = lazy(() => import('@/pages/admin/AdminFirm'))
const AdminEnterprise = lazy(() => import('@/pages/admin/AdminEnterprise'))
const AdminAcquisition = lazy(() => import('@/pages/admin/AdminAcquisition'))
const AdminHarness = lazy(() => import('@/pages/admin/AdminHarness'))

function App() {
  const { setLastSyncTime, setMode, setOnline, setSyncStatus } = useAppModeStore()

  // 全局监听 auth:redirect 事件，统一处理页面跳转
  // 在 Tauri 桌面端可替换为 Tauri 路由方式，Web 端保持 window.location 行为
  useEffect(() => {
    const handler = (e: CustomEvent) => {
      window.location.href = e.detail
    }
    window.addEventListener('auth:redirect', handler as EventListener)
    return () => window.removeEventListener('auth:redirect', handler as EventListener)
  }, [])

  useEffect(() => {
    if (!isTauri()) {
      return
    }

    let active = true

    const bootstrapDesktop = async () => {
      await initLocalDatabase()

      const storage = getTokenStorage()
      const [accessToken, refreshToken, appState] = await Promise.all([
        storage.getAccessToken(),
        storage.getRefreshToken(),
        getAppState(),
      ])

      if (accessToken) {
        await saveAuthToken(accessToken, refreshToken ?? undefined)
      }

      if (!active || !appState) {
        return
      }

      setMode(appState.mode)
      setSyncStatus(appState.sync_status)
      setLastSyncTime(appState.last_sync_time)
      setOnline(appState.is_online)
    }

    bootstrapDesktop().catch((error) => {
      console.error('[Desktop] 启动初始化失败:', error)
    })

    return () => {
      active = false
    }
  }, [setLastSyncTime, setMode, setOnline, setSyncStatus])

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
                <Route path="basic" element={<AdminBasic />} />
                <Route path="ai-config" element={<AdminAIConfig />} />
                <Route path="integrations" element={<AdminIntegrations />} />
                <Route path="security" element={<AdminSecurity />} />
                <Route path="config" element={<Navigate to="/admin/basic" replace />} />
                <Route path="health" element={<AdminHealth />} />
                <Route path="harness" element={<AdminHarness />} />
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
                <Route path="chat" element={<ProtectedRoute feature="ai_chat"><Chat /></ProtectedRoute>} />

                {/* ===== 智能协作（v3.0 模块合并） ===== */}
                <Route path="case-center" element={<ProtectedRoute feature="case_management"><CaseCenter /></ProtectedRoute>} />
                <Route path="case-center/:id" element={<ProtectedRoute feature="case_management"><CaseDetail /></ProtectedRoute>} />
                <Route path="management" element={<ProtectedRoute feature="contract_management"><ManagementCenter /></ProtectedRoute>} />
                <Route path="documents" element={<ProtectedRoute feature="document_management"><DocumentWorkbench /></ProtectedRoute>} />
                <Route path="find-lawyer" element={<ProtectedRoute feature="lawyer_matching"><FindLawyer /></ProtectedRoute>} />

                {/* ===== 舆情监测（v3.0 由"智能调查"重构） ===== */}
                <Route path="monitoring" element={<ProtectedRoute feature="due_diligence"><MonitoringCenter /></ProtectedRoute>} />
                <Route path="investigation" element={<ProtectedRoute feature="due_diligence"><Investigation /></ProtectedRoute>} />
                <Route path="investigation/:companyId" element={<ProtectedRoute feature="due_diligence"><Investigation /></ProtectedRoute>} />

                {/* ===== 法律智库 ===== */}
                <Route path="knowledge-graph" element={<ProtectedRoute feature="knowledge_graph"><KnowledgeGraph /></ProtectedRoute>} />
                <Route path="knowledge-base" element={<ProtectedRoute feature="knowledge_base"><KnowledgeBase /></ProtectedRoute>} />

                {/* ===== IM 即时通讯 ===== */}
                <Route path="messages" element={<ProtectedRoute feature="im_messaging"><Messages /></ProtectedRoute>} />
                <Route path="call/voice/:roomName" element={<VoiceCall />} />
                <Route path="call/video/:roomName" element={<VideoCall />} />

                {/* ===== 律师资料 ===== */}
                <Route path="lawyer/:profileId" element={<LawyerProfile />} />

                {/* ===== 律师入驻 ===== */}
                <Route path="lawyer-onboarding" element={<ProtectedRoute feature="lawyer_onboarding"><LawyerOnboarding /></ProtectedRoute>} />
                <Route path="lawyer-dashboard" element={<ProtectedRoute feature="lawyer_dashboard"><LawyerDashboard /></ProtectedRoute>} />

                {/* ===== 客户门户 ===== */}
                <Route path="client-portal" element={<ClientPortal />} />

                {/* ===== 计费系统 ===== */}
                <Route path="pricing" element={<ProtectedRoute feature="pricing"><Pricing /></ProtectedRoute>} />
                <Route path="my-subscription" element={<ProtectedRoute feature="my_subscription"><MySubscription /></ProtectedRoute>} />

                {/* ===== AI 配置已迁移到后台管理 ===== */}
                <Route path="ai-assistant-settings" element={<Navigate to="/private-llm" replace />} />
                <Route path="private-llm" element={<ProtectedRoute feature="private_llm"><PrivateLLMSetup /></ProtectedRoute>} />
                <Route path="conversation-insights" element={<Navigate to="/admin" replace />} />
                <Route path="agent-workflow" element={<Navigate to="/admin" replace />} />

                {/* ===== 系统 ===== */}
                <Route path="settings" element={<ProtectedRoute feature="settings"><Settings /></ProtectedRoute>} />

                {/* ===== 旧路由兼容重定向（v3.0 模块合并） ===== */}
                <Route path="cases" element={<Navigate to="/case-center" replace />} />
                <Route path="cases/:id" element={<Navigate to="/case-center" replace />} />
                <Route path="leads" element={<Navigate to="/case-center" replace />} />
                <Route path="tasks" element={<Navigate to="/case-center" replace />} />
                <Route path="contracts" element={<Navigate to="/management" replace />} />
                <Route path="contract-review" element={<Navigate to="/management" replace />} />
                <Route path="compliance-check" element={<Navigate to="/management" replace />} />
                <Route path="due-diligence" element={<Navigate to="/investigation" replace />} />
                <Route path="due-diligence/:section" element={<Navigate to="/investigation" replace />} />
                <Route path="collaboration" element={<Navigate to="/documents" replace />} />
                <Route path="collaboration/:sessionId" element={<Navigate to="/documents" replace />} />
                <Route path="approvals" element={<Navigate to="/case-center" replace />} />
                <Route path="knowledge" element={<Navigate to="/knowledge-base" replace />} />
                <Route path="tools" element={<Navigate to="/chat" replace />} />
                <Route path="tax-assets" element={<Navigate to="/chat" replace />} />
                <Route path="sentiment" element={<Navigate to="/monitoring" replace />} />
                <Route path="dashboard" element={<Navigate to="/case-center" replace />} />
                <Route path="experts" element={<Navigate to="/find-lawyer" replace />} />
                <Route path="search" element={<Navigate to="/investigation" replace />} />
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
