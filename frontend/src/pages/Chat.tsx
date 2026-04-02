/**
 * 智能对话页面 (v3 — A2UI 集成版)
 * 
 * 改造点：
 * 1. 流式消息渲染 — token-by-token + Markdown
 * 2. 思考链/推理过程展示
 * 3. 右侧 RightPanel（工作台/Canvas/分析）替代旧 ContextPane
 * 4. 需求分析引导 + 引导式问答
 * 5. Agent 中间结果实时推送到右侧工作台
 * 6. Canvas 双向编辑
 * 7. A2UI 组件渲染 — Agent 返回结构化 UI 组件嵌入对话流
 */

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { Resizable } from 're-resizable';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import ReactMarkdown from 'react-markdown';
import { chatApi } from '@/lib/api';
import { useChatStore, ConversationItem } from '@/lib/store';
import type { AgentResult, ThinkingStep, CanvasContent } from '@/lib/store';
import { usePrivacy, PrivacyMode } from '@/context/PrivacyContext';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { v4 as uuidv4 } from 'uuid';
import { CitationList } from '@/components/chat/CitationList';
import { KnowledgeBaseSelector } from '@/components/chat/KnowledgeBaseSelector';
import { LottieIcon } from '@/components/ui/LottieIcon';
import { RightPanel } from '@/components/chat/RightPanel';
import { StreamingMessage } from '@/components/chat/StreamingMessage';
import { ThinkingChain } from '@/components/chat/ThinkingChain';
import { QuickActionsBar, DeepModeToggle, type QuickActionFillPayload } from '@/components/chat/QuickActionsBar';
import { SlashCommandPalette, useSlashCommand, type SlashCommand } from '@/components/chat/SlashCommandPalette';
import { ThinkingIndicator, type ThinkingStatus } from '@/components/chat/ThinkingIndicator';
import {
  getWorkflowAction,
  getWorkflowPlaceholder,
  getWorkflowPrompt,
  inferAttachmentWorkflow,
  type QuickActionMode,
} from '@/components/chat/workflowConfig';
import { A2UIRenderer, StreamingA2UIRenderer, useStreamingA2UI } from '@/components/a2ui';
import { MobileA2UIAdapter } from '@/components/a2ui/MobileA2UIAdapter';
import type { A2UIMessage, A2UIEvent, A2UIStreamEvent, A2UIComponent } from '@/components/a2ui';

// ========== Canvas 内容清理工具 ==========

/**
 * 清理 Canvas 标题 — 去除过长的用户补充信息，提取核心文档名
 * 例如: "帮我起草一份贸易合同? 用户补充信息: 这份贸易合同是用于国内..." → "贸易合同"
 */
function cleanCanvasTitle(rawTitle: string): string {
  let title = rawTitle;

  // 去除 "用户补充信息: ..." 及后续内容
  title = title.replace(/[?？]?\s*用户补充信息[:：].*$/s, '');

  // 去除常见前缀："帮我起草一份"、"帮我写一份"、"请起草"、"起草一份" 等
  title = title.replace(/^(请|帮我|帮忙)?(起草|撰写|写|生成|草拟)(一份|一个|一篇)?/u, '');

  // 去除首尾空白和标点
  title = title.replace(/^[\s?？、，,.:：]+|[\s?？、，,.:：]+$/g, '').trim();

  // 如果清理后为空，用原始标题的前 20 个字符
  if (!title) {
    title = rawTitle.slice(0, 20).replace(/[?？].*$/, '').trim() || '文档';
  }

  // 限制最大长度 30 字
  if (title.length > 30) {
    title = title.slice(0, 30) + '…';
  }

  return title;
}

/**
 * 清理 Canvas 内容 — 去除 Agent 执行痕迹，只保留文书正文
 * 例如去除: "任务执行完成。\n### 文书起草Agent\n" 等系统前缀
 */
