// -*- coding: utf-8 -*-
/**
 * V3 移动端共享类型聚合。
 *
 * 大部分类型直接从对应 API 模块 re-export，业务页面只需 `import { ... } from '@/lib/types'`
 * 这一处即可。
 *
 * 与现有 `src/types/api.d.ts`（V2 全集）共存：V3 业务页用本聚合点，
 * 老 V2 页面继续用 `src/types/api.d.ts`。
 */

export type {
  Persona,
  PersonaId,
  PersonaDomain,
  PersonaDetail,
  PersonaListOut,
  ChatHistoryItem,
  ChatRequest,
  ChatResponse,
} from '../api/personas'

export type {
  AgentTask,
  AgentTaskStatus,
  TaskEvent,
  TaskEventType,
  ListTasksParams,
  CreateTaskRequest,
  RejectTaskRequest,
} from '../api/agentTasks'

export type {
  IMChannel,
  IMChannelType,
  IMChannelStatus,
  IMChannelStats,
  SetupChannelRequest,
  BindAgentRequest,
  TestConnectionResult,
} from '../api/imChannels'

export type {
  AuthUser,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
} from '../api/auth'

// ===== Mobile-specific 扩展类型 =====

/** 推送 token 注册响应 */
export interface PushTokenRegisterResult {
  /** 后端记录的 token id（首次注册返回 server-id；后续刷新拿同一个） */
  push_token_id?: string
  /** Expo Push Token */
  token: string
  platform: 'ios' | 'android' | 'web'
}

/** 设备信息（上报后端用） */
export interface DeviceInfo {
  device_id: string
  platform: 'ios' | 'android' | 'web'
  os_version?: string
  app_version?: string
  push_token?: string
}

/** 任务推送通知 deep-link payload */
export interface TaskNotificationPayload {
  type: 'agent_task_done' | 'agent_task_failed' | 'agent_task_needs_approval'
  task_id: string
  persona_id?: string
  preview?: string
}
