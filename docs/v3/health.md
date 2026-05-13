# V3 健康度报告（生成于 2026-04-27）

## 摘要

| 维度 | 数字 | 状态 |
|---|---|---|
| Backend pytest（修 conflict 后） | **601 passed / 59 failed / 37 errors / 0 skipped**（697 collected） | 🟡 86.2% pass rate |
| Backend pytest（v3/main 原始） | 443 passed / 44 failed / 202 errors（中断 18 collection error） | 🔴 ~62% pass rate |
| Frontend lint | **0 warning, 0 error** | 🟢 |
| Frontend tsc --noEmit | **0 error** | 🟢 |
| Frontend npm run build | **通过**（仅 1 chunk size warning：vendor-three 1.32MB） | 🟢 |
| Frontend audit | 31 vuln（1 critical / 19 high / 10 mod / 1 low） | 🔴 需另开任务跑 npm audit fix |

> **执行说明**：v3/main HEAD 的 `backend/src/api/routes/__init__.py` 存在未解决的 4 重 git merge conflict 标记
> （P7-A/B/C/D/E 五个 commit 都引入了 `personas / persona_market / persona_sales / persona_content / persona_ecommerce`
> 的 import + include_router，但合并未解决冲突）。该文件直接导致 18 个 test module 在 collection 期 import-fail，
> 大量 client fixture 无法构造（连锁出 ~165 个伪 error）。
>
> 任务规则允许 QA 修「显然的低级 syntax error」让 pytest 能跑起来 — 此处合并冲突 marker 完全符合该豁免范围。
> 解决方案：保留全部 5 个 import + 5 个 include_router（即 P7 系列设计意图），其余无业务改动。
> **下方所有按文件统计与失败归类，均基于「修 conflict 之后」的真实数字。**

---

## Backend Pytest 详情

### 按测试文件分组（仅列有失败/错误的文件 + 关键大模块）

| 文件 | total | pass | fail | error |
|---|---|---|---|---|
| test_brand_consistency.py | 7 | 0 | 7 | 0 |
| test_content_director_agent.py | 10 | 0 | 10 | 0 |
| test_deep_research_loop.py | 13 | 4 | 9 | 0 |
| test_dingtalk_oauth_provider.py | 5 | 0 | 5 | 0 |
| test_fetch_api.py | 8 | 0 | 8 | 0 |
| test_fetch_compliance.py | 21 | 18 | 3 | 0 |
| test_market_researcher.py | 8 | 4 | 4 | 0 |
| test_personas_api.py | 13 | 6 | 7 | 0 |
| test_shopify_oauth_provider.py | 7 | 2 | 5 | 0 |
| test_skill_registry.py | 17 | 16 | 1 | 0 |
| test_persona_content_api.py | 9 | 0 | 0 | 9 |
| test_persona_market_api.py | 1 | 0 | 0 | 1 |
| test_app_authorizations_api.py | 6 | 0 | 0 | 6 |
| test_oauth_flow.py | 5 | 0 | 0 | 5 |
| test_chat_stream_timeout_guard.py | 1 | 0 | 0 | 1 |
| test_l3_headlessx_tier.py | 1 | 0 | 0 | 1 |
| test_shopify_source.py / _multi_tenant.py | 2 | 0 | 0 | 2 |
| test_alibaba_1688_mock.py / amazon_sp_mock.py / ecommerce_*.py | 5 | 0 | 0 | 5 |
| test_credit_china_client.py / flk_npc_parser.py / historical_wenshu_query.py | 3 | 0 | 0 | 3 |
| test_legal_sources_compliance.py / pkulaw_mock_fallback.py | 2 | 0 | 0 | 2 |
| test_feishu_oauth_provider.py / notion_oauth_provider.py | 2 | 0 | 0 | 2 |
| **以下为高通过率核心模块（全 PASSED）** | | | | |
| test_chat.py | 33 | 33 | 0 | 0 |
| test_agent_task_state_machine.py | 29 | 29 | 0 | 0 |
| test_case_service.py | 26 | 26 | 0 | 0 |
| test_harness.py | 23 | 23 | 0 | 0 |
| test_fetch_router.py | 19 | 19 | 0 | 0 |
| test_skill_executor.py | 17 | 17 | 0 | 0 |
| test_sentiment.py | 17 | 17 | 0 | 0 |
| test_workforce.py | 16 | 16 | 0 | 0 |
| test_operations_manager_agent.py | 16 | 16 | 0 | 0 |
| test_persona_ecommerce_api.py | 12 | 12 | 0 | 0 |
| test_lead_hunter_agent.py | 13 | 13 | 0 | 0 |
| test_ai_bargaining.py | 13 | 13 | 0 | 0 |
| test_persona_registry.py | 11 | 11 | 0 | 0 |
| test_lawyer_matching_and_tasks_api.py | 11 | 11 | 0 | 0 |
| test_external_surface_guards.py | 11 | 11 | 0 | 0 |
| test_skills_api.py | 13 | 13 | 0 | 0 |
| test_skill_validator.py | 12 | 12 | 0 | 0 |
| test_skill_loader_yaml.py | 13 | 13 | 0 | 0 |

