/**
 * A2UI Provider - Agent-to-UI 框架核心
 * 提供动态组件渲染和状态管理能力
 */

import React, { createContext, useContext, ReactNode, useState, useCallback, useRef } from 'react';
import { A2UIRenderer } from './A2UIRenderer';
import { A2UIStateManager } from './A2UIStateManager';

/**
 * A2UI 组件规范
 */
export interface A2UIComponentSpec {
  type: string;                    // 组件类型
  props?: Record<string, any>;     // 组件属性
  children?: A2UIComponentSpec[];  // 嵌套子组件
  id?: string;                     // 组件唯一标识
  animations?: {                   // 动画配置
    enter?: any;
    exit?: any;
    hover?: any;
    tap?: any;
  };
  style?: React.CSSProperties;     // 内联样式
  className?: string;              // CSS 类名
}

/**
 * A2UI 上下文值
 */
export interface A2UIContextValue {
  // 组件注册
  registerComponent: (type: string, component: React.ComponentType<any>) => void;
  unregisterComponent: (type: string) => void;
  getComponent: (type: string) => React.ComponentType<any> | undefined;
  hasComponent: (type: string) => boolean;

  // 状态管理
  setState: (path: string, value: any) => void;
  getState: (path: string, defaultValue?: any) => any;
  subscribe: (path: string, callback: (value: any) => void) => () => void;

  // 组件渲染
  render: (spec: A2UIComponentSpec) => ReactNode;

  // 动画控制
  triggerAnimation: (animation: string, options?: any) => void;
  cancelAnimation: (animationId: string) => void;

  // 批量操作
  batchStart: () => void;
  batchEnd: () => void;

  // 调试
  debugMode: boolean;
  setDebugMode: (enabled: boolean) => void;
}

const A2UIContext = createContext<A2UIContextValue | null>(null);

/**
 * A2UI Provider 组件
 */
export interface A2UIProviderProps {
  children: ReactNode;
  debugMode?: boolean;
  initialState?: Record<string, any>;
  onStateChange?: (path: string, value: any) => void;
}

export const A2UIProvider: React.FC<A2UIProviderProps> = ({
  children,
  debugMode = false,
  initialState = {},
  onStateChange
}) => {
  // 状态管理器实例 (使用 ref 保持引用稳定)
  const stateManagerRef = useRef<A2UIStateManager>(
    new A2UIStateManager(initialState)
  );

  // 渲染器实例
  const rendererRef = useRef<A2UIRenderer>(
    new A2UIRenderer(stateManagerRef.current)
  );

  // 调试模式状态
  const [isDebug, setIsDebug] = useState(debugMode);

  // 组件注册
  const registerComponent = useCallback((type: string, component: React.ComponentType<any>) => {
    rendererRef.current.register(type, component);
    if (isDebug) {
      console.log(`[A2UI] Component registered: ${type}`);
    }
  }, [isDebug]);

  const unregisterComponent = useCallback((type: string) => {
    rendererRef.current.unregister(type);
    if (isDebug) {
      console.log(`[A2UI] Component unregistered: ${type}`);
    }
  }, [isDebug]);

  const getComponent = useCallback((type: string) => {
    return rendererRef.current.get(type);
  }, []);

  const hasComponent = useCallback((type: string) => {
    return rendererRef.current.has(type);
  }, []);

  // 状态管理
  const setState = useCallback((path: string, value: any) => {
    stateManagerRef.current.set(path, value);
    if (onStateChange) {
      onStateChange(path, value);
    }
    if (isDebug) {
      console.log(`[A2UI] State updated: ${path} =`, value);
    }
  }, [onStateChange, isDebug]);

  const getState = useCallback((path: string, defaultValue?: any) => {
    return stateManagerRef.current.get(path, defaultValue);
  }, []);

  const subscribe = useCallback((path: string, callback: (value: any) => void) => {
    return stateManagerRef.current.subscribe(path, callback);
  }, []);

  // 组件渲染
  const render = useCallback((spec: A2UIComponentSpec): ReactNode => {
    return rendererRef.current.render(spec);
  }, []);

  // 动画控制
  const triggerAnimation = useCallback((animation: string, options?: any) => {
    // TODO: 实现动画触发逻辑
    if (isDebug) {
      console.log(`[A2UI] Animation triggered: ${animation}`, options);
    }
  }, [isDebug]);

  const cancelAnimation = useCallback((animationId: string) => {
    // TODO: 实现动画取消逻辑
    if (isDebug) {
      console.log(`[A2UI] Animation cancelled: ${animationId}`);
    }
  }, [isDebug]);

  // 批量操作
  const batchStart = useCallback(() => {
    stateManagerRef.current.batchStart();
  }, []);

  const batchEnd = useCallback(() => {
    stateManagerRef.current.batchEnd();
  }, []);

  // 调试模式
  const setDebugMode = useCallback((enabled: boolean) => {
    setIsDebug(enabled);
  }, []);

  // 构建上下文值
  const contextValue: A2UIContextValue = {
    // 组件注册
    registerComponent,
    unregisterComponent,
    getComponent,
    hasComponent,

    // 状态管理
    setState,
    getState,
    subscribe,

    // 组件渲染
    render,

    // 动画控制
    triggerAnimation,
    cancelAnimation,

    // 批量操作
    batchStart,
    batchEnd,

    // 调试
    debugMode: isDebug,
    setDebugMode
  };

  return (
    <A2UIContext.Provider value={contextValue}>
      {children}
    </A2UIContext.Provider>
  );
};

/**
 * 使用 A2UI 上下文的 Hook
 */
export const useA2UI = (): A2UIContextValue => {
  const context = useContext(A2UIContext);
  if (!context) {
    throw new Error('useA2UI must be used within A2UIProvider');
  }
  return context;
};

/**
 * 使用 A2UI 状态的 Hook
 */
export const useA2UIState = <T = any>(
  path: string,
  defaultValue?: T
): [T, (value: T) => void] => {
  const { getState, setState, subscribe } = useA2UI();
  const [value, setValue] = useState<T>(() => getState(path, defaultValue));

  // 订阅状态变化
  useEffect(() => {
    const unsubscribe = subscribe(path, (newValue) => {
      setValue(newValue);
    });
    return unsubscribe;
  }, [path, subscribe]);

  // 更新状态的函数
  const updateValue = useCallback((newValue: T) => {
    setState(path, newValue);
  }, [path, setState]);

  return [value, updateValue];
};

/**
 * 使用 A2UI 组件渲染的 Hook
 */
export const useA2UIRenderer = () => {
  const { render, registerComponent, hasComponent } = useA2UI();

  return {
    render,
    registerComponent,
    hasComponent
  };
};

import { useEffect } from 'react';
