/**
 * 信息横幅
 * 类似千问的地址栏/活动公告横幅
 * → 法务场景：案件进度通知、法律政策更新提醒
 */

import { memo, useState } from'react';
import { icons } from'@/lib/icons';
import type { InfoBannerComponent, A2UIEventHandler } from'../types';
import { cn } from'@/lib/utils';

interface Props {
 component: InfoBannerComponent;
 onEvent: A2UIEventHandler;
}

const variantConfig = {
 info: { icon: icons.Info, bg:'bg-primary/5 dark:bg-primary/10', text:'text-primary dark:text-primary', border:'border-primary/10 dark:border-primary/20' },
 success: { icon: icons.CheckCircle, bg:'bg-success/10', text:'text-success', border:'border-success/20' },
 warning: { icon: icons.AlertTriangle, bg:'bg-warning/10', text:'text-warning', border:'border-warning/20' },
 error: { icon: icons.XCircle, bg:'bg-destructive/10', text:'text-destructive', border:'border-destructive/20' },
 promo: { icon: icons.Gift, bg:'bg-orange-50 dark:bg-orange-900/20', text:'text-orange-700 dark:text-orange-400', border:'border-orange-100 dark:border-orange-800' },
};

export const InfoBanner = memo(function InfoBanner({ component, onEvent }: Props) {
 const { data } = component;
 const [dismissed, setDismissed] = useState(false);
 const variant = data.variant ||'info';
 const config = variantConfig[variant];
 const Icon = config.icon;

 if (dismissed) return null;

 return (
 <div className={cn(
'a2ui-info-banner flex items-center gap-2 px-4 py-2.5 rounded-xl border',
 config.bg, config.border,
 component.className,
 )}>
 <Icon className={cn('w-4 h-4 flex-shrink-0', config.text)} />
 <p className={cn('flex-1 text-xs leading-relaxed', config.text)}>
 {data.content}
 </p>
 {data.action && (
 <button
 onClick={() => onEvent({
 type:'action',
 actionId: data.action!.actionId,
 componentId: component.id,
 })}
 className={cn('flex-shrink-0 flex items-center gap-0.5 text-xs font-medium', config.text)}
 >
 {data.action.label}
 <icons.ChevronRight className="w-3.5 h-3.5" />
 </button>
 )}
 {data.dismissible && (
 <button
 onClick={() => {
 setDismissed(true);
 onEvent({ type:'dismiss', actionId:'banner-dismiss', componentId: component.id });
 }}
 className="flex-shrink-0 p-0.5 rounded-full hover:bg-black/5 dark:hover:bg-white/5"
 >
 <icons.X className="w-3.5 h-3.5 text-muted-foreground/70" />
 </button>
 )}
 </div>
 );
});
