/**
 * 右侧面板 v8.0 — 工作台模式
 *
 * 单模式面板：AgentWorkspace（有 Agent 活动时全高展示，无内容时显示工作台引导）
 * 文档编辑通过 AI 生成响应自动触发 CanvasEditor（由 AgentWorkspace 内部处理）
 *
 * 自动切换由 Chat.tsx WebSocket handler 驱动，无需额外逻辑
 */

import { memo, useCallback, lazy, Suspense } from'react';
import { useNavigate } from'react-router-dom';
import { motion, AnimatePresence } from'framer-motion';
import { icons } from'@/lib/icons';
import { heading, cardStyle } from'@/lib/design-tokens';
import { useChatStore } from'@/lib/store';
import type {
 RightPanelTab,
 AgentResult,
 ThinkingStep,
 RequirementAnalysis,
 CanvasContent,
 AnalysisData,
} from'@/lib/store';

interface RightPanelProps {
 activeTab: RightPanelTab;
 onTabChange: (tab: RightPanelTab) => void;
 isLive: boolean;

 agentResults: AgentResult[];
 thinkingSteps: ThinkingStep[];
 a2uiData: any;
 requirementAnalysis: RequirementAnalysis | null;
 isProcessing: boolean;

 canvasContent: CanvasContent | null;
 onCanvasContentChange: (content: string) => void;
 onCanvasTitleChange: (title: string) => void;
 onCanvasModeChange: (mode: CanvasContent['type']) => void;
 onCanvasAIOptimize: () => void;
 onCanvasSuggestionAction: (id: string, action:'accept' |'reject') => void;

 onForwardToLawyer?: () => void;
 onInitiateSigning?: () => void;

 onCanvasSaveAsDocument?: () => void;
 canvasSaved?: boolean;

 analysisData: AnalysisData;

 onWorkspaceConfirm?: (confirmationId: string, selectedIds: string[]) => void;
 onWorkspaceAction?: (actionId: string, payload?: any) => void;

 onDocumentAction?: (action: string, payload?: any) => void;

 onClosePanel?: () => void;

 onNewConversation?: () => void;
}

const AgentWorkspace = lazy(async () => {
 const module = await import('./AgentWorkspace')
 return { default: module.AgentWorkspace }
})

const LawyerAssistPanel = lazy(async () => {
 const module = await import('./LawyerAssistPanel')
 return { default: module.LawyerAssistPanel }
})

const SigningWorkflow = lazy(async () => {
 const module = await import('./SigningWorkflow')
 return { default: module.SigningWorkflow }
})


