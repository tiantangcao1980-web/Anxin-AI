# 任务 3 — AI 智能体 + 对话 + Prompt

> 波次 2（与任务 4/5/6/7 并行）
> 工时估：3-5 天
> 前置：任务 0（基础设施 SOP）+ 任务 1/2（认证 + 三态运行）已收口
> 输出目录：`docs/audit/03-agents/`

---

## §1 范围

### 要碰的文件

后端（智能体编排 + 对话核心）：
- `backend/src/agents/` —— 全部 22 个智能体（含 contract_reviewer, contract_steward, contract_investigator, review_checker, due_diligence_*, lawyer_match_* 等）
- `backend/src/agents/workforce.py`
- `backend/src/agents/coordinator.py`
- `backend/src/agents/consensus_agent.py`
- `backend/src/services/chat_service.py`
- `backend/src/services/llm_service.py`
- `backend/src/services/prompt_assembler.py`
- `backend/src/services/context_compressor.py`
- `backend/src/services/citation_tracker.py`
- `backend/src/services/memory_layer.py`
- `backend/src/services/review_memory.py`
- `backend/src/services/episodic_memory_service.py`
- `backend/src/services/legal_intent_guardrails.py`
- `backend/src/api/routes/chat.py`
- `backend/src/api/routes/ai_assistant.py`
- `backend/src/api/routes/llm.py`
- `backend/src/api/routes/chat_handlers/`（全部）
- `backend/src/prompts/`（全部 system / role / few-shot）

前端：
- `frontend/src/pages/Chat.tsx`
- `frontend/src/components/chat/`
- `frontend/src/components/ai/`
- `frontend/src/components/ai-assistant/`

测试：
- `backend/tests/test_chat_*.py`
- `backend/tests/test_business_agents.py`
- `backend/tests/test_chat_template_context.py`
- `frontend/e2e/chat.spec.ts`

### 不要碰的文件

- `backend/src/services/payment_service.py` / `subscription_service.py` —— 任务 10
- `backend/src/services/esign_service.py` —— 任务 5
- `backend/src/api/routes/lawyer_matching.py` —— 任务 8b
- `backend/src/api/routes/due_diligence.py` —— 任务 9
- `backend/src/services/a2ui_*.py` —— 任务 4
- `frontend/src/lib/design-tokens.ts` —— 全局护栏，禁改

---

## §2 必修 P0（带文件:行号 + 期望状态）

### P0-1 协调器对四类核心意图的路由准确率 ≥ 90%

- 位置：`backend/src/agents/coordinator.py`、`backend/src/services/chat_service.py`、`backend/src/services/legal_intent_guardrails.py`
- 现状：四类意图（合同 / 尽调 / 法规 / 找律师）路由依赖关键词 + 单次 LLM 分类，缺少混淆样本回归集，命中率未量化
- 期望：构建 ≥ 200 条标注语料（每类 50 条 + 边界 / 反例），`pytest -k coordinator_routing` 输出准确率 ≥ 90%；低置信度（< 0.6）落入"澄清"分支而非默认 fallback

### P0-2 Prompt 注入防护

- 位置：`backend/src/services/prompt_assembler.py`、`backend/src/services/legal_intent_guardrails.py`、`backend/src/api/routes/chat.py`
- 现状：用户消息直接拼入上下文，未做 instruction-injection 过滤；"ignore previous instructions / 你现在是另一个助手 / system: ..." 等话术可越权
- 期望：用户输入进入 LLM 前，过 `legal_intent_guardrails` 的注入检测器（关键词 + 启发式 + 小模型分类，三票任一命中即标记），命中后改写为安全包装、并在审计日志记录原文 hash

### P0-3 长对话上下文压缩 + 引用追溯不丢

- 位置：`backend/src/services/context_compressor.py`、`backend/src/services/citation_tracker.py`、`backend/src/services/memory_layer.py`
- 现状：超长对话压缩后 citation id 与原段落映射丢失；review_memory 取回后无法定位原文
- 期望：压缩前给每个引用块分配稳定 `cite_id`（hash + 顺序号），压缩后重排不变；`pytest -k citation_after_compress` 全绿；前端点击引用可定位到原始消息

### P0-4 流式输出超时、断线重连、token 计费

- 位置：`backend/src/api/routes/chat.py`、`backend/src/services/llm_service.py`、`frontend/src/components/chat/`
- 现状：SSE 流断线后前端只显示"对话失败"，已扣 token 但用户看不到部分回复；服务端无 server-side timeout，长尾请求可挂死 worker
- 期望：
  - 服务端：单次流式硬超时 60s（可配置），首 token 超时 10s
  - 前端：SSE `onerror` 后自动重连一次（带 `last_event_id`），失败再降级为轮询
  - 计费：以"实际产出 token"计而非"请求开始"计；中断时按已产出部分入账，写入 `llm_usage_log` 表的 `interrupted_at`

