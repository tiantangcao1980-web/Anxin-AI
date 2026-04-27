# P8-A Baseline 修复说明

> 日期：2026-04-27
> 范围：仅 import / export / typo / 字段名一致性 + git 合并冲突遗留；不动业务逻辑、model、route、测试。
> 上游基线：`v3/main @ 2624335 feat(p7-ecommerce-assistant)`。

P7 五个 persona 串联式合入主干后，CI 抓不到的几个 import 链断裂导致整个后端
启动即崩。本阶段（P8-A）只做最小化修复，使 `python3 -c "import src..."` 与
`pytest --collect-only` 能跑通，把真正需要重构的 P6/P7 语义偏差留到 P8-B。

## 修复清单

### Bug 1 — `tiers/l3_headlessx.py` 引用不存在的 `TierName`

| 项 | 内容 |
|---|---|
| 文件 | `backend/src/services/fetch/tiers/l3_headlessx.py` |
| 现象 | `ImportError: cannot import name 'TierName' from 'src.services.fetch.tiers.base'` |
| 根因 | P6-B（`2ce0533 feat(p6-headlessx)`）实装时把层枚举命名为 `TierName`，而 P6-A（`4d53e3e feat(p6-fetch-service)`）已落地的实际枚举是 `FetchTier`。同一 commit 还把类命名成 `HeadlessXTier`，但 `tiers/__init__.py` 一直期望 `L3HeadlessXTier`。 |
| 修法 | 1. `tiers/base.py` 里加 `TierName = FetchTier` 兼容别名（同时让 `from .base import FetchRequest, FetchResponse` 可用，因为 base 已 import 了它们）。 2. `l3_headlessx.py` 末尾加 `L3HeadlessXTier = HeadlessXTier` 兼容别名。 |
| 验证 | `python3 -c "import src.services.fetch.tiers.l3_headlessx"` → OK |

> ⚠️ L3 文件内部仍引用 `request.wait_for_selector` / `result.html` / `self.name` 等
> 在当前 `FetchRequest`/`FetchResponse` 上不存在的字段。**这是运行时 bug**，
> 留给 P8-B 重写 L3 实现去对齐 `FetchRequest`/`FetchResponse` 的实际 schema。
> 本次只让 import 链不再断。

### Bug 2 — `app_authorization/base.py` 缺 OAuth 异常族

| 项 | 内容 |
|---|---|
| 文件 | `backend/src/services/app_authorization/base.py` |
| 现象 | `feishu_oauth.py` / `notion_oauth.py` 等 `from ..base import OAuthError, OAuthTokenExpiredError` 直接 ImportError；`providers.__init__._autoload_providers()` 一调用就崩。 |
| 根因 | P4-A 框架只在 `oauth_flow.py` 定义了 `OAuthFlowError` / `OAuthProviderError` 等「flow 侧」异常；P4-B/C/D（feishu/notion 等 provider 实装）需要的「provider 侧」异常基类 `OAuthError` 与 `OAuthTokenExpiredError` 一直没人在 `base.py` 暴露。 |
| 修法 | 在 `base.py` 顶部新增： `class OAuthError(Exception)` 与 `class OAuthTokenExpiredError(OAuthError)`。`OAuthProviderError` 维持在 `oauth_flow.py`（已正确导出），`OAuthRequiredError` 维持在 `fetch/sources/ecommerce/base.py`（不同子模块）。 |
| 验证 | `python3 -c "from src.services.app_authorization import providers"` → OK；`from src.services.app_authorization.providers import feishu_oauth, dingtalk_oauth, notion_oauth, shopify_oauth` → OK |

### Bug 3 — `personas/__init__.py` 没触发 5 个 persona 自动注册

