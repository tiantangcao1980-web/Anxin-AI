# 移动端工程文档

> 权威级别：⭐⭐ 工程参考
> 适用：移动端（`mobile/` Expo + `apps/uni-mobile/` UniApp + `mini-program/` Taro）

## 文档清单

| 文件 | 主题 |
|---|---|
| [error-handling-guidelines.md](./error-handling-guidelines.md) | 错误处理规范（loading/empty/error 三态） |
| [uni-app-migration-plan.md](./uni-app-migration-plan.md) | UniApp 迁移计划（Vue3 + 跨端） |

## 三端定位

| 端 | 技术栈 | 角色 |
|---|---|---|
| `mobile/` | React Native + Expo 52 | iOS / Android 原生壳 |
| `apps/uni-mobile/` | UniApp Vue3 + Vite | 跨端（H5 + 小程序 + App） |
| `mini-program/` | Taro 3.6 + React | 微信小程序专属 + H5 双端 |

## 当前阻断（M-C 候选）

详见 [../audit/_tasks/task-11c-mobile-design.md](../audit/_tasks/task-11c-mobile-design.md)：

- ✅ 本地 smoke / Vitest / Expo doctor / mini tsc-build / fake fallback guard / design token guard 全过
- ⏳ 缺 iOS/Android 真机截图、WeChat DevTools 交互证据、移动端品牌主色最终统一

## 维护

- 跨端代码请同时更新三端 API 客户端层
- 设计 token 改动必走 [../design/cross-platform-token-drift.md](../design/cross-platform-token-drift.md)
