# API 设计规范

> 强制规范。所有新增/修改后端 API 必须遵守。

## 1. 路径设计

### 1.1 资源路径

| 规则 | 示例 |
|---|---|
| **小写 + kebab-case** | `/api/v1/lawyer-matching` ✅ ；`/api/v1/lawyerMatching` ❌ |
| **复数资源名** | `/api/v1/contracts` ✅ ；`/api/v1/contract` ❌ |
| **嵌套不超 2 层** | `/api/v1/cases/{id}/events` ✅ ；`/api/v1/orgs/{oid}/users/{uid}/tasks/{tid}/comments` ❌ |
| **动作用 HTTP 动词，避免在 URL 里** | `POST /api/v1/contracts` ✅ ；`POST /api/v1/createContract` ❌ |
| **非 CRUD 操作用子资源** | `POST /api/v1/contracts/{id}/sign` ✅ |

### 1.2 版本化

- 全部 API 必须挂在 `/api/v1/` 或 `/api/v3/`（V3 为智能助手新接口）
- 破坏性变更走新版本，不在旧版本上改

### 1.3 双客户端分离（V2 架构）

| 前缀 | 适用 |
|---|---|
| `/api/v1/*` | 通用（需求方默认） |
| `/api/v3/*` | V3 智能助手新能力 |
| `/api/v1/billing/v2/*` | V2 订阅 / 商业化 |
| `/api/v3/personas/<persona>/*` | persona 专属能力 |

## 2. HTTP 方法

| 方法 | 用途 | 幂等 |
|---|---|---|
| `GET` | 查询 | ✅ |
| `POST` | 创建 / 触发动作 | ❌ |
| `PUT` | **完整**替换 | ✅ |
| `PATCH` | 部分更新 | 业务决定 |
| `DELETE` | 删除（软删建议返回 204） | ✅ |

**禁止**：用 `GET` 触发副作用、用 `POST` 实现查询（除非有大量 body）。

## 3. 响应包装（UnifiedResponse）

**所有路由必须返回**：

```json
{
  "code": 0,
  "data": { ... },
  "message": "ok",
  "request_id": "uuid-v4"
}
```

辅助函数：`backend/src/api/response.py`（或同类）。**禁止**返回裸 dict 或裸 list。

## 4. 错误码

`code` 编码空间：

| 范围 | 含义 |
|---|---|
| `0` | 成功 |
| `1xxx` | 客户端错误（参数 / 鉴权 / 权限） |
| `2xxx` | 业务错误（资源不存在 / 状态非法 / 业务规则违反） |
| `3xxx` | 外部依赖错误（LLM / 第三方 API / OAuth） |
| `5xxx` | 服务端错误（数据库 / 内部异常） |

具体编码集中在 `backend/src/api/error_codes.py`。

**禁止**：每个域自己造编码、直接抛 HTTPException(500)。

## 5. 状态码

| 场景 | HTTP 状态 | code |
|---|---|---|
| 成功 | 200 / 201 / 204 | 0 |
| 参数错误 | 400 | 1xxx |
| 未认证 | 401 | 1001 |
| 无权限 | 403 | 1003 |
| 资源不存在 | 404 | 2001 |
| 资源冲突 | 409 | 2002 |
| 限流 | 429 | 1004 |
| 服务端错误 | 500 | 5xxx |
| 服务不可用 | 503 | 5003 |

## 6. 请求与响应类型

### 6.1 必须用 Pydantic Schema

```python
# backend/src/api/routes/schemas/contract.py
from pydantic import BaseModel, Field

class ContractCreateRequest(BaseModel):
    title: str = Field(..., max_length=200)
    party_a: str
    party_b: str
    content: str

class ContractResponse(BaseModel):
    id: str
    title: str
    status: str
    created_at: datetime
```

路由：

```python
@router.post("/contracts", response_model=UnifiedResponse[ContractResponse])
async def create_contract(req: ContractCreateRequest, ...):
    ...
```

**禁止**：直接 `Dict[str, Any]` 接收 body / 返回未校验对象。

### 6.2 Schema 命名

- `XxxCreateRequest` / `XxxUpdateRequest` / `XxxResponse`
- `XxxListResponse` 含分页
- Schema 文件：`backend/src/api/routes/schemas/<domain>.py`

## 7. 分页

```json
{
  "code": 0,
  "data": {
    "items": [...],
    "total": 1234,
    "page": 1,
    "page_size": 20,
    "has_next": true
  }
}
```

- `page` 从 1 开始
- `page_size` 默认 20，最大 100
- 大数据集用 `cursor` 分页：`{ "cursor": "...", "next_cursor": "..." }`