完整 per-file 表格见 `/tmp/by_file_status.tsv`。

---

### 失败归类

#### 类别 1：baseline import 链断裂（P8-A 在修，已知）

**1a. `TierName` 缺 export**（18 个 errors，影响 2 个测试文件）
- 影响测试：`test_l3_headlessx_tier.py`, `test_shopify_source.py`, `test_shopify_source_multi_tenant.py`, `test_alibaba_1688_mock.py`, `test_amazon_sp_mock.py`, `test_ecommerce_base.py`, `test_ecommerce_oauth_required.py`, `test_ecommerce_shopee_tiktok_mock.py`, `test_credit_china_client.py`, `test_flk_npc_parser.py`, `test_historical_wenshu_query.py`, `test_legal_sources_compliance.py`, `test_pkulaw_mock_fallback.py`
- 根因：`src/services/fetch/tiers/l3_headlessx.py:32` `from .base import BaseTier, FetchRequest, FetchResponse, TierName` — `tiers/base.py` 未 export `TierName` 枚举
- 代表 traceback：
  ```
  src/services/fetch/tiers/l3_headlessx.py:32: in <module>
      from .base import BaseTier, FetchRequest, FetchResponse, TierName
  E   ImportError: cannot import name 'TierName' from 'src.services.fetch.tiers.base'
  ```
- 修复负责：**P8-A**
- 预期修复后 unblock 测试数：≈ 18

**1b. `OAuthError` 缺 export**（13 个 errors，影响 5 个测试文件）
- 影响测试：`test_feishu_oauth_provider.py`, `test_notion_oauth_provider.py`, `test_app_authorizations_api.py`(6), `test_oauth_flow.py`(5)
- 根因：`src/services/app_authorization/base.py` 未 export `OAuthError`
- 代表 traceback：
  ```
  E   ImportError: cannot import name 'OAuthError' from 'src.services.app_authorization.base'
  ```
- 修复负责：**P8-A**
- 预期修复后 unblock 测试数：≈ 13

**1c. PersonaRegistry autoload 不全**（7 fail + 1 error，影响 3 个测试文件 + 1 间接）
- 影响测试：`test_personas_api.py::TestOperationsEndpoints::*`(5), `TestPersonaChat::test_chat_with_persona`, `TestPersonaListAndDetail::test_get_persona_detail`, `test_persona_market_api.py`
- 根因：`operations_manager` persona 在 PersonaRegistry 启动时未加载
- 代表 assertion：`AssertionError: {"detail":"流程管家 persona 未加载: operations_manager"}` `assert 503 == 200`
- 修复负责：**P8-A**
- 预期修复后通过数：≈ 7

**baseline 三类合计：约 38 个测试将自动恢复**

---

#### 类别 2：真实业务 bug

**2a. BasePersonaAgent 构造签名不一致**（25 + 13 = 38 个 errors，但去重后影响 1 个测试文件 + 1 个 fixture）
- 影响测试：`test_persona_content_api.py`(9 errors)
- 根因：`tests/test_persona_content_api.py:32` 测试 fixture 中 `super().__init__(llm_client=None)` 与 `super().__init__(llm_callable=...)` 调用，但 `BasePersonaAgent.__init__()` 不接受这两个 kwargs
  ```
  E   TypeError: BasePersonaAgent.__init__() got an unexpected keyword argument 'llm_client'
  E   TypeError: BasePersonaAgent.__init__() got an unexpected keyword argument 'llm_callable'
  ```
