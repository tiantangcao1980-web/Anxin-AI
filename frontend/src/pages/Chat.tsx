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

import { useState, useRef, useEffect, useCallback, useMemo } from'react';
import { Resizable } from're-resizable';
import { motion, AnimatePresence } from'framer-motion';
import { icons } from'@/lib/icons';
import ReactMarkdown from'react-markdown';
import { chatApi } from'@/lib/api';
import { useChatStore, ConversationItem } from'@/lib/store';
import type { AgentResult, ThinkingStep, CanvasContent } from'@/lib/store';
import { usePrivacy, PrivacyMode } from'@/context/PrivacyContext';
import { cn } from'@/lib/utils';
import { toast } from'sonner';
import { v4 as uuidv4 } from'uuid';
import { CitationList } from'@/components/chat/CitationList';
import { LottieIcon } from'@/components/ui/LottieIcon';
import { RightPanel } from'@/components/chat/RightPanel';
import { StreamingMessage } from'@/components/chat/StreamingMessage';
import { ThinkingChain } from'@/components/chat/ThinkingChain';
import { DeepModeToggle, type QuickActionFillPayload } from'@/components/chat/QuickActionsBar';
import { InputOrchestrationBar } from'@/components/chat/InputOrchestrationBar';
import { SlashCommandPalette, useSlashCommand, type SlashCommand } from'@/components/chat/SlashCommandPalette';
import { ThinkingIndicator, type ThinkingStatus } from'@/components/chat/ThinkingIndicator';
import { ClarificationBubble } from'@/components/chat/ClarificationBubble';
import {
 getWorkflowAction,
 getWorkflowPlaceholder,
 getWorkflowPrompt,
 inferAttachmentWorkflow,
 type QuickActionMode,
} from'@/components/chat/workflowConfig';
import { A2UIRenderer, StreamingA2UIRenderer, useStreamingA2UI } from'@/components/a2ui';
import { MobileA2UIAdapter } from'@/components/a2ui/MobileA2UIAdapter';
import type { A2UIMessage, A2UIEvent, A2UIStreamEvent, A2UIComponent } from'@/components/a2ui';
// Harness: Chat.tsx 拆分 — 提取的 hooks
import { useCanvasOperations } from'@/hooks/useCanvasOperations';
import { useConversationManager } from'@/hooks/useConversationManager';
import { useSmartScroll } from'@/hooks/useSmartScroll';

// Canvas 工具函数 + 追问建议生成（已提取到独立文件）
import { cleanCanvasTitle, cleanCanvasContent, isDocumentGeneration, generateFollowUpSuggestions } from'@/components/chat/canvasUtils';
// A2UI 映射表 + 工作台动作映射（已提取）
import { A2UI_ACTION_TO_MESSAGE, WORKSPACE_TO_WORKFLOW_ACTION } from'@/components/chat/a2uiActionMap';
// 提取的子组件
import { WelcomeScreen } from'@/components/chat/WelcomeScreen';
import { SystemMessage } from'@/components/chat/SystemMessage';

// 类型定义和常量（已提取到独立文件）
import type { Message } from'@/components/chat/types';
import { WELCOME_MESSAGE } from'@/components/chat/types';

// ========== 主组件 ==========

