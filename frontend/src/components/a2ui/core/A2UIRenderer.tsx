/**
 * A2UI Renderer - 动态组件渲染器
 * 支持从 Agent 生成的规范动态渲染 React 组件
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { A2UIStateManager } from './A2UIStateManager';
import type { A2UIComponentSpec } from './A2UIProvider';

/**
 * 组件注册表
 */
type ComponentRegistry = Map<string, React.ComponentType<any>>;

/**
 * 渲染配置
 */
export interface RenderConfig {
  // 默认动画配置
  defaultEnterAnimation?: any;
  defaultExitAnimation?: any;
  defaultHoverAnimation?: any;

  // 错误处理
  showErrorComponent?: boolean;
  ErrorComponent?: React.ComponentType<{ error: Error; spec: A2UIComponentSpec }>;

  // 调试模式
  debug?: boolean;
}

/**
 * A2UI 动态渲染器
 */
export class A2UIRenderer {
  private components: ComponentRegistry;
  private stateManager: A2UIStateManager;
  private config: RenderConfig;

  constructor(stateManager: A2UIStateManager, config: RenderConfig = {}) {
    this.components = new Map();
    this.stateManager = stateManager;
    this.config = {
      defaultEnterAnimation: {
        opacity: 0,
        y: 20,
        scale: 0.95
      },
      defaultExitAnimation: {
        opacity: 0,
        scale: 0.95
      },
      defaultHoverAnimation: {
        scale: 1.02,
        transition: { type: 'spring', stiffness: 400, damping: 17 }
      },
      showErrorComponent: true,
      debug: false,
      ...config
    };
  }

  /**
   * 注册组件类型
   */
  register(type: string, component: React.ComponentType<any>): void {
    this.components.set(type, component);
    if (this.config.debug) {
      // console.log(`[A2UI Renderer] Component registered: ${type}`);
    }
  }

  /**
   * 批量注册组件
   */
  registerBatch(components: Record<string, React.ComponentType<any>>): void {
    Object.entries(components).forEach(([type, component]) => {
      this.register(type, component);
    });
  }

  /**
   * 取消注册组件
   */
  unregister(type: string): void {
    this.components.delete(type);
    if (this.config.debug) {
      // console.log(`[A2UI Renderer] Component unregistered: ${type}`);
    }
  }

  /**
   * 检查组件是否已注册
   */
  has(type: string): boolean {
    return this.components.has(type);
  }

  /**
   * 获取已注册组件
   */
  get(type: string): React.ComponentType<any> | undefined {
    return this.components.get(type);
  }

  /**
   * 获取所有已注册组件类型
   */
  getRegisteredTypes(): string[] {
    return Array.from(this.components.keys());
  }

  /**
   * 渲染组件规范为 React 元素
   */
  render(spec: A2UIComponentSpec): React.ReactNode {
    try {
      return this._renderSpec(spec);
    } catch (error) {
      console.error('[A2UI Renderer] Render error:', error, spec);
      if (this.config.showErrorComponent && this.config.ErrorComponent) {
        const ErrorComp = this.config.ErrorComponent;
        return React.createElement(ErrorComp, {
          error: error as Error,
          spec
        });
      }
      return null;
    }
  }

  /**
   * 批量渲染多个组件
   */
  renderBatch(specs: A2UIComponentSpec[]): React.ReactNode[] {
    return specs.map(spec => this.render(spec));
  }

  /**
   * 更新配置
   */
  setConfig(config: Partial<RenderConfig>): void {
    this.config = { ...this.config, ...config };
  }

  // ========== 私有方法 ==========

  /**
   * 内部渲染方法
   */
  private _renderSpec(spec: A2UIComponentSpec, key?: string | number): React.ReactNode {
    const Component = this.components.get(spec.type);

    if (!Component) {
      console.warn(`[A2UI Renderer] Unknown component type: ${spec.type}`);
      return this._renderErrorFallback(
        new Error(`Unknown component type: ${spec.type}`),
        spec,
        key
      );
    }

    // 合并默认动画和自定义动画
    const animations = {
      enter: this.config.defaultEnterAnimation,
      exit: this.config.defaultExitAnimation,
      hover: this.config.defaultHoverAnimation,
      ...spec.animations
    };

    // 处理 children
    const children = spec.children
      ? spec.children.map((child, index) => this._renderSpec(child, index))
      : spec.props?.children; // 支持 React children

    // 构建组件 props
    const componentProps = {
      ...spec.props,
      children
    };

    // 使用 motion 包装组件 (如果有动画配置)
    const motionProps: any = {};

    if (animations.enter || animations.exit) {
      motionProps.initial = animations.enter;
      motionProps.animate = { opacity: 1, y: 0, scale: 1 };
      motionProps.exit = animations.exit;
      motionProps.transition = { type: 'spring', stiffness: 300, damping: 30 };
    }

    if (animations.hover) {
      motionProps.whileHover = animations.hover;
    }

    if (spec.animations?.tap) {
      motionProps.whileTap = spec.animations.tap;
    }

    // 添加 key
    const renderKey = key || spec.id;

    // 创建元素
    const element = React.createElement(Component, componentProps);

    // 如果有动画配置,用 motion 包装
    if (Object.keys(motionProps).length > 0) {
      return React.createElement(
        motion.div,
        {
          key: renderKey,
          ...motionProps,
          style: spec.style,
          className: spec.className
        },
        element
      );
    }

    // 否则直接返回元素 (用 div 包装以支持 style 和 className)
    return React.createElement(
      'div',
      {
        key: renderKey,
        style: spec.style,
        className: spec.className
      },
      element
    );
  }

  /**
   * 渲染错误回退组件
   */
  private _renderErrorFallback(
    error: Error,
    spec: A2UIComponentSpec,
    key?: string | number
  ): React.ReactNode {
    const errorStyle: React.CSSProperties = {
      padding: '1rem',
      backgroundColor: 'hsl(var(--destructive) / 0.1)',
      border: '1px solid hsl(var(--destructive) / 0.3)',
      borderRadius: '0.5rem',
      color: 'hsl(var(--destructive))',
      fontFamily: 'monospace',
      fontSize: '0.875rem'
    };

    return React.createElement(
      'div',
      {
        key: key || spec.id,
        style: errorStyle,
        className: spec.className
      },
      React.createElement('strong', null, 'A2UI Render Error: '),
      error.message,
      React.createElement('pre', null, JSON.stringify(spec, null, 2))
    );
  }
}

/**
 * 默认错误组件
 */
export const DefaultA2UIErrorComponent: React.FC<{
  error: Error;
  spec: A2UIComponentSpec;
}> = ({ error, spec }) => {
  return (
    <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 font-mono text-sm">
      <strong>A2UI Render Error:</strong> {error.message}
      <pre className="mt-2 overflow-auto max-h-32">
        {JSON.stringify(spec, null, 2)}
      </pre>
    </div>
  );
};

/**
 * 渲染单条规范的便捷函数
 */
export function renderA2UI(
  spec: A2UIComponentSpec,
  stateManager: A2UIStateManager,
  config?: RenderConfig
): React.ReactNode {
  const renderer = new A2UIRenderer(stateManager, config);
  return renderer.render(spec);
}

/**
 * 渲染多条规范的便捷函数
 */
export function renderA2UIBatch(
  specs: A2UIComponentSpec[],
  stateManager: A2UIStateManager,
  config?: RenderConfig
): React.ReactNode[] {
  const renderer = new A2UIRenderer(stateManager, config);
  return renderer.renderBatch(specs);
}
