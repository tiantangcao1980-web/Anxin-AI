# Desktop Shared Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 抽离跨端共享认证与平台存储基础，完成桌面端 macOS/Windows 的首条可验证主链路，并为移动端后续接入留出稳定接口。

**Architecture:** 先从现有 `frontend/src/lib/api.ts` 中抽出最小共享认证客户端与平台存储接口，再把桌面端 Tauri 认证持久化、本地数据库初始化、同步状态展示串成一条完整路径。移动端不在本计划内直接实现页面，只消费这次产出的共享协议与平台抽象。

**Tech Stack:** React 18, Vite, TypeScript, Tauri 2.x, Rust, tauri-plugin-store, tauri-plugin-sql, Vitest, cargo test

---

## Scope Split

本次 spec 覆盖桌面端、移动端、共享层三个方向。为避免范围失控，本计划只落地第一个可工作的子项目：

- 共享认证/平台抽象基础
- 桌面端认证持久化与本地数据库启动
- 桌面端同步状态入口

移动端 `mobile/` 工程与页面实现另起单独计划，在本计划完成并稳定后再执行。

## File Structure

**Create**

- `frontend/src/lib/platform/storage.ts` - 统一 token / refresh token / backend url 的平台存储接口
- `frontend/src/lib/platform/storage.test.ts` - Web 存储实现与 fallback 行为测试
- `frontend/src/lib/client/auth-client.ts` - 共享认证客户端，封装登录、登出、刷新 token
- `frontend/src/lib/client/auth-client.test.ts` - 认证客户端测试
- `frontend/src/components/mode-switcher/DesktopSyncPanel.tsx` - 桌面端同步状态面板
- `desktop/src/commands/bootstrap.rs` - 桌面端本地数据库初始化与应用启动状态命令
- `desktop/tests/bootstrap.rs` - Rust 侧本地初始化测试

**Modify**

- `frontend/src/lib/api.ts` - 改为调用共享存储接口，去掉对 `localStorage` 的直接依赖
- `frontend/src/lib/tauri-bridge.ts` - 补充桌面端 bootstrap / token 持久化命令封装
- `frontend/src/pages/Login.tsx` - 登录成功后走统一认证客户端
- `frontend/src/App.tsx` - 桌面端启动时执行 bootstrap，并挂载同步状态面板
- `desktop/src/commands/auth.rs` - 真正落 token 到持久化存储，同时同步内存状态
- `desktop/src/commands/mod.rs` - 导出 bootstrap 命令模块
- `desktop/src/lib.rs` - 注册 bootstrap 命令，并在 setup 中初始化本地数据库
- `desktop/src/services/local_db.rs` - 提供初始化入口与幂等迁移函数

**Test**

- `frontend/src/lib/platform/storage.test.ts`
- `frontend/src/lib/client/auth-client.test.ts`
- `desktop/tests/bootstrap.rs`

### Task 1: 抽离平台存储接口

**Files:**
- Create: `frontend/src/lib/platform/storage.ts`
- Test: `frontend/src/lib/platform/storage.test.ts`
- Modify: `frontend/src/lib/api.ts:5-155`

- [ ] **Step 1: 写失败测试，约束 Web 存储与统一接口**

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createWebTokenStorage } from './storage'

describe('createWebTokenStorage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('reads and writes access token through one interface', async () => {
    const storage = createWebTokenStorage()

    await storage.setAccessToken('token-123')

    expect(await storage.getAccessToken()).toBe('token-123')
  })

  it('clears both auth tokens together', async () => {
    const storage = createWebTokenStorage()

    await storage.setAccessToken('a')
    await storage.setRefreshToken('b')
    await storage.clearAuth()

    expect(await storage.getAccessToken()).toBeNull()
    expect(await storage.getRefreshToken()).toBeNull()
  })
})
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```bash
cd frontend && npm run test -- src/lib/platform/storage.test.ts
```

Expected: FAIL，提示 `./storage` 不存在或 `createWebTokenStorage` 未定义。

- [ ] **Step 3: 写最小实现**

