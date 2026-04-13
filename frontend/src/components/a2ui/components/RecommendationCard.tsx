/**
 * 推荐卡片组件
 * 类似千问的商品推荐卡片 → 法务场景：律师推荐、法条推荐、服务推荐
 */

import { memo } from'react';
import { icons } from'@/lib/icons';
import type { RecommendationCardComponent, A2UIEventHandler } from'../types';
import { cn } from'@/lib/utils';
import { A2UICardShell } from'./A2UICardShell';

interface Props {
 component: RecommendationCardComponent;
 onEvent: A2UIEventHandler;
}

export const RecommendationCard = memo(function RecommendationCard({ component, onEvent }: Props) {
 const { data } = component;

 const handleAction = () => {
 if (data.action) {
 onEvent({
 type:'action',
 actionId: data.action.actionId,
 componentId: component.id,
 payload: data.action.payload,
 });
 }
 };

 const handleSecondaryAction = () => {
 if (data.secondaryAction) {
 onEvent({
 type:'action',
 actionId: data.secondaryAction.actionId,
 componentId: component.id,
 payload: data.secondaryAction.payload,
 });
 }
 };

 return (
 <A2UICardShell
 title={data.title}
 subtitle={data.subtitle}
 className={cn('a2ui-recommendation-card', component.className)}
 headerAside={data.rating !== undefined ? (
 <div className="flex items-center gap-0.5">
 <icons.Star className="w-3.5 h-3.5 fill-amber-400 text-warning" />
 <span className="text-xs font-medium text-muted-foreground">
 {data.ratingText || data.rating.toFixed(1)}
 </span>
 </div>
 ) : null}
 actions={
 <>
 {data.secondaryAction ? (
 <button
 onClick={handleSecondaryAction}
 className="inline-flex items-center gap-1 rounded-xl px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
 >
 {data.secondaryAction.label}
 </button>
 ) : null}
 {data.action ? (
 <button
 onClick={handleAction}
 className={cn(
'inline-flex items-center gap-1 rounded-xl px-4 py-2 text-xs font-medium transition-colors',
 data.action.variant ==='secondary'
 ?'bg-surface-2 text-foreground hover:bg-muted'
 : data.action.variant ==='outline'
 ?'border border-primary/20 text-primary hover:bg-primary/5'
 :'bg-primary text-white hover:bg-primary-600',
 )}
 >
 {data.action.label}
 </button>
 ) : null}
 </>
 }
 >
 <div className="flex gap-3">
 {/* 图片区 */}
 {(data.image || data.imageFallback) && (
 <div className="flex-shrink-0 w-20 h-20 rounded-xl overflow-hidden bg-muted">
 {data.image ? (
 <img src={data.image} alt={data.title} className="w-full h-full object-cover" />
 ) : (
 <div className="w-full h-full flex items-center justify-center text-2xl font-bold text-muted-foreground/70">
 {data.imageFallback}
 </div>
 )}
 </div>
 )}

 {/* 信息区 */}
 <div className="flex-1 min-w-0">
 {data.meta && (
 <p className="text-xs text-muted-foreground/70 mt-1 flex items-center gap-1">
 <icons.MapPin className="w-3 h-3" />
 {data.meta}
 </p>
 )}

 {/* 标签 */}
 {data.tags && data.tags.length > 0 && (
 <div className="flex flex-wrap gap-1 mt-2">
 {data.tags.map((tag, i) => (
 <span
 key={i}
 className={cn(
'inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium',
 tag.color ==='blue' &&'bg-primary/5 text-primary dark:bg-primary/10 dark:text-primary',
 tag.color ==='green' &&'bg-success/10 text-success',
 tag.color ==='orange' &&'bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
 tag.color ==='red' &&'bg-destructive/10 text-destructive',
 !tag.color &&'bg-muted text-muted-foreground',
 )}
 >
 {tag.label}
 </span>
 ))}
 </div>
 )}

 {/* 描述 */}
 {data.description && (
 <p className="text-xs text-muted-foreground mt-2 line-clamp-2 leading-relaxed">
 {data.description}
 </p>
 )}

 <div className="mt-3 flex items-center justify-between">
 {data.price && (
 <div className="flex items-baseline gap-1.5">
 <span className="text-base font-bold text-orange-600 dark:text-orange-400">
 {data.price.currency ||'¥'}{data.price.amount}
 </span>
 {data.price.original && (
 <span className="text-xs text-muted-foreground/70 line-through">
 {data.price.currency ||'¥'}{data.price.original}
 </span>
 )}
 {data.price.label && (
 <span className="text-[10px] bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400 px-1.5 py-0.5 rounded-full font-medium">
 {data.price.label}
 </span>
 )}
 </div>
 )}
 </div>
 </div>
 </div>

 {data.details && data.details.length > 0 && (
 <div className="border-t border-border/50 px-4 py-2">
 {data.details.map((detail, i) => (
 <div key={i} className="flex items-center justify-between py-1">
 <span className="text-xs text-muted-foreground">{detail.label}</span>
 <span className="text-xs text-foreground">{detail.value}</span>
 </div>
 ))}
 </div>
 )}
 </A2UICardShell>
 );
});