## 8. 鉴权

| 类型 | 实现 | 适用 |
|---|---|---|
| JWT Bearer | `Authorization: Bearer <access>` | 主流业务 |
| Refresh Cookie | `HttpOnly` cookie | refresh 流 |
| API Key | `X-API-Key: <key>` | CLI / 集成 |
| HMAC 签名 | `X-Signature: ...` | webhook |

路由必须显式声明依赖：

```python
@router.get("/contracts", dependencies=[Depends(require_auth)])
```

**禁止**：路由内部手动解析 token / 跳过认证。

## 9. 隐私模式 Header

所有路由必须支持 `X-Privacy-Mode` Header：

```python
from src.core.privacy import get_privacy_mode

@router.post("/chat/send")
async def send(req: ChatRequest, mode: PrivacyMode = Depends(get_privacy_mode)):
    if mode == PrivacyMode.LOCAL and req.requires_cloud:
        raise BizException(2003, "本地模式不可用：需要云端能力")
```

详见 [docs/ARCHITECTURE.md](../ARCHITECTURE.md) §4 三态模式。

## 10. 智能体治理六层校验（V3）

涉及 Skills / MCP / 远控 / 浏览器执行 / 代码执行 / 批量外发的接口必须六层校验通过：

```
subscription + role + permission + risk_level + privacy_mode + device_trust
```

详见 [openspec/00-intelligent-assistant-platform-spec.md §3.7](../openspec/00-intelligent-assistant-platform-spec.md)。

## 11. 限流

- 默认全局限流：100 req/min/IP
- 敏感接口（登录 / 注册 / 忘密 / 重发码）：5 req/min/IP
- 限流后端：Redis；fail-closed（Redis 不可用时拒绝）

## 12. 幂等

| 场景 | 实现 |
|---|---|
| Webhook | `Idempotency-Key` 表 + 24h TTL |
| 支付下单 | `out_trade_no` 业务键 |
| 重试任务 | 任务 ID + 状态机 |

## 13. WebSocket

- 路径：`/api/v1/<domain>/ws/{conv_id}` 或 `/api/v3/...`
- 首包必须发 token 鉴权，**禁止**信任 URL query 参数中的 user_id
- 心跳：30s 一次
- 断线重连：客户端实现指数退避

## 14. 流式响应（SSE / 流式 JSON）

```
data: {"event": "token", "content": "..."}\n\n
data: {"event": "done", "usage": {...}}\n\n
```

- 必须支持中断（前端 cancel → 后端 close）
- 错误也通过 SSE 推送：`data: {"event": "error", "message": "..."}`

## 15. 文件上传

```python
from fastapi import UploadFile, File
from src.api.routes.upload_validation import read_validated_upload_file

@router.post("/upload")
async def upload(file: UploadFile = File(...), ...):
    content = await read_validated_upload_file(file, max_size_mb=10)
```

三重校验：扩展名 + MIME + 内容（已封装）。

## 16. CORS

`backend/src/core/config.py` 的 `CORS_ORIGINS` 显式白名单；**禁止** `*`。

## 17. OpenAPI 文档

- Swagger UI：`/docs`（仅 `DEV_MODE=true` 暴露）
- ReDoc：`/redoc`（同上）
- 路由必须有 `summary` + `description` + 示例

## 18. 路由文件结构

```
backend/src/api/routes/
├── <domain>.py              业务路由（CRUD + 动作）
├── schemas/<domain>.py      请求/响应 schema
└── chat_handlers/            子模块（域较大时）
```

每个路由必须：
1. 文件顶部 docstring 说明域职责
2. 路由用 `prefix=` 统一前缀
3. `tags=` 用中文/英文一致

## 19. 服务层分离

**禁止**：路由内直接写数据库查询 / 业务逻辑。

正确分层：

```
api/routes/<domain>.py    →  参数校验 + 鉴权 + 调用 service
services/<domain>_service.py → 业务逻辑 + 编排
models/<domain>.py        →  ORM + Schema
```

详见 [code-style.md §1](./code-style.md#1-python).

## 20. 速查反例

```python
# ❌ 禁止
@router.get("/getContract")          # 动词在 URL
@router.post("/contracts")
async def x(body: dict): ...         # 无 Pydantic
    return {"contract": ...}          # 无 UnifiedResponse

# ✅ 正确
@router.post("/contracts", response_model=UnifiedResponse[ContractResponse])
async def create_contract(
    req: ContractCreateRequest,
    user: User = Depends(require_auth),
    mode: PrivacyMode = Depends(get_privacy_mode),
):
    contract = await contract_service.create(req, user, mode)
    return success(ContractResponse.model_validate(contract))
```
