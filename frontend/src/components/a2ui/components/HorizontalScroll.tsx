/**
 * 横向滚动列表
 * 类似千问的多商品横滑推荐列表
 */

import { memo, useRef, useState, useCallback } from 'react';
import { icons } from '@/lib/icons';
import type { HorizontalScrollComponent, A2UIEventHandler } from '../types';
import { cn } from '@/lib/utils';

// 内部组件渲染器（避免循环依赖，直接用简化版）
import { RecommendationCard } from './RecommendationCard';
import { LawyerCard } from './LawyerCard';

interface Props {
  component: HorizontalScrollComponent;
  onEvent: A2UIEventHandler;
}

function renderItem(item: any, onEvent: A2UIEventHandler) {
  switch (item.type) {
    case 'recommendation-card':
      return <RecommendationCard component={item} onEvent={onEvent} />;
    case 'lawyer-card':
      return <LawyerCard component={item} onEvent={onEvent} />;
    default:
      return null;
  }
}

export const HorizontalScroll = memo(function HorizontalScroll({ component, onEvent }: Props) {
  const { data } = component;
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(true);

  const updateScrollState = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 4);
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 4);
  }, []);

  const scroll = (direction: 'left' | 'right') => {
    const el = scrollRef.current;
    if (!el) return;
    const amount = el.clientWidth * 0.8;
    el.scrollBy({ left: direction === 'left' ? -amount : amount, behavior: 'smooth' });
    setTimeout(updateScrollState, 350);
  };

  return (
    <div className={cn('a2ui-horizontal-scroll relative group', component.className)}>
      {/* 标题 */}
      {data.title && (
        <h3 className="text-sm font-semibold text-foreground mb-2 px-1">
          {data.title}
        </h3>
      )}

      {/* 滚动容器 */}
      <div className="relative">
        {/* 左箭头 */}
        {data.showArrows !== false && canScrollLeft && (
          <button
            onClick={() => scroll('left')}
            className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-8 h-8 rounded-full bg-background/90 shadow-lg flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <icons.ChevronLeft className="w-4 h-4 text-muted-foreground" />
          </button>
        )}

        {/* 右箭头 */}
        {data.showArrows !== false && canScrollRight && (
          <button
            onClick={() => scroll('right')}
            className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-8 h-8 rounded-full bg-background/90 shadow-lg flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <icons.ChevronRight className="w-4 h-4 text-muted-foreground" />
          </button>
        )}

        {/* 滚动列表 */}
        <div
          ref={scrollRef}
          onScroll={updateScrollState}
          className="flex gap-3 overflow-x-auto scrollbar-hide snap-x snap-mandatory pb-2"
          style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
        >
          {data.items.map((item, index) => (
            <div
              key={item.id || `item-${index}`}
              className="flex-shrink-0 snap-start"
              style={{ width: data.visibleCount ? `calc(${100 / data.visibleCount}% - ${(data.visibleCount - 1) * 12 / data.visibleCount}px)` : '280px' }}
            >
              {renderItem(item, onEvent)}
            </div>
          ))}
        </div>

        {/* 渐变遮罩 */}
        {canScrollRight && (
          <div className="absolute right-0 top-0 bottom-2 w-8 bg-gradient-to-l from-background dark:from-background pointer-events-none" />
        )}
      </div>
    </div>
  );
});
