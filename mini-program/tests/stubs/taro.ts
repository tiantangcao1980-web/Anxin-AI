// Taro 在 vitest 中的最小 stub —— 仅暴露被测代码用到的 API。
// 当前覆盖：getStorageSync / setStorageSync / removeStorageSync / request / login。
// 真实运行时由微信小程序基础库提供，单测只验证生产代码的调用链与边界。

const _storage = new Map<string, unknown>()

export const __storage = {
  reset() {
    _storage.clear()
  },
  set(key: string, value: unknown) {
    _storage.set(key, value)
  },
  get(key: string) {
    return _storage.get(key)
  },
}

export const request = (() => {
  const fn = () => {
    throw new Error(
      'Taro.request stub was not mocked — vitest 用 vi.spyOn 拦截后再调被测代码',
    )
  }
  return fn
})()

export const login = (() => {
  const fn = () => {
    throw new Error(
      'Taro.login stub was not mocked — vitest 用 vi.spyOn 拦截后再调被测代码',
    )
  }
  return fn
})()

function getStorageSync<T = unknown>(key: string): T {
  return (_storage.get(key) ?? '') as T
}

function setStorageSync(key: string, value: unknown): void {
  _storage.set(key, value)
}

function removeStorageSync(key: string): void {
  _storage.delete(key)
}

export default {
  getStorageSync,
  setStorageSync,
  removeStorageSync,
  request,
  login,
}
