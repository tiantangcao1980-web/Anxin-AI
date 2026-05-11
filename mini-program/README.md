# 安心智能助手 · 微信小程序（V3）

第 5 端：小程序，基于 **Taro 3.6 + React + TypeScript + Sass**，与 web / mobile / desktop / chrome-ext 共用同一套后端契约（`/api/v1/...`）。

P21-A 已交付**基础层**：TabBar、登录、API client、theme、共享组件。
P21-B / C / D 在分包中分别完成 任务 / 智能体 / 能力中心。

---

## 启动

### 1. 安装依赖

```bash
cd mini-program
npm install
```

> 已通过 `package.json#overrides` 锁定 `webpack@5.89.0`，避免高版本 webpack 与 Taro 3.6 自带的 `webpackbar` 不兼容。

### 2. 编译微信小程序

```bash
npm run build:weapp     # 一次性编译
npm run dev:weapp       # 开发模式（watch）
```

输出在 `dist/`。

### 3. 用微信开发者工具打开

```bash
# macOS
/Applications/wechatwebdevtools.app/Contents/MacOS/cli open --project "$(pwd)"
# Windows
"C:\Program Files (x86)\Tencent\微信web开发者工具\cli.bat" open --project "项目根目录"
```

⚠️ 上线前需在 `project.config.json` 配置真实 `appid`，并在 mp 后台 `request.legalDomain` 加入后端 API 域名。

---

## 项目结构

```
mini-program/
├── scripts/
│   ├── generate-icons.js         # 生成 8 个 tabBar 占位 PNG（4 tab × 2 状态）
│   └── check-bundle-size.js      # H5 build 后产物大小守门
├── src/
│   ├── app.tsx                   # 根组件 — 启动检查 token，未登录跳 /pages/login
│   ├── app.config.ts             # 主包 + 分包 + tabBar 全局配置
│   ├── app.scss                  # 全局样式 + 设计 token (Sass 变量)
│   ├── pages/                    # 主包页面（必须 < 1.5 MB）
│   │   ├── index/                # tabBar — 智能体首页（4 大业务域 + 10 personas + 推荐场景）
│   │   ├── me/                   # tabBar — 个人中心
│   │   ├── login/                # 微信一键登录 + 邮箱密码登录（开发模式）
│   │   └── webview/              # 通用 H5 跳转壳（用户协议、OAuth 回跳）
│   ├── subpackages/              # 分包（共 < 8 MB）⚠️ 由 P21-B/C/D 接管
│   │   ├── tasks/                # P21-B：任务中心
│   │   ├── personas/             # P21-C：智能体详情 + chat
│   │   └── capabilities/         # P21-D：能力中心（7 个资源页）
│   ├── components/
│   │   ├── Layout/Screen.tsx     # 全屏容器（安全区适配）
│   │   ├── PersonaCard/          # 智能体卡片（compact / 详情两种形态）
│   │   └── EmptyState/           # 空状态 + 错误状态
│   ├── utils/
│   │   ├── api/                  # API client + 业务模块
│   │   │   ├── client.ts         # Taro.request 封装 + 401 refresh + 重试
│   │   │   ├── baseUrl.ts        # API base URL 解析（dev/prod）
│   │   │   ├── auth.ts           # wechatMiniprogramLogin / passwordLogin / logout
│   │   │   ├── personas.ts       # listPersonas / getPersona / chatWithPersona
│   │   │   ├── agentTasks.ts     # listTasks / createTask / getTask 等
│   │   │   ├── capabilities.ts   # 7 个 capability 资源 CRUD
│   │   │   └── index.ts          # 统一出口
│   │   ├── auth/
│   │   │   ├── token.ts          # Taro.setStorageSync 持久化（access/refresh/user）
│   │   │   ├── refresh.ts        # 单飞 refresh，多并发 401 时只发一次 /auth/refresh
│   │   │   └── index.ts
│   │   ├── theme/
│   │   │   ├── colors.ts         # palette / domainPalette
│   │   │   ├── typography.ts     # rpx 字号
│   │   │   ├── spacing.ts        # 间距 / 圆角 / 阴影
│   │   │   └── index.ts
│   │   └── personaSeeds.ts       # 10 personas 静态种子（home 首屏渲染）
│   ├── types/
│   │   ├── persona.ts            # Persona / PersonaDetail / ChatRequest 等
│   │   ├── agentTask.ts          # AgentTask / TaskEvent / CreateTaskRequest 等
│   │   └── index.ts
│   └── assets/
│       └── tab/                  # 8 个 PNG（agents / tasks / capabilities / me × normal/active）
└── config/                       # Taro 编译配置（dev / prod）
```

