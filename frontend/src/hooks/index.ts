/**
 * Chat Hooks - 聊天相关自定义 Hooks 导出
 */

export { useChatHistory } from './useChatHistory';
export type { CitationSource, Message, UseChatHistoryOptions, UseChatHistoryReturn } from './useChatHistory';

export { useChatWebSocket } from './useChatWebSocket';
export type { WebSocketMessageHandlers, UseChatWebSocketOptions, UseChatWebSocketReturn } from './useChatWebSocket';

export { useChatInput } from './useChatInput';
export type { PendingFile, UseChatInputOptions, UseChatInputReturn } from './useChatInput';

export { useChatScroll } from './useChatScroll';
export type { UseChatScrollOptions, UseChatScrollReturn } from './useChatScroll';

export { useWorkspace } from './useWorkspace';
export type { UseWorkspaceOptions, UseWorkspaceReturn } from './useWorkspace';

// Harness: Chat.tsx 拆分提取的 hooks
export { useCanvasOperations } from './useCanvasOperations';
export { useConversationManager } from './useConversationManager';
export { useSmartScroll } from './useSmartScroll';

// useStreamingA2UI is exported from @/components/a2ui/StreamingA2UIRenderer
