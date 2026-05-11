// -*- coding: utf-8 -*-
/** P21-A 统一出口 —— P21-B/C/D 仅需 import 一次 */
export { apiClient, ApiError, type RequestOptions, request } from './client'
export { resolveBaseUrl } from './baseUrl'
export { authApi, wechatMiniprogramLogin, passwordLogin, getCurrentUser, logout } from './auth'
export { personasApi, listPersonas, getPersona, chatWithPersona } from './personas'
export {
  agentTasksApi,
  listTasks,
  createTask,
  getTask,
  cancelTask,
  approveTask,
  rejectTask,
  getTaskResult,
  type ListTasksParams,
} from './agentTasks'
export {
  capabilitiesApi,
  type ScheduledTask,
  type AppAuthorization,
  type Skill,
  type Plugin,
  type MessageChannel,
  type PairingAuthorization,
} from './capabilities'
