/**
 * WebSocket 消息处理器集合
 *
 * 从 Chat.tsx handleWebSocketMessage (640行) 中提取的消息分类处理逻辑。
 * 每个处理器负责一类消息，降低主函数的认知负担。
 *
 * 使用方式：在 Chat.tsx 的 handleWebSocketMessage 中调用：
 *   import { handleAgentThinking, handleStreamingToken, ... } from './wsMessageHandlers'
 */

import { v4 as uuidv4 } from 'uuid'

// 消息类型定义（与 Chat.tsx 中的 Message 对齐）
export interface WSMessage {
  id: string
  type: 'user' | 'ai' | 'system' | 'clarification' | 'a2ui' | 'welcome'
  content: string
  timestamp: Date
  agent?: string
  citations?: any[]
  actions?: any[]
  a2uiMessage?: any
  thinkingSteps?: any[]
  suggestions?: string[]
  metadata?: Record<string, any>
  clarification?: any
}

// 处理器上下文（减少参数传递）
export interface WSHandlerContext {
  store: any
  setMessages: React.Dispatch<React.SetStateAction<WSMessage[]>>
  setIsProcessing: (v: boolean) => void
  setThinkingStatus: (v: any) => void
  isMobile: boolean
  openRightPanel: (tab?: string) => void
}

/**
 * 处理 Agent 思考/状态事件
 * 消息类型: agent_thinking, agent_start, agent_working
 */
export function handleAgentThinking(data: any, ctx: WSHandlerContext) {
  ctx.setIsProcessing(true)
  ctx.setThinkingStatus({
    agent: data.agent || '系统',
    message: data.message || data.content || '正在分析...',
  })
  if (data.agent || data.message) {
    ctx.store.addThinkingStep({
      id: uuidv4(),
      agent: data.agent || '系统',
      content: data.message || data.content || '',
      type: data.type === 'agent_working' ? 'progress' : 'thinking',
      timestamp: Date.now(),
    })
  }
}

/**
 * 处理流式 token 输出
 * 消息类型: streaming
 */
export function handleStreamingToken(data: any, ctx: WSHandlerContext) {
  ctx.setIsProcessing(true)
  const token = data.content ?? data.token ?? ''
  if (token) {
    ctx.store.appendStreamingContent(token)
  }
  // 更新 agent 名称
  if (data.agent) {
    ctx.store.setStreamingAgent(data.agent)
  }
}

/**
 * 处理完成事件 — 将流式内容转为正式消息
 * 消息类型: done
 */
export function handleDone(data: any, ctx: WSHandlerContext) {
  ctx.setIsProcessing(false)
  ctx.setThinkingStatus(null)

  const content = data.content || ctx.store.streamingContent || ''
  const agent = data.agent || ctx.store.streamingAgent || '法律顾问'

  if (content.trim()) {
    const aiMessage: WSMessage = {
      id: data.message_id || uuidv4(),
      type: 'ai',
      content,
      agent,
      timestamp: new Date(),
      citations: data.citations || data.sources || [],
      actions: data.actions || [],
      metadata: data._harness || {},
    }
    ctx.setMessages(prev => [...prev, aiMessage])
  }

  // 清除流式状态
  ctx.store.clearStreamingState()
}

/**
 * 处理错误事件
 * 消息类型: error
 */
export function handleError(data: any, ctx: WSHandlerContext) {
  ctx.setIsProcessing(false)
  ctx.setThinkingStatus(null)
  ctx.store.clearStreamingState()

  const rawError = data.content || data.message || '未知错误'

  // 友好化错误消息
  let friendlyMsg = `处理遇到问题：${rawError}`
  let actionableType: 'retry' | 'switch_model' = 'retry'

  if (rawError.includes('timeout') || rawError.includes('超时')) {
    friendlyMsg = '处理超时，请简化问题后重试，或尝试切换其他模型。'
    actionableType = 'switch_model'
  } else if (rawError.includes('Canvas')) {
    friendlyMsg = 'Canvas 内容优化失败，请稍后重试。'
  }

  ctx.setMessages(prev => [...prev, {
    id: uuidv4(),
    type: 'system' as const,
    content: friendlyMsg,
    timestamp: new Date(),
    metadata: { isError: true, originalError: rawError, actionable: actionableType },
  }])
}

/**
 * 处理需求分析/引导式问答事件
 * 消息类型: clarification_request, requirement_analysis
 */
export function handleClarificationRequest(data: any, ctx: WSHandlerContext) {
  const questions = data.questions || []
  if (questions.length === 0) return false

  if (ctx.isMobile) {
    // 移动端：在对话流中显示 ClarificationBubble
    ctx.setMessages(prev => [...prev, {
      id: uuidv4(),
      type: 'clarification' as const,
      content: data.message || '请补充以下信息：',
      timestamp: new Date(),
      clarification: {
        questions,
        originalContent: data.original_content || '',
        readinessScore: data.readiness_score,
        filledSlots: data.filled_slots,
        missingElements: data.missing_elements,
        _prev_assessment: data._prev_assessment,
        _prev_intent: data._prev_intent,
        _prev_round: data._prev_round,
      },
    }])
  } else {
    // 桌面端：推送到右侧面板
    ctx.store.setRequirementAnalysis({
      summary: data.message || data.requirement_summary || '',
      questions,
      originalContent: data.original_content || '',
      readinessScore: data.readiness_score,
      filledSlots: data.filled_slots,
      missingElements: data.missing_elements,
    })
    ctx.openRightPanel('workspace')
  }

  ctx.setIsProcessing(false)
  return true
}

/**
 * 处理保存警告（已被后端自动重试替代，仅作为降级保留）
 * 消息类型: save_warning
 */
export function handleSaveWarning(data: any, _ctx: WSHandlerContext) {
  // Harness: 后端已实现 3 次自动重试，这里仅记录日志
  console.warn('[WS] 保存警告（后端已自动重试）:', data.message)
}

/**
 * 处理 Agent 任务面板事件
 * 消息类型: agent_tasks_batch, agent_task_start, agent_task_complete, agent_task_failed
 */
export function handleAgentTaskEvent(data: any, ctx: WSHandlerContext) {
  switch (data.type) {
    case 'agent_tasks_batch':
      ctx.store.setAgentTasks(data.tasks || [])
      break
    case 'agent_task_start':
      ctx.store.updateAgentTask(data.task_id, { status: 'running', agent: data.agent })
      break
    case 'agent_task_complete':
      ctx.store.updateAgentTask(data.task_id, { status: 'completed', result: data.result })
      break
    case 'agent_task_failed':
      ctx.store.updateAgentTask(data.task_id, { status: 'failed', error: data.error })
      break
  }
}
