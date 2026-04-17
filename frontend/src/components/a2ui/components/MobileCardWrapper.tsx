/**
 * MobileCardWrapper — 移动端千问风格卡片包装器
 * 
 * 特性：
 * 1. 全宽卡片布局（移动端无边距）
 * 2. 可折叠/展开的卡片内容
 * 3. 底部固定操作栏
 * 4. 横向滑动的子卡片列表
 */

import { memo, useState, useRef, useCallback, type ReactNode } from'react';
import { motion, AnimatePresence, useMotionValue, useTransform, PanInfo } from'framer-motion';
import { icons } from'@/lib/icons';
import { cn } from'@/lib/utils';

// ========== 可折叠卡片 ==========

interface CollapsibleCardProps {
 title: string;
 subtitle?: string;
 icon?: ReactNode;
 defaultCollapsed?: boolean;
 children: ReactNode;
 className?: string;
 /** 折叠时显示的预览内容 */
 preview?: ReactNode;
}

export const CollapsibleCard = memo(function CollapsibleCard({
 title,
 subtitle,
 icon,
 defaultCollapsed = false,
 children,
 className,
 preview,
}: CollapsibleCardProps) {
 const [collapsed, setCollapsed] = useState(defaultCollapsed);

 return (
 <div className={cn(
'bg-background rounded-2xl border border-border shadow-sm overflow-hidden',
 className,
 )}>
 {/* 标题栏 — 可点击折叠 */}
 <button
 onClick={() => setCollapsed(!collapsed)}
 className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-muted/50 transition-colors"
 >
 {icon && <div className="flex-shrink-0">{icon}</div>}
 <div className="flex-1 min-w-0">
 <h4 className="text-sm font-semibold text-foreground truncate">{title}</h4>
 {subtitle && <p className="text-[10px] text-muted-foreground truncate">{subtitle}</p>}
 </div>
 <motion.div
 animate={{ rotate: collapsed ? 0 : 180 }}
 transition={{ duration: 0.2 }}
 >
 <icons.ChevronDown className="w-4 h-4 text-muted-foreground" />
 </motion.div>
 </button>

 {/* 折叠时的预览 */}
 {collapsed && preview && (
 <div className="px-4 pb-3 -mt-1">
 {preview}
 </div>
 )}

 {/* 内容区 */}
 <AnimatePresence initial={false}>
 {!collapsed && (
 <motion.div
 initial={{ height: 0, opacity: 0 }}
 animate={{ height:'auto', opacity: 1 }}
 exit={{ height: 0, opacity: 0 }}
 transition={{ duration: 0.25 }}
 className="overflow-hidden"
 >
 <div className="px-4 pb-4">
 {children}
 </div>
 </motion.div>
 )}
 </AnimatePresence>
 </div>
 );
});

// ========== 横向滑动卡片列表 ==========

interface HorizontalSwipeListProps {
 children: ReactNode[];
 /** 是否显示分页指示器 */
 showDots?: boolean;
 /** 卡片间距 */
 gap?: number;
 className?: string;
}

export const HorizontalSwipeList = memo(function HorizontalSwipeList({
 children,
 showDots = true,
 gap = 12,
 className,
}: HorizontalSwipeListProps) {
 const scrollRef = useRef<HTMLDivElement>(null);
 const [activeIndex, setActiveIndex] = useState(0);

 const handleScroll = useCallback(() => {
 if (!scrollRef.current) return;
 const { scrollLeft, clientWidth } = scrollRef.current;
 const newIndex = Math.round(scrollLeft / (clientWidth * 0.85 + gap));
 setActiveIndex(newIndex);
 }, [gap]);

 return (
 <div className={cn('relative', className)}>
 {/* 滚动容器 */}
 <div
 ref={scrollRef}
 onScroll={handleScroll}
 className="flex overflow-x-auto snap-x snap-mandatory scrollbar-hide -mx-4 px-4"
 style={{ gap: `${gap}px` }}
 >
 {children.map((child, i) => (
 <div
 key={i}
 className="snap-start flex-shrink-0"
 style={{ width:'85%' }}
 >
 {child}
 </div>
 ))}
 </div>

 {/* 分页指示器 */}
 {showDots && children.length > 1 && (
 <div className="flex items-center justify-center gap-1.5 mt-3">
 {children.map((_, i) => (
 <div
 key={i}
 className={cn(
'rounded-full transition-all duration-200',
 i === activeIndex
 ?'w-4 h-1.5 bg-primary'
 :'w-1.5 h-1.5 bg-muted-foreground',
 )}
 />
 ))}
 </div>
 )}
 </div>
 );
});

// ========== 底部固定操作栏 ==========

interface BottomActionBarProps {
 /** 操作按钮 */
 actions: {
 id: string;
 label: string;
 variant?:'primary' |'secondary' |'outline' |'destructive';
 icon?: ReactNode;
 onClick: () => void;
 disabled?: boolean;
 loading?: boolean;
 }[];
 /** 附加信息（如价格） */
 info?: ReactNode;
 className?: string;
}

export const BottomActionBar = memo(function BottomActionBar({
 actions,
 info,
 className,
}: BottomActionBarProps) {
 return (
 <motion.div
 initial={{ y: 100, opacity: 0 }}
 animate={{ y: 0, opacity: 1 }}
 exit={{ y: 100, opacity: 0 }}
 className={cn(
'fixed bottom-0 left-0 right-0 z-30 bg-background border-t border-border px-4 py-3 safe-area-inset-bottom',
 className,
 )}
 >
 <div className="flex items-center gap-3">
 {/* 信息区域（如价格） */}
 {info && <div className="flex-shrink-0">{info}</div>}

 {/* 操作按钮 */}
 <div className="flex-1 flex items-center gap-2 justify-end">
 {actions.map((action) => (
 <button
 key={action.id}
 onClick={action.onClick}
 disabled={action.disabled || action.loading}
 className={cn(
'flex items-center justify-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-[colors,transform] active:scale-95',
 action.variant ==='primary'
 ?'bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm flex-1'
 : action.variant ==='destructive'
 ?'bg-destructive text-destructive-foreground hover:bg-destructive/20'
 : action.variant ==='outline'
 ?'border border-border text-foreground hover:bg-muted'
 :'bg-muted text-foreground hover:bg-muted',
 (action.disabled || action.loading) &&'opacity-50 cursor-not-allowed',
 )}
 >
 {action.icon}
 {action.label}
 </button>
 ))}
 </div>
 </div>
 </motion.div>
 );
});

// ========== 全宽卡片容器（移动端） ==========

interface FullWidthCardProps {
 children: ReactNode;
 className?: string;
 /** 是否移除水平内边距（让卡片贴边） */
 flush?: boolean;
}

export const FullWidthCard = memo(function FullWidthCard({
 children,
 className,
 flush = false,
}: FullWidthCardProps) {
 return (
 <div className={cn(
'bg-background rounded-2xl border border-border shadow-sm overflow-hidden',
 flush ?'-mx-4 rounded-none border-x-0' :'',
 className,
 )}>
 {children}
 </div>
 );
});
