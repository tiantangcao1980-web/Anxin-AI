/**
 * A2UI 协议类型定义 (Agent-to-UI Protocol)
 * 
 * 灵感来源：Google A2UI + 千问 v2.0 移动端交互模式
 * AI Agent 返回 JSON 描述 → 前端用原生 React 组件渲染
 * 
 * 核心理念：
 * 1. AI 只描述 "要展示什么"（声明式 JSON）
 * 2. 前端决定 "怎么渲染"（原生组件）
 * 3. 用户交互结果回传给 Agent（事件回调）
 */

// ========== 顶层协议 ==========

/** A2UI 消息：包含一组要渲染的组件 */
export interface A2UIMessage {
  /** 消息唯一ID */
  id: string;
  /** 组件列表（按顺序渲染） */
  components: A2UIComponent[];
  /** 消息级元数据 */
  metadata?: {
    /** 来源Agent */
    agent?: string;
    /** 是否可折叠 */
    collapsible?: boolean;
    /** 过期时间（毫秒时间戳） */
    expiresAt?: number;
  };
}

/** 所有组件的联合类型 */
export type A2UIComponent =
  | RecommendationCardComponent
  | HorizontalScrollComponent
  | FormSheetComponent
  | OrderCardComponent
  | ActionBarComponent
  | InfoBannerComponent
  | ButtonGroupComponent
  | StatusCardComponent
  | DetailListComponent
  | ProgressStepsComponent
  | RiskIndicatorComponent
  | TextBlockComponent
  | DividerComponent
  | LawyerCardComponent
  | ServiceSelectionComponent
  | ContractPreviewComponent
  // === 法务专用卡片 ===
  | ContractCompareComponent
  | FeeEstimateComponent
  | CaseProgressComponent
  | RiskAssessmentComponent
  // === 扩展接口组件 ===
  | MapViewComponent
  | PaymentCardComponent
  | LawyerPickerComponent
  | MediaCardComponent
  | SchedulePickerComponent
  | FeedbackCardComponent
  | PluginContainerComponent;

/** 组件基础接口 */
interface BaseComponent {
  /** 组件实例ID */
  id: string;
  /** 组件类型标识 */
  type: string;
  /** 是否可见（默认true） */
  visible?: boolean;
  /** 自定义样式类名 */
  className?: string;
}

// ========== 推荐卡片 ==========

/** 推荐卡片：用于律师推荐、服务推荐、法条推荐等 */
export interface RecommendationCardComponent extends BaseComponent {
  type: 'recommendation-card';
  data: {
    /** 标题 */
    title: string;
    /** 副标题 */
    subtitle?: string;
    /** 描述 */
    description?: string;
    /** 图片URL */
    image?: string;
    /** 图片占位符（首字母/图标） */
    imageFallback?: string;
    /** 评分（0-5） */
    rating?: number;
    /** 评分文本（如 "4.9分"） */
    ratingText?: string;
    /** 标签列表 */
    tags?: { label: string; color?: string }[];
    /** 距离/时间等附加信息 */
    meta?: string;
    /** 价格 */
    price?: { amount: number; currency?: string; label?: string; original?: number };
    /** 详情列表 */
    details?: { label: string; value: string }[];
    /** 操作按钮 */
    action?: {
      label: string;
      actionId: string;
      variant?: 'primary' | 'secondary' | 'outline';
      payload?: Record<string, any>;
    };
    /** 附加操作 */
    secondaryAction?: {
      label: string;
      actionId: string;
      payload?: Record<string, any>;
    };
  };
}

// ========== 律师卡片（专用） ==========

/** 律师卡片：比通用推荐卡片更丰富 */
export interface LawyerCardComponent extends BaseComponent {
  type: 'lawyer-card';
  data: {
    lawyerId: string;
    name: string;
    avatar?: string;
    firm: string;
    title?: string;
    specialties: string[];
    rating: number;
    casesWon?: number;
    totalCases?: number;
    winRate?: string;
    experience?: string;
    responseTime?: string;
    consultFee?: { amount: number; unit?: string };
    status: 'online' | 'busy' | 'offline';
    introduction?: string;
    action?: {
      label: string;
      actionId: string;
      payload?: Record<string, any>;
    };
  };
}

