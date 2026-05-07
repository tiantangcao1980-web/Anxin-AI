# 任务 09 — 合规 / 风险 / 尽调 / 舆情 / 资讯收口

> 波次：3 / 工时估：4-5 天 / 负责人：待分配
> 必读前置：../PLAN.md、../00-platform/01-prd-reality-gap.md、../00-platform/03-cross-cutting-gaps.md

> 2026-05-08 定位补充：舆情监测是企业风险入口，也是后续专业服务转介和服务方推广获客的商业入口。P0 需要证明舆情告警、处置建议、材料包和转专业人士路径；P1/P2 再扩展获客归因、推广标识、反骚扰和效果追踪。

## 1. 范围

### 要碰的文件

- 后端服务：
  - `backend/src/services/compliance_service.py`
  - `backend/src/services/risk_scoring_engine.py`
  - `backend/src/services/audit_service.py`
  - `backend/src/services/due_diligence_service.py`
  - `backend/src/services/investigation_orchestrator.py`
  - `backend/src/services/investigation_data_store.py`
  - `backend/src/services/deep_research_engine.py`
  - `backend/src/services/sentiment_service.py`
  - `backend/src/services/crawler_service.py`
  - `backend/src/services/crawl4ai_service.py`
  - `backend/src/services/web_search_service.py`
  - `backend/src/services/scenario_simulation.py`
  - `backend/src/services/scenario_templates.py`
- 后端 Agents：
  - `backend/src/agents/compliance_officer.py`
  - `backend/src/agents/risk_assessor.py`
  - `backend/src/agents/due_diligence.py`
  - `backend/src/agents/sentiment_agent.py`
  - `backend/src/agents/regulatory_monitor.py`
  - `backend/src/agents/evidence_analyst.py`
- 后端路由：
  - `backend/src/api/routes/compliance.py`
  - `backend/src/api/routes/due_diligence.py`（重点 60 行）
  - `backend/src/api/routes/sentiment.py`
  - `backend/src/api/routes/datacenter.py`
  - `backend/src/api/routes/anonymous_chat.py`（重点 136-169 行）
- 前端：
  - `frontend/src/pages/ComplianceCheck.tsx`
  - `frontend/src/pages/RiskAlertPanel.tsx`
  - `frontend/src/pages/DueDiligence.tsx`
  - `frontend/src/pages/Investigation.tsx`
  - `frontend/src/pages/MonitoringCenter.tsx`
  - `frontend/src/pages/News.tsx`
  - `frontend/src/components/due-diligence/`
- 测试：
  - `backend/tests/test_due_diligence_*.py`、`test_compliance_*.py`、`test_anonymous_chat_*.py`、`test_investigation_*.py`、`test_sentiment_*.py`、`test_crawler_*.py`
  - `frontend/e2e/due-diligence.spec.ts`、`investigation.spec.ts`、`compliance.spec.ts`（如缺则补）

### 明确不要碰的文件

- `backend/src/services/payment_service.py` / `subscription_service.py` / `billing_service.py`（属任务 10）
- `backend/src/services/im_service.py` / `im_hub.py` / `rtc_service.py`（属任务 10）
- `backend/src/services/esign_service.py`（属任务 05）
- `backend/src/services/document_service.py`（属任务 06；尽调附件落地等待 storage_service 抽象层）
- `backend/src/prompts/`（任何 prompt 改动需用户预审）

## 2. 必修 P0（带文件:行号）

- [x] **P0-1 due_diligence 加 require_mode 守卫 + require_subscription**
  - 现状：2026-05-06 已改为 `require_mode(["hybrid", "cloud"])` + `require_subscription_feature("due_diligence")`；`backend/tests/test_mode_subscription_guards.py` 覆盖免费/local 阻断、hybrid 通过、订阅 feature 402。
  - 期望：叠加 `require_mode(allow=["hybrid", "cloud"])` 守卫（禁止纯 local 模式调用）+ `require_subscription(plan_in=["pro","enterprise"])` 订阅检查；未订阅返回 402，模式不允许返回 403
  - 文件：`backend/src/api/routes/due_diligence.py`
