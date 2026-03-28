/**
 * A2UI 组件系统 - Barrel Export
 */

// 核心渲染引擎
export { A2UIRenderer } from './A2UIRenderer';
export { StreamingA2UIRenderer, CardSkeleton, SkeletonList, useStreamingA2UI } from './StreamingA2UIRenderer';
export { MobileA2UIAdapter } from './MobileA2UIAdapter';

// 类型
export type {
  A2UIMessage,
  A2UIComponent,
  A2UIEvent,
  A2UIEventHandler,
  RecommendationCardComponent,
  LawyerCardComponent,
  HorizontalScrollComponent,
  FormSheetComponent,
  FormSection,
  FormOption,
  OrderCardComponent,
  ActionBarComponent,
  InfoBannerComponent,
  ButtonGroupComponent,
  StatusCardComponent,
  DetailListComponent,
  ProgressStepsComponent,
  RiskIndicatorComponent,
  TextBlockComponent,
  DividerComponent,
  ServiceSelectionComponent,
  ContractPreviewComponent,
  ContractCompareComponent,
  FeeEstimateComponent,
  CaseProgressComponent,
  RiskAssessmentComponent,
  A2UIStreamEvent,
} from './types';

// 组件（按需导入）
export { RecommendationCard } from './components/RecommendationCard';
export { LawyerCard } from './components/LawyerCard';
export { HorizontalScroll } from './components/HorizontalScroll';
export { FormSheet } from './components/FormSheet';
export { OrderCard } from './components/OrderCard';
export { ActionBar } from './components/ActionBar';
export { InfoBanner } from './components/InfoBanner';
export { ButtonGroup } from './components/ButtonGroup';
export { StatusCard } from './components/StatusCard';
export { DetailList } from './components/DetailList';
export { ProgressSteps } from './components/ProgressSteps';
export { RiskIndicator } from './components/RiskIndicator';
export { TextBlock } from './components/TextBlock';
export { A2UIDivider } from './components/A2UIDivider';
export { ServiceSelection } from './components/ServiceSelection';
export { ContractPreview } from './components/ContractPreview';
export { ContractCompareCard } from './components/ContractCompareCard';
export { FeeEstimateCard } from './components/FeeEstimateCard';
export { CaseProgressCard } from './components/CaseProgressCard';
export { RiskAssessmentCard } from './components/RiskAssessmentCard';

// 移动端千问风格组件
export {
  CollapsibleCard,
  HorizontalSwipeList,
  BottomActionBar,
  FullWidthCard,
} from './components/MobileCardWrapper';
