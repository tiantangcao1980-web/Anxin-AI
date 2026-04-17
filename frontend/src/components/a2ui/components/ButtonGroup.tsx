/**
 * 按钮组组件
 * 
 * 支持 horizontal / vertical / grid 布局
 * grid 模式下按钮带卡片效果，适合快捷入口场景
 */

import { memo } from'react';
import { icons } from'@/lib/icons';
import type { ButtonGroupComponent, A2UIEventHandler } from'../types';
import { cn } from'@/lib/utils';

const ICON_MAP: Record<string, React.ElementType> = {
 users: icons.Users,
'file-text': icons.FileText,
'pen-tool': icons.PenTool,
 shield: icons.Shield,
'message-circle': icons.MessageCircle,
 search: icons.Search,
};

interface Props {
 component: ButtonGroupComponent;
 onEvent: A2UIEventHandler;
}

export const ButtonGroup = memo(function ButtonGroup({ component, onEvent }: Props) {
 const { data } = component;
 const isGrid = data.layout ==='grid';

 return (
 <div className={cn(
'a2ui-button-group',
 data.layout ==='vertical' &&'flex flex-col gap-2',
 isGrid &&'grid grid-cols-2 gap-2.5',
 (!data.layout || data.layout ==='horizontal') &&'flex flex-wrap gap-2',
 data.align ==='center' &&'justify-center',
 data.align ==='right' &&'justify-end',
 data.align ==='stretch' && !isGrid &&'[&>button]:flex-1',
 component.className,
 )}>
 {data.buttons.map((btn) => {
 const Icon = btn.icon ? ICON_MAP[btn.icon] : null;

 return (
 <button
 key={btn.id}
 onClick={() => {
 if (!btn.disabled && !btn.loading) {
 onEvent({
 type:'action',
 actionId: btn.actionId,
 componentId: component.id,
 payload: btn.payload,
 });
 }
 }}
 disabled={btn.disabled || btn.loading}
 className={cn(
'transition-all active:scale-[0.97]',
 // Grid 模式 — 卡片式按钮
 isGrid &&'flex items-center gap-3 px-4 py-3.5 rounded-xl border border-border bg-background hover:border-primary/20 hover:bg-primary/5 hover:shadow-sm text-left group',
 // 非 Grid 模式 — 标准按钮
 !isGrid &&'inline-flex items-center justify-center gap-2 rounded-xl font-medium',
 !isGrid && btn.size ==='sm' &&'px-3 py-1.5 text-xs',
 !isGrid && btn.size ==='lg' &&'px-6 py-3 text-base',
 !isGrid && (!btn.size || btn.size ==='md') &&'px-5 py-2.5 text-sm',
 !isGrid && btn.variant ==='primary' &&'bg-primary text-primary-foreground hover:bg-primary/90',
 !isGrid && btn.variant ==='secondary' &&'bg-muted text-foreground hover:bg-accent',
 !isGrid && btn.variant ==='outline' &&'border border-border text-foreground hover:bg-muted/50',
 !isGrid && btn.variant ==='ghost' &&'text-muted-foreground hover:bg-muted',
 !isGrid && btn.variant ==='destructive' &&'bg-destructive text-destructive-foreground hover:bg-destructive/20',
 !isGrid && !btn.variant &&'bg-muted text-foreground hover:bg-accent',
 (btn.disabled || btn.loading) &&'opacity-50 cursor-not-allowed',
 )}
 >
 {btn.loading && <icons.Loader2 className="w-4 h-4 animate-spin" />}
 {isGrid && Icon && (
 <div className="w-9 h-9 rounded-lg bg-primary/5 text-primary flex items-center justify-center flex-shrink-0 group-hover:bg-primary/10 transition-colors">
 <Icon className="w-4.5 h-4.5" />
 </div>
 )}
 {isGrid ? (
 <span className="text-sm font-medium text-foreground flex-1">{btn.label}</span>
 ) : (
 <span>{btn.label}</span>
 )}
 {isGrid && (
 <icons.ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
 )}
 </button>
 );
 })}
 </div>
 );
});