- [x] **P0-2 匿名聊天双 token 拆分（PROJECT_STATUS S7）**
  - 现状：2026-05-06 已改为发起人/律师分开领 token；`backend/tests/test_anonymous_chat_token_split.py` 覆盖发起人校验、律师 join、`my-token` 只返回当前身份 token。
  - 期望：
    - `create_room` 加 `Depends(get_current_user_required)` 验证发起人 = 关联 consultation 的所有者
    - 不再一次返回双 token；改为 `GET /rooms/{id}/my-token` 受保护接口分别取
    - lawyer 一侧 token 仅当用户身份匹配 consultation.lawyer_id 才返回
  - 文件：`backend/src/api/routes/anonymous_chat.py`
- [x] **P0-3 爬虫合规（robots / 频控 / UA / 法定数据源）**
  - 现状：2026-05-06 已新增 `crawler_service.fetch()` 统一合规入口，`crawler_service` 与 `crawl4ai_service` 的真实抓取均走白名单、robots、合法 UA、host 频控；尽调执行网/信用中国路径不再在合规入口失败后降级到直接 Playwright。`backend/tests/test_crawler_compliance.py` 覆盖非白名单拒绝、robots disallow、dry-run UA/频控和真实 fetch header。真实外网 dry-run 在本机 DNS 将法定域名解析到 `198.18.0.0/15` 测试网段时被 SSRF 防护拒绝，未作为商业放行证据。
  - 期望：所有 outbound 抓取统一经过 `crawler_service.fetch()` 入口，强制：
    - robots.txt 解析与遵守（配置允许豁免名单时记录审计）
    - 标识合法 UA（`Anxin-Legal-Crawler/{version} (+contact)`）
    - 默认 1 req/s/host 频控；可配置但下限 0.5 req/s/host
    - 数据源白名单：仅允许在 `data_sources.legal_whitelist` 配置内的域名
  - 文件：`backend/src/services/crawler_service.py`、`backend/src/services/crawl4ai_service.py`、`backend/src/services/web_search_service.py`
- [x] **P0-4 风险打分一致性、可解释性**
  - 现状：2026-05-06 已补顶层 `score/factors/explain`，每个因子含 `weight`、`contribution`、`evidence` 与人类可读说明；`RiskAlertPanel` 支持在合同返回 `risk_factors` / `risk_explain` 时渲染贡献条；`backend/tests/test_risk_scoring_engine.py` 覆盖同输入确定性与旧 `dimensions` 契约兼容。
  - 期望：`risk_scoring_engine` 同一输入两次调用结果一致（无随机种子漂移）；返回结构含 `score`、`factors`（每个因子 weight + contribution）、`explain`（人类可读说明），前端 `RiskAlertPanel` 渲染因子贡献条
  - 文件：`backend/src/services/risk_scoring_engine.py`、`frontend/src/pages/RiskAlertPanel.tsx`
- [x] **P0-5 调查请求意图识别 + 公司名抽取强路由命中率 ≥ 85%**
  - 现状：2026-05-06 已新增 `classify_investigation_request()`，支持 "尽调 / 舆情 / 法规监测 / 普通搜索" 四类强路由，并接入 `ChatService._decide_route()`；尽调走专用尽调流程，舆情走 `legal_researcher`，法规监测走 `regulatory_monitor`。新增 200 条离线 JSONL 评测集，`backend/tests/test_due_diligence_intent.py` 覆盖门槛，当前评测 `intent_accuracy=1.000`、`company_accuracy=1.000`（150 条含企业名）。
  - 期望：`investigation_orchestrator` 增加 intent classifier（"尽调 / 舆情 / 法规监测 / 普通搜索"）+ company name extractor；离线测试集 ≥ 200 条样本，整体强路由命中率 ≥ 85%
  - 文件：`backend/src/services/due_diligence_service.py`、`backend/src/services/chat_service.py`、`backend/tests/test_due_diligence_intent.py`、`backend/tests/test_chat_due_diligence_routing.py`、`backend/tests/eval/investigation_routing_eval.jsonl`
