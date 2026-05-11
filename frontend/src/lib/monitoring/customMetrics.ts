// -*- coding: utf-8 -*-
/**
 * 业务自定义事件埋点（P19-B / Web 前端）
 *
 * 设计原则：
 *   - helper 函数 = 一类业务事件，调用方只关心语义不关心传输；
 *   - 内部双通道：Sentry breadcrumb（带上下文，便于错误回放） +
 *     后端 /api/v1/client-errors（带 type:'event'，便于 Grafana 聚合）；
 *   - 所有 helper 都是同步触发、内部异步发送，避免阻塞业务路径。
 *
 * 10 个建议埋点位置（详见 docs/v3/OBSERVABILITY_FRONTEND.md "埋点清单"）：
 *   1. persona_chat_message_sent     —— src/components/chat/ChatInput.tsx onSend
 *   2. persona_chat_message_received —— src/lib/api/persona-stream.ts onComplete
 *   3. agent_task_created            —— src/components/agent-tasks/CreateTaskDialog onSubmit
 *   4. agent_task_completed          —— src/lib/api/agent-tasks.ts websocket "task.completed"
 *   5. oauth_authorize_started       —— src/pages/oauth/AuthorizePage onClick("授权")
 *   6. oauth_authorize_completed     —— src/pages/oauth/AuthorizePage 收到回调
 *   7. oauth_authorize_failed        —— 同上 catch 分支
 *   8. skill_executed                —— src/lib/api/skills.ts execute 完成
 *   9. fetch_request_sent            —— src/lib/api/fetch.ts 发起前
 *  10. pairing_request_approved      —— src/pages/im-pairing/* 同意时
 */
import { Sentry } from './sentry'

const ENDPOINT = '/api/v1/client-errors'

export type EventName =
  | 'persona_chat_message_sent'
  | 'persona_chat_message_received'
  | 'agent_task_created'
  | 'agent_task_completed'
  | 'oauth_authorize_started'
  | 'oauth_authorize_completed'
  | 'oauth_authorize_failed'
  | 'skill_executed'
  | 'fetch_request_sent'
  | 'pairing_request_approved'

export interface EventContext {
  [key: string]: unknown
}

function send(name: EventName, ctx?: EventContext): void {
  // 1) Sentry breadcrumb：错误回放时能看到事件上下文
  try {
    Sentry?.addBreadcrumb?.({
      category: 'business',
      message: name,
      level: 'info',
      data: ctx,
    })
  } catch {
    /* sentry 未初始化忽略 */
  }

  // 2) 自实装聚合端点
  try {
    const body = JSON.stringify({
      source: 'web',
      type: 'event',
      name,
      context: ctx || {},
      url: typeof window !== 'undefined' ? window.location.pathname : '',
      ts: Date.now(),
    })
    if (typeof navigator !== 'undefined' && 'sendBeacon' in navigator) {
      navigator.sendBeacon(ENDPOINT, new Blob([body], { type: 'application/json' }))
    } else {
      fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        keepalive: true,
      }).catch(() => {
        /* swallow */
      })
    }
  } catch {
    /* swallow */
  }
}

/* ──────────── 业务事件 helper ──────────── */

export const trackPersonaChatMessageSent = (ctx: { personaId: string; messageId: string }) =>
  send('persona_chat_message_sent', ctx)

export const trackPersonaChatMessageReceived = (ctx: {
  personaId: string
  messageId: string
  durationMs: number
  tokens?: number
}) => send('persona_chat_message_received', ctx)

export const trackAgentTaskCreated = (ctx: { taskId: string; type: string }) =>
  send('agent_task_created', ctx)

export const trackAgentTaskCompleted = (ctx: {
  taskId: string
  status: 'success' | 'failed' | 'cancelled'
  durationMs: number
}) => send('agent_task_completed', ctx)

export const trackOAuthAuthorizeStarted = (ctx: { provider: string; scope?: string }) =>
  send('oauth_authorize_started', ctx)

export const trackOAuthAuthorizeCompleted = (ctx: { provider: string; appId?: string }) =>
  send('oauth_authorize_completed', ctx)

export const trackOAuthAuthorizeFailed = (ctx: { provider: string; reason: string }) =>
  send('oauth_authorize_failed', ctx)

export const trackSkillExecuted = (ctx: {
  skillId: string
  status: 'success' | 'failed'
  durationMs: number
}) => send('skill_executed', ctx)

export const trackFetchRequestSent = (ctx: { url: string; method: string }) =>
  send('fetch_request_sent', ctx)

export const trackPairingRequestApproved = (ctx: { pairingId: string; appId: string }) =>
  send('pairing_request_approved', ctx)

/** 通用透传：用于不在上述 10 个 helper 中的临时事件 */
export function trackEvent(name: EventName, ctx?: EventContext): void {
  send(name, ctx)
}
