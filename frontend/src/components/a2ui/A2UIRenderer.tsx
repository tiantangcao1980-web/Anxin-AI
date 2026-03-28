/**
 * A2UI 渲染引擎
 * 
 * 接收 A2UIMessage JSON → 遍历 components → 分发到对应 React 组件
 * 支持事件冒泡回传给 Agent
 */

import { memo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { A2UIMessage, A2UIComponent, A2UIEvent, A2UIEventHandler } from './types';
import { RecommendationCard } from './components/RecommendationCard';
import { LawyerCard } from './components/LawyerCard';
import { HorizontalScroll } from './components/HorizontalScroll';
import { FormSheet } from './components/FormSheet';
import { OrderCard } from './components/OrderCard';
import { ActionBar } from './components/ActionBar';
import { InfoBanner } from './components/InfoBanner';
import { ButtonGroup } from './components/ButtonGroup';
import { StatusCard } from './components/StatusCard';
import { DetailList } from './components/DetailList';
import { ProgressSteps } from './components/ProgressSteps';
import { RiskIndicator } from './components/RiskIndicator';
import { TextBlock } from './components/TextBlock';
import { A2UIDivider } from './components/A2UIDivider';
import { ServiceSelection } from './components/ServiceSelection';
import { ContractPreview } from './components/ContractPreview';
import { ContractCompareCard } from './components/ContractCompareCard';
import { FeeEstimateCard } from './components/FeeEstimateCard';
import { CaseProgressCard } from './components/CaseProgressCard';
import { RiskAssessmentCard } from './components/RiskAssessmentCard';
import {
  MapView, PaymentCard, LawyerPicker, MediaCard,
  SchedulePicker, FeedbackCard, PluginContainer,
} from './components/ExtensionComponents';
import { FullWidthCard } from './components/MobileCardWrapper';
import { cn } from '@/lib/utils';

/** 需要在移动端使用全宽包裹的组件类型 */
const MOBILE_FULLWIDTH_TYPES = new Set([
  'recommendation-card', 'lawyer-card', 'form-sheet', 'order-card',
  'status-card', 'detail-list', 'contract-preview', 'contract-compare',
  'fee-estimate', 'case-progress', 'risk-assessment', 'service-selection',
]);

interface A2UIRendererProps {
  /** A2UI 消息数据 */
  message: A2UIMessage;
  /** 事件处理器 */
  onEvent: A2UIEventHandler;
  /** 附加类名 */
  className?: string;
  /** 是否启用动画 */
  animated?: boolean;
  /** 移动端模式 — 启用全宽卡片、可折叠等千问风格包裹 */
  isMobile?: boolean;
}

/** 单个组件的渲染分发 */
const ComponentRenderer = memo(function ComponentRenderer({
  component,
  onEvent,
}: {
  component: A2UIComponent;
  onEvent: A2UIEventHandler;
}) {
  if (component.visible === false) return null;

  switch (component.type) {
    case 'recommendation-card':
      return <RecommendationCard component={component} onEvent={onEvent} />;
    case 'lawyer-card':
      return <LawyerCard component={component} onEvent={onEvent} />;
    case 'horizontal-scroll':
      return <HorizontalScroll component={component} onEvent={onEvent} />;
    case 'form-sheet':
      return <FormSheet component={component} onEvent={onEvent} />;
    case 'order-card':
      return <OrderCard component={component} onEvent={onEvent} />;
    case 'action-bar':
      return <ActionBar component={component} onEvent={onEvent} />;
    case 'info-banner':
      return <InfoBanner component={component} onEvent={onEvent} />;
    case 'button-group':
      return <ButtonGroup component={component} onEvent={onEvent} />;
    case 'status-card':
      return <StatusCard component={component} onEvent={onEvent} />;
    case 'detail-list':
      return <DetailList component={component} onEvent={onEvent} />;
    case 'progress-steps':
      return <ProgressSteps component={component} onEvent={onEvent} />;
    case 'risk-indicator':
      return <RiskIndicator component={component} onEvent={onEvent} />;
    case 'text-block':
      return <TextBlock component={component} onEvent={onEvent} />;
    case 'divider':
      return <A2UIDivider component={component} />;
    case 'service-selection':
      return <ServiceSelection component={component} onEvent={onEvent} />;
    case 'contract-preview':
      return <ContractPreview component={component} onEvent={onEvent} />;
    // === 法务专用卡片 ===
    case 'contract-compare':
      return <ContractCompareCard component={component as any} onEvent={onEvent} />;
    case 'fee-estimate':
      return <FeeEstimateCard component={component as any} onEvent={onEvent} />;
    case 'case-progress':
      return <CaseProgressCard component={component as any} onEvent={onEvent} />;
    case 'risk-assessment':
      return <RiskAssessmentCard component={component as any} onEvent={onEvent} />;
    // === 扩展接口组件 ===
    case 'map-view':
      return <MapView component={component as any} onEvent={onEvent} />;
    case 'payment-card':
      return <PaymentCard component={component as any} onEvent={onEvent} />;
    case 'lawyer-picker':
      return <LawyerPicker component={component as any} onEvent={onEvent} />;
    case 'media-card':
      return <MediaCard component={component as any} onEvent={onEvent} />;
    case 'schedule-picker':
      return <SchedulePicker component={component as any} onEvent={onEvent} />;
    case 'feedback-card':
      return <FeedbackCard component={component as any} onEvent={onEvent} />;
    case 'plugin-container':
      return <PluginContainer component={component as any} onEvent={onEvent} />;
    default:
      console.warn('[A2UI] Unknown component type:', (component as any).type);
      return null;
  }
});

/** A2UI 渲染引擎主组件 */
export const A2UIRenderer = memo(function A2UIRenderer({
  message,
  onEvent,
  className,
  animated = true,
  isMobile = false,
}: A2UIRendererProps) {
  const handleEvent = useCallback(
    (event: A2UIEvent) => {
      // 检查是否过期
      if (message.metadata?.expiresAt && Date.now() > message.metadata.expiresAt) {
        console.warn('[A2UI] Message expired, ignoring event');
        return;
      }
      onEvent(event);
    },
    [message.metadata?.expiresAt, onEvent]
  );

  if (!message.components || message.components.length === 0) return null;

  const wrapMobile = (node: React.ReactNode, component: A2UIComponent) => {
    if (!isMobile || !MOBILE_FULLWIDTH_TYPES.has(component.type)) return node;
    return <FullWidthCard flush>{node}</FullWidthCard>;
  };

  const content = (
    <div className={cn('a2ui-message space-y-3', isMobile && 'space-y-2', className)}>
      {message.components.map((component, index) => (
        animated ? (
          <motion.div
            key={component.id || `comp-${index}`}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.08, duration: 0.3, ease: 'easeOut' }}
          >
            {wrapMobile(<ComponentRenderer component={component} onEvent={handleEvent} />, component)}
          </motion.div>
        ) : (
          <div key={component.id || `comp-${index}`}>
            {wrapMobile(<ComponentRenderer component={component} onEvent={handleEvent} />, component)}
          </div>
        )
      ))}
    </div>
  );

  if (animated) {
    return (
      <AnimatePresence mode="wait">
        {content}
      </AnimatePresence>
    );
  }

  return content;
});

export default A2UIRenderer;