| 项 | 内容 |
|---|---|
| 文件 | `backend/src/agents/personas/__init__.py` |
| 现象 | `PersonaRegistry.instance().list_all()` 默认只能拿到 `operations_manager` 一个；其余 4 个必须显式 `autoload()` 才出现，前端列表页直接缺。 |
| 根因 | P7-A 的 `__init__.py` 只 import 了 `OperationsManagerAgent`；P7-B/C/D/E 各自合入时没维护这个聚合点，`__init_subclass__` 永远不触发。 |
| 修法 | 顶层 import 全部 5 个 persona class（market / lead / content / ecommerce + operations），并放进 `__all__`。 |
| 验证 | `python3 -c "from src.agents.personas.registry import PersonaRegistry; r = PersonaRegistry.instance(); r.autoload(); print(len(r.list_all()))"` → `5`；persona id 集合 `['content_director', 'ecommerce_assistant', 'lead_hunter', 'market_researcher', 'operations_manager']`。 |

### Bug 4（顺手） — `api/routes/__init__.py` 4 层未解决的 git 合并冲突

| 项 | 内容 |
|---|---|
| 文件 | `backend/src/api/routes/__init__.py` |
| 现象 | `SyntaxError: invalid decimal literal`，整个测试集 collect 阶段就挂。 |
| 根因 | P7-B/C/D/E 四次 merge 都把 `<<<<<<< HEAD` / `=======` / `>>>>>>>` 标记直接 commit 进了主干，没人手动合并。 |
| 修法 | 保留全部 5 个 persona 路由（`personas` + `persona_market` + `persona_sales` + `persona_content` + `persona_ecommerce`）+ `fetch`，删除所有冲突标记。 |
| 验证 | `pytest --collect-only` 不再报 `SyntaxError`；从 0 个用例可收集 → 804 个用例可收集。 |

## 健康度对比

| 指标 | 修复前 | 修复后 |
|---|---|---|
| `pytest --collect-only` 用例数 | 0（collect 阶段 SyntaxError 全挂） | 804 |
| `pytest tests/` 通过 | — | **726 pass** |
| `pytest tests/` 失败 | — | 52 fail + 19 error |
| 后端可 `import` | ❌ | ✅ |

## 留给 P8-B 处理的真 bug（本阶段不动）

1. **`l3_headlessx.py` 重写**：P6-B 实装版本与 `FetchRequest`/`FetchResponse` 实际 schema 完全不对齐（`wait_for_selector`、`html`、`bot_score`、`screenshot_png` 等字段都不存在；`tier=self.name` / `tier_used=self.tier` 二者也用错）。需要：要么扩 `FetchRequest`/`FetchResponse` 加上 headless 必备字段，要么按现有 schema 重写 L3 适配器。涉及 6 个测试 (`tests/test_l3_headlessx_tier.py`)。
2. **persona agent 构造器签名**：所有 persona 测试与部分 route 都按 `Agent(llm_client=..., http_client=...)` 注入，但 `BasePersonaAgent.__init__()` 不接受任何 kwargs，`self._llm` 走的是别的路径。涉及 ~25+ 测试（`test_content_director_agent.py` / `test_market_researcher.py` / `test_personas_api.py` / `test_persona_*_api.py`）。
3. **OAuth provider 构造器签名**：`DingTalkOAuthProvider()` / `FeishuOAuthProvider()` / `ShopifyOAuthProvider()` / `NotionOAuthProvider()` 都不接收 `http_client` / `app_id` 等显式参数，但全部 provider 测试用 `_make_provider(http_client=...)` 注入。涉及 4 套 test 文件。
4. **`watchdog` 缺包**：`test_skill_registry::test_observer_starts_and_stops` ModuleNotFoundError，需要在 `pyproject.toml` 加依赖。

## 验证清单（一键）

```bash
cd backend

# Bug 1
python3 -c "import src.services.fetch.tiers.l3_headlessx; print('Bug1 OK')"

# Bug 2
python3 -c "from src.services.app_authorization import providers; print('Bug2 OK')"

# Bug 3
python3 -c "from src.agents.personas.registry import PersonaRegistry; \
  r = PersonaRegistry.instance(); r.autoload(); \
  assert len(r.list_all()) == 5; print('Bug3 OK')"

# Bug 4 + overall
uv run pytest tests/ --collect-only -q | tail -3   # 应显示 804 collected
```
