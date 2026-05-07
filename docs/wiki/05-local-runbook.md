# 本地运行与预览

## Web + 后端开发

推荐先启动基础设施：

```bash
cd /Users/pengchengkeji/Documents/GitHub/Anxin-Smart-Legal-Services
make dev-infra
```

然后分别启动后端和前端：

```bash
cd backend
python -m uvicorn src.api.main:app --reload --port 8005 --host 0.0.0.0
```

```bash
cd frontend
npm run dev
```

常用地址：

| 服务 | 地址 |
|---|---|
| 前端 | `http://localhost:3001` |
| 后端 API | `http://localhost:8005` |
| API 文档 | `http://localhost:8005/docs` |

注意：根 `package.json` 的 `dev:backend` 默认端口是 `8001`，Makefile 本地开发默认后端端口是 `8005`。联调前要确认前端代理配置和后端端口一致。

## Docker 开发环境

```bash
make dev
```

完整基础设施：

```bash
make dev-full
```

停止：

```bash
make down
```

## 前端构建预览

```bash
cd frontend
npm run build
npm run preview
```

## 桌面端

开发：

```bash
cd desktop
cargo tauri dev
```

或从前端目录：

```bash
cd frontend
npm run tauri:dev
```

构建：

```bash
cd desktop
cargo tauri build
```

## 移动端

```bash
cd mobile
npm install
npm run start
```

iOS / Android：

```bash
npm run ios
npm run android
```

## 微信小程序

```bash
cd mini-program
npm install
npm run build:weapp
```

H5 构建：

```bash
npm run build:h5
```

## 文档 Wiki

这份 Codex Wiki 位于：

```text
docs/wiki/
```

可以直接在编辑器中打开 Markdown。若需要简单本地 HTTP 预览，可在仓库根目录运行：

```bash
python3 -m http.server 8765
```

然后访问：

```text
http://localhost:8765/docs/wiki/
```

这只是静态文件预览，不提供 Markdown 渲染样式。推荐用编辑器 Markdown Preview 或后续接入 VitePress/MkDocs。

