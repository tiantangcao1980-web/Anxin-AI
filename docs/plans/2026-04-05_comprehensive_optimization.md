# 全面优化项目体验 (Comprehensive Experience Optimization) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 结合用户角色视角，从安全、高效、稳定及高质量产品体验四个维度全面优化 Anxin-Smart-Legal-Services。

**Architecture:** 
1. **安全**: 将前端 `refresh_token` 存储由 `localStorage` 迁移至安全的 `HttpOnly Cookie`，消除 XSS 窃取风险。
2. **高效**: 引入全局单例 `httpx.AsyncClient` 复用 HTTP 连接池，消除每次 LLM 调用的 TCP/TLS 握手延迟。
3. **稳定**: 在核心 Agent 逻辑中引入业界标准 `Tenacity` 重试框架，替换手写的循环退避重试，提升代码可靠性。
4. **高质量体验**: 前端优化 WebSocket 错误捕获，将纯文本错误提示升级为带“重试”或“重新表述”等按钮的 Actionable UI。

**Tech Stack:** FastAPI, React, Tenacity, HTTPX

---

### Task 1: 安全优化 - HttpOnly Cookie 迁移 (Security)

**Files:**
- Modify: `backend/src/api/routes/auth.py`
- Modify: `frontend/src/pages/Login.tsx`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: 后端 auth.py 改写 login 与 refresh 路由**
在 `login_for_access_token` 和 `refresh_access_token` 路由中，不再于 JSON 体返回 `refresh_token`，而是通过 `Response.set_cookie` 写入 HttpOnly 的 cookie。

```python
# in backend/src/api/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from src.core.config import settings

# In login_for_access_token:
response.set_cookie(
    key="refresh_token",
    value=refresh_token,
    httponly=True,
    secure=not settings.DEV_MODE,
    samesite="lax",
    max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
)
return {"access_token": access_token, "token_type": "bearer", "user": user_data}

# In refresh_access_token:
# extract from request.cookies.get("refresh_token")
```

- [ ] **Step 2: 前端 api.ts 拦截器改造**
在 `api.ts` 的 `axios` 拦截器中，移除从 `localStorage` 读取 `refresh_token` 的逻辑，并配置 `withCredentials: true`。

```typescript
# in frontend/src/lib/api.ts
api.defaults.withCredentials = true; // 确保跨域请求携带 cookie
// 在 401 拦截器中，直接请求 /auth/refresh，浏览器会自动携带 HttpOnly cookie
```

- [ ] **Step 3: 前端 Login.tsx 清理 localStorage**
登录成功后不再调用 `localStorage.setItem('refresh_token', ...)`，只需存 `access_token` 或依赖闭包。

```typescript
// in frontend/src/pages/Login.tsx
localStorage.setItem('access_token', data.access_token);
// 移除 localStorage.setItem('refresh_token', data.refresh_token);
```

- [ ] **Step 4: 测试登录与刷新机制**
启动前后端，执行登录，观察浏览器 Network 面板是否收到 `Set-Cookie: refresh_token=...; HttpOnly`。然后手动将 `access_token` 过期，测试自动刷新是否成功。

- [ ] **Step 5: 提交变更**
```bash
git add backend/src/api/routes/auth.py frontend/src/pages/Login.tsx frontend/src/lib/api.ts
git commit -m "feat(security): migrate refresh_token to HttpOnly cookie to prevent XSS"
```

### Task 2: 高效优化 - HTTP 连接池复用 (Efficiency)

**Files:**
- Modify: `backend/src/services/ai_assistant_service.py` (及 `llm_service.py` 视具体位置而定)

- [ ] **Step 1: 建立全局 httpx.AsyncClient 单例**
如果 `ai_assistant_service.py` 或 `llm_service.py` 每次请求都新开 `httpx.AsyncClient`，需要改为复用。

```python
import httpx

_http_client: httpx.AsyncClient | None = None

def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=60.0)
    return _http_client
```

- [ ] **Step 2: 替换调用逻辑**
在 `_call_llm` 等方法中，使用全局 client。

```python
client = get_http_client()
response = await client.post(...)
```

- [ ] **Step 3: 测试模型调用**
调用一个 AI Agent 或发起一次对话，观察是否成功，且响应速度是否由于连接复用而提升。

- [ ] **Step 4: 提交变更**
```bash
git add backend/src/services/ai_assistant_service.py
git commit -m "perf(llm): implement httpx.AsyncClient connection pool singleton"
```

### Task 3: 稳定优化 - 引入 Tenacity 重试机制 (Stability)

**Files:**
- Modify: `backend/src/agents/base.py`

- [ ] **Step 1: 引入 tenacity**
替换原本手写的 `for attempt in range(...)`。

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError))
)
async def _call_llm_with_retry(self, ...):
    # 纯业务逻辑，发生异常直接 raise
```

- [ ] **Step 2: 移除手工重试代码**
清理 `agents/base.py` 内部的 `while` 或 `for` 重试嵌套，使代码拉平。

- [ ] **Step 3: 测试重试机制**
编写/运行单元测试 `pytest backend/tests/test_chat.py` 确保核心流程不受影响。

- [ ] **Step 4: 提交变更**
```bash
git add backend/src/agents/base.py
git commit -m "refactor(stability): replace manual retry loop with tenacity framework in base agent"
```

### Task 4: 体验优化 - 交互式错误提示 (UX)

**Files:**
- Modify: `frontend/src/components/chat/wsMessageHandlers.ts`
- Modify: `frontend/src/components/chat/Chat.tsx` (或者错误卡片组件)

- [ ] **Step 1: 扩充 Message 错误类型**
允许 Message 带有 `actionable` 字段。

```typescript
// in message types
export interface Message {
  // ...
  isError?: boolean;
  actionable?: 'retry' | 'switch_model';
}
```

- [ ] **Step 2: WS handler 抛出带状态的错误**
当收到后端超时或失败信号时，在推入 store 时附带 actionable 状态。

```typescript
// in wsMessageHandlers.ts
addMessage({
  id: msgId,
  role: 'assistant',
  content: '抱歉，当前思考时间过长或模型繁忙，请重试。',
  isError: true,
  actionable: 'retry'
});
```

- [ ] **Step 3: Chat UI 渲染错误操作按钮**
在消息气泡渲染中，若 `isError` 且 `actionable` 存在，渲染一个操作按钮。

```tsx
{message.isError && message.actionable === 'retry' && (
  <Button size="sm" variant="outline" onClick={() => handleRetry(message.id)}>
    重新生成
  </Button>
)}
```

- [ ] **Step 4: 测试 UI 表现**
断开网络或模拟后端 500 报错，观察气泡是否出现重试按钮，点击重试是否再次发送。

- [ ] **Step 5: 提交变更**
```bash
git add frontend/src/components/chat/
git commit -m "feat(ux): add actionable retry button for chat error messages"
```
