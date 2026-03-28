/**
 * A2UI Component Registry - 组件注册表
 * 集中管理所有 A2UI 组件类型
 */

import React from 'react';

/**
 * A2UI 内置组件类型
 */
export enum A2UIComponentType {
  // 基础组件
  BUTTON = 'button',
  CARD = 'card',
  BADGE = 'badge',
  AVATAR = 'avatar',

  // 表单组件
  INPUT = 'input',
  TEXTAREA = 'textarea',
  SELECT = 'select',
  CHECKBOX = 'checkbox',
  RADIO = 'radio',
  SWITCH = 'switch',
  SLIDER = 'slider',

  // 数据展示
  LIST = 'list',
  TABLE = 'table',
  TREE = 'tree',
  TIMELINE = 'timeline',
  CHART = 'chart',

  // 布局组件
  CONTAINER = 'container',
  GRID = 'grid',
  FLEX = 'flex',
  STACK = 'stack',
  TABS = 'tabs',
  ACCORDION = 'accordion',
  COLLAPSE = 'collapse',

  // 反馈组件
  ALERT = 'alert',
  TOAST = 'toast',
  MODAL = 'modal',
  DRAWER = 'drawer',
  PROGRESS = 'progress',
  SPINNER = 'spinner',
  SKELETON = 'skeleton',

  // 导航组件
  BREADCRUMB = 'breadcrumb',
  PAGINATION = 'pagination',
  STEPS = 'steps',
  MENU = 'menu',
  SIDEBAR = 'sidebar',

  // 特殊组件
  CANVAS = 'canvas',
  EDITOR = 'editor',
  CODE_BLOCK = 'code_block',
  MARKDOWN = 'markdown',
  FILE_UPLOAD = 'file_upload',

  // 法律专用
  CONTRACT_VIEWER = 'contract_viewer',
  CLAUSE_EDITOR = 'clause_editor',
  RISK_ASSESSMENT = 'risk_assessment',
  DOCUMENT_COMPARE = 'document_compare',
  LEGAL_CLAUSE = 'legal_clause',
  CASE_ANALYSIS = 'case_analysis',
  RISK_MATRIX = 'risk_matrix'
}

/**
 * 组件元数据
 */
export interface ComponentMetadata {
  type: string;
  name: string;
  category: 'basic' | 'form' | 'data' | 'layout' | 'feedback' | 'navigation' | 'special' | 'legal';
  description: string;
  props?: Record<string, PropSchema>;
  version: string;
  author?: string;
}

/**
 * 属性 Schema
 */
export interface PropSchema {
  type: 'string' | 'number' | 'boolean' | 'array' | 'object' | 'enum' | 'reactNode';
  required?: boolean;
  default?: any;
  description?: string;
  enum?: any[];
}

/**
 * 组件注册表类
 */
export class A2UIComponentRegistry {
  private static instance: A2UIComponentRegistry;
  private components: Map<string, ComponentMetadata>;
  private implementations: Map<string, React.ComponentType<any>>;

  private constructor() {
    this.components = new Map();
    this.implementations = new Map();
    this._registerBuiltInComponents();
  }

  /**
   * 获取单例实例
   */
  static getInstance(): A2UIComponentRegistry {
    if (!A2UIComponentRegistry.instance) {
      A2UIComponentRegistry.instance = new A2UIComponentRegistry();
    }
    return A2UIComponentRegistry.instance;
  }

  /**
   * 注册组件元数据
   */
  registerMetadata(metadata: ComponentMetadata): void {
    this.components.set(metadata.type, metadata);
  }

  /**
   * 批量注册元数据
   */
  registerMetadataBatch(metadataArray: ComponentMetadata[]): void {
    metadataArray.forEach(metadata => this.registerMetadata(metadata));
  }

  /**
   * 注册组件实现
   */
  registerImplementation(type: string, component: React.ComponentType<any>): void {
    this.implementations.set(type, component);
  }

  /**
   * 同时注册元数据和实现
   */
  register(
    metadata: ComponentMetadata,
    implementation: React.ComponentType<any>
  ): void {
    this.registerMetadata(metadata);
    this.registerImplementation(metadata.type, implementation);
  }

  /**
   * 获取组件元数据
   */
  getMetadata(type: string): ComponentMetadata | undefined {
    return this.components.get(type);
  }

  /**
   * 获取组件实现
   */
  getImplementation(type: string): React.ComponentType<any> | undefined {
    return this.implementations.get(type);
  }

  /**
   * 检查组件是否已注册
   */
  has(type: string): boolean {
    return this.components.has(type) && this.implementations.has(type);
  }

  /**
   * 获取所有已注册组件类型
   */
  getRegisteredTypes(): string[] {
    return Array.from(this.components.keys());
  }

  /**
   * 按分类获取组件
   */
  getByCategory(category: ComponentMetadata['category']): ComponentMetadata[] {
    return Array.from(this.components.values()).filter(
      meta => meta.category === category
    );
  }

  /**
   * 搜索组件
   */
  search(query: string): ComponentMetadata[] {
    const lowerQuery = query.toLowerCase();
    return Array.from(this.components.values()).filter(meta =>
      meta.name.toLowerCase().includes(lowerQuery) ||
      meta.type.toLowerCase().includes(lowerQuery) ||
      meta.description.toLowerCase().includes(lowerQuery)
    );
  }

  /**
   * 注销组件
   */
  unregister(type: string): void {
    this.components.delete(type);
    this.implementations.delete(type);
  }

