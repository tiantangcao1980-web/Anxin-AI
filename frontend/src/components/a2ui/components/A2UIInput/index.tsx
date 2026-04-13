/**
 * A2UI Input - 智能输入框组件
 * 支持多种状态、自动调整高度、错误提示
 */

import React, { forwardRef, useEffect, useRef } from'react';
import { motion } from'framer-motion';
import { cn } from'../../utils/cn';

/**
 * 输入框变体
 */
export type InputVariant ='default' |'filled' |'outlined' |'underlined';

/**
 * 输入框尺寸
 */
export type InputSize ='sm' |'md' |'lg';

/**
 * 输入框属性
 */
export interface A2UIInputProps extends Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>,'size' |'onAnimationStart' |'onAnimationEnd' |'onDragStart' |'onDragEnd' |'onDrag'> {
 variant?: InputVariant;
 size?: InputSize;
 error?: string;
 success?: string;
 icon?: React.ReactNode;
 onIconClick?: () => void;
 autoResize?: boolean;
 minHeight?: number;
 maxHeight?: number;
}

/**
 * 样式配置
 */
const inputStyles = {
 variants: {
 default:'bg-background border border-border focus:border-primary',
 filled:'bg-muted border-0 focus:bg-muted focus:ring-2 focus:ring-primary',
 outlined:'bg-transparent border-2 border-border focus:border-primary',
 underlined:'bg-transparent border-0 border-b-2 border-border rounded-none focus:border-primary px-0',
 },

 sizes: {
 sm:'px-3 py-2 text-sm rounded-md',
 md:'px-4 py-2.5 text-base rounded-lg',
 lg:'px-5 py-3 text-lg rounded-xl',
 },

 iconSizes: {
 sm:'w-4 h-4',
 md:'w-5 h-5',
 lg:'w-6 h-6',
 },
};

/**
 * A2UI Input 组件
 */
export const A2UIInput = forwardRef<HTMLTextAreaElement, A2UIInputProps>(
 (
 {
 variant ='default',
 size ='md',
 error,
 success,
 icon,
 onIconClick,
 autoResize = false,
 minHeight = 40,
 maxHeight = 120,
 className,
 value,
 onChange,
 ...props
 },
 ref
 ) => {
 const internalRef = useRef<HTMLTextAreaElement>(null);

 // 合并 refs
 const textareaRef = (ref || internalRef) as React.RefObject<HTMLTextAreaElement>;

 /**
 * 自动调整高度
 */
 useEffect(() => {
 if (!autoResize || !textareaRef.current) return;

 const textarea = textareaRef.current;
 textarea.style.height ='auto';
 const newHeight = Math.min(Math.max(textarea.scrollHeight, minHeight), maxHeight);
 textarea.style.height = `${newHeight}px`;
 }, [value, autoResize, minHeight, maxHeight, textareaRef]);

 const baseClassName = cn(
 // 基础样式
'w-full',
'transition-all',
'duration-200',
'resize-none',
'focus:outline-none',

 // 变体样式
 inputStyles.variants[variant],

 // 尺寸样式
 inputStyles.sizes[size],

 // 状态样式
 error &&'border-destructive/20 focus:border-destructive/20',
 success &&'border-success/20 focus:border-success/20',

 // 是否有图标
 icon &&'pr-10',

 // 禁用状态
 props.disabled &&'opacity-50 cursor-not-allowed bg-muted',

 className
 );

 const iconSizeClass = inputStyles.iconSizes[size];

 return (
 <div className="relative">
 <motion.textarea
 ref={textareaRef}
 className={baseClassName}
 value={value}
 onChange={onChange}
 whileFocus={{ scale: 1.01 }}
 transition={{ type:'spring', stiffness: 300, damping: 20 }}
 style={{
 minHeight: autoResize ? undefined : minHeight,
 maxHeight: autoResize ? undefined : maxHeight,
 }}
 {...props}
 />

 {/* 图标 */}
 {icon && (
 <motion.button
 type="button"
 onClick={onIconClick}
 className={cn(
'absolute right-3 top-1/2 -translate-y-1/2',
'text-muted-foreground hover:text-foreground',
'transition-colors'
 )}
 whileHover={{ scale: 1.1 }}
 whileTap={{ scale: 0.9 }}
 >
 {icon}
 </motion.button>
 )}

 {/* 错误提示 */}
 {error && (
 <motion.p
 initial={{ opacity: 0, y: -5 }}
 animate={{ opacity: 1, y: 0 }}
 className="text-xs text-destructive mt-1"
 >
 {error}
 </motion.p>
 )}

 {/* 成功提示 */}
 {success && (
 <motion.p
 initial={{ opacity: 0, y: -5 }}
 animate={{ opacity: 1, y: 0 }}
 className="text-xs text-success mt-1"
 >
 {success}
 </motion.p>
 )}
 </div>
 );
 }
);

A2UIInput.displayName ='A2UIInput';

/**
 * 默认导出
 */
export default A2UIInput;
