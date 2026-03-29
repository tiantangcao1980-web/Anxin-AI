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