export const RightPanel = memo(function RightPanel(props: RightPanelProps) {
 const { activeTab, isLive } = props;
 const store = useChatStore();
 const navigate = useNavigate();
 const { documentOverlay } = store;

 const hasDocument = !!props.canvasContent;
 const hasActivity =
 props.agentResults.length > 0 ||
 props.thinkingSteps.length > 0 ||
 !!props.requirementAnalysis ||
 !!props.a2uiData ||
 store.workspaceConfirmations.length > 0 ||
 store.workspaceActions.length > 0 ||
 store.agentTasks.length > 0;

 const handleSwitchToDocument = useCallback(() => {
 if (!hasDocument || !props.canvasContent) return;

 const entryState = {
 entryMode:'chat' as const,
 initialDocument: {
 id: `chat-${Date.now()}`,
 title: props.canvasContent.title ||'未命名文档',
 content: props.canvasContent.content,
 type: props.canvasContent.type,
 metadata: props.canvasContent.metadata,
 },
 };
 window.sessionStorage.setItem('document-workbench-entry', JSON.stringify(entryState));

 navigate('/documents', {
 state: entryState,
 });
 }, [hasDocument, navigate, props.canvasContent]);

 const panelFallback = (
 <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
 正在加载...
 </div>
 )

 return (
 <div
 data-workbench-shell="chat"
 data-workbench-tab={activeTab}
 data-workbench-surface
 className="flex h-full flex-col border-l border-border/60 bg-surface-2"
 >
 {/* 顶栏：标题 + 功能按钮 */}
 <div data-workbench-header className="flex h-12 shrink-0 items-center border-b border-border/60 bg-surface-1/95 px-3 backdrop-blur-xl">
 {/* 左侧：工作台标题 */}
 <div className="flex items-center gap-1.5 flex-shrink-0">
 <icons.Cpu className="w-3.5 h-3.5 text-primary" />
 <span className="text-xs font-semibold text-foreground">工作台</span>
 {props.isProcessing && (
 <span className="relative flex h-1.5 w-1.5">
 <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
 <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-success" />
 </span>
 )}
 </div>

 <div className="flex-1" />

 {/* 右侧：功能按钮 */}
 <div className="flex items-center gap-0.5 flex-shrink-0">
 {props.onNewConversation && (
 <button
 type="button"
 onClick={props.onNewConversation}
 className="p-1.5 text-muted-foreground hover:text-primary hover:bg-primary/5 rounded-lg transition-colors"
 title="新建对话"
 >
 <icons.Plus className="w-4 h-4" />
 </button>
 )}

 {isLive && (
 <div className="flex items-center gap-1.5 flex-shrink-0 px-1">
 <span className="relative flex h-2 w-2">
 <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
 <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
 </span>
 <span className={`${heading.micro} font-medium text-success uppercase tracking-caption`}>LIVE</span>
 </div>
 )}

 </div>
 </div>

 {/* 内容区 — 每个 Tab 独立渲染 */}
 <div data-workbench-content className="relative flex-1 overflow-hidden bg-surface-2">
 {/* ===== 工作台模式 ===== */}
 {activeTab ==='smart' && (
 <div className="h-full overflow-y-auto px-3 py-3">
 <Suspense fallback={panelFallback}>
 <AgentWorkspace
 agentResults={props.agentResults}
 thinkingSteps={props.thinkingSteps}
 requirementAnalysis={props.requirementAnalysis}
 a2uiData={props.a2uiData}
 isProcessing={props.isProcessing}
 onWorkspaceConfirm={props.onWorkspaceConfirm}
 onWorkspaceAction={props.onWorkspaceAction}
 onSwitchToDocument={handleSwitchToDocument}
 hasDocument={hasDocument}
 />
 </Suspense>

 {/* 工作台空状态 — 系统内置功能入口 */}
 {!hasActivity && !props.isProcessing && !store.contractReviewVisible && (
 <div className={`${cardStyle.compact} flex h-full flex-col !px-4 !py-5`}>
 {/* 顶部标题 */}
 <div className="flex items-center gap-2.5 mb-5 px-1">
 <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center shadow-sm">
 <icons.Cpu className="w-5 h-5 text-primary" />
 </div>
 <div>
 <h3 className="text-sm font-semibold text-foreground">智能工作台</h3>
 <p className="text-[11px] text-muted-foreground">选择功能开始，或对话触发自动展示</p>
 </div>
 </div>

 {/* 功能卡片区 — 可交互的 A2UI 触发器 */}
 <div className="space-y-2.5 flex-1 overflow-y-auto">
 {/* 快捷工具 */}
 <div>
 <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-caption mb-2 px-1">快捷工具</p>
 <div className="grid grid-cols-3 gap-2">
 {([
 { icon: icons.Users, label:'找律师', actionId:'ws-find-lawyer', color:'text-info bg-info/10' },
 { icon: icons.FileCheck, label:'合同审查', actionId:'ws-contract-review', color:'text-warning bg-warning/10' },
 { icon: icons.Scale, label:'法规速查', actionId:'ws-regulation', color:'text-success bg-success/10' },
 ] as const).map((item) => {
 const Icon = item.icon;
 return (
 <button
 key={item.actionId}
 onClick={() => props.onWorkspaceAction?.(item.actionId)}
 className="flex flex-col items-center gap-1.5 rounded-xl border border-border/60 bg-surface-1 p-3 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-card active:scale-95"
 >
 <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${item.color}`}>
 <Icon className="w-4.5 h-4.5" />
 </div>
 <span className="text-[11px] font-medium text-foreground">{item.label}</span>
 </button>
 );
 })}
 </div>
 </div>

 {/* 智能服务 — 带描述的交互卡片 */}
 <div>
 <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-caption mb-2 px-1">智能服务</p>
 <div className="space-y-2">
 {([
 {
 icon: icons.Search,
 label:'尽职调查',
 desc:'输入企业名称，自动检索工商、诉讼、风险信息',
 actionId:'ws-due-diligence',
 tag:'AI 驱动',
 },
 {
 icon: icons.ShieldCheck,
 label:'合规检查',
 desc:'选择行业和场景，生成合规检查清单与风险报告',
 actionId:'ws-compliance',
 tag:'多 Agent',
 },
 {
 icon: icons.PenTool,
 label:'文书生成',
 desc:'描述需求，AI 协作起草合同、函件、法律意见书',
 actionId:'ws-doc-generate',
 tag:'协作式',
 },
 ] as const).map((item) => {
 const Icon = item.icon;
 return (
 <button
 key={item.actionId}
 onClick={() => props.onWorkspaceAction?.(item.actionId)}
 className="group flex w-full items-start gap-3 rounded-xl border border-border/60 bg-surface-1 p-3 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-card active:scale-[0.98]"
 >
 <div className="w-9 h-9 rounded-lg bg-primary/5 group-hover:bg-primary/10 flex items-center justify-center flex-shrink-0 transition-colors">
 <Icon className="w-4.5 h-4.5 text-primary/60 group-hover:text-primary transition-colors" />
 </div>
 <div className="flex-1 min-w-0">
 <div className="flex items-center gap-1.5">
 <span className="text-xs font-semibold text-foreground">{item.label}</span>
 <span className="px-1.5 py-0.5 text-[9px] font-medium text-primary bg-primary/5 rounded">{item.tag}</span>
 </div>
 <p className="text-[11px] text-muted-foreground leading-relaxed mt-0.5">{item.desc}</p>
 </div>
 <icons.ChevronRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-primary/50 flex-shrink-0 mt-0.5 transition-colors" />
 </button>
 );
 })}
 </div>
 </div>

 {/* 沟通协作 */}
 <div>
 <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-caption mb-2 px-1">沟通协作</p>
 <div className="grid grid-cols-2 gap-2">
 {([
 { icon: icons.MessageSquare, label:'消息中心', desc:'通知与审批', actionId:'ws-messages' },
 { icon: icons.Mic, label:'语音对话', desc:'AI 语音助手', actionId:'ws-voice-chat' },
 ] as const).map((item) => {
 const Icon = item.icon;
 return (
 <button
 key={item.actionId}
 onClick={() => props.onWorkspaceAction?.(item.actionId)}
 className="group flex items-center gap-2.5 rounded-xl border border-border/60 bg-surface-1 p-3 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-card active:scale-[0.98]"
 >
 <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center flex-shrink-0 group-hover:bg-primary/5 transition-colors">
 <Icon className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
 </div>
 <div className="min-w-0">
 <p className="text-[11px] font-semibold text-foreground">{item.label}</p>
 <p className="text-[10px] text-muted-foreground">{item.desc}</p>
 </div>
 </button>
 );
 })}
 </div>
 </div>
 </div>

 {/* 底部能力标签 */}
 <div className="flex flex-wrap justify-center gap-1.5 mt-4 pt-3 border-t border-border/50">
 {['需求分析','多Agent协作','进度追踪'].map((tag) => (
 <span key={tag} className="rounded-full border border-border bg-surface-2 px-2 py-0.5 text-[10px] text-muted-foreground">
 {tag}
 </span>
 ))}
 </div>
 </div>
 )}
 </div>
 )}

 {/* 律师协助浮层 */}
 <AnimatePresence>
 {documentOverlay ==='lawyer' && (
 <motion.div
 initial={{ x:'100%' }}
 animate={{ x: 0 }}
 exit={{ x:'100%' }}
 transition={{ type:'spring', damping: 25, stiffness: 300 }}
 className="absolute inset-0 bg-background z-20 shadow-xl"
 >
 <Suspense fallback={panelFallback}>
 <LawyerAssistPanel />
 </Suspense>
 </motion.div>
 )}
 </AnimatePresence>

 {/* 签约工作流浮层 */}
 <AnimatePresence>
 {documentOverlay ==='signing' && (
 <motion.div
 initial={{ x:'100%' }}
 animate={{ x: 0 }}
 exit={{ x:'100%' }}
 transition={{ type:'spring', damping: 25, stiffness: 300 }}
 className="absolute inset-0 bg-background z-20 shadow-xl"
 >
 <Suspense fallback={panelFallback}>
 <SigningWorkflow />
 </Suspense>
 </motion.div>
 )}
 </AnimatePresence>

 </div>
 </div>
 );
});