export default function Chat() {
 const store = useChatStore();
 const { mode } = usePrivacy();

 // 本地状态
 const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
 const [isProcessing, setIsProcessing] = useState(false);
 const isDesktopInit = typeof window !=='undefined' && window.innerWidth >= 1024;
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
 const [selectedTemplateIdsByConversation, setSelectedTemplateIdsByConversation] = useState<Record<string, string | null>>({});
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

 // Harness: 使用提取的智能滚动 hook（替代内联实现）
 const {
 messagesContainerRef, messagesEndRef, userScrolledUp, setUserScrolledUp,
 scrollToBottom, debouncedScrollToBottom, handleScroll: handleScrollEvent,
 } = useSmartScroll();

 // Refs
 const wsRef = useRef<WebSocket | null>(null);
 const fileInputRef = useRef<HTMLInputElement>(null);
 const editInputRef = useRef<HTMLInputElement>(null);
 const chatInputRef = useRef<HTMLTextAreaElement>(null);
 const clarificationRef = useRef<{ original_content: string } | null>(null);

 const {
 conversationId, setConversationId,
 conversations: rawConversations, setConversations, addConversation, removeConversation, removeConversations, updateConversationTitle,
 sidebarOpen: chatSidebarOpen, setChatSidebarOpen,
 } = store;
 // 防御性保护：确保 conversations 始终是数组（防止 persist 数据损坏）
 const conversations = Array.isArray(rawConversations) ? rawConversations : [];
 const conversationSelectionKey = conversationId ||'__draft__';
 const selectedKbIds = selectedKbIdsByConversation[conversationSelectionKey] || [];
 const selectedTemplateId = selectedTemplateIdsByConversation[conversationSelectionKey] || null;

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

 const handleSelectedTemplateChange = useCallback((templateId: string | null) => {
 setSelectedTemplateIdsByConversation((prev) => {
 if (!templateId) {
 if (!(conversationSelectionKey in prev)) return prev;
 const next = { ...prev };
 delete next[conversationSelectionKey];
 return next;
 }
 return {
 ...prev,
 [conversationSelectionKey]: templateId,
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

 const clearTemplateSelections = useCallback((conversationKeys: string[]) => {
 if (conversationKeys.length === 0) return;
 setSelectedTemplateIdsByConversation((prev) => {
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
 if (Array.isArray(result?.conversations)) setConversations(result.conversations);
 } catch (e) { import.meta.env.DEV && console.debug('加载对话列表失败:', e); }
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
 wsRef.current.close(1000,'switching conversation');
 wsRef.current = null;
 }
 }, []);

 const handleNewConversation = useCallback(() => {
 // 保存当前对话的工作台状态到缓存
 if (conversationId) {
 store.saveWorkspaceToCache(conversationId);
 }
 closeCurrentWs();
 const newId = uuidv4();
 setConversationId(newId);
 // 保持 id 不变：React 复用已挂载的 WelcomeScreen，避免 framer-motion 重新入场动画
 // 造成的短暂 opacity:0 —— 这会导致 E2E 测试偶发 timeout。
 setMessages([WELCOME_MESSAGE]);
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

 // 1. 保存当前对话的工作台状态到缓存
 if (conversationId) {
 store.saveWorkspaceToCache(conversationId);
 }

 closeCurrentWs();
 setConversationId(conv.id);
 setMessages([WELCOME_MESSAGE]);
 setHistoryLoaded(false); // 触发重新加载历史
 setIsLoadingHistory(false);
 setIsProcessing(false);

 // 2. 尝试从缓存恢复目标对话的工作台状态
 const restored = store.restoreWorkspaceFromCache(conv.id);
 if (!restored) {
 // 缓存没有 — 从后端 API 加载该对话的历史文档
 store.resetWorkspace();
 import('@/lib/api').then(({ chatApi }) => {
 // 加载最新一份文档到 Canvas
 chatApi.getConversationCanvas(conv.id).then(canvas => {
 if (canvas && canvas.content) {
 store.setCanvasContent({
 type: (canvas.type as any) ||'document',
 title: canvas.title ||'历史文档',
 content: canvas.content,
 suggestions: [],
 });
 // 自动打开右侧文档面板
 setTimeout(() => openRightPanel?.('document'), 300);
 }
 }).catch(() => {});

 // 加载完整文档列表到工作台（用于"历史文档"选择）
 chatApi.listConversationDocuments(conv.id).then(result => {
 const items = result?.items || [];
 if (items.length > 0) {
 store.setDocumentList?.(items.map(d => ({
 id: d.id,
 title: d.title,
 type: (d.type as any) ||'document',
 updatedAt: d.updated_at,
 preview: d.preview,
 })));
 }
 }).catch(() => {});
 });
 }
 }, [conversationId, closeCurrentWs, setConversationId, store, openRightPanel]);

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
 store.clearWorkspaceCache(convId);
 clearKnowledgeBaseSelections([convId]);
 clearTemplateSelections([convId]);
 toast.success('对话已删除');
 if (convId === conversationId) handleNewConversation();
 } catch { toast.error('删除失败'); }
 }, [clearKnowledgeBaseSelections, clearTemplateSelections, deleteConfirmId, conversationId, removeConversation, handleNewConversation]);

 const handleStartRename = useCallback((conv: ConversationItem, e?: React.MouseEvent) => {
 e?.stopPropagation();
 setMenuOpenId(null);
 setEditingConvId(conv.id);
 setEditingTitle(conv.title ||'');
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
 ids.forEach(id => store.clearWorkspaceCache(id));
 clearKnowledgeBaseSelections(ids);
 clearTemplateSelections(ids);
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
 }, [clearKnowledgeBaseSelections, clearTemplateSelections, selectedConvIds, conversationId, removeConversations, handleNewConversation]);

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
 type: /\.(jpg|jpeg|png|gif|webp|bmp|svg)$/i.test(attachMatch[1]) ?'image' :'file' as const,
 name: attachMatch[1].trim(),
 size:'',
 } : undefined;
 const displayContent = attachMatch ? m.content.replace(attachMatch[0],'').trim() : m.content;
 return {
 id: m.id || uuidv4(), type: m.role ==='user' ?'user' :'ai',
 content: displayContent || m.content,
 timestamp: new Date(m.created_at || Date.now()), agent: m.agent_name,
 attachment,
 sources: Array.isArray(m.sources) ? m.sources : undefined,
 };
 });
 // 加载历史时去掉欢迎消息，直接显示对话内容
 setMessages(hist);
 }
 } catch (e) {
 if (!cancelled) {
 console.warn('加载对话历史失败:', e);
 // 加载失败时给用户提示
 setMessages([{
 id: uuidv4(), type:'system', content:'对话历史加载失败，请重试',
 timestamp: new Date(), metadata: { isError: true },
 }]);
 }
 }

 // 同时恢复 Canvas 文档
 try {
 const canvasResult = await chatApi.getConversationCanvas(conversationId);
 if (!cancelled && canvasResult) {
 const canvasData = (canvasResult as any)?.data || canvasResult;
 if (canvasData?.content) {
 store.setCanvasContent({
 title: cleanCanvasTitle(canvasData.title ||'文档'),
 content: cleanCanvasContent(canvasData.content),
 type: (canvasData.type ==='contract' ?'contract' :'document') as any,
 suggestions: [],
 });
 }
 }
 } catch (e) {
 // Canvas 恢复失败不影响主流程
 }

 // 无论成功失败都标记完成，防止加载状态卡住
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

 // Harness: scrollToBottom / debouncedScrollToBottom 已移至 useSmartScroll hook

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
 const openRightPanel = useCallback((tab?:'smart' |'document') => {
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

 const processingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

 const getProcessingTimeoutMs = useCallback(() => {
 if (typeof window !=='undefined') {
 const testTimeout = (window as any).__TEST_PROCESSING_TIMEOUT_MS;
 if (typeof testTimeout ==='number' && Number.isFinite(testTimeout) && testTimeout > 0) {
 return testTimeout;
 }
 }
 return 90_000;
 }, []);

 const clearProcessingTimeout = useCallback(() => {
 if (processingTimeoutRef.current) {
 clearTimeout(processingTimeoutRef.current);
 processingTimeoutRef.current = null;
 }
 }, []);

 const armProcessingTimeout = useCallback(() => {
 clearProcessingTimeout();
 processingTimeoutRef.current = setTimeout(() => {
 setIsProcessing(false);
 store.finalizeStream();
 setMessages(prev => [
 ...prev,
 {
 id: uuidv4(),
 type:'system' as const,
 content:'请求超时，服务器未在规定时间内响应。请稍后重试。',
 timestamp: new Date(),
 },
 ]);
 }, getProcessingTimeoutMs());
 }, [clearProcessingTimeout, getProcessingTimeoutMs, store]);

 // ========== WebSocket 消息处理（v2 — 流式 + 思考链 + Agent 结果）==========

 const handleWebSocketMessage = useCallback((data: any) => {
 if (!['done','agent_response','error','task_force_complete'].includes(data?.type ||'')) {
 armProcessingTimeout();
 }
 switch (data.type) {
 // --- 思考 / Agent 状态 → 同步到思考链 ---
 case'agent_thinking':
 case'agent_start':
 setIsProcessing(true);
 // 更新内联思考指示器（不打开面板）
 setThinkingStatus({
 agent: data.agent ||'系统',
 message: data.message || data.content ||'正在分析...',
 });
 if (data.agent || data.message) {
 store.addThinkingStep({
 id: uuidv4(),
 agent: data.agent ||'系统',
 content: data.message || data.content ||'正在分析...',
 phase: data.type ==='agent_start' ?'planning' :'execution',
 timestamp: Date.now(),
 });
 }
 break;

 case'agent_working':
 setIsProcessing(true);
 setThinkingStatus({
 agent: data.agent ||'',
 message: data.message ||'正在执行任务...',
 });
 if (data.agent || data.message) {
 store.addThinkingStep({
 id: uuidv4(),
 agent: data.agent ||'',
 content: data.message ||'正在执行任务...',
 phase:'execution',
 timestamp: Date.now(),
 });
 }
 break;

 case'agent_complete':
 // 进度更新
 if (data.agent) {
 store.addThinkingStep({
 id: uuidv4(),
 agent: data.agent ||'',
 content: data.message ||'任务完成',
 phase:'result',
 timestamp: Date.now(),
 });
 }
 break;

 // --- 思考链内容 ---
 case'thinking_content':
 store.addThinkingStep({
 id: uuidv4(),
 agent: data.agent ||'',
 content: data.content ||'',
 phase: data.phase ||'execution',
 planSteps: data.plan_steps,
 timestamp: Date.now(),
 });
 break;

 // --- 需求分析结果 ---
 case'requirement_analysis':
 store.setRequirementAnalysis(data);
 // 如果有引导问题，根据设备类型选择交互方式
 if (data.guidance_questions && data.guidance_questions.length > 0) {
 const validQuestions = data.guidance_questions.filter(
 (q: any) => q.options && q.options.length > 0
 );

 if (isMobile && validQuestions.length > 0) {
 // === 移动端：在对话框内以 ClarificationBubble 形式展示 ===
 setIsProcessing(false);
 const mobileMsg: Message = {
 id: uuidv4(), type:'clarification',
 content: data.summary
 ? `我来帮您处理：${data.summary}\n\n为了更精准地满足需求，请补充以下信息：`
 :'为了更好地帮助您，请补充以下信息：',
 timestamp: new Date(), agent:'需求分析',
 clarification: {
 questions: validQuestions.map((q: any) => ({
 question: q.question,
 options: q.options,
 })),
 original_content: data.original_content ||'',
 },
 };
 setMessages(prev => [...prev, mobileMsg]);
 clarificationRef.current = { original_content: data.original_content ||'' };
 } else {
 // === 桌面端/Web端：在右侧工作台生成确认卡片 ===
 validQuestions.forEach((q: any, idx: number) => {
 store.addWorkspaceConfirmation({
 id: `req-confirm-${uuidv4()}`,
 title: q.question || `确认事项 ${idx + 1}`,
 description: q.purpose,
 type: q.options.length > 3 ?'multi' :'single',
 options: q.options.map((opt: string, i: number) => ({
 id: `opt-${i}`,
 label: opt,
 })),
 selectedIds: [],
 status:'pending',
 source:'需求分析Agent',
 callbackAction:'requirement_clarification',
 createdAt: Date.now(),
 });
 });
 }
 }
 // 如果需求完整，推送建议动作
 if (data.is_complete && data.suggested_agents && data.suggested_agents.length > 0) {
 store.addWorkspaceAction({
 id: `action-start-${uuidv4()}`,
 label:'开始处理',
 description: `将由 ${data.suggested_agents.join('、')} 协同处理`,
 icon:'quick',
 variant:'primary',
 action:'start_processing',
 payload: { suggested_agents: data.suggested_agents },
 });
 }
 break;

 // --- Agent 中间结果 → 右侧工作台 ---
 case'agent_result':
 store.addAgentResult({
 id: uuidv4(),
 agent: data.agent ||'',
 agentKey: data.agent_key,
 content: data.content ||'',
 step: data.step || 0,
 totalSteps: data.total_steps || 0,
 elapsed: data.elapsed,
 timestamp: Date.now(),
 });
 break;

 // --- Agent 任务看板（多 Agent 并列协作） ---
 case'agent_task_start':
 store.addAgentTask({
 id: data.task_id || uuidv4(),
 agent: data.agent ||'',
 agentKey: data.agent_key,
 description: data.description ||'',
 status:'running',
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

 case'agent_task_progress':
 if (data.task_id) {
 store.updateAgentTask(data.task_id, {
 progress: data.progress || 0,
 elapsed: data.elapsed,
 });
 }
 break;

 case'agent_task_complete':
 if (data.task_id) {
 store.updateAgentTask(data.task_id, {
 status:'completed',
 progress: 100,
 result: data.result ||'',
 elapsed: data.elapsed,
 completedAt: Date.now(),
 });
 }
 break;

 case'agent_task_failed':
 if (data.task_id) {
 store.updateAgentTask(data.task_id, {
 status:'failed',
 result: data.error ||'处理失败',
 });
 }
 break;

 // --- Agent 生命周期事件（重试/替换/降级/强制完成） ---
 case'agent_task_retry':
 setThinkingStatus({
 agent: data.agent ||'系统',
 message: `正在重试 (${data.attempt}/${data.max_retries})...`,
 });
 break;

 case'agent_replaced':
 setThinkingStatus({
 agent: data.replacement_agent ||'系统',
 message: `接管 ${data.failed_agent} 的任务...`,
 });
 break;

 case'task_degraded':
 // 降级输出通知
 if (data.task_id) {
 store.updateAgentTask(data.task_id, {
 status:'failed',
 result: data.message ||'降级输出',
 });
 }
 break;

 case'task_force_complete':
 setIsProcessing(false);
 setThinkingStatus(null);
 toast.warning?.('任务超时，已返回部分结果') ?? toast.error('任务超时');
 break;

 case'agent_tasks_batch':
 // 一次性推送多个 Agent 并列任务（含依赖关系，用于 DAG 层级分组展示）
 if (data.tasks && Array.isArray(data.tasks)) {
 store.setAgentTasks(data.tasks.map((t: any) => ({
 id: t.task_id || uuidv4(),
 agent: t.agent ||'',
 agentKey: t.agent_key,
 description: t.description ||'',
 status: t.status ||'queued',
 progress: t.progress || 0,
 startedAt: t.status ==='running' ? Date.now() : undefined,
 dependencies: t.dependencies || [],
 })));
 // 不再自动打开面板 — 由后端 panel_trigger 事件决定
 }
 break;

 // --- 工作台需求确认（从左侧触发右侧展示） ---
 case'workspace_confirmation':
 store.addWorkspaceConfirmation({
 id: data.confirmation_id || uuidv4(),
 title: data.title ||'请确认',
 description: data.description,
 type: data.selection_type ||'single',
 options: data.options || [],
 selectedIds: [],
 status:'pending',
 source: data.source || data.agent,
 callbackAction: data.callback_action,
 createdAt: Date.now(),
 });
 // workspace_confirmation 仍打开面板 — 用户需要交互
 openRightPanel('smart');
 break;

 // --- 工作台动作按钮推送 ---
 case'workspace_actions':
 if (data.actions && Array.isArray(data.actions)) {
 data.actions.forEach((a: any) => {
 store.addWorkspaceAction({
 id: a.id || uuidv4(),
 label: a.label ||'',
 description: a.description,
 icon: a.icon,
 variant: a.variant ||'secondary',
 action: a.action ||'',
 payload: a.payload,
 disabled: a.disabled,
 });
 });
 // 不再自动打开面板 — 由后端 panel_trigger 事件决定
 }
 break;

 // --- 流式 token ---
 case'content_token':
 if (!store.streamingMessageId) {
 const newId = uuidv4();
 store.startStream(newId, data.agent ||'');
 }
 store.appendStreamToken(data.token ||'');
 break;

 // --- A2UI 上下文更新 ---
 case'context_update':
 if (data.context_type ==='a2ui') {
 if (data.data?.a2ui?.components) {
 store.appendA2uiComponents(data.data.a2ui.components);
 } else {
 store.setA2uiData(data.data);
 }
 if (isMobile) setShowContextPanel(true);
 }
 break;

 // --- A2UI 消息（直接嵌入对话流的结构化 UI） ---
 case'a2ui_message': {
 const a2uiMsg: Message = {
 id: uuidv4(),
 type:'a2ui',
 content: data.text ||'',
 timestamp: new Date(),
 agent: data.agent ||'AI 助手',
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
 case'a2ui_stream': {
 const streamEvt = data as A2UIStreamEvent;
 // 委托给 useStreamingA2UI Hook 管理流式状态（含骨架屏、增量更新）
 handleA2UIStreamEvent(streamEvt);

 // stream_component / stream_delta / stream_end 时同步到消息列表以持久化
 if (
 streamEvt.action ==='stream_component' ||
 streamEvt.action ==='stream_delta' ||
 streamEvt.action ==='stream_end'
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
 completed: streamEvt.action ==='stream_end' ? true : (m.a2ui as any)?.completed,
 },
 } : m);
 }
 return [...prev, {
 id: sid,
 type:'a2ui' as const,
 content:'',
 timestamp: new Date(),
 agent: streamState.agent ||'AI 助手',
 a2ui: {
 id: sid,
 components: [...streamState.components],
 completed: streamEvt.action ==='stream_end',
 },
 }];
 });
 }
 });
 }
 break;
 }

 // --- 后端主动触发面板 ---
 case'panel_trigger':
 if (data.tab) {
 if (isMobile) {
 // 移动端：打开底部抽屉
 store.setRightPanelTab(data.tab as'smart' |'document');
 setShowContextPanel(true);
 } else {
 openRightPanel(data.tab as'smart' |'document');
 }
 }
 break;

 // --- Canvas 打开 ---
 case'canvas_open':
 store.setCanvasContent({
 type: data.type ||'document',
 title: cleanCanvasTitle(data.title ||'文档'),
 content: cleanCanvasContent(data.content ||''),
 language: data.language,
 metadata: data.metadata,
 });
 openRightPanel('document');
 break;

 // --- Canvas AI 更新 ---
 case'canvas_update':
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
 case'tab_switch':
 if (data.tab) {
 // 将旧 Tab 名映射到新面板
 const tabMap: Record<string, string> = {
 workspace:'smart', canvas:'document', analysis:'smart',
 lawyer:'document', signing:'document',
 };
 const mappedTab = tabMap[data.tab] || data.tab;
 if (mappedTab ==='smart' || mappedTab ==='document') {
 openRightPanel(mappedTab as'smart' |'document');
 }
 // 如果后端建议律师/签约，打开浮层
 if (data.tab ==='lawyer') store.setDocumentOverlay('lawyer');
 if (data.tab ==='signing') store.setDocumentOverlay('signing');
 }
 break;

 // --- 律师协助消息 ---
 case'lawyer_comment':
 if (data.comment) {
 store.addLawyerComment(data.comment);
 }
 break;

 case'lawyer_request_update':
 if (data.request) {
 store.setActiveAssistRequest(data.request);
 }
 break;

 // --- 律师在线状态更新 ---
 case'lawyer_status':
 if (data.lawyers) {
 store.setOnlineLawyers(data.lawyers);
 }
 break;

 // --- 签约/盖章工作流更新 ---
 case'signing_update':
 if (data.workflow_id && data.updates) {
 store.updateSigningWorkflow(data.workflow_id, data.updates);
 }
 break;

 // --- 文档就绪 → 工作台推送动作 + 切换签约 ---
 case'document_ready':
 if (data.suggest_signing) {
 openRightPanel('document');
 store.setDocumentOverlay('signing');
 toast.success('文档已就绪，可发起签约/盖章流程');
 }
 // 同时在工作台推送相关动作
 store.addWorkspaceAction({
 id: `action-doc-${uuidv4()}`,
 label:'查看文档',
 description: data.title ||'文档已生成',
 icon:'document',
 variant:'secondary',
 action:'open_document',
 });
 if (data.suggest_signing) {
 store.addWorkspaceAction({
 id: `action-sign-${uuidv4()}`,
 label:'发起签约/盖章',
 description:'文档已就绪，可启动签约流程',
 icon:'stamp',
 variant:'success',
 action:'initiate_signing',
 });
 }
 if (data.suggest_lawyer) {
 store.addWorkspaceAction({
 id: `action-lawyer-${uuidv4()}`,
 label:'转交律师审核',
 description:'建议由律师审阅后再签约',
 icon:'approve',
 variant:'warning',
 action:'forward_lawyer',
 });
 }
 break;

 // --- 最终完成 (替代旧的 agent_response) ---
 case'done':
 case'agent_response': {
 setIsProcessing(false);
 setThinkingStatus(null);

 // A2UI 响应已通过 a2ui_message 事件插入对话流，不需要重复添加
 if (data.a2ui) {
 loadConversationsRef.current();
 break;
 }

 // 在 finalizeStream 之前获取原始响应内容
 const responseContent = data.content || store.streamingContent ||'';

 // 检测是否为法律文书生成（合同起草、法律意见书等）
 const isDocGen = isDocumentGeneration(responseContent);

 // 法律文书：清理 Agent 系统噪音（"智能体团队"、"任务执行完成"、"文书起草Agent" 等）
 const displayContent = isDocGen ? cleanCanvasContent(responseContent) : responseContent;

 // V2：把当前轮次的 thinkingSteps 快照下来，绑定到这条 AI 消息
 const currentThinkingSteps = [...(store.thinkingSteps || [])];

 if (store.streamingMessageId) {
 const streamAgent = store.streamingAgent || data.agent ||'';
 store.finalizeStream();

 const lastUserContent = [...messages].reverse().find(m => m.type ==='user')?.content ||'';
 const aiMessage: Message = {
 id: uuidv4(), type:'ai', content: displayContent,
 timestamp: new Date(), agent: streamAgent,
 memory_id: data.memory_id,
 sources: data.sources,
 suggestions: generateFollowUpSuggestions(displayContent, lastUserContent),
 thinkingSteps: currentThinkingSteps.length > 0 ? currentThinkingSteps : undefined,
 };
 setMessages(prev => [...prev, aiMessage]);
 } else if (displayContent) {
 const lastUserContent = [...messages].reverse().find(m => m.type ==='user')?.content ||'';
 const aiMessage: Message = {
 id: uuidv4(), type:'ai', content: displayContent,
 timestamp: new Date(), agent: data.agent,
 memory_id: data.memory_id,
 sources: data.sources,
 suggestions: generateFollowUpSuggestions(displayContent, lastUserContent),
 thinkingSteps: currentThinkingSteps.length > 0 ? currentThinkingSteps : undefined,
 };
 setMessages(prev => [...prev, aiMessage]);
 }
 // 清空全局 thinkingSteps，为下一轮准备
 store.clearThinkingSteps?.();
 loadConversationsRef.current();

 // === 法律文书自动推送到文档面板（始终更新，新文书覆盖旧文档） ===
 if (isDocGen) {
 const docContent = cleanCanvasContent(responseContent);
 const titleMatch = docContent.match(/^#\s*(.+)$/m);
 const inferredTitle = titleMatch
 ? titleMatch[1].trim()
 : (docContent.match(/^(.+?(?:合同|协议|意见书|律师函|起诉状|答辩状|仲裁申请书|通知书|声明|备忘录))/m)?.[1]?.trim() ||'法律文书');
 const isContract = /合同|协议|contract|agreement/i.test(responseContent);
 store.setCanvasContent({
 type: isContract ?'contract' :'document',
 title: cleanCanvasTitle(inferredTitle),
 content: docContent,
 suggestions: [],
 });
 setTimeout(() => openRightPanel('document'), 600);
 }

 // V2 修复：生成完成后自动保存工作台快照到当前对话缓存
 // 这样切换到其他对话再切回来时，工作台还在
 if (conversationId) {
 setTimeout(() => store.saveWorkspaceToCache(conversationId), 200);
 }
 break;
 }

 // --- 引导式问答 ---
 case'clarification_request':
 setIsProcessing(false);
 const safeQuestions = Array.isArray(data.questions)
 ? data.questions.map((q: any, index: number) => ({
 question: typeof q?.question ==='string' && q.question.trim()
 ? q.question
 : `问题 ${index + 1}`,
 options: Array.isArray(q?.options) ? q.options : [],
 }))
 : [];
 const clarMsg: Message = {
 id: uuidv4(), type:'clarification',
 content: data.message ||'为了更好地帮助您，请补充以下信息：',
 timestamp: new Date(), agent:'需求分析',
 clarification: {
 questions: safeQuestions,
 original_content: data.original_content ||'',
 },
 };
 setMessages(prev => [...prev, clarMsg]);
 clarificationRef.current = { original_content: data.original_content ||'' };
 break;

 // --- 对话修复：主题跳转/矛盾检测 ---
 case'conversation_repair': {
 setIsProcessing(false);
 const repairMsg: Message = {
 id: uuidv4(), type:'clarification',
 content: data.message ||'检测到信息不一致，请确认',
 timestamp: new Date(), agent:'需求分析',
 clarification: {
 questions: [{
 question: data.message ||'',
 options: data.options || [],
 }],
 original_content: data.original_content ||'',
 },
 metadata: { repair_type: data.repair_type },
 };
 setMessages(prev => [...prev, repairMsg]);
 clarificationRef.current = { original_content: data.original_content ||'' };
 break;
 }

 // --- 后端通知对话标题已更新 ---
 case'conversation_title_updated':
 if (data.conversation_id && data.title) {
 store.updateConversationTitle(data.conversation_id, data.title);
 }
 break;

 // --- 消息保存失败警告 ---
 case'save_warning':
 toast.warning?.(data.message ||'消息保存异常') ?? toast.error(data.message ||'消息保存异常');
 break;

 // --- Canvas 保存结果 ---
 case'canvas_saved':
 if (data.status ==='ok') {
 setCanvasSaved(true);
 } else {
 toast.error('Canvas 内容保存失败');
 }
 break;

 // --- 错误 ---
 case'error': {
 setIsProcessing(false);
 setThinkingStatus(null);
 store.finalizeStream();
 const rawError = data.content || data.message ||'发生错误';
 // 将技术性错误转为友好提示
 let friendlyMsg = rawError;
 if (rawError.includes('must not be empty')) {
 friendlyMsg ='AI 处理时遇到问题，请重新发送您的消息。';
 } else if (rawError.includes('API返回 4')) {
 friendlyMsg ='AI 服务暂时不可用，请稍后重试。';
 } else if (rawError.includes('超时') || rawError.includes('timeout')) {
 friendlyMsg ='处理超时，请简化问题后重试。';
 } else if (rawError.includes('Canvas 优化失败')) {
 friendlyMsg ='Canvas 内容优化失败，请稍后重试。';
 }
 // 在消息列表中显示可操作的错误提示
 setMessages(prev => [...prev, {
 id: uuidv4(),
 type:'system' as const,
 content: friendlyMsg,
 timestamp: new Date(),
 metadata: { isError: true, originalError: rawError },
 }]);
 break;
 }
 }
 }, [armProcessingTimeout, isMobile, store]);

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
 type:'system' as const,
 content:'与服务器的连接已断开，多次重连失败。请检查网络或刷新页面重试。',
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
 wsRef.current.close(1000,'component cleanup');
 }
 wsRef.current = null;
 };
 }, [conversationId]); // 只在 conversationId 变化时重建连接

 // ========== 发送消息超时保护 ==========
 useEffect(() => {
 if (isProcessing) {
 armProcessingTimeout();
 } else {
 clearProcessingTimeout();
 }
 return () => {
 clearProcessingTimeout();
 };
 }, [armProcessingTimeout, clearProcessingTimeout, isProcessing]);

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
 id: uuidv4(), type:'user', content: messageContent, timestamp: new Date(),
 attachment: attachedFile ? {
 type: attachedFile.type.includes('image') ?'image' :'file',
 name: attachedFile.name, size: `${(attachedFile.size / 1024).toFixed(1)} KB`,
 } : undefined,
 };

 setMessages(prev => [...prev, userMessage]);
 setInput('');
 setPendingFile(null);
 setActiveActionId(null); // 发送后取消快捷操作高亮
 setActionModeOverride(null);
 setIsProcessing(true);
 armProcessingTimeout();
 setUserScrolledUp(false); // 发送消息时重置滚动状态，自动跟随新内容
 // V2 修复：只清思考过程/流式状态，保留 Canvas 文档和工作台内容
 // 这样生成完成后工作台不会被下一轮请求清空
 store.resetTransientState();

 // === 文件上传：先上传文件获取文档 ID 和提取文本，再通过 WebSocket 发送 ===
 let sendContent = messageContent;
 let uploadedDocId: string | undefined;
 let extractedText: string | undefined;

 if (attachedFile) {
 try {
 // 1. 上传文件到后端文档系统
 const { documentsApi } = await import('@/lib/api');
 const uploadResult = await documentsApi.upload(attachedFile, {
 doc_type: attachedFile.name.endsWith('.docx') || attachedFile.name.endsWith('.doc') ?'contract' :'other',
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
 mode: actionModeOverride ?? quickActionMode, // 快捷技能优先，其次是深度思考开关
 knowledge_base_ids: selectedKbIds.length > 0 ? selectedKbIds : undefined,
 template_id: selectedTemplateId ?? undefined,
 }));
 if (conversationId && !conversations.find(c => c.id === conversationId)) {
 const title = messageContent.slice(0, 30) + (messageContent.length > 30 ?'...' :'');
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
 armProcessingTimeout();
 // V2 修复：澄清响应只清临时状态，保留之前生成的文档
 store.resetTransientState();
 if (wsRef.current?.readyState === WebSocket.OPEN) {
 wsRef.current.send(JSON.stringify({
 type:'clarification_response', content: selectionText,
 original_content: originalContent, selections: selectionText, privacy_mode: mode,
 }));
 }
 };

 // ========== 反馈 ==========

 const handleFeedback = async (message: Message, rating: number) => {
 if (!message.memory_id) return;
 try {
 await chatApi.submitMemoryFeedback(message.memory_id, rating);
 setMessages(prev => prev.map(m => m.id === message.id ? { ...m, feedback: rating >= 4 ?'up' :'down' } : m));
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
 el.style.height ='auto';
 el.style.height = el.scrollHeight +'px';
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
 if (e.key ==='Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); }
 };

 // 动态 placeholder — 根据当前业务快捷动作切换提示文本
 const dynamicPlaceholder = useMemo(() => {
 if (pendingFile) return `描述您对「${pendingFile.name}」的需求...`;
 if (quickActionMode ==='deep_analysis') return'描述您需要深度分析的法律问题...';
 const workflowPlaceholder = getWorkflowPlaceholder(activeActionId);
 if (workflowPlaceholder) return workflowPlaceholder;
 return'发送消息或输入 / 选择技能';
 }, [pendingFile, quickActionMode, activeActionId]);

 // ========== Harness: Canvas 操作已提取到 useCanvasOperations hook ==========
 const {
 canvasSaved, setCanvasSaved,
 handleCanvasContentChange, handleCanvasSaveAsDocument,
 handleCanvasAIOptimize, handleCanvasSuggestionAction,
 handleDocumentAction,
 } = useCanvasOperations(wsRef, conversationId, setIsProcessing, handleSendMessage);

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
 const handleWorkspaceConfirm = useCallback((confirmationId: string, selectedIds: string[], customText?: string) => {
 // 通过 WebSocket 将用户选择发送回后端
 if (wsRef.current?.readyState === WebSocket.OPEN) {
 wsRef.current.send(JSON.stringify({
 type:'workspace_confirmation_response',
 confirmation_id: confirmationId,
 selected_ids: selectedIds,
 custom_text: customText || undefined,
 conversation_id: store.conversationId,
 }));
 }
 }, [store.conversationId]);

 // ========== 工作台动作回调 ==========

 // WORKSPACE_TO_WORKFLOW_ACTION 已提取到 @/components/chat/a2uiActionMap.ts

 const handleWorkspaceAction = useCallback((actionId: string, payload?: any) => {
 if (actionId.startsWith('ws-')) {
 if (actionId ==='ws-messages') {
 window.location.href ='/messages';
 return;
 }
 if (actionId ==='ws-voice-chat') {
 toast.info('语音对话功能正在开发中，敬请期待', {
 icon: <icons.Mic className="h-4 w-4" />,
 });
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
 toast(workflowBridge.hint, {
 icon: <icons.Lightbulb className="h-4 w-4" />,
 duration: 4000,
 });
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
 type:'workspace_action',
 action_id: actionId,
 payload,
 conversation_id: store.conversationId,
 }));
 }
 switch (actionId) {
 case'open_document':
 openRightPanel('document');
 break;
 case'forward_lawyer':
 handleForwardToLawyer();
 break;
 case'initiate_signing':
 handleInitiateSigning();
 break;
 }
 }, [store.conversationId, handleForwardToLawyer, handleInitiateSigning]);

 // ========== 隐私提示 ==========

 const getPrivacyHint = () => {
 switch (mode) {
 case PrivacyMode.LOCAL: return { text:'绝密模式：数据仅在本地处理', icon: icons.Lock, color:'text-primary' };
 case PrivacyMode.HYBRID: return { text:'安全混合：敏感数据已自动脱敏', icon: icons.ShieldCheck, color:'text-success' };
 case PrivacyMode.CLOUD: return { text:'云端增强：正在使用联网模型', icon: icons.Cloud, color:'text-primary' };
 }
 };
 const privacyHint = getPrivacyHint();
 const PrivacyIcon = privacyHint.icon;

 const formatConvDate = (dateStr: string | null) => {
 if (!dateStr) return'';
 const d = new Date(dateStr);
 const diff = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
 if (diff === 0) return d.toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' });
 if (diff === 1) return'昨天';
 if (diff < 7) return `${diff}天前`;
 return d.toLocaleDateString([], { month:'short', day:'numeric' });
 };

 // ========== 渲染消息 ==========

 // ========== A2UI 事件处理（千问购物式：卡片操作 → 对话消息回传） ==========

 // A2UI_ACTION_TO_MESSAGE 已提取到 @/components/chat/a2uiActionMap.ts（通过顶部 import 引入）

 const handleA2UIEvent = useCallback((event: A2UIEvent) => {
 // 特殊处理：快捷意图按钮 → 直接作为用户消息发送
 if (event.actionId ==='quick_intent' && event.payload?.query) {
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
 type:'a2ui_event',
 action_id: event.actionId,
 component_id: event.componentId,
 payload: event.payload || {},
 form_data: event.formData || {},
 }));
 } else {
 // 降级：作为普通消息发送
 const fallbackContent = `[A2UI操作] ${event.actionId}${event.formData ?' | 表单数据:' + JSON.stringify(event.formData) :''}`;
 handleSendMessage(fallbackContent);
 }
 }, [handleSendMessage, A2UI_ACTION_TO_MESSAGE]);

 // 找到最后一个 A2UI 类型消息的 ID（用于移动端历史折叠判断）
 const lastA2UIMessageId = useMemo(() => {
 for (let i = messages.length - 1; i >= 0; i--) {
 if (messages[i].type ==='a2ui' && messages[i].a2ui) {
 return messages[i].id;
 }
 }
 return null;
 }, [messages]);

 const renderMessage = (message: Message) => {
 if (message.content ==='__WELCOME__') {
 return <WelcomeScreen key={message.id} />;
 }

 // A2UI 消息 — 结构化 UI 组件
 if (message.type ==='a2ui' && message.a2ui) {
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
 <div className={cn('', isMobile ?'w-full' :'max-w-[95%]')}>
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
 {message.timestamp.toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' })}
 </span>
 </div>
 </motion.div>
 );
 }

 if (message.type ==='clarification') {
 return (
 <ClarificationBubble
 key={message.id}
 message={message.content}
 questions={message.clarification?.questions ?? []}
 originalContent={message.clarification?.original_content ??''}
 onSubmit={handleClarificationResponse}
 disabled={isProcessing}
 />
 );
 }

 // 系统消息
 if (message.type ==='system') {
 return (
 <SystemMessage
 key={message.id}
 content={message.content}
 isError={message.metadata?.isError}
 actionable={message.metadata?.actionable}
 onRetry={message.metadata?.isError ? () => {
 const lastUserMsg = [...messages].reverse().find(m => m.type ==='user');
 if (lastUserMsg) handleSendMessage(lastUserMsg.content);
 } : undefined}
 onSwitchModel={() => {
 toast('请点击页面右上角的模型选择器切换其他大模型');
 }}
 />
 );
 }

 const isUser = message.type ==='user';
 const isEditing = editingMessageId === message.id;
 const knowledgeBaseSources = !isUser
 ? (message.sources || []).filter((source) => source.type ==='knowledge_base')
 : [];
 const regularSources = !isUser
 ? (message.sources || []).filter((source) => source.type !=='knowledge_base')
 : [];

 return (
 <motion.div
 initial={{ opacity: 0, y: 8 }}
 animate={{ opacity: 1, y: 0 }}
 key={message.id}
 className={`group ${isUser ?'flex justify-end' :''}`}
 >
 <div className={`max-w-[85%] ${isUser ?'' :''}`}>
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
 ?'bg-primary/10 border-2 border-primary/40 text-foreground px-4 py-2.5 rounded-br-md'
 :'bg-primary text-primary-foreground px-4 py-2.5 rounded-br-md'
 :'bg-background border border-border/50 text-foreground px-4 py-3 rounded-bl-md shadow-sm'
 }`}>
 {/* 附件 */}
 {message.attachment && (
 <div className={`flex items-center gap-2.5 mb-2.5 p-2 rounded-lg ${
 isUser ? (isEditing ?'bg-primary/5 border border-primary/10' :'bg-primary-foreground/15') :'bg-muted/50 border border-border/50'
 }`}>
 <div className={`p-1.5 rounded ${isUser ? (isEditing ?'bg-primary/10' :'bg-primary-foreground/20') :'bg-background shadow-sm'}`}>
 <icons.FileText className={`w-4 h-4 ${isUser ? (isEditing ?'text-primary' :'text-primary-foreground') :'text-primary'}`} />
 </div>
 <div className="flex flex-col min-w-0">
 <span className="text-xs font-medium truncate">{message.attachment.name}</span>
 {message.attachment.size && (
 <span className={`text-[10px] ${isUser ? (isEditing ?'text-muted-foreground' :'text-primary-foreground/70') :'text-muted-foreground'}`}>{message.attachment.size}</span>
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
 e.target.style.height ='auto';
 e.target.style.height = e.target.scrollHeight +'px';
 }}
 onKeyDown={(e) => {
 if (e.key ==='Enter' && !e.shiftKey) { e.preventDefault(); handleConfirmEditMessage(); }
 if (e.key ==='Escape') handleCancelEditMessage();
 }}
 className="w-full bg-transparent border-none resize-none focus:outline-none text-foreground text-sm leading-relaxed"
 style={{ minHeight:'24px' }}
 />
 <div className="flex items-center gap-2 justify-end">
 <button
 onClick={handleCancelEditMessage}
 className="px-3 py-1 text-xs font-medium text-muted-foreground hover:text-foreground rounded-lg hover:bg-muted transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary/15"
 >
 取消
 </button>
 <button
 onClick={handleConfirmEditMessage}
 disabled={!editingMessageContent.trim() || isProcessing}
 className="px-3 py-1 text-xs font-medium text-primary-foreground bg-primary hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-1 outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-1"
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
 <div className="prose prose-sm max-w-none prose-headings:text-foreground prose-headings:font-medium prose-p:text-foreground prose-p:leading-relaxed prose-strong:text-foreground prose-ul:text-foreground/80 prose-ol:text-foreground/80 prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-[13px] prose-pre:bg-foreground prose-pre:text-background">
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
 const score = typeof source.relevance_score ==='number'
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
 type: source.type ||'knowledge',
 title: source.title || source.source || `引用 ${index + 1}`,
 content_snippet: source.content_snippet ||'',
 source: source.source ||'知识库检索',
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
 {message.timestamp.toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' })}
 </span>
 <button
 onClick={() => handleStartEditMessage(message)}
 disabled={isProcessing}
 className="p-1 rounded-md text-muted-foreground/50 hover:text-primary hover:bg-primary/5 transition-colors disabled:opacity-30 outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
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
 {message.timestamp.toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' })}
 </span>
 {message.memory_id && (
 <div className="flex items-center gap-0.5">
 <button
 onClick={() => handleFeedback(message, 5)}
 disabled={!!message.feedback}
 className={`p-1 rounded-md hover:bg-muted transition-colors ${
 message.feedback ==='up' ?'text-success' :'text-muted-foreground/50 hover:text-success'
 }`}
 title="有帮助"
 >
 <icons.ThumbsUp className="w-3 h-3" />
 </button>
 <button
 onClick={() => handleFeedback(message, 1)}
 disabled={!!message.feedback}
 className={`p-1 rounded-md hover:bg-muted transition-colors ${
 message.feedback ==='down' ?'text-destructive' :'text-muted-foreground/50 hover:text-destructive'
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
 message.id === [...messages].reverse().find(m => m.type ==='ai')?.id && !isProcessing && (
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
 className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-foreground/70 bg-background border border-border/80 rounded-full hover:border-primary/40 hover:text-primary hover:bg-primary/5 transition-[colors,transform] shadow-sm active:scale-95 outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
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
 <div className="relative flex h-full min-h-0 bg-surface-2">
 {/* ========== 左侧对话列表侧边栏 ========== */}
 <AnimatePresence>
 {chatSidebarOpen && (
 <motion.div
 initial={{ width: 0, opacity: 0 }}
 animate={{ width: sidebarWidth, opacity: 1 }}
 exit={{ width: 0, opacity: 0 }}
 transition={{ duration: 0.2, ease:'easeInOut' }}
 className="h-full flex-shrink-0 bg-background flex flex-col overflow-hidden max-md:!w-full max-md:absolute max-md:inset-0 max-md:z-20 max-md:border-r max-md:border-border"
 >
 <div className="h-12 px-3 flex items-center gap-2 border-b border-border/50 shrink-0">
 <div className="flex items-center justify-between flex-1">
 {!batchMode ? (
 <>
 <button onClick={handleNewConversation}
 className="flex items-center gap-2 px-3 py-2 text-sm font-medium bg-primary hover:bg-primary/90 text-primary-foreground rounded-2xl transition-colors flex-1 mr-2 shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-1">
 <icons.Plus className="w-4 h-4" /> 新建对话
 </button>
 <button onClick={handleToggleBatchMode}
 className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary/15" title="批量管理">
 <icons.MoreHorizontal className="w-4 h-4" />
 </button>
 <button onClick={() => setChatSidebarOpen(false)}
 className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary/15" title="收起侧边栏">
 <icons.ChevronLeft className="w-4 h-4" />
 </button>
 </>
 ) : (
 <>
 <span className="text-sm font-medium text-foreground/80 flex-1">
 已选 {selectedConvIds.size} / {conversations.length}
 </span>
 <button onClick={handleToggleBatchMode}
 className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary/15" title="取消">
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
 className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-destructive-foreground bg-destructive hover:bg-destructive/90 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors flex-1 justify-center shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-destructive/30 focus-visible:ring-offset-1">
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
 ?'bg-destructive/5 text-destructive border border-destructive/20'
 : isActive && !batchMode
 ?'bg-primary/5 text-primary border border-primary/10'
 :'text-foreground/80 hover:bg-muted/50 border border-transparent'
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
 <icons.MessageSquare className={`w-4 h-4 flex-shrink-0 ${isActive ?'text-primary' :'text-muted-foreground'}`} />
 )}
 <div className="flex-1 min-w-0">
 {isEditing && !batchMode ? (
 <input ref={editInputRef} value={editingTitle} onChange={(e) => setEditingTitle(e.target.value)}
 onBlur={handleFinishRename} onKeyDown={(e) => { if (e.key ==='Enter') handleFinishRename(); if (e.key ==='Escape') setEditingConvId(null); }}
 onClick={(e) => e.stopPropagation()}
 className="w-full bg-background text-foreground text-sm px-2 py-0.5 rounded border border-primary/30 focus:outline-none focus:border-primary" />
 ) : (
 <>
 <p className={`text-sm truncate font-medium ${
 batchMode && isSelected ?'text-destructive' : isActive && !batchMode ?'text-primary' :'text-foreground'
 }`}>{conv.title ||'未命名对话'}</p>
 <p className="text-[10px] text-muted-foreground mt-0.5">
 {formatConvDate(conv.last_message_at || conv.created_at)}
 {conv.message_count > 0 && ` · ${conv.message_count}条`}
 </p>
 </>
 )}
 </div>
 {!isEditing && !batchMode && (
 <div className={`flex items-center gap-0.5 ${isActive ?'visible' :'invisible group-hover:visible'}`}>
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
 className={`flex flex-col bg-background relative ${isDragging ?'' :'transition-[width] duration-300 ease-in-out'}`}
 style={{ width: rightPanelOpen && !isMobile ? `${100 - rightPanelWidth}%` :'100%', minWidth: 0 }}
 >
 {/* Header — v3 紧凑版 */}
 <div data-chat-local-header className="hidden h-12 shrink-0 items-center gap-2.5 border-b border-border bg-background/80 px-4 backdrop-blur-sm md:flex">
 {!chatSidebarOpen && (
 <button onClick={() => setChatSidebarOpen(true)}
 className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary/15" title="展开对话列表">
 <icons.ChevronRight className="w-4 h-4" />
 </button>
 )}
 <div className="flex items-center gap-2">
 <span className="font-medium text-sm text-foreground">AI 法务助手</span>
 <span className={`flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full font-medium border ${
 wsConnected
 ?'text-success bg-success/10 border-success/20'
 :'text-muted-foreground bg-muted border-border'
 }`}>
 <div className={`w-1.5 h-1.5 rounded-full ${wsConnected ?'bg-success' :'bg-muted-foreground'}`} />
 {wsConnected ?'在线' :'连接中'}
 </span>
 </div>
 <div className="flex-1" />
 {/* 智能工作台面板切换 */}
 {!isMobile && (
 <button
 onClick={toggleRightPanel}
 className={`p-1.5 rounded-lg transition-colors ${
 rightPanelOpen
 ?'text-primary bg-primary/5 hover:bg-primary/10'
 :'text-muted-foreground hover:text-foreground hover:bg-muted'
 }`}
 title={rightPanelOpen ?'收起智能工作台' :'展开智能工作台'}
 >
 {rightPanelOpen ? <icons.ChevronRight className="w-4 h-4" /> : <icons.LayoutDashboard className="w-4 h-4" />}
 </button>
 )}
 </div>

 {/* Messages — 支持拖拽上传，移动端额外底部内边距防止 BottomActionBar 遮挡 */}
 <div
 ref={messagesContainerRef}
 className={`relative flex-1 overflow-y-auto scroll-smooth space-y-6 px-4 pt-6 md:p-8 ${isMobile ?'pb-[calc(10rem+env(safe-area-inset-bottom))]' :'pb-8'}`}
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
 messagesEndRef.current?.scrollIntoView({ behavior:'smooth' });
 }}
 className="absolute bottom-20 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1.5 px-3 py-1.5 bg-primary text-primary-foreground text-xs font-medium rounded-full shadow-lg hover:bg-primary/90 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-1"
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
 className="shrink-0 flex flex-col border-t border-border/60 bg-surface-1/95 p-3 shadow-card backdrop-blur-xl"
 style={isMobile ? { paddingBottom:'calc(0.75rem + env(safe-area-inset-bottom))', ...(inputAreaHeight ? { height: inputAreaHeight } : {}) } : (inputAreaHeight ? { height: inputAreaHeight } : undefined)}
 >
 <div className="flex-1 flex flex-col min-h-0">
 <AnimatePresence>
 {pendingFile && (
 <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height:'auto' }} exit={{ opacity: 0, height: 0 }} className="mb-2">
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
 <InputOrchestrationBar
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
 selectedKbIds={selectedKbIds}
 selectedTemplateId={selectedTemplateId}
 onKnowledgeSelectionChange={handleSelectedKbIdsChange}
 onTemplateSelectionChange={handleSelectedTemplateChange}
 />

 {/* 输入框容器 — 一体式设计 */}
 <div className={`relative flex bg-muted/50 rounded-2xl border border-border focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-primary/10 transition-colors ${inputAreaHeight ?'flex-1 min-h-0' :''}`}>
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
 if (e.target) e.target.value ='';
 }}
 />
 <button onClick={() => fileInputRef.current?.click()} disabled={isProcessing}
 className="p-2.5 text-muted-foreground hover:text-primary transition-colors disabled:opacity-50 flex-shrink-0 self-end outline-none focus-visible:ring-2 focus-visible:ring-primary/20 rounded-lg"
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
 style={{ minHeight:'56px', maxHeight: inputAreaHeight ?'none' :'300px', height: inputAreaHeight ?'100%' : undefined }}
 disabled={isProcessing}
 rows={2}
 />

 {/* 右侧功能按钮组：深度思考 + 发送 */}
 <div className="flex items-center gap-0.5 flex-shrink-0 self-end">
 {/* 深度思考开关 — 输入框内右侧 */}
 <DeepModeToggle
 isActive={quickActionMode ==='deep_analysis'}
 onToggle={() => setQuickActionMode(prev => prev ==='deep_analysis' ?'chat' :'deep_analysis')}
 disabled={isProcessing}
 />
 {/* 分隔线 */}
 <div className="w-px h-5 bg-border mx-0.5" />
 {/* 发送按钮 */}
 <button
 onClick={() => handleSendMessage()}
 disabled={!input.trim() || isProcessing}
 className={`p-2 m-1 rounded-xl transition-[colors,transform] disabled:opacity-30 flex-shrink-0 ${
 input.trim()
 ?'bg-primary text-primary-foreground hover:bg-primary/90 active:scale-95 shadow-sm'
 :'bg-transparent text-muted-foreground/50'
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
 transition={{ duration: 0.3, ease:'easeInOut' }}
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
 className="fixed inset-0 z-40 bg-foreground/40"
 onClick={() => setShowContextPanel(false)}
 />
 {/* 底部抽屉面板 */}
 <motion.div
 initial={{ y:'100%' }}
 animate={{ y: 0 }}
 exit={{ y:'100%' }}
 transition={{ type:'spring', damping: 30, stiffness: 300 }}
 className="fixed bottom-0 left-0 right-0 z-50 bg-background flex flex-col rounded-t-2xl shadow-2xl"
 style={{ maxHeight:'85vh' }}
 >
 {/* 拖拽指示器 */}
 <div className="flex justify-center pt-3 pb-1">
 <div className="w-10 h-1 bg-muted-foreground/50 rounded-full" />
 </div>
 <div className="px-4 pb-2 flex justify-between items-center border-b border-border/50">
 <h3 className="font-medium text-base text-foreground">智能工作台</h3>
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
 className="fixed inset-0 z-[100] flex items-center justify-center bg-foreground/40 backdrop-blur-sm"
 onClick={() => setDeleteConfirmId(null)}>
 <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
 className="bg-background rounded-2xl shadow-2xl p-6 w-80 mx-4" onClick={(e) => e.stopPropagation()}>
 <div className="flex items-center gap-3 mb-4">
 <div className="p-2 bg-destructive/5 rounded-full"><icons.Trash2 className="w-5 h-5 text-destructive" /></div>
 <h3 className="text-lg font-medium text-foreground">确认删除</h3>
 </div>
 <p className="text-sm text-muted-foreground mb-6">
 确定要删除这个对话吗？删除后将无法恢复。
 </p>
 <div className="flex gap-3 justify-end">
 <button onClick={() => setDeleteConfirmId(null)}
 className="px-4 py-2 text-sm font-medium text-muted-foreground bg-muted rounded-2xl hover:bg-muted transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary/15">
 取消
 </button>
 <button onClick={confirmDeleteConversation}
 className="px-4 py-2 text-sm font-medium text-destructive-foreground bg-destructive rounded-2xl hover:bg-destructive/90 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-destructive/30 focus-visible:ring-offset-1">
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


// ClarificationBubble 已提取到 @/components/chat/ClarificationBubble.tsx（通过顶部 import 引入）
