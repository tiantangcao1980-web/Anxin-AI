/**
 * CaseProgressCard — 案件进度时间线卡片
 *
 * 在对话流中展示案件处理进度：
 * - 垂直时间线布局
 * - 当前阶段高亮 + 脉冲动画
 * - 已完成/进行中/待处理 三种状态
 * - 预计完成时间
 * - 操作按钮（查看详情、催办等）
 */

import { memo } from'react';
import { motion } from'framer-motion';
import { icons } from'@/lib/icons';
import type { A2UIEventHandler } from'../types';
import { cn } from'@/lib/utils';

export interface CaseProgressStep {
 id: string;
 label: string;
 description?: string;
 status:'completed' |'active' |'pending' |'error';
 timestamp?: string;
 agent?: string;
}

export interface CaseProgressCardData {
 caseId: string;
 title: string;
 caseType?: string;
 currentPhase: string;
 progress: number; // 0-100
 steps: CaseProgressStep[];
 estimatedCompletion?: string;
 actions?: {
 label: string;
 actionId: string;
 variant?:'primary' |'secondary' |'outline';
 payload?: Record<string, any>;
 }[];
}

interface CaseProgressCardProps {
 component: {
 id: string;
 type:'case-progress';
 data: CaseProgressCardData;
 };
 onEvent: A2UIEventHandler;
}

const STATUS_CONFIG = {
 completed: {
 icon: icons.CheckCircle2,
 color:'text-success',
 bgColor:'bg-success/10',
 borderColor:'border-success/20',
 lineColor:'bg-success',
 },
 active: {
 icon: icons.Clock,
 color:'text-primary',
 bgColor:'bg-primary/10',
 borderColor:'border-primary',
 lineColor:'bg-primary',
 },
 pending: {
 icon: icons.Circle,
 color:'text-muted-foreground',
 bgColor:'bg-muted',
 borderColor:'border-border',
 lineColor:'bg-muted',
 },
 error: {
 icon: icons.AlertCircle,
 color:'text-destructive',
 bgColor:'bg-destructive/10',
 borderColor:'border-destructive/20',
 lineColor:'bg-destructive',
 },
};

export const CaseProgressCard = memo(function CaseProgressCard({
 component,
 onEvent,
}: CaseProgressCardProps) {
 const { data } = component;
 const { title, caseType, currentPhase, progress, steps, estimatedCompletion, actions } = data;

 const handleAction = (actionId: string, payload?: Record<string, any>) => {
 onEvent({
 type:'action',
 actionId,
 componentId: component.id,
 payload: { ...payload, caseId: data.caseId },
 });
 };

 return (
 <div className="bg-background rounded-2xl border border-border shadow-sm overflow-hidden">
 {/* 头部 */}
 <div className="px-4 pt-4 pb-3">
 <div className="flex items-start justify-between">
 <div>
 <h4 className="text-sm font-semibold text-foreground">{title}</h4>
 {caseType && (
 <span className="text-[10px] text-muted-foreground mt-0.5">{caseType}</span>
 )}
 </div>
 <span className="text-[10px] font-medium text-primary bg-primary/10 px-2 py-0.5 rounded-full border border-primary/20">
 {currentPhase}
 </span>
 </div>

 {/* 进度条 */}
 <div className="mt-3">
 <div className="flex items-center justify-between mb-1">
 <span className="text-[10px] text-muted-foreground">总进度</span>
 <span className="text-[10px] font-semibold text-primary">{progress}%</span>
 </div>
 <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
 <motion.div
 className="h-full bg-primary rounded-full"
 initial={{ width: 0 }}
 animate={{ width: `${progress}%` }}
 transition={{ duration: 0.8, ease:'easeOut' }}
 />
 </div>
 </div>
 </div>

 {/* 时间线 */}
 <div className="px-4 pb-3">
 <div className="space-y-0">
 {steps.map((step, idx) => {
 const config = STATUS_CONFIG[step.status];
 const Icon = config.icon;
 const isLast = idx === steps.length - 1;

 return (
 <div key={step.id} className="flex gap-3">
 {/* 时间线图标和连接线 */}
 <div className="flex flex-col items-center flex-shrink-0">
 <div
 className={cn(
'w-6 h-6 rounded-full flex items-center justify-center border',
 config.bgColor,
 config.borderColor,
 )}
 >
 {step.status ==='active' ? (
 <div className="relative">
 <Icon className={cn('w-3.5 h-3.5', config.color)} />
 <span className="absolute -top-0.5 -right-0.5 flex h-2 w-2">
 <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
 <span className="relative inline-flex rounded-full h-2 w-2 bg-primary" />
 </span>
 </div>
 ) : (
 <Icon className={cn('w-3.5 h-3.5', config.color)} />
 )}
 </div>
 {!isLast && (
 <div className={cn('w-0.5 flex-1 min-h-[20px]', config.lineColor)} />
 )}
 </div>

 {/* 内容 */}
 <div className="pb-3 flex-1 min-w-0">
 <div className="flex items-center gap-2">
 <span className={cn(
'text-xs font-medium',
 step.status ==='active' ?'text-primary' :
 step.status ==='completed' ?'text-foreground' :
'text-muted-foreground',
 )}>
 {step.label}
 </span>
 {step.agent && (
 <span className="text-[9px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
 {step.agent}
 </span>
 )}
 </div>
 {step.description && (
 <p className={cn(
'text-[10px] mt-0.5',
 step.status ==='pending' ?'text-muted-foreground' :'text-muted-foreground',
 )}>
 {step.description}
 </p>
 )}
 {step.timestamp && (
 <span className="text-[9px] text-muted-foreground">{step.timestamp}</span>
 )}
 </div>
 </div>
 );
 })}
 </div>
 </div>

 {/* 预计完成时间 */}
 {estimatedCompletion && (
 <div className="px-4 pb-3">
 <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
 <icons.Calendar className="w-3 h-3" />
 <span>预计完成: {estimatedCompletion}</span>
 </div>
 </div>
 )}

 {/* 操作按钮 */}
 {actions && actions.length > 0 && (
 <div className="px-4 pb-4 flex gap-2">
 {actions.map((action) => (
 <button
 key={action.actionId}
 onClick={() => handleAction(action.actionId, action.payload)}
 className={cn(
'flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-[colors,transform] active:scale-95',
 action.variant ==='primary'
 ?'bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm'
 : action.variant ==='outline'
 ?'border border-border text-muted-foreground hover:bg-muted'
 :'bg-muted text-muted-foreground hover:bg-muted/80',
 )}
 >
 {action.label}
 <icons.ChevronRight className="w-3 h-3" />
 </button>
 ))}
 </div>
 )}
 </div>
 );
});