// ========== 横滑列表 ==========

/** 横向滚动列表：包裹多个卡片 */
export interface HorizontalScrollComponent extends BaseComponent {
  type: 'horizontal-scroll';
  data: {
    /** 标题 */
    title?: string;
    /** 子项组件 */
    items: A2UIComponent[];
    /** 是否显示翻页箭头 */
    showArrows?: boolean;
    /** 每屏显示数量（桌面端） */
    visibleCount?: number;
  };
}

// ========== 表单 Sheet ==========

/** 底部弹出表单：用于服务定制、信息收集 */
export interface FormSheetComponent extends BaseComponent {
  type: 'form-sheet';
  data: {
    /** 标题 */
    title: string;
    /** 副标题 */
    subtitle?: string;
    /** 表单头部（摘要信息） */
    header?: {
      image?: string;
      title: string;
      subtitle?: string;
      price?: { amount: number; original?: number };
    };
    /** 表单分区 */
    sections: FormSection[];
    /** 提交按钮 */
    submitAction: {
      label: string;
      actionId: string;
      variant?: 'primary' | 'secondary';
    };
    /** 取消按钮 */
    cancelAction?: {
      label: string;
      actionId: string;
    };
    /** 是否以 Sheet（底部弹出）方式展示 */
    asSheet?: boolean;
    /** Sheet 初始高度百分比 */
    sheetHeight?: number;
  };
}

/** 表单分区 */
export interface FormSection {
  id: string;
  label: string;
  description?: string;
  type: 'single-select' | 'multi-select' | 'text-input' | 'date-picker' | 'file-upload' | 'textarea';
  required?: boolean;
  options?: FormOption[];
  defaultValue?: any;
  placeholder?: string;
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
    message?: string;
  };
}

/** 表单选项 */
export interface FormOption {
  id: string;
  label: string;
  description?: string;
  icon?: string;
  disabled?: boolean;
  disabledReason?: string;
  price?: { amount: number; label?: string };
}

// ========== 服务选择（专用） ==========

/** 服务选择组件：用于选择法律服务类型 */
export interface ServiceSelectionComponent extends BaseComponent {
  type: 'service-selection';
  data: {
    title: string;
    subtitle?: string;
    services: {
      id: string;
      name: string;
      icon?: string;
      description: string;
      features: string[];
      price?: { amount: number; unit?: string; label?: string };
      popular?: boolean;
      actionId: string;
    }[];
  };
}

// ========== 订单/委托确认卡片 ==========

/** 订单确认卡片：用于委托确认、服务确认 */
export interface OrderCardComponent extends BaseComponent {
  type: 'order-card';
  data: {
    /** 标题 */
    title?: string;
    /** 主要商品/服务信息 */
    item: {
      image?: string;
      title: string;
      subtitle?: string;
      specs?: string;
      quantity?: number;
      price?: { amount: number; original?: number };
    };
    /** 详情列表（如送达时间、地址等） */
    details: { label: string; value: string; editable?: boolean; editActionId?: string }[];
    /** 费用明细 */
    pricing?: {
      items: { label: string; amount: number; original?: number; type?: 'add' | 'subtract' | 'info' }[];
      total: { label: string; amount: number };
    };
    /** 操作区 */
    actions: {
      label: string;
      actionId: string;
      variant?: 'primary' | 'secondary' | 'outline' | 'warning';
      payload?: Record<string, any>;
      fullWidth?: boolean;
    }[];
    /** 提示/备注 */
    note?: string;
  };
}

// ========== 合同预览卡片 ==========

/** 合同预览：用于展示待签署的合同概要 */
export interface ContractPreviewComponent extends BaseComponent {
  type: 'contract-preview';
  data: {
    contractId: string;
    title: string;
    type: string;
    parties: { name: string; role: string }[];
    keyTerms: { label: string; value: string }[];
    riskLevel: 'low' | 'medium' | 'high';
    riskItems?: { level: 'low' | 'medium' | 'high'; description: string }[];
    actions: {
      label: string;
      actionId: string;
      variant?: 'primary' | 'secondary' | 'outline';
    }[];
  };
}

