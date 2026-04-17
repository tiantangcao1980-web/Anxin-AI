/**
 * 合同预览卡片
 * 展示待签署合同的概要和风险信息
 */

import { memo } from'react';
import { icons } from'@/lib/icons';
import type { ContractPreviewComponent, A2UIEventHandler } from'../types';
import { cn } from'@/lib/utils';

interface Props {
 component: ContractPreviewComponent;
 onEvent: A2UIEventHandler;
}

const riskLevelConfig = {
 low: { label:'低风险', color:'text-success', bg:'bg-success/10', icon: icons.CheckCircle },
 medium: { label:'中风险', color:'text-warning', bg:'bg-warning/10', icon: icons.Info },
 high: { label:'高风险', color:'text-destructive', bg:'bg-destructive/10', icon: icons.AlertTriangle },
};

export const ContractPreview = memo(function ContractPreview({ component, onEvent }: Props) {
 const { data } = component;
 const riskConfig = riskLevelConfig[data.riskLevel];
 const RiskIcon = riskConfig.icon;

 return (
 <div className={cn(
'a2ui-contract-preview bg-background rounded-2xl border border-border/50 shadow-sm overflow-hidden',
 component.className,
 )}>
 {/* 头部 */}
 <div className="flex items-start gap-3 p-4 pb-3">
 <div className="w-10 h-10 rounded-xl bg-primary/5 dark:bg-primary/10 flex items-center justify-center flex-shrink-0">
 <icons.FileText className="w-5 h-5 text-primary dark:text-primary" />
 </div>
 <div className="flex-1 min-w-0">
 <h4 className="font-semibold text-sm text-foreground line-clamp-1">
 {data.title}
 </h4>
 <p className="text-xs text-muted-foreground mt-0.5">{data.type}</p>
 </div>
 <div className={cn('flex items-center gap-1 px-2.5 py-1 rounded-full', riskConfig.bg)}>
 <RiskIcon className={cn('w-3.5 h-3.5', riskConfig.color)} />
 <span className={cn('text-[10px] font-semibold', riskConfig.color)}>{riskConfig.label}</span>
 </div>
 </div>

 {/* 签约方 */}
 {data.parties.length > 0 && (
 <div className="px-4 pb-3">
 <div className="flex items-center gap-1.5 mb-2">
 <icons.Users className="w-3.5 h-3.5 text-muted-foreground/70" />
 <span className="text-xs text-muted-foreground font-medium">签约方</span>
 </div>
 <div className="flex flex-wrap gap-2">
 {data.parties.map((party, i) => (
 <span key={i} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-muted/50 text-xs">
 <span className="text-foreground font-medium">{party.name}</span>
 <span className="text-muted-foreground/70">({party.role})</span>
 </span>
 ))}
 </div>
 </div>
 )}

 {/* 关键条款 */}
 {data.keyTerms.length > 0 && (
 <div className="mx-4 border-t border-border/50 py-2">
 {data.keyTerms.map((term, i) => (
 <div key={i} className="flex items-center justify-between py-1.5">
 <span className="text-xs text-muted-foreground">{term.label}</span>
 <span className="text-xs text-foreground font-medium">{term.value}</span>
 </div>
 ))}
 </div>
 )}

 {/* 风险项 */}
 {data.riskItems && data.riskItems.length > 0 && (
 <div className="mx-4 border-t border-border/50 py-3">
 <p className="text-xs text-muted-foreground font-medium mb-2">风险提示</p>
 <div className="space-y-1.5">
 {data.riskItems.map((risk, i) => (
 <div key={i} className="flex items-start gap-2">
 <div className={cn(
'w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0',
 risk.level ==='high' &&'bg-destructive',
 risk.level ==='medium' &&'bg-warning',
 risk.level ==='low' &&'bg-success',
 )} />
 <span className="text-xs text-muted-foreground leading-relaxed">
 {risk.description}
 </span>
 </div>
 ))}
 </div>
 </div>
 )}

 {/* 操作按钮 */}
 {data.actions.length > 0 && (
 <div className="flex gap-2 p-4 border-t border-border/50">
 {data.actions.map((action) => (
 <button
 key={action.actionId}
 onClick={() => onEvent({
 type:'action',
 actionId: action.actionId,
 componentId: component.id,
 payload: { contractId: data.contractId },
 })}
 className={cn(
'flex-1 py-2.5 rounded-xl text-xs font-semibold transition-[colors,transform] active:scale-[0.98]',
 action.variant ==='primary' &&'bg-primary text-primary-foreground hover:bg-primary/90',
 action.variant ==='secondary' &&'bg-muted text-foreground hover:bg-accent',
 action.variant ==='outline' &&'border border-border text-foreground hover:bg-muted/50',
 !action.variant &&'bg-muted text-foreground hover:bg-accent',
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