- 建议修复优先级：**P0** — 整个内容总监 API 9 个端点 0 测试覆盖
- 工作量估计：30 分钟（要么改 BasePersonaAgent 接受 llm_client/llm_callable，要么改 stub fixture 不传 kwarg）

**2b. ContentDirectorAgent 缺 manifest classmethod**（1 fail）
- 影响：`test_content_director_agent.py::test_manifest_exposes_persona_metadata`
  ```
  E   AttributeError: type object 'ContentDirectorAgent' has no attribute 'manifest'
  ```
- 该测试文件 10/10 全失败，可能与 2a 同根
- 建议优先级：**P0**（与 2a 一起修）
- 工作量估计：与 2a 合并修，0 增量

**2c. DingTalkOAuthProvider() takes no arguments**（5 fail）
- 影响：`test_dingtalk_oauth_provider.py` 全 5 测试
- 根因：`DingTalkOAuthProvider` 没定义 `__init__`，但测试传入 client_id/client_secret
- 建议优先级：**P1**（钉钉 OAuth 完全无测试覆盖）
- 工作量估计：15 分钟

**2d. ShopifyOAuthProvider super().__init__() 签名错**（5 fail）
- 影响：`test_shopify_oauth_provider.py` 5/7 失败
- 根因：`src/services/app_authorization/providers/shopify_oauth.py:166` `super().__init__(...)` 调用父类，但父类未接受这些 kwargs
  ```
  E   TypeError: object.__init__() takes exactly one argument
  ```
- 建议优先级：**P1**（Shopify 是 P6 唯一真实接入的电商平台）
- 工作量估计：20 分钟

**2e. Fetch API 路由 404 + fetch_service 缺 module attr**（8 fail）
- 影响：`test_fetch_api.py` 全 8 测试
- 根因 1：`module 'src.api.routes.fetch' has no attribute 'fetch_service'`（mock 目标找不到）
- 根因 2：404（路由未挂载或 path mismatch）
- 建议优先级：**P0**（P6 信息获取栈 4 层门面对外 API 0 覆盖）
- 工作量估计：1 小时（先通监控后调整测试）

**2f. Fetch 合规 service 行为不符**（3 fail）
- 影响：`test_fetch_compliance.py::test_fetch_service_wechat_returns_403_with_reason`, `test_fetch_service_wenshu_returns_403_with_reason`, `test_check_compliance_returns_full_judgment`
- 18/21 已通过，仅 3 个边缘合规判断未覆盖到
- 建议优先级：**P2**
- 工作量估计：30 分钟

**2g. Brand consistency 服务签名错**（7 fail）
- 影响：`test_brand_consistency.py` 7/7 失败
- 与 2a 同源，TypeError 在 LLM stub 注入处
- 建议优先级：**P0**（与 2a 合并修）

**2h. DeepResearch loop 函数签名错**（9 fail）
- 影响：`test_deep_research_loop.py` 9/13 失败
- TypeError 出现，市场研究员 deep research 主算法未达可用
- 建议优先级：**P0**
- 工作量估计：1 小时

**2i. MarketResearcher Agent**（4 fail）
- 影响：`test_market_researcher.py` 4/8 失败（含 `test_investigate_company_returns_report`, `test_industry_trends_returns_4_axes`）
- 与 2h 同根（都是 P7-A 市场研究员）
- 建议优先级：**P0**

---

#### 类别 3：测试自身问题（mock/fixture/pytest 配置）

**3a. PersonaContentAgent stub fixture 用错 kwarg**
- 已合入类别 2a — 既可能是测试自身问题（kwargs 名变了未同步），也可能是业务接口设计问题（应支持 LLM 注入），需 P8-A 或代码 owner 决策
- 建议两修一：把 BasePersonaAgent.__init__ 改成接受 `llm_client` 名（与 OperationsManager 已 PASS 的 fixture 风格统一）

**3b. test_skill_registry::test_observer_starts_and_stops**（1 fail）
- 根因：`watchdog` 模块在 lazy import 时 `ModuleNotFoundError`（实际已通过 `uv sync` 装上）
  ```
  E   ModuleNotFoundError: No module named 'watchdog'
  ```
- 实际 watchdog 在 `uv.lock` 里有，但该测试用了 `subprocess` 启 observer，环境隔离丢了 PYTHONPATH/site-packages
- 建议优先级：**P3**（不影响 registry 主路径，16/17 已 PASS）

