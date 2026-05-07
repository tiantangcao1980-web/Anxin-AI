# 提案：为 due_diligence 加 require_mode 守卫

> 来源任务：TASK-09 P0-1（backend/src/api/routes/due_diligence.py:60）
> 作者：Claude Code 调研
> 状态：待实施（**仅方案，不改代码**）

## 1. 现状（grep 结果）

### 1.1 due_diligence.py 当前依赖列表

`backend/src/api/routes/due_diligence.py` 共 26 个路由，**全部仅挂 `Depends(get_current_user_required)`**，无模式 / 订阅守卫。需修复重点：

- `POST /company` — `due_diligence.py:64`（任务文档点名）
- `POST /company/stream` — `:93`
- `POST /company/orchestrated-stream` — `:406`
- `POST /company/deep-investigate` — `:433`
- `POST /report/generate` / `/report/generate/stream` — `:566` / `:604`
- `POST /simulate` / `/simulate/stream` — `:646` / `:665`
- 只读类（`/profile` `:160`、`/risks` `:180`、`/litigation` `:222`、`/graph` `:256`、`/snapshots/*`、`/cache/*`、`/preferences`、`/memory/*`、`/experience/*`）单独处理。

### 1.2 后端已有判定能力

- `subscription_service.py:351` `get_effective_features` 返回 `{modes: [...], due_diligence: bool, ...}`
- `subscription_service.py:383` `can_access_feature(user_id, feature_key)`
- `subscription_service.py:400` `can_use_mode(user_id, mode)`
- `subscription_service.py:317` `_FREE_FEATURES` 中 `"modes": ["local"]` 且 `"due_diligence": False`——**免费用户默认既不能尽调也不能用 hybrid/cloud**，无需新增数据。
- 前端 `frontend/src/context/PrivacyContext.tsx` 已持有 `mode` 状态并调用 `/billing/v2/can-use-mode`（`billing.py:373`）。
- ✅ 2026-05-06 已补齐 Web 端透传：`frontend/src/lib/api.ts` 的 `buildApiHeaders` 统一注入 `X-Privacy-Mode`，`PrivacyContext` 在 mode 变更时同步 API 快照，api-adapter、流式/上传/后台/支付/电签/模板/画布直连 fetch 已接入。

### 1.3 依赖工厂模式

`backend/src/core/deps.py` 已有 `require_permission` (`:391`)、`require_any_permission` (`:439`)、`require_role` (`:475`)，新守卫复用同款"工厂返回 async def dependency"模式。

---

## 2. 关键决策点：后端怎么知道当前模式？

| 选项 | 描述 | 优点 | 缺点 |
|---|---|---|---|
| **A. 请求头 `X-Privacy-Mode`** | 前端 PrivacyContext 在每个请求注入头，后端守卫读取并比对订阅 `allowed_modes` | 与前端 UI 模式可视化一致；本地模式调用尽调可以直接 403 | 老客户端不传需要回退；Web 端已由 `buildApiHeaders` 统一注入 |
| **B. 后端从订阅推断** | 完全忽略前端传入，后端根据用户订阅 `allowed_modes` 自行决定，不允许 local-only 用户调尽调 | 防伪造；前端无需改造 | 失去"用户主动选择 local"的语义；与 PrivacyContext 不能完全对齐 |
| **C. 仅订阅维度** | 完全用 `can_access_feature(user, "due_diligence")` 判定，不再分 mode | 最简单 | 满足不了 P0-1 文字描述（明确要 mode 守卫 + subscription 双重） |

### 推荐：**A + C 组合（首选 A，订阅 feature 兜底为 C）**

理由：

1. P0-1 描述明确要"模式守卫 + 订阅守卫"双层（`TASK-09:61`）。
2. PrivacyContext 已是事实上的真理来源，前端已自带 `mode` 状态，只差请求头注入。
3. `_FREE_FEATURES` 已内置 `due_diligence=False`，订阅维度的判定不需要新建数据。
4. 老客户端不传 `X-Privacy-Mode` 时，后端**默认按订阅 `allowed_modes` 第一项**推断（fail-safe：免费用户得到 local，触发 403）。

---

## 3. 实施方案（代码草稿，**不直接修改源文件**）

### 3.1 新增文件：`backend/src/core/mode_deps.py`

