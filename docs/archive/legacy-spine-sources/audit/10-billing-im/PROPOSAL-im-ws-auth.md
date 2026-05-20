# 提案：IM WebSocket URL token → 首包鉴权改造

> 关联：task-10-billing-im.md P0-4；PROJECT_STATUS S8；01-auth/PROPOSAL-token-storage.md Step 5
> 性质：实施方案（不含代码改动）
> 作者：Claude Code（审计）
> 日期：2026-05-04
> 状态：✅ 2026-05-06 已实施。Web 前端不再拼接 URL token；后端 `/im/ws` 改为首包 `auth` 鉴权并新增 `tests/test_im_websocket_auth.py`。

---

## 1. 修复前 IM ws 鉴权流程

### 1.1 前端（`frontend/src/hooks/useIMWebSocket.ts`）

| 行 | 行为 |
|---|---|
| `:60` | `const token = localStorage.getItem('access_token')` 直读 |
| `:69-70` | 拼 `wsBase`（dev 走 Vite proxy，prod 用同源）|
| `:71` | 修复前 `const wsUrl = ${wsBase}/api/v1/im/ws?...` —— **token 进入 URL** |
| `:73` | `new WebSocket(wsUrl)` 触发 HTTP Upgrade，token 落到 nginx access log + 浏览器 Network/History |
| `:75-79` | `onopen` 仅设 `isConnected=true`，**未发任何鉴权帧** |
| `:104-113` | 关闭后指数退避（1s→15s，最多 10 次）重连，每次都重新拼 URL |

### 1.2 后端（`backend/src/api/routes/im.py:193-220`）

```python
@router.websocket("/ws")
async def im_websocket(websocket, token: str = Query(...), db = Depends(get_db)):
    user_id = verify_token(token)            # 同步、无黑名单
    if not user_id:
        await websocket.close(code=4001, reason="认证失败")
        return
    await im_manager.connect(user_id, websocket)   # accept 在 connect 里做
    try:
        while True:
            data = await websocket.receive_json()
            ...
```

特征：
- token 用 FastAPI `Query(...)` 强制必填 → 没有 query 直接 422，连握手都过不去。
- `verify_token` 是同步轻量校验（仅 JWT 签名 + exp），**未走 `verify_token_with_blacklist`**（refresh 黑名单不生效；access 被踢号场景未覆盖）。
- 没有"等待首帧"的窗口，`accept()` 在 `im_manager.connect` 内部隐式完成。

### 1.3 服务层（`backend/src/services/im_hub.py:26-49`）

`im_manager.connect(user_id, ws)` 负责 `await ws.accept()` + 注册到 `active_connections[user_id]`；不参与鉴权。`disconnect` 仅负责摘除。鉴权完全是路由层的事，**改造点全部聚焦在 `routes/im.py` 与 `useIMWebSocket.ts`**。

### 1.4 暴露面

- nginx access log：`GET /api/v1/im/ws?token=eyJhbGci...` 全量留存。
- 浏览器：DevTools Network → WS 条目 URL 永久可见；history API 不会写但崩溃 dump / 截屏分享会泄漏。
- 反代日志、APM 链路追踪、CDN 边缘日志同此风险。
- access_token 默认 120 分钟有效期（`backend/src/core/config.py:39 JWT_EXPIRE_MINUTES`），泄漏即长期可用。

---

## 2. 参考实现：协作 WS 已用的"首包 token 鉴权"模式

`backend/src/api/routes/collaboration_ws.py:54-127` 是同样问题的已上线方案，可直接对齐：

1. **先 `await websocket.accept()`** —— 不再用 `Query(...)` 强制 token。
2. **保留 URL token 作为兼容路径**（`token: Optional[str] = Query(None)`）：若有则尝试 `verify_token_with_blacklist` + 查 `User`，命中则 `authenticated=True`。
3. **`asyncio.wait_for(websocket.receive_json(), timeout=15)`** 等首帧。
4. 若首帧 `type=="auth"` 且尚未鉴权 → 取 `data.token` 再走 `verify_token_with_blacklist`，仍失败 → `send_json({type:"error",...})` + `close(code=4001)` 退出。
5. 鉴权通过后再读第二帧（join / 业务），**协议层把"鉴权"和"业务首帧"分成两个独立帧**（IM 场景可简化为单帧鉴权 + 进入消息循环）。

这套模式已在 collaboration_ws 跑通，IM 复用即可，不需要再创新。

---

## 3. 实施方案

### 3.1 前端（`useIMWebSocket.ts`）