- [x] **P0-6 抓取频控参数校核**
  - 现状：2026-05-06 已新增 `backend/src/config/crawler.py`，默认 1 req/s/host，代码强制下限 0.5 req/s/host；`LIC_DEFAULT_HOST_RATE_LIMIT_SECONDS` / `LIC_HOST_RATE_LIMIT_SECONDS` 支持配置但会被 clamp，不允许代码层直接下调到更频繁。
  - 期望：把现有频控参数从代码硬编码挪到 `backend/src/config/crawler.py`（含 host 级别覆盖），并在 hierarchical-memory 中查 `project_legal_data_collection` 已有经验作为基线；任何下调（更频繁）都必须用户审
  - 文件：`backend/src/services/crawler_service.py` + 新增 `backend/src/config/crawler.py`
- [x] **P0-7 尽调缓存 org 维度边界**
  - 现状：2026-05-06 已给 `SearchCache` 增加 `org_id`，缓存读/写/维度查询/失效均按组织过滤；API 层对无组织普通用户 fail-closed，编排器与 deep research 缓存读写传递 org scope。
  - 期望：cache key = `(org_id, target_entity_id, scope_signature)`；新增 `backend/tests/test_investigation_cache_org_scope.py` 覆盖同公司跨组织不串读、不串失效、无组织用户态 fail-closed。
  - 文件：`backend/src/models/investigation.py`、`backend/src/services/investigation_data_store.py`、`backend/src/services/investigation_orchestrator.py`、`backend/src/services/deep_research_engine.py`、`backend/src/api/routes/due_diligence.py`

## 3. 流程

### Step 0 — PRD vs 现实差分
读 `../00-platform/01-prd-reality-gap.md` 中 S5/S7 与本任务相关条目；写 `docs/audit/09-risk-investigation/00-prd-reality-gap.md`，列出尽调 / 匿名聊天 / 风控 / 舆情各自"承诺 vs 现实"。

### Step 1 — hierarchical-memory find-bugfix / find-feature
关键词：`anonymous chat dual token`、`due diligence subscription guard`、`crawler robots throttle`、`risk score determinism`、`intent classifier extractor`、`org-scoped cache key`、`project_legal_data_collection`。命中即复用。

### Step 2 — 分层读取（路由 → 服务 → Agent → 前端 → 测试）
1. `due_diligence.py` 路由 + `due_diligence_service.py` + `due_diligence` agent
2. `anonymous_chat.py` 路由（双 token 改造）
3. `compliance.py` / `compliance_service.py` / `compliance_officer` agent
4. `risk_scoring_engine.py` + `risk_assessor` agent + `RiskAlertPanel.tsx`
5. `investigation_orchestrator.py` + `deep_research_engine.py` + `investigation_data_store.py` + `Investigation.tsx`
6. `sentiment_service.py` + `sentiment_agent` + `regulatory_monitor` + `News.tsx` / `MonitoringCenter.tsx`
7. `crawler_service.py` / `crawl4ai_service.py` / `web_search_service.py`（合规闸门）
8. `scenario_simulation.py` / `scenario_templates.py`（兜底覆盖）
9. 测试：`tests/test_anonymous_chat_*`、`test_due_diligence_*`、`test_investigation_*`、`test_compliance_*`

### Step 3 — code-review + security-review
关注：订阅/模式守卫位置（路由 vs 服务）、token 颁发授权链、爬虫白名单 + 频控、缓存 key 多租户隔离、风险打分确定性 + 可解释性、PII / 商业秘密在尽调日志中的脱敏。

