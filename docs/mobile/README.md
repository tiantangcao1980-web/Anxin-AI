# 移动端工程文档

> 权威级别：⭐⭐ 工程参考
> 适用：移动端（`mobile/` Expo + `mini-program/` Taro）
>
> **2026-05-20 路线纠正**：原 uni-app / UniApp 跨端方案已**彻底放弃**，相关 `apps/uni-mobile/`
> 目录及 `uni-app-migration-plan.md` 已删除。移动端回归 mobile/Expo + mini-program/Taro 双端独立方案。

## 文档清单

| 文件 | 主题 |
|---|---|
| [error-handling-guidelines.md](./error-handling-guidelines.md) | 错误处理规范（loading/empty/error 三态） |

## 双端定位

| 端 | 技术栈 | 角色 |
|---|---|---|
| `mobile/` | React Native + Expo 52 | iOS / Android 原生壳（EAS Build / TestFlight） |
| `mini-program/` | Taro 3.6 + React | 微信小程序专属（微信开发者工具 / 体验版） |

> 不再有跨端统一方案，两端分别独立设计、独立 build、独立 release。

## 当前阻断

详见 [../audit/_tasks/task-11c-mobile-design.md](../audit/_tasks/task-11c-mobile-design.md)：

- ✅ 本地 smoke / Vitest / Expo doctor / mini tsc-build / fake fallback guard / design token guard 全过
- ⏳ 缺 iOS/Android 真机截图、WeChat DevTools 交互证据、移动端品牌主色最终统一

## 维护

- 双端代码请同时更新各自 API 客户端层（不再"三端共享"，两端独立维护）
- 设计 token 改动必走 [../design/cross-platform-token-drift.md](../design/cross-platform-token-drift.md)
