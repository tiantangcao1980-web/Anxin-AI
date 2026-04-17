/**
 * CaseAnalysisCard - AI 案件分析结果卡片
 *
 * 在对话流中展示 AI 对案件的综合分析：
 * - 案件类型 + 管辖区域徽章
 * - 当事人列表
 * - 争议焦点（编号列表）
 * - 法律依据（徽章组）
 * - 胜诉概率进度条
 * - AI 建议文本
 */

import { memo } from'react';
import { icons } from'@/lib/icons';
import { cardStyle, heading, statusBadge } from'@/lib/design-tokens';
import { cn } from'@/lib/utils';

export interface CaseAnalysisCardProps {
 caseType: string;
 parties: string[];
 jurisdiction: string;
 keyIssues: string[];
 legalBasis: string[];
 winProbability: number;
 recommendation: string;
}

const getProbabilityConfig = (probability: number) => {
 if (probability >= 70) return { color:'bg-success', text:'text-success', label:'较高' };
 if (probability >= 40) return { color:'bg-warning', text:'text-warning', label:'中等' };
 return { color:'bg-destructive', text:'text-destructive', label:'较低' };
};

export const CaseAnalysisCard = memo(function CaseAnalysisCard({
 caseType,
 parties,
 jurisdiction,
 keyIssues,
 legalBasis,
 winProbability,
 recommendation,
}: CaseAnalysisCardProps) {
 const probConfig = getProbabilityConfig(winProbability);

 return (
 <div className={cn(cardStyle.base,'overflow-hidden')}>
 {/* 头部：案件类型 + 管辖区域 */}
 <div className="flex items-center gap-2 mb-4">
 <span className={cn(
'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold',
 statusBadge.info,
 )}>
 <icons.Briefcase className="w-3.5 h-3.5" />
 {caseType}
 </span>
 <span className={cn(
'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold',
 statusBadge.neutral,
 )}>
 <icons.MapPin className="w-3.5 h-3.5" />
 {jurisdiction}
 </span>
 </div>

 {/* 当事人 */}
 <div className="mb-4">
 <h5 className={cn(heading.card,'mb-2 flex items-center gap-1.5')}>
 <icons.Users className="w-4 h-4 text-muted-foreground" />
 当事人
 </h5>
 <div className="flex flex-wrap gap-2">
 {parties.map((party, i) => (
 <span
 key={i}
 className="inline-flex items-center px-2.5 py-1 rounded-lg bg-muted/50 text-xs text-foreground font-medium"
 >
 {party}
 </span>
 ))}
 </div>
 </div>

 {/* 争议焦点 */}
 <div className="mb-4">
 <h5 className={cn(heading.card,'mb-2 flex items-center gap-1.5')}>
 <icons.AlertCircle className="w-4 h-4 text-muted-foreground" />
 争议焦点
 </h5>
 <ol className="space-y-1.5 pl-1">
 {keyIssues.map((issue, i) => (
 <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground leading-relaxed">
 <span className="flex-shrink-0 w-5 h-5 rounded-full bg-primary/10 text-primary text-[10px] font-semibold flex items-center justify-center mt-0.5">
 {i + 1}
 </span>
 <span>{issue}</span>
 </li>
 ))}
 </ol>
 </div>

 {/* 法律依据 */}
 <div className="mb-4">
 <h5 className={cn(heading.card,'mb-2 flex items-center gap-1.5')}>
 <icons.Scale className="w-4 h-4 text-muted-foreground" />
 法律依据
 </h5>
 <div className="flex flex-wrap gap-1.5">
 {legalBasis.map((basis, i) => (
 <span
 key={i}
 className={cn(
'inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium',
 statusBadge.info,
 )}
 >
 {basis}
 </span>
 ))}
 </div>
 </div>

 {/* 胜诉概率 */}
 <div className="mb-4">
 <div className="flex items-center justify-between mb-2">
 <h5 className={cn(heading.card,'flex items-center gap-1.5')}>
 <icons.TrendingUp className="w-4 h-4 text-muted-foreground" />
 胜诉概率
 </h5>
 <span className={cn('text-sm font-bold', probConfig.text)}>
 {winProbability}%
 <span className="text-[10px] font-normal ml-1">({probConfig.label})</span>
 </span>
 </div>
 <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
 <div
 className={cn('h-full rounded-full transition-[width] duration-700 ease-out', probConfig.color)}
 style={{ width: `${Math.min(100, Math.max(0, winProbability))}%` }}
 />
 </div>
 </div>

 {/* AI 建议 */}
 <div className="bg-primary/5 border border-primary/20 rounded-lg p-3">
 <div className="flex items-start gap-2">
 <icons.Sparkles className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
 <div>
 <span className="text-xs font-semibold text-primary">AI 建议</span>
 <p className="text-xs text-primary/80 leading-relaxed mt-1">
 {recommendation}
 </p>
 </div>
 </div>
 </div>
 </div>
 );
});