- `:71` 改为：`const wsUrl = \`${wsBase}/api/v1/im/ws\``（**不再带 query token**）。
- `:75 ws.onopen`：立即 `ws.send(JSON.stringify({type:"auth", token}))`。token 来源在 Step 5（PROPOSAL-token-storage）落地后改走 `getTokenStorage()` 抽象，过渡期仍可读 `localStorage`。
- 新增本地状态 `authState: 'pending'|'ok'|'failed'`：
  - `onopen` 后置 `pending`，启动 `setTimeout(()=>ws.close(4002,'auth timeout'), 5000)` watchdog；
  - 收到首条 `{type:"auth_ok"}` 清 watchdog，置 `ok`，`setIsConnected(true)`；
  - 收到 `{type:"error", code:4001}` 或被服务端关闭 → 置 `failed`，**不进入指数退避**（避免坏 token 死循环重连）。
- `setIsConnected(true)` 从 `onopen` 移到 `auth_ok`，避免业务以为已可用就 send 业务消息。

### 3.2 后端（`api/routes/im.py:193-220`）

```python
@router.websocket("/ws")
async def im_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None),     # 兼容期保留
    db: AsyncSession = Depends(get_db),
):
    await websocket.accept()

    user_id: Optional[str] = None

    # 兼容路径：URL 带 token 时先尝试（仅过渡期）
    if token:
        user_id = await verify_token_with_blacklist(token)
        # 同时打 metric: im.ws.auth.via_url_total

    if not user_id:
        try:
            first = await asyncio.wait_for(websocket.receive_json(), timeout=3)
        except (asyncio.TimeoutError, WebSocketDisconnect):
            await websocket.close(code=4002, reason="auth timeout"); return
        if first.get("type") != "auth":
            await websocket.close(code=4001, reason="first frame must be auth"); return
        user_id = await verify_token_with_blacklist(first.get("token", ""))
        # metric: im.ws.auth.via_first_frame_total

    if not user_id:
        await websocket.send_json({"type":"error","code":4001,"message":"认证失败"})
        await websocket.close(code=4001, reason="认证失败"); return

    await websocket.send_json({"type":"auth_ok"})
    # 注意：im_manager.connect 当前实现也会 accept；需把 accept 抽出/调整为幂等
    await im_manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            ...
```

要点：
- 首帧超时收紧到 **3 s**（IM 是高频建连，不需要 collaboration_ws 的 15 s 宽容）。
- 切到 `verify_token_with_blacklist`（异步）—— 顺手覆盖被踢号 / refresh 拉黑场景（S2 / S10）。
- 注意 `im_manager.connect` 当前内部会 `ws.accept()`：改造时 hub 的 `accept()` 调用需移除或改为幂等（已 accept 则跳过）。
- 关闭码约定：`4001`=认证失败、`4002`=认证超时、`4003`=ticket 无效（如启用 ticket 路径）。

### 3.3 是否需要 `POST /im/ticket` 短期 ticket

TASK-10 P0-4 给了"首包 token 或 ticket"两种选择。结论：**首包 token 模式即可满足 P0**，不引入 ticket。

理由：
- ticket 模式（≤60 s 一次性）主要解决"WS 客户端不能发自定义首帧"的端（极个别小程序运行时）。Web/Tauri 都能发首帧。
- 引入 ticket 等于多一张表 / 多一个端点 / 多一份过期清理逻辑，工程成本高于收益。
- 若未来要给小程序端开 IM，再叠加 ticket 路径作为可选硬化（与 PROPOSAL-token-storage Step 5 兼容）。

---

## 4. 兼容期策略

- **双轨期 = 14 天**（与 TASK-10 P0-4 风险护栏第 6 条对齐）：URL `?token=` 与首包 `auth` 两条路径同时识别；前端按版本切到首包，老客户端继续走 URL。
- 后端打 metric：`im.ws.auth.via_url_total` / `im.ws.auth.via_first_frame_total`，前者归零持续 7 天后再关闭 URL 路径。
- 关 URL 路径 = 把 `Query(None)` 段删掉、回到强制要求首帧。
- 灰度 flag：环境变量 `IM_WS_AUTH_MODE` ∈ `{legacy, dual, first_frame_only}`，与 PROPOSAL-token-storage 的 `AUTH_TOKEN_STORAGE_MODE` 相互独立，避免一锁锁全部。
- 回滚：任意阶段把 flag 调回 `legacy` 即恢复 URL 必填，无 schema 变更，无数据迁移。

---

## 5. 测试方案

### 5.1 后端 pytest（3 个 case）

放在 `backend/tests/test_im_ws_auth.py`（新建）：

1. `test_im_ws_first_frame_auth_success`
   - 用 `httpx.AsyncClient` + `websockets` 直连，不带 query；onopen 后发 `{type:"auth", token: <valid>}`；断言收到 `{type:"auth_ok"}` 且后续可发 `typing` 帧。
