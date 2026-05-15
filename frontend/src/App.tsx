/**
 * App.tsx - 应用根组件与路由配置
 *
 * ===== [Phase 1] 移除废弃模块 =====
 * 删除了 PRD 不需要的页面：TaxAssets、Sentiment、LegalTools，以及已被重定向替代的旧业务页
 * 合同审查已合并到合同管理，智能文档和智能中台已整合到在线协作
 *
 * ===== [Phase 2] 路由懒加载 + 四大业务域路由结构 =====
 * 使用 React.lazy() + Suspense 实现按需加载，减少首屏 bundle 体积
 * 路由按 PRD 四大业务域分组：AI 智能助手、智能协作、智能调查、法律智库
 *
 * ===== [Phase 3] ErrorBoundary + 404 页面 =====
 * 添加全局错误边界，防止子组件崩溃导致白屏
 * 添加 404 兜底路由
 */

import { lazy, Suspense, useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom'
import { Toaster, toast } from 'sonner'
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
import { fetchCurrentUserWithToken, installDesktopDataNetworkGuard, refreshAuthSession, setDesktopRuntimePrivacyMode } from '@/lib/api'
import { getTokenStorage } from '@/lib/platform/storage'
import { ModeGate } from '@/components/mode/ModeGate'
import { SubscriptionGate } from '@/components/mode/SubscriptionGate'
import { useAppModeStore, useAuthStore } from '@/lib/store'
import { summarizeFileDropQueueReport } from '@/lib/desktopFileDropEvents'
import {
  getAppState,
  isTauri,
  listenDesktopFileDrops,
  listenFileDropQueued,
  queueFileDropPaths,
  saveAuthToken,
} from '@/lib/tauri-bridge'

// ===== 路由懒加载 =====
// 每个页面只在用户访问时才加载对应的 JS 代码
// 特别是 Knowledge（含 three.js 3D 图形库）和 Collaboration（含 tiptap/yjs）等重型页面

// AI 智能助手
const Chat = lazy(() => import('@/pages/Chat'))

// 智能协作（v3.0 模块合并）
const CaseCenter = lazy(() => import('@/pages/CaseCenter'))
const CaseDetail = lazy(() => import('@/pages/CaseDetail'))
const ManagementCenter = lazy(() => import('@/pages/ManagementCenter'))
const DocumentWorkbench = lazy(() => import('@/pages/DocumentWorkbench'))
const AgentApprovalWorkspace = lazy(() => import('@/pages/AgentApprovalWorkspace'))

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
const SyncConflicts = lazy(() => import('@/pages/SyncConflicts'))
const CaseMarket = lazy(() => import('@/pages/CaseMarket'))
const QuickQuery = lazy(() => import('@/pages/QuickQuery'))
const NotFound = lazy(() => import('@/pages/NotFound'))

// 登录页
const Login = lazy(() => import('@/pages/Login'))

// V2 架构：服务方端独立布局
import ProLayout from '@/components/pro/ProLayout'

// ===== V3 IA 占位页（与旧路由并存，可独立访问） =====
const AgentsPage = lazy(() => import('@/pages/v3/agents/AgentsPage'))
const ScheduledTasksPage = lazy(() => import('@/pages/v3/capabilities/ScheduledTasksPage'))
const AppAuthorizationsPage = lazy(() => import('@/pages/v3/capabilities/AppAuthorizationsPage'))
const SkillsPage = lazy(() => import('@/pages/v3/capabilities/SkillsPage'))
const PluginsPage = lazy(() => import('@/pages/v3/capabilities/PluginsPage'))
const MessageChannelsPage = lazy(() => import('@/pages/v3/capabilities/MessageChannelsPage'))
const PairingAuthorizationsPage = lazy(() => import('@/pages/v3/capabilities/PairingAuthorizationsPage'))
// V3 任务中心（P2 真业务化）
const V3TasksPage = lazy(() => import('@/pages/v3/tasks/TasksPage'))
// V3 智能体工作台（P8-C 真业务化 — 10 个 user-facing persona）
const PersonaWorkspacePage = lazy(() => import('@/pages/v3/personas/PersonaWorkspacePage'))
// V3 RAG 数据看板（P13-D — 多模态文档解析 / 文档库 / KG / VLM 查询）
const RagDashboardPage = lazy(() => import('@/pages/v3/rag/RagDashboardPage'))
const RagIngestPage = lazy(() => import('@/pages/v3/rag/IngestPage'))
const RagDocumentLibraryPage = lazy(() => import('@/pages/v3/rag/DocumentLibraryPage'))
const RagKnowledgeGraphPage = lazy(() => import('@/pages/v3/rag/KnowledgeGraphPage'))
const RagMultimodalQueryPage = lazy(() => import('@/pages/v3/rag/MultimodalQueryPage'))

// V3 Layout（侧边栏 IA）— 通过 VITE_V3_NAV=true 启用，默认仍用旧 Layout
import LayoutV3 from '@/components/layout/LayoutV3'

// 严格读取 boolean flag（避免 'false' 字符串被当成真值）
const V3_NAV_ENABLED = import.meta.env.VITE_V3_NAV === 'true'
const RootLayout = V3_NAV_ENABLED ? LayoutV3 : Layout

// 治理后台（AdminLayout 静态引入，避免 Vite 动态 import 偶发 Failed to fetch module）
const AdminDashboard = lazy(() => import('@/pages/admin/AdminDashboard'))
const AdminUsers = lazy(() => import('@/pages/admin/AdminUsers'))
const AdminRoles = lazy(() => import('@/pages/admin/AdminRoles'))
const AdminAudit = lazy(() => import('@/pages/admin/AdminAudit'))
const AdminGovernance = lazy(() => import('@/pages/admin/AdminGovernance'))
const AdminGovernancePolicy = lazy(() => import('@/pages/admin/AdminGovernancePolicy'))
const AdminGovernanceAudit = lazy(() => import('@/pages/admin/AdminGovernanceAudit'))
const AdminGovernanceTickets = lazy(() => import('@/pages/admin/AdminGovernanceTickets'))
const AdminGovernanceRevoked = lazy(() => import('@/pages/admin/AdminGovernanceRevoked'))
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

function CollaborationRedirect() {
  const { sessionId } = useParams()

  return (
    <Navigate
      to="/documents"
      replace
      state={{
        entryMode: 'collaboration',
        sessionId: sessionId ?? null,
      }}
    />
  )
}

function App() {
  const { setLastSyncTime, setMode, setOnline, setSyncStatus } = useAppModeStore()
  const [authBootstrapped, setAuthBootstrapped] = useState(false)

  useEffect(() => {
    installDesktopDataNetworkGuard()
  }, [])

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
    let active = true

    const bootstrapAuth = async () => {
      const storage = getTokenStorage()
      let accessToken = await storage.getAccessToken()

      if (!accessToken) {
        accessToken = await refreshAuthSession()
      }

      if (!accessToken || !active) {
        return
      }

      const auth = useAuthStore.getState()
      auth.setToken(accessToken)

      if (!auth.user) {
        const user = await fetchCurrentUserWithToken(accessToken)
        if (user && active) {
          useAuthStore.getState().setUser(user)
        }
      }
    }

    bootstrapAuth()
      .catch((error) => {
        console.debug('[Auth] 启动会话恢复失败:', error)
      })
      .finally(() => {
        if (active) {
          setAuthBootstrapped(true)
        }
      })

    return () => {
      active = false
    }
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

      setDesktopRuntimePrivacyMode(appState.mode)
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

  useEffect(() => {
    if (!isTauri()) {
      return
    }

    let disposed = false
    let unlisten: (() => void) | null = null

    listenFileDropQueued((report) => {
      const summary = summarizeFileDropQueueReport(report)
      if (!summary) return

      if (summary.variant === 'success') {
        toast.success(summary.title, { description: summary.description })
        return
      }

      toast.warning(summary.title, { description: summary.description })
    })
      .then((cleanup) => {
        if (disposed) {
          cleanup?.()
          return
        }
        unlisten = cleanup
      })
      .catch((error) => {
        console.debug('[Desktop] 文件拖入队列提示监听失败:', error)
      })

    return () => {
      disposed = true
      unlisten?.()
    }
  }, [])

  useEffect(() => {
    if (!isTauri()) {
      return
    }

    let disposed = false
    let unlisten: (() => void) | null = null

    listenDesktopFileDrops((paths) => {
      if (paths.length === 0) return

      queueFileDropPaths(paths).catch((error) => {
        toast.error('文件入队失败', {
          description: error instanceof Error ? error.message : '请稍后重试',
        })
      })
    })
      .then((cleanup) => {
        if (disposed) {
          cleanup()
          return
        }
        unlisten = cleanup
      })
      .catch((error) => {
        console.debug('[Desktop] 文件拖放监听启动失败:', error)
      })

    return () => {
      disposed = true
      unlisten?.()
    }
  }, [])

  if (!authBootstrapped) {
    return <PageSkeleton />
  }

  return (
    <ErrorBoundary>
      <ThemeProvider>
        <PrivacyProvider>
          <BrowserRouter>
            <Toaster position="top-right" richColors />
            {/* V2：全局订阅引导弹窗 — 切换到混合/云端模式无订阅时触发 */}
            <SubscriptionGate />
            <Suspense fallback={<PageSkeleton />}>
              <Routes>
              {/* 登录页（不需要 Layout 和路由守卫） */}
              <Route path="/login" element={<Login />} />
              {/* V2 架构：服务方端（律师/律所）专属登录入口 */}
              <Route path="/pro/login" element={<Login />} />
              <Route path="/desktop/quick-query" element={<QuickQuery />} />

              {/* ===== 治理后台（独立布局 + Admin 权限守卫） ===== */}
              <Route path="/admin" element={<AdminRoute><AdminLayout /></AdminRoute>}>
                <Route index element={<AdminDashboard />} />
                <Route path="users" element={<AdminUsers />} />
                <Route path="roles" element={<AdminRoles />} />
                <Route path="audit" element={<AdminAudit />} />
                <Route path="governance" element={<AdminGovernance />} />
                <Route path="governance/policy" element={<AdminGovernancePolicy />} />
                <Route path="governance/audit" element={<AdminGovernanceAudit />} />
                <Route path="governance/tickets" element={<AdminGovernanceTickets />} />
                <Route path="governance/revoked" element={<AdminGovernanceRevoked />} />
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

              {/* ===== V2 架构：服务方端（律师/律所独立布局） ===== */}
              <Route path="/pro" element={<ProtectedRoute requirePrimaryClient="provider"><ProLayout /></ProtectedRoute>}>
                <Route index element={<Navigate to="/pro/dashboard" replace />} />
                <Route path="dashboard" element={<LawyerDashboard />} />
                <Route path="cases" element={<CaseCenter />} />
                <Route path="contracts" element={<ManagementCenter />} />
                <Route path="documents" element={<DocumentWorkbench />} />
                <Route path="chat" element={<Chat />} />
                <Route path="messages" element={<Messages />} />
                <Route path="knowledge" element={<KnowledgeBase />} />
                <Route path="investigation" element={<Investigation />} />
                <Route path="onboarding" element={<LawyerOnboarding />} />
                <Route path="subscription" element={<MySubscription />} />
                <Route path="settings" element={<Settings />} />
                <Route path="market" element={<CaseMarket />} />
              </Route>

              {/* 受保护的业务路由 — Layout 由 VITE_V3_NAV 切换（默认旧 Layout） */}
              <Route path="/" element={<ProtectedRoute><RootLayout /></ProtectedRoute>}>
                <Route index element={<Navigate to="/chat" replace />} />

                {/* ===== V3 IA 新增路由（占位） ===== */}
                <Route path="agents" element={<AgentsPage />} />
                <Route path="capabilities/scheduled-tasks" element={<ScheduledTasksPage />} />
                <Route path="capabilities/app-authorizations" element={<AppAuthorizationsPage />} />
                <Route path="capabilities/skills" element={<SkillsPage />} />
                <Route path="capabilities/plugins" element={<PluginsPage />} />
                <Route path="capabilities/message-channels" element={<MessageChannelsPage />} />
                <Route path="capabilities/pairing-authorizations" element={<PairingAuthorizationsPage />} />

                {/* ===== AI 智能助手（仅智能对话） ===== */}
                <Route path="chat" element={<ProtectedRoute feature="ai_chat"><Chat /></ProtectedRoute>} />

                {/* ===== 智能协作（v3.0 模块合并） ===== */}
                <Route path="case-center" element={<ProtectedRoute feature="case_management"><CaseCenter /></ProtectedRoute>} />
                <Route path="case-center/:id" element={<ProtectedRoute feature="case_management"><CaseDetail /></ProtectedRoute>} />
                <Route path="management" element={<ProtectedRoute feature="contract_management"><ManagementCenter /></ProtectedRoute>} />
                <Route path="documents" element={<ProtectedRoute feature="document_management"><DocumentWorkbench /></ProtectedRoute>} />
                <Route path="agent-approvals" element={<ProtectedRoute feature="approval_workflow"><AgentApprovalWorkspace /></ProtectedRoute>} />
                {/* V2: 找律师需要云端数据库支持 */}
                <Route path="find-lawyer" element={
                  <ProtectedRoute feature="lawyer_matching">
                    <ModeGate required="hybrid_or_cloud" feature="找律师">
                      <FindLawyer />
                    </ModeGate>
                  </ProtectedRoute>
                } />

                {/* ===== 舆情监测 — V2: 必须云端/混合模式（爬虫+NLP） ===== */}
                <Route path="monitoring" element={
                  <ProtectedRoute feature="due_diligence">
                    <ModeGate required="hybrid_or_cloud" feature="舆情监测">
                      <MonitoringCenter />
                    </ModeGate>
                  </ProtectedRoute>
                } />
                <Route path="investigation" element={
                  <ProtectedRoute feature="due_diligence">
                    <ModeGate required="hybrid_or_cloud" feature="尽职调查">
                      <Investigation />
                    </ModeGate>
                  </ProtectedRoute>
                } />
                <Route path="investigation/:companyId" element={
                  <ProtectedRoute feature="due_diligence">
                    <ModeGate required="hybrid_or_cloud" feature="尽职调查">
                      <Investigation />
                    </ModeGate>
                  </ProtectedRoute>
                } />

                {/* ===== 法律智库 — V2: 本地可用但需先下载数据包 ===== */}
                <Route path="knowledge-graph" element={
                  <ProtectedRoute feature="knowledge_graph">
                    <ModeGate required="local_ok_with_download" feature="知识图谱">
                      <KnowledgeGraph />
                    </ModeGate>
                  </ProtectedRoute>
                } />
                <Route path="knowledge-base" element={
                  <ProtectedRoute feature="knowledge_base">
                    <ModeGate required="local_ok_with_download" feature="法律智库">
                      <KnowledgeBase />
                    </ModeGate>
                  </ProtectedRoute>
                } />

                {/* ===== IM 即时通讯 — V2: 必须云端/混合（需 WebSocket 转发） ===== */}
                <Route path="messages" element={
                  <ProtectedRoute feature="im_messaging">
                    <ModeGate required="hybrid_or_cloud" feature="即时通讯">
                      <Messages />
                    </ModeGate>
                  </ProtectedRoute>
                } />
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

                {/* ===== AI 配置已迁移到治理后台 ===== */}
                <Route path="ai-assistant-settings" element={<Navigate to="/private-llm" replace />} />
                <Route path="private-llm" element={<ProtectedRoute feature="private_llm"><PrivateLLMSetup /></ProtectedRoute>} />
                <Route path="sync-conflicts" element={<SyncConflicts />} />
                <Route path="conversation-insights" element={<Navigate to="/admin" replace />} />
                <Route path="agent-workflow" element={<Navigate to="/admin" replace />} />

                {/* ===== V3 任务中心(P2 真业务化) ===== */}
                <Route path="v3/tasks" element={<ProtectedRoute><V3TasksPage /></ProtectedRoute>} />
                <Route path="v3/personas/:personaId" element={<ProtectedRoute><PersonaWorkspacePage /></ProtectedRoute>} />
                {/* ===== V3 RAG 数据看板(P13-D) ===== */}
                <Route path="v3/rag" element={<ProtectedRoute><RagDashboardPage /></ProtectedRoute>} />
                <Route path="v3/rag/ingest" element={<ProtectedRoute><RagIngestPage /></ProtectedRoute>} />
                <Route path="v3/rag/library" element={<ProtectedRoute><RagDocumentLibraryPage /></ProtectedRoute>} />
                <Route path="v3/rag/kg" element={<ProtectedRoute><RagKnowledgeGraphPage /></ProtectedRoute>} />
                <Route path="v3/rag/query" element={<ProtectedRoute><RagMultimodalQueryPage /></ProtectedRoute>} />

                {/* ===== 系统 ===== */}
                <Route path="settings" element={<ProtectedRoute feature="settings"><Settings /></ProtectedRoute>} />
                {/* V2：案源市场（需求方发布，本页根据 primary_client 自动切换视图） */}
                <Route path="market" element={
                  <ProtectedRoute feature="lawyer_matching">
                    <ModeGate required="hybrid_or_cloud" feature="案源市场">
                      <CaseMarket />
                    </ModeGate>
                  </ProtectedRoute>
                } />

                {/* ===== 旧路由兼容重定向（v3.0 模块合并） =====
                 * 保留语义：`/tasks` 必须落到「任务与审批」tab，`/contracts`
                 * 必须落到「合同管理」tab，避免用户书签或外部链接失效。
                 */}
                <Route path="cases" element={<Navigate to="/case-center?tab=cases" replace />} />
                <Route path="cases/:id" element={<Navigate to="/case-center?tab=cases" replace />} />
                <Route path="leads" element={<Navigate to="/case-center?tab=leads" replace />} />
                <Route path="tasks" element={<Navigate to="/case-center?tab=tasks" replace />} />
                <Route path="contracts" element={<Navigate to="/management?tab=contracts" replace />} />
                <Route path="contract-review" element={<Navigate to="/management?tab=contracts" replace />} />
                <Route path="compliance-check" element={<Navigate to="/management?tab=compliance" replace />} />
                <Route path="due-diligence" element={<Navigate to="/investigation" replace />} />
                <Route path="due-diligence/:section" element={<Navigate to="/investigation" replace />} />
                <Route path="collaboration" element={<CollaborationRedirect />} />
                <Route path="collaboration/:sessionId" element={<CollaborationRedirect />} />
                <Route path="approvals" element={<Navigate to="/case-center?tab=tasks" replace />} />
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
