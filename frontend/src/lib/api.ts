/**
 * API服务层
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8003/api/v1'

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '')
}

export function getWebSocketBaseUrl(): string {
  const configuredWsBase = import.meta.env.VITE_WS_URL
  if (configuredWsBase) {
    return trimTrailingSlash(configuredWsBase)
  }

  if (/^https?:\/\//.test(API_BASE_URL)) {
    return trimTrailingSlash(API_BASE_URL.replace(/^http/, 'ws'))
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const relativeApiBase = API_BASE_URL.startsWith('/') ? API_BASE_URL : `/${API_BASE_URL}`
  return `${protocol}//${window.location.host}${trimTrailingSlash(relativeApiBase)}`
}

export function buildWebSocketUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${getWebSocketBaseUrl()}${normalizedPath}`
}

// 通用响应结构
export interface UnifiedResponse<T> {
  code: number
  data: T
  message: string
  request_id: string
}

// 通用请求函数
async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  _retry = false
): Promise<T> {
  const token = localStorage.getItem('access_token')
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })
  
  // 处理 401 认证失败：尝试刷新 Token，失败则跳转登录
  if (response.status === 401 && !_retry && token) {
    // Try to refresh token
    const refreshToken = localStorage.getItem('refresh_token')
    if (refreshToken) {
      try {
        const refreshResp = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        })
        if (refreshResp.ok) {
          const refreshData = await refreshResp.json()
          const newToken = refreshData.data?.access_token || refreshData.access_token
          const newRefresh = refreshData.data?.refresh_token || refreshData.refresh_token
          if (newToken) {
            localStorage.setItem('access_token', newToken)
            if (newRefresh) localStorage.setItem('refresh_token', newRefresh)
            return request<T>(endpoint, options, true)
          }
        }
      } catch {
        // Refresh failed, proceed to logout
      }
    }
    // Refresh failed or no refresh token — clear auth and redirect
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    if (!window.location.pathname.startsWith('/login')) {
      window.dispatchEvent(new CustomEvent('auth:redirect', { detail: '/login' }))
    }
    throw new Error('登录已过期，请重新登录')
  }
  
  const json = await response.json().catch(() => ({ 
    code: 500, 
    message: '解析响应失败',
    detail: '请求失败' 
  }))

  if (!response.ok || (json.code && json.code >= 400)) {
    throw new Error(json.message || json.detail || '请求失败')
  }
  
  // 适配 UnifiedResponse 格式，如果 json 包含 data 字段，则返回 data
  if (json && typeof json === 'object' && 'data' in json && 'code' in json) {
    return json.data as T
  }
  
  return json as T
}

// ============ 认证 API ============

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: {
    id: string
    email: string
    name: string
    role: string
  }
}

export interface User {
  id: string
  email: string
  name: string
  role: string
  avatar_url?: string
}

export const authApi = {
  login: (data: LoginRequest) =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  register: (data: { email: string; password: string; name: string }) =>
    request<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  getCurrentUser: () => request<User>('/auth/me'),
  
  updateProfile: (data: { name?: string; avatar_url?: string }) =>
    request<User>('/auth/me', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  logout: () => request('/auth/logout', { method: 'POST' }),

  forgotPassword: (email: string) =>
    request<{ message: string; debug_token?: string }>('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),

  resetPassword: (token: string, new_password: string) =>
    request<{ message: string }>('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ token, new_password }),
    }),

  changePassword: (old_password: string, new_password: string) =>
    request<{ message: string }>('/auth/change-password', {
      method: 'PUT',
      body: JSON.stringify({ old_password, new_password }),
    }),
}

// ============ 对话 API ============

export interface ChatMessage {
  content: string
  conversation_id?: string
  case_id?: string
  agent_name?: string
}

export interface ChatResponse {
  conversation_id: string
  message_id: string
  content: string
  agent: string
  citations: any[]
  actions: any[]
}

export interface Agent {
  name: string
  role: string
  description: string
  tools: string[]
}

export interface StreamEvent {
  type: 'start' | 'thinking' | 'agent_start' | 'agent_working' | 'agent_complete' | 'content' | 'done' | 'error' | 'context_update';
  agent?: string;
  message?: string;
  text?: string;
  full_content?: string;
  context_type?: string;
  data?: any;
}

export const chatApi = {
  sendMessage: (message: ChatMessage) =>
    request<ChatResponse>('/chat/', {
      method: 'POST',
      body: JSON.stringify(message),
    }),
  
  // 流式对话 (SSE)
  streamMessage: async (
    message: ChatMessage,
    onEvent: (event: StreamEvent) => void,
    onError?: (error: Error) => void
  ): Promise<void> => {
    const token = localStorage.getItem('access_token')
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    
    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify(message),
      })
      
      if (!response.ok) {
        throw new Error('流式请求失败')
      }
      
      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法获取响应流')
      
      const decoder = new TextDecoder()
      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              onEvent(data as StreamEvent)
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      }
    } catch (error) {
      if (onError) {
        onError(error as Error)
      } else {
        throw error
      }
    }
  },
  
  getHistory: (params?: { conversation_id?: string; case_id?: string; limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.conversation_id) query.append('conversation_id', params.conversation_id)
    if (params?.case_id) query.append('case_id', params.case_id)
    if (params?.limit) query.append('limit', params.limit.toString())
    return request<any>(`/chat/history?${query}`)
  },

  // 获取对话列表（不传 conversation_id 即返回列表）
  listConversations: (limit: number = 50) =>
    request<any>(`/chat/history?limit=${limit}`),

  // 删除对话
  deleteConversation: (conversationId: string) =>
    request<any>(`/chat/conversations/${conversationId}`, { method: 'DELETE' }),

  // 批量删除对话
  batchDeleteConversations: (conversationIds: string[]) =>
    request<{ deleted: boolean; count: number }>('/chat/conversations/batch-delete', {
      method: 'POST',
      body: JSON.stringify({ conversation_ids: conversationIds }),
    }),

  // 重命名对话
  updateConversationTitle: (conversationId: string, title: string) =>
    request<any>(`/chat/conversations/${conversationId}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    }),

  // 获取对话关联的 Canvas 文档
  getConversationCanvas: (conversationId: string) =>
    request<{ document_id: string; title: string; content: string; type: string; updated_at: string } | null>(
      `/chat/conversations/${conversationId}/canvas`
    ),
  
  getAgents: () => request<{ agents: Agent[] }>('/chat/agents'),
  
  // 新增: 提交情景记忆反馈 (RLHF)
  submitMemoryFeedback: (memoryId: string, rating: number, comment?: string) =>
    request('/chat/feedback/memory', {
      method: 'POST',
      body: JSON.stringify({ memory_id: memoryId, rating, comment }),
    }),

  // WebSocket 连接工厂（带错误/断连回调）
  connectWebSocket: (
    sessionId: string,
    onMessage: (data: any) => void,
    onError?: (error: Event) => void,
    onClose?: (event: CloseEvent) => void,
  ) => {
    const wsUrl = buildWebSocketUrl(`/chat/ws/${sessionId}`);
    
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        console.error('WebSocket 消息解析失败:', e);
      }
    };
    
    ws.onerror = (event) => {
      // React StrictMode 下 effect 会重复挂载/清理，连接尚未建立就被主动关闭时会触发误报。
      // 这类“预连接期”错误交给 onClose 统一处理，避免开发环境噪音掩盖真实异常。
      if (ws.readyState === WebSocket.OPEN) {
        console.warn('[WebSocket] 连接失败，实时功能暂不可用');
      }
      onError?.(event);
    };
    
    ws.onclose = (event) => {
      console.info(`WebSocket 已关闭 (code=${event.code}, reason=${event.reason})`);
      onClose?.(event);
    };
    
    return ws;
  },

  // 新增: 创建人工交接任务
  createHandover: (conversationId: string, summary: string, priority: string = 'normal') =>
    request<{ ticket_id: string; status: string; estimated_response: string; message: string }>('/chat/handover', {
      method: 'POST',
      body: JSON.stringify({ conversation_id: conversationId, summary, priority }),
    }),
}

// ============ 案件 API ============

export interface Case {
  id: string
  case_number?: string
  title: string
  case_type: string
  status: string
  priority: string
  description?: string
  assignee_id?: string
  risk_score?: number
  amount?: number
  deadline?: string
  parties?: any
  created_at: string
  updated_at: string
}

export interface CaseCreate {
  title: string
  case_type: string
  description?: string
  priority?: string
  parties?: any
  deadline?: string
}

export interface CaseListResponse {
  items: Case[]
  total: number
  page: number
  page_size: number
}

export const casesApi = {
  list: (params?: { status?: string; case_type?: string; priority?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams()
    if (params?.status) query.append('status', params.status)
    if (params?.case_type) query.append('case_type', params.case_type)
    if (params?.priority) query.append('priority', params.priority)
    if (params?.page) query.append('page', params.page.toString())
    if (params?.page_size) query.append('page_size', params.page_size.toString())
    return request<CaseListResponse>(`/cases/?${query}`)
  },
  
  get: (id: string) => request<Case>(`/cases/${id}`),
  
  create: (data: CaseCreate) =>
    request<Case>('/cases/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  update: (id: string, data: Partial<CaseCreate>) =>
    request<Case>(`/cases/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  delete: (id: string) =>
    request(`/cases/${id}`, { method: 'DELETE' }),
  
  getTimeline: (id: string) =>
    request<any[]>(`/cases/${id}/timeline`),
  
  analyze: (id: string) =>
    request(`/cases/${id}/analyze`, { method: 'POST' }),
  
  generateBriefing: (id: string) =>
    request<any>(`/cases/${id}/briefing`, { method: 'POST' }),

  // 文档关联
  getDocuments: (caseId: string) =>
    request<Array<{
      id: string
      name: string
      doc_type: string
      file_size: number
      ai_summary?: string
      created_at: string
    }>>(`/cases/${caseId}/documents`),
  
  linkDocument: (caseId: string, documentId: string) =>
    request(`/cases/${caseId}/documents`, {
      method: 'POST',
      body: JSON.stringify({ document_id: documentId }),
    }),
  
  unlinkDocument: (caseId: string, documentId: string) =>
    request(`/cases/${caseId}/documents/${documentId}`, { method: 'DELETE' }),
  
  // 统计
  getStatistics: () =>
    request<{
      total: number
      by_status: Record<string, number>
      by_type: Record<string, number>
      by_priority: Record<string, number>
      workload: Array<{ id: string; name: string; count: number }>
    }>('/cases/statistics/overview'),

  getRecentEvents: (limit: number = 10) =>
    request<Array<{
      id: string
      case_id: string
      case_number: string
      case_title: string
      event_type: string
      title: string
      description: string
      event_time: string
      created_at: string
    }>>(`/cases/events/recent?limit=${limit}`),

  getAlerts: () =>
    request<Array<{
      id: string
      type: string
      title: string
      content: string
      time: string
    }>>('/cases/alerts'),

  getComplianceScore: () =>
    request<{
      score: number
      metrics: {
        doc_compliance: string
        risk_control: string
        process_norm: string
      }
      trend: number
    }>('/cases/statistics/compliance'),
}

// ============ 合同 API ============

export interface Contract {
  id: string
  contract_number?: string
  title: string
  contract_type: string
  status: string
  risk_level?: string
  risk_score?: number
  amount?: number
  effective_date?: string
  expiry_date?: string
  created_at: string
  updated_at: string
}

export interface ContractCreate {
  title: string
  contract_type: string
  party_a?: any
  party_b?: any
  amount?: number
  effective_date?: string
  expiry_date?: string
}

export interface ContractReviewResponse {
  contract_id: string
  risk_score?: number
  risk_level?: string
  summary: string
  risks: any[]
  suggestions: any[]
  key_terms: any
}

export interface DocumentParseResult {
  success: boolean
  text: string
  char_count: number
  word_count: number
  contract_type: string
  key_info: {
    parties?: string[]
    amount?: string
    dates?: string[]
    high_risk_terms?: string[]
  }
  structure: {
    sections?: string[]
    has_signature?: boolean
    has_date?: boolean
    has_parties?: boolean
  }
  error?: string
}

export interface ReviewRiskItem {
  id?: string
  type: string
  title: string
  level: string
  description: string
  suggestion: string
  clause?: string
  original_text?: string
  suggested_text?: string
}

export interface QuickReviewResult {
  summary: string
  risk_level: string
  risk_score: number
  key_risks: ReviewRiskItem[]
  suggestions: string[]
  key_terms: Record<string, string>
  contract_id?: string
}

export interface ContractReviewStreamEvent {
  type: 'start' | 'parsing' | 'parsed' | 'analyzing' | 'key_info' | 'reviewing' | 'risks' | 'suggestions' | 'done' | 'error'
  message?: string
  agent?: string
  data?: any
  contract_type?: string
  char_count?: number
  summary?: string
  risk_level?: string
  risk_score?: number
}

export const contractsApi = {
  list: (params?: { status?: string; contract_type?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams()
    if (params?.status) query.append('status', params.status)
    if (params?.contract_type) query.append('contract_type', params.contract_type)
    if (params?.page) query.append('page', params.page.toString())
    if (params?.page_size) query.append('page_size', params.page_size.toString())
    return request<{ items: Contract[]; total: number; page: number; page_size: number }>(`/contracts/?${query}`)
  },
  
  get: (id: string) => request<Contract>(`/contracts/${id}`),
  
  create: (data: ContractCreate) =>
    request<Contract>('/contracts/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  review: (id: string, contractText: string) =>
    request<ContractReviewResponse>(`/contracts/${id}/review`, {
      method: 'POST',
      body: JSON.stringify({ contract_text: contractText }),
    }),
  
  getRisks: (id: string) =>
    request<any[]>(`/contracts/${id}/risks`),
  
  resolveRisk: (contractId: string, riskId: string, note?: string) =>
    request(`/contracts/${contractId}/risks/${riskId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ resolution_note: note }),
    }),
  
  getTemplates: () => request<{ templates: any[] }>('/contracts/templates'),
  
  // 新增: 解析合同文档
  parseDocument: async (file: File): Promise<DocumentParseResult> => {
    const formData = new FormData()
    formData.append('file', file)
    
    const token = localStorage.getItem('access_token')
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    
    const response = await fetch(`${API_BASE_URL}/contracts/parse`, {
      method: 'POST',
      headers,
      body: formData,
    })
    
    if (!response.ok) {
      throw new Error('文档解析失败')
    }
    
    return response.json()
  },
  
  // 新增: 快速审查合同文本
  quickReview: (text: string, contractType?: string) =>
    request<QuickReviewResult>('/contracts/quick-review', {
      method: 'POST',
      body: JSON.stringify({ text, contract_type: contractType }),
    }),
  
  // 新增: 流式审查合同
  streamReview: async (
    options: { file?: File; text?: string },
    onEvent: (event: ContractReviewStreamEvent) => void,
    onError?: (error: Error) => void
  ): Promise<void> => {
    const formData = new FormData()
    if (options.file) {
      formData.append('file', options.file)
    }
    if (options.text) {
      formData.append('text', options.text)
    }
    
    const token = localStorage.getItem('access_token')
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    
    try {
      const response = await fetch(`${API_BASE_URL}/contracts/review-stream`, {
        method: 'POST',
        headers,
        body: formData,
      })
      
      if (!response.ok) {
        throw new Error('审查请求失败')
      }
      
      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法获取响应流')
      
      const decoder = new TextDecoder()
      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              onEvent(data as ContractReviewStreamEvent)
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      }
    } catch (error) {
      if (onError) {
        onError(error as Error)
      } else {
        throw error
      }
    }
  },
  
  // 新增: 上传并完整审查
  uploadAndReview: async (file: File, title?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (title) formData.append('title', title)
    
    const token = localStorage.getItem('access_token')
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    
    const response = await fetch(`${API_BASE_URL}/contracts/upload-and-review`, {
      method: 'POST',
      headers,
      body: formData,
    })
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '上传审查失败' }))
      throw new Error(error.detail || '上传审查失败')
    }
    
    return response.json()
  },

  // 应用修改建议
  applySuggestions: (contractId: string, acceptedRiskIds: string[]) =>
    request<{ modified_text: string }>(`/contracts/${contractId}/apply-suggestions`, {
      method: 'POST',
      body: JSON.stringify({ accepted_risk_ids: acceptedRiskIds }),
    }),

  // 保存合同文件
  saveContractFile: (contractId: string) =>
    request<{ file_path: string }>(`/contracts/${contractId}/save-file`, {
      method: 'POST',
    }),

  // 下载合同
  downloadContract: async (contractId: string, format: 'pdf' | 'docx' = 'docx'): Promise<void> => {
    const token = localStorage.getItem('access_token')
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`

    const response = await fetch(`${API_BASE_URL}/contracts/${contractId}/download?format=${format}`, {
      headers,
    })

    if (!response.ok) throw new Error('下载失败')

    const blob = await response.blob()
    const contentDisposition = response.headers.get('Content-Disposition')
    let filename = `合同.${format}`
    if (contentDisposition) {
      const match = contentDisposition.match(/filename\*=UTF-8''(.+)/)
      if (match) filename = decodeURIComponent(match[1])
    }

    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  },
}

// ============ 文档 API ============

export interface Document {
  id: string
  name: string
  doc_type: string
  description?: string
  file_size: number
  mime_type?: string
  version: number
  ai_summary?: string
  extracted_text?: string // 支持在线编辑
  tags?: string[]
  created_at: string
  updated_at: string
}

export const documentsApi = {
  list: (params?: { case_id?: string; doc_type?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams()
    if (params?.case_id) query.append('case_id', params.case_id)
    if (params?.doc_type) query.append('doc_type', params.doc_type)
    if (params?.page) query.append('page', params.page.toString())
    if (params?.page_size) query.append('page_size', params.page_size.toString())
    return request<{ items: Document[]; total: number; page: number; page_size: number }>(`/documents/?${query}`)
  },
  
  get: (id: string) => request<Document>(`/documents/${id}`),
  
  upload: async (file: File, data: { doc_type?: string; description?: string; case_id?: string; tags?: string[] }) => {
    const formData = new FormData()
    formData.append('file', file)
    if (data.doc_type) formData.append('doc_type', data.doc_type)
    if (data.description) formData.append('description', data.description)
    if (data.case_id) formData.append('case_id', data.case_id)
    if (data.tags) formData.append('tags', JSON.stringify(data.tags))
    
    const token = localStorage.getItem('access_token')
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    
    const response = await fetch(`${API_BASE_URL}/documents/`, {
      method: 'POST',
      headers,
      body: formData,
    })
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '上传失败' }))
      throw new Error(error.detail || '上传失败')
    }
    
    return response.json() as Promise<Document>
  },
  
  // 新增: 创建纯文本文档
  createText: (data: { name: string; content: string; doc_type?: string; description?: string; case_id?: string; tags?: string[] }) =>
    request<Document>('/documents/text', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // 新增: 更新文档内容
  updateContent: (id: string, data: { content: string; change_summary?: string }) =>
    request<Document>(`/documents/${id}/content`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  // 新增: AI生成文档
  generate: (data: { doc_type: string; scenario: string; requirements: any; case_id?: string }) =>
    request<Document>('/documents/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: { name?: string; description?: string; tags?: string[] }) =>
    request<Document>(`/documents/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  delete: (id: string) =>
    request(`/documents/${id}`, { method: 'DELETE' }),
  
  analyze: (id: string) =>
    request(`/documents/${id}/analyze`, { method: 'POST' }),

  getVersions: (id: string) => request<{ versions: any[] }>(`/documents/${id}/versions`),
}

// ============ 尽职调查 API ============

export interface CompanyProfile {
  name: string
  legal_representative?: string
  registered_capital?: string
  established_date?: string
  business_scope?: string
  address?: string
  company_type?: string
  status: string
}

export interface RiskBreakdown {
  score: number
  label: string
}

export interface CompanyRisks {
  company_name: string
  risk_score: number
  risk_level: string
  breakdown: Record<string, RiskBreakdown>
  risk_points: string[]
  recommendations: string[]
}

export interface CompanyLitigation {
  company_name: string
  summary: {
    total_cases: number
    as_plaintiff: number
    as_defendant: number
    execution_cases: number
    dishonest_records: number
  }
  major_cases: any[]
  case_types: Array<{ type: string; count: number }>
}

export interface CompanyGraph {
  company_name: string
  graph: {
    nodes: Array<{ id: string; name: string; type: string; level: number }>
    edges: Array<{ source: string; target: string; relation: string; label?: string }>
  }
  statistics: {
    shareholders: number
    investments: number
    executives: number
  }
}

export interface InvestigationStreamEvent {
  type: 'start' | 'step' | 'result' | 'step_error' | 'done' | 'error' | 'stage' | 'agent_start' | 'agent_result' | 'conflict' | 'consensus'
  message?: string
  step?: string
  agent?: string
  task?: string
  data?: any
}

export const dueDiligenceApi = {
  investigateCompany: (companyName: string, investigationType: string = 'comprehensive') =>
    request<{
      company_name: string
      investigation_type: string
      timestamp: string
      results: any
      report: any
    }>('/due-diligence/company', {
      method: 'POST',
      body: JSON.stringify({ company_name: companyName, investigation_type: investigationType }),
    }),
  
  // 流式调查
  streamInvestigate: async (
    companyName: string,
    investigationType: string,
    onEvent: (event: InvestigationStreamEvent) => void,
    onError?: (error: Error) => void
  ): Promise<void> => {
    const token = localStorage.getItem('access_token')
    const headers: HeadersInit = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`

    // 后端最多重试 3 次（每次 60s + 等待间隔），前端总超时 200s
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 200000)

    try {
      const response = await fetch(`${API_BASE_URL}/due-diligence/company/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ company_name: companyName, investigation_type: investigationType }),
        signal: controller.signal,
      })
      
      if (!response.ok) throw new Error('调查请求失败')
      
      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法获取响应流')
      
      const decoder = new TextDecoder()
      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              onEvent(data as InvestigationStreamEvent)
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      }
    } catch (error) {
      clearTimeout(timeoutId)
      if (onError) onError(error as Error)
      else throw error
      return
    }
    clearTimeout(timeoutId)
  },
  
  getCompanyProfile: (companyName: string) =>
    request<{ company_name: string; profile: CompanyProfile; source: string }>(
      `/due-diligence/company/${encodeURIComponent(companyName)}/profile`
    ),
  
  getCompanyRisks: (companyName: string) =>
    request<CompanyRisks>(`/due-diligence/company/${encodeURIComponent(companyName)}/risks`),
  
  getCompanyLitigation: (companyName: string) =>
    request<CompanyLitigation>(`/due-diligence/company/${encodeURIComponent(companyName)}/litigation`),
  
  getCompanyGraph: (companyName: string, depth: number = 1) =>
    request<CompanyGraph>(`/due-diligence/company/${encodeURIComponent(companyName)}/graph?depth=${depth}`),
  
  searchCompanies: (keyword: string, limit: number = 10) =>
    request<{
      keyword: string
      total: number
      results: Array<{
        name: string
        credit_code: string
        legal_representative: string
        status: string
      }>
    }>(`/due-diligence/search?keyword=${encodeURIComponent(keyword)}&limit=${limit}`),

  // 调查历史
  getInvestigationHistory: (page: number = 1, pageSize: number = 20) =>
    request<any[]>(`/due-diligence/investigations?page=${page}&page_size=${pageSize}`),

  getInvestigation: (id: string) =>
    request<any>(`/due-diligence/investigations/${id}`),

  // 报告生成
  generateReport: (companyName: string) =>
    request<any>('/due-diligence/report/generate', {
      method: 'POST',
      body: JSON.stringify({ company_name: companyName }),
    }),

  // 场景推演
  simulateScenario: (scenarioId: string, companyName: string, currentRisk?: any) =>
    request<any>('/due-diligence/simulate', {
      method: 'POST',
      body: JSON.stringify({ scenario_id: scenarioId, company_name: companyName, current_risk: currentRisk }),
    }),

  listScenarios: () =>
    request<any[]>('/due-diligence/simulate/scenarios'),
}


// ============ 知识库 API ============

export interface KnowledgeBase {
  id: string
  name: string
  knowledge_type: string
  description?: string
  doc_count: number
  is_public: boolean
  created_at: string
}

export interface KnowledgeDocument {
  id: string
  title: string
  source?: string
  summary?: string
  is_processed: boolean
  tags?: string[]
  created_at: string
}

export const knowledgeApi = {
  listBases: (params?: { knowledge_type?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams()
    if (params?.knowledge_type) query.append('knowledge_type', params.knowledge_type)
    if (params?.page) query.append('page', params.page.toString())
    if (params?.page_size) query.append('page_size', params.page_size.toString())
    return request<{ items: KnowledgeBase[]; total: number; page: number; page_size: number }>(`/knowledge/bases?${query}`)
  },
  
  getBase: (id: string) => request<KnowledgeBase>(`/knowledge/bases/${id}`),
  
  createBase: (data: { name: string; knowledge_type?: string; description?: string; is_public?: boolean }) =>
    request<KnowledgeBase>('/knowledge/bases', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  listDocuments: (kbId: string, params?: { page?: number; page_size?: number }) => {
    const query = new URLSearchParams()
    if (params?.page) query.append('page', params.page.toString())
    if (params?.page_size) query.append('page_size', params.page_size.toString())
    return request<{ items: KnowledgeDocument[]; total: number; page: number; page_size: number }>(`/knowledge/bases/${kbId}/documents?${query}`)
  },
  
  addDocument: (kbId: string, data: { title: string; content: string; source?: string; tags?: string[] }) =>
    request<KnowledgeDocument>(`/knowledge/bases/${kbId}/documents`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  search: (query: string, kbIds?: string[], topK: number = 10, hybrid: boolean = true) =>
    request<any[]>('/knowledge/search', {
      method: 'POST',
      body: JSON.stringify({ query, kb_ids: kbIds, top_k: topK, hybrid }),
    }),
  
  // 新增: 深度研究
  deepResearch: (topic: string, kbIds?: string[]) =>
    request<any>('/knowledge/deep-research', {
      method: 'POST',
      body: JSON.stringify({ topic, kb_ids: kbIds }),
    }),
  
  deleteDocument: (docId: string) =>
    request(`/knowledge/documents/${docId}`, { method: 'DELETE' }),

  // 文件上传并索引
  uploadDocument: (kbId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const token = localStorage.getItem('access_token')
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    return fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8003/api/v1'}/knowledge/bases/${kbId}/upload`, {
      method: 'POST',
      headers,
      body: formData,
    }).then(async res => {
      const json = await res.json()
      if (!res.ok || (json.code && json.code >= 400)) throw new Error(json.message || '上传失败')
      return json.data || json
    })
  },

  // RAG 智能问答
  ragQuery: (query: string, kbIds?: string[], systemPrompt?: string) =>
    request<{ answer: string; sources: any[]; context_used: boolean; chunks_used?: number }>('/knowledge/rag-query', {
      method: 'POST',
      body: JSON.stringify({ query, kb_ids: kbIds, system_prompt: systemPrompt }),
    }),

  // 索引文档
  indexDocument: (kbId: string, data: { title: string; content: string; source?: string; metadata?: any }) =>
    request<{ success: boolean; doc_id?: string; chunk_count: number }>(`/knowledge/bases/${kbId}/index`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // 向量存储信息
  getVectorStoreInfo: () =>
    request<{ available: boolean; embedding: any; collections: any[] }>('/knowledge/vector-store/info'),

  // 编辑知识库
  updateBase: (id: string, data: { name?: string; description?: string; knowledge_type?: string; is_public?: boolean }) =>
    request<KnowledgeBase>(`/knowledge/bases/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  // 删除知识库
  deleteBase: (id: string) =>
    request(`/knowledge/bases/${id}`, { method: 'DELETE' }),

  // 获取文档完整内容
  getDocument: (docId: string) =>
    request<KnowledgeDocument & { content: string; source_url?: string; chunk_count?: number; law_category?: string; effective_date?: string; issuing_authority?: string }>(`/knowledge/documents/${docId}`),

  // 更新文档
  updateDocument: (docId: string, data: { title?: string; content?: string; source?: string; tags?: string[]; law_category?: string; effective_date?: string; issuing_authority?: string }) =>
    request<KnowledgeDocument>(`/knowledge/documents/${docId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  // 知识库统计
  getBaseStats: (kbId: string) =>
    request<{ kb_id: string; name: string; doc_count: number; processed_count: number; total_chunks: number; categories: Record<string, number> }>(`/knowledge/bases/${kbId}/stats`),

  // 导出知识库
  exportBase: (kbId: string) =>
    request<{ knowledge_base: any; documents: any[]; exported_at: string; total_documents: number }>(`/knowledge/bases/${kbId}/export`, { method: 'POST' }),

  // 批量上传
  batchUpload: (kbId: string, files: File[]) => {
    const formData = new FormData()
    files.forEach(f => formData.append('files', f))
    const token = localStorage.getItem('access_token')
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    return fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8003/api/v1'}/knowledge/bases/${kbId}/batch-upload`, {
      method: 'POST', headers, body: formData,
    }).then(async res => {
      const json = await res.json()
      if (!res.ok) throw new Error(json.message || '上传失败')
      return json.data || json
    })
  },
}

// ============ 知识中心 API (经验记忆 + 图谱 + 自进化) ============

export interface MemoryItem {
  memory_id?: string
  task?: string
  plan: any[]
  result_summary?: string
  timestamp?: string
  rating?: number
  similarity_score?: number
}

export interface EvolutionStatus {
  total_memories: number
  avg_rating: number
  high_rated_count: number
  low_rated_count: number
  unrated_count: number
  last_evolution_time?: string
  evolution_tasks_total: number
}

export interface GraphNode {
  id: string
  label: string
  type: 'entity' | 'law' | 'document' | 'query' | 'conclusion'
}

export interface GraphEdge {
  source: string
  target: string
  relation: string
  label?: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  total?: number
  center_entity?: string
}

export interface GraphStats {
  available: boolean
  total_nodes: number
  total_edges: number
  node_types: Record<string, number>
  relation_types: Record<string, number>
}

export const knowledgeCenterApi = {
  // 经验记忆
  createMemory: (data: { task_description: string; plan: any[]; final_result: any; user_feedback?: any }) =>
    request<{ memory_id: string }>('/knowledge-center/memories', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  searchMemories: (query: string, topK: number = 5, scoreThreshold: number = 0.5) =>
    request<{ items: MemoryItem[]; total: number; query: string }>('/knowledge-center/memories/search', {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK, score_threshold: scoreThreshold }),
    }),

  getRecentMemories: (limit: number = 20) =>
    request<{ items: MemoryItem[]; total: number }>(`/knowledge-center/memories/recent?limit=${limit}`),

  updateMemoryFeedback: (memoryId: string, rating: number, comment: string = '') =>
    request(`/knowledge-center/memories/${memoryId}/feedback`, {
      method: 'PUT',
      body: JSON.stringify({ rating, comment }),
    }),

  // 自进化
  getEvolutionStatus: () =>
    request<EvolutionStatus>('/knowledge-center/evolution/status'),

  // 知识图谱
  getGraphOverview: () =>
    request<GraphStats>('/knowledge-center/graph/overview'),

  searchGraph: (query: string, depth: number = 1, limit: number = 30) =>
    request<GraphData>(`/knowledge-center/graph/search?query=${encodeURIComponent(query)}&depth=${depth}&limit=${limit}`),

  getEntityRelations: (entityName: string, depth: number = 1) =>
    request<GraphData>(`/knowledge-center/graph/entity/${encodeURIComponent(entityName)}?depth=${depth}`),

  getEntityDetail: (entityName: string) =>
    request<any>(`/knowledge-center/graph/entity/${encodeURIComponent(entityName)}/detail`),

  // 图谱实体 CRUD
  createEntity: (data: { name: string; entity_type?: string; properties?: Record<string, any> }) =>
    request('/knowledge-center/graph/entity', { method: 'POST', body: JSON.stringify(data) }),

  updateEntity: (name: string, properties: Record<string, any>) =>
    request(`/knowledge-center/graph/entity/${encodeURIComponent(name)}`, {
      method: 'PUT', body: JSON.stringify({ properties }),
    }),

  deleteEntity: (name: string) =>
    request(`/knowledge-center/graph/entity/${encodeURIComponent(name)}`, { method: 'DELETE' }),

  // 图谱关系 CRUD
  createRelation: (data: { subject: string; predicate: string; object: string }) =>
    request('/knowledge-center/graph/relation', { method: 'POST', body: JSON.stringify(data) }),

  deleteRelation: (data: { subject: string; predicate: string; object: string }) =>
    request('/knowledge-center/graph/relation', { method: 'DELETE', body: JSON.stringify(data) }),

  // 导出图谱
  exportGraph: (entityType?: string, limit?: number) => {
    const params = new URLSearchParams()
    if (entityType) params.append('entity_type', entityType)
    if (limit) params.append('limit', limit.toString())
    return request<{ triples: any[]; total: number }>(`/knowledge-center/graph/export?${params}`, { method: 'POST' })
  },

  // LLM实体抽取
  extractEntities: (text: string, autoImport: boolean = false) =>
    request<{ entities: any[]; relations: any[]; imported_entities?: number; imported_relations?: number }>('/knowledge-center/graph/extract', {
      method: 'POST', body: JSON.stringify({ text, auto_import: autoImport }),
    }),

  // 获取图谱实体类型
  getEntityTypes: () =>
    request<{ type: string; count: number; color: string }[]>('/knowledge-center/graph/types'),

  // 最短路径
  getShortestPath: (from: string, to: string) =>
    request<{ path_length: number; nodes: any[]; relationships: any[]; found: boolean }>(`/knowledge-center/graph/path?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`),

  // 子图
  getSubgraph: (entityName: string, depth?: number, maxNodes?: number) => {
    const params = new URLSearchParams()
    if (depth) params.append('depth', depth.toString())
    if (maxNodes) params.append('max_nodes', maxNodes.toString())
    return request<{ center: string; nodes: any[]; edges: any[] }>(`/knowledge-center/graph/subgraph/${encodeURIComponent(entityName)}?${params}`)
  },
}

// ============ LLM配置 API ============

export interface LLMProvider {
  name: string
  base_url: string
  models: {
    llm?: string[]
    embedding?: string[]
  }
  supports_streaming: boolean
  api_key_required: boolean
  is_local?: boolean
  openai_compatible?: boolean
  note?: string
}

export interface LLMConfig {
  id: string
  name: string
  provider: string
  config_type: string
  model_name: string
  description?: string
  api_base_url?: string
  api_key_masked?: string
  max_tokens: number
  temperature: number
  top_p?: number
  frequency_penalty?: number
  presence_penalty?: number
  is_active: boolean
  is_default: boolean
  local_endpoint?: string
  local_model_path?: string
  context_length?: number
  extra_params?: Record<string, any>
  total_calls?: number
  total_tokens?: number
  avg_latency?: number
  created_at: string
  updated_at: string
}

export interface LLMConfigCreate {
  name: string
  provider: string
  model_name: string
  config_type?: string
  description?: string
  api_key?: string
  api_base_url?: string
  max_tokens?: number
  temperature?: number
  top_p?: number
  frequency_penalty?: number
  presence_penalty?: number
  is_default?: boolean
  local_endpoint?: string
  local_model_path?: string
  context_length?: number
  extra_params?: Record<string, any>
  headers?: Record<string, string>
}

export interface TestConnectionRequest {
  provider: string
  api_key?: string
  api_base_url: string
  model_name: string
  headers?: Record<string, string>
}

export interface TestConnectionResponse {
  success: boolean
  message: string
  error?: string
  response_time_ms?: number
}

export const llmApi = {
  // 获取所有提供商
  getProviders: () => request<Record<string, LLMProvider>>('/llm/providers'),
  
  // 获取指定提供商的模型
  getProviderModels: (provider: string) => 
    request<{
      provider: string
      name: string
      models: { llm?: string[]; embedding?: string[] }
      base_url: string
      api_key_required: boolean
      is_local: boolean
      note?: string
    }>(`/llm/providers/${provider}/models`),
  
  // 列出配置
  listConfigs: (params?: { 
    config_type?: string
    provider?: string
    is_active?: boolean
    page?: number
    page_size?: number 
  }) => {
    const query = new URLSearchParams()
    if (params?.config_type) query.append('config_type', params.config_type)
    if (params?.provider) query.append('provider', params.provider)
    if (params?.is_active !== undefined) query.append('is_active', params.is_active.toString())
    if (params?.page) query.append('page', params.page.toString())
    if (params?.page_size) query.append('page_size', params.page_size.toString())
    return request<{ items: LLMConfig[]; total: number; page: number; page_size: number }>(`/llm/configs?${query}`)
  },
  
  // 获取单个配置
  getConfig: (id: string) => request<LLMConfig>(`/llm/configs/${id}`),
  
  // 获取默认配置
  getDefaultConfig: (configType: string = 'llm') => 
    request<LLMConfig>(`/llm/configs/default?config_type=${configType}`),
  
  // 创建配置
  createConfig: (data: LLMConfigCreate) =>
    request<LLMConfig>('/llm/configs', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  // 更新配置
  updateConfig: (id: string, data: Partial<LLMConfigCreate>) =>
    request<LLMConfig>(`/llm/configs/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  // 删除配置
  deleteConfig: (id: string) =>
    request<{ success: boolean; message: string }>(`/llm/configs/${id}`, { method: 'DELETE' }),
  
  // 设置默认配置
  setDefault: (id: string) =>
    request<LLMConfig>(`/llm/configs/${id}/set-default`, { method: 'POST' }),
  
  // 切换启用状态
  toggleActive: (id: string) =>
    request<LLMConfig>(`/llm/configs/${id}/toggle-active`, { method: 'POST' }),
  
  // 测试连接
  testConnection: (data: TestConnectionRequest) =>
    request<TestConnectionResponse>('/llm/test-connection', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  // 测试已保存配置的连接
  testConfigConnection: (id: string) =>
    request<TestConnectionResponse>(`/llm/configs/${id}/test`, { method: 'POST' }),
}

// ============ 舆情监控 API ============

export interface SentimentMonitor {
  id: string
  name: string
  keywords: string[]
  sources?: string[]
  alert_threshold: number
  is_active: boolean
  total_records: number
  negative_count: number
  alert_count: number
  last_scan_at?: string
  created_at: string
  updated_at: string
}

export interface SentimentRecord {
  id: string
  keyword: string
  title?: string
  content: string
  source?: string
  source_type: string
  sentiment_type: string
  sentiment_score: number
  risk_level: string
  risk_score: number
  summary?: string
  created_at: string
}

export interface SentimentAlert {
  id: string
  alert_type: string
  alert_level: string
  title: string
  message: string
  is_read: boolean
  is_handled: boolean
  handled_at?: string
  handle_note?: string
  created_at: string
}

export interface SentimentAnalyzeRequest {
  content: string
  keyword: string
  source?: string
  source_type?: string
  title?: string
  save_record?: boolean
}

export interface SentimentAnalyzeResponse {
  sentiment_type: string
  sentiment_score: number
  risk_level: string
  risk_score: number
  analysis?: string
  record_id?: string
}

export interface SentimentStatistics {
  period: string
  total_records: number
  sentiment_distribution: Record<string, number>
  risk_distribution: Record<string, number>
  alerts: { total: number; unread: number }
  daily_trend: Array<{ date: string; count: number }>
}

export const sentimentApi = {
  // 监控配置
  listMonitors: (params?: { is_active?: boolean; page?: number; page_size?: number }) => {
    const query = new URLSearchParams()
    if (params?.is_active !== undefined) query.append('is_active', params.is_active.toString())
    if (params?.page) query.append('page', params.page.toString())
    if (params?.page_size) query.append('page_size', params.page_size.toString())
    return request<{ items: SentimentMonitor[]; total: number; page: number; page_size: number }>(`/sentiment/monitors?${query}`)
  },
  
  getMonitor: (id: string) => request<SentimentMonitor>(`/sentiment/monitors/${id}`),
  
  createMonitor: (data: { name: string; keywords: string[]; sources?: string[]; alert_threshold?: number }) =>
    request<SentimentMonitor>('/sentiment/monitors', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  updateMonitor: (id: string, data: Partial<{ name: string; keywords: string[]; is_active: boolean; alert_threshold: number }>) =>
    request<SentimentMonitor>(`/sentiment/monitors/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  deleteMonitor: (id: string) =>
    request(`/sentiment/monitors/${id}`, { method: 'DELETE' }),
  
  toggleMonitor: (id: string, is_active: boolean) =>
    request(`/sentiment/monitors/${id}/toggle?is_active=${is_active}`, { method: 'POST' }),
  
  // 舆情分析
  analyze: (data: SentimentAnalyzeRequest) =>
    request<SentimentAnalyzeResponse>('/sentiment/analyze', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  // 舆情记录
  listRecords: (params?: { 
    monitor_id?: string
    keyword?: string
    sentiment_type?: string
    risk_level?: string
    page?: number
    page_size?: number 
  }) => {
    const query = new URLSearchParams()
    if (params?.monitor_id) query.append('monitor_id', params.monitor_id)
    if (params?.keyword) query.append('keyword', params.keyword)
    if (params?.sentiment_type) query.append('sentiment_type', params.sentiment_type)
    if (params?.risk_level) query.append('risk_level', params.risk_level)
    if (params?.page) query.append('page', params.page.toString())
    if (params?.page_size) query.append('page_size', params.page_size.toString())
    return request<{ items: SentimentRecord[]; total: number; page: number; page_size: number }>(`/sentiment/records?${query}`)
  },
  
  getRecord: (id: string) => request<SentimentRecord>(`/sentiment/records/${id}`),
  
  // 预警管理
  listAlerts: (params?: { is_read?: boolean; is_handled?: boolean; alert_level?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams()
    if (params?.is_read !== undefined) query.append('is_read', params.is_read.toString())
    if (params?.is_handled !== undefined) query.append('is_handled', params.is_handled.toString())
    if (params?.alert_level) query.append('alert_level', params.alert_level)
    if (params?.page) query.append('page', params.page.toString())
    if (params?.page_size) query.append('page_size', params.page_size.toString())
    return request<{ items: SentimentAlert[]; total: number; page: number; page_size: number }>(`/sentiment/alerts?${query}`)
  },
  
  getAlert: (id: string) => request<SentimentAlert>(`/sentiment/alerts/${id}`),
  
  markAlertRead: (id: string) =>
    request(`/sentiment/alerts/${id}/read`, { method: 'POST' }),
  
  handleAlert: (id: string, handle_note?: string) =>
    request(`/sentiment/alerts/${id}/handle`, {
      method: 'POST',
      body: JSON.stringify({ handle_note }),
    }),
  
  // 统计报告
  getStatistics: (days: number = 7) =>
    request<SentimentStatistics>(`/sentiment/statistics?days=${days}`),
  
  generateReport: (period: string = 'daily', focus_keywords?: string[]) =>
    request('/sentiment/reports', {
      method: 'POST',
      body: JSON.stringify({ period, focus_keywords }),
    }),
}

// ============ 协作编辑 API ============

export interface CollaborationSession {
  id: string
  document_id: string
  name?: string
  status: string
  current_version: number
  active_collaborators: number
  max_collaborators: number
  total_edits?: number
  started_at: string
  last_activity_at: string
  created_at: string
}

export interface Collaborator {
  id: string
  user_id?: string
  nickname?: string
  role: string
  is_online: boolean
  color?: string
  cursor_position?: any
  last_seen_at: string
}

export const collaborationApi = {
  // 会话管理
  listSessions: (params?: { document_id?: string; status?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams()
    if (params?.document_id) query.append('document_id', params.document_id)
    if (params?.status) query.append('status', params.status)
    if (params?.page) query.append('page', params.page.toString())
    if (params?.page_size) query.append('page_size', params.page_size.toString())
    return request<{ items: CollaborationSession[]; total: number; page: number; page_size: number }>(`/collaboration/sessions?${query}`)
  },
  
  getSession: (id: string) => request<CollaborationSession>(`/collaboration/sessions/${id}`),
  
  createSession: (data: { document_id: string; name?: string; max_collaborators?: number }) =>
    request<CollaborationSession>('/collaboration/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  closeSession: (id: string) =>
    request(`/collaboration/sessions/${id}/close`, { method: 'POST' }),
  
  // 协作者
  getCollaborators: (sessionId: string) =>
    request<Collaborator[]>(`/collaboration/sessions/${sessionId}/collaborators`),
  
  // 新增: 提交版本
  commit: (sessionId: string, message: string) =>
    request<any>(`/collaboration/sessions/${sessionId}/commit`, {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, message }),
    }),

  // 新增: 获取配置
  getConfig: () => request<any>('/collaboration/config'),

  // ===== [S-06] WebSocket 连接 - 不再通过 URL 传递 Token =====
  // 原因：Token 在 URL 参数中会被记录到服务器日志、浏览器历史、代理日志
  // 修复方式：URL 中不再携带 token，改为连接建立后通过首条 auth 消息发送
  connectWebSocket: (documentId: string, userId?: string, userName?: string) => {
    const ws = new WebSocket(buildWebSocketUrl(`/collaboration/ws/document/${documentId}`))

    return {
      ws,
      // ===== [S-06] 新增 auth 方法：连接后首先发送认证消息 =====
      auth: () => {
        const token = localStorage.getItem('access_token')
        if (ws.readyState === WebSocket.OPEN && token) {
          ws.sendJSON({
            type: 'auth',
            data: { token },
          })
        }
      },
      // 发送加入消息
      join: (initialContent?: string) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.sendJSON({
            type: 'join',
            data: {
              user_id: userId,
              user_name: userName || '用户',
              initial_content: initialContent || '',
            },
          })
        }
      },
      // 发送操作
      sendOperation: (operation: { type: string; position: number; length?: number; content?: string; attributes?: any }) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.sendJSON({
            type: 'operation',
            data: operation,
          })
        }
      },
      // 更新光标
      updateCursor: (position: number, selection?: { from: number; to: number }) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.sendJSON({
            type: 'cursor_update',
            data: { position, selection },
          })
        }
      },
      // 添加评论
      addComment: (content: string, position: { from: number; to: number }) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.sendJSON({
            type: 'comment',
            data: { content, position },
          })
        }
      },
      // 解决评论
      resolveComment: (commentId: string) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.sendJSON({
            type: 'resolve_comment',
            data: { comment_id: commentId },
          })
        }
      },
      // 保存文档
      save: (content: string) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.sendJSON({
            type: 'save',
            data: { content },
          })
        }
      },
      // 心跳
      ping: () => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.sendJSON({
            type: 'ping',
            data: { timestamp: Date.now() },
          })
        }
      },
    }
  },
}

// 扩展 WebSocket 原型
declare global {
  interface WebSocket {
    sendJSON(data: any): void
  }
}

WebSocket.prototype.sendJSON = function(data: any) {
  this.send(JSON.stringify(data))
}

// ============ LIC 抓取 API ============

export const licApi = {
  startCrawl: (data: { url?: string; keyword: string; task_id: string }) =>
    request<{ message: string; task_id: string }>('/lic/crawl', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  // 新增: 触发自进化抓取
  evolve: () =>
    request<any>('/lic/evolve', {
      method: 'POST',
    }),
}

// ============ 资产管理 API ============

export interface Asset {
  id: string
  name: string
  type: string
  originalValue: number
  currentValue: number
  acquisitionDate?: string
}

export interface AssetCreate {
  name: string
  type: string
  originalValue: number
  currentValue: number
  acquisitionDate?: string
}

export interface AssetUpdate {
  name?: string
  type?: string
  originalValue?: number
  currentValue?: number
  acquisitionDate?: string
}

export const assetsApi = {
  list: () => request<Asset[]>('/assets/'),
  
  create: (data: AssetCreate) =>
    request<Asset>('/assets/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  update: (id: string, data: AssetUpdate) =>
    request<Asset>(`/assets/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  delete: (id: string) =>
    request(`/assets/${id}`, { method: 'DELETE' }),
}

// ============ MCP API ============

export interface McpServerConfig {
  id: string
  name: string
  description?: string
  type: string
  command?: string
  args?: string[]
  env?: Record<string, string>
  url?: string
  is_enabled: boolean
  cached_tools?: any[]
  created_at: string
}

export interface McpServerCreate {
  name: string
  description?: string
  type: string
  command?: string
  args?: string[]
  env?: Record<string, string>
  url?: string
  is_enabled: boolean
}

export const mcpApi = {
  listServers: () => request<McpServerConfig[]>('/mcp/servers'),
  
  create: (data: McpServerCreate) =>
    request<McpServerConfig>('/mcp/servers', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  update: (id: string, data: Partial<McpServerCreate>) =>
    request<McpServerConfig>(`/mcp/servers/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  delete: (id: string) =>
    request(`/mcp/servers/${id}`, { method: 'DELETE' }),
  
  connect: (id: string) =>
    request<{ status: string; tools_count: number; tools: any[] }>(`/mcp/servers/${id}/connect`, {
      method: 'POST',
    }),
  
  getTools: () => request<any[]>('/mcp/tools'),
}

// ============ 通知 API ============

export interface Notification {
  id: string
  type: string
  title: string
  message: string
  is_read: boolean
  related_link?: string
  event_type?: string
  created_at: string
}

export const notificationsApi = {
  /** 获取通知列表，支持按事件类型筛选 */
  list: (params?: { limit?: number; unread_only?: boolean; event_type?: string }) => {
    const query = new URLSearchParams()
    if (params?.limit) query.append('limit', params.limit.toString())
    if (params?.unread_only) query.append('unread_only', params.unread_only.toString())
    if (params?.event_type) query.append('event_type', params.event_type)
    return request<{ data: Notification[]; total: number }>(`/notifications/?${query}`)
  },

  /** 获取未读通知总数（轻量接口） */
  getUnreadCount: () =>
    request<{ count: number }>('/notifications/unread-count'),

  markAsRead: (id: string) =>
    request<Notification>(`/notifications/${id}/read`, { method: 'POST' }),

  markAllAsRead: () =>
    request<{ message: string; count: number }>('/notifications/read-all', { method: 'POST' }),

  delete: (id: string) =>
    request(`/notifications/${id}`, { method: 'DELETE' }),

  getPreferences: () =>
    request<NotificationPreference[]>('/notifications/preferences'),

  updatePreferences: (preferences: NotificationPreference[]) =>
    request<NotificationPreference[]>('/notifications/preferences', {
      method: 'PUT',
      body: JSON.stringify({ preferences }),
    }),
}

