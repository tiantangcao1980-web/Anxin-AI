/**
 * A2UI Components - 组件导出
 */

// Button
export {
  A2UIButton,
  type A2UIButtonProps,
  type ButtonVariant,
  type ButtonSize
} from './A2UIButton';

// Card
export {
  A2UICard,
  A2UICardHeader,
  A2UICardContent,
  A2UICardFooter,
  type A2UICardProps,
  type CardVariant
} from './A2UICard';

// TypingIndicator
export {
  A2UITypingIndicator,
  A2UITypingDots,
  type A2UITypingIndicatorProps,
  type TypingAnimation
} from './A2UITypingIndicator';

// Input
export {
  A2UIInput,
  type A2UIInputProps,
  type InputVariant,
  type InputSize
} from './A2UIInput';

// Alert
export {
  A2UIAlert,
  A2UIAlertGroup,
  type A2UIAlertProps,
  type AlertType
} from './A2UIAlert';

// 法务专用卡片
export { ContractCompareCard } from './ContractCompareCard';
export { FeeEstimateCard } from './FeeEstimateCard';
export { LawyerCard } from './LawyerCard';

// 法律条款分析卡片
export { LegalClauseCard, type LegalClauseCardProps } from './LegalClauseCard';
// AI 案件分析卡片
export { CaseAnalysisCard, type CaseAnalysisCardProps } from './CaseAnalysisCard';
// 风险矩阵卡片
export { RiskMatrixCard, type RiskMatrixCardProps, type RiskItem } from './RiskMatrixCard';

// 移动端千问风格组件
export {
  CollapsibleCard,
  HorizontalSwipeList,
  BottomActionBar,
  FullWidthCard,
} from './MobileCardWrapper';
