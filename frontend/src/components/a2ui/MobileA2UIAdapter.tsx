/**
 * MobileA2UIAdapter — 移动端千问风格 A2UI 适配层
 * 
 * 核心职责：
 * 1. 全宽卡片布局：移动端卡片占满屏幕宽度
 * 2. 水平滑动分组：连续同类型卡片（如律师卡）自动合并为横向轮播
 * 3. 底部操作栏集成：从卡片中提取操作按钮，固定在底部
 * 4. 卡片自动折叠：历史消息中的 A2UI 卡片自动折叠为摘要
 * 5. 流式骨架屏适配：StreamingA2UIRenderer 在移动端适配全宽
 * 
 * 使用方式：
 *   在移动端替代 <A2UIRenderer> 使用 <MobileA2UIAdapter>
 *   自动检测并应用上述移动端增强
 */

import { memo, useMemo, useState, useCallback, type ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { A2UIMessage, A2UIComponent, A2UIEvent, A2UIEventHandler } from './types';
import { A2UIRenderer } from './A2UIRenderer';
import { CollapsibleCard, HorizontalSwipeList, BottomActionBar, FullWidthCard } from './components/MobileCardWrapper';
import { cn } from '@/lib/utils';

// ========== 可分组的卡片类型 ==========

/** 可以横向滑动分组的卡片类型 */
const SWIPEABLE_TYPES = new Set([
  'lawyer-card',
  'recommendation-card',
  'service-selection',
]);

/** 带操作按钮的卡片类型（actions 字段可提取到底部栏） */
const ACTIONABLE_TYPES = new Set([
  'lawyer-card',
  'recommendation-card',
  'order-card',
  'contract-compare',
  'fee-estimate',
  'case-progress',
  'risk-assessment',
  'form-sheet',
]);

// ========== 辅助函数 ==========

/** 将连续同类型的卡片分组 */
function groupComponents(components: A2UIComponent[]): Array<{
  type: 'single' | 'swipe-group';
  components: A2UIComponent[];
}> {
  const groups: Array<{
    type: 'single' | 'swipe-group';
    components: A2UIComponent[];
  }> = [];

  let i = 0;
  while (i < components.length) {
    const comp = components[i];

    // 检查是否可分组
    if (SWIPEABLE_TYPES.has(comp.type)) {
      // 收集连续同类型的组件
      const group: A2UIComponent[] = [comp];
      let j = i + 1;
      while (j < components.length && components[j].type === comp.type) {
        group.push(components[j]);
        j++;
      }
      
      if (group.length > 1) {
        groups.push({ type: 'swipe-group', components: group });
      } else {
        groups.push({ type: 'single', components: [comp] });
      }
      i = j;
    } else {
      groups.push({ type: 'single', components: [comp] });
      i++;
    }
  }

  return groups;
}

/** 从组件中提取操作按钮 */
function extractActions(components: A2UIComponent[]): Array<{
  id: string;
  label: string;
  variant?: 'primary' | 'secondary' | 'outline' | 'destructive';
  onClick: () => void;
}> {
  const actions: Array<{
    id: string;
    label: string;
    variant?: 'primary' | 'secondary' | 'outline' | 'destructive';
    onClick: () => void;
  }> = [];

  for (const comp of components) {
    if (!ACTIONABLE_TYPES.has(comp.type)) continue;
    const data = (comp as any).data;
    if (!data?.actions) continue;

    for (const action of data.actions) {
      if (action.label && action.actionId) {
        actions.push({
          id: `${comp.id}-${action.actionId}`,
          label: action.label,
          variant: action.variant || 'primary',
          onClick: () => {}, // 占位，实际事件通过 onEvent 触发
        });
      }
    }
  }

  return actions;
}

/** 为卡片生成折叠摘要 */
function getCardSummary(components: A2UIComponent[]): string {
  if (components.length === 0) return '查看详情';
  
  const first = components[0];
  const data = (first as any).data;
  
  switch (first.type) {
    case 'lawyer-card':
      return data?.name ? `律师推荐: ${data.name}` : '律师推荐卡片';
    case 'recommendation-card':
      return data?.title || '推荐方案';
    case 'contract-compare':
      return data?.title || '合同对比分析';
    case 'fee-estimate':
      return data?.title || '费用估算';
    case 'case-progress':
      return data?.title ? `案件进度: ${data.title}` : '案件进度';
    case 'risk-assessment':
      return data?.title || '风险评估';
    case 'order-card':
      return data?.title || '服务订单';
    case 'form-sheet':
      return data?.title || '信息表单';
    default:
      return `${components.length} 个组件`;
  }
}

// ========== 主组件 ==========

interface MobileA2UIAdapterProps {
  /** A2UI 消息数据 */
  message: A2UIMessage;
  /** 事件处理器 */
  onEvent: A2UIEventHandler;
  /** 是否为历史消息（自动折叠） */
  isHistorical?: boolean;
  /** 附加类名 */
  className?: string;
  /** 是否显示底部操作栏 */
  showBottomBar?: boolean;
}

export const MobileA2UIAdapter = memo(function MobileA2UIAdapter({
  message,
  onEvent,
  isHistorical = false,
  className,
  showBottomBar = true,
}: MobileA2UIAdapterProps) {
  const [expanded, setExpanded] = useState(!isHistorical);

  const components = message.components || [];

  // 分组处理
  const groups = useMemo(() => groupComponents(components), [components]);

  // 提取底部操作
  const bottomActions = useMemo(() => {
    if (!showBottomBar) return [];
    return extractActions(components).slice(0, 3); // 最多 3 个按钮
  }, [components, showBottomBar]);

  // 底部操作栏的 actions — 需要绑定 onEvent
  const actionBarActions = useMemo(() => {
    return bottomActions.map((action) => ({
      ...action,
      onClick: () => {
        // 解析出 componentId 和 actionId
        const parts = action.id.split('-');
        const actionId = parts.pop() || '';
        const componentId = parts.join('-');
        onEvent({
          type: 'action',
          componentId,
          actionId,
          payload: {},
        });
      },
    }));
  }, [bottomActions, onEvent]);

  // 折叠摘要
  const summary = useMemo(() => getCardSummary(components), [components]);

  if (components.length === 0) return null;

  // === 历史消息：自动折叠模式 ===
  if (isHistorical) {
    return (
      <div className={cn('mobile-a2ui-collapsed', className)}>
        <CollapsibleCard
          title={summary}
          subtitle={`${components.length} 个卡片`}
          defaultCollapsed={true}
          preview={
            <p className="text-xs text-muted-foreground line-clamp-1">
              点击展开查看完整内容
            </p>
          }
        >
          <div className="space-y-3">
            {groups.map((group, gIdx) => (
              <MobileGroupRenderer
                key={`g-${gIdx}`}
                group={group}
                onEvent={onEvent}
              />
            ))}
          </div>
        </CollapsibleCard>
      </div>
    );
  }

  // === 当前消息：全宽卡片 + 横向滑动 ===
  return (
    <div className={cn('mobile-a2ui-adapter space-y-3', className)}>
      {groups.map((group, gIdx) => (
        <motion.div
          key={`g-${gIdx}`}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: gIdx * 0.1, duration: 0.3 }}
        >
          <MobileGroupRenderer group={group} onEvent={onEvent} />
        </motion.div>
      ))}

      {/* 底部操作栏 */}
      <AnimatePresence>
        {actionBarActions.length > 0 && (
          <BottomActionBar actions={actionBarActions} />
        )}
      </AnimatePresence>
    </div>
  );
});