// ========== 快捷操作栏 ==========

/** 底部快捷操作栏：类似千问的"深度思考/AI生图/拍题答疑" */
export interface ActionBarComponent extends BaseComponent {
  type: 'action-bar';
  data: {
    items: {
      id: string;
      label: string;
      icon?: string;
      actionId: string;
      badge?: string;
      disabled?: boolean;
    }[];
    /** 是否固定在底部 */
    sticky?: boolean;
    /** 布局方式 */
    layout?: 'scroll' | 'grid';
  };
}

// ========== 信息横幅 ==========

/** 顶部信息横幅：地址提示、活动公告等 */
export interface InfoBannerComponent extends BaseComponent {
  type: 'info-banner';
  data: {
    content: string;
    /** 横幅类型 */
    variant?: 'info' | 'success' | 'warning' | 'error' | 'promo';
    /** 图标 */
    icon?: string;
    /** 操作链接 */
    action?: {
      label: string;
      actionId: string;
    };
    /** 是否可关闭 */
    dismissible?: boolean;
  };
}

// ========== 按钮组 ==========

/** 按钮组：多个按钮并排 */
export interface ButtonGroupComponent extends BaseComponent {
  type: 'button-group';
  data: {
    buttons: {
      id: string;
      label: string;
      icon?: string;
      actionId: string;
      variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive';
      size?: 'sm' | 'md' | 'lg';
      loading?: boolean;
      disabled?: boolean;
      payload?: Record<string, any>;
    }[];
    /** 布局方式 */
    layout?: 'horizontal' | 'vertical' | 'grid';
    /** 对齐 */
    align?: 'left' | 'center' | 'right' | 'stretch';
  };
}

// ========== 状态卡片 ==========

/** 状态卡片：成功/失败/进行中等状态展示 */
export interface StatusCardComponent extends BaseComponent {
  type: 'status-card';
  data: {
    status: 'success' | 'error' | 'pending' | 'info' | 'warning';
    title: string;
    description?: string;
    icon?: string;
    action?: {
      label: string;
      actionId: string;
    };
    secondaryAction?: {
      label: string;
      actionId: string;
    };
  };
}

// ========== 详情列表 ==========

/** 详情列表：key-value 展示 */
export interface DetailListComponent extends BaseComponent {
  type: 'detail-list';
  data: {
    title?: string;
    items: {
      label: string;
      value: string;
      /** 值的类型 */
      valueType?: 'text' | 'link' | 'badge' | 'highlight';
      /** 链接地址 */
      href?: string;
      /** 可编辑 */
      editable?: boolean;
      editActionId?: string;
      /** 颜色 */
      color?: string;
    }[];
    /** 是否显示分隔线 */
    divider?: boolean;
  };
}

// ========== 步骤进度 ==========

/** 步骤进度：工作流可视化 */
export interface ProgressStepsComponent extends BaseComponent {
  type: 'progress-steps';
  data: {
    title?: string;
    currentStep: number;
    steps: {
      id: string;
      label: string;
      description?: string;
      status: 'pending' | 'active' | 'completed' | 'error' | 'skipped';
      timestamp?: string;
    }[];
    /** 方向 */
    direction?: 'horizontal' | 'vertical';
  };
}

// ========== 风险指标 ==========

/** 风险指标：仪表盘式展示 */
export interface RiskIndicatorComponent extends BaseComponent {
  type: 'risk-indicator';
  data: {
    title: string;
    /** 总分/得分 */
    score: number;
    maxScore?: number;
    /** 风险等级 */
    level: 'low' | 'medium' | 'high' | 'critical';
    /** 描述 */
    description?: string;
    /** 细分指标 */
    factors?: {
      label: string;
      score: number;
      maxScore: number;
      level: 'low' | 'medium' | 'high';
    }[];
    /** 操作 */
    action?: {
      label: string;
      actionId: string;
    };
  };
}

// ========== 文本块 ==========

/** 富文本块：AI 生成的 Markdown 内容 */
export interface TextBlockComponent extends BaseComponent {
  type: 'text-block';
  data: {
    content: string;
    /** 渲染模式 */
    format?: 'markdown' | 'plain' | 'html';
    /** 是否可折叠 */
    collapsible?: boolean;
    /** 折叠时的预览行数 */
    previewLines?: number;
  };
}

