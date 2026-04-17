/**
 * RiskAssessmentCard — 风险评估雷达图卡片
 * 
 * 在对话流中展示综合风险评估结果：
 * - CSS 实现的简化雷达图（无需 D3/Chart.js 依赖）
 * - 风险等级色标
 * - 细分维度评分
 * - AI 建议摘要
 * - 操作按钮（查看详情、下载报告等）
 */

import { memo, useMemo } from'react';
import { motion } from'framer-motion';
import { icons } from'@/lib/icons';
import type { A2UIEventHandler } from'../types';
import { cn } from'@/lib/utils';

export interface RiskDimension {
 id: string;
 label: string;
 score: number; // 0-100
 maxScore?: number;
 level:'low' |'medium' |'high' |'critical';
 trend?:'up' |'down' |'stable';
}

export interface RiskAssessmentCardData {
 title: string;
 subtitle?: string;
 overallScore: number; // 0-100
 overallLevel:'low' |'medium' |'high' |'critical';
 dimensions: RiskDimension[];
 summary?: string;
 recommendations?: string[];
 actions?: {
 label: string;
 actionId: string;
 variant?:'primary' |'secondary' |'outline';
 payload?: Record<string, any>;
 }[];
}

interface RiskAssessmentCardProps {
 component: {
 id: string;
 type:'risk-assessment';
 data: RiskAssessmentCardData;
 };
 onEvent: A2UIEventHandler;
}

const LEVEL_CONFIG = {
 low: {
 label:'低风险',
 color:'text-success',
 bgColor:'bg-success/10',
 borderColor:'border-success/20',
 barColor:'bg-success',
 icon: icons.CheckCircle2,
 },
 medium: {
 label:'中风险',
 color:'text-warning',
 bgColor:'bg-warning/10 dark:bg-warning/30',
 borderColor:'border-yellow-200 dark:border-yellow-800',
 barColor:'bg-warning',
 icon: icons.AlertTriangle,
 },
 high: {
 label:'高风险',
 color:'text-orange-600 dark:text-orange-400',
 bgColor:'bg-orange-50 dark:bg-orange-950/30',
 borderColor:'border-orange-200 dark:border-orange-800',
 barColor:'bg-orange-500',
 icon: icons.AlertTriangle,
 },
 critical: {
 label:'严重风险',
 color:'text-destructive',
 bgColor:'bg-destructive/10',
 borderColor:'border-destructive/20',
 barColor:'bg-destructive',
 icon: icons.XCircle,
 },
};

/** CSS 雷达图（简化实现，最多 6 个维度） */
const RadarChart = memo(function RadarChart({
 dimensions,
}: {
 dimensions: RiskDimension[];
}) {
 // 限制最多 6 个维度
 const dims = dimensions.slice(0, 6);
 const count = dims.length;
 if (count < 3) return null;

 const size = 140;
 const center = size / 2;
 const maxRadius = center - 20;

 // 生成多边形顶点
 const getPoint = (index: number, radius: number) => {
 const angle = (Math.PI * 2 * index) / count - Math.PI / 2;
 return {
 x: center + radius * Math.cos(angle),
 y: center + radius * Math.sin(angle),
 };
 };

 // 背景网格
 const gridLevels = [0.25, 0.5, 0.75, 1];
 const gridPaths = gridLevels.map(level => {
 const points = Array.from({ length: count }, (_, i) => getPoint(i, maxRadius * level));
 return points.map(p => `${p.x},${p.y}`).join('');
 });

 // 数据多边形
 const dataPoints = dims.map((d, i) => getPoint(i, maxRadius * (d.score / 100)));
 const dataPath = dataPoints.map(p => `${p.x},${p.y}`).join('');

 // 轴线和标签
 const axes = dims.map((d, i) => ({
 end: getPoint(i, maxRadius),
 labelPos: getPoint(i, maxRadius + 14),
 label: d.label,
 score: d.score,
 }));

 return (
 <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="mx-auto">
 {/* 背景网格 */}
 {gridPaths.map((points, i) => (
 <polygon
 key={i}
 points={points}
 fill="none"
 stroke="hsl(var(--border))"
 strokeWidth="0.5"
 />
 ))}

 {/* 轴线 */}
 {axes.map((axis, i) => (
 <line
 key={i}
 x1={center}
 y1={center}
 x2={axis.end.x}
 y2={axis.end.y}
 stroke="hsl(var(--border))"
 strokeWidth="0.5"
 />
 ))}

 {/* 数据多边形 */}
 <motion.polygon
 points={dataPath}
 fill="rgba(59, 130, 246, 0.15)"
 stroke="rgba(59, 130, 246, 0.6)"
 strokeWidth="1.5"
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 transition={{ duration: 0.6, delay: 0.2 }}
 />

 {/* 数据点 */}
 {dataPoints.map((p, i) => (
 <motion.circle
 key={i}
 cx={p.x}
 cy={p.y}
 r="2.5"
 fill="#3b82f6"
 stroke="currentColor"
 strokeWidth="1"
 initial={{ scale: 0 }}
 animate={{ scale: 1 }}
 transition={{ delay: 0.3 + i * 0.1, duration: 0.3 }}
 />
 ))}

 {/* 标签 */}
 {axes.map((axis, i) => (
 <text
 key={i}
 x={axis.labelPos.x}
 y={axis.labelPos.y}
 textAnchor="middle"
 dominantBaseline="middle"
 className="fill-muted-foreground"
 fontSize="8"
 >
 {axis.label}
 </text>
 ))}
 </svg>
 );
});