// ========== 分组渲染器 ==========

const MobileGroupRenderer = memo(function MobileGroupRenderer({
  group,
  onEvent,
}: {
  group: { type: 'single' | 'swipe-group'; components: A2UIComponent[] };
  onEvent: A2UIEventHandler;
}) {
  if (group.type === 'swipe-group') {
    // 横向滑动卡片列表
    return (
      <HorizontalSwipeList showDots gap={12}>
        {group.components.map((comp) => (
          <FullWidthCard key={comp.id}>
            <SingleComponentRenderer component={comp} onEvent={onEvent} />
          </FullWidthCard>
        ))}
      </HorizontalSwipeList>
    );
  }

  // 单个卡片 — 全宽
  const comp = group.components[0];
  return (
    <FullWidthCard>
      <SingleComponentRenderer component={comp} onEvent={onEvent} />
    </FullWidthCard>
  );
});

// ========== 单组件渲染（委托给 A2UIRenderer） ==========

const SingleComponentRenderer = memo(function SingleComponentRenderer({
  component,
  onEvent,
}: {
  component: A2UIComponent;
  onEvent: A2UIEventHandler;
}) {
  // 构造只有一个组件的 A2UIMessage
  const message: A2UIMessage = useMemo(() => ({
    id: component.id || 'single',
    components: [component],
  }), [component]);

  return (
    <A2UIRenderer
      message={message}
      onEvent={onEvent}
      animated={false}
    />
  );
});

export default MobileA2UIAdapter;
