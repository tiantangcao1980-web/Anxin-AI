/**
 * MemoryVisualization Component
 * 显示记忆来源和使用情况
 */

import { motion } from'framer-motion';
import { icons } from'@/lib/icons';
import { cn } from'@/components/a2ui/utils/cn';

interface MemorySourceBadgeProps {
 sources: {
 semantic?: number;
 episodic?: number;
 working?: boolean;
 };
 className?: string;
}

/**
 * 记忆来源徽章组件
 */
export function MemorySourceBadge({ sources, className }: MemorySourceBadgeProps) {
 const badges = [];

 if (sources.semantic && sources.semantic > 0) {
 badges.push({
 type:'semantic',
 icon: icons.BookOpen,
 label:'知识库',
 count: sources.semantic,
 color:'bg-primary/10 text-primary',
 iconColor:'text-primary',
 });
 }

 if (sources.episodic && sources.episodic > 0) {
 badges.push({
 type:'episodic',
 icon: icons.Lightbulb,
 label:'历史案例',
 count: sources.episodic,
 color:'bg-violet-50 text-violet-700',
 iconColor:'text-violet-500',
 });
 }

 if (sources.working) {
 badges.push({
 type:'working',
 icon: icons.Brain,
 label:'会话记忆',
 count: 1,
 color:'bg-success/10 text-success',
 iconColor:'text-success',
 });
 }

 if (badges.length === 0) return null;

 return (
 <div className={cn('flex items-center gap-2', className)}>
 <div className="flex items-center gap-1 text-xs text-muted-foreground mr-2">
 <icons.Brain className="w-3 h-3" />
 <span>已使用记忆</span>
 </div>
 {badges.map((badge) => (
 <motion.div
 key={badge.type}
 initial={{ opacity: 0, scale: 0.8 }}
 animate={{ opacity: 1, scale: 1 }}
 className={cn(
'flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
 badge.color
 )}
 >
 <badge.icon className={cn('w-3 h-3', badge.iconColor)} />
 <span>{badge.label}</span>
 {badge.count > 1 && <span>x{badge.count}</span>}
 </motion.div>
 ))}
 </div>
 );
}

/**
 * 记忆检索详情面板
 */
interface MemoryRetrievalDetailsProps {
 semantic?: Array<{
 knowledge_id: string;
 title: string;
 similarity_score: number;
 }>;
 episodic?: Array<{
 episode_id: string;
 task_description: string;
 user_rating: number;
 similarity_score: number;
 }>;
 className?: string;
}

export function MemoryRetrievalDetails({
 semantic = [],
 episodic = [],
 className,
}: MemoryRetrievalDetailsProps) {
 if (semantic.length === 0 && episodic.length === 0) {
 return (
 <div className={cn('text-center py-4 text-muted-foreground text-sm', className)}>
 <icons.Brain className="w-8 h-8 mx-auto mb-2 opacity-30" />
 <p>未使用记忆</p>
 </div>
 );
 }

 return (
 <div className={cn('space-y-3', className)}>
 {/* 语义记忆 */}
 {semantic.length > 0 && (
 <div>
 <h4 className="text-xs font-medium text-foreground mb-2 flex items-center gap-1">
 <icons.BookOpen className="w-3 h-3 text-primary" />
 语义记忆 (知识库)
 </h4>
 <div className="space-y-2">
 {semantic.map((item, index) => (
 <div
 key={item.knowledge_id || index}
 className="p-2 bg-primary/10 border border-primary/20 rounded-lg"
 >
 <div className="flex items-center justify-between mb-1">
 <p className="text-xs font-medium text-foreground truncate flex-1">
 {item.title}
 </p>
 <span className="text-[10px] text-primary bg-primary/10 px-1.5 py-0.5 rounded">
 {(item.similarity_score * 100).toFixed(0)}%
 </span>
 </div>
 </div>
 ))}
 </div>
 </div>
 )}

 {/* 情景记忆 */}
 {episodic.length > 0 && (
 <div>
 <h4 className="text-xs font-medium text-foreground mb-2 flex items-center gap-1">
 <icons.Lightbulb className="w-3 h-3 text-violet-500" />
 情景记忆 (历史案例)
 </h4>
 <div className="space-y-2">
 {episodic.map((item, index) => (
 <div
 key={item.episode_id || index}
 className="p-2 bg-violet-50 border border-violet-100 rounded-lg"
 >
 <div className="flex items-center justify-between mb-1">
 <p className="text-xs text-muted-foreground truncate flex-1">
 {item.task_description}
 </p>
 <div className="flex items-center gap-1">
 {item.user_rating >= 4 && (
 <icons.CheckCircle className="w-3 h-3 text-success" />
 )}
 <span className="text-[10px] text-violet-600 bg-violet-100 px-1.5 py-0.5 rounded">
 {item.user_rating}★
 </span>
 </div>
 </div>
 <div className="flex items-center gap-2">
 <span className="text-[10px] text-muted-foreground">
 相似度: {(item.similarity_score * 100).toFixed(0)}%
 </span>
 </div>
 </div>
 ))}
 </div>
 </div>
 )}
 </div>
 );
}

/**
 * 记忆统计卡片
 */
interface MemoryStatsProps {
 semanticCount?: number;
 episodicCount?: number;
 workingSessions?: number;
 retrievalTime?: number;
 className?: string;
}

export function MemoryStats({
 semanticCount = 0,
 episodicCount = 0,
 workingSessions = 0,
 retrievalTime = 0,
 className,
}: MemoryStatsProps) {
 const stats = [
 {
 label:'语义记忆',
 value: semanticCount,
 icon: icons.BookOpen,
 color:'text-primary',
 bgColor:'bg-primary/10',
 },
 {
 label:'情景记忆',
 value: episodicCount,
 icon: icons.Lightbulb,
 color:'text-violet-500',
 bgColor:'bg-violet-50',
 },
 {
 label:'活跃会话',
 value: workingSessions,
 icon: icons.Brain,
 color:'text-success',
 bgColor:'bg-success/10',
 },
 ];

 return (
 <div className={cn('grid grid-cols-3 gap-3', className)}>
 {stats.map((stat) => (
 <div
 key={stat.label}
 className="p-3 bg-background border border-border rounded-lg"
 >
 <div className="flex items-center gap-2 mb-1">
 <stat.icon className={cn('w-4 h-4', stat.color)} />
 <span className="text-xs text-muted-foreground">{stat.label}</span>
 </div>
 <p className="text-lg font-semibold text-foreground">{stat.value}</p>
 </div>
 ))}
 {retrievalTime > 0 && (
 <div className="col-span-3 p-2 bg-muted rounded-lg text-center">
 <span className="text-xs text-muted-foreground">
 检索耗时: {retrievalTime.toFixed(3)}秒
 </span>
 </div>
 )}
 </div>
 );
}
