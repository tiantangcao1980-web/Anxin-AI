# Apps — 跨端应用容器（预留）

> 状态：**当前为空目录**。2026-05 UniApp 跨端方案终止后，本目录保留为未来"非主线移动/桌面新增容器"的预留位置。

## 历史
- **～2026-04**：曾托管 `uni-mobile/`（UniApp Vue3 跨端方案）
- **2026-05**：UniApp 路线终止 — 与 Expo RN（`mobile/`）和 Taro（`mini-program/`）维护重叠、DCloud 云打包流程未跑通、跨端 token 漂移引入额外审计成本。详见 [PRODUCT_ROADMAP.md §2.3](../PRODUCT_ROADMAP.md) 路线调整说明。

## 当前端路线（事实源）

```
顶级根/
├── frontend/         Web 浏览器 + 桌面端（Tauri 共用渲染）— React
├── desktop/          桌面端 Rust + Tauri 壳
├── mobile/           iOS / Android 原生 — Expo + React Native
└── mini-program/     微信小程序 — Taro + React
```

- **响应式 Web → H5 移动端**：由 `frontend/` 通过断点覆盖，无需独立 H5 容器
- **新移动能力**：进入 `mobile/`
- **新小程序能力**：进入 `mini-program/`
- **桌面新窗口/壳**：进入 `desktop/` 或 `frontend/`（视渲染逻辑而定）

## 在此处新建子项目的门槛

引入新的子目录前必须先答清：
1. 是否能复用 `frontend/` + 响应式断点？（绝大多数 H5/移动场景应能复用）
2. 是否能复用 `mobile/` 或 `mini-program/` 的现有 stack？
3. 引入第四套技术栈带来的设计 token 同步成本、构建链路成本、CI 时长成本是否被充分评估？
4. 是否有明确的退出条件，避免再次成为 legacy？

若 3 项以上不能确认，**不要在此处新建子项目**。