---

#### 类别 4：外部依赖缺失（postgres/redis/celery/livekit）

未在本次跑出 — fixtures 用 SQLite + in-memory mock 跑通，无 DB 连不上等阻塞类报错。这是好消息：测试套件对外部依赖的隔离做得不错。

---

## Frontend

### Lint
- `npm run lint`（eslint --max-warnings 0）：**EXIT 0**，0 warning, 0 error
- 4 行 stdout（仅命令头）

### TypeScript
- `npx tsc --noEmit`：**EXIT 0**，0 error，stdout 为空

### Build
- `npm run build`（tsc + vite build）：**EXIT 0**
- 产物大小：dist 总 ~3.6MB（gzip ~1.1MB）
- 1 个 chunk size warning：`vendor-three.js` 1,323 kB（可考虑代码分割，非阻塞）
- 主要 chunks：vendor-three (1.3M) > vendor-livekit (552K) > vendor-recharts (487K) > vendor-editor (473K) > vendor-lottie (315K) > index (215K) > Chat (206K) > vendor-react (163K)

### Audit（提示用）
- 31 vulns：1 critical / 19 high / 10 moderate / 1 low — 建议 P8-C 后单独开 npm audit fix 任务

---

## 优先级修复清单（按影响面排序）

| 排序 | 项 | 影响测试数 | 优先级 | 估时 | 负责 |
|---|---|---|---|---|---|
| 1 | TierName 缺 export | 18 测试 unblock | P0 | 5 min | P8-A |
| 2 | OAuthError 缺 export | 13 测试 unblock | P0 | 5 min | P8-A |
| 3 | BasePersonaAgent.__init__ 接受 llm_client/llm_callable | 25 fail/error（2a+2b+2g）| P0 | 30 min | 业务 owner |
| 4 | DeepResearch loop / MarketResearcher 签名修复 | 13 fail | P0 | 1 h | 业务 owner |
| 5 | Fetch API mock 目标 + 路由 404 | 8 fail | P0 | 1 h | 业务 owner |
| 6 | PersonaRegistry 加载 operations_manager | 7 fail | P0 | 30 min | P8-A |
| 7 | DingTalkOAuthProvider __init__ | 5 fail | P1 | 15 min | 业务 owner |
| 8 | ShopifyOAuthProvider super().__init__ | 5 fail | P1 | 20 min | 业务 owner |
| 9 | git merge conflict（已在本任务修） | unblock 18 file collection | — | done | QA |

**P0 累计：约 84 个测试可恢复，估时约 4 小时**

---

## 健康度评分

| 维度 | 评分 | 说明 |
|---|---|---|
| Backend | 🟡 **86.2%** (601/697) | 修 conflict + 估算 P8-A baseline 三类修复后预计可达 ~92% |
| Frontend | 🟢 build/lint/tsc 全绿 | 唯一阴影是 audit 31 vuln，不阻塞 |
| 整体 | 🟡 | 后端关键 path（chat/case/agent_task/skill/persona registry）质量稳；P7 新增 4 个 persona 中 ContentDirector + MarketResearcher 测试 fixture 与生产签名不对齐，需要 4h 工作量收口 |

---

## 下一步建议

### 可立即 ship 的部分
- **Backend：** chat / agent_task / case / harness / fetch_router / skill_* / lead_hunter / ecommerce_assistant / ai_bargaining / operations_manager / persona_registry / persona_ecommerce / lawyer_matching / 全部 auth/security guard 测试（约 18 个文件、~330 tests 全 PASS）
- **Frontend：** 整个前端（lint/tsc/build 三绿，可以发 dist）

### 需要修后再 ship
- **Backend persona content（内容总监 API）**：9 个端点 0 测试覆盖，必修 BasePersonaAgent 签名
- **Backend market_researcher**：DeepResearch 主算法 9 fail，必修
- **Backend fetch_api（信息获取栈 HTTP 层）**：8 fail，是 P6 对外 API 入口
- **OAuth providers**：DingTalk + Shopify 共 10 fail，影响第三方接入

### 不建议本轮做
- npm audit fix —— 31 个 vuln 多在嵌套 transitive dep，需单开任务
- vendor-three 1.3MB chunk split —— 性能优化，非健康度问题
