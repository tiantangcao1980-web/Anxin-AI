/**
 * ReadinessIndicator — 信息就绪度可视化组件
 *
 * 在需求分析阶段展示信息收集进度，让用户有控制感：
 * - 进度条显示就绪度百分比
 * - 已收集/待补充信息清单
 * - 用户可选择"继续补充"或"直接生成"
 */

import { motion } from'framer-motion';
import { icons } from'@/lib/icons';

interface SlotInfo {
 key: string;
 label: string;
 value?: string;
 source?: string;
}

interface ReadinessIndicatorProps {
 score: number; // 0-1
 filledSlots: SlotInfo[];
 missingElements: string[];
 onProceed?: () => void;
 onContinue?: () => void;
 compact?: boolean;
}

export function ReadinessIndicator({
 score,
 filledSlots,
 missingElements,
 onProceed,
 onContinue,
 compact = false,
}: ReadinessIndicatorProps) {
 const percentage = Math.round(score * 100);
 const level = score >= 0.7 ?'high' : score >= 0.4 ?'medium' :'low';

 const colorMap = {
 high: { bar:'bg-success', text:'text-success', bg:'bg-success/10', border:'border-success/20' },
 medium: { bar:'bg-warning', text:'text-warning', bg:'bg-warning/10', border:'border-warning/20' },
 low: { bar:'bg-destructive', text:'text-destructive', bg:'bg-destructive/10', border:'border-destructive/20' },
 };
 const colors = colorMap[level];

 if (compact) {
 return (
 <motion.div
 initial={{ opacity: 0, scale: 0.95 }}
 animate={{ opacity: 1, scale: 1 }}
 className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full ${colors.bg} border ${colors.border}`}
 >
 <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
 <motion.div
 className={`h-full ${colors.bar} rounded-full`}
 initial={{ width: 0 }}
 animate={{ width: `${percentage}%` }}
 transition={{ duration: 0.6, ease:'easeOut' }}
 />
 </div>
 <span className={`text-[10px] font-semibold ${colors.text}`}>{percentage}%</span>
 </motion.div>
 );
 }

 return (
 <motion.div
 initial={{ opacity: 0, y: 8 }}
 animate={{ opacity: 1, y: 0 }}
 className={`${colors.bg} border ${colors.border} rounded-xl p-4 max-w-[90%]`}
 >
 {/* 标题行 */}
 <div className="flex items-center justify-between mb-3">
 <div className="flex items-center gap-2">
 <icons.BarChart3 className={`w-4 h-4 ${colors.text}`} />
 <span className={`text-xs font-semibold ${colors.text}`}>信息就绪度</span>
 </div>
 <span className={`text-lg font-bold ${colors.text}`}>{percentage}%</span>
 </div>

 {/* 进度条 */}
 <div className="w-full h-2 bg-muted rounded-full overflow-hidden mb-3">
 <motion.div
 className={`h-full ${colors.bar} rounded-full`}
 initial={{ width: 0 }}
 animate={{ width: `${percentage}%` }}
 transition={{ duration: 0.8, ease:'easeOut' }}
 />
 </div>

 {/* 已收集信息 */}
 {filledSlots.length > 0 && (
 <div className="mb-2">
 {filledSlots.map((slot) => (
 <div key={slot.key} className="flex items-center gap-1.5 py-0.5">
 <icons.CheckCircle className="w-3 h-3 text-success flex-shrink-0" />
 <span className="text-xs text-foreground">
 {slot.label}: <span className="font-medium">{slot.value}</span>
 </span>
 {slot.source ==='profile' && (
 <span className="text-[9px] text-muted-foreground bg-muted px-1 rounded">历史记录</span>
 )}
 </div>
 ))}
 </div>
 )}

 {/* 缺失信息 */}
 {missingElements.length > 0 && (
 <div className="mb-3">
 {missingElements.map((item, i) => (
 <div key={i} className="flex items-center gap-1.5 py-0.5">
 <icons.AlertCircle className="w-3 h-3 text-warning flex-shrink-0" />
 <span className="text-xs text-muted-foreground">待补充: {item}</span>
 </div>
 ))}
 </div>
 )}

 {/* 操作按钮 */}
 {(onProceed || onContinue) && (
 <div className="flex gap-2 mt-1">
 {onContinue && missingElements.length > 0 && (
 <button
 onClick={onContinue}
 className="flex-1 px-3 py-2 text-xs font-medium rounded-lg border border-border bg-background text-foreground hover:bg-muted transition-colors"
 >
 继续补充
 </button>
 )}
 {onProceed && score >= 0.4 && (
 <button
 onClick={onProceed}
 className={`flex-1 px-3 py-2 text-xs font-medium rounded-lg transition-colors ${
 score >= 0.7
 ?'bg-primary text-primary-foreground hover:bg-primary/90'
 :'bg-warning text-warning-foreground hover:bg-warning/20'
 }`}
 >
 {score >= 0.7 ?'开始处理' :'使用默认值生成'}
 </button>
 )}
 </div>
 )}
 </motion.div>
 );
}
