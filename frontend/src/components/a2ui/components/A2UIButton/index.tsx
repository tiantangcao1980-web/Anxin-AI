/**
 * A2UI Button - 智能按钮组件
 * 支持多种变体、加载状态、动画效果
 */

import React, { forwardRef } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';

/**
 * 按钮变体
 */
export type ButtonVariant = 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'ghost';

/**
 * 按钮尺寸
 */
export type ButtonSize = 'sm' | 'md' | 'lg' | 'xl';

/**
 * 按钮属性
 */
export interface A2UIButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'onAnimationStart' | 'onAnimationEnd' | 'onDragStart' | 'onDragEnd' | 'onDrag'> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  success?: boolean;
  error?: boolean;
  fullWidth?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  animation?: 'scale' | 'bounce' | 'shake' | 'none';
}

/**
 * 样式配置
 */
const buttonStyles = {
  variants: {
    primary: 'bg-primary text-white shadow-lg hover:shadow-xl',
    secondary: 'bg-muted text-foreground hover:bg-muted/80 border border-border',
    success: 'bg-emerald-600 text-white shadow-lg hover:shadow-xl',
    danger: 'bg-destructive text-white shadow-lg hover:shadow-xl',
    warning: 'bg-amber-600 text-white shadow-lg hover:shadow-xl',
    ghost: 'bg-transparent text-foreground hover:bg-muted'
  },

  sizes: {
    sm: 'px-3 py-1.5 text-sm rounded-lg',
    md: 'px-4 py-2 text-base rounded-xl',
    lg: 'px-6 py-3 text-lg rounded-2xl',
    xl: 'px-8 py-4 text-xl rounded-3xl'
  },

  iconSizes: {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
    xl: 'w-7 h-7'
  }
};

/**
 * 动画配置
 */
const animations = {
  scale: {
    whileHover: { scale: 1.05 },
    whileTap: { scale: 0.95 }
  },
  bounce: {
    whileHover: { y: -2 },
    whileTap: { y: 0 }
  },
  shake: {
    whileHover: { x: [0, -2, 2, -2, 2, 0] },
    whileTap: { scale: 0.95 }
  },
  none: {}
};

/**
 * 加载动画组件
 */
const ButtonSpinner: React.FC<{ size: ButtonSize }> = ({ size }) => {
  const spinnerSize = {
    sm: 'w-4 h-4 border-2',
    md: 'w-5 h-5 border-2',
    lg: 'w-6 h-6 border-3',
    xl: 'w-7 h-7 border-3'
  }[size];

  return (
    <svg
      className={cn('animate-spin', spinnerSize, 'border-current border-t-transparent')}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
};

/**
 * 成功图标组件
 */
const SuccessIcon: React.FC = () => (
  <svg
    className="w-5 h-5"
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M5 13l4 4L19 7"
    />
  </svg>
);

/**
 * 错误图标组件
 */
const ErrorIcon: React.FC = () => (
  <svg
    className="w-5 h-5"
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M6 18L18 6M6 6l12 12"
    />
  </svg>
);

/**
 * A2UI Button 组件
 */
export const A2UIButton = forwardRef<HTMLButtonElement, A2UIButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      success = false,
      error = false,
      fullWidth = false,
      icon,
      iconPosition = 'left',
      animation = 'scale',
      disabled,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const baseClassName = cn(
      // 基础样式
      'font-medium',
      'inline-flex',
      'items-center',
      'justify-center',
      'gap-2',
      'transition-all',
      'duration-200',
      'disabled:opacity-50',
      'disabled:cursor-not-allowed',

      // 变体样式
      buttonStyles.variants[variant],

      // 尺寸样式
      buttonStyles.sizes[size],

      // 全宽
      fullWidth && 'w-full',

      // 成功/错误状态
      success && 'ring-2 ring-emerald-400',
      error && 'ring-2 ring-destructive/40',

      className
    );

    const animationProps = animations[animation];

    const iconSizeClass = buttonStyles.iconSizes[size];

    return (
      <motion.button
        ref={ref}
        className={baseClassName}
        disabled={disabled || loading}
        {...animationProps}
        transition={{ type: 'spring', stiffness: 400, damping: 17 }}
        {...props}
      >
        {/* 加载状态 */}
        {loading && <ButtonSpinner size={size} />}

        {/* 成功状态 */}
        {success && !loading && <SuccessIcon />}

        {/* 错误状态 */}
        {error && !loading && !success && <ErrorIcon />}

        {/* 左侧图标 */}
        {!loading && !success && !error && icon && iconPosition === 'left' && (
          <span className={iconSizeClass}>{icon}</span>
        )}

        {/* 按钮文本 */}
        {!loading && !success && !error && children}

        {/* 右侧图标 */}
        {!loading && !success && !error && icon && iconPosition === 'right' && (
          <span className={iconSizeClass}>{icon}</span>
      )}
      </motion.button>
    );
  }
);

A2UIButton.displayName = 'A2UIButton';

/**
 * 默认导出
 */
export default A2UIButton;
