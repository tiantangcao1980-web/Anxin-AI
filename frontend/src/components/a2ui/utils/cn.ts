/**
 * A2UI Utils - 工具函数
 */

import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * 合并 Tailwind CSS 类名的工具函数
 * 使用 clsx 和 tailwind-merge 来智能处理类名冲突
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * 格式化组件规范为字符串 (用于调试)
 */
export function formatSpec(spec: any): string {
  return JSON.stringify(spec, null, 2);
}

/**
 * 验证组件规范
 */
export function validateSpec(spec: any): boolean {
  if (!spec || typeof spec !== 'object') {
    console.error('[A2UI] Invalid spec: must be an object');
    return false;
  }

  if (!spec.type || typeof spec.type !== 'string') {
    console.error('[A2UI] Invalid spec: missing or invalid "type" property');
    return false;
  }

  return true;
}

/**
 * 深度合并对象
 */
export function deepMerge<T extends Record<string, any>>(
  target: T,
  source: Partial<T>
): T {
  const result = { ...target };

  for (const key in source) {
    if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
      result[key] = deepMerge(result[key] || ({} as any), source[key] as any);
    } else {
      result[key] = source[key] as any;
    }
  }

  return result;
}

/**
 * 生成唯一 ID
 */
export function generateId(prefix: string = 'a2ui'): string {
  return `${prefix}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * 防抖函数
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      func(...args);
    };

    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, wait);
  };
}

/**
 * 节流函数
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;

  return function executedFunction(...args: Parameters<T>) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}