// ========== 分隔线 ==========

export interface DividerComponent extends BaseComponent {
  type: 'divider';
  data?: {
    label?: string;
  };
}

// ========== 扩展接口：地图组件 ==========

/** 地图视图：展示地点位置（律所/法院/公证处等） */
export interface MapViewComponent extends BaseComponent {
  type: 'map-view';
  data: {
    title: string;
    center?: { lat: number; lng: number };
    markers?: {
      id: string;
      lat: number;
      lng: number;
      label: string;
      info?: string;
    }[];
    zoom?: number;
    mapProvider?: 'amap' | 'bmap' | 'google';
    action?: { label: string; actionId: string };
  };
}

// ========== 扩展接口：支付组件 ==========

/** 支付卡片：用于法律服务费用支付 */
export interface PaymentCardComponent extends BaseComponent {
  type: 'payment-card';
  data: {
    title: string;
    amount: number;
    currency?: string;
    description?: string;
    paymentMethods?: {
      id: string;
      name: string;
      icon?: string;
    }[];
    orderId?: string;
    payAction?: { label: string; actionId: string };
    cancelAction?: { label: string; actionId: string };
  };
}

// ========== 扩展接口：律师选择器 ==========

/** 律师选择器：带筛选排序的律师列表 */
export interface LawyerPickerComponent extends BaseComponent {
  type: 'lawyer-picker';
  data: {
    title: string;
    lawyers: A2UIComponent[]; // lawyer-card 组件列表
    filters?: {
      id: string;
      label: string;
      options: { id: string; label: string }[];
    }[];
    sortOptions?: { id: string; label: string }[];
    onSelectAction?: { label: string; actionId: string };
    multiSelect?: boolean;
  };
}

// ========== 扩展接口：媒体卡片 ==========

/** 媒体预览卡片：图片/视频/文件预览 */
export interface MediaCardComponent extends BaseComponent {
  type: 'media-card';
  data: {
    title: string;
    mediaType: 'image' | 'video' | 'pdf' | 'document';
    url: string;
    thumbnail?: string;
    description?: string;
    size?: string;
    action?: { label: string; actionId: string };
  };
}

// ========== 扩展接口：日程预约 ==========

/** 日程预约组件：选择咨询时间 */
export interface SchedulePickerComponent extends BaseComponent {
  type: 'schedule-picker';
  data: {
    title: string;
    subtitle?: string;
    availableSlots: {
      id: string;
      date: string;
      time: string;
      available: boolean;
    }[];
    durationOptions?: {
      id: string;
      label: string;
      duration: number;
    }[];
    onSelectAction?: { label: string; actionId: string };
  };
}

// ========== 扩展接口：评价反馈 ==========

/** 评价反馈组件：服务完成后评价 */
export interface FeedbackCardComponent extends BaseComponent {
  type: 'feedback-card';
  data: {
    title: string;
    ratingEnabled?: boolean;
    commentEnabled?: boolean;
    tags?: string[];
    submitAction?: { label: string; actionId: string };
  };
}

// ========== 扩展接口：通用插件容器 ==========

/** 通用插件容器：Skills/MCP 扩展的统一接口 */
export interface PluginContainerComponent extends BaseComponent {
  type: 'plugin-container';
  data: {
    pluginType: string;
    title?: string;
    config: Record<string, any>;
    fallbackText?: string;
  };
}

// ========== 事件回调 ==========

/** A2UI 事件：用户与组件交互时触发 */
export interface A2UIEvent {
  /** 事件类型 */
  type: 'action' | 'form-submit' | 'selection' | 'dismiss';
  /** 动作标识 */
  actionId: string;
  /** 来源组件ID */
  componentId: string;
  /** 负载数据 */
  payload?: Record<string, any>;
  /** 表单数据（type=form-submit 时） */
  formData?: Record<string, any>;
}

/** A2UI 事件处理器 */
export type A2UIEventHandler = (event: A2UIEvent) => void;

// ========== StreamObject 协议（流式生成 A2UI） ==========

