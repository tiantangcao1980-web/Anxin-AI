# 桌面端工程文档

> 权威级别：⭐⭐ 工程参考
> 适用：Tauri 2 桌面端（`desktop/`）工程实施

## 文档清单

| 文件 | 主题 |
|---|---|
| [window-styling.md](./window-styling.md) | 窗口样式（macOS overlay 标题栏、毛玻璃等） |
| [quick-query-flow.md](./quick-query-flow.md) | 全局快捷键呼出 + 快问流程 |
| [sqlite-encryption-strategy.md](./sqlite-encryption-strategy.md) | SQLCipher 本地加密策略 |
| [sync-engine-design.md](./sync-engine-design.md) | 同步引擎设计 |
| [sync-engine-protocol.md](./sync-engine-protocol.md) | 同步协议 |
| [sync-engine-runbook.md](./sync-engine-runbook.md) | 同步引擎运行手册 |

## 当前阻断（M-C 桌面 MVP 候选）

详见 [../audit/_tasks/task-11a-desktop-mvp.md](../audit/_tasks/task-11a-desktop-mvp.md) 与 [../audit/_tasks/task-11b-sync-engine.md](../audit/_tasks/task-11b-sync-engine.md)：

- ✅ 代码级 self-test / runtime smoke / SQLCipher migration smoke / 100/500 性能基线
- ⏳ 缺 dmg signing + Apple notarization + 跨设备连续会话证据

## 维护

- 桌面端代码改动同步更新对应文档
- 涉及 IPC / 安全边界的改动必须更新 [sync-engine-protocol.md](./sync-engine-protocol.md)
