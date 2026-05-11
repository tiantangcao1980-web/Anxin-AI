# app_authorization — 通用 OAuth 应用授权框架（P4-A）

> 第三方应用接入的统一抽象层。让 P4-B/C/D/E 各家 provider（飞书 / 钉钉 / Notion / Shopify ...）
> 只需写一个文件即可上线，前端无需改任何代码。

## 模块结构

```
app_authorization/
├── __init__.py        # 公开 API 汇总
├── base.py            # BaseOAuthProvider + OAuthTokenBundle
├── registry.py        # OAuthProviderRegistry + @register_provider 装饰器
├── token_store.py     # Fernet 加密 token 持久化
├── oauth_flow.py      # OAuthFlowService（start/callback/refresh/disconnect）
├── models.py          # AppAuthorization + AppToken ORM
├── providers/
│   ├── __init__.py    # _autoload_providers() 自动扫描 *_oauth.py
│   ├── feishu_oauth.py     ← P4-B
│   ├── dingtalk_oauth.py   ← P4-C
│   ├── notion_oauth.py     ← P4-D
│   └── shopify_oauth.py    ← P4-E
└── README.md
```

## 接口契约（强约束）

```python
from src.services.app_authorization import BaseOAuthProvider, OAuthTokenBundle

class MyProvider(BaseOAuthProvider):
    provider_id = "my_app"          # 全小写 snake_case
    display_name = "My App"
    category = "office"             # office | ecommerce | content | crm | design | info_source | compliance
    icon_url = "https://..."        # 可选
    default_scopes = ["read", "write"]

    async def authorize_url(self, state, redirect_uri, scopes=None) -> str: ...
    async def exchange_code(self, code, redirect_uri) -> OAuthTokenBundle: ...
    async def refresh_token(self, refresh_token) -> OAuthTokenBundle: ...
    async def revoke(self, access_token) -> None: ...
    async def get_user_info(self, access_token) -> dict: ...
```

⚠️ 字段名 / 方法签名 / 返回类型严禁改动 —— OAuthFlowService 调用链对所有 provider 一致。

## 接入新 provider 的 5 步指南

1. **新建文件** `providers/<name>_oauth.py`（必须以 `_oauth.py` 结尾，否则不会被自动加载）。
2. **继承基类** 并实现 5 个抽象方法。
3. **加装饰器** `@register_provider`：

   ```python
   from src.services.app_authorization import (
       BaseOAuthProvider, OAuthTokenBundle, register_provider,
   )

   @register_provider
   class MyAppOAuthProvider(BaseOAuthProvider):
       provider_id = "myapp"
       ...
   ```

4. **配置环境变量**（在 `core/config.py` 添加 `MYAPP_CLIENT_ID` / `MYAPP_CLIENT_SECRET`），
   provider 内部用 `from src.core.config import settings` 读取。
5. **写测试** `tests/providers/test_<name>_oauth.py`，mock httpx 验证：
   - `authorize_url` 拼接正确
   - `exchange_code` 正确解析 token
   - `refresh_token` / `revoke` / `get_user_info` 正常调用

无需改 API 路由 / 前端 / 注册表 —— `OAuthProviderRegistry.default()` 自动发现。

## API 路由（在 `routes/app_authorizations.py`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/app-authorizations/providers` | 列出所有可用 provider |
| GET | `/api/v1/app-authorizations` | 当前用户已连接列表 |
| POST | `/api/v1/app-authorizations/{provider_id}/start` | 生成 authorize URL |
| GET | `/api/v1/app-authorizations/{provider_id}/callback?code=&state=` | OAuth 回调 |
| POST | `/api/v1/app-authorizations/{id}/refresh` | 续期 |
| DELETE | `/api/v1/app-authorizations/{id}` | 断开连接 |

## 加密 key 管理（生产环境必看）

### 生成 key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 注入

```bash
export OAUTH_TOKEN_ENCRYPTION_KEY="base64-urlsafe-32B-key"
# 或 docker-compose / k8s Secret
```

### Key Rotation 流程

`OAUTH_TOKEN_ENCRYPTION_KEY` 支持逗号分隔多 key —— `MultiFernet` 加密永远用 `keys[0]`，
解密按顺序尝试所有 key。

```bash
# 第 1 步：在原 key 前面加新 key
export OAUTH_TOKEN_ENCRYPTION_KEY="NEW_KEY,OLD_KEY"
# 重启服务 → 新写入用 NEW_KEY，旧 token 用 OLD_KEY 解密

# 第 2 步：跑后台脚本 re-encrypt 所有旧 token（或等自然 refresh 替换）

# 第 3 步：确认无 OLD_KEY 加密的 token 后
export OAUTH_TOKEN_ENCRYPTION_KEY="NEW_KEY"
```

## 数据库

```
app_authorizations           ← user × provider 唯一
└── app_tokens (1:1)         ← Fernet 加密 token
```

迁移：`backend/alembic/versions/030_add_app_authorization_tables.py`

## 状态机

```
CONNECTED  ──── refresh 成功 ──→  CONNECTED
   │                                 │
   ├── refresh 失败 ──→ EXPIRED      │
   ├── 解密 / 平台错误 ──→ ERROR     │
   └── disconnect ──→ REVOKED        │
```
