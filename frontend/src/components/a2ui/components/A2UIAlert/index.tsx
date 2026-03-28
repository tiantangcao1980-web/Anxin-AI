/**
 * A2UI Alert - 智能提示组件
 * 支持多种类型、可关闭、图标
 */

import React, { forwardRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../../utils/cn';

/**
 * Alert 类型
 */
export type AlertType = 'info' | 'success' | 'warning' | 'error';

/**
 * Alert 属性
 */
export interface A2UIAlertProps {
  type?: AlertType;
  title?: string;
  message: string;
  closable?: boolean;
  onClose?: () => void;
  icon?: React.ReactNode;
  className?: string;
  variant?: 'solid' | 'outlined' | 'soft';
}

/**
 * 样式配置
 */
const alertStyles = {
  types: {
    info: {
      solid: 'bg-primary text-white',
      outlined: 'border-2 border-primary text-primary bg-primary/5',
      soft: 'bg-primary/5 text-primary border border-primary/20',
    },
    success: {
      solid: 'bg-emerald-500 text-white',
      outlined: 'border-2 border-emerald-500 text-emerald-600 bg-emerald-50',
      soft: 'bg-emerald-50 text-emerald-600 border border-emerald-200',
    },
    warning: {
      solid: 'bg-amber-500 text-white',
      outlined: 'border-2 border-amber-500 text-amber-600 bg-amber-50',
      soft: 'bg-amber-50 text-amber-700 border border-amber-200',
    },
    error: {
      solid: 'bg-red-500 text-white',
      outlined: 'border-2 border-red-500 text-red-600 bg-red-50',
      soft: 'bg-red-50 text-red-700 border border-red-200',
    },
  },

  icons: {
    info: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    success: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    warning: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    error: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
};

/**
 * A2UI Alert 组件
 */
export const A2UIAlert = forwardRef<HTMLDivElement, A2UIAlertProps>(
  (
    {
      type = 'info',
      title,
      message,
      closable = false,
      onClose,
      icon,
      className,
      variant = 'soft',
    },
    ref
  ) => {
    const [visible, setVisible] = React.useState(true);

    const handleClose = () => {
      setVisible(false);
      onClose?.();
    };

    if (!visible) return null;

    const styles = alertStyles.types[type];
    const baseClassName = cn(
      'rounded-lg p-4',
      'flex items-start gap-3',
      'transition-all',
      styles[variant],
      className
    );

    const defaultIcon = alertStyles.icons[type];

    return (
      <motion.div
        ref={ref}
        className={baseClassName}
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.2 }}
      >
        {/* 图标 */}
        <div className="flex-shrink-0">{icon || defaultIcon}</div>

        {/* 内容 */}
        <div className="flex-1 min-w-0">
          {title && (
            <h4 className="font-semibold mb-1">{title}</h4>
          )}
          <p className="text-sm leading-relaxed">{message}</p>
        </div>

        {/* 关闭按钮 */}
        {closable && (
          <button
            onClick={handleClose}
            className="flex-shrink-0 opacity-50 hover:opacity-100 transition-opacity"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </motion.div>
    );
  }
);

A2UIAlert.displayName = 'A2UIAlert';

/**
 * Alert Group 容器
 */
export interface A2UIAlertGroupProps {
  children: React.ReactNode;
  className?: string;
}

export const A2UIAlertGroup: React.FC<A2UIAlertGroupProps> = ({ children, className }) => {
  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <AnimatePresence>{children}</AnimatePresence>
    </div>
  );
};

/**
 * 默认导出
 */
export default A2UIAlert;
