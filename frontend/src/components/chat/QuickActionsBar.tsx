/**
 * QuickActionsBar — 项目业务快捷操作工具栏
 *
 * 设计目标：
 * - 围绕当前项目已落地的法务能力做输入加速
 * - 统一通过对话填充型动作触发能力，不离开聊天页
 * - 一级展示高频业务动作，溢出收纳到"更多"弹出面板
 * - 始终显示（处理中也保持可见，但置灰禁用对话填充型）
 * - 支持基于用户使用频率的个性化排序
 */

import { useState, useCallback, useRef, useEffect, memo, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { iconSize, radius } from '@/lib/design-tokens';
import { TemplateSelector } from './TemplateSelector';
import {
  getWorkflowPrompt,
  getPersonalizedActions,
  trackActionUsage,
  type QuickActionMode,
  type QuickActionType,
  type WorkflowActionDefinition,
} from '@/components/chat/workflowConfig';

export interface QuickActionFillPayload {
  text: string;
  actionId?: string;
  mode?: QuickActionMode | null;
  /** @deprecated 旧版导航型快捷动作遗留字段，当前聊天入口不再使用 */
  navigateTo?: string;
  /** @deprecated 仅保留给历史调用方做兼容，当前统一使用对话填充型动作 */
  actionType?: QuickActionType | 'navigate';
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

const MAX_VISIBLE_DESKTOP = 5;
const MAX_VISIBLE_MOBILE = 3;

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
  const [templateOpen, setTemplateOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);
  const portalRef = useRef<HTMLDivElement>(null);
  const moreBtnRef = useRef<HTMLButtonElement>(null);
  const templateRef = useRef<HTMLDivElement>(null);
  const templateBtnRef = useRef<HTMLButtonElement>(null);
  const [popupPos, setPopupPos] = useState<{ x: number; y: number } | null>(null);
  const [templatePos, setTemplatePos] = useState<{ x: number; y: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [maxVisible, setMaxVisible] = useState(isMobile ? MAX_VISIBLE_MOBILE : MAX_VISIBLE_DESKTOP);

  const personalizedActions = useMemo(
    () => actions || getPersonalizedActions(MAX_VISIBLE_DESKTOP),
    [actions],
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new ResizeObserver(() => {
      const width = el.clientWidth;
      if (width < 400) setMaxVisible(MAX_VISIBLE_MOBILE);
      else if (width < 600) setMaxVisible(4);
      else if (width < 800) setMaxVisible(MAX_VISIBLE_DESKTOP);
      else setMaxVisible(personalizedActions.length);
    });

    observer.observe(el);
    return () => observer.disconnect();
  }, [personalizedActions.length]);

  const visibleActions = personalizedActions.slice(0, maxVisible);
  const hiddenActions = personalizedActions.slice(maxVisible);

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
    trackActionUsage(action.id);
    const text = getWorkflowPrompt(action.id, {
      hasAttachment: !!attachmentName,
      attachmentName,
    });
    onFillInput({ text, actionId: action.id, mode: action.mode });
    setMoreOpen(false);
  }, [attachmentName, onFillInput]);

  const renderActionButton = (action: QuickAction, compact = false) => {
    const Icon = icons[action.iconKey];
    const isSelected = activeActionId === action.id;
    const isDisabled = isProcessing;

    if (compact) {
      return (
        <button
          key={action.id}
          onClick={() => handleQuickAction(action)}
          disabled={isDisabled}
          className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-foreground/80 hover:bg-muted/50 hover:text-primary transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Icon className="w-4 h-4 text-muted-foreground" />
          <div className="flex-1 text-left">
            <span>{action.label}</span>
          </div>
        </button>
      );
    }

    return (
      <button
        key={action.id}
        onClick={() => handleQuickAction(action)}
        disabled={isDisabled}
        title={action.description}
        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap transition-all active:scale-95 border disabled:opacity-40 disabled:cursor-not-allowed ${
          isSelected
            ? 'text-primary bg-primary/5 border-primary/30 shadow-sm'
            : 'text-foreground/70 bg-background border-border/80 hover:border-primary/40 hover:text-primary hover:bg-primary/5 shadow-sm'
        }`}
      >
        <Icon className="w-3.5 h-3.5" />
        <span>{action.label}</span>
      </button>
    );
  };

  return (
    <div ref={containerRef}>
      <div className="flex items-center gap-1.5 mb-2">
        {visibleActions.map((action) => renderActionButton(action))}

        {hiddenActions.length > 0 && (
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
                    {hiddenActions.map((action) => renderActionButton(action, true))}
                  </motion.div>
                </AnimatePresence>
              </div>,
              document.body
            )}
          </div>
        )}

        {/* 常用模板按钮 */}
        <div className="relative flex-shrink-0" ref={templateRef}>
          <button
            ref={templateBtnRef}
            onClick={() => {
              if (!templateOpen && templateBtnRef.current) {
                const rect = templateBtnRef.current.getBoundingClientRect();
                setTemplatePos({ x: rect.right, y: rect.top });
              }
              setTemplateOpen(!templateOpen);
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap transition-all border ${
              templateOpen
                ? 'text-primary bg-primary/5 border-primary/30 shadow-sm'
                : 'text-foreground/70 bg-background border-border/80 hover:border-primary/40 hover:text-primary hover:bg-primary/5 shadow-sm'
            }`}
          >
            <icons.FileText className="w-3.5 h-3.5" />
            <span>模板</span>
          </button>

          {templateOpen && createPortal(
            <div>
              <AnimatePresence>
                <div
                  style={templatePos ? { position: 'fixed', right: window.innerWidth - templatePos.x, bottom: window.innerHeight - templatePos.y + 8 } : undefined}
                >
                  <TemplateSelector
                    onSelect={(t) => {
                      onSelect({
                        text: `请基于「${t.name}」模板帮我起草一份${t.name}。`,
                        actionId: 'qa-draft',
                        mode: 'document',
                      });
                    }}
                    onClose={() => setTemplateOpen(false)}
                  />
                </div>
              </AnimatePresence>
            </div>,
            document.body
          )}
        </div>
      </div>
    </div>
  );
}
