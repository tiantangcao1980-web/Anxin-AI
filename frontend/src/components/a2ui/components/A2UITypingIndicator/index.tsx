/**
 * A2UI TypingIndicator - AI 思考动画
 * 多种动画风格：跳动圆点、波浪、脉冲
 */

import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';

/**
 * 动画类型
 */
export type TypingAnimation = 'dots' | 'wave' | 'pulse' | 'bounce';

/**
 * TypingIndicator 属性
 */
export interface A2UITypingIndicatorProps {
  animation?: TypingAnimation;
  text?: string;
  dotCount?: number;
  color?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

/**
 * 尺寸配置
 */
const sizes = {
  sm: {
    dot: 'w-1.5 h-1.5',
    text: 'text-xs',
    gap: 'gap-1'
  },
  md: {
    dot: 'w-2 h-2',
    text: 'text-sm',
    gap: 'gap-2'
  },
  lg: {
    dot: 'w-3 h-3',
    text: 'text-base',
    gap: 'gap-3'
  }
};

/**
 * 跳动圆点动画
 */
const DotsAnimation: React.FC<{
  count: number;
  color: string;
  size: 'sm' | 'md' | 'lg';
  sizeConfig: typeof sizes.sm;
}> = ({ count, color, sizeConfig }) => {
  return (
    <div className={cn('flex items-center', sizeConfig.gap)}>
      {Array.from({ length: count }).map((_, i) => (
        <motion.div
          key={i}
          className={cn(
            'rounded-full',
            sizeConfig.dot,
            color || 'bg-primary'
          )}
          animate={{
            y: [0, -10, 0],
            opacity: [0.5, 1, 0.5]
          }}
          transition={{
            duration: 0.8,
            repeat: Infinity,
            delay: i * 0.15,
            ease: 'easeInOut'
          }}
        />
      ))}
    </div>
  );
};

/**
 * 波浪动画
 */
const WaveAnimation: React.FC<{
  count: number;
  color: string;
  sizeConfig: typeof sizes.sm;
}> = ({ count, color, sizeConfig }) => {
  return (
    <div className={cn('flex items-center', sizeConfig.gap)}>
      {Array.from({ length: count }).map((_, i) => (
        <motion.div
          key={i}
          className={cn(
            'rounded-full',
            sizeConfig.dot,
            color || 'bg-primary'
          )}
          animate={{
            scaleY: [1, 2, 1]
          }}
          transition={{
            duration: 0.6,
            repeat: Infinity,
            delay: i * 0.1,
            ease: 'easeInOut'
          }}
        />
      ))}
    </div>
  );
};

/**
 * 脉冲动画
 */
const PulseAnimation: React.FC<{
  color: string;
  sizeConfig: typeof sizes.sm;
}> = ({ color, sizeConfig }) => {
  return (
    <div className="relative flex items-center justify-center">
      <motion.div
        className={cn(
          'rounded-full absolute',
          sizeConfig.dot,
          color || 'bg-primary'
        )}
        animate={{
          scale: [1, 2, 1],
          opacity: [0.8, 0, 0.8]
        }}
        transition={{
          duration: 1.5,
          repeat: Infinity,
          ease: 'easeInOut'
        }}
      />
      <motion.div
        className={cn(
          'rounded-full relative z-10',
          sizeConfig.dot,
          color || 'bg-primary'
        )}
        animate={{
          scale: [1, 1.2, 1]
        }}
        transition={{
          duration: 1.5,
          repeat: Infinity,
          ease: 'easeInOut'
        }}
      />
    </div>
  );
};

/**
 * 弹跳动画
 */
const BounceAnimation: React.FC<{
  count: number;
  color: string;
  sizeConfig: typeof sizes.sm;
}> = ({ count, color, sizeConfig }) => {
  return (
    <div className={cn('flex items-end', sizeConfig.gap)}>
      {Array.from({ length: count }).map((_, i) => (
        <motion.div
          key={i}
          className={cn(
            'rounded-t-sm',
            'w-1',
            color || 'bg-primary'
          )}
          style={{
            height: sizeConfig.dot
          }}
          animate={{
            height: ['8px', '24px', '8px']
          }}
          transition={{
            duration: 0.5,
            repeat: Infinity,
            delay: i * 0.1,
            ease: 'easeInOut'
          }}
        />
      ))}
    </div>
  );
};

/**
 * A2UI TypingIndicator 组件
 */
export const A2UITypingIndicator: React.FC<A2UITypingIndicatorProps> = ({
  animation = 'dots',
  text = 'AI 正在思考...',
  dotCount = 3,
  color = '',
  size = 'md',
  className
}) => {
  const sizeConfig = sizes[size];

  const renderAnimation = () => {
    switch (animation) {
      case 'dots':
        return (
          <DotsAnimation
            count={dotCount}
            color={color}
            size={size}
            sizeConfig={sizeConfig}
          />
        );
      case 'wave':
        return (
          <WaveAnimation
            count={dotCount}
            color={color}
            sizeConfig={sizeConfig}
          />
        );
      case 'pulse':
        return <PulseAnimation color={color} sizeConfig={sizeConfig} />;
      case 'bounce':
        return (
          <BounceAnimation
            count={dotCount}
            color={color}
            sizeConfig={sizeConfig}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-4 py-3 text-muted-foreground',
        className
      )}
    >
      {renderAnimation()}
      {text && (
        <motion.span
          className={sizeConfig.text}
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          {text}
        </motion.span>
      )}
    </div>
  );
};

/**
 * 紧凑型 TypingIndicator (无文本)
 */
export const A2UITypingDots: React.FC<{
  color?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}> = ({ color, size = 'sm', className }) => {
  return (
    <A2UITypingIndicator
      animation="dots"
      dotCount={3}
      color={color}
      size={size}
      text=""
      className={className}
    />
  );
};

/**
 * 默认导出
 */
export default A2UITypingIndicator;
