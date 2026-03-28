/**
 * Lottie 动画组件库
 * 提供常用的预加载动画
 */

import React, { useEffect, useState } from 'react';
import Lottie from 'lottie-react';
import { motion } from 'framer-motion';
import { cn } from '@/components/a2ui/utils/cn';

/**
 * 动画类型
 */
export type LottieAnimationType =
  | 'loading-spinner'
  | 'success-check'
  | 'error-x'
  | 'thinking-dots'
  | 'sending-message'
  | 'typing-indicator'
  | 'confetti'
  | 'rocket-launch'
  | 'file-upload'
  | 'ai-processing';

/**
 * Lottie 动画组件
 */
interface LottieAnimationProps {
  type: LottieAnimationType;
  size?: number;
  className?: string;
  loop?: boolean;
  autoplay?: boolean;
  onComplete?: () => void;
}

/**
 * 动画配置 (使用 LottieFiles 的免费动画)
 * 注意: 这些是示例 URL,实际使用时需要替换为真实的 Lottie JSON
 */
const ANIMATION_URLS: Record<LottieAnimationType, string> = {
  'loading-spinner': 'https://lottie.host/832344c0-51f5-4468-8a5a-5b4c3c2f1e2e/loading.json',
  'success-check': 'https://lottie.host/12345678-1234-1234-1234-123456789abc/success.json',
  'error-x': 'https://lottie.host/87654321-4321-4321-4321-cba987654321/error.json',
  'thinking-dots': 'https://lottie.host/11111111-2222-3333-4444-555555555555/thinking.json',
  'sending-message': 'https://lottie.host/22222222-3333-4444-5555-666666666666/sending.json',
  'typing-indicator': 'https://lottie.host/33333333-4444-5555-6666-777777777777/typing.json',
  'confetti': 'https://lottie.host/44444444-5555-6666-7777-888888888888/confetti.json',
  'rocket-launch': 'https://lottie.host/55555555-6666-7777-8888-999999999999/rocket.json',
  'file-upload': 'https://lottie.host/66666666-7777-8888-9999-000000000000/upload.json',
  'ai-processing': 'https://lottie.host/77777777-8888-9999-0000-111111111111/ai.json',
};

/**
 * 简化版动画配置 (内联,不依赖外部 URL)
 * 这里使用 CSS 动画模拟 Lottie 效果
 */
const SIMPLE_ANIMATIONS: Record<LottieAnimationType, React.ReactNode> = {
  'loading-spinner': (
    <div className="w-full h-full flex items-center justify-center">
      <div className="w-3/4 h-3/4 border-4 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  ),
  'success-check': (
    <div className="w-full h-full flex items-center justify-center">
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 10 }}
        className="w-3/4 h-3/4 rounded-full bg-emerald-500 flex items-center justify-center"
      >
        <svg
          className="w-1/2 h-1/2 text-white"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={3}
            d="M5 13l4 4L19 7"
          />
        </svg>
      </motion.div>
    </div>
  ),
  'error-x': (
    <div className="w-full h-full flex items-center justify-center">
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 10 }}
        className="w-3/4 h-3/4 rounded-full bg-red-500 flex items-center justify-center"
      >
        <svg
          className="w-1/2 h-1/2 text-white"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={3}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </motion.div>
    </div>
  ),
  'thinking-dots': (
    <div className="w-full h-full flex items-center justify-center gap-1">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-1/4 h-1/4 rounded-full bg-primary"
          animate={{
            y: [0, -8, 0],
            opacity: [0.5, 1, 0.5],
          }}
          transition={{
            duration: 0.8,
            repeat: Infinity,
            delay: i * 0.15,
          }}
        />
      ))}
    </div>
  ),
  'sending-message': (
    <div className="w-full h-full flex items-center justify-center">
      <motion.div
        animate={{ x: [-10, 10, -10] }}
        transition={{ duration: 1, repeat: Infinity, ease: 'easeInOut' }}
        className="w-1 h-1/2 rounded-full bg-primary"
      />
    </div>
  ),
  'typing-indicator': (
    <div className="w-full h-full flex items-center justify-center gap-1">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-1/4 h-1/4 rounded-full bg-muted-foreground"
          animate={{
            scaleY: [1, 2, 1],
          }}
          transition={{
            duration: 0.6,
            repeat: Infinity,
            delay: i * 0.1,
          }}
        />
      ))}
    </div>
  ),
  'confetti': (
    <div className="w-full h-full relative">
      {[...Array(20)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1 h-1 rounded-full"
          style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
            backgroundColor: ['#ff0', '#f00', '#0f0', '#00f', '#f0f'][Math.floor(Math.random() * 5)],
          }}
          initial={{ y: -10, opacity: 0 }}
          animate={{
            y: [null, 100, 100],
            opacity: [0, 1, 0],
          }}
          transition={{
            duration: 2 + Math.random(),
            delay: Math.random() * 0.5,
          }}
        />
      ))}
    </div>
  ),
  'rocket-launch': (
    <div className="w-full h-full flex items-center justify-center">
      <motion.svg
        initial={{ y: 4 }}
        animate={{ y: [-2, -6, -2] }}
        transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
        className="w-3/4 h-3/4 text-primary"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.63 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
      </motion.svg>
    </div>
  ),
  'file-upload': (
    <div className="w-full h-full flex items-center justify-center relative">
      <svg className="w-3/4 h-3/4 text-primary/30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v12m0 0l-3.75-3.75M12 15l3.75-3.75" />
      </svg>
      <motion.div
        className="absolute inset-0 flex items-center justify-center"
        animate={{ y: [0, -3, 0] }}
        transition={{ duration: 1.5, repeat: Infinity }}
      >
        <svg className="w-3/4 h-3/4 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v12" />
        </svg>
      </motion.div>
    </div>
  ),
  'ai-processing': (
    <div className="w-full h-full flex items-center justify-center">
      <motion.svg
        animate={{ rotate: 360 }}
        transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
        className="w-3/4 h-3/4 text-primary"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
      </motion.svg>
    </div>
  ),
};

