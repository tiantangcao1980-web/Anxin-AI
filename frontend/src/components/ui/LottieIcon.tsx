import React, { Suspense, lazy, useState, useEffect } from 'react';

// 懒加载 Lottie 组件（减少首屏 bundle）
const Lottie = lazy(() => import('lottie-react'));

// 动画 JSON 文件动态导入（不再静态 import，减少首屏 ~200KB）
const ANIMATION_LOADERS: Record<string, () => Promise<{ default: unknown }>> = {
  loading: () => import('@/assets/animations/loading.json'),
  success: () => import('@/assets/animations/success.json'),
  empty: () => import('@/assets/animations/empty.json'),
  thinking: () => import('@/assets/animations/thinking.json'),
  searching: () => import('@/assets/animations/searching.json'),
  analyzing: () => import('@/assets/animations/searching.json'),
  error: () => import('@/assets/animations/success.json'),
};

export type LottieAnimationType = 'thinking' | 'success' | 'analyzing' | 'error' | 'loading' | 'empty' | 'searching';

interface LottieIconProps {
  type: LottieAnimationType;
  className?: string;
  loop?: boolean;
  autoplay?: boolean;
}

/**
 * LottieIcon - 统一 Lottie 动画组件
 *
 * 优先使用本地 JSON 动画，降级到 SVG 动画
 * 动画文件存放在 src/assets/animations/ 目录
 */
export const LottieIcon: React.FC<LottieIconProps> = ({
  type,
  className,
  loop = true,
  autoplay = true,
}) => {
  const [animationData, setAnimationData] = useState<unknown>(null);

  // 动态加载动画 JSON（仅在组件渲染时按需加载）
  useEffect(() => {
    const loader = ANIMATION_LOADERS[type];
    if (loader) {
      loader().then(mod => setAnimationData(mod.default)).catch(() => {});
    }
  }, [type]);

  // 有 Lottie 数据时使用 Lottie 渲染
  if (animationData) {
    return (
      <Suspense fallback={<FallbackAnimation type={type} className={className} />}>
        <Lottie
          animationData={animationData}
          loop={type === 'success' || type === 'error' ? false : loop}
          autoplay={autoplay}
          className={className}
        />
      </Suspense>
    );
  }

  // 加载中或无数据时降级到 SVG 动画
  return <FallbackAnimation type={type} className={className} />;
};

/**
 * SVG 降级动画 — 当 Lottie JSON 加载失败或不可用时使用
 */
const FallbackAnimation: React.FC<{ type: string; className?: string }> = ({ type, className }) => {
  if (type === 'thinking') {
    return (
      <div className={`flex items-center justify-center gap-1 ${className}`}>
        <span className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]" />
        <span className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]" />
        <span className="w-2 h-2 bg-primary rounded-full animate-bounce" />
      </div>
    );
  }

  if (type === 'success') {
    return (
      <div className={`text-emerald-600 dark:text-emerald-400 ${className}`}>
        <svg className="w-full h-full" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
        </svg>
      </div>
    );
  }

  if (type === 'error') {
    return (
      <div className={`text-destructive ${className}`}>
        <svg className="w-full h-full" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
        </svg>
      </div>
    );
  }

  // loading / analyzing / searching / empty 的通用降级
  return (
    <div className={`text-muted-foreground ${className}`}>
      <svg className="w-full h-full animate-spin" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    </div>
  );
};
