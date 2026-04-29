# 安心智能助手 - 移动端

Expo + React Native + TypeScript + expo-router 的 V3 移动端基础层。

本目录由 P17-A 完成基础脚手架；业务页面由 P17-B/C/D 接入。

## 启动

```bash
cd mobile
npm install
npm run ios       # iOS 模拟器
npm run android   # Android 模拟器
npm run web       # Expo Web
npm run typecheck # TypeScript 检查（必须 0 error）
npm test          # vitest 单测
```

环境配置见 `app.json -> expo.extra`：
- `apiBaseUrl` 生产环境 API（默认 `https://api.anxinagent.com/api/v1`）
- `apiBaseUrlDev` 本地开发 API（默认 iOS `http://localhost:8001/api/v1` / Android `http://10.0.2.2:8001/api/v1`）

## V3 4 tab 结构

| Tab | 文件 | 状态 | 实装方 |
|-----|------|------|--------|
| 智能体 | `app/(tabs)/personas.tsx` | 占位 | P17-B |
| 任务 | `app/(tabs)/tasks.tsx` | 占位 | P17-C |
| 能力 | `app/(tabs)/capabilities.tsx` | 占位 | P17-D |
| 我 | `app/(tabs)/me.tsx` | 简易实装（头像 + 设置 + 登出） | P17-A |

V2 老 tab（chat/collaboration/investigation/knowledge/profile/index）暂保留在 `(tabs)/` 下，
通过 `href: null` 从底部栏隐藏，避免破坏老的 router 路径。

## 目录布局（V3）

```
mobile/
├── app/
│   ├── _layout.tsx          # 根 layout：SafeArea + Privacy + V3Theme + 推送初始化
│   ├── index.tsx            # 入口：未登录 → /(auth)/login，已登录 → /(tabs)
│   ├── (auth)/              # 登录 / 注册（V2 已实装，contract 与 V3 兼容）
│   └── (tabs)/
│       ├── _layout.tsx      # V3 4 tab 导航
│       ├── personas.tsx     # 占位（P17-B）
│       ├── tasks.tsx        # 占位（P17-C）
│       ├── capabilities.tsx # 占位（P17-D）
│       └── me.tsx           # 我（P17-A）
└── src/
    ├── theme/               # V3 设计令牌（颜色/字体/间距/圆角/阴影）+ ThemeProvider
    ├── components/Layout/   # Screen / PlaceholderScreen 通用容器
    ├── lib/
    │   ├── api/             # V3 API 客户端
    │   │   ├── client.ts        # axios + 401 自动 refresh + ApiError
    │   │   ├── auth.ts          # /auth/login /register /refresh /me /logout
    │   │   ├── personas.ts      # /personas /personas/{id} /personas/{id}/chat
    │   │   ├── agentTasks.ts    # /agent-tasks 8 endpoint + pollTaskUntilDone
    │   │   ├── imChannels.ts    # /im/channels 6 endpoint
    │   │   └── index.ts         # 统一导出
    │   ├── notifications/   # expo-notifications 包装
    │   │   ├── register.ts      # registerForPushNotificationsAsync
    │   │   ├── handler.ts       # 前台 / 后台 handler + 任务通知 dispatcher
    │   │   ├── setup.ts         # setupV3PushNotifications 一键初始化
    │   │   └── index.ts
    │   └── types/           # 共享类型聚合（re-export 自 api/*）
    ├── services/api.ts      # （V2 老 fetch 客户端，仍兼容）
    ├── lib/auth-storage.ts  # SecureStore 包装的 token 持久化
    └── ...                  # V2 业务模块（features/ inbox / workflow 等）
```

## V3 接口契约（给 P17-B/C/D 用）

### 1. 智能体（P17-B 用）

```typescript
import { personasApi, type Persona, type PersonaDomain } from '@/lib/api'

const list = await personasApi.list()                 // Persona[]
const detail = await personasApi.get(personaId)       // PersonaDetail
const reply = await personasApi.chat(personaId, { message, history })
```

10 个 persona ID（与 web 端 `frontend/src/lib/api/personas.ts` 完全对齐）：
`anxin_assistant / legal_advisor / contract_steward / due_diligence_expert / tax_finance_advisor / operations_manager / market_researcher / lead_hunter / content_director / ecommerce_assistant`

### 2. 任务中心（P17-C 用）

```typescript
import { agentTasksApi, type AgentTask, type AgentTaskStatus } from '@/lib/api'

const tasks = await agentTasksApi.listTasks({ status: 'running', limit: 50 })
const task = await agentTasksApi.getTask(id)
await agentTasksApi.cancelTask(id)
await agentTasksApi.approveTask(id)

// 实时刷新（轮询版，等同于 web 的 SSE 订阅）
const stop = agentTasksApi.pollTaskUntilDone(id, (task) => { ... })
```

### 3. IM 渠道（P17-D 用）

```typescript
import { imChannelsApi, type IMChannel, type IMChannelType } from '@/lib/api'

const channels = await imChannelsApi.listChannels()
await imChannelsApi.bindAgent(channelId, { agent_persona: 'legal_advisor' })
```

### 4. 主题 / 布局

```typescript
import { useV3Theme } from '@/theme'
import { Screen, PlaceholderScreen } from '@/components/Layout'

function MyPage() {
  const t = useV3Theme()
  return (
    <Screen scrollable padded>
      <Text style={{ color: t.colors.text }}>...</Text>
    </Screen>
  )
}
```

### 5. 推送

```typescript
import { setupV3PushNotifications } from '@/lib/notifications'

// 已在 app/_layout.tsx 全局调用
// 业务页面只需关心：任务通知会自动 deep-link 到 /(tabs)/tasks/[id]
```

## 已知 TODO（给 P17-B/C/D）

1. **V2 老 tab 替换**：`(tabs)/` 下的 chat/collaboration/investigation/knowledge/profile/index 需要 P17-B/C/D 决定保留迁移还是清理。
2. **路由 deep-link**：`/(tabs)/tasks/[id]` 详情页路由仍走 V2 `app/tasks/[id].tsx`；V3 版本由 P17-C 实装。
3. **设备 / 推送注册端点**：默认上报到 `/notifications/devices/register`，后端如果实际是 `/notifications/push-tokens` 可在 `setupV3PushNotifications({ endpoint: ... })` 覆盖。
4. **SSE 任务事件**：移动端用 `pollTaskUntilDone` 轮询替代 EventSource。如需真实 SSE，需引入 `react-native-sse` 或 `eventsource-polyfill`。
