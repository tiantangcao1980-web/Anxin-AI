/**
 * QuickActionsBar — 快捷操作工具栏 (v5)
 * 
 * 设计理念：
 * - 深度思考开关：独立导出为 DeepModeToggle 组件，由父组件放置到输入框内右侧
 * - 快捷操作按钮：
 *   - 点击后 **填充到输入框** 并聚焦，用户可补充需求后再发送
 *   - 点击后按钮高亮显示，用户发送/清空后自动取消高亮
 *   - 默认只显示一行（桌面 5 个，移动 3 个），多余收起到"更多"
 * - 按钮列表未来可从后端/设置动态加载（预留 actions prop）
 * - 处理中时淡出隐藏
 */

import { useState, useCallback, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { iconSize, buttonStyle, radius } from '@/lib/design-tokens';

/** 功能模式（传给后端 context.mode） */
export type QuickActionMode = 'chat' | 'deep_analysis' | 'contract' | 'document' | 'research';

/** 快捷操作定义 */
export interface QuickAction {
  id: string;
  label: string;
  icon: React.ElementType;
  /** 点击后填充到输入框的提示文本 */
  query: string;
}

/**
 * 默认快捷操作列表
 * 
 * 未来可通过 props.actions 从后端/设置页面动态注入
 */
const DEFAULT_QUICK_ACTIONS: QuickAction[] = [
  { id: 'qa-consult',    label: '法律咨询', icon: icons.MessageCircle, query: '我有一个法律问题想咨询：' },
  { id: 'qa-contract',   label: '合同审查', icon: icons.FileText,      query: '请帮我审查以下合同：' },
  { id: 'qa-draft',      label: '文书起草', icon: icons.PenTool,       query: '请帮我起草一份' },
  { id: 'qa-risk',       label: '风险评估', icon: icons.Shield,        query: '请帮我评估以下风险：' },
  { id: 'qa-dd',         label: '尽职调查', icon: icons.Search,        query: '请帮我调查以下企业的背景：' },
  { id: 'qa-lawyer',     label: '找律师',   icon: icons.Users,         query: '我想找一位擅长' },
  { id: 'qa-regulation', label: '法规查询', icon: icons.BookOpen,      query: '请帮我查询关于' },
  { id: 'qa-case',       label: '案例检索', icon: icons.Briefcase,     query: '请帮我检索与' },
];

// ========== 深度思考开关（独立组件，由 Chat.tsx 放到输入框内） ==========

interface DeepModeToggleProps {
  isActive: boolean;
  onToggle: () => void;
  disabled?: boolean;
}

/**
 * 深度思考开关按钮 — 放在输入框内部（发送按钮左侧）
 * 
 * 紧凑设计：仅图标 + 圆点指示器，hover 显示 tooltip
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
  /** 用户点击快捷操作后：填充文本到输入框（不直接发送），同时传回 actionId 用于高亮 */
  onFillInput: (text: string, actionId?: string) => void;
  isProcessing: boolean;
  isMobile: boolean;
  /** 当前选中的快捷操作 ID（用于高亮显示） */
  activeActionId?: string | null;
  /** 外部传入的动态操作列表（未来从后端/设置加载），不传则使用默认 */
  actions?: QuickAction[];
}

export function QuickActionsBar({
  onFillInput,
  isProcessing,
  isMobile,
  activeActionId = null,
  actions,
}: QuickActionsBarProps) {
  const [expanded, setExpanded] = useState(false);

  const quickActions = actions || DEFAULT_QUICK_ACTIONS;

  const handleQuickAction = useCallback((action: QuickAction) => {
    // 填充到输入框 + 传回 actionId 供父组件高亮
    onFillInput(action.query, action.id);
  }, [onFillInput]);

  // 默认显示数量：桌面 5 个（一行刚好），移动 3 个
  const defaultVisibleCount = isMobile ? 3 : 5;
  const visibleActions = expanded ? quickActions : quickActions.slice(0, defaultVisibleCount);
  const hasMore = quickActions.length > defaultVisibleCount;

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
          {/* 快捷操作按钮 — 点击填充输入框 + 选中高亮 */}
          <div className="flex flex-wrap items-center gap-1.5 mb-2">
            <AnimatePresence mode="popLayout">
              {visibleActions.map((action) => {
                const Icon = action.icon;
                const isSelected = activeActionId === action.id;
                return (
                  <motion.button
                    key={action.id}
                    layout
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ duration: 0.15 }}
                    onClick={() => handleQuickAction(action)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full transition-all active:scale-95 shadow-sm border ${
                      isSelected
                        ? 'bg-primary/5 text-primary border-primary/30 ring-1 ring-primary/20'
                        : 'text-muted-foreground bg-background border-border hover:border-primary/30 hover:text-primary hover:bg-primary/5'
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isSelected ? 'text-primary' : ''}`} />
                    <span>{action.label}</span>
                  </motion.button>
                );
              })}
            </AnimatePresence>
            {hasMore && (
              <button
                onClick={() => setExpanded(!expanded)}
                className={`inline-flex items-center gap-1 px-2.5 py-1.5 ${buttonStyle.sm} text-muted-foreground hover:text-foreground rounded-full hover:bg-muted transition-colors`}
              >
                {expanded ? (
                  <>收起 <icons.ChevronUp className="w-3 h-3" /></>
                ) : (
                  <>更多 <icons.ChevronDown className="w-3 h-3" /></>
                )}
              </button>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
