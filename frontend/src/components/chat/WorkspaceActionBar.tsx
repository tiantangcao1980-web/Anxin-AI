/**
 * 工作台动作按钮区 — Agent 推送的快捷操作
 * 
 * 支持多种样式变体：primary / secondary / warning / success
 * 点击后通过回调通知上层，支持附带数据
 */

import { memo } from'react';
import { motion } from'framer-motion';
import { icons } from'@/lib/icons';
import type { WorkspaceAction } from'@/lib/store';

interface WorkspaceActionBarProps {
 actions: WorkspaceAction[];
 onAction: (actionId: string, payload?: any) => void;
}

const iconMap: Record<string, React.ElementType> = {
 arrow: icons.ArrowRight,
 document: icons.FileText,
 contract: icons.Scale,
 send: icons.Send,
 download: icons.Download,
 preview: icons.Eye,
 refresh: icons.RefreshCw,
 check: icons.CheckCircle,
 warning: icons.AlertTriangle,
 edit: icons.Edit,
 stamp: icons.FileSignature,
 approve: icons.User,
 quick: icons.Zap,
};

const variantStyles: Record<string, string> = {
 primary:'bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm shadow-primary/20',
 secondary:'bg-background text-foreground border border-border hover:bg-muted hover:border-border',
 warning:'bg-warning text-warning-foreground hover:bg-warning/20 shadow-sm shadow-amber-200',
 success:'bg-success text-success-foreground hover:bg-success/20 shadow-sm shadow-emerald-200',
};

export const WorkspaceActionBar = memo(function WorkspaceActionBar({
 actions,
 onAction,
}: WorkspaceActionBarProps) {
 if (actions.length === 0) return null;

 return (
 <div className="bg-background rounded-xl border border-border shadow-sm p-4">
 <div className="flex items-center gap-2 mb-3">
 <icons.Zap className="w-3.5 h-3.5 text-warning" />
 <span className="text-xs font-medium text-muted-foreground">快捷操作</span>
 </div>

 <div className="space-y-2">
 {actions.map((action, index) => {
 const Icon = action.icon ? (iconMap[action.icon] || icons.ArrowRight) : icons.ArrowRight;
 const style = variantStyles[action.variant] || variantStyles.secondary;

 return (
 <motion.button
 key={action.id}
 initial={{ opacity: 0, x: -10 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ delay: index * 0.05 }}
 onClick={() => onAction(action.action, action.payload)}
 disabled={action.disabled}
 whileHover={action.disabled ? {} : { scale: 1.01 }}
 whileTap={action.disabled ? {} : { scale: 0.98 }}
 className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
 action.disabled ?'opacity-50 cursor-not-allowed' :''
 } ${style}`}
 >
 <Icon className="w-4 h-4 flex-shrink-0" />
 <div className="flex-1 text-left">
 <span>{action.label}</span>
 {action.description && (
 <p className={`text-[11px] mt-0.5 ${
 action.variant ==='secondary' ?'text-muted-foreground' :'opacity-70'
 }`}>
 {action.description}
 </p>
 )}
 </div>
 <icons.ArrowRight className="w-3.5 h-3.5 opacity-50 flex-shrink-0" />
 </motion.button>
 );
 })}
 </div>
 </div>
 );
});
