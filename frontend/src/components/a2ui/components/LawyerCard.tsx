/**
 * 律师推荐卡片（专用）
 * 展示律师详细信息：头像、评分、专长、胜诉率、咨询费等
 */

import { memo } from 'react';
import { icons } from '@/lib/icons';
import type { LawyerCardComponent, A2UIEventHandler } from '../types';
import { cn } from '@/lib/utils';

interface Props {
  component: LawyerCardComponent;
  onEvent: A2UIEventHandler;
}

const statusMap = {
  online: { label: '在线', color: 'bg-emerald-500' },
  busy: { label: '忙碌', color: 'bg-amber-500' },
  offline: { label: '离线', color: 'bg-muted-foreground/70' },
};

export const LawyerCard = memo(function LawyerCard({ component, onEvent }: Props) {
  const { data } = component;
  const statusInfo = statusMap[data.status];

  const handleAction = () => {
    if (data.action) {
      onEvent({
        type: 'action',
        actionId: data.action.actionId,
        componentId: component.id,
        payload: { lawyerId: data.lawyerId, ...data.action.payload },
      });
    }
  };

  return (
    <div className={cn(
      'a2ui-lawyer-card',
      'bg-background rounded-2xl border border-border/50',
      'shadow-sm hover:shadow-md transition-all duration-200',
      'p-4',
      component.className,
    )}>
      {/* 头部：头像 + 基本信息 */}
      <div className="flex gap-3">
        {/* 头像 */}
        <div className="relative flex-shrink-0">
          <div className="w-14 h-14 rounded-full bg-primary/10 dark:bg-primary/20 flex items-center justify-center overflow-hidden">
            {data.avatar ? (
              <img src={data.avatar} alt={data.name} className="w-full h-full object-cover" />
            ) : (
              <span className="text-xl font-bold text-primary dark:text-primary">
                {data.name.charAt(0)}
              </span>
            )}
          </div>
          {/* 在线状态指示器 */}
          <div className={cn(
            'absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full border-2 border-background',
            statusInfo.color,
          )} />
        </div>

        {/* 信息 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="font-semibold text-sm text-foreground">
              {data.name}
            </h4>
            {data.title && (
              <span className="text-[10px] bg-primary/5 text-primary dark:bg-primary/10 dark:text-primary px-1.5 py-0.5 rounded-full">
                {data.title}
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {data.firm}
          </p>

          {/* 评分 */}
          <div className="flex items-center gap-3 mt-1.5">
            <div className="flex items-center gap-0.5">
              <icons.Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
              <span className="text-xs font-medium text-foreground">
                {data.rating.toFixed(1)}
              </span>
            </div>
            {data.winRate && (
              <div className="flex items-center gap-1">
                <icons.Trophy className="w-3 h-3 text-emerald-600" />
                <span className="text-xs text-muted-foreground">
                  胜诉率 {data.winRate}
                </span>
              </div>
            )}
            {data.experience && (
              <span className="text-xs text-muted-foreground/70">
                {data.experience}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* 专长标签 */}
      <div className="flex flex-wrap gap-1.5 mt-3">
        {data.specialties.map((specialty, i) => (
          <span
            key={i}
            className="inline-flex items-center px-2.5 py-1 rounded-lg text-[11px] font-medium bg-muted/50 text-muted-foreground"
          >
            {specialty}
          </span>
        ))}
      </div>

      {/* 简介 */}
      {data.introduction && (
        <p className="text-xs text-muted-foreground mt-2.5 leading-relaxed line-clamp-2">
          {data.introduction}
        </p>
      )}

      {/* 底部信息 + 操作 */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border/50">
        <div className="flex items-center gap-3">
          {data.responseTime && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground/70">
              <icons.Clock className="w-3 h-3" />
              {data.responseTime}
            </div>
          )}
          {data.consultFee && (
            <span className="text-sm font-semibold text-orange-600 dark:text-orange-400">
              ¥{data.consultFee.amount}
              <span className="text-xs font-normal text-muted-foreground/70">
                /{data.consultFee.unit || '次'}
              </span>
            </span>
          )}
        </div>

        {data.action && (
          <button
            onClick={handleAction}
            disabled={data.status === 'offline'}
            className={cn(
              'inline-flex items-center gap-1.5 px-5 py-2 rounded-full text-xs font-medium transition-all',
              data.status === 'offline'
                ? 'bg-muted text-muted-foreground/70 cursor-not-allowed'
                : 'bg-primary text-white hover:bg-primary/90 active:scale-95',
            )}
          >
            <icons.Phone className="w-3.5 h-3.5" />
            {data.action.label}
          </button>
        )}
      </div>
    </div>
  );
});