### P0-5 22 个智能体的最小可验证能力契约

- 位置：`backend/src/agents/*.py` + `backend/tests/test_business_agents.py`
- 现状：智能体类存在，但部分（尤其 contract_steward / consensus_agent / review_checker）缺少端到端"输入 → 期望输出"测试，回归无依据
- 期望：每个智能体至少 1 条最小 happy-path + 1 条边界 case 测试；统一契约接口（`name / accepts / produces / max_latency_ms / fallback_strategy`）；契约通过 `tests/test_agent_contracts.py` 自动校验

---

## §3 流程

### Step 0 — PRD vs 代码现实差分（强制）

输出 `docs/audit/03-agents/00-prd-reality-gap.md`：
- 把 `PROJECT_STATUS.md` 中"AI 智能体 / 对话 / Prompt"标"已完成"项与实际代码逐条对账
- 重点关注 `coordinator.py` 的"22 智能体协同" + `consensus_agent.py` 的"共识投票" + Prompt 体系的多组织隔离

### Step 1 — 检索与读取

1. `/hierarchical-memory find-feature "agent coordinator routing"` / `find-bugfix "prompt injection"`
2. `/iterative-retrieval` 按"路由 → coordinator → workforce → 单 agent → prompts → tests"分层读
3. 读 `legal_intent_guardrails.py` 现有规则，确认是否已有注入防护雏形

### Step 2 — Track A 三角对齐

输出 `01-prd-coverage.md`：把 PRD 承诺（22 智能体 / 协调路由 / 流式 / 引用追溯）与代码 + 路由 + 前端 + 测试四面对齐。

### Step 3 — Track B 质量四件套

`/code-review` + `/backend-patterns` + `/api-design` + `/security-review`（重点 prompt 注入 + LLM 用量爆破）。

### Step 4 — P0 修复

按 P0-1 → P0-5 顺序修复，每个 P0 单独 commit + 单独测试运行通过。

### Step 5 — 测试补全

- `/tdd-workflow` 补 P0-1 路由准确率回归集 + P0-3 引用追溯 + P0-5 智能体契约
- `/e2e-testing` 补 `frontend/e2e/chat.spec.ts` 的"长对话压缩 + 引用点击 + 流式中断重连"三个故事

### Step 6 — `/verification-loop` + `/simplify` + `/hierarchical-memory add-feature/add-bugfix`

---

## §4 输出物

```
docs/audit/03-agents/
  ├─ 00-prd-reality-gap.md
  ├─ 01-prd-coverage.md
  ├─ 02-issues.md            P0/P1/P2 清单
  ├─ 03-fixes.md             本轮修复变更说明
  ├─ 04-test-additions.md    新增测试 + 覆盖率前后对比
  └─ 05-followups.md         遗留 → memory
```

代码 PR：建议拆 5 个（每个 P0 一个），全部跑通后再合并到主分支。

---

## §5 风险护栏

- **修改 `backend/src/prompts/` 任一文件前必须 diff 给用户**，禁止未审核就改 system prompt
- **不要把 LLM API key 写进任何测试 fixture**；测试用 mock LLM client，真实调用走 `respx` / VCR 录制回放
- 不动 `payment_service` / `subscription_service` / `esign_service`（任务 10 / 5 范围）
- 路由准确率回归集若引入第三方语料，需标注许可来源；不得抓取微信内容
- 流式中断的"已产出 token 入账"逻辑要给用户审；不得擅自调整计费规则
- LLM 用量限流（防恶意刷 token）若新增策略，需要先与任务 1（认证 + 限流）协商共用基础设施

---

## §6 完成标准 DoD

- [ ] Step 0 差分文档输出，用户审阅通过
- [ ] P0-1 路由准确率 ≥ 90%（200 条回归集）
- [ ] P0-2 注入检测器命中率 ≥ 95%（标准注入语料 + 业务定制语料各 50 条）
- [ ] P0-3 `pytest -k citation_after_compress` 全绿；前端引用点击 e2e 通过
- [ ] P0-4 SSE 断线重连 e2e 通过；`llm_usage_log.interrupted_at` 有数据
- [ ] P0-5 22 个智能体契约测试 100% 通过
- [ ] `pytest backend/tests/test_chat_*.py test_business_agents.py test_chat_template_context.py` 全绿
- [ ] `frontend/e2e/chat.spec.ts` 全绿
- [ ] `02-issues.md` 中 P0 全部状态 = "已修复"，P1 / P2 列入 followups
- [ ] hierarchical-memory `add-feature` / `add-bugfix` 已沉淀