```python
"""模式 / 订阅守卫依赖（V2 三态运行模式专用）"""
from typing import Iterable
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.models.user import User
from src.services.subscription_service import SubscriptionService

VALID_MODES = {"local", "hybrid", "cloud"}

def require_mode(allow: Iterable[str]):
    allow_set = {m.lower() for m in allow}
    async def dep(request: Request,
                  user: User = Depends(get_current_user_required),
                  db: AsyncSession = Depends(get_db)) -> User:
        header_mode = (request.headers.get("X-Privacy-Mode") or "").lower()
        svc = SubscriptionService(db)
        if header_mode not in VALID_MODES:  # 老客户端兼容：按订阅推断
            features = await svc.get_effective_features(user.id)
            modes = [m.lower() for m in features.get("modes", ["local"])]
            header_mode = modes[0] if modes else "local"
        if header_mode not in allow_set:
            raise HTTPException(403, f"该功能不支持 {header_mode} 模式")
        if not await svc.can_use_mode(user.id, header_mode):
            raise HTTPException(402, f"当前订阅不支持 {header_mode} 模式")
        return user
    return dep

def require_subscription_feature(feature_key: str):
    async def dep(user: User = Depends(get_current_user_required),
                  db: AsyncSession = Depends(get_db)) -> User:
        if not await SubscriptionService(db).can_access_feature(user.id, feature_key):
            raise HTTPException(402, f"该功能需要订阅升级（feature={feature_key}）")
        return user
    return dep
```

### 3.2 `due_diligence.py` 修改前后对比（5 个核心路由）

```python
# 修改前（5 处全部相同模式）
async def investigate_company(
    request: CompanyInvestigateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):

# 修改后
from src.core.mode_deps import require_mode, require_subscription_feature

async def investigate_company(
    request: CompanyInvestigateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_mode(["hybrid", "cloud"])),
    _sub: User = Depends(require_subscription_feature("due_diligence")),
):
```

应用到的路由（按优先级）：`investigate_company` (`:60`)、`stream_investigate_company` (`:90`)、`orchestrated_stream_investigate` (`:403`)、`deep_investigate_stream` (`:430`)、`generate_report_direct` (`:563`)、`generate_report_stream` (`:600`)、`simulate_scenario` (`:643`)、`simulate_scenario_stream` (`:662`)。

只读路由（`/profile` `/risks` `/litigation` `/graph` `/snapshots/*` `/cache/*` `/preferences` `/memory/*`）建议**只挂 `require_subscription_feature`**，不挂 `require_mode`——允许本地模式查看历史快照，但不允许触发新爬虫。

### 3.3 前端配套（独立 PR，不在本提案改动）

`frontend/src/lib/api.ts` 全局拦截器加：
```ts
config.headers["X-Privacy-Mode"] = usePrivacyStore.getState().mode;
```

---

## 4. 兼容性 + 风险

| 场景 | 行为 | 风险等级 |
|---|---|---|
| 老客户端（不传 `X-Privacy-Mode`） | 后端按订阅 `allowed_modes[0]` 推断；免费用户落到 `local` 触发 403 | 低（与升级订阅引导一致） |
| 普通无订阅用户调用 `/company` | 402 返回 `"该功能需要订阅升级"`，前端 `DueDiligence.tsx` 拦截后跳 `/pricing` | 中（需前端配合提示） |
| Trial 用户（`status=trial`） | `get_effective_features` 已正确返回 trial plan 的 modes，正常放行 | 低 |
| 超级管理员 / `is_superuser` 测试用户 | 当前方案不绕过；如需后台调试，可在 `require_mode` 起点加 `if user.is_superuser: return user` | 低 |
| 错误的 `X-Privacy-Mode` 值（如 `"foo"`） | 当前方案：当成"未传"处理，按订阅推断；不抛 400 | 低 |

---

## 5. 测试方案

### 5.1 后端 pytest（至少 3 条）

1. `test_due_diligence_blocks_local_mode` — 带 `X-Privacy-Mode: local` 调 `POST /due-diligence/company` → 403。
2. `test_due_diligence_requires_subscription` — 免费用户带 `X-Privacy-Mode: hybrid` → 402。
3. `test_due_diligence_allows_pro_user_in_cloud_mode` — Pro 订阅 + `cloud` → 200。
4. （可选）`test_due_diligence_no_header_falls_back` / `test_due_diligence_readonly_routes_skip_mode_guard`。

### 5.2 前端 e2e

`frontend/e2e/due-diligence-mode-guard.spec.ts`：免费个人用户在 local 模式下点击尽调 → 出现升级订阅引导，toast `"该功能需要订阅升级"`。

### 5.3 回归

`pytest -k "due_diligence"` 不退化；默认全量 `pytest`（当前基线 `354 passed, 1 skipped`）不退化；`ModeGate.tsx` 包裹页行为不受影响。

---

## 6. 工时估算

| 阶段 | 估时 |
|---|---|
| 实施：新建 `mode_deps.py` + 修改 `due_diligence.py` 8 处 + Web 端 `buildApiHeaders` 统一注入 | 已完成 |
| 测试：5 个后端 pytest + 1 个 e2e | 0.5 天 |
| 验证：本地跑 `pytest` + `npm run build` + `playwright`，文档回写 `docs/audit/09-risk/03-fixes.md` 与 hierarchical-memory `add-feature` | 0.25 天 |
| **合计** | **约 1.25 天**（不含 PR review） |

---

> 后续动作：方案确认后开 PR，在描述里贴"失败测试 → 通过测试"截图，并回写 `docs/audit/00-platform/01-prd-reality-gap.md` 1.2 节"三态运行"实质就绪度（当前 50% → 目标 70%）。
