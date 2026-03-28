/**
 * 右侧面板 v5 — 智能工作台
 *
 * 两个核心视图（统一为"智能工作台"）：
 * 1. 工作台 (smart)  — 多Agent并列协作进度卡片、需求确认交互、动作按钮、律师协作入口
 * 2. 文档面板 (document) — 合并原画布 + 律师批注 + 签约操作
 *
 * 律师协助 & 签约盖章作为文档面板的浮层/侧抽屉自然衔接，
 * 工作台中可邀请律师参与咨询、协作和委托签约。
 * 底层与智能协作模块联动，共享律师匹配和签约能力。
 */

import { memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { cardStyle, heading, buttonStyle, iconSize, chatBubble } from '@/lib/design-tokens';
import { AgentWorkspace } from './AgentWorkspace';
import { CanvasEditor } from './CanvasEditor';
import { LawyerAssistPanel } from './LawyerAssistPanel';
import { SigningWorkflow } from './SigningWorkflow';
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
}

const tabs: { id: RightPanelTab; label: string; icon: React.ElementType }[] = [
  { id: 'smart', label: '智能工作台', icon: icons.LayoutDashboard },
  { id: 'document', label: '文档', icon: icons.FileText },
];

export const RightPanel = memo(function RightPanel(props: RightPanelProps) {
  const { activeTab, onTabChange, isLive } = props;
  const store = useChatStore();
  const { documentOverlay, setDocumentOverlay } = store;

  // 是否有文档内容（用于文档 Tab 上的提示点）
  const hasDocument = !!props.canvasContent;
  // 是否有智能体活动
  const hasActivity = props.agentResults.length > 0 || !!props.requirementAnalysis || !!props.a2uiData;

  return (
    <div className="h-full flex flex-col bg-muted/30">
      {/* Tab 导航栏 */}
      <div className="flex items-center px-3 py-2 bg-background border-b border-border flex-shrink-0">
        <div className="flex items-center gap-1 flex-1 bg-muted rounded-xl p-0.5">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            const hasDot = (tab.id === 'document' && hasDocument) || (tab.id === 'smart' && hasActivity);
            
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`relative flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg transition-all ${
                  isActive
                    ? 'bg-background text-primary shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Icon className={iconSize.sm} />
                <span>{tab.label}</span>
                {hasDot && !isActive && (
                  <span className="absolute top-1 right-2 w-1.5 h-1.5 bg-primary rounded-full" />
                )}
              </button>
            );
          })}
        </div>

        {/* LIVE 指示灯 */}
        {isLive && (
          <div className="flex items-center gap-1.5 ml-2 flex-shrink-0">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 dark:bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500 dark:bg-emerald-400" />
            </span>
            <span className={`${heading.micro} font-bold text-emerald-600 uppercase tracking-wider`}>LIVE</span>
          </div>
        )}
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-hidden relative">
        <AnimatePresence mode="wait">
          {/* ========== 智能面板 ========== */}
          {activeTab === 'smart' && (
            <motion.div
              key="smart"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              transition={{ duration: 0.15 }}
              className="h-full"
            >
              <AgentWorkspace
                agentResults={props.agentResults}
                thinkingSteps={props.thinkingSteps}
                requirementAnalysis={props.requirementAnalysis}
                a2uiData={props.a2uiData}
                isProcessing={props.isProcessing}
                onWorkspaceConfirm={props.onWorkspaceConfirm}
                onWorkspaceAction={props.onWorkspaceAction}
              />
            </motion.div>
          )}

          {/* ========== 文档面板 ========== */}
          {activeTab === 'document' && (
            <motion.div
              key="document"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              transition={{ duration: 0.15 }}
              className="h-full relative"
            >
              <CanvasEditor
                canvas={props.canvasContent}
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
                    <LawyerAssistPanel />
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
                    <SigningWorkflow />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
});
