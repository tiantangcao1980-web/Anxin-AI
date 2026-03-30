/**
 * QuickActionsBar — 项目业务快捷操作工具栏
 *
 * 设计目标：
 * - 围绕当前项目已落地的法务能力做输入加速
 * - 点击后填充输入框提示文本，用户可继续补充后发送
 * - 一级展示高频业务动作，二级收纳扩展能力
 * - 深度思考开关独立，放在输入框内
 */

import { useState, useCallback, useRef, useEffect, memo } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { iconSize, radius } from '@/lib/design-tokens';
import {
  QUICK_WORKFLOW_ACTIONS,
  getWorkflowPrompt,
  type QuickActionMode,
  type WorkflowActionDefinition,
} from '@/components/chat/workflowConfig';

export interface QuickActionFillPayload {
  text: string;
  actionId?: string;
  mode?: QuickActionMode | null;
}

export type QuickAction = WorkflowActionDefinition;

// ========== 深度思考开关（独立组件，由 Chat.tsx 放到输入框内） ==========

interface DeepModeToggleProps {
  isActive: boolean;
  onToggle: () => void;
  disabled?: boolean;
}

/**
 * 深度思考开关按钮 — 放在输入框内部（发送按钮左侧）
 */
export const DeepModeToggle = memo(function DeepModeToggle({
  isActive,
  onToggle,
  disabled = false,
}: DeepModeToggleProps) {
  return (
    <button
      onClick={onToggle}
      disabled={disabled}
      title={isActive ? '关闭深度思考（多智能体协作·深度分析·联网搜索）' : '开启深度思考（多智能体协作·深度分析·联网搜索）'}
      className={`relative flex items-center gap-1 px-2 py-1.5 text-xs font-medium ${radius.button} transition-all duration-200 flex-shrink-0 disabled:opacity-40 ${
        isActive
          ? 'bg-primary/5 text-primary hover:bg-primary/10'
          : 'text-muted-foreground hover:text-foreground hover:bg-muted'
      }`}
    >
      <icons.Brain className={iconSize.sm} />
      {/* 激活指示圆点 */}
      {isActive && (
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-primary ring-2 ring-background"
        />
      )}
    </button>
  );
});

// ========== 快捷操作工具栏 ==========

interface QuickActionsBarProps {
  onFillInput: (payload: QuickActionFillPayload) => void;
  isProcessing: boolean;
  isMobile: boolean;
  activeActionId?: string | null;
  actions?: WorkflowActionDefinition[];
  attachmentName?: string | null;
  onTriggerUpload?: () => void;
}

export function QuickActionsBar({
  onFillInput,
  isProcessing,
  isMobile,
  activeActionId = null,
  actions,
  attachmentName = null,
  onTriggerUpload,
}: QuickActionsBarProps) {
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);
  const portalRef = useRef<HTMLDivElement>(null);
  const moreBtnRef = useRef<HTMLButtonElement>(null);
  const [popupPos, setPopupPos] = useState<{ x: number; y: number } | null>(null);

  const quickActions = actions || QUICK_WORKFLOW_ACTIONS;
  const primaryActions = quickActions.filter((action) => action.quickGroup !== 'secondary');
  const secondaryActions = quickActions.filter((action) => action.quickGroup === 'secondary');

  const visiblePrimary = isMobile ? primaryActions.slice(0, 4) : primaryActions;

  useEffect(() => {
    if (!moreOpen) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        moreRef.current && !moreRef.current.contains(target) &&
        portalRef.current && !portalRef.current.contains(target)
      ) {
        setMoreOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [moreOpen]);

  const handleQuickAction = useCallback((action: QuickAction) => {
    const text = getWorkflowPrompt(action.id, {
      hasAttachment: !!attachmentName,
      attachmentName,
    });
    onFillInput({ text, actionId: action.id, mode: action.mode });
    setMoreOpen(false);
  }, [attachmentName, onFillInput]);

  return (
    <AnimatePresence>
      {!isProcessing && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.2 }}
          className="overflow-hidden"
        >
          {/* 业务快捷入口：图标+文字紧凑横排 */}
          <div className="flex items-center gap-1.5 mb-2">
            {/* 可滚动区域：主操作按钮 */}
            <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-none">
              {visiblePrimary.map((action) => {
                const Icon = icons[action.iconKey];
                const isSelected = activeActionId === action.id;
                return (
                  <button
                    key={action.id}
                    onClick={() => handleQuickAction(action)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap transition-all active:scale-95 flex-shrink-0 border ${
                      isSelected
                        ? 'text-primary bg-primary/5 border-primary/30 shadow-sm'
                        : 'text-foreground/70 bg-background border-border/80 hover:border-primary/40 hover:text-primary hover:bg-primary/5 shadow-sm'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{action.label}</span>
                  </button>
                );
              })}
            </div>

            {/* "更多"按钮 — 弹出面板通过 Portal 渲染到 body 以突破 overflow:hidden */}
            {secondaryActions.length > 0 && (
              <div className="relative flex-shrink-0" ref={moreRef}>
                <button
                  ref={moreBtnRef}
                  onClick={() => {
                    if (!moreOpen && moreBtnRef.current) {
                      const rect = moreBtnRef.current.getBoundingClientRect();
                      setPopupPos({ x: rect.right, y: rect.top });
                    }
                    setMoreOpen(!moreOpen);
                  }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap transition-all border ${
                    moreOpen
                      ? 'text-primary bg-primary/5 border-primary/30 shadow-sm'
                      : 'text-foreground/70 bg-background border-border/80 hover:border-primary/40 hover:text-primary hover:bg-primary/5 shadow-sm'
                  }`}
                >
                  <icons.MoreHorizontal className="w-3.5 h-3.5" />
                  <span>更多</span>
                </button>

                {/* Portal 弹出面板 */}
                {moreOpen && createPortal(
                  <div ref={portalRef}>
                    <AnimatePresence>
                      <motion.div
                        initial={{ opacity: 0, y: 8, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 8, scale: 0.95 }}
                        transition={{ duration: 0.15 }}
                        style={popupPos ? { position: 'fixed', right: window.innerWidth - popupPos.x, bottom: window.innerHeight - popupPos.y + 8 } : undefined}
                        className="bg-background border border-border rounded-xl shadow-xl py-1.5 min-w-[160px] z-[9999]"
                      >
                        {secondaryActions.map((action) => {
                          const Icon = icons[action.iconKey];
                          return (
                            <button
                              key={action.id}
                              onClick={() => handleQuickAction(action)}
                              className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-foreground/80 hover:bg-muted/50 hover:text-primary transition-colors"
                            >
                              <Icon className="w-4 h-4 text-muted-foreground" />
                              <span>{action.label}</span>
                            </button>
                          );
                        })}

                        {isMobile && primaryActions.length > 4 && (
                          <>
                            <div className="h-px bg-border my-1" />
                            {primaryActions.slice(4).map((action) => {
                              const Icon = icons[action.iconKey];
                              return (
                                <button
                                  key={action.id}
                                  onClick={() => handleQuickAction(action)}
                                  className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-foreground/80 hover:bg-muted/50 hover:text-primary transition-colors"
                                >
                                  <Icon className="w-4 h-4 text-muted-foreground" />
                                  <span>{action.label}</span>
                                </button>
                              );
                            })}
                          </>
                        )}
                      </motion.div>
                    </AnimatePresence>
                  </div>,
                  document.body
                )}
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