/**
 * LottieAnimation 组件
 */
export const LottieAnimation: React.FC<LottieAnimationProps> = ({
  type,
  size = 24,
  className,
  loop = true,
  autoplay = true,
  onComplete,
}) => {
  const [animationData, setAnimationData] = useState<any>(null);

  useEffect(() => {
    // 尝试加载 Lottie JSON
    const url = ANIMATION_URLS[type];
    // 实际使用时可以从 URL 加载
    // 这里使用简化版动画
  }, [type]);

  // 使用简化版动画
  const simpleAnimation = SIMPLE_ANIMATIONS[type];

  return (
    <div
      className={cn('flex-shrink-0', className)}
      style={{ width: size, height: size }}
    >
      {simpleAnimation}
    </div>
  );
};

/**
 * 预设大小的动画组件
 */
export const LottieSpinner: React.FC<{ size?: number; className?: string }> = ({
  size = 24,
  className,
}) => <LottieAnimation type="loading-spinner" size={size} className={className} />;

export const LottieSuccess: React.FC<{ size?: number; className?: string }> = ({
  size = 24,
  className,
}) => <LottieAnimation type="success-check" size={size} className={className} />;

export const LottieError: React.FC<{ size?: number; className?: string }> = ({
  size = 24,
  className,
}) => <LottieAnimation type="error-x" size={size} className={className} />;

export const LottieThinking: React.FC<{ size?: number; className?: string }> = ({
  size = 24,
  className,
}) => <LottieAnimation type="thinking-dots" size={size} className={className} loop />;

export const LottieConfetti: React.FC<{ size?: number; className?: string }> = ({
  size = 24,
  className,
}) => <LottieAnimation type="confetti" size={size} className={className} loop={false} />;

export const LottieRocket: React.FC<{ size?: number; className?: string }> = ({
  size = 24,
  className,
}) => <LottieAnimation type="rocket-launch" size={size} className={className} loop />;

/**
 * 集成到 A2UI Button 的动画
 */
export const LottieButtonIcon: React.FC<{
  loading?: boolean;
  success?: boolean;
  error?: boolean;
  size?: number;
}> = ({ loading, success, error, size = 20 }) => {
  if (loading) return <LottieSpinner size={size} />;
  if (success) return <LottieSuccess size={size} />;
  if (error) return <LottieError size={size} />;
  return null;
};

/**
 * 默认导出
 */
export default LottieAnimation;
