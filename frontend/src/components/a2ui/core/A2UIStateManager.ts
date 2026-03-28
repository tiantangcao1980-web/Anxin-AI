/**
 * A2UI State Manager - 状态管理器
 * 支持路径访问、批量更新、订阅机制
 */

type StateListener = (value: any) => void;
type StateSubscribers = Map<string, Set<StateListener>>;

export class A2UIStateManager {
  private state: Record<string, any>;
  private subscribers: StateSubscribers;
  private batchDepth: number;
  private batchedUpdates: Array<{ path: string; value: any }>;

  constructor(initialState: Record<string, any> = {}) {
    this.state = this._deepClone(initialState);
    this.subscribers = new Map();
    this.batchDepth = 0;
    this.batchedUpdates = [];
  }

  /**
   * 获取状态值 (支持路径访问)
   * @example
   * get('user.profile.name')
   * get('user', {})
   */
  get(path: string, defaultValue?: any): any {
    const keys = path.split('.');
    let current = this.state;

    for (const key of keys) {
      if (current == null || typeof current !== 'object') {
        return defaultValue;
      }
      if (!(key in current)) {
        return defaultValue;
      }
      current = current[key];
    }

    return current;
  }

  /**
   * 设置状态值 (支持路径设置)
   * @example
   * set('user.profile.name', 'Alice')
   * set('user.age', 30)
   */
  set(path: string, value: any): void {
    if (this.batchDepth > 0) {
      // 批处理模式
      this.batchedUpdates.push({ path, value });
      return;
    }

    this._setInternal(path, value);
  }

  /**
   * 删除状态值
   */
  delete(path: string): void {
    const keys = path.split('.');
    if (keys.length === 0) return;

    const lastKey = keys.pop()!;
    let current = this.state;

    for (const key of keys) {
      if (!(key in current) || typeof current[key] !== 'object') {
        return; // 路径不存在
      }
      current = current[key];
    }

    delete current[lastKey];
    this._notify(path, undefined);
  }

  /**
   * 批量更新开始
   */
  batchStart(): void {
    this.batchDepth++;
  }

  /**
   * 批量更新结束并执行
   */
  batchEnd(): void {
    this.batchDepth--;
    if (this.batchDepth === 0 && this.batchedUpdates.length > 0) {
      const updates = [...this.batchedUpdates];
      this.batchedUpdates = [];

      // 合并相同路径的更新
      const merged = new Map<string, any>();
      for (const update of updates) {
        merged.set(update.path, update.value);
      }

      // 执行更新
      for (const [path, value] of merged.entries()) {
        this._setInternal(path, value);
      }
    }
  }

  /**
   * 订阅状态变化
   * @returns 取消订阅函数
   */
  subscribe(path: string, listener: StateListener): () => void {
    if (!this.subscribers.has(path)) {
      this.subscribers.set(path, new Set());
    }

    this.subscribers.get(path)!.add(listener);

    // 返回取消订阅函数
    return () => {
      const subscribers = this.subscribers.get(path);
      if (subscribers) {
        subscribers.delete(listener);
        if (subscribers.size === 0) {
          this.subscribers.delete(path);
        }
      }
    };
  }

  /**
   * 获取整个状态的快照
   */
  getSnapshot(): Record<string, any> {
    return this._deepClone(this.state);
  }

  /**
   * 替换整个状态
   */
  replace(newState: Record<string, any>): void {
    this.state = this._deepClone(newState);
    this._notifyAll();
  }

  /**
   * 清空所有状态
   */
  clear(): void {
    this.state = {};
    this._notifyAll();
  }

  // ========== 私有方法 ==========

  /**
   * 内部设置方法
   */
  private _setInternal(path: string, value: any): void {
    const keys = path.split('.');
    if (keys.length === 0) return;

    const lastKey = keys.pop()!;
    let current = this.state;

    // 创建路径上的中间对象
    for (const key of keys) {
      if (!(key in current)) {
        current[key] = {};
      } else if (typeof current[key] !== 'object') {
        current[key] = {}; // 覆盖非对象值
      }
      current = current[key];
    }

    // 检查值是否真的变化
    const oldValue = current[lastKey];
    const newValue = value;
    const hasChanged = !this._isEqual(oldValue, newValue);

    if (hasChanged) {
      current[lastKey] = this._deepClone(newValue);
      this._notify(path, newValue);
    }
  }

  /**
   * 通知订阅者
   */
  private _notify(path: string, value: any): void {
    // 通知精确路径的订阅者
    const exactSubscribers = this.subscribers.get(path);
    if (exactSubscribers) {
      for (const listener of exactSubscribers) {
        try {
          listener(value);
        } catch (error) {
          console.error(`[A2UI State] Error in listener for path "${path}":`, error);
        }
      }
    }

    // 通知父路径的订阅者
    const keys = path.split('.');
    for (let i = keys.length - 1; i > 0; i--) {
      const parentPath = keys.slice(0, i).join('.');
      const parentSubscribers = this.subscribers.get(parentPath);
      if (parentSubscribers) {
        const parentValue = this.get(parentPath);
        for (const listener of parentSubscribers) {
          try {
            listener(parentValue);
          } catch (error) {
            console.error(`[A2UI State] Error in parent listener for "${parentPath}":`, error);
          }
        }
      }
    }
  }

  /**
   * 通知所有订阅者
   */
  private _notifyAll(): void {
    for (const [path, subscribers] of this.subscribers.entries()) {
      const value = this.get(path);
      for (const listener of subscribers) {
        try {
          listener(value);
        } catch (error) {
          console.error(`[A2UI State] Error in listener for "${path}":`, error);
        }
      }
    }
  }

  /**
   * 深度克隆对象
   */
  private _deepClone<T>(obj: T): T {
    if (obj === null || typeof obj !== 'object') {
      return obj;
    }

    if (obj instanceof Date) {
      return new Date(obj.getTime()) as any;
    }

    if (obj instanceof Array) {
      return obj.map(item => this._deepClone(item)) as any;
    }

    if (obj instanceof Object) {
      const cloned: any = {};
      for (const key in obj) {
        if (Object.prototype.hasOwnProperty.call(obj, key)) {
          cloned[key] = this._deepClone(obj[key]);
        }
      }
      return cloned;
    }

    return obj;
  }

  /**
   * 简单的相等比较
   */
  private _isEqual(a: any, b: any): boolean {
    // 基本类型比较
    if (a === b) return true;

    // null/undefined 比较
    if (a == null || b == null) return a === b;

    // 类型不同
    if (typeof a !== typeof b) return false;

    // 数组比较
    if (Array.isArray(a) && Array.isArray(b)) {
      if (a.length !== b.length) return false;
      return a.every((item, index) => this._isEqual(item, b[index]));
    }

    // 对象比较
    if (typeof a === 'object' && typeof b === 'object') {
      const keysA = Object.keys(a);
      const keysB = Object.keys(b);

      if (keysA.length !== keysB.length) return false;

      return keysA.every(key => this._isEqual(a[key], b[key]));
    }

    return false;
  }
}