export interface NotificationPreference {
  event_type: string
  channel: string
  enabled: boolean
}

// ============ 任务管理 API ============

export interface TaskItem {
  id: string
  title: string
  description?: string
  status: string
  priority: string
  dueDate?: string
  assignee?: string
  caseId?: string
  caseTitle?: string
  tags: string[]
  createdAt?: string
}

export const tasksApi = {
  list: (params?: { status?: string; priority?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams()
    if (params?.status) query.append('status', params.status)
    if (params?.priority) query.append('priority', params.priority)
    if (params?.page) query.append('page', params.page.toString())
    if (params?.page_size) query.append('page_size', params.page_size.toString())
    return request<{ items: TaskItem[]; total: number }>(`/tasks/?${query}`)
  },
  create: (data: Partial<TaskItem>) =>
    request<TaskItem>('/tasks/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<TaskItem>) =>
    request<TaskItem>(`/tasks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  updateStatus: (id: string, status: string) =>
    request<TaskItem>(`/tasks/${id}/status?status=${status}`, { method: 'PATCH' }),
  delete: (id: string) =>
    request(`/tasks/${id}`, { method: 'DELETE' }),
}

// ============ 案源管理 API ============

export interface LeadItem {
  id: string
  clientName: string
  contactInfo?: string
  source?: string
  caseType?: string
  estimatedAmount: number
  stage: string
  assignee?: string
  followUps: Array<{ id: string; date: string; content: string; type: string }>
  createdAt?: string
}

export const leadsApi = {
  list: (params?: { stage?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams()
    if (params?.stage) query.append('stage', params.stage)
    if (params?.page) query.append('page', params.page.toString())
    if (params?.page_size) query.append('page_size', params.page_size.toString())
    return request<{ items: LeadItem[]; total: number }>(`/leads/?${query}`)
  },
  create: (data: Partial<LeadItem>) =>
    request<LeadItem>('/leads/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<LeadItem>) =>
    request<LeadItem>(`/leads/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  updateStage: (id: string, stage: string) =>
    request<LeadItem>(`/leads/${id}/stage?stage=${stage}`, { method: 'PATCH' }),
  addFollowUp: (id: string, followUp: { date: string; content: string; type: string }) =>
    request<LeadItem>(`/leads/${id}/follow-ups`, { method: 'POST', body: JSON.stringify(followUp) }),
  delete: (id: string) =>
    request(`/leads/${id}`, { method: 'DELETE' }),
}

// ============ 律师精英 API ============

export interface ExpertItem {
  id: string
  name: string
  title?: string
  specialty: string[]
  yearsOfExperience: number
  rating: number
  casesHandled: number
  description?: string
  achievements: string[]
}

export const expertsApi = {
  list: (params?: { specialty?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams()
    if (params?.specialty) query.append('specialty', params.specialty)
    if (params?.page) query.append('page', params.page.toString())
    if (params?.page_size) query.append('page_size', params.page_size.toString())
    return request<{ items: ExpertItem[]; total: number }>(`/experts/?${query}`)
  },
  get: (id: string) => request<ExpertItem>(`/experts/${id}`),
  create: (data: Partial<ExpertItem>) =>
    request<ExpertItem>('/experts/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<ExpertItem>) =>
    request<ExpertItem>(`/experts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: string) =>
    request(`/experts/${id}`, { method: 'DELETE' }),
}

// ============ 司法学院 API ============

export interface CourseItem {
  id: string
  title: string
  instructor?: string
  category: string
  duration?: string
  lessons: number
  description?: string
  level: string
  tags: string[]
  progress: number
}

export const coursesApi = {
  list: (params?: { category?: string; level?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams()
    if (params?.category) query.append('category', params.category)
    if (params?.level) query.append('level', params.level)
    if (params?.page) query.append('page', params.page.toString())
    if (params?.page_size) query.append('page_size', params.page_size.toString())
    return request<{ items: CourseItem[]; total: number }>(`/courses/?${query}`)
  },
  get: (id: string) => request<CourseItem>(`/courses/${id}`),
  create: (data: Partial<CourseItem>) =>
    request<CourseItem>('/courses/', { method: 'POST', body: JSON.stringify(data) }),
  updateProgress: (id: string, progress: number, completedLessons?: number[]) =>
    request(`/courses/${id}/progress`, {
      method: 'PUT',
      body: JSON.stringify({ progress, completedLessons }),
    }),
  delete: (id: string) =>
    request(`/courses/${id}`, { method: 'DELETE' }),
}

// ============ 审批流 API ============

export interface ApprovalItem {
  id: string
  title: string
  type: string
  status: 'pending' | 'approved' | 'rejected' | 'withdrawn'
  description?: string
  requester_id: string
  requester_name?: string
  approver_id?: string
  approver_name?: string
  resource_type?: string
  resource_id?: string
  comment?: string
  priority: number
  metadata_?: Record<string, any>
  created_at: string
  updated_at: string
  approved_at?: string
}

export const approvalsApi = {
  list: (params?: { status?: string; type?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams()
    if (params?.status) query.set('status', params.status)
    if (params?.type) query.set('type', params.type)
    if (params?.page) query.set('page', String(params.page))
    if (params?.page_size) query.set('page_size', String(params.page_size))
    return request<{ items: ApprovalItem[]; total: number }>(`/approvals?${query}`)
  },

  create: (data: { title: string; type: string; description?: string; approver_id?: string; priority?: number; resource_type?: string; resource_id?: string }) =>
    request<ApprovalItem>('/approvals', { method: 'POST', body: JSON.stringify(data) }),

  get: (id: string) => request<ApprovalItem>(`/approvals/${id}`),

  approve: (id: string, comment?: string) =>
    request<ApprovalItem>(`/approvals/${id}/approve`, { method: 'PUT', body: JSON.stringify({ comment }) }),

  reject: (id: string, comment: string) =>
    request<ApprovalItem>(`/approvals/${id}/reject`, { method: 'PUT', body: JSON.stringify({ comment }) }),

  withdraw: (id: string) =>
    request<ApprovalItem>(`/approvals/${id}/withdraw`, { method: 'PUT' }),

  stats: () => request<Record<string, number>>('/approvals/stats'),
}

// ========== Admin API ==========
export const adminApi = {
  // Dashboard
  dashboard: () => request<any>('/admin/dashboard'),

  // Users
  listUsers: (params?: { skip?: number; limit?: number; search?: string; role?: string; is_active?: boolean }) => {
    const searchParams = new URLSearchParams()
    if (params?.skip) searchParams.set('skip', String(params.skip))
    if (params?.limit) searchParams.set('limit', String(params.limit))
    if (params?.search) searchParams.set('search', params.search)
    if (params?.role) searchParams.set('role', params.role)
    if (params?.is_active !== undefined) searchParams.set('is_active', String(params.is_active))
    const qs = searchParams.toString()
    return request<{ users: any[]; total: number }>(`/admin/users${qs ? '?' + qs : ''}`)
  },
  getUser: (id: string) => request<any>(`/admin/users/${id}`),
  createUser: (data: { email: string; password: string; name: string; role?: string }) =>
    request<any>('/admin/users', { method: 'POST', body: JSON.stringify(data) }),
  updateUser: (id: string, data: any) =>
    request<any>(`/admin/users/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  toggleUserStatus: (id: string) =>
    request<any>(`/admin/users/${id}/toggle-status`, { method: 'PUT' }),
  resetPassword: (id: string, data: { new_password: string }) =>
    request<any>(`/admin/users/${id}/reset-password`, { method: 'PUT', body: JSON.stringify(data) }),

  // Roles
  listRoles: () => request<any[]>('/admin/roles'),
  updateRolePermissions: (role: string, permissions: string[]) =>
    request<any>(`/admin/roles/${role}/permissions`, { method: 'PUT', body: JSON.stringify({ permissions }) }),

  // Audit
  listAuditLogs: (params?: { skip?: number; limit?: number; action?: string; user_id?: string; start_date?: string; end_date?: string }) => {
    const searchParams = new URLSearchParams()
    if (params?.skip) searchParams.set('skip', String(params.skip))
    if (params?.limit) searchParams.set('limit', String(params.limit))
    if (params?.action) searchParams.set('action', params.action)
    if (params?.user_id) searchParams.set('user_id', params.user_id)
    if (params?.start_date) searchParams.set('start_date', params.start_date)
    if (params?.end_date) searchParams.set('end_date', params.end_date)
    const qs = searchParams.toString()
    return request<{ logs: any[]; total: number }>(`/admin/audit-logs${qs ? '?' + qs : ''}`)
  },
  auditStats: () => request<any>('/admin/audit-logs/stats'),

  // System
  getSystemConfig: () => request<any>('/admin/system/config'),
  updateSystemConfig: (data: any) =>
    request<any>('/admin/system/config', { method: 'PUT', body: JSON.stringify(data) }),
  systemHealth: () => request<any>('/admin/system/health'),

  // Organizations
  listOrgs: () => request<any[]>('/admin/organizations'),
  createOrg: (data: { name: string; description?: string }) =>
    request<any>('/admin/organizations', { method: 'POST', body: JSON.stringify(data) }),
  updateOrg: (id: string, data: any) =>
    request<any>(`/admin/organizations/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
}

// 导出所有 API
export default {
  auth: authApi,
  chat: chatApi,
  cases: casesApi,
  contracts: contractsApi,
  documents: documentsApi,
  dueDiligence: dueDiligenceApi,
  knowledge: knowledgeApi,
  knowledgeCenter: knowledgeCenterApi,
  llm: llmApi,
  sentiment: sentimentApi,
  collaboration: collaborationApi,
  lic: licApi,
  assets: assetsApi,
  mcp: mcpApi,
  notifications: notificationsApi,
  tasks: tasksApi,
  approvals: approvalsApi,
  leads: leadsApi,
  experts: expertsApi,
  courses: coursesApi,
  admin: adminApi,
}

// ===== 找律师 API =====

export const lawyerMatchingApi = {
  // 用户：发起咨询
  createConsultation: (data: { description: string; legal_domain?: string; urgency?: string }) =>
    request<any>('/lawyer/consultations', { method: 'POST', body: JSON.stringify(data) }),

  // 用户：我的咨询列表
  listConsultations: (params?: { status?: string; page?: number; page_size?: number }) =>
    request<any>(`/lawyer/consultations?${new URLSearchParams(params as any).toString()}`),

  // 用户：一键委托
  createDelegation: (consultationId: string, data: { title: string; description?: string; service_type?: string }) =>
    request<any>(`/lawyer/consultations/${consultationId}/delegate`, { method: 'POST', body: JSON.stringify(data) }),

  // 公开：律师列表
  listLawyers: (params?: { domain?: string; city?: string; min_rating?: number; page?: number; page_size?: number }) =>
    request<any>(`/lawyer/lawyers?${new URLSearchParams(params as any).toString()}`),

  // 入驻律师：接单大厅
  getLawyerHall: () =>
    request<any>('/lawyer/hall'),

  // 入驻律师：接单
  acceptConsultation: (consultationId: string) =>
    request<any>(`/lawyer/hall/${consultationId}/accept`, { method: 'POST' }),
}

// ===== 匿名聊天 API =====

export const anonymousChatApi = {
  // 创建聊天室
  createRoom: (data: { consultation_id?: string; user_name?: string; lawyer_name?: string; user_contact?: string; lawyer_contact?: string }) =>
    request<any>('/anonymous-chat/rooms', { method: 'POST', body: JSON.stringify(data) }),

  // 获取聊天室信息
  getRoomInfo: (roomId: string, token: string) =>
    request<any>(`/anonymous-chat/rooms/${roomId}?token=${encodeURIComponent(token)}`),

  // 揭示身份
  revealIdentity: (roomId: string, token: string) =>
    request<any>(`/anonymous-chat/rooms/${roomId}/reveal?token=${encodeURIComponent(token)}`, { method: 'POST' }),
}

// ===== 合规自检 API =====

export const complianceApi = {
  // 获取行业列表（无需登录）
  listIndustries: () =>
    request<any>('/compliance-check/industries'),

  // 获取检查清单（无需登录）
  getChecklist: (industry: string) =>
    request<any>(`/compliance-check/checklist/${industry}`),

  // 提交评估
  evaluate: (data: { industry: string; company_size: string; answers: { item_id: string; answer: boolean }[] }) =>
    request<any>('/compliance-check/evaluate', { method: 'POST', body: JSON.stringify(data) }),
}

// ===== IM 即时通讯 API =====

export const imApi = {
  /** 搜索用户（创建对话时使用） */
  searchUsers: (q: string = '', limit: number = 20) =>
    request<any>(`/im/users/search?q=${encodeURIComponent(q)}&limit=${limit}`),

  /** 获取对话列表 */
  getConversations: (params?: { limit?: number; offset?: number }) => {
    const qs = new URLSearchParams()
    if (params?.limit) qs.set('limit', String(params.limit))
    if (params?.offset) qs.set('offset', String(params.offset))
    const query = qs.toString()
    return request<any>(`/im/conversations${query ? `?${query}` : ''}`)
  },

  // 创建对话
  createConversation: (data: {
    type: string
    participant_ids: string[]
    title?: string
    case_id?: string
    contract_id?: string
  }) => request<any>('/im/conversations', { method: 'POST', body: JSON.stringify(data) }),

  // 获取对话消息历史
  getMessages: (conversationId: string, params?: { before_id?: string; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.before_id) qs.set('before_id', params.before_id)
    if (params?.limit) qs.set('limit', String(params.limit))
    const query = qs.toString()
    return request<any>(`/im/conversations/${conversationId}/messages${query ? `?${query}` : ''}`)
  },

  // 标记对话为已读
  markAsRead: (conversationId: string) =>
    request<any>(`/im/conversations/${conversationId}/read`, { method: 'PUT' }),
}
