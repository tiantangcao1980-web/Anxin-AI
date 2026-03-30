/**
 * 全局状态管理 (v2 — 扩展右侧面板、Canvas、Agent 工作台状态)
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// ========== 类型定义 ==========

interface User {
  id: string
  email: string
  name: string
  role: string
  avatar_url?: string
}

// 对话列表项
export interface ConversationItem {
  id: string
  title: string
  message_count: number
  last_message_at: string | null
  created_at: string
}

// Agent 中间结果
export interface AgentResult {
  id: string
  agent: string
  agentKey?: string
  content: string
  step: number
  totalSteps: number
  elapsed?: number
  timestamp: number
}

// 思考链步骤
export interface ThinkingStep {
  id: string
  agent: string
  content: string
  phase: string  // 'requirement' | 'planning' | 'execution'
  planSteps?: { agent: string; instruction: string }[]
  timestamp: number
}

// 需求分析结果
export interface RequirementAnalysis {
  is_complete: boolean
  completeness_score: number
  summary: string
  elements?: Record<string, any>
  missing_elements?: string[]
  guidance_questions?: { question: string; options: string[]; purpose?: string }[]
  suggested_agents?: string[]
  complexity: string
}

// Canvas 内容
export interface CanvasContent {
  type: 'document' | 'code' | 'table' | 'contract'
  title: string
  content: string
  language?: string
  suggestions?: CanvasSuggestion[]
  metadata?: Record<string, any>
}

export interface CanvasSuggestion {
  id: string
  range: { startLine: number; endLine: number }
  original: string
  suggested: string
  reason: string
  status: 'pending' | 'accepted' | 'rejected'
}

// 分析数据
export interface AnalysisData {
  riskRadar: any | null
  documentDiff: any | null
  knowledgeGraph: any | null
}

// ========== 律师协助相关类型 ==========

export interface OnlineLawyer {
  id: string
  name: string
  avatar?: string
  specialties: string[]
  status: 'online' | 'busy' | 'offline'
  rating: number
  responseTime: string // 如 "通常5分钟内回复"
  firm?: string
}

export interface LawyerAssistRequest {
  id: string
  lawyerId: string
  lawyerName: string
  type: 'review' | 'edit' | 'consult' | 'approve'
  documentTitle: string
  content: string
  status: 'pending' | 'accepted' | 'in_progress' | 'completed' | 'rejected'
  createdAt: number
  respondedAt?: number
  completedAt?: number
  lawyerComments?: LawyerComment[]
}

export interface LawyerComment {
  id: string
  lawyerId: string
  lawyerName: string
  content: string
  type: 'suggestion' | 'approval' | 'revision' | 'question'
  timestamp: number
  lineRange?: { start: number; end: number }
}

// ========== 签约/盖章工作流相关类型 ==========

export type SigningWorkflowStatus =
  | 'idle'
  | 'document_ready'
  | 'pending_review'
  | 'lawyer_reviewing'
  | 'approved'
  | 'pending_sign'
  | 'signing'
  | 'signed'
  | 'pending_seal'
  | 'sealing'
  | 'sealed'
  | 'completed'
  | 'rejected'

export type SigningDocType =
  | 'contract'         // 合同签约
  | 'lawyer_letter'    // 律师函
  | 'authorization'    // 授权书
  | 'engagement'       // 委托书
  | 'legal_opinion'    // 法律意见书
  | 'seal_request'     // 盖章申请

export interface SigningWorkflowItem {
  id: string
  docType: SigningDocType
  title: string
  status: SigningWorkflowStatus
  documentId?: string
  content?: string
  parties: SigningParty[]
  steps: SigningStep[]
  currentStepIndex: number
  createdAt: number
  updatedAt: number
  completedAt?: number
  sealType?: 'company' | 'contract' | 'finance' | 'legal'
  urgency: 'normal' | 'urgent' | 'critical'
}

export interface SigningParty {
  id: string
  name: string
  role: 'initiator' | 'signer' | 'reviewer' | 'approver' | 'witness'
  status: 'pending' | 'signed' | 'rejected'
  signedAt?: number
  signatureUrl?: string
}

export interface SigningStep {
  id: string
  name: string
  description: string
  status: 'pending' | 'in_progress' | 'completed' | 'skipped'
  assignee?: string
  completedAt?: number
  order: number
}

// ========== 工作台交互相关类型 ==========

// 工作台确认卡片（左侧对话触发 → 右侧展示）
export interface WorkspaceConfirmation {
  id: string
  title: string
  description?: string
  type: 'single' | 'multi'   // 单选 / 多选
  options: { id: string; label: string; description?: string; icon?: string }[]
  selectedIds: string[]
  status: 'pending' | 'confirmed' | 'expired'
  source?: string  // 来源 Agent 或消息
  callbackAction?: string  // 确认后的回调动作标识
  createdAt: number
}

// 工作台动作按钮（由 Agent 推送到工作台）
export interface WorkspaceAction {
  id: string
  label: string
  description?: string
  icon?: string
  variant: 'primary' | 'secondary' | 'warning' | 'success'
  action: string  // 动作标识
  payload?: any   // 附带数据
  disabled?: boolean
}

// Agent 运行时任务卡片（用于并列协作展示）
export interface AgentTask {
  id: string
  agent: string
  agentKey?: string
  description: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  progress: number  // 0 - 100
  startedAt?: number
  completedAt?: number
  elapsed?: number
  result?: string   // 完成后的简要结果
  dependencies?: string[]  // 依赖的其他 agent 任务 ID
}

// 右侧面板 Tab 类型 — 工作台 + 文档面板
export type RightPanelTab = 'smart' | 'document'

// 文档面板内的浮层模式
export type DocumentOverlay = 'none' | 'lawyer' | 'signing'

// ========== Auth Store ==========

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  login: (user: User, token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setToken: (token) => {
        if (token) {
          localStorage.setItem('access_token', token)
        } else {
          localStorage.removeItem('access_token')
        }
        set({ token })
      },
      login: (user, token) => {
        localStorage.setItem('access_token', token)
        set({ user, token, isAuthenticated: true })
      },
      logout: () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        set({ user: null, token: null, isAuthenticated: false })
      },
    }),
    { name: 'auth-storage' }
  )
)

// ========== Chat Store (扩展) ==========

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent?: string
  timestamp: Date
}

interface ChatState {
  messages: Message[]
  conversationId: string | null
  isLoading: boolean
  conversations: ConversationItem[]
  sidebarOpen: boolean

  // 右侧面板
  rightPanelTab: RightPanelTab
  setRightPanelTab: (tab: RightPanelTab) => void
  documentOverlay: DocumentOverlay
  setDocumentOverlay: (overlay: DocumentOverlay) => void

  // 工作台数据
  agentResults: AgentResult[]
  addAgentResult: (result: AgentResult) => void
  clearAgentResults: () => void
  thinkingSteps: ThinkingStep[]
  addThinkingStep: (step: ThinkingStep) => void
  clearThinkingSteps: () => void

  // 需求分析
  requirementAnalysis: RequirementAnalysis | null
  setRequirementAnalysis: (data: RequirementAnalysis | null) => void

  // Canvas
  canvasContent: CanvasContent | null
  setCanvasContent: (content: CanvasContent | null) => void
  updateCanvasText: (text: string) => void

  // 文档列表（工作台内管理的历史文档）
  documentList: { id: string; title: string; type: CanvasContent['type']; updatedAt: number; preview?: string }[]
  addDocumentToList: (doc: { id: string; title: string; type: CanvasContent['type']; preview?: string }) => void
  removeDocumentFromList: (id: string) => void
  clearDocumentList: () => void

  // 分析数据
  analysisData: AnalysisData
  setAnalysisItem: (key: keyof AnalysisData, data: any) => void
  clearAnalysisData: () => void

  // A2UI
  a2uiData: any | null
  setA2uiData: (data: any) => void
  appendA2uiComponents: (components: any[]) => void

  // 流式消息
  streamingMessageId: string | null
  streamingContent: string
  streamingAgent: string
  startStream: (id: string, agent: string) => void
  appendStreamToken: (token: string) => void
  finalizeStream: () => void

  // 标准操作
  addMessage: (message: Message) => void
  setMessages: (messages: Message[]) => void
  setConversationId: (id: string | null) => void
  setLoading: (loading: boolean) => void
  clearMessages: () => void
  setConversations: (conversations: ConversationItem[]) => void
  addConversation: (conversation: ConversationItem) => void
  removeConversation: (id: string) => void
  removeConversations: (ids: string[]) => void
  updateConversationTitle: (id: string, title: string) => void
  setChatSidebarOpen: (open: boolean) => void
  toggleChatSidebar: () => void

  // 律师协助
  onlineLawyers: OnlineLawyer[]
  setOnlineLawyers: (lawyers: OnlineLawyer[]) => void
  activeAssistRequest: LawyerAssistRequest | null
  setActiveAssistRequest: (request: LawyerAssistRequest | null) => void
  assistHistory: LawyerAssistRequest[]
  addAssistHistory: (request: LawyerAssistRequest) => void
  lawyerPanelOpen: boolean
  setLawyerPanelOpen: (open: boolean) => void
  addLawyerComment: (comment: LawyerComment) => void

  // 工作台交互
  workspaceConfirmations: WorkspaceConfirmation[]
  addWorkspaceConfirmation: (confirmation: WorkspaceConfirmation) => void
  updateConfirmationSelection: (id: string, selectedIds: string[]) => void
  confirmWorkspaceSelection: (id: string) => void
  removeWorkspaceConfirmation: (id: string) => void
  workspaceActions: WorkspaceAction[]
  setWorkspaceActions: (actions: WorkspaceAction[]) => void
  addWorkspaceAction: (action: WorkspaceAction) => void
  clearWorkspaceActions: () => void
  agentTasks: AgentTask[]
  setAgentTasks: (tasks: AgentTask[]) => void
  addAgentTask: (task: AgentTask) => void
  updateAgentTask: (id: string, updates: Partial<AgentTask>) => void
  clearAgentTasks: () => void

  // 合同审查卡片（仅上传合同时弹出）
  contractReviewVisible: boolean
  contractReviewFile: File | null
  setContractReviewVisible: (visible: boolean) => void
  setContractReviewFile: (file: File | null) => void

  // 签约/盖章工作流
  signingWorkflows: SigningWorkflowItem[]
  addSigningWorkflow: (workflow: SigningWorkflowItem) => void
  updateSigningWorkflow: (id: string, updates: Partial<SigningWorkflowItem>) => void
  removeSigningWorkflow: (id: string) => void
  activeSigningId: string | null
  setActiveSigningId: (id: string | null) => void
  signingPanelOpen: boolean
  setSigningPanelOpen: (open: boolean) => void

  // 重置工作区（新对话时调用）
  resetWorkspace: () => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      conversationId: null,
      isLoading: false,
      conversations: [],
      sidebarOpen: false,

      // 右侧面板
      rightPanelTab: 'smart',
      setRightPanelTab: (tab) => set({ rightPanelTab: tab }),
      documentOverlay: 'none' as DocumentOverlay,
      setDocumentOverlay: (overlay) => set({ documentOverlay: overlay }),

      // 工作台
      agentResults: [],
      addAgentResult: (result) =>
        set((s) => ({ agentResults: [...s.agentResults, result] })),
      clearAgentResults: () => set({ agentResults: [] }),
      thinkingSteps: [],
      addThinkingStep: (step) =>
        set((s) => ({ thinkingSteps: [...s.thinkingSteps, step] })),
      clearThinkingSteps: () => set({ thinkingSteps: [] }),

      // 需求分析
      requirementAnalysis: null,
      setRequirementAnalysis: (data) => set({ requirementAnalysis: data }),

      // Canvas
      canvasContent: null,
      setCanvasContent: (content) => set({ canvasContent: content }),
      updateCanvasText: (text) =>
        set((s) => ({
          canvasContent: s.canvasContent ? { ...s.canvasContent, content: text } : null,
        })),

      // 文档列表
      documentList: [],
      addDocumentToList: (doc) =>
        set((s) => ({
          documentList: [
            { ...doc, updatedAt: Date.now() },
            ...s.documentList.filter((d) => d.id !== doc.id),
          ],
        })),
      removeDocumentFromList: (id) =>
        set((s) => ({ documentList: s.documentList.filter((d) => d.id !== id) })),
      clearDocumentList: () => set({ documentList: [] }),

      // 分析
      analysisData: { riskRadar: null, documentDiff: null, knowledgeGraph: null },
      setAnalysisItem: (key, data) =>
        set((s) => ({
          analysisData: { ...s.analysisData, [key]: data },
        })),
      clearAnalysisData: () =>
        set({ analysisData: { riskRadar: null, documentDiff: null, knowledgeGraph: null } }),

      // A2UI
      a2uiData: null,
      setA2uiData: (data) => set({ a2uiData: data }),
      appendA2uiComponents: (components) =>
        set((s) => {
          const prev = s.a2uiData?.a2ui?.components || s.a2uiData?.components || []
          return {
            a2uiData: { a2ui: { components: [...prev, ...components] } },
          }
        }),

      // 流式消息
      streamingMessageId: null,
      streamingContent: '',
      streamingAgent: '',
      startStream: (id, agent) =>
        set({ streamingMessageId: id, streamingContent: '', streamingAgent: agent }),
      appendStreamToken: (token) =>
        set((s) => ({ streamingContent: s.streamingContent + token })),
      finalizeStream: () =>
        set({ streamingMessageId: null, streamingContent: '', streamingAgent: '' }),

      // 标准操作
      addMessage: (message) =>
        set((state) => ({ messages: [...state.messages, message] })),
      setMessages: (messages) => set({ messages }),
      setConversationId: (id) => set({ conversationId: id }),
      setLoading: (loading) => set({ isLoading: loading }),
      clearMessages: () => set({ messages: [], conversationId: null }),
      setConversations: (conversations) => set({ conversations }),
      addConversation: (conversation) =>
        set((state) => ({
          conversations: [conversation, ...state.conversations.filter((c) => c.id !== conversation.id)],
        })),
      removeConversation: (id) =>
        set((state) => ({
          conversations: state.conversations.filter((c) => c.id !== id),
        })),
      removeConversations: (ids) =>
        set((state) => ({
          conversations: state.conversations.filter((c) => !ids.includes(c.id)),
        })),
      updateConversationTitle: (id, title) =>
        set((state) => ({
          conversations: state.conversations.map((c) => (c.id === id ? { ...c, title } : c)),
        })),
      setChatSidebarOpen: (open) => set({ sidebarOpen: open }),
      toggleChatSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

      // 律师协助
      onlineLawyers: [
        {
          id: 'lawyer-1', name: '张明律师', specialties: ['合同法', '公司法', '知识产权'],
          status: 'online', rating: 4.9, responseTime: '通常3分钟内回复', firm: '金杜律师事务所',
          avatar: '',
        },
        {
          id: 'lawyer-2', name: '李婷律师', specialties: ['劳动法', '人事合规', '竞业禁止'],
          status: 'online', rating: 4.8, responseTime: '通常5分钟内回复', firm: '中伦律师事务所',
          avatar: '',
        },
        {
          id: 'lawyer-3', name: '王强律师', specialties: ['并购重组', '投资基金', '证券法'],
          status: 'busy', rating: 4.7, responseTime: '通常15分钟内回复', firm: '方达律师事务所',
          avatar: '',
        },
        {
          id: 'lawyer-4', name: '赵雪律师', specialties: ['知识产权', '商标注册', '专利诉讼'],
          status: 'online', rating: 4.9, responseTime: '通常5分钟内回复', firm: '君合律师事务所',
          avatar: '',
        },
        {
          id: 'lawyer-5', name: '陈浩律师', specialties: ['刑事辩护', '行政诉讼', '合规审查'],
          status: 'offline', rating: 4.6, responseTime: '通常30分钟内回复', firm: '德恒律师事务所',
          avatar: '',
        },
      ],
      setOnlineLawyers: (lawyers) => set({ onlineLawyers: lawyers }),
      activeAssistRequest: null,
      setActiveAssistRequest: (request) => set({ activeAssistRequest: request }),
      assistHistory: [],
      addAssistHistory: (request) =>
        set((s) => ({ assistHistory: [request, ...s.assistHistory] })),
      lawyerPanelOpen: false,
      setLawyerPanelOpen: (open) => set({ lawyerPanelOpen: open }),
      addLawyerComment: (comment) =>
        set((s) => {
          if (!s.activeAssistRequest) return {}
          return {
            activeAssistRequest: {
              ...s.activeAssistRequest,
              lawyerComments: [...(s.activeAssistRequest.lawyerComments || []), comment],
            },
          }
        }),

      // 工作台交互
      workspaceConfirmations: [],
      addWorkspaceConfirmation: (confirmation) =>
        set((s) => ({ workspaceConfirmations: [...s.workspaceConfirmations, confirmation] })),
      updateConfirmationSelection: (id, selectedIds) =>
        set((s) => ({
          workspaceConfirmations: s.workspaceConfirmations.map((c) =>
            c.id === id ? { ...c, selectedIds } : c
          ),
        })),
      confirmWorkspaceSelection: (id) =>
        set((s) => ({
          workspaceConfirmations: s.workspaceConfirmations.map((c) =>
            c.id === id ? { ...c, status: 'confirmed' as const } : c
          ),
        })),
      removeWorkspaceConfirmation: (id) =>
        set((s) => ({
          workspaceConfirmations: s.workspaceConfirmations.filter((c) => c.id !== id),
        })),
      workspaceActions: [],
      setWorkspaceActions: (actions) => set({ workspaceActions: actions }),
      addWorkspaceAction: (action) =>
        set((s) => ({ workspaceActions: [...s.workspaceActions, action] })),
      clearWorkspaceActions: () => set({ workspaceActions: [] }),
      agentTasks: [],
      setAgentTasks: (tasks) => set({ agentTasks: tasks }),
      addAgentTask: (task) =>
        set((s) => ({
          agentTasks: s.agentTasks.some((t) => t.id === task.id)
            ? s.agentTasks.map((t) => (t.id === task.id ? { ...t, ...task } : t))
            : [...s.agentTasks, task],
        })),
      updateAgentTask: (id, updates) =>
        set((s) => ({
          agentTasks: s.agentTasks.map((t) =>
            t.id === id ? { ...t, ...updates } : t
          ),
        })),
      clearAgentTasks: () => set({ agentTasks: [] }),

      // 签约/盖章工作流
      signingWorkflows: [],
      addSigningWorkflow: (workflow) =>
        set((s) => ({ signingWorkflows: [...s.signingWorkflows, workflow] })),
      updateSigningWorkflow: (id, updates) =>
        set((s) => ({
          signingWorkflows: s.signingWorkflows.map((w) =>
            w.id === id ? { ...w, ...updates, updatedAt: Date.now() } : w
          ),
        })),
      removeSigningWorkflow: (id) =>
        set((s) => ({
          signingWorkflows: s.signingWorkflows.filter((w) => w.id !== id),
        })),
      activeSigningId: null,
      setActiveSigningId: (id) => set({ activeSigningId: id }),
      signingPanelOpen: false,
      setSigningPanelOpen: (open) => set({ signingPanelOpen: open }),

      // 合同审查卡片
      contractReviewVisible: false,
      contractReviewFile: null,
      setContractReviewVisible: (visible) => set({ contractReviewVisible: visible }),
      setContractReviewFile: (file) => set({ contractReviewFile: file }),

      // 重置工作区
      resetWorkspace: () =>
        set({
          agentResults: [],
          thinkingSteps: [],
          requirementAnalysis: null,
          a2uiData: null,
          canvasContent: null,
          analysisData: { riskRadar: null, documentDiff: null, knowledgeGraph: null },
          streamingMessageId: null,
          streamingContent: '',
          streamingAgent: '',
          rightPanelTab: 'smart',
          documentOverlay: 'none' as DocumentOverlay,
          workspaceConfirmations: [],
          workspaceActions: [],
          agentTasks: [],
          contractReviewVisible: false,
          contractReviewFile: null,
        }),
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({
        conversationId: state.conversationId,
        sidebarOpen: state.sidebarOpen,
        conversations: state.conversations,
      }),
    }
  )
)

// ========== UI Store ==========

interface UIState {
  sidebarOpen: boolean
  theme: 'light' | 'dark' | 'system'
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  setTheme: (theme: 'light' | 'dark' | 'system') => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      theme: 'system',
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setTheme: (theme) => set({ theme }),
    }),
    { name: 'ui-storage' }
  )
)

// ========== IM 即时通讯 Store ==========

export interface IMConversation {
  id: string
  type: string
  title: string | null
  avatar_url?: string
  last_message_preview?: string
  last_message_at?: string
  unread_count: number
  case_id?: string
  contract_id?: string
  participants: { user_id: string; role: string; nickname?: string }[]
  created_at: string
}

export interface IMMessage {
  id: string
  conversation_id: string
  sender_id: string
  content: string
  message_type: string
  reply_to_id?: string
  is_recalled: boolean
  created_at: string
  metadata_?: any
  read_by?: string[]
}

interface IMState {
  conversations: IMConversation[]
  activeConversationId: string | null
  messagesMap: Record<string, IMMessage[]>
  typingUsers: Record<string, string[]>
  unreadTotal: number

  setConversations: (convs: IMConversation[]) => void
  setActiveConversation: (id: string | null) => void
  addMessage: (msg: IMMessage) => void
  prependMessages: (convId: string, msgs: IMMessage[]) => void
  updateConversation: (id: string, partial: Partial<IMConversation>) => void
  setTyping: (convId: string, userId: string) => void
  clearTyping: (convId: string, userId: string) => void
  recallMessage: (messageId: string) => void
  markAsRead: (convId: string) => void
  updateReadReceipt: (convId: string, userId: string) => void
  addConversation: (conv: IMConversation) => void
}

export const useIMStore = create<IMState>()(
  persist(
    (set, get) => ({
      conversations: [],
      activeConversationId: null,
      messagesMap: {},
      typingUsers: {},
      unreadTotal: 0,

      setConversations: (convs) => {
        const total = convs.reduce((sum, c) => sum + (c.unread_count || 0), 0)
        set({ conversations: convs, unreadTotal: total })
      },

      setActiveConversation: (id) => set({ activeConversationId: id }),

      addMessage: (msg) =>
        set((s) => {
          const convId = msg.conversation_id
          const existing = s.messagesMap[convId] || []
          // 去重
          if (existing.some((m) => m.id === msg.id)) return {}

          const newMessages = { ...s.messagesMap, [convId]: [...existing, msg] }

          // 更新对话列表中的预览和排序
          const preview =
            msg.message_type === 'text' ? msg.content.slice(0, 100) : `[${msg.message_type}]`
          const updatedConvs = s.conversations.map((c) =>
            c.id === convId
              ? {
                  ...c,
                  last_message_preview: preview,
                  last_message_at: msg.created_at,
                  unread_count:
                    s.activeConversationId === convId ? c.unread_count : c.unread_count + 1,
                }
              : c
          )
          // 按最后消息时间排序
          updatedConvs.sort((a, b) => {
            const ta = a.last_message_at ? new Date(a.last_message_at).getTime() : 0
            const tb = b.last_message_at ? new Date(b.last_message_at).getTime() : 0
            return tb - ta
          })

          const total = updatedConvs.reduce((sum, c) => sum + (c.unread_count || 0), 0)

          return { messagesMap: newMessages, conversations: updatedConvs, unreadTotal: total }
        }),

      prependMessages: (convId, msgs) =>
        set((s) => {
          const existing = s.messagesMap[convId] || []
          const existingIds = new Set(existing.map((m) => m.id))
          const newOnes = msgs.filter((m) => !existingIds.has(m.id))
          return {
            messagesMap: { ...s.messagesMap, [convId]: [...newOnes, ...existing] },
          }
        }),

      updateConversation: (id, partial) =>
        set((s) => ({
          conversations: s.conversations.map((c) => (c.id === id ? { ...c, ...partial } : c)),
        })),

      setTyping: (convId, userId) =>
        set((s) => {
          const current = s.typingUsers[convId] || []
          if (current.includes(userId)) return {}
          return {
            typingUsers: { ...s.typingUsers, [convId]: [...current, userId] },
          }
        }),

      clearTyping: (convId, userId) =>
        set((s) => {
          const current = s.typingUsers[convId] || []
          return {
            typingUsers: {
              ...s.typingUsers,
              [convId]: current.filter((u) => u !== userId),
            },
          }
        }),

      recallMessage: (messageId) =>
        set((s) => {
          const newMap = { ...s.messagesMap }
          for (const convId of Object.keys(newMap)) {
            newMap[convId] = newMap[convId].map((m) =>
              m.id === messageId ? { ...m, is_recalled: true, content: '消息已撤回' } : m
            )
          }
          return { messagesMap: newMap }
        }),

      markAsRead: (convId) =>
        set((s) => {
          const updatedConvs = s.conversations.map((c) =>
            c.id === convId ? { ...c, unread_count: 0 } : c
          )
          const total = updatedConvs.reduce((sum, c) => sum + (c.unread_count || 0), 0)
          return { conversations: updatedConvs, unreadTotal: total }
        }),

      updateReadReceipt: (_convId, _userId) => {
        // 可扩展：更新消息的 read_by 列表
      },

      addConversation: (conv) =>
        set((s) => {
          if (s.conversations.some((c) => c.id === conv.id)) return {}
          return { conversations: [conv, ...s.conversations] }
        }),
    }),
    {
      name: 'im-storage',
      partialize: (state) => ({
        activeConversationId: state.activeConversationId,
      }),
    }
  )
)

// ========== 通知 Store ==========

export interface NotificationItem {
  id: string
  type: 'urgent' | 'warning' | 'info' | 'success'
  title: string
  message: string
  is_read: boolean
  related_link?: string
  event_type?: string
  created_at: string
}

interface NotificationState {
  notifications: NotificationItem[]
  unreadCount: number
  loading: boolean
  activeTab: 'messages' | 'notifications'
  notificationFilter: 'all' | 'unread' | 'approval' | 'case' | 'system' | 'contract'

  setNotifications: (items: NotificationItem[]) => void
  addNotification: (item: NotificationItem) => void
  markNotificationRead: (id: string) => void
  markAllNotificationsRead: () => void
  removeNotification: (id: string) => void
  setLoading: (loading: boolean) => void
  setActiveTab: (tab: 'messages' | 'notifications') => void
  setNotificationFilter: (filter: NotificationState['notificationFilter']) => void
  setUnreadCount: (count: number) => void
}

export const useNotificationStore = create<NotificationState>()(
  persist(
    (set) => ({
      notifications: [],
      unreadCount: 0,
      loading: false,
      activeTab: 'messages',
      notificationFilter: 'all',

      setNotifications: (items) => {
        const unread = items.filter((n) => !n.is_read).length
        set({ notifications: items, unreadCount: unread })
      },

      addNotification: (item) =>
        set((s) => {
          if (s.notifications.some((n) => n.id === item.id)) return {}
          const updated = [item, ...s.notifications]
          return {
            notifications: updated,
            unreadCount: item.is_read ? s.unreadCount : s.unreadCount + 1,
          }
        }),

      markNotificationRead: (id) =>
        set((s) => {
          const target = s.notifications.find((n) => n.id === id)
          if (!target || target.is_read) return {}
          return {
            notifications: s.notifications.map((n) =>
              n.id === id ? { ...n, is_read: true } : n
            ),
            unreadCount: Math.max(0, s.unreadCount - 1),
          }
        }),

      markAllNotificationsRead: () =>
        set((s) => ({
          notifications: s.notifications.map((n) => ({ ...n, is_read: true })),
          unreadCount: 0,
        })),

      removeNotification: (id) =>
        set((s) => {
          const target = s.notifications.find((n) => n.id === id)
          return {
            notifications: s.notifications.filter((n) => n.id !== id),
            unreadCount: target && !target.is_read ? Math.max(0, s.unreadCount - 1) : s.unreadCount,
          }
        }),

      setLoading: (loading) => set({ loading }),
      setActiveTab: (tab) => set({ activeTab: tab }),
      setNotificationFilter: (filter) => set({ notificationFilter: filter }),
      setUnreadCount: (count) => set({ unreadCount: count }),
    }),
    {
      name: 'notification-storage',
      partialize: (state) => ({
        activeTab: state.activeTab,
      }),
    }
  )
)
