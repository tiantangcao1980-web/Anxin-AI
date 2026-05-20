# 提案：匿名聊天双 token 拆分

> 来源任务：TASK-09 P0-2（`backend/src/api/routes/anonymous_chat.py:136-169`），对应 PRD 差分 S7
> 作者：Claude Code 调研
> 状态：待实施（**仅方案，不改代码**）

## 1. 现状（grep 结果）

### 1.1 后端 create_room 当前签名

`backend/src/api/routes/anonymous_chat.py:136-172`：

```python
@router.post("/rooms", response_model=CreateRoomResponse)
async def create_room(
    req: CreateRoomRequest,
    request: Request,
    _: None = Depends(rate_limit(limit=10, window=300, endpoint="anon_chat_create", by_user=False)),
):
    ...
    return CreateRoomResponse(
        room_id=room_id,
        user_token=user_token,    # ← u-xxxx
        lawyer_token=lawyer_token,  # ← l-xxxx
        ...
    )
```

- 仅挂 `rate_limit(by_user=False)`，**无 `Depends(get_current_user_required)`**
- 一次性返回双方 token，且 `req.consultation_id` 仅落盘不校验
- 任意未登录请求都能拿到 `lawyer_token`，可冒充律师建立 WebSocket（`anonymous_chat.py:259-270` 的 `_get_role_by_token` 仅按字符串前缀比对内存映射）

### 1.2 前端调用方

唯一调用点：`frontend/src/pages/FindLawyer.tsx:103-118`（用户侧"进入匿名聊天室"按钮）：

```ts
const result = await anonymousChatApi.createRoom({
  consultation_id: consultationId || undefined,
  lawyer_name: selectedLawyer?.real_name,
});
setChatRoomId(result.room_id);
setChatToken(result.user_token);  // 仅用 user_token
```

`frontend/src/lib/api.ts:2725-2737` 的 `anonymousChatApi`：`createRoom` / `getRoomInfo(roomId, token)` / `revealIdentity(roomId, token)`。前端**当前仅消费 `user_token`**，`lawyer_token` 没有任何前端入口在使用——意味着 lawyer 一侧的 IM 房间初始化路径目前**根本未实装**，这是好消息：拆分不会破坏已有律师端登录流程。

### 1.3 是否有"用户 → 拿自己 token"独立接口

**没有**。当前只有：
- `POST /rooms` → 一次返回双 token
- `GET /rooms/{id}` → 输入任意一个 token 校验返回 RoomInfo
- `POST /rooms/{id}/reveal` → 同上
- `WS /ws/{id}?token=...` → 同上

### 1.4 关联模型

`backend/src/models/lawyer_matching.py:120-168` `Consultation` 已有 `user_id` 与 `matched_lawyer_id` 字段，是天然的"谁是发起人 / 谁是律师"权威源。`anonymous_chat.py` 的 `ChatRoom` 当前为内存 Pydantic 模型，**无 lawyer_user_id 字段**。

---

## 2. 关键决策

| 选项 | 描述 | 优点 | 缺点 |
|---|---|---|---|
| **A. 单端点 + 拉取律师 token** | `create_room` 仅返回 `room_id` + 用户自己的 token；律师调 `GET /rooms/{id}/lawyer-token`，后端校验 `current_user.id == consultation.matched_lawyer_id` 后返回 | 端点最少；与 TASK-09 文档"`my-token` 受保护接口"措辞一致 | 律师无显式"认领"动作，撮合状态机无入口；token 可被多次拉取，需要做单次发放语义 |
| **B. 拆分两个端点** | `POST /rooms`（用户发起，含 `Depends(get_current_user_required)`）+ `POST /rooms/{id}/lawyer-join`（律师认领，幂等，校验 `matched_lawyer_id`） | 撮合状态机有显式动作点；可与"接单流程"打通；可记录"律师何时进入"审计 | 多 1 个端点；前端需为律师侧新增调用 |

**推荐：选项 B（带选项 A 的兼容口）**。理由：

1. PRD S7 的安全目标本质是"持有 user_token 的人不能伪造 lawyer 身份"，二者都满足；但选项 B 把"律师认领"显式化，与 `Consultation.matched_lawyer_id` 状态机自然耦合，复用 task 8b 律师大厅"接单"逻辑（`/lawyer/hall/{id}/accept`）后再发 token。
2. 选项 B 的 `lawyer-join` 等价于"我，律师 X，认领此咨询并领取 token"——审计、限流、防刷都可独立处理。
3. 选项 B 同时附带一个 `GET /rooms/{id}/my-token`（**两边复用**，已认领后律师可重取，符合 task 文档措辞）。

---

## 3. 实施方案

### 3.1 路由签名草稿

