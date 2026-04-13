/**
 * AI内容标识组件
 *
 * 依据GB 45438-2025《网络安全技术 人工智能生成合成内容标识方法》
 * 在AI生成的内容旁显示合规标识
 */

import { cn } from'@/lib/utils';
import { icons } from'@/lib/icons';

// ==================== AI标识徽章 ====================

interface AIBadgeProps {
 /** 标识类型 */
 type?:'text' |'document' |'analysis' |'suggestion';
 /** 尺寸 */
 size?:'sm' |'md';
 /** 额外类名 */
 className?: string;
}

const TYPE_LABELS: Record<string, string> = {
 text:'AI辅助生成',
 document:'AI辅助起草',
 analysis:'AI辅助分析',
 suggestion:'AI辅助建议',
};

export function AIBadge({ type ='text', size ='sm', className }: AIBadgeProps) {
 const label = TYPE_LABELS[type] || TYPE_LABELS.text;

 return (
 <span
 className={cn(
'inline-flex items-center gap-1 rounded-full border',
'bg-violet-50 border-violet-200 text-violet-600',
'dark:bg-violet-900/20 dark:border-violet-800 dark:text-violet-400',
 size ==='sm' ?'px-2 py-0.5 text-[10px]' :'px-2.5 py-1 text-xs',
 className,
 )}
 title="本内容由AI辅助生成，仅供参考"
 >
 <icons.Sparkles className={size ==='sm' ?'w-2.5 h-2.5' :'w-3 h-3'} />
 {label}
 </span>
 );
}

// ==================== AI免责声明 ====================

interface AIDisclaimerProps {
 type?:'text' |'document' |'analysis' |'suggestion';
 compact?: boolean;
 className?: string;
}

const DISCLAIMERS: Record<string, string> = {
 text:'本内容由AI辅助生成，仅供参考，不构成法律意见。如需专业法律服务，请咨询执业律师。',
 document:'本文书由AI辅助起草，使用前请由专业律师审核确认。',
 analysis:'本分析报告由AI辅助生成，分析结论仅供参考，请结合实际情况综合判断。',
 suggestion:'本建议由AI辅助生成，具体实施方案请咨询专业律师。',
};

export function AIDisclaimer({ type ='text', compact = false, className }: AIDisclaimerProps) {
 const disclaimer = DISCLAIMERS[type] || DISCLAIMERS.text;

 if (compact) {
 return (
 <p className={cn(
'text-[10px] text-muted-foreground flex items-center gap-1',
 className,
 )}>
 <icons.Info className="w-3 h-3 shrink-0" />
 {disclaimer}
 </p>
 );
 }

 return (
 <div className={cn(
'flex items-start gap-2 p-3 rounded-lg border',
'bg-warning/10/50 border-warning/20/50 text-warning',
'dark:bg-warning/10',
 className,
 )}>
 <icons.AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
 <div>
 <p className="text-xs font-medium mb-0.5">AI生成内容声明</p>
 <p className="text-[11px] leading-relaxed opacity-90">{disclaimer}</p>
 <p className="text-[10px] opacity-60 mt-1">依据：GB 45438-2025</p>
 </div>
 </div>
 );
}

// ==================== 法律引用卡片 ====================

interface LegalCitationCardProps {
 citation: {
 law_name: string;
 article: string;
 paragraph?: string;
 item?: string;
 content_preview?: string;
 url?: string;
 confidence?: number;
 };
 className?: string;
}

export function LegalCitationCard({ citation, className }: LegalCitationCardProps) {
 const displayText = `《${citation.law_name}》${citation.article}${citation.paragraph ||''}${citation.item ||''}`;

 return (
 <a
 href={citation.url ||'#'}
 target="_blank"
 rel="noopener noreferrer"
 className={cn(
'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs',
'bg-info/10 text-info border border-info/20',
'dark:bg-info/20',
'hover:bg-info/20 transition-colors',
'cursor-pointer no-underline',
 className,
 )}
 title={citation.content_preview || `查看${displayText}原文`}
 >
 <icons.Scale className="w-3 h-3 shrink-0" />
 <span>{displayText}</span>
 {citation.url && <icons.ExternalLink className="w-2.5 h-2.5 shrink-0 opacity-50" />}
 </a>
 );
}

// ==================== 引用列表 ====================

interface CitationListProps {
 citations: LegalCitationCardProps['citation'][];
 className?: string;
}

export function CitationList({ citations, className }: CitationListProps) {
 if (!citations || citations.length === 0) return null;

 return (
 <div className={cn('flex flex-wrap gap-1.5', className)}>
 {citations.map((citation, i) => (
 <LegalCitationCard key={`${citation.law_name}-${citation.article}-${i}`} citation={citation} />
 ))}
 </div>
 );
}

// ==================== 缺失条款警示 ====================

interface MissingClausesAlertProps {
 clauses: string[];
 className?: string;
}

export function MissingClausesAlert({ clauses, className }: MissingClausesAlertProps) {
 if (!clauses || clauses.length === 0) return null;

 return (
 <div className={cn(
'p-3 rounded-lg border',
'bg-warning/10 border-warning/20',
'dark:bg-warning/10',
 className,
 )}>
 <div className="flex items-center gap-2 mb-2">
 <icons.AlertTriangle className="w-4 h-4 text-warning" />
 <span className="text-sm font-medium text-warning">
 缺失条款提醒 ({clauses.length}项)
 </span>
 </div>
 <ul className="space-y-1">
 {clauses.map((clause, i) => (
 <li key={i} className="text-xs text-warning flex items-start gap-1.5">
 <span className="w-4 h-4 rounded-full bg-warning text-warning flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">
 {i + 1}
 </span>
 {clause}
 </li>
 ))}
 </ul>
 </div>
 );
}