2. `test_im_ws_first_frame_auth_invalid_token`
   - 同上但 token 替换为 `"bad"`；断言收到 `{type:"error",code:4001}` 且服务端 `close(code=4001)`，连接终止。
3. `test_im_ws_first_frame_auth_timeout`
   - 不带 query、不发首帧；wait 4 s；断言连接被 `close(code=4002)`，`reason="auth timeout"`。

可选第 4 个：`test_im_ws_url_token_dual_mode`（兼容期回归）—— 仅 `IM_WS_AUTH_MODE=dual` 下断言 URL token 仍可用。

### 5.2 前端 Playwright e2e（1 个）

`frontend/e2e/im-ws-auth.spec.ts`：
- 登录后打开 Messages 页面。
- `page.evaluate` 读取 WS 实例 URL（通过 `window.performance.getEntriesByType('resource')` 或注入 `WebSocket.prototype.send` 的 spy）。
- 断言 URL **不含** `?token=`，且首条 send 的 frame 是 `{"type":"auth", ...}`。
- 断言 5 s 内 `isConnected===true` 且能成功发一条 typing。

### 5.3 不退化基线

- `cd backend && pytest -k "im"` 不退化原 `test_im_*.py`。
- `cd backend && pytest`（当前默认基线 `354 passed, 1 skipped` 不退化，TASK-10 DoD 第 5 条）。

---

## 6. 与 token 存储 Step 5 的协调

PROPOSAL-token-storage Step 5 与本提案是**同一改动**的一体两面，必须合并 PR：

- Step 5 的"前端切首包鉴权"= 本提案 §3.1，文案口径统一即可。
- Step 5 把 access_token 从 localStorage 移到 in-memory（选项 B）后：
  - `useIMWebSocket.ts:60` 不再 `localStorage.getItem`，改走 `useAuthStore.getState().token` 或 `getTokenStorage().getAccessToken()`；
  - 内存 token 在刷新瞬间为 null → 必须等 `silentRefresh` hydration 完成后再触发 `connect()`，否则会发空 token 首帧被 4001 断开。
- cookie 模式（选项 A，未采纳）下 ws 路径的差异：浏览器同源 ws 会自动带 cookie，可在 `accept` 后从 `websocket.cookies` 读 access；跨源不带 cookie。**当前选项 B 不走 cookie，ws 路径与本提案一致**，不需要分支。
- Tauri 端：仍走 Bearer + plugin-store；ws 首帧同样从 `getTokenStorage()` 读，无差别。

---

## 7. 工时估算

| 步骤 | 工时 |
|---|---|
| 后端首帧鉴权 + dual flag + metric | 0.5 天 |
| `im_hub.connect` accept 幂等性调整 | 0.25 天 |
| 前端 onopen 首帧 + watchdog + isConnected 时序 | 0.5 天 |
| 3 个 pytest + 1 个 e2e | 0.75 天 |
| 双轨期观测 + 灰度 flag 切换 | 0.25 天（不含 14 天观测） |
| **合计** | **~2.25 天** |

注：PROPOSAL-token-storage Step 5 的 1.5 天估算已包含上述前端 0.5 天，合并 PR 时按 2.25 天而非简单相加。

---

## 8. 风险护栏

- **不允许 big-bang**：`IM_WS_AUTH_MODE=dual` 至少 14 天，URL 调用归零再切 `first_frame_only`。
- **重连风暴**：坏 token 必须在前端 `failed` 态阻断指数退避；后端可叠加 IP 维度滑动窗口（10 次/分钟）防爆。
- **`im_manager.connect` accept 幂等**：当前实现会再次 `accept()`，已 accept 后再 accept 抛 `RuntimeError`；改造必须同步调整 hub 或路由层不重复 accept。
- **`verify_token` → `verify_token_with_blacklist`**：异步 + DB 查询，注意路由内不要把 db session 的生命周期跨到首帧之外。
- **首帧超时 3 s**：移动弱网下偏紧；上线前先在 staging 用 `tc qdisc` 模拟 RTT 800ms 验证；必要时放宽到 5 s。
- **过渡期 metric 必须先有再切**：没有 `via_url_total / via_first_frame_total` 双指标就关 URL 路径=黑灯切换，严格禁止。
- **不动 `prompts/`**；不动 `.env`；不动 `backend/src/core/security.py` 公共 API（仅在路由内换调用）。
- **PR 拆分**：建议本提案单独成 PR（与 TASK-10 其他 P0 解耦），便于回滚。
- **预审**：协议层变更（首帧约定、关闭码语义）属对前端/桌面端契约级改动，PR 提交前必须用户预审。

---

> 完成此提案后，对应 task-10-billing-im.md P0-4 验收点（"WS URL 不再含 token + 首帧鉴权 + 3 个 pytest + 1 个 e2e 全绿"）。
