# Apps — 跨端应用集合

> 多端 V3 智能助手应用容器

## 当前子项目

| 目录 | 技术栈 | 角色 |
|---|---|---|
| [uni-mobile/](./uni-mobile/) | UniApp Vue3 + Vite + TypeScript | 跨端（H5 + 小程序 + iOS/Android App） |

## 与其他端的关系

```
顶级根/
├── frontend/         Web 浏览器 + 桌面端（Tauri 共用渲染）— React
├── desktop/          桌面端 Rust + Tauri 壳
├── mobile/           原生移动（Expo + RN）— React Native
├── apps/uni-mobile/  跨端方案 — Vue3 + UniApp（覆盖 H5/小程序/App）
└── mini-program/     微信小程序专属 — Taro + React
```

## 与 mini-program/ 与 mobile/ 的边界

- **mini-program/**：纯微信小程序，Taro + React
- **mobile/**：iOS / Android 原生（Expo Router）
- **apps/uni-mobile/**：覆盖多端的 Vue 方案，作为 mobile/mini-program 之外的跨端补充

详见 [../docs/mobile/uni-app-migration-plan.md](../docs/mobile/uni-app-migration-plan.md)。

## 规范

- 命名：kebab-case 目录
- 各子项目自带 README + package.json
- 共用设计 token：`../frontend/src/lib/design-tokens.ts`
