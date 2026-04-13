/**
 * 合同条款对比卡片
 * 对比两个版本的合同条款差异，高亮变更部分
 * 
 * 用于：合同审查、修改建议、版本对比
 */

import { memo, useState } from'react';
import { icons } from'@/lib/icons';
import type { A2UIEventHandler } from'../types';
import { cn } from'@/lib/utils';

export interface ContractCompareData {
 title: string;
 subtitle?: string;
 /** 对比双方名称 */
 leftLabel: string;
 rightLabel: string;
 /** 差异条款列表 */
 clauses: ClauseDiff[];
 /** 总结 */
 summary?: {
 totalClauses: number;
 changedClauses: number;
 riskLevel:'low' |'medium' |'high';
 recommendation: string;
 };
 /** 操作按钮 */
 actions?: {
 label: string;
 actionId: string;
 variant?:'primary' |'secondary' |'outline';
 }[];
}

interface ClauseDiff {
 id: string;
 clauseTitle: string;
 /** 变更类型 */
 changeType:'added' |'removed' |'modified' |'unchanged';
 /** 左侧（原始）内容 */
 leftContent?: string;
 /** 右侧（新版）内容 */
 rightContent?: string;
 /** 风险等级 */
 riskLevel?:'low' |'medium' |'high';
 /** AI 点评 */
 comment?: string;
}

export interface ContractCompareCardComponent {
 id: string;
 type:'contract-compare';
 data: ContractCompareData;
 visible?: boolean;
 className?: string;
}

interface Props {
 component: ContractCompareCardComponent;
 onEvent: A2UIEventHandler;
}

const changeTypeConfig = {
 added: { label:'新增', color:'text-success bg-success/10 border-success/20', icon: icons.CheckCircle },
 removed: { label:'删除', color:'text-destructive bg-destructive/10 border-destructive/20', icon: icons.XCircle },
 modified: { label:'修改', color:'text-warning bg-warning/10 border-warning/20', icon: icons.AlertTriangle },
 unchanged: { label:'未变', color:'text-muted-foreground bg-muted border-border', icon: icons.Minus },
};

const riskColors = {
 low:'text-success bg-success/10',
 medium:'text-warning bg-warning/10',
 high:'text-destructive bg-destructive/10',
};

export const ContractCompareCard = memo(function ContractCompareCard({ component, onEvent }: Props) {
 const { data } = component;
 const [expandedClauses, setExpandedClauses] = useState<Set<string>>(new Set());

 const toggleClause = (id: string) => {
 setExpandedClauses(prev => {
 const next = new Set(prev);
 if (next.has(id)) next.delete(id);
 else next.add(id);
 return next;
 });
 };

 return (
 <div className={cn(
'bg-background rounded-2xl border border-border shadow-sm overflow-hidden',
 component.className,
 )}>
 {/* 标题栏 */}
 <div className="px-4 py-3 border-b border-border bg-primary/5">
 <h3 className="font-semibold text-sm text-foreground">{data.title}</h3>
 {data.subtitle && (
 <p className="text-xs text-muted-foreground mt-0.5">{data.subtitle}</p>
 )}
 </div>

 {/* 摘要 */}
 {data.summary && (
 <div className="px-4 py-3 bg-muted/50 border-b border-border flex items-center gap-4 text-xs">
 <span className="text-muted-foreground">
 共 <strong>{data.summary.totalClauses}</strong> 条 · 变更 <strong>{data.summary.changedClauses}</strong> 条
 </span>
 <span className={cn('px-2 py-0.5 rounded-full text-[10px] font-medium', riskColors[data.summary.riskLevel])}>
 风险: {data.summary.riskLevel ==='low' ?'低' : data.summary.riskLevel ==='medium' ?'中' :'高'}
 </span>
 {data.summary.recommendation && (
 <span className="text-muted-foreground flex-1 truncate">{data.summary.recommendation}</span>
 )}
 </div>
 )}

 {/* 对比列头 */}
 <div className="grid grid-cols-[1fr,1fr] gap-0 px-4 py-2 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider border-b border-border">
 <span>{data.leftLabel}</span>
 <span>{data.rightLabel}</span>
 </div>

 {/* 条款对比列表 */}
 <div className="divide-y divide-border/30">
 {data.clauses.map((clause) => {
 const config = changeTypeConfig[clause.changeType];
 const ChangeIcon = config.icon;
 const isExpanded = expandedClauses.has(clause.id);

 return (
 <div key={clause.id} className="group">
 {/* 条款标题行 */}
 <button
 onClick={() => toggleClause(clause.id)}
 className="w-full flex items-center gap-2 px-4 py-2.5 hover:bg-muted/50 transition-colors text-left"
 >
 <ChangeIcon className={cn('w-3.5 h-3.5 flex-shrink-0', config.color.split('')[0])} />
 <span className="text-xs font-medium text-foreground flex-1">{clause.clauseTitle}</span>
 <span className={cn('text-[10px] px-2 py-0.5 rounded-full border font-medium', config.color)}>
 {config.label}
 </span>
 {clause.riskLevel && clause.riskLevel !=='low' && (
 <icons.AlertTriangle className={cn('w-3 h-3', clause.riskLevel ==='high' ?'text-destructive' :'text-warning')} />
 )}
 {isExpanded ? <icons.ChevronUp className="w-3.5 h-3.5 text-muted-foreground" /> : <icons.ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />}
 </button>

 {/* 展开的对比内容 */}
 {isExpanded && (
 <div className="px-4 pb-3">
 <div className="grid grid-cols-2 gap-3">
 {/* 左侧（原始） */}
 <div className={cn(
'p-3 rounded-lg text-xs leading-relaxed',
 clause.changeType ==='removed' ?'bg-destructive/10/50 text-destructive line-through' :'bg-muted text-foreground/80',
 )}>
 {clause.leftContent || <span className="text-muted-foreground italic">（无）</span>}
 </div>
 {/* 右侧（新版） */}
 <div className={cn(
'p-3 rounded-lg text-xs leading-relaxed',
 clause.changeType ==='added' ?'bg-success/10 text-success' :
 clause.changeType ==='modified' ?'bg-warning/10/50 text-warning' :'bg-muted text-foreground/80',
 )}>
 {clause.rightContent || <span className="text-muted-foreground italic">（无）</span>}
 </div>
 </div>
 {/* AI 点评 */}
 {clause.comment && (
 <div className="mt-2 px-3 py-2 bg-primary/5 rounded-lg flex items-start gap-2">
 <span className="text-[10px] font-medium text-primary bg-primary/10 px-1.5 py-0.5 rounded flex-shrink-0">AI</span>
 <p className="text-[11px] text-primary leading-relaxed">{clause.comment}</p>
 </div>
 )}
 </div>
 )}
 </div>
 );
 })}
 </div>

 {/* 操作按钮 */}
 {data.actions && data.actions.length > 0 && (
 <div className="px-4 py-3 border-t border-border flex items-center gap-2 justify-end">
 {data.actions.map((action) => (
 <button
 key={action.actionId}
 onClick={() => onEvent({
 type:'action',
 actionId: action.actionId,
 componentId: component.id,
 })}
 className={cn(
'px-4 py-2 rounded-lg text-xs font-medium transition-all active:scale-95',
 action.variant ==='primary'
 ?'bg-primary text-white hover:bg-primary/90'
 : action.variant ==='outline'
 ?'border border-border text-foreground/80 hover:bg-muted/50'
 :'bg-muted text-foreground/80 hover:bg-muted/80',
 )}
 >
 {action.label}
 </button>
 ))}
 </div>
 )}
 </div>
 );
});
