/**
 * vitest 全局 setup（2026-06 新增）
 *
 * 背景：privacy.test.ts / privacy-integration.test.ts 经 `./client` 间接 import 真实
 * @tarojs/runtime，而该 runtime 在 ESM 顶层引用了一批构建期注入的全局开关
 * （ENABLE_INNER_HTML 等）。node 测试环境没有 Taro 编译期注入这些全局，
 * 模块加载时即抛 `ReferenceError: ENABLE_INNER_HTML is not defined`。
 *
 * 这里在全局对象上把这批开关全部置为 false（功能等价于"不启用对应 DOM 能力"），
 * 让 runtime 能在 node 下顺利加载。不影响任何测试断言意图。
 *
 * 参考 @tarojs/runtime/dist/runtime.esm.js 中引用到的全部 ENABLE_* 开关。
 */

const taroRuntimeFlags = {
  ENABLE_INNER_HTML: false,
  ENABLE_ADJACENT_HTML: false,
  ENABLE_SIZE_APIS: false,
  ENABLE_TEMPLATE_CONTENT: false,
  ENABLE_CLONE_NODE: false,
  ENABLE_CONTAINS: false,
  ENABLE_MUTATION_OBSERVER: false,
} as const

for (const [key, value] of Object.entries(taroRuntimeFlags)) {
  if (!(key in globalThis)) {
    Object.defineProperty(globalThis, key, {
      value,
      writable: true,
      configurable: true,
      enumerable: false,
    })
  }
}