  /**
   * 清空所有注册
   */
  clear(): void {
    this.components.clear();
    this.implementations.clear();
    this._registerBuiltInComponents();
  }

  /**
   * 导出所有组件元数据为 JSON
   */
  exportMetadata(): Record<string, ComponentMetadata> {
    const obj: Record<string, ComponentMetadata> = {};
    this.components.forEach((meta, type) => {
      obj[type] = meta;
    });
    return obj;
  }

  // ========== 私有方法 ==========

  /**
   * 注册内置组件元数据
   */
  private _registerBuiltInComponents(): void {
    const builtInMetadata: ComponentMetadata[] = [
      {
        type: A2UIComponentType.BUTTON,
        name: 'Button',
        category: 'basic',
        description: '按钮组件，支持多种样式和状态',
        props: {
          variant: {
            type: 'enum',
            enum: ['primary', 'secondary', 'success', 'danger', 'warning'],
            default: 'primary',
            description: '按钮变体'
          },
          size: {
            type: 'enum',
            enum: ['sm', 'md', 'lg'],
            default: 'md',
            description: '按钮尺寸'
          },
          disabled: {
            type: 'boolean',
            default: false,
            description: '是否禁用'
          },
          loading: {
            type: 'boolean',
            default: false,
            description: '是否加载中'
          },
          onClick: {
            type: 'object',
            description: '点击事件处理函数'
          }
        },
        version: '1.0.0'
      },
      {
        type: A2UIComponentType.CARD,
        name: 'Card',
        category: 'basic',
        description: '卡片容器组件',
        props: {
          title: {
            type: 'string',
            description: '卡片标题'
          },
          subtitle: {
            type: 'string',
            description: '卡片副标题'
          },
          variant: {
            type: 'enum',
            enum: ['default', 'gradient', 'glass'],
            default: 'default',
            description: '卡片变体'
          }
        },
        version: '1.0.0'
      },
      {
        type: A2UIComponentType.INPUT,
        name: 'Input',
        category: 'form',
        description: '文本输入框',
        props: {
          value: {
            type: 'string',
            description: '输入值'
          },
          placeholder: {
            type: 'string',
            description: '占位文本'
          },
          disabled: {
            type: 'boolean',
            default: false
          },
          error: {
            type: 'string',
            description: '错误提示文本'
          }
        },
        version: '1.0.0'
      },
      {
        type: A2UIComponentType.LIST,
        name: 'List',
        category: 'data',
        description: '列表组件',
        props: {
          items: {
            type: 'array',
            description: '列表项数据'
          },
          renderItem: {
            type: 'object',
            description: '自定义渲染函数'
          }
        },
        version: '1.0.0'
      },
      {
        type: A2UIComponentType.ALERT,
        name: 'Alert',
        category: 'feedback',
        description: '警告提示组件',
        props: {
          type: {
            type: 'enum',
            enum: ['info', 'success', 'warning', 'error'],
            default: 'info'
          },
          message: {
            type: 'string',
            description: '提示内容'
          },
          closable: {
            type: 'boolean',
            default: false
          }
        },
        version: '1.0.0'
      },
      {
        type: A2UIComponentType.CONTRACT_VIEWER,
        name: 'ContractViewer',
        category: 'legal',
        description: '合同查看器，支持注释和高亮',
        props: {
          contractId: {
            type: 'string',
            description: '合同 ID'
          },
          showAnnotations: {
            type: 'boolean',
            default: true
          }
        },
        version: '1.0.0'
      },
      {
        type: A2UIComponentType.LEGAL_CLAUSE,
        name: 'LegalClauseCard',
        category: 'legal',
        description: '法律条款分析卡片，展示条款原文、AI解读和修改建议',
        props: {
          clause: { type: 'string', required: true, description: '条款原文' },
          article: { type: 'string', required: true, description: '条款编号' },
          interpretation: { type: 'string', required: true, description: 'AI 解读' },
          risk: { type: 'enum', enum: ['low', 'medium', 'high'], default: 'low', description: '风险等级' },
          suggestion: { type: 'string', description: '修改建议' }
        },
        version: '1.0.0'
      },
      {
        type: A2UIComponentType.CASE_ANALYSIS,
        name: 'CaseAnalysisCard',
        category: 'legal',
        description: 'AI 案件分析结果卡片，展示综合案件分析',
        props: {
          caseType: { type: 'string', required: true, description: '案件类型' },
          parties: { type: 'array', required: true, description: '当事人列表' },
          jurisdiction: { type: 'string', required: true, description: '管辖区域' },
          keyIssues: { type: 'array', required: true, description: '争议焦点' },
          legalBasis: { type: 'array', required: true, description: '法律依据' },
          winProbability: { type: 'number', required: true, description: '胜诉概率 0-100' },
          recommendation: { type: 'string', required: true, description: 'AI 建议' }
        },
        version: '1.0.0'
      },
      {
        type: A2UIComponentType.RISK_MATRIX,
        name: 'RiskMatrixCard',
        category: 'legal',
        description: '风险矩阵卡片，展示分类风险评估及缓解建议',
        props: {
          title: { type: 'string', required: true, description: '矩阵标题' },
          risks: { type: 'array', required: true, description: '风险项数组' },
          overallScore: { type: 'number', required: true, description: '综合评分 0-100' }
        },
        version: '1.0.0'
      }
    ];

    this.registerMetadataBatch(builtInMetadata);
  }
}

/**
 * 导出单例实例
 */
export const a2uiRegistry = A2UIComponentRegistry.getInstance();