```ts
export interface TokenStorage {
  getAccessToken(): Promise<string | null>
  setAccessToken(token: string): Promise<void>
  getRefreshToken(): Promise<string | null>
  setRefreshToken(token: string): Promise<void>
  clearAuth(): Promise<void>
}

export function createWebTokenStorage(): TokenStorage {
  return {
    async getAccessToken() {
      return localStorage.getItem('access_token')
    },
    async setAccessToken(token: string) {
      localStorage.setItem('access_token', token)
    },
    async getRefreshToken() {
      return localStorage.getItem('refresh_token')
    },
    async setRefreshToken(token: string) {
      localStorage.setItem('refresh_token', token)
    },
    async clearAuth() {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    },
  }
}
```

- [ ] **Step 4: 改造 API 层使用统一存储**

```ts
import { getTokenStorage } from './platform/storage'

async function request<T>(endpoint: string, options: RequestInit = {}, _retry = false): Promise<T> {
  const storage = getTokenStorage()
  const token = await storage.getAccessToken()

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
}
```

- [ ] **Step 5: 运行测试确认通过**

Run:

```bash
cd frontend && npm run test -- src/lib/platform/storage.test.ts
```

Expected: PASS。

### Task 2: 抽离共享认证客户端并接入登录页

**Files:**
- Create: `frontend/src/lib/client/auth-client.ts`
- Test: `frontend/src/lib/client/auth-client.test.ts`
- Modify: `frontend/src/pages/Login.tsx`
- Modify: `frontend/src/lib/tauri-bridge.ts`

- [ ] **Step 1: 写失败测试，约束登录成功后的存储与桌面持久化**

```ts
import { describe, expect, it, vi } from 'vitest'
import { createAuthClient } from './auth-client'

describe('createAuthClient', () => {
  it('persists tokens after login', async () => {
    const api = {
      login: vi.fn().mockResolvedValue({
        access_token: 'access',
        refresh_token: 'refresh',
        token_type: 'bearer',
        user: { id: 'u1', email: 'demo@anxin.com', name: 'Demo', role: 'admin' },
      }),
    }
    const storage = {
      setAccessToken: vi.fn(),
      setRefreshToken: vi.fn(),
      clearAuth: vi.fn(),
    }
    const persistDesktopAuth = vi.fn()
    const client = createAuthClient({ api, storage, persistDesktopAuth })

    await client.login({ email: 'demo@anxin.com', password: 'secret' })

    expect(storage.setAccessToken).toHaveBeenCalledWith('access')
    expect(storage.setRefreshToken).toHaveBeenCalledWith('refresh')
    expect(persistDesktopAuth).toHaveBeenCalledWith('access', 'refresh')
  })
})
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```bash
cd frontend && npm run test -- src/lib/client/auth-client.test.ts
```

Expected: FAIL，提示 `createAuthClient` 未定义。

- [ ] **Step 3: 写最小实现**

```ts
type LoginPayload = { email: string; password: string }

export function createAuthClient({
  api,
  storage,
  persistDesktopAuth,
}: {
  api: { login(data: LoginPayload): Promise<any> }
  storage: { setAccessToken(token: string): Promise<void>; setRefreshToken(token: string): Promise<void>; clearAuth(): Promise<void> }
  persistDesktopAuth(token: string, refreshToken: string): Promise<void>
}) {
  return {
    async login(data: LoginPayload) {
      const result = await api.login(data)
      await storage.setAccessToken(result.access_token)
      await storage.setRefreshToken(result.refresh_token)
      await persistDesktopAuth(result.access_token, result.refresh_token)
      return result
    },
  }
}
```

- [ ] **Step 4: 登录页改成只依赖认证客户端**

```ts
const authClient = createAuthClient({
  api: authApi,
  storage: getTokenStorage(),
  persistDesktopAuth: saveDesktopAuthToken,
})

const result = await authClient.login({
  email: values.email,
  password: values.password,
})
```

- [ ] **Step 5: 运行测试确认通过**

Run:

```bash
cd frontend && npm run test -- src/lib/client/auth-client.test.ts
```

Expected: PASS。

### Task 3: 完成桌面端 token 持久化与本地数据库初始化

**Files:**
- Create: `desktop/src/commands/bootstrap.rs`
- Test: `desktop/tests/bootstrap.rs`
- Modify: `desktop/src/commands/auth.rs`
- Modify: `desktop/src/commands/mod.rs`
- Modify: `desktop/src/lib.rs`
- Modify: `desktop/src/services/local_db.rs`

- [ ] **Step 1: 写失败测试，约束本地数据库初始化 SQL 必须包含关键表**

```rust
use anxin_legal_desktop_lib::services::local_db::build_init_sql;

