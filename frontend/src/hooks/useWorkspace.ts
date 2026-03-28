/**
 * useWorkspace Hook
 * 管理右侧工作台状态和操作
 */

import { useCallback } from 'react';
import { useChatStore } from '@/lib/store';
import { toast } from 'sonner';

export interface UseWorkspaceOptions {
  conversationId: string;
  wsRef: React.MutableRefObject<WebSocket | null>;
}

export interface UseWorkspaceReturn {
  // 状态
  workspaceState: any;
  canvasContent: any;
  agentResults: any[];
  thinkingSteps: any[];

  // 操作
  handleCanvasContentChange: (content: string) => void;
  handleCanvasSaveAsDocument: () => Promise<void>;
  handleCanvasAIOptimize: () => void;
  handleCanvasSuggestionAction: (id: string, action: 'accept' | 'reject') => void;
  handleWorkspaceConfirm: (confirmationId: string, selectedIds: string[]) => void;
  handleWorkspaceAction: (actionId: string, payload?: any) => void;
  handleForwardToLawyer: () => void;
  handleInitiateSigning: () => void;
}

export function useWorkspace(
  options: UseWorkspaceOptions
): UseWorkspaceReturn {
  const { conversationId, wsRef } = options;
  const store = useChatStore();

  // Canvas 内容变更 → 防抖发送到后端
  const canvasSaveTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleCanvasContentChange = useCallback((content: string) => {
    // 1. 立即更新本地状态
    store.updateCanvasText(content);

    // 2. 防抖 1.5s 后发送到后端
    if (canvasSaveTimerRef.current) {
      clearTimeout(canvasSaveTimerRef.current);
    }

    canvasSaveTimerRef.current = setTimeout(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: 'canvas_edit',
            content,
            title: store.canvasContent?.title || '文档',
            canvas_type: store.canvasContent?.type || 'document',
          })
        );
      }
    }, 1500);
  }, [store, wsRef]);

  // Canvas 手动保存
  const handleCanvasSaveAsDocument = useCallback(async () => {
    if (!store.canvasContent?.content) return;

    try {
      const { chatApi, documentsApi } = await import('@/lib/api');

      // 调用文档 API 保存
      await documentsApi.createText({
        name: store.canvasContent.title || '未命名文档',
        content: store.canvasContent.content,
        doc_type: store.canvasContent.type === 'contract' ? 'contract' : 'document',
        description: '通过 Canvas 编辑器创建',
      });

      toast.success('文档已保存到文档库');
    } catch (e) {
      toast.error('保存失败，请稍后重试');
    }
  }, [store.canvasContent]);

  // Canvas AI 优化
  const handleCanvasAIOptimize = useCallback(() => {
    if (!store.canvasContent || !wsRef.current) return;

    wsRef.current.send(
      JSON.stringify({
        type: 'canvas_request',
        canvas_content: store.canvasContent.content,
        canvas_type: store.canvasContent.type,
      })
    );
  }, [store.canvasContent, wsRef]);

  // Canvas 建议操作
  const handleCanvasSuggestionAction = useCallback(
    (id: string, action: 'accept' | 'reject') => {
      if (!store.canvasContent) return;

      const updated = (store.canvasContent.suggestions || []).map((s: any) =>
        s.id === id ? { ...s, status: action === 'accept' ? 'accepted' : 'rejected' } : s
      );

      store.setCanvasContent({
        ...store.canvasContent,
        suggestions: updated,
      });
    },
    [store.canvasContent]
  );

  // 工作台确认回调
  const handleWorkspaceConfirm = useCallback(
    (confirmationId: string, selectedIds: string[]) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: 'workspace_confirmation_response',
            confirmation_id: confirmationId,
            selected_ids: selectedIds,
            conversation_id: conversationId,
          })
        );
      }
    },
    [wsRef, conversationId]
  );

  // 工作台动作回调
  const handleWorkspaceAction = useCallback(
    (actionId: string, payload?: any) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: 'workspace_action',
            action_id: actionId,
            payload,
            conversation_id: conversationId,
          })
        );
      }

      // 某些动作可以直接在前端执行
      switch (actionId) {
        case 'open_document':
          store.setRightPanelTab('document');
          break;
        case 'forward_lawyer':
          store.setRightPanelTab('document');
          store.setDocumentOverlay('lawyer');
          break;
        case 'initiate_signing':
          store.setRightPanelTab('document');
          store.setDocumentOverlay('signing');
          break;
      }
    },
    [wsRef, conversationId, store]
  );

  // 转发律师
  const handleForwardToLawyer = useCallback(() => {
    store.setRightPanelTab('document');
    store.setDocumentOverlay('lawyer');
  }, [store]);

  // 发起签约
  const handleInitiateSigning = useCallback(() => {
    store.setRightPanelTab('document');
    store.setDocumentOverlay('signing');
  }, [store]);

  return {
    // 状态
    workspaceState: store,
    canvasContent: store.canvasContent,
    agentResults: store.agentResults,
    thinkingSteps: store.thinkingSteps,

    // 操作
    handleCanvasContentChange,
    handleCanvasSaveAsDocument,
    handleCanvasAIOptimize,
    handleCanvasSuggestionAction,
    handleWorkspaceConfirm,
    handleWorkspaceAction,
    handleForwardToLawyer,
    handleInitiateSigning,
  };
}

// 添加 React import
import React from 'react';