---

## TabBar

| 顺序 | 文案 | 路径 | 主负责 |
|------|------|------|--------|
| 1 | 智能体 | `pages/index/index` | **P21-A** |
| 2 | 任务 | `subpackages/tasks/index/index` | P21-B |
| 3 | 能力 | `subpackages/capabilities/index/index` | P21-D |
| 4 | 我 | `pages/me/index` | **P21-A** |

主色 `#D4A574`（暖色调），与 web / mobile 端一致。

---

## P21-B / C / D 接入指南

### 通用导入路径

```typescript
import { apiClient, ApiError } from '@/utils/api'           // HTTP 客户端
import { tokenStorage } from '@/utils/auth/token'           // Token 存储
import { palette, domainPalette } from '@/utils/theme'      // 设计 token
import { Screen } from '@/components/Layout'                // 全屏容器
import PersonaCard from '@/components/PersonaCard'          // 智能体卡片
import EmptyState from '@/components/EmptyState'            // 空状态
```

> Taro tsconfig 已配 `"@/*": ["./src/*"]`，分包内可直接用绝对路径。

### 业务模块

```typescript
import { listTasks, createTask, getTask, cancelTask } from '@/utils/api/agentTasks'
import { listPersonas, getPersona, chatWithPersona } from '@/utils/api/personas'
import { capabilitiesApi } from '@/utils/api/capabilities'
// capabilitiesApi.scheduledTasks.list() / .skills.list() / .messageChannels.list() 等
```

### 分包页面声明

P21-A 在 `app.config.ts#subpackages` 中只声明了 3 个 `index/index` 入口。
P21-B/C/D 接入时**自行追加** `detail/index`、`chat/index`、`create/index` 等子页面到对应分包的 `pages` 数组。

例如 P21-B 加入任务详情页：

```diff
   {
     root: 'subpackages/tasks',
-    pages: ['index/index'],
+    pages: ['index/index', 'detail/index', 'create/index'],
   },
```

### SSE 事件订阅

⚠️ 微信小程序无浏览器原生 `EventSource`。任务事件流的实现策略由 P21-B 决定：

- **方案 A（推荐）**：短 long-polling，每 1.5–2s 调 `getTask(id)` 拉一次状态
- **方案 B**：后端为小程序提供 WebSocket 端点 `/agent-tasks/{id}/ws`，用 `Taro.connectSocket`
- **方案 C**：HTTP chunked 流，`Taro.request` + `enableChunked: true`（基础库 2.20.1+）

---

## 后端契约

| Endpoint | 用途 | 调用方 |
|----------|------|--------|
| `POST /auth/oauth/wechat/callback { code }` | 微信一键登录（wx.login → js_code 换 token） | 主包 login 页 |
| `POST /auth/login { email, password }` | 邮箱密码登录（开发体验） | 主包 login 页 |
| `POST /auth/refresh { refresh_token }` | 401 自动续签 | utils/auth/refresh.ts |
| `POST /auth/logout` | 退出（清除服务端 session） | 主包 me 页 |
| `GET /personas` | 智能体列表 | home + P21-C |
| `GET /personas/{id}` | 智能体详情 | P21-C |
| `POST /personas/{id}/chat` | 对话 | P21-C |
| `GET /agent-tasks` | 任务列表 | P21-B |
| `POST /agent-tasks` | 创建任务 | P21-B |
| ... | 7 个 capabilities 资源 | P21-D |

---

## 主包大小

P21-A 当前 build:weapp 产物：

```
主包：约 340 KB / 1.5 MB 限制
分包（占位）：3 KB / 8 MB 限制
```

P21-B/C/D 接入后，单个分包应保持 < 1.5 MB。

## 已知问题

- **Node 24 + webpack 5.106 ProgressPlugin 不兼容**：已通过 `package.json#overrides` 锁定 webpack 5.89.0 解决。
- **subpackages/ 当前仅占位**：tabBar 必须指向真实文件，故 P21-A 创建了 `subpackages/{tasks,personas,capabilities}/index/index.tsx` 的最小 stub，**P21-B/C/D 直接覆盖即可**（这些 stub 文件顶部已标 `// PLACEHOLDER for P21-X`）。