export const RiskAssessmentCard = memo(function RiskAssessmentCard({
 component,
 onEvent,
}: RiskAssessmentCardProps) {
 const { data } = component;
 const {
 title, subtitle, overallScore, overallLevel,
 dimensions, summary, recommendations, actions,
 } = data;

 const levelConfig = LEVEL_CONFIG[overallLevel];
 const LevelIcon = levelConfig.icon;

 const handleAction = (actionId: string, payload?: Record<string, any>) => {
 onEvent({
 type:'action',
 actionId,
 componentId: component.id,
 payload,
 });
 };

 return (
 <div className="bg-background rounded-2xl border border-border shadow-sm overflow-hidden">
 {/* 头部：总分 + 等级 */}
 <div className="px-4 pt-4 pb-3">
 <div className="flex items-center justify-between">
 <div>
 <h4 className="text-sm font-semibold text-foreground">{title}</h4>
 {subtitle && (
 <p className="text-[10px] text-muted-foreground mt-0.5">{subtitle}</p>
 )}
 </div>
 <div className={cn(
'flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold',
 levelConfig.bgColor, levelConfig.borderColor, levelConfig.color,
 )}>
 <LevelIcon className="w-3.5 h-3.5" />
 {levelConfig.label}
 </div>
 </div>

 {/* 总分仪表盘 */}
 <div className="flex items-center gap-4 mt-3">
 <div className="relative w-16 h-16 flex-shrink-0">
 <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
 <path
 d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
 fill="none"
 stroke="hsl(var(--border))"
 strokeWidth="3"
 />
 <motion.path
 d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
 fill="none"
 stroke={overallLevel ==='low' ?'#22c55e' : overallLevel ==='medium' ?'#eab308' : overallLevel ==='high' ?'#f97316' :'#ef4444'}
 strokeWidth="3"
 strokeLinecap="round"
 strokeDasharray={`${overallScore}, 100`}
 initial={{ strokeDasharray:'0, 100' }}
 animate={{ strokeDasharray: `${overallScore}, 100` }}
 transition={{ duration: 1, ease:'easeOut' }}
 />
 </svg>
 <div className="absolute inset-0 flex items-center justify-center">
 <span className={cn('text-lg font-bold', levelConfig.color)}>{overallScore}</span>
 </div>
 </div>
 <div className="flex-1 min-w-0">
 {summary && (
 <p className="text-xs text-muted-foreground leading-relaxed">{summary}</p>
 )}
 </div>
 </div>
 </div>

 {/* 雷达图 */}
 {dimensions.length >= 3 && (
 <div className="px-4 pb-2">
 <RadarChart dimensions={dimensions} />
 </div>
 )}

 {/* 维度细分 */}
 <div className="px-4 pb-3">
 <div className="space-y-2">
 {dimensions.map((dim) => {
 const dimConfig = LEVEL_CONFIG[dim.level];
 return (
 <div key={dim.id} className="flex items-center gap-2">
 <span className="text-[10px] text-muted-foreground w-16 flex-shrink-0 truncate">{dim.label}</span>
 <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
 <motion.div
 className={cn('h-full rounded-full', dimConfig.barColor)}
 initial={{ width: 0 }}
 animate={{ width: `${dim.score}%` }}
 transition={{ duration: 0.6, delay: 0.1 }}
 />
 </div>
 <span className={cn('text-[10px] font-semibold w-8 text-right', dimConfig.color)}>
 {dim.score}
 </span>
 {dim.trend && dim.trend !=='stable' && (
 dim.trend ==='up' ?
 <icons.TrendingUp className="w-3 h-3 text-destructive" /> :
 <icons.TrendingDown className="w-3 h-3 text-success" />
 )}
 </div>
 );
 })}
 </div>
 </div>

 {/* AI 建议 */}
 {recommendations && recommendations.length > 0 && (
 <div className="px-4 pb-3">
 <div className="bg-primary/10 border border-primary/20 rounded-xl p-3">
 <div className="flex items-center gap-1.5 mb-1.5">
 <icons.Shield className="w-3 h-3 text-primary" />
 <span className="text-[10px] font-semibold text-primary">AI 建议</span>
 </div>
 <ul className="space-y-1">
 {recommendations.map((rec, i) => (
 <li key={i} className="text-[10px] text-primary flex items-start gap-1.5">
 <span className="text-primary/60 mt-0.5">•</span>
 {rec}
 </li>
 ))}
 </ul>
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