/**
 * StreamObject：流式 A2UI 组件协议
 * 
 * 后端通过 WebSocket `a2ui_stream` 事件逐步发送组件数据：
 * 1. `stream_start` — 开始一个新的流式 A2UI 消息
 * 2. `stream_delta` — 增量更新某个组件的数据字段
 * 3. `stream_component` — 新增一个完整组件
 * 4. `stream_end` — 流式结束，最终确认
 */
export interface A2UIStreamEvent {
  /** 流式消息唯一 ID（与 A2UIMessage.id 对应） */
  streamId: string;
  /** 事件子类型 */
  action: 'stream_start' | 'stream_delta' | 'stream_component' | 'stream_end';
  /** 来源 Agent */
  agent?: string;
  /** 组件 ID（stream_delta 时必填） */
  componentId?: string;
  /** 增量数据（stream_delta 时使用，将 deep merge 到现有组件 data） */
  delta?: Record<string, any>;
  /** 完整组件（stream_component 时使用） */
  component?: A2UIComponent;
  /** 元数据 */
  metadata?: Record<string, any>;
}

// ========== 新增法务专用组件类型标识 ==========

/** 合同对比卡片 */
export interface ContractCompareComponent extends BaseComponent {
  type: 'contract-compare';
  data: {
    title: string;
    subtitle?: string;
    leftLabel: string;
    rightLabel: string;
    clauses: {
      id: string;
      clauseTitle: string;
      changeType: 'added' | 'removed' | 'modified' | 'unchanged';
      leftContent?: string;
      rightContent?: string;
      riskLevel?: 'low' | 'medium' | 'high';
      comment?: string;
    }[];
    summary?: {
      totalClauses: number;
      changedClauses: number;
      riskLevel: 'low' | 'medium' | 'high';
      recommendation: string;
    };
    actions?: {
      label: string;
      actionId: string;
      variant?: 'primary' | 'secondary' | 'outline';
    }[];
  };
}

/** 费用估算卡片 */
export interface FeeEstimateComponent extends BaseComponent {
  type: 'fee-estimate';
  data: {
    title: string;
    subtitle?: string;
    items: {
      id: string;
      label: string;
      description?: string;
      amount: number;
      unit?: string;
      optional?: boolean;
      selected?: boolean;
    }[];
    discounts?: { label: string; amount: number; type: 'fixed' | 'percent' }[];
    total: { label: string; amount: number; original?: number };
    packages?: {
      id: string;
      name: string;
      description: string;
      features: string[];
      price: number;
      originalPrice?: number;
      popular?: boolean;
      actionId: string;
    }[];
    paymentMethods?: { id: string; name: string; icon?: string; recommended?: boolean }[];
    notes?: string[];
    actions?: {
      label: string;
      actionId: string;
      variant?: 'primary' | 'secondary' | 'outline';
      payload?: Record<string, any>;
    }[];
  };
}

/** 案件进度时间线卡片 */
export interface CaseProgressComponent extends BaseComponent {
  type: 'case-progress';
  data: {
    caseId: string;
    title: string;
    caseType?: string;
    currentPhase: string;
    progress: number;
    steps: {
      id: string;
      label: string;
      description?: string;
      status: 'completed' | 'active' | 'pending' | 'error';
      timestamp?: string;
      agent?: string;
    }[];
    estimatedCompletion?: string;
    actions?: {
      label: string;
      actionId: string;
      variant?: 'primary' | 'secondary' | 'outline';
      payload?: Record<string, any>;
    }[];
  };
}

/** 风险评估雷达图卡片 */
export interface RiskAssessmentComponent extends BaseComponent {
  type: 'risk-assessment';
  data: {
    title: string;
    subtitle?: string;
    overallScore: number;
    overallLevel: 'low' | 'medium' | 'high' | 'critical';
    dimensions: {
      id: string;
      label: string;
      score: number;
      maxScore?: number;
      level: 'low' | 'medium' | 'high' | 'critical';
      trend?: 'up' | 'down' | 'stable';
    }[];
    summary?: string;
    recommendations?: string[];
    actions?: {
      label: string;
      actionId: string;
      variant?: 'primary' | 'secondary' | 'outline';
      payload?: Record<string, any>;
    }[];
  };
}