function cleanCanvasContent(rawContent: string): string {
  let content = rawContent;

  // 循环清理开头的系统噪音（可能连续出现多段）
  let prev = '';
  while (prev !== content) {
    prev = content;

    // 去除 "智能体团队" / "Agent 团队" / "多Agent协作" 等系统标签
    content = content.replace(/^(智能体团队|Agent\s*团队|多Agent协作|AI\s*团队|协作完成)\s*\n*/u, '');

    // 去除 "任务执行完成。" / "任务已完成。" 前缀
    content = content.replace(/^(任务(执行)?完成|处理完毕|已完成)[。.!]\s*/u, '');

    // 去除 "### Agent名称" / "## 文书起草Agent" 标题行
    content = content.replace(/^#{1,4}\s*[\w\u4e00-\u9fff]+Agent[^\n]*\n*/u, '');

    // 去除纯 Agent 名称行（无标题标记格式，如 "文书起草Agent"）
    content = content.replace(/^[\u4e00-\u9fff]+Agent\s*\n*/u, '');

    // 去除 "**Agent名称**" / "**文书起草Agent 输出**"
    content = content.replace(/^\*{1,2}[\w\u4e00-\u9fff]+Agent[^*]*\*{1,2}\s*\n*/u, '');

    // 去除 "---" 分隔线（Agent 输出常用分隔）
    content = content.replace(/^-{3,}\s*\n*/u, '');

    // 去除 "以下是为您起草的..." / "根据您的需求..." 引导语
    content = content.replace(/^(以下是|根据您的|按照您的|应您要求|为您)(需求|要求|提供)?[，,]?(我)?(为您|已|特)?[^。\n]{0,50}[。.：:]\s*\n*/u, '');

    // 去除空白行
    content = content.replace(/^\s*\n/, '');
  }

  return content.trim();
}

/**
 * 检测内容是否为法律文书/合同生成（用于区分文书生成 vs 普通对话）
 * 仅当内容足够长且包含明确的文书结构特征时返回 true
 */
function isDocumentGeneration(content: string): boolean {
  if (content.length < 300) return false;
  return /第[一二三四五六七八九十]+[条章节]|甲方[\s\S]{0,30}乙方|乙方[\s\S]{0,30}甲方|合同编号|签署日期|^#\s*.{2,}|鉴于.*双方|本合同自|违约责任|争议解决/m.test(content);
}

// ========== 类型定义 ==========

interface Message {
  id: string;
  type: 'user' | 'ai' | 'system' | 'clarification' | 'a2ui';
  content: string;
  timestamp: Date;
  agent?: string;
  memory_id?: string;
  feedback?: 'up' | 'down';
  attachment?: { type: 'file' | 'image'; name: string; size: string };
  metadata?: { isError?: boolean; originalError?: string; lastUserMessage?: string };
  clarification?: {
    questions: { question: string; options: string[] }[];
    original_content: string;
  };
  /** A2UI 结构化组件数据（嵌入对话流中的可交互 UI） */
  a2ui?: A2UIMessage;
  /** RAG 引用来源 */
  sources?: { id: string; type: string; title: string; content_snippet?: string; source?: string; relevance_score?: number; url?: string }[];
  /** 后续引导建议（AI 回复后的推荐问题） */
  suggestions?: string[];
}

/**
 * 根据 AI 回复内容和上下文生成后续引导建议
 * 基于关键词匹配和内容分析，提供 2-3 条有针对性的推荐问题
 */
function generateFollowUpSuggestions(aiContent: string, userContent: string): string[] {
  const content = aiContent.toLowerCase();
  const suggestions: string[] = [];

  if (/合同|协议|条款|合约/.test(content)) {
    suggestions.push('这份合同有哪些主要风险点？');
    if (/风险|注意/.test(content)) {
      suggestions.push('请给出修改建议和替代条款');
    } else {
      suggestions.push('请逐条解读关键条款的法律含义');
    }
    suggestions.push('帮我生成一份修改版合同');
  } else if (/合规|法规|法律|条文|法条/.test(content)) {
    suggestions.push('有没有相关的司法解释或案例？');
    suggestions.push('这在不同地区的适用是否有差异？');
    suggestions.push('请帮我整理一份合规检查清单');
  } else if (/尽职调查|尽调|工商|股权/.test(content)) {
    suggestions.push('有哪些需要重点关注的风险事项？');
    suggestions.push('请帮我生成尽调报告模板');
    suggestions.push('类似项目的常见风险有哪些？');
  } else if (/证据|举证|证明/.test(content)) {
    suggestions.push('证据链是否完整？还需要补充什么？');
    suggestions.push('对方可能提出哪些抗辩？');
    suggestions.push('请帮我整理证据目录和说明');
  } else if (/起草|草拟|文书|函件/.test(content)) {
    suggestions.push('请帮我优化文书的措辞和格式');
    suggestions.push('有没有需要补充的法律条款引用？');
    suggestions.push('请生成配套的送达回执模板');
  } else if (/案例|判决|裁判|判例/.test(content)) {
    suggestions.push('有没有相反观点的判例？');
    suggestions.push('这个裁判思路在近年有变化吗？');
    suggestions.push('请帮我总结可援引的裁判要旨');
  } else {
    suggestions.push('请进一步展开分析');
    suggestions.push('有哪些实操层面的注意事项？');
    suggestions.push('请帮我整理一份行动清单');
  }

  return suggestions.slice(0, 3);
}

/** 欢迎消息标记 — 渲染时替换为品牌视觉组件 */
const WELCOME_MESSAGE: Message = {
  id: '1',
  type: 'system',
  content: '__WELCOME__',
  timestamp: new Date(),
};

// ========== 主组件 ==========

export default function Chat() {
  const store = useChatStore();
  const { mode } = usePrivacy();

  // 本地状态
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [isProcessing, setIsProcessing] = useState(false);
  const isDesktopInit = typeof window !== 'undefined' && window.innerWidth >= 1024;
  const [chatWidth, setChatWidth] = useState(isDesktopInit ? 50 : 100);
  const [isMobile, setIsMobile] = useState(!isDesktopInit);
  const [showContextPanel, setShowContextPanel] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(isDesktopInit);
  // 左侧对话列表宽度（可拖拽调整）
  const [sidebarWidth, setSidebarWidth] = useState(220);
  // 右侧面板宽度百分比（可拖拽调整）
  const [rightPanelWidth, setRightPanelWidth] = useState(50);
  // 输入区高度（可拖拽调整，与消息区联动）
  const [inputAreaHeight, setInputAreaHeight] = useState<number | null>(null);
  const [input, setInput] = useState('');
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedKbIdsByConversation, setSelectedKbIdsByConversation] = useState<Record<string, string[]>>({});
  // 内联 Agent 思考状态指示器
  const [thinkingStatus, setThinkingStatus] = useState<ThinkingStatus | null>(null);
  // 模式切换 + 斜杠命令 + 快捷操作选中态
  const [quickActionMode, setQuickActionMode] = useState<QuickActionMode>('chat');
  const [activeActionId, setActiveActionId] = useState<string | null>(null);
  const [actionModeOverride, setActionModeOverride] = useState<QuickActionMode | null>(null);
  const [slashPaletteOpen, setSlashPaletteOpen] = useState(false);
  // 流式 A2UI 状态管理（StreamObject 协议 — 骨架屏 + 渐进渲染）
  const { streams: streamingA2UIMap, activeStreams, handleStreamEvent: handleA2UIStreamEvent } = useStreamingA2UI();
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);

  // 侧边栏
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);

  // 消息编辑模式（参考千问：点击用户消息可编辑并重新生成）
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editingMessageContent, setEditingMessageContent] = useState('');
  const editTextareaRef = useRef<HTMLTextAreaElement>(null);

  // 批量选择模式
  const [batchMode, setBatchMode] = useState(false);
  const [selectedConvIds, setSelectedConvIds] = useState<Set<string>>(new Set());
  const [isBatchDeleting, setIsBatchDeleting] = useState(false);

  // 拖拽状态标记 — 拖拽时禁用 CSS transition 以避免卡顿
  const [isDragging, setIsDragging] = useState(false);
  // 智能滚动：用户主动向上滚动时暂停自动滚动
  const [userScrolledUp, setUserScrolledUp] = useState(false);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const editInputRef = useRef<HTMLInputElement>(null);
  const chatInputRef = useRef<HTMLTextAreaElement>(null);
  const clarificationRef = useRef<{ original_content: string } | null>(null);

  const {
    conversationId, setConversationId,
    conversations, setConversations, addConversation, removeConversation, removeConversations, updateConversationTitle,
    sidebarOpen: chatSidebarOpen, setChatSidebarOpen,
  } = store;
  const conversationSelectionKey = conversationId || '__draft__';
  const selectedKbIds = selectedKbIdsByConversation[conversationSelectionKey] || [];

  const handleSelectedKbIdsChange = useCallback((ids: string[]) => {
    const normalizedIds = Array.from(new Set(ids.filter((id): id is string => Boolean(id))));
    setSelectedKbIdsByConversation((prev) => {
      if (normalizedIds.length === 0) {
        if (!(conversationSelectionKey in prev)) return prev;
        const next = { ...prev };
        delete next[conversationSelectionKey];
        return next;
      }
      return {
        ...prev,
        [conversationSelectionKey]: normalizedIds,
      };
    });
  }, [conversationSelectionKey]);

  const clearKnowledgeBaseSelections = useCallback((conversationKeys: string[]) => {
    if (conversationKeys.length === 0) return;
    setSelectedKbIdsByConversation((prev) => {
      let changed = false;
      const next = { ...prev };
      conversationKeys.forEach((key) => {
        if (key in next) {
          delete next[key];
          changed = true;
        }
      });
      return changed ? next : prev;
    });
  }, []);

  // ========== 初始化 ==========

  useEffect(() => {
    if (!conversationId) setConversationId(uuidv4());
  }, [conversationId, setConversationId]);

  useEffect(() => {
    const check = () => {
      const mobile = window.innerWidth < 1024;
      setIsMobile(mobile);
      return mobile;
    };
    const mobile = check();
    if (mobile) setChatSidebarOpen(false);
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  // ========== 对话管理 ==========

  const loadConversations = useCallback(async () => {
    try {
      const result = await chatApi.listConversations(50);
      if (result?.conversations) setConversations(result.conversations);
    } catch (e) { console.debug('加载对话列表失败:', e); }
  }, [setConversations]);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  const closeCurrentWs = useCallback(() => {
    intentionalCloseRef.current = true;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    reconnectAttemptRef.current = 0;
    if (wsRef.current) {
      wsRef.current.close(1000, 'switching conversation');
      wsRef.current = null;
    }
  }, []);

  const handleNewConversation = useCallback(() => {
    closeCurrentWs();
    const newId = uuidv4();
    setConversationId(newId);
    setMessages([{ ...WELCOME_MESSAGE, id: uuidv4() }]);
    setHistoryLoaded(true); // 新对话无需加载历史
    setIsLoadingHistory(false);
    setIsProcessing(false);
    setInput('');
    setPendingFile(null);
    setActiveActionId(null);
    store.resetWorkspace();
    // 桌面端保持面板展开，移动端收起
    if (window.innerWidth < 1024) {
      setRightPanelOpen(false);
      setChatWidth(100);
    }
    setTimeout(() => chatInputRef.current?.focus(), 100);
    toast.success('已创建新对话');
  }, [closeCurrentWs, setConversationId, store]);

  const handleSwitchConversation = useCallback((conv: ConversationItem) => {
    if (conv.id === conversationId) return;
    closeCurrentWs();
    setConversationId(conv.id);
    setMessages([WELCOME_MESSAGE]);
    setHistoryLoaded(false); // 触发重新加载历史
    setIsLoadingHistory(false);
    setIsProcessing(false);
    store.resetWorkspace();
  }, [conversationId, closeCurrentWs, setConversationId, store]);

  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const handleDeleteConversation = useCallback(async (convId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setMenuOpenId(null);
    setDeleteConfirmId(convId); // 弹出确认框
  }, []);

  const confirmDeleteConversation = useCallback(async () => {
    if (!deleteConfirmId) return;
    const convId = deleteConfirmId;
    setDeleteConfirmId(null);
    try {
      await chatApi.deleteConversation(convId);
      removeConversation(convId);
      clearKnowledgeBaseSelections([convId]);
      toast.success('对话已删除');
      if (convId === conversationId) handleNewConversation();
    } catch { toast.error('删除失败'); }
  }, [clearKnowledgeBaseSelections, deleteConfirmId, conversationId, removeConversation, handleNewConversation]);

  const handleStartRename = useCallback((conv: ConversationItem, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setMenuOpenId(null);
    setEditingConvId(conv.id);
    setEditingTitle(conv.title || '');
    setTimeout(() => editInputRef.current?.focus(), 50);
  }, []);

  const handleFinishRename = useCallback(async () => {
    if (!editingConvId) return;
    const trimmed = editingTitle.trim();
    if (!trimmed) { setEditingConvId(null); return; }
    try {
      await chatApi.updateConversationTitle(editingConvId, trimmed);
      updateConversationTitle(editingConvId, trimmed);
    } catch { toast.error('重命名失败'); }
    setEditingConvId(null);
  }, [editingConvId, editingTitle, updateConversationTitle]);

  // ========== 批量操作 ==========

  const handleToggleBatchMode = useCallback(() => {
    setBatchMode(prev => {
      if (prev) setSelectedConvIds(new Set()); // 退出批量模式时清空选择
      return !prev;
    });
  }, []);

  const handleToggleSelect = useCallback((convId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setSelectedConvIds(prev => {
      const next = new Set(prev);
      if (next.has(convId)) next.delete(convId);
      else next.add(convId);
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    if (selectedConvIds.size === conversations.length) {
      setSelectedConvIds(new Set());
    } else {
      setSelectedConvIds(new Set(conversations.map(c => c.id)));
    }
  }, [conversations, selectedConvIds.size]);

  const handleBatchDelete = useCallback(async () => {
    const ids = Array.from(selectedConvIds);
    if (ids.length === 0) return;
    setIsBatchDeleting(true);
    try {
      await chatApi.batchDeleteConversations(ids);
      removeConversations(ids);
      clearKnowledgeBaseSelections(ids);
      toast.success(`已删除 ${ids.length} 个对话`);
      if (conversationId && ids.includes(conversationId)) {
        handleNewConversation();
      }
      setSelectedConvIds(new Set());
      setBatchMode(false);
    } catch {
      toast.error('批量删除失败');
    } finally {
      setIsBatchDeleting(false);
    }
  }, [clearKnowledgeBaseSelections, selectedConvIds, conversationId, removeConversations, handleNewConversation]);

  useEffect(() => {
    if (!menuOpenId) return;
    const handler = () => setMenuOpenId(null);
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, [menuOpenId]);

  // ========== 加载对话历史 ==========

  useEffect(() => {
    if (!conversationId || historyLoaded) return;
    let cancelled = false;
    (async () => {
      setIsLoadingHistory(true);
      try {
        const result = await chatApi.getHistory({ conversation_id: conversationId, limit: 100 });
        if (cancelled) return;
        if (result?.messages?.length > 0) {
          const hist: Message[] = result.messages.map((m: any) => {
            // 从消息内容中还原附件信息
            const attachMatch = m.content?.match(/^\[附件:\s*(.+?)\]\n?/);
            const attachment = attachMatch ? {
              type: /\.(jpg|jpeg|png|gif|webp|bmp|svg)$/i.test(attachMatch[1]) ? 'image' : 'file' as const,
              name: attachMatch[1].trim(),
              size: '',
            } : undefined;
            const displayContent = attachMatch ? m.content.replace(attachMatch[0], '').trim() : m.content;
            return {
              id: m.id || uuidv4(), type: m.role === 'user' ? 'user' : 'ai',
              content: displayContent || m.content,
              timestamp: new Date(m.created_at || Date.now()), agent: m.agent_name,
              attachment,
              sources: Array.isArray(m.sources) ? m.sources : undefined,
            };
          });
          setMessages(prev => {
            const welcome = prev.length > 0 && prev[0].id === '1' ? [prev[0]] : [];
            return [...welcome, ...hist];
          });
        }
      } catch (e) {
        if (!cancelled) console.debug('加载对话历史失败:', e);
      }

      // 同时恢复 Canvas 文档
      try {
        const canvasResult = await chatApi.getConversationCanvas(conversationId);
        if (!cancelled && canvasResult) {
          const canvasData = (canvasResult as any)?.data || canvasResult;
          if (canvasData?.content) {
            store.setCanvasContent({
              title: cleanCanvasTitle(canvasData.title || '文档'),
              content: cleanCanvasContent(canvasData.content),
              type: (canvasData.type === 'contract' ? 'contract' : 'document') as any,
              suggestions: [],
            });
          }
        }
      } catch (e) {
        // Canvas 恢复失败不影响主流程
        console.debug('Canvas 文档恢复失败:', e);
      }

      if (!cancelled) {
        setHistoryLoaded(true);
        setIsLoadingHistory(false);
      }
    })();
    return () => { cancelled = true; };
  }, [conversationId, historyLoaded]);

  // ========== 智能滚动控制 ==========
  // 检测用户是否主动向上滚动
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      // 距底部 150px 以内认为用户没有向上滚动
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 150;
      setUserScrolledUp(!isNearBottom);
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  // 滚动到底部（仅在用户未主动向上滚动时）
  const scrollToBottom = useCallback((force = false) => {
    if (!force && userScrolledUp) return; // 尊重用户的滚动意图
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [userScrolledUp]);

  // 防抖滚动 — 流式内容更新时最多 200ms 触发一次
  const scrollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const debouncedScrollToBottom = useCallback(() => {
    if (userScrolledUp) return;
    if (scrollTimerRef.current) clearTimeout(scrollTimerRef.current);
    scrollTimerRef.current = setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 200);
  }, [userScrolledUp]);

  // 新消息到达时智能滚动
  useEffect(() => {
    if (store.streamingContent) {
      debouncedScrollToBottom(); // 流式内容：防抖滚动
    } else {
      scrollToBottom(); // 新消息完成：立即滚动（除非用户主动向上滚了）
    }
  }, [messages, store.streamingContent, scrollToBottom, debouncedScrollToBottom]);

  // 使用 ref 保存 loadConversations，在 WS handler 中调用不会引起依赖循环
  const loadConversationsRef = useRef(loadConversations);
  useEffect(() => { loadConversationsRef.current = loadConversations; }, [loadConversations]);

  // ========== 右侧面板展开控制 ==========
  const openRightPanel = useCallback((tab?: 'smart' | 'document') => {
    setRightPanelOpen(true);
    setChatWidth(50);
    if (tab) store.setRightPanelTab(tab);
  }, [store]);

  const closeRightPanel = useCallback(() => {
    setRightPanelOpen(false);
    setChatWidth(100);
  }, []);

  const toggleRightPanel = useCallback(() => {
    if (rightPanelOpen) {
      closeRightPanel();
    } else {
      openRightPanel();
    }
  }, [rightPanelOpen, openRightPanel, closeRightPanel]);

  // ========== WebSocket 消息处理（v2 — 流式 + 思考链 + Agent 结果）==========

  const handleWebSocketMessage = useCallback((data: any) => {
    switch (data.type) {
      // --- 思考 / Agent 状态 → 同步到思考链 ---
      case 'agent_thinking':
      case 'agent_start':
        setIsProcessing(true);
        // 更新内联思考指示器（不打开面板）
        setThinkingStatus({
          agent: data.agent || '系统',
          message: data.message || data.content || '正在分析...',
        });
        if (data.agent || data.message) {
          store.addThinkingStep({
            id: uuidv4(),
            agent: data.agent || '系统',
            content: data.message || data.content || '正在分析...',
            phase: data.type === 'agent_start' ? 'planning' : 'execution',
            timestamp: Date.now(),
          });
        }
        break;

      case 'agent_working':
        setIsProcessing(true);
        setThinkingStatus({
          agent: data.agent || '',
          message: data.message || '正在执行任务...',
        });
        if (data.agent || data.message) {
          store.addThinkingStep({
            id: uuidv4(),
            agent: data.agent || '',
            content: data.message || '正在执行任务...',
            phase: 'execution',
            timestamp: Date.now(),
          });
        }
        break;

      case 'agent_complete':
        // 进度更新
        if (data.agent) {
          store.addThinkingStep({
            id: uuidv4(),
            agent: data.agent || '',
            content: data.message || '任务完成',
            phase: 'result',
            timestamp: Date.now(),
          });
        }
        break;

      // --- 思考链内容 ---
      case 'thinking_content':
        store.addThinkingStep({
          id: uuidv4(),
          agent: data.agent || '',
          content: data.content || '',
          phase: data.phase || 'execution',
          planSteps: data.plan_steps,
          timestamp: Date.now(),
        });
        break;

      // --- 需求分析结果 ---
      case 'requirement_analysis':
        store.setRequirementAnalysis(data);
        // 不再自动打开面板 — 由后端 panel_trigger 事件决定
        // 如果有引导问题，自动在右侧工作台生成确认卡片
        if (data.guidance_questions && data.guidance_questions.length > 0) {
          data.guidance_questions.forEach((q: any, idx: number) => {
            if (q.options && q.options.length > 0) {
              store.addWorkspaceConfirmation({
                id: `req-confirm-${uuidv4()}`,
                title: q.question || `确认事项 ${idx + 1}`,
                description: q.purpose,
                type: q.options.length > 3 ? 'multi' : 'single',
                options: q.options.map((opt: string, i: number) => ({
                  id: `opt-${i}`,
                  label: opt,
                })),
                selectedIds: [],
                status: 'pending',
                source: '需求分析Agent',
                callbackAction: 'requirement_clarification',
                createdAt: Date.now(),
              });
            }
          });
        }
        // 如果需求完整，推送建议动作
        if (data.is_complete && data.suggested_agents && data.suggested_agents.length > 0) {
          store.addWorkspaceAction({
            id: `action-start-${uuidv4()}`,
            label: '开始处理',
            description: `将由 ${data.suggested_agents.join('、')} 协同处理`,
            icon: 'quick',
            variant: 'primary',
            action: 'start_processing',
            payload: { suggested_agents: data.suggested_agents },
          });
        }
        break;

      // --- Agent 中间结果 → 右侧工作台 ---
      case 'agent_result':
        store.addAgentResult({
          id: uuidv4(),
          agent: data.agent || '',
          agentKey: data.agent_key,
          content: data.content || '',
          step: data.step || 0,
          totalSteps: data.total_steps || 0,
          elapsed: data.elapsed,
          timestamp: Date.now(),
        });
        break;

      // --- Agent 任务看板（多 Agent 并列协作） ---
      case 'agent_task_start':
        store.addAgentTask({
          id: data.task_id || uuidv4(),
          agent: data.agent || '',
          agentKey: data.agent_key,
          description: data.description || '',
          status: 'running',
          progress: 0,
          startedAt: Date.now(),
        });
        if (isMobile) {
          store.setRightPanelTab('smart');
          setShowContextPanel(true);
        } else {
          openRightPanel('smart');
        }
        break;

      case 'agent_task_progress':
        if (data.task_id) {
          store.updateAgentTask(data.task_id, {
            progress: data.progress || 0,
            elapsed: data.elapsed,
          });
        }
        break;

      case 'agent_task_complete':
        if (data.task_id) {
          store.updateAgentTask(data.task_id, {
            status: 'completed',
            progress: 100,
            result: data.result || '',
            elapsed: data.elapsed,
            completedAt: Date.now(),
          });
        }
        break;

      case 'agent_task_failed':
        if (data.task_id) {
          store.updateAgentTask(data.task_id, {
            status: 'failed',
            result: data.error || '处理失败',
          });
        }
        break;

      // --- Agent 生命周期事件（重试/替换/降级/强制完成） ---
      case 'agent_task_retry':
        setThinkingStatus({
          agent: data.agent || '系统',
          message: `正在重试 (${data.attempt}/${data.max_retries})...`,
        });
        break;

      case 'agent_replaced':
        setThinkingStatus({
          agent: data.replacement_agent || '系统',
          message: `接管 ${data.failed_agent} 的任务...`,
        });
        break;

      case 'task_degraded':
        // 降级输出通知
        if (data.task_id) {
          store.updateAgentTask(data.task_id, {
            status: 'failed',
            result: data.message || '降级输出',
          });
        }
        break;

      case 'task_force_complete':
        setIsProcessing(false);
        setThinkingStatus(null);
        toast.warning?.('任务超时，已返回部分结果') ?? toast.error('任务超时');
        break;

      case 'agent_tasks_batch':
        // 一次性推送多个 Agent 并列任务（含依赖关系，用于 DAG 层级分组展示）
        if (data.tasks && Array.isArray(data.tasks)) {
          store.setAgentTasks(data.tasks.map((t: any) => ({
            id: t.task_id || uuidv4(),
            agent: t.agent || '',
            agentKey: t.agent_key,
            description: t.description || '',
            status: t.status || 'queued',
            progress: t.progress || 0,
            startedAt: t.status === 'running' ? Date.now() : undefined,
            dependencies: t.dependencies || [],
          })));
          // 不再自动打开面板 — 由后端 panel_trigger 事件决定
        }
        break;

      // --- 工作台需求确认（从左侧触发右侧展示） ---
      case 'workspace_confirmation':
        store.addWorkspaceConfirmation({
          id: data.confirmation_id || uuidv4(),
          title: data.title || '请确认',
          description: data.description,
          type: data.selection_type || 'single',
          options: data.options || [],
          selectedIds: [],
          status: 'pending',
          source: data.source || data.agent,
          callbackAction: data.callback_action,
          createdAt: Date.now(),
        });
        // workspace_confirmation 仍打开面板 — 用户需要交互
        openRightPanel('smart');
        break;

      // --- 工作台动作按钮推送 ---
      case 'workspace_actions':
        if (data.actions && Array.isArray(data.actions)) {
          data.actions.forEach((a: any) => {
            store.addWorkspaceAction({
              id: a.id || uuidv4(),
              label: a.label || '',
              description: a.description,
              icon: a.icon,
              variant: a.variant || 'secondary',
              action: a.action || '',
              payload: a.payload,
              disabled: a.disabled,
            });
          });
          // 不再自动打开面板 — 由后端 panel_trigger 事件决定
        }
        break;

      // --- 流式 token ---
      case 'content_token':
        if (!store.streamingMessageId) {
          const newId = uuidv4();
          store.startStream(newId, data.agent || '');
        }
        store.appendStreamToken(data.token || '');
        break;

      // --- A2UI 上下文更新 ---
      case 'context_update':
        if (data.context_type === 'a2ui') {
          if (data.data?.a2ui?.components) {
            store.appendA2uiComponents(data.data.a2ui.components);
          } else {
            store.setA2uiData(data.data);
          }
          if (isMobile) setShowContextPanel(true);
        }
        break;

      // --- A2UI 消息（直接嵌入对话流的结构化 UI） ---
      case 'a2ui_message': {
        const a2uiMsg: Message = {
          id: uuidv4(),
          type: 'a2ui',
          content: data.text || '',
          timestamp: new Date(),
          agent: data.agent || 'AI 助手',
          a2ui: {
            id: data.a2ui_id || uuidv4(),
            components: data.components || [],
            metadata: data.metadata,
          },
        };
        setMessages(prev => [...prev, a2uiMsg]);
        break;
      }

      // --- 流式 A2UI（StreamObject 协议 — 使用 useStreamingA2UI Hook） ---
      case 'a2ui_stream': {
        const streamEvt = data as A2UIStreamEvent;
        // 委托给 useStreamingA2UI Hook 管理流式状态（含骨架屏、增量更新）
        handleA2UIStreamEvent(streamEvt);

        // stream_component / stream_delta / stream_end 时同步到消息列表以持久化
        if (
          streamEvt.action === 'stream_component' ||
          streamEvt.action === 'stream_delta' ||
          streamEvt.action === 'stream_end'
        ) {
          const sid = streamEvt.streamId;
          // 从 Hook 的 streams Map 中获取最新状态（下一个渲染周期会更新）
          requestAnimationFrame(() => {
            const streamState = streamingA2UIMap.get(sid);
            if (streamState) {
              setMessages(prev => {
                const existing = prev.find(m => m.id === sid);
                if (existing) {
                  return prev.map(m => m.id === sid ? {
                    ...m,
                    a2ui: {
                      id: sid,
                      components: [...streamState.components],
                      // stream_end 时标记为完成，方便后续折叠/归档
                      completed: streamEvt.action === 'stream_end' ? true : (m.a2ui as any)?.completed,
                    },
                  } : m);
                }
                return [...prev, {
                  id: sid,
                  type: 'a2ui' as const,
                  content: '',
                  timestamp: new Date(),
                  agent: streamState.agent || 'AI 助手',
                  a2ui: {
                    id: sid,
                    components: [...streamState.components],
                    completed: streamEvt.action === 'stream_end',
                  },
                }];
              });
            }
          });
        }
        break;
      }

      // --- 后端主动触发面板 ---
      case 'panel_trigger':
        if (data.tab) {
          if (isMobile) {
            // 移动端：打开底部抽屉
            store.setRightPanelTab(data.tab as 'smart' | 'document');
            setShowContextPanel(true);
          } else {
            openRightPanel(data.tab as 'smart' | 'document');
          }
        }
        break;

      // --- Canvas 打开 ---
      case 'canvas_open':
        store.setCanvasContent({
          type: data.type || 'document',
          title: cleanCanvasTitle(data.title || '文档'),
          content: cleanCanvasContent(data.content || ''),
          language: data.language,
        });
        openRightPanel('document');
        break;

      // --- Canvas AI 更新 ---
      case 'canvas_update':
        if (store.canvasContent) {
          store.setCanvasContent({
            ...store.canvasContent,
            content: cleanCanvasContent(data.content || store.canvasContent.content),
            title: data.title ? cleanCanvasTitle(data.title) : store.canvasContent.title,
          });
          toast.success('AI 优化完成');
          setIsProcessing(false);
        }
        openRightPanel('document');
        break;

      // --- Tab 切换建议 ---
      case 'tab_switch':
        if (data.tab) {
          // 将旧 Tab 名映射到新面板
          const tabMap: Record<string, string> = {
            workspace: 'smart', canvas: 'document', analysis: 'smart',
            lawyer: 'document', signing: 'document',
          };
          const mappedTab = tabMap[data.tab] || data.tab;
          if (mappedTab === 'smart' || mappedTab === 'document') {
            openRightPanel(mappedTab as 'smart' | 'document');
          }
          // 如果后端建议律师/签约，打开浮层
          if (data.tab === 'lawyer') store.setDocumentOverlay('lawyer');
          if (data.tab === 'signing') store.setDocumentOverlay('signing');
        }
        break;

      // --- 律师协助消息 ---
      case 'lawyer_comment':
        if (data.comment) {
          store.addLawyerComment(data.comment);
        }
        break;

      case 'lawyer_request_update':
        if (data.request) {
          store.setActiveAssistRequest(data.request);
        }
        break;

      // --- 律师在线状态更新 ---
      case 'lawyer_status':
        if (data.lawyers) {
          store.setOnlineLawyers(data.lawyers);
        }
        break;

      // --- 签约/盖章工作流更新 ---
      case 'signing_update':
        if (data.workflow_id && data.updates) {
          store.updateSigningWorkflow(data.workflow_id, data.updates);
        }
        break;

      // --- 文档就绪 → 工作台推送动作 + 切换签约 ---
      case 'document_ready':
        if (data.suggest_signing) {
          openRightPanel('document');
          store.setDocumentOverlay('signing');
          toast.success('文档已就绪，可发起签约/盖章流程');
        }
        // 同时在工作台推送相关动作
        store.addWorkspaceAction({
          id: `action-doc-${uuidv4()}`,
          label: '查看文档',
          description: data.title || '文档已生成',
          icon: 'document',
          variant: 'secondary',
          action: 'open_document',
        });
        if (data.suggest_signing) {
          store.addWorkspaceAction({
            id: `action-sign-${uuidv4()}`,
            label: '发起签约/盖章',
            description: '文档已就绪，可启动签约流程',
            icon: 'stamp',
            variant: 'success',
            action: 'initiate_signing',
          });
        }
        if (data.suggest_lawyer) {
          store.addWorkspaceAction({
            id: `action-lawyer-${uuidv4()}`,
            label: '转交律师审核',
            description: '建议由律师审阅后再签约',
            icon: 'approve',
            variant: 'warning',
            action: 'forward_lawyer',
          });
        }
        break;

      // --- 最终完成 (替代旧的 agent_response) ---
      case 'done':
      case 'agent_response': {
        setIsProcessing(false);
        setThinkingStatus(null);

        // A2UI 响应已通过 a2ui_message 事件插入对话流，不需要重复添加
        if (data.a2ui) {
          loadConversationsRef.current();
          break;
        }

        // 在 finalizeStream 之前获取原始响应内容
        const responseContent = data.content || store.streamingContent || '';

        // 检测是否为法律文书生成（合同起草、法律意见书等）
        const isDocGen = isDocumentGeneration(responseContent);

        // 法律文书：清理 Agent 系统噪音（"智能体团队"、"任务执行完成"、"文书起草Agent" 等）
        const displayContent = isDocGen ? cleanCanvasContent(responseContent) : responseContent;

        if (store.streamingMessageId) {
          const streamAgent = store.streamingAgent || data.agent || '';
          store.finalizeStream();

          const lastUserContent = [...messages].reverse().find(m => m.type === 'user')?.content || '';
          const aiMessage: Message = {
            id: uuidv4(), type: 'ai', content: displayContent,
            timestamp: new Date(), agent: streamAgent,
            memory_id: data.memory_id,
            sources: data.sources,
            suggestions: generateFollowUpSuggestions(displayContent, lastUserContent),
          };
          setMessages(prev => [...prev, aiMessage]);
        } else if (displayContent) {
          const lastUserContent = [...messages].reverse().find(m => m.type === 'user')?.content || '';
          const aiMessage: Message = {
            id: uuidv4(), type: 'ai', content: displayContent,
            timestamp: new Date(), agent: data.agent,
            memory_id: data.memory_id,
            sources: data.sources,
            suggestions: generateFollowUpSuggestions(displayContent, lastUserContent),
          };
          setMessages(prev => [...prev, aiMessage]);
        }
        loadConversationsRef.current();

        // === 法律文书自动推送到文档面板（始终更新，新文书覆盖旧文档） ===
        if (isDocGen) {
          const docContent = cleanCanvasContent(responseContent);
          const titleMatch = docContent.match(/^#\s*(.+)$/m);
          const inferredTitle = titleMatch
            ? titleMatch[1].trim()
            : (docContent.match(/^(.+?(?:合同|协议|意见书|律师函|起诉状|答辩状|仲裁申请书|通知书|声明|备忘录))/m)?.[1]?.trim() || '法律文书');
          const isContract = /合同|协议|contract|agreement/i.test(responseContent);
          store.setCanvasContent({
            type: isContract ? 'contract' : 'document',
            title: cleanCanvasTitle(inferredTitle),
            content: docContent,
            suggestions: [],
          });
          setTimeout(() => openRightPanel('document'), 600);
        }
        break;
      }

      // --- 引导式问答 ---
      case 'clarification_request':
        setIsProcessing(false);
        const clarMsg: Message = {
          id: uuidv4(), type: 'clarification',
          content: data.message || '为了更好地帮助您，请补充以下信息：',
          timestamp: new Date(), agent: '需求分析',
          clarification: {
            questions: data.questions || [],
            original_content: data.original_content || '',
          },
        };
        setMessages(prev => [...prev, clarMsg]);
        clarificationRef.current = { original_content: data.original_content || '' };
        break;

      // --- 对话修复：主题跳转/矛盾检测 ---
      case 'conversation_repair': {
        setIsProcessing(false);
        const repairMsg: Message = {
          id: uuidv4(), type: 'clarification',
          content: data.message || '检测到信息不一致，请确认',
          timestamp: new Date(), agent: '需求分析',
          clarification: {
            questions: [{
              question: data.message || '',
              options: data.options || [],
            }],
            original_content: data.original_content || '',
          },
          metadata: { repair_type: data.repair_type },
        };
        setMessages(prev => [...prev, repairMsg]);
        clarificationRef.current = { original_content: data.original_content || '' };
        break;
      }

      // --- 后端通知对话标题已更新 ---
      case 'conversation_title_updated':
        if (data.conversation_id && data.title) {
          store.updateConversationTitle(data.conversation_id, data.title);
        }
        break;

      // --- 消息保存失败警告 ---
      case 'save_warning':
        toast.warning?.(data.message || '消息保存异常') ?? toast.error(data.message || '消息保存异常');
        break;

      // --- Canvas 保存结果 ---
      case 'canvas_saved':
        if (data.status === 'ok') {
          setCanvasSaved(true);
        } else {
          toast.error('Canvas 内容保存失败');
        }
        break;

      // --- 错误 ---
      case 'error': {
        setIsProcessing(false);
        setThinkingStatus(null);
        store.finalizeStream();
        const rawError = data.content || data.message || '发生错误';
        // 将技术性错误转为友好提示
        let friendlyMsg = rawError;
        if (rawError.includes('must not be empty')) {
          friendlyMsg = 'AI 处理时遇到问题，请重新发送您的消息。';
        } else if (rawError.includes('API返回 4')) {
          friendlyMsg = 'AI 服务暂时不可用，请稍后重试。';
        } else if (rawError.includes('超时') || rawError.includes('timeout')) {
          friendlyMsg = '处理超时，请简化问题后重试。';
        } else if (rawError.includes('Canvas 优化失败')) {
          friendlyMsg = 'Canvas 内容优化失败，请稍后重试。';
        }
        // 在消息列表中显示可操作的错误提示
        setMessages(prev => [...prev, {
          id: uuidv4(),
          type: 'system' as const,
          content: friendlyMsg,
          timestamp: new Date(),
          metadata: { isError: true, originalError: rawError },
        }]);
        break;
      }
    }
  }, [isMobile, store]);

  // ========== WebSocket 连接（稳定引用，不因回调变化而重连）==========

  // 使用 ref 保存最新的 message handler，避免 WebSocket 因 callback 变化而断连重建
  const messageHandlerRef = useRef(handleWebSocketMessage);
  useEffect(() => {
    messageHandlerRef.current = handleWebSocketMessage;
  }, [handleWebSocketMessage]);

  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const initialConnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptRef = useRef(0);
  const maxReconnectAttempts = 5;
  const intentionalCloseRef = useRef(false); // 标记是否为主动关闭

  const connectWs = useCallback((convId: string) => {
    const ws = chatApi.connectWebSocket(
      convId,
      // 始终调用最新 handler，但引用不变
      (data: any) => messageHandlerRef.current(data),
      // onError
      () => {
        setIsProcessing(false);
        store.finalizeStream();
      },
      // onClose
      (event) => {
        wsRef.current = null;
        // 如果是主动关闭（切换对话等），不重连
        if (intentionalCloseRef.current) {
          intentionalCloseRef.current = false;
          return;
        }
        if (event.code !== 1000) {
          // 非正常关闭 → 自动重连
          setIsProcessing(false);
          store.finalizeStream();
          if (reconnectAttemptRef.current < maxReconnectAttempts) {
            const delay = Math.min(1000 * Math.pow(2, reconnectAttemptRef.current), 15000);
            reconnectAttemptRef.current += 1;
            console.info(`WebSocket 断开，${delay / 1000}s 后尝试第 ${reconnectAttemptRef.current} 次重连...`);
            reconnectTimerRef.current = setTimeout(() => {
              if (!wsRef.current) {
                const newWs = connectWs(convId);
                wsRef.current = newWs;
              }
            }, delay);
          } else {
            setMessages(prev => [
              ...prev,
              {
                id: uuidv4(),
                type: 'system' as const,
                content: '与服务器的连接已断开，多次重连失败。请检查网络或刷新页面重试。',
                timestamp: new Date(),
              },
            ]);
          }
        }
      },
    );
    // 连接成功后重置重连计数
    ws.addEventListener('open', () => {
      reconnectAttemptRef.current = 0;
      setWsConnected(true);
    });
    ws.addEventListener('close', () => {
      setWsConnected(false);
    });
    return ws;
  }, []); // 不依赖任何变化的回调 — 通过 ref 间接引用

  useEffect(() => {
    if (!conversationId || wsRef.current) return;
    initialConnectTimerRef.current = setTimeout(() => {
      if (!wsRef.current) {
        wsRef.current = connectWs(conversationId);
      }
      initialConnectTimerRef.current = null;
    }, 0);

    return () => {
      intentionalCloseRef.current = true;
      if (initialConnectTimerRef.current) {
        clearTimeout(initialConnectTimerRef.current);
        initialConnectTimerRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      reconnectAttemptRef.current = 0;
      if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
        wsRef.current.close(1000, 'component cleanup');
      }
      wsRef.current = null;
    };
  }, [conversationId]); // 只在 conversationId 变化时重建连接

  // ========== 发送消息超时保护 ==========

  const processingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (isProcessing) {
      // 90 秒超时：若后端一直无回复，自动停止 loading
      processingTimeoutRef.current = setTimeout(() => {
        setIsProcessing(false);
        store.finalizeStream();
        setMessages(prev => [
          ...prev,
          {
            id: uuidv4(),
            type: 'system' as const,
            content: '请求超时，服务器未在规定时间内响应。请稍后重试。',
            timestamp: new Date(),
          },
        ]);
      }, 90_000);
    } else {
      if (processingTimeoutRef.current) {
        clearTimeout(processingTimeoutRef.current);
        processingTimeoutRef.current = null;
      }
    }
    return () => {
      if (processingTimeoutRef.current) clearTimeout(processingTimeoutRef.current);
    };
  }, [isProcessing]);

  // ========== 发送消息 ==========

  const handleSendMessage = async (content?: string) => {
    const messageContent = content || input;
    if (!messageContent.trim() || isProcessing) return;

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      if (conversationId) {
        wsRef.current = connectWs(conversationId);
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }

    const attachedFile = pendingFile;
    const userMessage: Message = {
      id: uuidv4(), type: 'user', content: messageContent, timestamp: new Date(),
      attachment: attachedFile ? {
        type: attachedFile.type.includes('image') ? 'image' : 'file',
        name: attachedFile.name, size: `${(attachedFile.size / 1024).toFixed(1)} KB`,
      } : undefined,
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setPendingFile(null);
    setActiveActionId(null); // 发送后取消快捷操作高亮
    setActionModeOverride(null);
    setIsProcessing(true);
    setUserScrolledUp(false); // 发送消息时重置滚动状态，自动跟随新内容
    store.resetWorkspace();

    // === 文件上传：先上传文件获取文档 ID 和提取文本，再通过 WebSocket 发送 ===
    let sendContent = messageContent;
    let uploadedDocId: string | undefined;
    let extractedText: string | undefined;

    if (attachedFile) {
      try {
        // 1. 上传文件到后端文档系统
        const { documentsApi } = await import('@/lib/api');
        const uploadResult = await documentsApi.upload(attachedFile, {
          doc_type: attachedFile.name.endsWith('.docx') || attachedFile.name.endsWith('.doc') ? 'contract' : 'other',
          description: `聊天附件：${messageContent.slice(0, 50)}`,
        });
        
        // 2. 提取文档信息
        const docData = (uploadResult as any)?.data;
        if (docData) {
          uploadedDocId = docData.id;
          extractedText = docData.extracted_text;
        }
        
        // 3. 构建包含文件内容的消息
        if (extractedText && extractedText.trim()) {
          sendContent = `[附件: ${attachedFile.name}]\n${messageContent}\n\n---\n以下是文件「${attachedFile.name}」的内容：\n${extractedText.slice(0, 15000)}`;
        } else {
          sendContent = `[附件: ${attachedFile.name}]\n${messageContent}`;
        }
      } catch (e: any) {
        console.warn('文件上传失败，将仅发送文件名：', e);
        toast.warning?.('文件上传失败，将仅发送文本消息') ?? toast.error('文件上传失败');
        sendContent = `[附件: ${attachedFile.name}]\n${messageContent}`;
      }
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        content: sendContent,
        privacy_mode: mode,
        has_attachments: !!attachedFile,
        document_id: uploadedDocId,
        mode: actionModeOverride ?? quickActionMode,  // 快捷技能优先，其次是深度思考开关
        knowledge_base_ids: selectedKbIds.length > 0 ? selectedKbIds : undefined,
      }));
      if (conversationId && !conversations.find(c => c.id === conversationId)) {
        const title = messageContent.slice(0, 30) + (messageContent.length > 30 ? '...' : '');
        addConversation({
          id: conversationId, title, message_count: 1,
          last_message_at: new Date().toISOString(), created_at: new Date().toISOString(),
        });
      }
    } else {
      toast.error('连接断开，请刷新重试');
      setIsProcessing(false);
    }
  };

  // ========== 澄清回复 ==========

  const handleClarificationResponse = (originalContent: string, selections: Record<string, string>) => {
    if (isProcessing) return;
    const selectionText = Object.entries(selections).map(([q, a]) => `${q}: ${a}`).join('；');
    // v3 优化：不再在对话流中重复输出选择内容，直接发送到后端
    setIsProcessing(true);
    store.resetWorkspace();
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'clarification_response', content: selectionText,
        original_content: originalContent, selections: selectionText, privacy_mode: mode,
      }));
    }
  };

  // ========== 反馈 ==========

  const handleFeedback = async (message: Message, rating: number) => {
    if (!message.memory_id) return;
    try {
      await chatApi.submitMemoryFeedback(message.memory_id, rating);
      setMessages(prev => prev.map(m => m.id === message.id ? { ...m, feedback: rating >= 4 ? 'up' : 'down' } : m));
      toast.success('反馈已记录');
    } catch { toast.error('反馈提交失败'); }
  };

  // ========== 消息编辑 & 重新生成（参考千问设计）==========

  const handleStartEditMessage = useCallback((message: Message) => {
    setEditingMessageId(message.id);
    setEditingMessageContent(message.content);
    setTimeout(() => {
      const el = editTextareaRef.current;
      if (el) {
        el.focus();
        el.setSelectionRange(message.content.length, message.content.length);
        // 自适应高度
        el.style.height = 'auto';
        el.style.height = el.scrollHeight + 'px';
      }
    }, 50);
  }, []);

  const handleCancelEditMessage = useCallback(() => {
    setEditingMessageId(null);
    setEditingMessageContent('');
  }, []);

  const handleConfirmEditMessage = useCallback(() => {
    if (!editingMessageId || !editingMessageContent.trim() || isProcessing) return;
    const editedContent = editingMessageContent.trim();
    // 找到被编辑消息的索引，删除该消息及之后的所有消息
    const msgIndex = messages.findIndex(m => m.id === editingMessageId);
    if (msgIndex === -1) return;
    setMessages(prev => prev.slice(0, msgIndex));
    setEditingMessageId(null);
    setEditingMessageContent('');
    // 重新发送编辑后的内容
    setTimeout(() => handleSendMessage(editedContent), 100);
  }, [editingMessageId, editingMessageContent, isProcessing, messages, handleSendMessage]);

  // 斜杠命令检测
  const { isSlashMode } = useSlashCommand(input);

  // 输入变化时控制斜杠命令面板
  useEffect(() => {
    setSlashPaletteOpen(isSlashMode);
  }, [isSlashMode]);

  // 斜杠命令选择
  const handleSlashCommandSelect = useCallback((cmd: SlashCommand) => {
    setSlashPaletteOpen(false);
    if (cmd.query) {
      setActiveActionId(cmd.actionId ?? null);
      setActionModeOverride(cmd.mode ?? null);
      setInput(cmd.query);
      setTimeout(() => {
        const el = chatInputRef.current;
        if (el) {
          el.focus();
          el.setSelectionRange(cmd.query.length, cmd.query.length);
        }
      }, 50);
    }
  }, []);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    // 斜杠命令模式下，Enter 由 SlashCommandPalette 处理
    if (slashPaletteOpen) return;
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); }
  };

  // 动态 placeholder — 根据当前业务快捷动作切换提示文本
  const dynamicPlaceholder = useMemo(() => {
    if (pendingFile) return `描述您对「${pendingFile.name}」的需求...`;
    if (quickActionMode === 'deep_analysis') return '描述您需要深度分析的法律问题...';
    const workflowPlaceholder = getWorkflowPlaceholder(activeActionId);
    if (workflowPlaceholder) return workflowPlaceholder;
    return '发送消息或输入 / 选择技能';
  }, [pendingFile, quickActionMode, activeActionId]);

  // ========== Canvas 操作 ==========

  // Canvas 内容变更 → 防抖发送到后端 + 保存到文档系统
  const canvasSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [canvasSaved, setCanvasSaved] = useState(true);

  const handleCanvasContentChange = useCallback((content: string) => {
    // 1. 立即更新本地状态
    store.updateCanvasText(content);
    setCanvasSaved(false);

    // 2. 防抖 1.5s 后发送到后端
    if (canvasSaveTimerRef.current) clearTimeout(canvasSaveTimerRef.current);
    canvasSaveTimerRef.current = setTimeout(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'canvas_edit',
          content,
          title: store.canvasContent?.title || '文档',
          canvas_type: store.canvasContent?.type || 'document',
        }));
        setCanvasSaved(true);
      }
    }, 1500);
  }, [store]);

  // Canvas 手动保存（将内容保存为文档）
  const handleCanvasSaveAsDocument = useCallback(async () => {
    if (!store.canvasContent?.content) return;
    try {
      await chatApi.sendMessage({
        content: `[系统] 保存文档: ${store.canvasContent.title}`,
        conversation_id: conversationId || undefined,
      });
      // 调用文档 API 保存
      const { documentsApi } = await import('@/lib/api');
      await documentsApi.createText({
        name: store.canvasContent.title || '未命名文档',
        content: store.canvasContent.content,
        doc_type: store.canvasContent.type === 'contract' ? 'contract' : 'document',
        description: `通过 Canvas 编辑器创建`,
      });
      toast.success('文档已保存到文档库');
      setCanvasSaved(true);
    } catch (e) {
      toast.error('保存失败，请稍后重试');
    }
  }, [store.canvasContent, conversationId]);

  const handleCanvasAIOptimize = useCallback(() => {
    if (!store.canvasContent) {
      toast.error('没有文档内容可以润色');
      return;
    }
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      toast.error('连接已断开，请刷新后重试');
      return;
    }
    wsRef.current.send(JSON.stringify({
      type: 'canvas_request',
      canvas_content: store.canvasContent.content,
      canvas_type: store.canvasContent.type,
    }));
    setIsProcessing(true);
  }, [store.canvasContent]);

  const handleCanvasSuggestionAction = useCallback((id: string, action: 'accept' | 'reject') => {
    if (!store.canvasContent) return;
    const updated = (store.canvasContent.suggestions || []).map(s =>
      s.id === id ? { ...s, status: action === 'accept' ? 'accepted' as const : 'rejected' as const } : s
    );
    store.setCanvasContent({ ...store.canvasContent, suggestions: updated });
  }, [store]);

  // ========== 文档快捷操作（翻译/摘要/润色/风险检查）==========
  const handleDocumentAction = useCallback((action: string, payload?: any) => {
    if (!store.canvasContent) {
      toast.error('没有文档内容');
      return;
    }
    const content = store.canvasContent.content;

    const actionMessages: Record<string, string> = {
      summarize: `请为以下文档生成结构化摘要，包含主要内容、关键条款和核心结论：\n\n---\n${content.slice(0, 10000)}`,
      translate: `请将以下文档翻译为英文（保留原格式）：\n\n---\n${content.slice(0, 10000)}`,
      optimize: `请对以下法律文档进行措辞润色和结构优化：\n\n---\n${content.slice(0, 10000)}`,
      risk_check: `请检查以下文档中的法律风险点，标出有风险的条款并给出修改建议：\n\n---\n${content.slice(0, 10000)}`,
    };

    const message = actionMessages[action];
    if (message) {
      handleSendMessage(message);
    }
  }, [store.canvasContent, handleSendMessage]);

  // ========== 转发律师 ==========
  const handleForwardToLawyer = useCallback(() => {
    openRightPanel('document');
    store.setDocumentOverlay('lawyer');
  }, [store, openRightPanel]);

  // ========== 发起签约/盖章 ==========
  const handleInitiateSigning = useCallback(() => {
    openRightPanel('document');
    store.setDocumentOverlay('signing');
  }, [store, openRightPanel]);

  // ========== 工作台确认回调 ==========
  const handleWorkspaceConfirm = useCallback((confirmationId: string, selectedIds: string[]) => {
    // 通过 WebSocket 将用户选择发送回后端
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'workspace_confirmation_response',
        confirmation_id: confirmationId,
        selected_ids: selectedIds,
        conversation_id: store.conversationId,
      }));
    }
  }, [store.conversationId]);

  // ========== 工作台动作回调 ==========

  const WORKSPACE_TO_WORKFLOW_ACTION: Record<string, { workflowActionId: string; hint?: string }> = {
    'ws-contract-review': {
      workflowActionId: 'qa-contract',
      hint: '可先上传合同文件，或直接粘贴合同条款后发送',
    },
    'ws-regulation': {
      workflowActionId: 'qa-search',
    },
    'ws-due-diligence': {
      workflowActionId: 'qa-compliance',
    },
    'ws-compliance': {
      workflowActionId: 'qa-compliance',
    },
    'ws-find-lawyer': {
      workflowActionId: 'qa-lawyer',
    },
    'ws-doc-generate': {
      workflowActionId: 'qa-draft',
    },
  };

  const handleWorkspaceAction = useCallback((actionId: string, payload?: any) => {
    if (actionId.startsWith('ws-')) {
      if (actionId === 'ws-messages') {
        window.location.href = '/messages';
        return;
      }
      if (actionId === 'ws-voice-chat') {
        toast.info('语音对话功能正在开发中，敬请期待', { icon: '🎙️' });
        return;
      }

      // 工作台入口统一复用现有 qa-* 工作流配置，避免输入语义与发送模式漂移。
      const workflowBridge = WORKSPACE_TO_WORKFLOW_ACTION[actionId];
      if (workflowBridge) {
        const workflowAction = getWorkflowAction(workflowBridge.workflowActionId);
        const prompt = getWorkflowPrompt(workflowBridge.workflowActionId, {
          hasAttachment: false,
          attachmentName: null,
        });

        setInput(prompt);
        setActiveActionId(workflowBridge.workflowActionId);
        setActionModeOverride(workflowAction?.mode ?? null);
        setTimeout(() => {
          const el = chatInputRef.current;
          if (el) {
            el.focus();
            el.setSelectionRange(prompt.length, prompt.length);
          }
        }, 50);
        if (workflowBridge.hint) {
          toast(workflowBridge.hint, { icon: '💡', duration: 4000 });
        }
        return;
      }
    }

    // 快捷功能入口：qa-* 动作直接填充输入框
    if (actionId.startsWith('qa-')) {
      const prompt = getWorkflowPrompt(actionId, { hasAttachment: false, attachmentName: null });
      if (prompt) {
        setInput(prompt);
        setActiveActionId(actionId);
        setTimeout(() => chatInputRef.current?.focus(), 50);
        return;
      }
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'workspace_action',
        action_id: actionId,
        payload,
        conversation_id: store.conversationId,
      }));
    }
    switch (actionId) {
      case 'open_document':
        openRightPanel('document');
        break;
      case 'forward_lawyer':
        handleForwardToLawyer();
        break;
      case 'initiate_signing':
        handleInitiateSigning();
        break;
    }
  }, [store.conversationId, handleForwardToLawyer, handleInitiateSigning]);

  // ========== 隐私提示 ==========

  const getPrivacyHint = () => {
    switch (mode) {
      case PrivacyMode.LOCAL: return { text: '绝密模式：数据仅在本地处理', icon: icons.Lock, color: 'text-primary' };
      case PrivacyMode.HYBRID: return { text: '安全混合：敏感数据已自动脱敏', icon: icons.ShieldCheck, color: 'text-emerald-600' };
      case PrivacyMode.CLOUD: return { text: '云端增强：正在使用联网模型', icon: icons.Cloud, color: 'text-primary' };
    }
  };
  const privacyHint = getPrivacyHint();
  const PrivacyIcon = privacyHint.icon;

  const formatConvDate = (dateStr: string | null) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const diff = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
    if (diff === 0) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (diff === 1) return '昨天';
    if (diff < 7) return `${diff}天前`;
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  // ========== 渲染消息 ==========

  // ========== A2UI 事件处理（千问购物式：卡片操作 → 对话消息回传） ==========

  /**
   * 卡片操作→对话消息映射表
   * 
   * 千问购物模式的核心交互：用户点击卡片上的操作按钮后，
   * 自动在对话流中生成可见的用户消息，让整个流程像自然对话一样流畅。
   * 
   * 映射规则：
   * - 浏览类操作（查看详情、了解更多）→ 生成自然语言消息
   * - 确认类操作（确认委托、接受修改）→ 生成确认消息 + 发送 A2UI 事件
   * - 表单类操作（提交表单）→ 静默发送 A2UI 事件（不生成消息）
   */
  const A2UI_ACTION_TO_MESSAGE: Record<string, (payload: Record<string, any>) => string | null> = useMemo(() => ({
    // --- 律师相关 ---
    'contact_lawyer': (p) => `我想咨询${p.lawyerName || '这位'}律师`,
    'consult_lawyer': (p) => `请帮我联系${p.lawyerName || '这位'}律师进行咨询`,
    'view_lawyer_detail': (p) => `请详细介绍${p.lawyerName || '这位'}律师的擅长领域和成功案例`,
    'view_more_lawyers': () => '请推荐更多律师',
    'ai_match_lawyer': () => '请用 AI 帮我智能匹配最合适的律师',
    // --- 合同相关 ---
    'accept_changes': () => '我接受这些修改建议',
    'export_report': () => '请导出合同审查报告',
    'view_full_report': () => '请展示完整的合同审查报告',
    'ai_suggestions': () => '请给出 AI 修改建议',
    'start_review': () => '开始审查合同',
    // --- 费用/委托相关 ---
    'confirm_fee': () => '我确认这个费用方案',
    'confirm_engagement': () => '确认委托，请开始处理',
    // --- 风险/案件相关 ---
    'view_case_detail': (p) => `请展示案件${p.caseId ? ` ${p.caseId}` : ''}的详细信息`,
    'assess_contract_risk': () => '请评估合同风险',
    'assess_compliance': () => '请进行合规审查',
    'assess_litigation_risk': () => '请评估诉讼风险',
    'assess_ip_risk': () => '请评估知识产权风险',
    // --- 文书相关 ---
    'select_doc_type': (p) => `我需要起草${p.docType === 'contract' ? '合同/协议' : p.docType === 'lawyer_letter' ? '律师函' : p.docType === 'legal_opinion' ? '法律意见书' : '法律文书'}`,
    // --- 通用 ---
    'quick_intent': () => null, // 由 query payload 处理
    'go_back': () => null, // 导航操作，不生成消息
  }), []);

  const handleA2UIEvent = useCallback((event: A2UIEvent) => {
    // 特殊处理：快捷意图按钮 → 直接作为用户消息发送
    if (event.actionId === 'quick_intent' && event.payload?.query) {
      handleSendMessage(event.payload.query);
      return;
    }

    // 千问购物模式：检查是否有对应的自然语言消息映射
    const messageGenerator = A2UI_ACTION_TO_MESSAGE[event.actionId];
    if (messageGenerator) {
      const naturalMessage = messageGenerator(event.payload || {});
      if (naturalMessage) {
        // 同时作为对话消息发送（让用户看到自己的操作）+ A2UI 事件（让后端正确处理）
        handleSendMessage(naturalMessage);
        return;
      }
    }

    // 无映射的操作：通过 A2UI 事件系统静默发送（表单提交等）
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'a2ui_event',
        action_id: event.actionId,
        component_id: event.componentId,
        payload: event.payload || {},
        form_data: event.formData || {},
      }));
    } else {
      // 降级：作为普通消息发送
      const fallbackContent = `[A2UI操作] ${event.actionId}${event.formData ? ' | 表单数据: ' + JSON.stringify(event.formData) : ''}`;
      handleSendMessage(fallbackContent);
    }
  }, [handleSendMessage, A2UI_ACTION_TO_MESSAGE]);

  // 找到最后一个 A2UI 类型消息的 ID（用于移动端历史折叠判断）
  const lastA2UIMessageId = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].type === 'a2ui' && messages[i].a2ui) {
        return messages[i].id;
      }
    }
    return null;
  }, [messages]);

  const renderMessage = (message: Message) => {
    // ========== 欢迎页：品牌问候 + 能力简介 ==========
    if (message.content === '__WELCOME__') {
      return (
        <motion.div
          key={message.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full min-h-[50vh] flex flex-col items-center justify-center mx-auto max-w-lg px-4"
        >
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary/80 to-primary flex items-center justify-center shadow-lg shadow-primary/20">
            <icons.Scale className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight mt-4">你好，有什么可以帮您？</h1>
          <p className="text-sm text-muted-foreground mt-3 text-center leading-relaxed">
            我是安心 AI 法务助手，您可以直接在下方输入问题，
            <br className="hidden sm:block" />
            或使用底部工具栏选择具体服务。我可以帮您：
          </p>
          <div className="mt-4 text-sm text-muted-foreground/80 text-center leading-loose">
            审查合同条款与风险 · 起草法律文书与函件
            <br />
            合规检查与尽职调查 · 检索法规与裁判案例
            <br />
            梳理证据链 · 拆解法务任务 · 推荐律师
          </div>
        </motion.div>
      );
    }

    // A2UI 消息 — 结构化 UI 组件
    if (message.type === 'a2ui' && message.a2ui) {
      return (
        <motion.div
          key={message.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="group"
        >
          {/* Agent 标签 */}
          {message.agent && (
            <div className="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground mb-1.5 ml-0.5">
              <icons.Bot className="h-3 w-3" />
              {message.agent}
            </div>
          )}

          {/* 文本内容（如果有） */}
          {message.content && (
            <div className="bg-background border border-border/50 text-foreground px-4 py-3 rounded-2xl rounded-bl-md shadow-sm mb-2">
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            </div>
          )}

          {/* A2UI 组件 — 移动端使用千问风格适配器（历史卡片自动折叠） */}
          <div className={cn('', isMobile ? 'w-full' : 'max-w-[95%]')}>
            {isMobile ? (
              <MobileA2UIAdapter
                message={message.a2ui}
                onEvent={handleA2UIEvent}
                isHistorical={message.id !== lastA2UIMessageId}
                showBottomBar={message.id === lastA2UIMessageId}
              />
            ) : (
              <A2UIRenderer
                message={message.a2ui}
                onEvent={handleA2UIEvent}
                animated={true}
              />
            )}
          </div>

          {/* 时间戳 */}
          <div className="flex items-center gap-2 mt-1.5 ml-0.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            <span className="text-[10px] text-muted-foreground/50">
              {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        </motion.div>
      );
    }

    if (message.type === 'clarification') {
      return (
        <ClarificationBubble
          key={message.id}
          message={message.content}
          questions={message.clarification!.questions}
          originalContent={message.clarification!.original_content}
          onSubmit={handleClarificationResponse}
          disabled={isProcessing}
        />
      );
    }

    // 系统消息 — 居中提示条（错误消息带重试按钮）
    if (message.type === 'system') {
      const isErr = message.metadata?.isError;
      return (
        <motion.div
          key={message.id}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex justify-center"
        >
          <div className={`text-[11px] mx-auto font-medium px-4 py-1.5 rounded-full flex items-center gap-2 ${
            isErr
              ? 'bg-destructive/5 text-destructive border border-destructive/20'
              : 'bg-amber-50 dark:bg-amber-950/30 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800'
          }`}>
            <span>{message.content}</span>
            {isErr && (
              <button
                onClick={() => {
                  // 找到最后一条用户消息重新发送
                  const lastUserMsg = [...messages].reverse().find(m => m.type === 'user');
                  if (lastUserMsg) {
                    handleSendMessage(lastUserMsg.content);
                  }
                }}
                className="ml-1 px-2 py-0.5 bg-destructive/10 hover:bg-destructive/10 text-destructive rounded-full text-[10px] font-semibold transition-colors"
              >
                重试
              </button>
            )}
          </div>
        </motion.div>
      );
    }

    const isUser = message.type === 'user';
    const isEditing = editingMessageId === message.id;
    const knowledgeBaseSources = !isUser
      ? (message.sources || []).filter((source) => source.type === 'knowledge_base')
      : [];
    const regularSources = !isUser
      ? (message.sources || []).filter((source) => source.type !== 'knowledge_base')
      : [];

    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        key={message.id}
        className={`group ${isUser ? 'flex justify-end' : ''}`}
      >
        <div className={`max-w-[85%] ${isUser ? '' : ''}`}>
          {/* AI 消息 — Agent 标签 */}
          {!isUser && message.agent && (
            <div className="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground mb-1.5 ml-0.5">
              <icons.Bot className="h-3 w-3" />
              {message.agent}
            </div>
          )}

          {/* 消息气泡 */}
          <div className={`rounded-2xl leading-relaxed text-sm ${
            isUser
              ? isEditing
                ? 'bg-primary/10 border-2 border-primary/40 text-foreground px-4 py-2.5 rounded-br-md'
                : 'bg-primary text-white px-4 py-2.5 rounded-br-md'
              : 'bg-background border border-border/50 text-foreground px-4 py-3 rounded-bl-md shadow-sm'
          }`}>
            {/* 附件 */}
            {message.attachment && (
              <div className={`flex items-center gap-2.5 mb-2.5 p-2 rounded-lg ${
                isUser ? (isEditing ? 'bg-primary/5 border border-primary/10' : 'bg-white/15') : 'bg-muted/50 border border-border/50'
              }`}>
                <div className={`p-1.5 rounded ${isUser ? (isEditing ? 'bg-primary/10' : 'bg-white/20') : 'bg-background shadow-sm'}`}>
                  <icons.FileText className={`w-4 h-4 ${isUser ? (isEditing ? 'text-primary' : 'text-white') : 'text-primary'}`} />
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="text-xs font-medium truncate">{message.attachment.name}</span>
                  {message.attachment.size && (
                    <span className={`text-[10px] ${isUser ? (isEditing ? 'text-muted-foreground' : 'text-white/70') : 'text-muted-foreground'}`}>{message.attachment.size}</span>
                  )}
                </div>
              </div>
            )}

            {/* 消息内容 — 编辑模式 vs 展示模式 */}
            {isUser ? (
              isEditing ? (
                <div className="flex flex-col gap-2">
                  <textarea
                    ref={editTextareaRef}
                    value={editingMessageContent}
                    onChange={(e) => {
                      setEditingMessageContent(e.target.value);
                      e.target.style.height = 'auto';
                      e.target.style.height = e.target.scrollHeight + 'px';
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleConfirmEditMessage(); }
                      if (e.key === 'Escape') handleCancelEditMessage();
                    }}
                    className="w-full bg-transparent border-none resize-none focus:outline-none text-foreground text-sm leading-relaxed"
                    style={{ minHeight: '24px' }}
                  />
                  <div className="flex items-center gap-2 justify-end">
                    <button
                      onClick={handleCancelEditMessage}
                      className="px-3 py-1 text-xs font-medium text-muted-foreground hover:text-foreground rounded-lg hover:bg-muted transition-colors"
                    >
                      取消
                    </button>
                    <button
                      onClick={handleConfirmEditMessage}
                      disabled={!editingMessageContent.trim() || isProcessing}
                      className="px-3 py-1 text-xs font-medium text-white bg-primary hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-1"
                    >
                      <icons.Send className="w-3 h-3" />
                      重新发送
                    </button>
                  </div>
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{message.content}</p>
              )
            ) : (
              <div className="prose prose-sm max-w-none prose-headings:text-foreground prose-headings:font-semibold prose-p:text-foreground prose-p:leading-relaxed prose-strong:text-foreground prose-ul:text-foreground/80 prose-ol:text-foreground/80 prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-[13px] prose-pre:bg-foreground prose-pre:text-background">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            )}
          </div>

          {/* AI 消息内嵌的 A2UI 组件（文本 + 结构化 UI 混合展示） */}
          {!isUser && message.a2ui && (
            <div className="mt-2">
              {isMobile ? (
                <MobileA2UIAdapter
                  message={message.a2ui}
                  onEvent={handleA2UIEvent}
                  isHistorical={false}
                  showBottomBar={false}
                />
              ) : (
                <A2UIRenderer
                  message={message.a2ui}
                  onEvent={handleA2UIEvent}
                  animated={true}
                  isMobile={isMobile}
                />
              )}
            </div>
          )}

          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="mt-3 space-y-2">
              {knowledgeBaseSources.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {knowledgeBaseSources.map((source, index) => {
                    const knowledgeBaseName = source.source || source.title || `知识库 ${index + 1}`;
                    const score = typeof source.relevance_score === 'number'
                      ? `${Math.round(source.relevance_score * 100)}%`
                      : null;

                    return (
                      <div
                        key={source.id || `${knowledgeBaseName}-${index}`}
                        className="inline-flex max-w-full items-center gap-2 rounded-xl border border-primary/15 bg-primary/5 px-3 py-2 text-xs text-foreground shadow-sm"
                      >
                        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-background text-primary shadow-sm">
                          <icons.Database className="h-3.5 w-3.5" />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="truncate font-medium text-foreground">
                              {knowledgeBaseName}
                            </span>
                            {score && (
                              <span className="rounded-full bg-background px-1.5 py-0.5 text-[10px] text-primary">
                                相关度 {score}
                              </span>
                            )}
                          </div>
                          {source.title && source.title !== knowledgeBaseName && (
                            <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
                              {source.title}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {regularSources.length > 0 && (
                <CitationList
                  sources={regularSources.map((source, index) => ({
                    id: source.id || `${source.type}-${index}`,
                    type: source.type || 'knowledge',
                    title: source.title || source.source || `引用 ${index + 1}`,
                    content_snippet: source.content_snippet || '',
                    source: source.source || '知识库检索',
                    relevance_score: source.relevance_score ?? 0,
                    url: source.url || null,
                  }))}
                />
              )}
            </div>
          )}

          {/* 用户消息底部操作栏 — 编辑 + 时间戳 */}
          {isUser && !isEditing && (
            <div className="flex items-center gap-2 mt-1.5 mr-0.5 justify-end opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              <span className="text-[10px] text-muted-foreground/50">
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
              <button
                onClick={() => handleStartEditMessage(message)}
                disabled={isProcessing}
                className="p-1 rounded-md text-muted-foreground/50 hover:text-primary hover:bg-primary/5 transition-colors disabled:opacity-30"
                title="编辑消息并重新生成"
              >
                <icons.Edit className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* AI 消息底部操作栏 — 始终显示但淡入 */}
          {!isUser && (
            <div className="flex items-center gap-2 mt-1.5 ml-0.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              <span className="text-[10px] text-muted-foreground/50">
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
              {message.memory_id && (
                <div className="flex items-center gap-0.5">
                  <button
                    onClick={() => handleFeedback(message, 5)}
                    disabled={!!message.feedback}
                    className={`p-1 rounded-md hover:bg-muted transition-colors ${
                      message.feedback === 'up' ? 'text-emerald-600' : 'text-muted-foreground/50 hover:text-emerald-600'
                    }`}
                    title="有帮助"
                  >
                    <icons.ThumbsUp className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => handleFeedback(message, 1)}
                    disabled={!!message.feedback}
                    className={`p-1 rounded-md hover:bg-muted transition-colors ${
                      message.feedback === 'down' ? 'text-destructive' : 'text-muted-foreground/50 hover:text-destructive'
                    }`}
                    title="需改进"
                  >
                    <icons.ThumbsDown className="w-3 h-3" />
                  </button>
                </div>
              )}
            </div>
          )}

          {/* 后续引导建议 — 仅在最后一条 AI 消息下方显示，类似豆包/千问 */}
          {!isUser && message.suggestions && message.suggestions.length > 0 &&
            message.id === [...messages].reverse().find(m => m.type === 'ai')?.id && !isProcessing && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.3 }}
              className="flex flex-wrap gap-2 mt-3 ml-0.5"
            >
              {message.suggestions.map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setInput(suggestion);
                    setTimeout(() => {
                      chatInputRef.current?.focus();
                      handleSendMessage(suggestion);
                    }, 50);
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-foreground/70 bg-background border border-border/80 rounded-full hover:border-primary/40 hover:text-primary hover:bg-primary/5 transition-all shadow-sm active:scale-95"
                >
                  <icons.Sparkles className="w-3 h-3 text-primary/50" />
                  <span>{suggestion}</span>
                </button>
              ))}
            </motion.div>
          )}
        </div>
      </motion.div>
    );
  };

  // ========== JSX ==========

  return (
    <div className="h-full flex bg-muted/50 relative">
      {/* ========== 左侧对话列表侧边栏 ========== */}
      <AnimatePresence>
        {chatSidebarOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: sidebarWidth, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="h-full flex-shrink-0 bg-background flex flex-col overflow-hidden max-md:!w-full max-md:absolute max-md:inset-0 max-md:z-20 max-md:border-r max-md:border-border"
          >
            <div className="h-12 px-3 flex items-center gap-2 border-b border-border/50 shrink-0">
              <div className="flex items-center justify-between flex-1">
                {!batchMode ? (
                  <>
                    <button onClick={handleNewConversation}
                      className="flex items-center gap-2 px-3 py-2 text-sm font-medium bg-primary hover:bg-primary/90 text-white rounded-lg transition-colors flex-1 mr-2 shadow-sm">
                      <icons.Plus className="w-4 h-4" /> 新建对话
                    </button>
                    <button onClick={handleToggleBatchMode}
                      className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors" title="批量管理">
                      <icons.MoreHorizontal className="w-4 h-4" />
                    </button>
                    <button onClick={() => setChatSidebarOpen(false)}
                      className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors" title="收起侧边栏">
                      <icons.ChevronLeft className="w-4 h-4" />
                    </button>
                  </>
                ) : (
                  <>
                    <span className="text-sm font-medium text-foreground/80 flex-1">
                      已选 {selectedConvIds.size} / {conversations.length}
                    </span>
                    <button onClick={handleToggleBatchMode}
                      className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors" title="取消">
                      <icons.XCircle className="w-4 h-4" />
                    </button>
                  </>
                )}
              </div>
            </div>
            {batchMode && (
              <div className="flex items-center gap-2 px-3 py-1.5 border-b border-border/50 bg-muted/30 shrink-0">
                <button onClick={handleSelectAll}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:text-primary hover:bg-primary/5 rounded-lg border border-border transition-colors">
                  {selectedConvIds.size === conversations.length ? (
                    <><icons.Check className="w-3.5 h-3.5" /> 取消全选</>
                  ) : (
                    <><icons.Circle className="w-3.5 h-3.5" /> 全选</>
                  )}
                </button>
                <button onClick={handleBatchDelete}
                  disabled={selectedConvIds.size === 0 || isBatchDeleting}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-white bg-destructive hover:bg-destructive/90 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors flex-1 justify-center shadow-sm">
                  {isBatchDeleting ? (
                    <><icons.Loader2 className="w-3.5 h-3.5 animate-spin" /> 删除中...</>
                  ) : (
                    <><icons.Trash2 className="w-3.5 h-3.5" /> 删除所选 ({selectedConvIds.size})</>
                  )}
                </button>
              </div>
            )}

            <div className="flex-1 overflow-y-auto py-2">
              {conversations.length === 0 ? (
                <div className="text-center text-muted-foreground text-sm mt-8 px-4">
                  <icons.MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  <p className="text-muted-foreground">暂无对话记录</p>
                  <p className="text-xs mt-1 text-muted-foreground">开始新对话后将在此处显示</p>
                </div>
              ) : conversations.map((conv) => {
                const isActive = conv.id === conversationId;
                const isEditing = editingConvId === conv.id;
                const isSelected = selectedConvIds.has(conv.id);
                return (
                  <div key={conv.id} onClick={() => batchMode ? handleToggleSelect(conv.id) : (!isEditing && handleSwitchConversation(conv))}
                    className={`group relative mx-2 mb-0.5 rounded-lg cursor-pointer transition-colors ${
                      batchMode && isSelected
                        ? 'bg-destructive/5 text-destructive border border-destructive/20'
                        : isActive && !batchMode
                        ? 'bg-primary/5 text-primary border border-primary/10'
                        : 'text-foreground/80 hover:bg-muted/50 border border-transparent'
                    }`}>
                    <div className="flex items-center gap-3 px-3 py-2.5">
                      {batchMode ? (
                        <div className="flex-shrink-0" onClick={(e) => handleToggleSelect(conv.id, e)}>
                          {isSelected ? (
                            <icons.Check className="w-4 h-4 text-destructive" />
                          ) : (
                            <icons.Circle className="w-4 h-4 text-muted-foreground" />
                          )}
                        </div>
                      ) : (
                        <icons.MessageSquare className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-primary' : 'text-muted-foreground'}`} />
                      )}
                      <div className="flex-1 min-w-0">
                        {isEditing && !batchMode ? (
                          <input ref={editInputRef} value={editingTitle} onChange={(e) => setEditingTitle(e.target.value)}
                            onBlur={handleFinishRename} onKeyDown={(e) => { if (e.key === 'Enter') handleFinishRename(); if (e.key === 'Escape') setEditingConvId(null); }}
                            onClick={(e) => e.stopPropagation()}
                            className="w-full bg-background text-foreground text-sm px-2 py-0.5 rounded border border-primary/30 focus:outline-none focus:border-primary" />
                        ) : (
                          <>
                            <p className={`text-sm truncate font-medium ${
                              batchMode && isSelected ? 'text-destructive' : isActive && !batchMode ? 'text-primary' : 'text-foreground'
                            }`}>{conv.title || '未命名对话'}</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">
                              {formatConvDate(conv.last_message_at || conv.created_at)}
                              {conv.message_count > 0 && ` · ${conv.message_count}条`}
                            </p>
                          </>
                        )}
                      </div>
                      {!isEditing && !batchMode && (
                        <div className={`flex items-center gap-0.5 ${isActive ? 'visible' : 'invisible group-hover:visible'}`}>
                          <button onClick={(e) => { e.stopPropagation(); setMenuOpenId(menuOpenId === conv.id ? null : conv.id); }}
                            className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors">
                            <icons.MoreHorizontal className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                    <AnimatePresence>
                      {!batchMode && menuOpenId === conv.id && (
                        <motion.div initial={{ opacity: 0, y: -5, scale: 0.95 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -5, scale: 0.95 }}
                          className="absolute right-2 top-full z-50 bg-background border border-border rounded-lg shadow-lg py-1 min-w-[120px]" onClick={(e) => e.stopPropagation()}>
                          <button onClick={(e) => handleStartRename(conv, e)} className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50">
                            <icons.Edit className="w-3 h-3" /> 重命名
                          </button>
                          <button onClick={(e) => handleDeleteConversation(conv.id, e)} className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-destructive hover:text-destructive hover:bg-destructive/5">
                            <icons.Trash2 className="w-3 h-3" /> 删除
                          </button>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })}
            </div>
            <div className="p-3 border-t border-border/50 text-center">
              <p className="text-[10px] text-muted-foreground">共 {conversations.length} 个对话</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 对话列表 ↔ 聊天区 拖拽分隔条 */}
      {chatSidebarOpen && !isMobile && (
        <div
          className="w-[2px] cursor-col-resize shrink-0 group relative flex items-center justify-center before:absolute before:inset-y-0 before:left-1/2 before:-translate-x-1/2 before:w-px before:bg-border hover:before:bg-primary/40 before:transition-colors"
          onMouseDown={(e) => {
            e.preventDefault();
            setIsDragging(true);
            const startX = e.clientX;
            const startWidth = sidebarWidth;
            const onMove = (ev: MouseEvent) => {
              const delta = ev.clientX - startX;
              setSidebarWidth(Math.min(400, Math.max(200, startWidth + delta)));
            };
            const onUp = () => {
              setIsDragging(false);
              document.removeEventListener('mousemove', onMove);
              document.removeEventListener('mouseup', onUp);
            };
            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);
          }}
        />
      )}

      {/* ========== 主内容区 ========== */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        <div className="flex-1 flex overflow-hidden">
          {/* 左侧聊天区 — 自适应宽度，拖拽时禁用动画防止卡顿 */}
          <div
            className={`flex flex-col bg-background relative ${isDragging ? '' : 'transition-all duration-300 ease-in-out'}`}
            style={{ width: rightPanelOpen && !isMobile ? `${100 - rightPanelWidth}%` : '100%', minWidth: 0 }}
          >
            {/* Header — v3 紧凑版 */}
            <div className="h-12 px-4 border-b border-border flex items-center gap-2.5 bg-background/80 backdrop-blur-sm shrink-0">
              {!chatSidebarOpen && (
                <button onClick={() => setChatSidebarOpen(true)}
                  className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors" title="展开对话列表">
                  <icons.ChevronRight className="w-4 h-4" />
                </button>
              )}
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-foreground">AI 法务助手</span>
                <span className={`flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full font-medium border ${
                  wsConnected
                    ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800'
                    : 'text-muted-foreground bg-muted border-border'
                }`}>
                  <div className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-emerald-500' : 'bg-muted-foreground'}`} />
                  {wsConnected ? '在线' : '连接中'}
                </span>
              </div>
              <div className="flex-1" />
              {/* 智能工作台面板切换 */}
              {!isMobile && (
                <button
                  onClick={toggleRightPanel}
                  className={`p-1.5 rounded-lg transition-colors ${
                    rightPanelOpen
                      ? 'text-primary bg-primary/5 hover:bg-primary/10'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                  }`}
                  title={rightPanelOpen ? '收起智能工作台' : '展开智能工作台'}
                >
                  {rightPanelOpen ? <icons.ChevronRight className="w-4 h-4" /> : <icons.LayoutDashboard className="w-4 h-4" />}
                </button>
              )}
            </div>

            {/* Messages — 支持拖拽上传，移动端额外底部内边距防止 BottomActionBar 遮挡 */}
            <div
              ref={messagesContainerRef}
              className={`flex-1 overflow-y-auto p-4 md:p-8 space-y-6 scroll-smooth relative ${isMobile ? 'pb-20' : ''}`}
              onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragOver(true); }}
              onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragOver(false); }}
              onDrop={(e) => {
                e.preventDefault(); e.stopPropagation(); setIsDragOver(false);
                const f = e.dataTransfer.files?.[0];
                if (f) {
                  // 复用文件输入框的处理逻辑
                  const workflow = inferAttachmentWorkflow(f);
                  setPendingFile(f);
                  setActiveActionId(workflow.actionId);
                  setActionModeOverride(workflow.mode);
                  setInput((prev) => (prev.trim() ? prev : workflow.prompt));
                  toast.success(`已附加: ${f.name}，已切换到${workflow.label}`);
                  if (workflow.triggerContractReview) {
                    store.setContractReviewFile(f);
                    store.setContractReviewVisible(true);
                  }
                  if (workflow.openSmartPanel) openRightPanel('smart');
                }
              }}
            >
              {/* 拖拽上传蒙层 */}
              {isDragOver && (
                <div className="absolute inset-0 z-50 flex items-center justify-center bg-primary/5 border-2 border-dashed border-primary/40 rounded-xl backdrop-blur-sm pointer-events-none">
                  <div className="flex flex-col items-center gap-2 text-primary">
                    <icons.Upload className="w-10 h-10" />
                    <span className="text-sm font-medium">释放以上传文件</span>
                    <span className="text-xs text-muted-foreground">支持 PDF、Word、Excel、CSV、PPT、TXT、图片</span>
                  </div>
                </div>
              )}
              {isLoadingHistory && (
                <div className="flex items-center justify-center py-8">
                  <icons.Loader2 className="w-5 h-5 animate-spin text-muted-foreground mr-2" />
                  <span className="text-sm text-muted-foreground">正在加载对话历史...</span>
                </div>
              )}
              {messages.map(renderMessage)}

              {/* 思考链（嵌入消息流中，作为 AI 回复的一部分） */}
              {store.thinkingSteps.length > 0 && (
                <ThinkingChain steps={store.thinkingSteps} isThinking={isProcessing} />
              )}

              {/* 流式消息 — 法律文书生成时实时清理 Agent 系统噪音 */}
              {store.streamingMessageId && (
                <StreamingMessage
                  content={
                    store.streamingContent.length > 200 && isDocumentGeneration(store.streamingContent)
                      ? cleanCanvasContent(store.streamingContent)
                      : store.streamingContent
                  }
                  agent={store.streamingAgent}
                  isStreaming={true}
                />
              )}

              {/* 流式 A2UI 渲染器 — 骨架屏 + 渐进式卡片生长 */}
              {activeStreams.length > 0 && (
                <div className="space-y-3">
                  {activeStreams.map(stream => (
                    <StreamingA2UIRenderer
                      key={stream.streamId}
                      stream={stream}
                      onEvent={handleA2UIEvent}
                      isMobile={isMobile}
                    />
                  ))}
                </div>
              )}

              {/* 内联 Agent 思考指示器 — 替代打开面板 */}
              {isProcessing && !store.streamingMessageId && (
                <AnimatePresence>
                  {thinkingStatus ? (
                    <ThinkingIndicator status={thinkingStatus} />
                  ) : store.thinkingSteps.length === 0 ? (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                      <div className="bg-muted rounded-2xl px-4 py-3 flex items-center gap-2">
                        <icons.Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">AI 正在思考...</span>
                      </div>
                    </motion.div>
                  ) : null}
                </AnimatePresence>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* 回到底部悬浮按钮 — 用户向上滚动时显示 */}
            <AnimatePresence>
              {userScrolledUp && isProcessing && (
                <motion.button
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  onClick={() => {
                    setUserScrolledUp(false);
                    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
                  }}
                  className="absolute bottom-20 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1.5 px-3 py-1.5 bg-primary text-white text-xs font-medium rounded-full shadow-lg hover:bg-primary/90 transition-colors"
                >
                  <icons.ChevronDown className="w-3.5 h-3.5" />
                  回到最新
                </motion.button>
              )}
            </AnimatePresence>

            {/* 消息区 ↔ 输入区 拖拽分隔条 */}
            <div
              className="h-[2px] cursor-row-resize shrink-0 group relative flex items-center justify-center before:absolute before:inset-x-0 before:top-1/2 before:-translate-y-1/2 before:h-px before:bg-border hover:before:bg-primary/40 before:transition-colors"
              onMouseDown={(e) => {
                e.preventDefault();
                setIsDragging(true);
                const container = e.currentTarget.parentElement;
                if (!container) return;
                const startY = e.clientY;
                const containerH = container.offsetHeight;
                const inputEl = e.currentTarget.nextElementSibling as HTMLElement;
                const startH = inputEl?.offsetHeight || 160;
                const onMove = (ev: MouseEvent) => {
                  const delta = startY - ev.clientY;
                  const newH = Math.min(containerH * 0.6, Math.max(100, startH + delta));
                  setInputAreaHeight(newH);
                };
                const onUp = () => {
                  setIsDragging(false);
                  document.removeEventListener('mousemove', onMove);
                  document.removeEventListener('mouseup', onUp);
                };
                document.addEventListener('mousemove', onMove);
                document.addEventListener('mouseup', onUp);
              }}
            />

            {/* Input Area — 工作台一体化输入区 */}
            <div
              className="p-3 bg-background shrink-0 flex flex-col"
              style={inputAreaHeight ? { height: inputAreaHeight } : undefined}
            >
              <div className="flex-1 flex flex-col min-h-0">
                <AnimatePresence>
                  {pendingFile && (
                    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="mb-2">
                      <div className="flex items-center gap-2.5 px-3 py-2 bg-primary/5 border border-primary/10 rounded-xl">
                        <div className="bg-background p-1 rounded shadow-sm"><icons.FileText className="w-3.5 h-3.5 text-primary" /></div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-foreground truncate">{pendingFile.name}</p>
                          <p className="text-[10px] text-muted-foreground">{(pendingFile.size / 1024).toFixed(1)} KB</p>
                        </div>
                        <button onClick={() => setPendingFile(null)} className="p-0.5 text-muted-foreground hover:text-destructive rounded">
                          <icons.X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* 快捷操作工具栏 — 常驻输入框上方 */}
                <QuickActionsBar
                  onFillInput={({ text, actionId, mode: filledMode }: QuickActionFillPayload) => {
                    setInput(text);
                    setActiveActionId(actionId ?? null);
                    setActionModeOverride(filledMode ?? null);
                    setTimeout(() => {
                      const el = chatInputRef.current;
                      if (el) {
                        el.focus();
                        el.setSelectionRange(text.length, text.length);
                      }
                    }, 50);
                  }}
                  isProcessing={isProcessing}
                  isMobile={isMobile}
                  activeActionId={activeActionId}
                  attachmentName={pendingFile?.name ?? null}
                  onTriggerUpload={() => fileInputRef.current?.click()}
                />

                <KnowledgeBaseSelector
                  selectedKbIds={selectedKbIds}
                  onSelectionChange={handleSelectedKbIdsChange}
                  disabled={isProcessing}
                />

                {/* 输入框容器 — 一体式设计 */}
                <div className={`relative flex bg-muted/50 rounded-2xl border border-border focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-primary/10 transition-all ${inputAreaHeight ? 'flex-1 min-h-0' : ''}`}>
                  {/* 斜杠命令面板 — 输入框上方浮层 */}
                  <SlashCommandPalette
                    inputValue={input}
                    onSelect={handleSlashCommandSelect}
                    onClose={() => setSlashPaletteOpen(false)}
                    visible={slashPaletteOpen}
                  />
                  {/* 附件按钮 */}
                  <input ref={fileInputRef} type="file" className="hidden"
                    accept=".pdf,.doc,.docx,.txt,.md,.xlsx,.xls,.csv,.pptx,image/*"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) {
                        const workflow = inferAttachmentWorkflow(f);
                        setPendingFile(f);
                        setActiveActionId(workflow.actionId);
                        setActionModeOverride(workflow.mode);
                        setSlashPaletteOpen(false);
                        setInput((prev) => (prev.trim() ? prev : workflow.prompt));
                        toast.success(`已附加: ${f.name}，已切换到${workflow.label}`);

                        if (workflow.triggerContractReview) {
                          store.setContractReviewFile(f);
                          store.setContractReviewVisible(true);
                        }
                        if (workflow.openSmartPanel) {
                          openRightPanel('smart');
                        }

                        setTimeout(() => {
                          const el = chatInputRef.current;
                          if (!el) return;
                          el.focus();
                          if (!input.trim()) {
                            const nextValue = workflow.prompt;
                            el.setSelectionRange(nextValue.length, nextValue.length);
                          }
                        }, 50);
                      }
                      if (e.target) e.target.value = '';
                    }}
                    />
                  <button onClick={() => fileInputRef.current?.click()} disabled={isProcessing}
                    className="p-2.5 text-muted-foreground hover:text-primary transition-colors disabled:opacity-50 flex-shrink-0 self-end"
                    title="上传文件">
                    <icons.Paperclip className="w-4.5 h-4.5" />
                  </button>

                  {/* 文本输入 */}
                  <textarea
                    ref={chatInputRef}
                    value={input}
                    onChange={(e) => {
                      setInput(e.target.value);
                      // 用户手动编辑/清空输入框时取消快捷操作高亮
                      if (!e.target.value.trim()) {
                        setActiveActionId(null);
                        setActionModeOverride(null);
                      }
                    }}
                    onKeyPress={handleKeyPress}
                    placeholder={dynamicPlaceholder}
                    className="flex-1 py-2.5 bg-transparent border-none resize-none focus:outline-none text-foreground placeholder:text-muted-foreground text-sm leading-relaxed self-stretch"
                    style={{ minHeight: '56px', maxHeight: inputAreaHeight ? 'none' : '300px', height: inputAreaHeight ? '100%' : undefined }}
                    disabled={isProcessing}
                    rows={2}
                  />

                  {/* 右侧功能按钮组：深度思考 + 发送 */}
                  <div className="flex items-center gap-0.5 flex-shrink-0 self-end">
                    {/* 深度思考开关 — 输入框内右侧 */}
                    <DeepModeToggle
                      isActive={quickActionMode === 'deep_analysis'}
                      onToggle={() => setQuickActionMode(prev => prev === 'deep_analysis' ? 'chat' : 'deep_analysis')}
                      disabled={isProcessing}
                    />
                    {/* 分隔线 */}
                    <div className="w-px h-5 bg-border mx-0.5" />
                    {/* 发送按钮 */}
                    <button
                      onClick={() => handleSendMessage()}
                      disabled={!input.trim() || isProcessing}
                      className={`p-2 m-1 rounded-xl transition-all disabled:opacity-30 flex-shrink-0 ${
                        input.trim()
                          ? 'bg-primary text-white hover:bg-primary/90 active:scale-95 shadow-sm'
                          : 'bg-transparent text-muted-foreground/50'
                      }`}
                    >
                      {isProcessing ? <icons.Loader2 className="w-4 h-4 animate-spin" /> : <icons.Send className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* 底部提示 — 更简洁 */}
                <div className="flex items-center justify-center gap-3 mt-1.5">
                  <div className={`flex items-center gap-1 text-[10px] font-medium ${privacyHint.color}`}>
                    <PrivacyIcon className="w-2.5 h-2.5" />
                    <span>{privacyHint.text}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 聊天区 ↔ 智能工作台 拖拽分隔条 */}
          {!isMobile && rightPanelOpen && (
            <div
              className="w-[2px] cursor-col-resize shrink-0 group relative z-10 flex items-center justify-center before:absolute before:inset-y-0 before:left-1/2 before:-translate-x-1/2 before:w-px before:bg-border hover:before:bg-primary/40 before:transition-colors"
              onMouseDown={(e) => {
                e.preventDefault();
                setIsDragging(true);
                const container = e.currentTarget.parentElement;
                if (!container) return;
                const containerWidth = container.offsetWidth;
                const startX = e.clientX;
                const startPct = rightPanelWidth;
                const onMove = (ev: MouseEvent) => {
                  const deltaPx = startX - ev.clientX;
                  const deltaPct = (deltaPx / containerWidth) * 100;
                  setRightPanelWidth(Math.min(70, Math.max(25, startPct + deltaPct)));
                };
                const onUp = () => {
                  setIsDragging(false);
                  document.removeEventListener('mousemove', onMove);
                  document.removeEventListener('mouseup', onUp);
                };
                document.addEventListener('mousemove', onMove);
                document.addEventListener('mouseup', onUp);
              }}
            />
          )}

          {/* ========== 右侧面板 — 默认收起,任务触发展开 ========== */}
          <AnimatePresence>
            {!isMobile && rightPanelOpen && (
              <motion.div
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: `${rightPanelWidth}%`, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                transition={{ duration: 0.3, ease: 'easeInOut' }}
                className="bg-muted overflow-hidden relative"
              >
                <RightPanel
                  activeTab={store.rightPanelTab}
                  onTabChange={store.setRightPanelTab}
                  onClosePanel={closeRightPanel}
                  isLive={isProcessing}
                  agentResults={store.agentResults}
                  thinkingSteps={store.thinkingSteps}
                  a2uiData={store.a2uiData}
                  requirementAnalysis={store.requirementAnalysis}
                  isProcessing={isProcessing}
                  canvasContent={store.canvasContent}
                  onCanvasContentChange={handleCanvasContentChange}
                  onCanvasTitleChange={(title) => store.canvasContent && store.setCanvasContent({ ...store.canvasContent, title })}
                  onCanvasModeChange={(mode) => store.canvasContent && store.setCanvasContent({ ...store.canvasContent, type: mode })}
                  onCanvasAIOptimize={handleCanvasAIOptimize}
                  onCanvasSuggestionAction={handleCanvasSuggestionAction}
                  onForwardToLawyer={handleForwardToLawyer}
                  onInitiateSigning={handleInitiateSigning}
                  onCanvasSaveAsDocument={handleCanvasSaveAsDocument}
                  canvasSaved={canvasSaved}
                  analysisData={store.analysisData}
                  onWorkspaceConfirm={handleWorkspaceConfirm}
                  onWorkspaceAction={handleWorkspaceAction}
                  onDocumentAction={handleDocumentAction}
                  onNewConversation={handleNewConversation}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Mobile Panel — 底部抽屉（从底部滑入，覆盖 80% 高度） */}
        <AnimatePresence>
          {isMobile && showContextPanel && (
            <>
              {/* 遮罩层 */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-40 bg-black/40"
                onClick={() => setShowContextPanel(false)}
              />
              {/* 底部抽屉面板 */}
              <motion.div
                initial={{ y: '100%' }}
                animate={{ y: 0 }}
                exit={{ y: '100%' }}
                transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                className="fixed bottom-0 left-0 right-0 z-50 bg-background flex flex-col rounded-t-2xl shadow-2xl"
                style={{ maxHeight: '85vh' }}
              >
                {/* 拖拽指示器 */}
                <div className="flex justify-center pt-3 pb-1">
                  <div className="w-10 h-1 bg-muted-foreground/50 rounded-full" />
                </div>
                <div className="px-4 pb-2 flex justify-between items-center border-b border-border/50">
                  <h3 className="font-bold text-base text-foreground">智能工作台</h3>
                  <button
                    onClick={() => setShowContextPanel(false)}
                    className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg"
                  >
                    <icons.X className="w-5 h-5" />
                  </button>
                </div>
                <div className="flex-1 overflow-auto">
                  <RightPanel
                    activeTab={store.rightPanelTab}
                    onTabChange={store.setRightPanelTab}
                    isLive={isProcessing}
                    agentResults={store.agentResults}
                    thinkingSteps={store.thinkingSteps}
                    a2uiData={store.a2uiData}
                    requirementAnalysis={store.requirementAnalysis}
                    isProcessing={isProcessing}
                    canvasContent={store.canvasContent}
                    onCanvasContentChange={handleCanvasContentChange}
                    onCanvasTitleChange={(title) => store.canvasContent && store.setCanvasContent({ ...store.canvasContent, title })}
                    onCanvasModeChange={(mode) => store.canvasContent && store.setCanvasContent({ ...store.canvasContent, type: mode })}
                    onCanvasAIOptimize={handleCanvasAIOptimize}
                    onCanvasSuggestionAction={handleCanvasSuggestionAction}
                    onForwardToLawyer={handleForwardToLawyer}
                    onInitiateSigning={handleInitiateSigning}
                    onCanvasSaveAsDocument={handleCanvasSaveAsDocument}
                    canvasSaved={canvasSaved}
                    analysisData={store.analysisData}
                    onWorkspaceConfirm={handleWorkspaceConfirm}
                    onWorkspaceAction={handleWorkspaceAction}
                    onDocumentAction={handleDocumentAction}
                    onNewConversation={handleNewConversation}
                  />
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>

        {/* 删除对话确认弹窗 */}
        <AnimatePresence>
          {deleteConfirmId && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm"
              onClick={() => setDeleteConfirmId(null)}>
              <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
                className="bg-background rounded-2xl shadow-2xl p-6 w-80 mx-4" onClick={(e) => e.stopPropagation()}>
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-destructive/5 rounded-full"><icons.Trash2 className="w-5 h-5 text-destructive" /></div>
                  <h3 className="text-lg font-semibold text-foreground">确认删除</h3>
                </div>
                <p className="text-sm text-muted-foreground mb-6">
                  确定要删除这个对话吗？删除后将无法恢复。
                </p>
                <div className="flex gap-3 justify-end">
                  <button onClick={() => setDeleteConfirmId(null)}
                    className="px-4 py-2 text-sm font-medium text-muted-foreground bg-muted rounded-lg hover:bg-muted transition-colors">
                    取消
                  </button>
                  <button onClick={confirmDeleteConversation}
                    className="px-4 py-2 text-sm font-medium text-white bg-destructive rounded-lg hover:bg-destructive/90 transition-colors">
                    确认删除
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}


// ========== 引导式问答气泡组件 — v3 优化版 ==========
// 核心改进：
// 1. 选择后立即锁定（不可修改、不可多选）
// 2. 提交后不再输出选择内容到对话流（直接显示"已确认"状态）
// 3. 提交后的选择以紧凑标签形式展示，不重复出现
function ClarificationBubble({ message, questions, originalContent, onSubmit, disabled }: {
  message: string;
  questions: { question: string; options: string[] }[];
  originalContent: string;
  onSubmit: (originalContent: string, selections: Record<string, string>) => void;
  disabled: boolean;
}) {
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);

  const handleSelect = (question: string, option: string) => {
    // 已提交或已有选择时不可更改（单选锁定）
    if (submitted || selections[question]) return;
    setSelections(prev => ({ ...prev, [question]: option }));
  };

  const handleSubmit = () => {
    if (submitted || disabled) return;
    const valid = Object.fromEntries(Object.entries(selections).filter(([_, v]) => v));
    if (Object.keys(valid).length === 0) return;
    setSubmitted(true);
    // 直接发送到后端，不在对话流中重复输出选择文字
    onSubmit(originalContent, valid);
  };

  const answeredCount = Object.values(selections).filter(v => v).length;
  const allAnswered = answeredCount === questions.length;

  // 提交后的紧凑视图
  if (submitted) {
    return (
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3 items-start">
        <div className="w-8 h-8 rounded-full bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center flex-shrink-0">
          <icons.CheckCircle className="h-4 w-4 text-emerald-600" />
        </div>
        <div className="flex flex-col gap-1 max-w-[80%]">
          <div className="bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-2xl rounded-tl-none px-4 py-3">
            <div className="flex items-center gap-1.5 mb-2">
              <span className="text-xs font-semibold text-emerald-600">已确认需求</span>
              <icons.Loader2 className="w-3 h-3 animate-spin text-emerald-600" />
              <span className="text-[10px] text-emerald-600">处理中...</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(selections).filter(([_, v]) => v).map(([q, a]) => (
                <span key={q} className="inline-flex items-center gap-1 px-2 py-1 bg-background rounded-lg text-[11px] text-foreground/80 border border-emerald-200">
                  <icons.CheckCircle className="w-2.5 h-2.5 text-emerald-600" />
                  {a}
                </span>
              ))}
            </div>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3 items-start">
      <div className="w-8 h-8 rounded-full bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 flex items-center justify-center flex-shrink-0">
        <icons.HelpCircle className="h-4 w-4 text-amber-500" />
      </div>
      <div className="flex flex-col gap-1.5 max-w-[85%]">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground ml-1">
          <icons.Sparkles className="h-3 w-3 text-amber-500" /> 需求确认
        </div>
        <div className="bg-background border border-border rounded-2xl rounded-tl-none px-4 py-3.5 shadow-sm">
          <p className="text-sm text-foreground/80 mb-3 leading-relaxed">{message}</p>
          <div className="space-y-3">
            {questions.map((q, qi) => {
              const isAnswered = !!selections[q.question];
              return (
                <div key={qi}>
                  <p className="text-xs font-medium text-foreground mb-1.5">{q.question}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {q.options.map((opt, oi) => {
                      const isSelected = selections[q.question] === opt;
                      const isLocked = isAnswered && !isSelected;
                      return (
                        <button
                          key={oi}
                          onClick={() => handleSelect(q.question, opt)}
                          disabled={isLocked}
                          className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                            isSelected
                              ? 'bg-primary text-white border-primary shadow-sm scale-[1.02]'
                              : isLocked
                              ? 'bg-muted/50 text-muted-foreground/50 border-border/50 cursor-not-allowed'
                              : 'bg-background text-muted-foreground border-border hover:border-primary/30 hover:text-primary hover:bg-primary/5 cursor-pointer active:scale-95'
                          }`}
                        >
                          {opt}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
          {/* 确认按钮 — 仅全部选择后显示 */}
          <AnimatePresence>
            {allAnswered && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <button
                  onClick={handleSubmit}
                  disabled={disabled}
                  className="mt-3 w-full flex items-center justify-center gap-1.5 px-4 py-2.5 bg-primary text-white text-sm font-medium rounded-xl hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-[0.98] shadow-sm"
                >
                  <span>确认并继续</span>
                  <icons.ChevronRight className="w-4 h-4" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>
          {!allAnswered && (
            <p className="text-[10px] text-muted-foreground mt-2 text-center">
              请逐一选择 · 已完成 {answeredCount}/{questions.length}
            </p>
          )}
        </div>
      </div>
    </motion.div>
  );
}
