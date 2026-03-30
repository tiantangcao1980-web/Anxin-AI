/**
 * 右侧面板 v6 — 智能工作台（文档管理增强版）
 *
 * 参考豆包设计：
 * - Agent 工作区 + 文档编辑统一视图
 * - 文档快捷操作工具栏（翻译全文、生成摘要、截图提问等）
 * - 无文档时显示空状态引导 + 新建文档入口
 * - 文档列表：历史文档可快速切换、删除
 * - 律师协助 & 签约浮层
 */

import { memo, useState, useCallback, lazy, Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { cardStyle, heading, buttonStyle, iconSize, chatBubble } from '@/lib/design-tokens';
import { useChatStore } from '@/lib/store';
import type {
  RightPanelTab,
  DocumentOverlay,
  AgentResult,
  ThinkingStep,
  RequirementAnalysis,
  CanvasContent,
  AnalysisData,
} from '@/lib/store';

interface RightPanelProps {
  activeTab: RightPanelTab;
  onTabChange: (tab: RightPanelTab) => void;
  isLive: boolean;

  // 工作台数据
  agentResults: AgentResult[];
  thinkingSteps: ThinkingStep[];
  a2uiData: any;
  requirementAnalysis: RequirementAnalysis | null;
  isProcessing: boolean;

  // 文档面板数据
  canvasContent: CanvasContent | null;
  onCanvasContentChange: (content: string) => void;
  onCanvasTitleChange: (title: string) => void;
  onCanvasModeChange: (mode: CanvasContent['type']) => void;
  onCanvasAIOptimize: () => void;
  onCanvasSuggestionAction: (id: string, action: 'accept' | 'reject') => void;

  // 律师 & 签约
  onForwardToLawyer?: () => void;
  onInitiateSigning?: () => void;

  // Canvas 保存
  onCanvasSaveAsDocument?: () => void;
  canvasSaved?: boolean;

  // 分析数据
  analysisData: AnalysisData;

  // 工作台交互回调
  onWorkspaceConfirm?: (confirmationId: string, selectedIds: string[]) => void;
  onWorkspaceAction?: (actionId: string, payload?: any) => void;

  // 文档快捷操作回调（翻译/摘要/提问等）
  onDocumentAction?: (action: string, payload?: any) => void;

  /** 收起右侧栏（桌面分栏由 Chat 传入；移动端抽屉已有顶栏关闭，无需传入） */
  onClosePanel?: () => void;
}

const AgentWorkspace = lazy(async () => {
  const module = await import('./AgentWorkspace')
  return { default: module.AgentWorkspace }
})

const CanvasEditor = lazy(async () => {
  const module = await import('./CanvasEditor')
  return { default: module.CanvasEditor }
})

const LawyerAssistPanel = lazy(async () => {
  const module = await import('./LawyerAssistPanel')
  return { default: module.LawyerAssistPanel }
})

const SigningWorkflow = lazy(async () => {
  const module = await import('./SigningWorkflow')
  return { default: module.SigningWorkflow }
})

/** 文档快捷操作定义（参考豆包工具栏） */
const DOCUMENT_ACTIONS = [
  { id: 'summarize', label: '生成摘要', icon: icons.Wand2, description: '为当前文档生成结构化摘要' },
  { id: 'translate', label: '翻译全文', icon: icons.Globe, description: '将文档翻译为目标语言' },
  { id: 'optimize', label: 'AI 润色', icon: icons.Sparkles, description: '优化文档措辞和结构' },
  { id: 'risk_check', label: '风险检查', icon: icons.Shield, description: '识别文档中的法律风险点' },
] as const;

export const RightPanel = memo(function RightPanel(props: RightPanelProps) {
  const { activeTab, onTabChange, isLive } = props;
  const store = useChatStore();
  const { documentOverlay, setDocumentOverlay, documentList, addDocumentToList, removeDocumentFromList } = store;

  const [showDocList, setShowDocList] = useState(false);

  const hasDocument = !!props.canvasContent;
  const hasActivity = props.agentResults.length > 0 || !!props.requirementAnalysis || !!props.a2uiData;

  /** 新建空白文档 */
  const handleCreateDocument = useCallback(() => {
    store.setCanvasContent({
      type: 'document',
      title: '未命名文档',
      content: '',
      suggestions: [],
    });
  }, [store]);

  /** 保存当前文档到列表 */
  const handleSaveToList = useCallback(() => {
    if (!props.canvasContent) return;
    const id = `doc-${Date.now()}`;
    addDocumentToList({
      id,
      title: props.canvasContent.title || '未命名文档',
      type: props.canvasContent.type,
      preview: props.canvasContent.content.slice(0, 100),
    });
    props.onCanvasSaveAsDocument?.();
  }, [props.canvasContent, addDocumentToList, props.onCanvasSaveAsDocument]);

  /** 文档快捷操作 */
  const handleDocAction = useCallback((actionId: string) => {
    if (props.onDocumentAction) {
      props.onDocumentAction(actionId, { content: props.canvasContent?.content });
    } else {
      // 默认行为：通过 AI 优化按钮触发
      if (actionId === 'optimize') {
        props.onCanvasAIOptimize();
      }
    }
  }, [props]);

  /** 关闭当前文档 */
  const handleCloseDocument = useCallback(() => {
    // 保存到列表再关闭
    if (props.canvasContent?.content) {
      const id = `doc-${Date.now()}`;
      addDocumentToList({
        id,
        title: props.canvasContent.title || '未命名文档',
        type: props.canvasContent.type,
        preview: props.canvasContent.content.slice(0, 100),
      });
    }
    store.setCanvasContent(null);
  }, [props.canvasContent, store, addDocumentToList]);

  const panelFallback = (
    <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
      正在加载工作台...
    </div>
  )

  return (
    <div className="h-full flex flex-col bg-muted/30">
      {/* 标题栏 */}
      <div className="h-12 flex items-center px-4 bg-background border-b border-border flex-shrink-0">
        <div className="flex items-center gap-2 flex-1">
          <icons.LayoutDashboard className={`${iconSize.sm} text-primary`} />
          <span className="text-sm font-semibold text-foreground">智能工作台</span>
        </div>

        <div className="flex items-center gap-1 flex-shrink-0 min-w-0">
          {/* 文档列表切换 */}
          {documentList.length > 0 && (
            <button
              type="button"
              onClick={() => setShowDocList(!showDocList)}
              className={`relative p-1.5 rounded-lg transition-colors ${
                showDocList ? 'text-primary bg-primary/5' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              }`}
              title="文档列表"
            >
              <icons.FolderOpen className="w-4 h-4" />
              <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-primary text-white text-[8px] font-bold rounded-full flex items-center justify-center">
                {documentList.length}
              </span>
            </button>
          )}

          {/* 新建文档 */}
          <button
            type="button"
            onClick={handleCreateDocument}
            className="p-1.5 text-muted-foreground hover:text-primary hover:bg-primary/5 rounded-lg transition-colors"
            title="新建文档"
          >
            <icons.FilePlus className="w-4 h-4" />
          </button>

          {/* LIVE 指示灯 */}
          {isLive && (
            <div className="flex items-center gap-1.5 flex-shrink-0 px-1">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 dark:bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500 dark:bg-emerald-400" />
              </span>
              <span className={`${heading.micro} font-bold text-emerald-600 uppercase tracking-wider`}>LIVE</span>
            </div>
          )}

          {props.onClosePanel && (
            <button
              type="button"
              onClick={props.onClosePanel}
              className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors flex-shrink-0"
              title="收起面板"
            >
              <icons.X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-hidden relative">
        {/* 文档列表弹出面板 */}
        <AnimatePresence>
          {showDocList && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute top-0 left-0 right-0 z-30 bg-background border-b border-border shadow-lg max-h-[50%] overflow-y-auto"
            >
              <div className="p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-foreground">历史文档</span>
                  <button onClick={() => setShowDocList(false)} className="p-1 text-muted-foreground hover:text-foreground rounded">
                    <icons.X className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="space-y-1">
                  {documentList.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-muted/50 cursor-pointer group transition-colors"
                    >
                      <div className="p-1.5 rounded bg-primary/5">
                        <icons.FileText className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-foreground truncate">{doc.title}</p>
                        <p className="text-[10px] text-muted-foreground truncate">{doc.preview || '空文档'}</p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeDocumentFromList(doc.id);
                        }}
                        className="p-1 text-muted-foreground/50 hover:text-destructive rounded opacity-0 group-hover:opacity-100 transition-opacity"
                        title="删除"
                      >
                        <icons.Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="h-full overflow-y-auto">
          {/* 统一空状态：无 Agent 活动且无文档时 */}
          {!hasActivity && !hasDocument && !props.isProcessing ? (
            <div className="h-full flex flex-col items-center justify-center px-8 py-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-5 shadow-sm">
                <icons.LayoutDashboard className="w-8 h-8 text-primary" />
              </div>
              <h3 className="text-sm font-semibold text-foreground mb-1.5">智能工作台</h3>
              <p className="text-xs text-muted-foreground mb-6 max-w-[260px] leading-relaxed">
                发送消息后，AI 将实时展示需求分析、多 Agent 协作进度和处理结果；您也可以直接新建文档进行编辑。
              </p>

              {/* 文档快速操作 */}
              <div className="flex flex-col gap-2 w-full max-w-[200px] mb-6">
                <button
                  onClick={handleCreateDocument}
                  className="flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-white text-xs font-medium rounded-xl hover:bg-primary/90 transition-colors shadow-sm"
                >
                  <icons.Plus className="w-3.5 h-3.5" />
                  新建空白文档
                </button>
                <button
                  onClick={() => {
                    store.setCanvasContent({
                      type: 'contract',
                      title: '合同模板',
                      content: '# 合同标题\n\n**甲方：**\n**乙方：**\n\n## 第一条 合同目的\n\n## 第二条 权利义务\n\n## 第三条 违约责任\n\n## 第四条 争议解决\n\n## 第五条 其他条款\n\n签署日期：____年__月__日',
                      suggestions: [],
                    });
                  }}
                  className="flex items-center justify-center gap-2 px-4 py-2.5 bg-background text-foreground/80 text-xs font-medium rounded-xl hover:bg-muted border border-border transition-colors"
                >
                  <icons.FileCheck className="w-3.5 h-3.5" />
                  使用合同模板
                </button>
              </div>

              {/* 功能标签：融合 Agent + 文档能力 */}
              <div className="flex flex-wrap justify-center gap-1.5">
                {['需求分析', '多Agent协作', '进度追踪', '文书起草', '合同审查', 'AI 润色', '风险检查'].map((tag) => (
                  <span key={tag} className="px-2.5 py-1 bg-background text-[10px] text-muted-foreground border border-border rounded-full shadow-xs">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <>
              {/* Agent 工作区 */}
              <Suspense fallback={panelFallback}>
                <AgentWorkspace
                  agentResults={props.agentResults}
                  thinkingSteps={props.thinkingSteps}
                  requirementAnalysis={props.requirementAnalysis}
                  a2uiData={props.a2uiData}
                  isProcessing={props.isProcessing}
                  onWorkspaceConfirm={props.onWorkspaceConfirm}
                  onWorkspaceAction={props.onWorkspaceAction}
                />
              </Suspense>

              {/* 文档编辑区 */}
              {hasDocument && (
                <div className="border-t border-border">
                  {/* 文档快捷操作工具栏 */}
                  <div className="flex items-center gap-1 px-3 py-2 bg-background/80 border-b border-border/50 overflow-x-auto scrollbar-none">
                    {DOCUMENT_ACTIONS.map((action) => {
                      const Icon = action.icon;
                      return (
                        <button
                          key={action.id}
                          onClick={() => handleDocAction(action.id)}
                          disabled={props.isProcessing}
                          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:text-primary hover:bg-primary/5 rounded-lg transition-colors whitespace-nowrap disabled:opacity-40 flex-shrink-0"
                          title={action.description}
                        >
                          <Icon className="w-3.5 h-3.5" />
                          <span>{action.label}</span>
                        </button>
                      );
                    })}

                    <div className="flex-1" />

                    <button
                      onClick={handleSaveToList}
                      className="flex items-center gap-1 px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 rounded-lg transition-colors flex-shrink-0"
                      title="保存到文档库"
                    >
                      <icons.Save className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={handleCloseDocument}
                      className="flex items-center gap-1 px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors flex-shrink-0"
                      title="关闭文档"
                    >
                      <icons.X className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* 编辑器 */}
                  <Suspense fallback={panelFallback}>
                    <CanvasEditor
                      canvas={props.canvasContent!}
                      onContentChange={props.onCanvasContentChange}
                      onTitleChange={props.onCanvasTitleChange}
                      onModeChange={props.onCanvasModeChange}
                      onAIOptimize={props.onCanvasAIOptimize}
                      onSuggestionAction={props.onCanvasSuggestionAction}
                      onForwardToLawyer={props.onForwardToLawyer}
                      onInitiateSigning={props.onInitiateSigning}
                      onSaveAsDocument={props.onCanvasSaveAsDocument}
                      isSaved={props.canvasSaved}
                      isOptimizing={props.isProcessing}
                    />
                  </Suspense>
                </div>
              )}
            </>
          )}
        </div>

        {/* 律师协助浮层 */}
        <AnimatePresence>
          {documentOverlay === 'lawyer' && (
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
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
          {documentOverlay === 'signing' && (
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
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
