export interface User {
  id: string
  name: string
  email: string
  role: string
  avatar_url?: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  status?: 'sending' | 'sent' | 'error'
}

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
  participants: Array<{
    user_id: string
    role: string
    nickname?: string
  }>
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
  metadata_?: Record<string, unknown>
  read_by?: string[]
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  created_at: string
  updated_at: string
}

export interface Contract {
  id: string
  title: string
  type: string
  status: 'draft' | 'reviewing' | 'signed' | 'archived'
  parties: string[]
  created_at: string
}

export interface NotificationItem {
  id: string
  type: string
  title: string
  message: string
  is_read: boolean
  related_link?: string
  event_type?: string
  created_at: string
}

export interface TaskItem {
  id: string
  title: string
  description?: string
  status: 'todo' | 'in_progress' | 'done'
  priority: 'high' | 'medium' | 'low'
  dueDate?: string
  assignee?: string
  caseId?: string
  tags: string[]
  createdAt?: string
}

export interface ApprovalItem {
  id: string
  title: string
  type: string
  description?: string
  status: 'pending' | 'approved' | 'rejected' | 'withdrawn'
  requester_id?: string
  requester_name?: string
  approver_id?: string
  approver_name?: string
  resource_type?: string
  resource_id?: string
  comment?: string
  priority?: number
  created_at?: string
  updated_at?: string
  approved_at?: string
}

export interface Case {
  id: string
  title: string
  case_number: string
  status: 'active' | 'pending' | 'closed'
  lawyer_name?: string
  created_at: string
}

export interface LawyerProfile {
  id: string
  name: string
  avatar_url?: string
  specializations: string[]
  rating: number
  years_of_practice: number
  city?: string
  hourly_rate_min?: number
  hourly_rate_max?: number
}

export interface ApiResponse<T = any> {
  code: number
  data: T
  message: string
  request_id: string
}