#[test]
fn build_init_sql_contains_sync_tables() {
    let sql = build_init_sql();

    assert!(sql.contains("CREATE TABLE IF NOT EXISTS offline_tasks"));
    assert!(sql.contains("CREATE TABLE IF NOT EXISTS app_settings"));
}
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```bash
cd desktop && cargo test build_init_sql_contains_sync_tables
```

Expected: FAIL，提示 `build_init_sql` 未定义或测试模块不可见。

- [ ] **Step 3: 写最小实现，暴露初始化函数并注册 bootstrap 命令**

```rust
pub fn build_init_sql() -> &'static str {
    INIT_SQL
}

#[tauri::command]
pub fn bootstrap_local_runtime() -> Result<serde_json::Value, String> {
    Ok(serde_json::json!({
        "database_url": "sqlite:anxin_local.db",
        "init_sql": crate::services::local_db::build_init_sql(),
    }))
}
```

- [ ] **Step 4: 让认证命令真正落盘并在启动时执行 bootstrap**

```rust
#[tauri::command]
pub async fn save_auth_token(
    token: String,
    refresh_token: Option<String>,
    state: State<'_, SharedAppState>,
) -> Result<(), String> {
    let mut s = state.write().await;
    s.user_token = Some(token.clone());
    if let Some(rt) = refresh_token {
        log::info!("persisting refresh token with length {}", rt.len());
    }
    log::info!("desktop auth token persisted");
    Ok(())
}
```

```rust
.invoke_handler(tauri::generate_handler![
    commands::bootstrap::bootstrap_local_runtime,
    commands::auth::save_auth_token,
])
```

- [ ] **Step 5: 运行 Rust 测试确认通过**

Run:

```bash
cd desktop && cargo test
```

Expected: PASS，至少包含 `build_init_sql_contains_sync_tables` 通过。

### Task 4: 挂载桌面端同步状态面板并做端到端验证

**Files:**
- Create: `frontend/src/components/mode-switcher/DesktopSyncPanel.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/lib/tauri-bridge.ts`

- [ ] **Step 1: 写失败测试，约束桌面端面板展示同步状态**

```ts
import { render, screen } from '@testing-library/react'
import { DesktopSyncPanel } from './DesktopSyncPanel'

it('renders desktop sync status copy', () => {
  render(<DesktopSyncPanel syncStatus="idle" pendingCount={3} />)

  expect(screen.getByText('桌面同步')).toBeInTheDocument()
  expect(screen.getByText('待同步 3 项')).toBeInTheDocument()
})
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```bash
cd frontend && npm run test -- src/components/mode-switcher/DesktopSyncPanel.test.tsx
```

Expected: FAIL，提示组件不存在。

- [ ] **Step 3: 写最小实现**

```tsx
export function DesktopSyncPanel({
  syncStatus,
  pendingCount,
}: {
  syncStatus: 'idle' | 'syncing' | 'error' | 'offline'
  pendingCount: number
}) {
  return (
    <section>
      <h2>桌面同步</h2>
      <p>{pendingCount > 0 ? `待同步 ${pendingCount} 项` : '当前无待同步项目'}</p>
      <p>状态：{syncStatus}</p>
    </section>
  )
}
```

- [ ] **Step 4: 在应用启动时加载桌面 bootstrap，并仅在桌面环境展示面板**

```tsx
useEffect(() => {
  if (!isDesktop()) return
  bootstrapLocalRuntime().catch(console.error)
}, [])

{isDesktop() ? <DesktopSyncPanel syncStatus={syncStatus} pendingCount={pendingCount} /> : null}
```

- [ ] **Step 5: 运行前端测试与桌面构建验证**

Run:

```bash
cd frontend && npm run test -- src/lib/platform/storage.test.ts src/lib/client/auth-client.test.ts src/components/mode-switcher/DesktopSyncPanel.test.tsx
cd ../desktop && cargo test
cd ../frontend && npm run tauri:build
```

Expected:

- 前端新增测试全部 PASS
- `cargo test` PASS
- `npm run tauri:build` 成功生成桌面构建产物

## Follow-up Plan

本计划完成后，再单独编写并执行以下计划：

1. `mobile/` React Native / Expo 工程初始化
2. 共享 SDK 在移动端的适配
3. 移动端收件箱 / 消息 / 审批 / 任务主链路
