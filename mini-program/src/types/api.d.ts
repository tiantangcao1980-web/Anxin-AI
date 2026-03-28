/** 用户 */
export interface User {
  id: string
  name: string
  email: string
  role: string
  avatar_url?: string
}

/** 聊天消息 */
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

/** 对话 */
export interface Conversation {
  id: string
  title: string
  messages: Message[]
  created_at: string
  updated_at: string
}

/** 合同 */
export interface Contract {
  id: string
  title: string
  status: 'draft' | 'reviewing' | 'approved' | 'rejected'
  created_at: string
}

/** 案件 */
export interface Case {
  id: string
  title: string
  description: string
  status: string
  created_at: string
}

/** 分页响应 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