### Step 4 — 先写失败测试再改实现
- P0-1：`test_due_diligence_requires_subscription`、`test_due_diligence_blocks_local_mode`
- P0-2：`test_anonymous_create_room_requires_owner`、`test_anonymous_my_token_returns_only_self`
- P0-3：`test_crawler_respects_robots`、`test_crawler_rate_limit_per_host`、`test_crawler_rejects_non_whitelisted_host`
- P0-4：`test_risk_score_deterministic`、`test_risk_score_factors_contract`
- P0-5：`test_investigation_intent_routing_accuracy`（在 200 样本评估集上 ≥ 85%）
- P0-6：`test_crawler_config_override`（host 级别覆盖生效）
- P0-7：`test_due_diligence_cache_org_isolation`、`test_due_diligence_cache_no_org_namespace`

### Step 5 — verification-loop
- `cd backend && pytest -k "anonymous or due_diligence or investigation or compliance or crawler or risk_score or sentiment"`
- `cd backend && pytest`（不退化当前默认 `354 passed, 1 skipped` 基线）
- `cd frontend && npm run lint && npm run build`
- `cd frontend && npx playwright test e2e/due-diligence.spec.ts e2e/investigation.spec.ts e2e/compliance.spec.ts`
- 抓取 P0-3 的合规闸门要补一个对真实 host 的"dry run"日志（不抓数据），证明 robots / UA / 频控生效

### Step 6 — simplify + 沉淀到 hierarchical-memory
- `add-bugfix --symptom "匿名聊天 create_room 公开 + 双 token 一次返回" --fix "create_room 加 owner 校验 + 拆 my-token 两个受保护接口" --files ...`
- `add-feature --name "尽调订阅 + 模式双重守卫" --pattern "require_subscription + require_mode 装饰器" --files ...`
- `add-feature --name "爬虫合规闸门" --pattern "统一 fetch + robots + 频控 + 白名单" --files ...`
- `add-bugfix --symptom "尽调缓存跨 org 命中" --fix "(org_id, entity, scope) 复合 key" --files ...`

## 4. 输出物（写到 `docs/audit/09-risk-investigation/`）
- `00-prd-reality-gap.md`
- `01-prd-coverage.md`
- `02-issues.md`（P0/P1/P2 合并清单）
- `03-fixes.md`
- `04-test-additions.md`（含 200 样本评估集说明）
- `05-followups.md`
- 代码 PR（直接修复 P0；P1/P2 标 followup）

## 5. 风险护栏（必须遵守）
- 爬虫频控参数任何下调（让爬取更频繁）会触发对方风控/法务，**必须用户预审**
- 抓取数据源白名单变更 → PR 描述里必须列出新增域名 + 法务/合规依据
- 不动 `prompts/` 任意文件；尽调 / 风控相关 prompt 改动需用户预审 diff
- 匿名聊天 token 颁发逻辑改动属敏感安全面，PR 提交前用户预审
- 不允许跨任务越界：商业化（10）/ 电签（5）/ 文档存储（6）这次不动
- 不动 `.env` / 不轮换密钥（属任务 0）；尽调外部 API key 仍走环境变量注入
- 离线评估集（P0-5）若包含真实公司名，要做脱敏或仅留行业代号

## 6. 完成标准（DoD）
- [ ] 全部 7 个 P0 修复，每个有"失败 test → 通过 test"证据
- [x] P0-5 投放评估集（≥200 条）+ 命中率 ≥ 85% 报告（写入 `docs/audit/09-risk/04-test-additions.md` 与 test evidence）
- [ ] 后端 `pytest` 不退化（当前默认 `354 passed, 1 skipped` 基线）
- [ ] 前端 `npm run build` + `playwright test` 不退化
- [ ] 爬虫 dry-run 日志展示 robots / UA / 频控生效（截图或文本日志）
- [ ] 6 份文档（`00..05.md`）齐全
- [ ] 沉淀到 hierarchical-memory 至少 3 条（建议 P0-1 + P0-2 + P0-3）
- [ ] 回写 `../00-platform/01-prd-reality-gap.md` 中 S7（匿名聊天）状态
- [ ] PR 描述列出"对外抓取新增 / 修改的域名清单"，无新增则注明 N/A