```python
# 1) 用户发起：必须登录，且必须是 consultation 所有者
@router.post("/rooms", response_model=CreateRoomResponse)
async def create_room(
    req: CreateRoomRequest,
    user: User = Depends(get_current_user_required),
    _: None = Depends(rate_limit(limit=10, window=300, endpoint="anon_chat_create", by_user=True)),
):
    if req.consultation_id:
        consultation = await consultation_repo.get(req.consultation_id)
        if not consultation or consultation.user_id != user.id:
            raise HTTPException(403, "无权为此咨询创建聊天室")
    # 仅生成 user_token；lawyer_token 留空，由 lawyer-join 时签发
    ...
    return CreateRoomResponse(room_id=..., my_token=user_token, role="user", ...)

# 2) 律师认领：必须是 matched_lawyer
@router.post("/rooms/{room_id}/lawyer-join", response_model=JoinRoomResponse)
async def lawyer_join(
    room_id: str,
    user: User = Depends(get_current_user_required),
    _: None = Depends(rate_limit(limit=20, window=300, endpoint="anon_chat_join", by_user=True)),
):
    room = _get_room(room_id)
    consultation = await consultation_repo.get(room.consultation_id)
    if not consultation or consultation.matched_lawyer_id != user.id:
        raise HTTPException(403, "您不是此咨询的匹配律师")
    if not room.lawyer_token:
        room.lawyer_token = f"l-{uuid.uuid4().hex[:16]}"
        room.lawyer_user_id = user.id
    return JoinRoomResponse(room_id=room_id, my_token=room.lawyer_token, role="lawyer")

# 3) 受保护重取：双方各自取自己的 token（task 文档措辞）
@router.get("/rooms/{room_id}/my-token")
async def get_my_token(
    room_id: str,
    user: User = Depends(get_current_user_required),
):
    room = _get_room(room_id)
    consultation = await consultation_repo.get(room.consultation_id)
    if user.id == consultation.user_id:
        return {"token": room.user_token, "role": "user"}
    if user.id == consultation.matched_lawyer_id and room.lawyer_token:
        return {"token": room.lawyer_token, "role": "lawyer"}
    raise HTTPException(403, "无权访问该聊天室")
```

### 3.2 数据模型变化

`ChatRoom` Pydantic 内存模型新增字段：
- `user_user_id: str`（必填，发起用户 ID）
- `lawyer_user_id: Optional[str]`（律师认领后填）
- `lawyer_token: Optional[str]`（默认 None，认领后签发）

**不需要 DB schema 变更**——`ChatRoom` 当前就是内存 dict，迁移到 Redis/DB 是任务 10 的事；本次只动 Pydantic + 内存映射。

### 3.3 前端配合改动

- `frontend/src/lib/api.ts:2725` `anonymousChatApi.createRoom` 返回类型改为 `{ room_id, my_token, role }`，不再读 `user_token`
- `frontend/src/pages/FindLawyer.tsx:111` `setChatToken(result.user_token)` → `setChatToken(result.my_token)`
- 新增 `anonymousChatApi.lawyerJoin(roomId)`（律师端，task 8b 律师大厅"接单"成功后跳转聊天室前调用）
- 律师端 IM 入口（task 10 IM hub 落地时统一）调 `lawyer-join` 拿 token 后再 `AnonymousChatRoom role="lawyer"`

---

## 4. 兼容性

- **老前端**调旧 `POST /rooms` 仍能跑——若**未带 Authorization 头**，401；**带头但无 consultation_id**，可放行（保留 dev/演示路径，仅签 user_token 单边）。
- 旧响应 `user_token` / `lawyer_token` 字段在过渡期保留（`user_token = my_token`，`lawyer_token = None`），避免类型断言炸；下个版本删除。
- 短期 deprecation 期：**1 周**。期间 `lawyer_token` 字段始终为 `None`，老律师客户端发现拿不到 token 时降级到"提示更新"。
- 鉴于 grep 显示前端**没有**消费 `lawyer_token` 的代码路径，实质兼容风险极低。

---

## 5. 测试方案（先写失败 test 再改实现）

`backend/tests/test_anonymous_chat_token.py`（新文件）至少 4 个 case：

1. `test_anonymous_create_room_requires_owner`：未登录调 `POST /rooms` → 401；登录但 `consultation_id` 不属于 self → 403
2. `test_anonymous_create_room_returns_only_self_token`：成功创建后响应 JSON 不含 `lawyer_token` 键（或为 None），仅 `my_token + role="user"`
3. `test_anonymous_lawyer_join_rejects_non_matched`：B 律师调 `POST /rooms/{id}/lawyer-join` 但 `consultation.matched_lawyer_id != B.id` → 403
4. `test_anonymous_lawyer_join_returns_lawyer_token`：匹配律师调用 → 返回 `my_token` 以 `l-` 开头；二次调用幂等返回同一 token
5. （可选）`test_anonymous_my_token_isolation`：A 用户调 `/my-token` 仅得 `u-`，永远拿不到 `l-`

**E2E**：`frontend/e2e/anonymous-chat.spec.ts`（新增）：用户登录 → 发起咨询 → 进入聊天室 → 验证只拿到 1 个 token；用 Playwright 拦截 network 断言响应 schema。

---

## 6. 工时估算

| 子项 | 工时 |
|---|---|
| 后端路由 + 内存模型 + consultation 校验 | 0.5d |
| 失败测试 → 通过测试（5 个 pytest + 1 个 e2e） | 0.5d |
| 前端 api.ts + FindLawyer.tsx 字段改名 | 0.25d |
| 律师端 lawyer-join 调用接入（task 8b 律师大厅协同） | 0.25d |
| 文档 + memory 沉淀 + PR 描述 | 0.25d |
| **合计** | **1.75d** |

---

## 7. 风险护栏

- **影响所有匿名咨询业务流**：用户 → 律师匹配 → 进聊天室是当前 V2 主链路，前后端必须同时发版，不能仅发后端
- **灰度策略**：保留旧响应字段（`user_token` 别名 `my_token`）1 周；新前端仅读 `my_token`；旧前端仍可工作但拿不到 lawyer_token
- **审计**：lawyer_join 必须写 audit_service 日志（律师 ID、room_id、consultation_id、ts），便于事后追责
- **PR 提交前用户预审**：token 颁发授权链属敏感安全面（task 文档第 5 节明确点名）
- **不动 `consultation_id` 为空的 dev 路径**（演示/集成测试需要），仅在 `consultation_id` 非空时强制 owner 校验
- **回写**：完成后更新 `docs/audit/00-platform/01-prd-reality-gap.md` 表 2 中 S7 行 🔴 → ✅，PR 描述贴失败 → 通过测试截图
