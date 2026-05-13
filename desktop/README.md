# 安心智能助手 — 桌面客户端

基于 [Tauri 2.x](https://v2.tauri.app/) 构建的跨平台桌面应用。

## 前置要求

- [Rust](https://www.rust-lang.org/tools/install) (最新稳定版)
- [Node.js](https://nodejs.org/) >= 18
- 前端依赖已安装: `cd ../frontend && npm install`

### macOS 额外要求
- Xcode Command Line Tools: `xcode-select --install`

### Windows 额外要求
- [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- WebView2 (Windows 10/11 已内置)

## 开发

```bash
# 启动开发模式（自动启动前端 dev server + Tauri 窗口）
cargo tauri dev

# 或从项目根目录
make tauri-dev
```

## 构建

```bash
# 构建安装包
cargo tauri build

# 或从项目根目录
make tauri-build
```

构建产物位置：
- macOS: `target/release/bundle/dmg/`
- Windows: `target/release/bundle/msi/` 和 `target/release/bundle/nsis/`
- Linux: `target/release/bundle/deb/` 和 `target/release/bundle/appimage/`

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ANXIN_BACKEND_URL` | 后端 API 地址 | `http://localhost:8001` |

## 架构

```
Tauri App (Rust + WebView)
    ├── 前端: ../frontend/dist (Vite SPA)
    ├── IPC: get_app_info, get_backend_url
    └── 插件: http, fs, dialog, clipboard, shell
```
