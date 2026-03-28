/**
 * 分隔线组件
 */

import { memo } from 'react';
import type { DividerComponent } from '../types';
import { cn } from '@/lib/utils';

interface Props {
  component: DividerComponent;
}

export const A2UIDivider = memo(function A2UIDivider({ component }: Props) {
  const label = component.data?.label;

  if (label) {
    return (
      <div className={cn('a2ui-divider flex items-center gap-3 py-2', component.className)}>
        <div className="flex-1 h-px bg-border" />
        <span className="text-[10px] text-muted-foreground/70 font-medium">{label}</span>
        <div className="flex-1 h-px bg-border" />
      </div>
    );
  }

  return (
    <div className={cn('a2ui-divider py-2', component.className)}>
      <div className="h-px bg-border" />
    </div>
  );
});
