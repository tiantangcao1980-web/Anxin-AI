# TASK-12 企业智能体工作台与治理引擎

> 波次 5 · 工时估 8-12 天
> 前置依赖：任务 1（认证）、任务 2（三态运行/LLM）、任务 3（Agent）、任务 4（A2UI）、任务 7（知识库）、任务 11a/11b/11c（桌面/同步/移动）
> 必读：`../PLAN.md`、`../00-platform/01-prd-reality-gap.md`、`docs/openspec/00-intelligent-assistant-platform-spec.md`、`docs/references/agentic-platform-benchmark-2026-05-08.md`

> 定位：把安心 AI 从“能调用工具的助手”升级为“企业可治理的智能体工作台”。能力可以强，但必须默认可控、可审计、可撤销、可解释。

---

## 1. 范围

### 要碰的文件

- 后端模型与迁移：
  - **新建** `backend/src/models/agent_governance.py`
  - **新建** alembic migration：agent managers / teams / workers / humans / channel policies / capability routes / approvals / audit events
  - **新增** SkillGovernance proposal / enabled version / audit persistence migration
- 后端服务：
  - **新建** `backend/src/services/agent_governance_service.py`
  - **新建** `backend/src/services/capability_policy_engine.py`
  - **新建** `backend/src/services/agent_approval_service.py`
  - **新建** `backend/src/services/agent_audit_service.py`
  - **新建** `backend/src/services/skill_governance_service.py`
  - 改造 `backend/src/services/mcp_client_service.py`、`skill_service.py`、`llm_service.py`、`private_llm_service.py`
- 后端路由：
  - **新建** `backend/src/api/routes/agent_governance.py`
  - **新建** `backend/src/api/routes/capability_routes.py`
  - **新建** `backend/src/api/routes/agent_approvals.py`
  - **新建** `backend/src/api/routes/skill_governance.py`
- 前端：
  - **新建** `frontend/src/pages/AgentGovernance.tsx`
  - **新建** `frontend/src/pages/CapabilityCenter.tsx`
  - **新建** `frontend/src/components/agent-governance/`
  - `frontend/src/components/pro/ProLayout.tsx`（增加治理入口，仅老板/超级管理员可见）
- 桌面/移动协同：
  - `frontend/src/components/desktop/`（显示当前 agent 能力、风险级别、审批状态、执行审计）
  - `mobile/app/desktop-control.tsx`（消费审批和远控状态，不在本任务实现底层远控）
- 测试：
  - **新建** `backend/tests/test_agent_governance_policy.py`
  - **新建** `backend/tests/test_capability_routes.py`
  - **新建** `backend/tests/test_agent_approval_flow.py`
  - **新建** `frontend/src/pages/AgentGovernance.test.tsx`

### 不要碰的文件

- payment / esign live provider 真实渠道逻辑
- 桌面签名、公证、自动更新
- `backend/src/prompts/`，除非任务明确要求并单独审查
- 生产 `.env` 或任何真实密钥

---

## 2. 必修 P0

| # | 能力 | 现状 | 期望 |
|---|---|---|---|
| P0-1 | 统一权限决策 | 目前 RBAC、订阅、隐私模式、工具调用分散 | `capability_policy_engine` 统一判定 `subscription + role + permission + risk_level + privacy_mode + device_trust + channel_policy + approval_state` |
| P0-2 | Agent 控制面模型 | AgentManager/Team/Worker/Human/ChannelPolicy/CapabilityRoute/TokenLease/Approval/AuditEvent 模型与迁移已补；route-token 服务已接入 DB；UI/真实运行时接入未闭环 | 建立可审计数据模型，支持组织/部门/项目/客户维度 |
| P0-3 | 真实密钥隔离 | 持久化 route-token lease 已只存 hash，跨服务实例可验证；MCP tool execution、CLI `/execute`、REST/SSE/WebSocket Chat Agent LLM runtime、RAG direct LLM 与浏览器/爬虫 fetch 入口已在商业环境接入 DB-backed route token；完整浏览器自动化和 desktop-control 高风险真实调用链尚未全部改造 | Agent/Worker 只拿短期 consumer token 或等价 route token；真实 API key/PAT/财税凭据只在密钥服务/网关侧 |
| P0-4 | 高风险审批 | 高风险动作已有最小 service/API/UI 审批模型；真实能力链路接入未闭环 | L3/L4 能力必须创建 approval request；老板/超级管理员或授权管理员批准后才能执行；过期/撤销 fail-closed |
| P0-5 | 通信/房间策略 | 当前没有声明式 agent channel policy | 定义谁能看、谁能说、谁能 @、谁能分派、谁能接管；外部专业服务方只能看授权材料包 |
| P0-6 | 可见审计与接管 | agent 执行过程散落在日志或消息中 | 高风险任务进入可审计工作室；支持旁听、暂停、接管、终止、导出 artifact |
| P0-7 | 能力中心 | 模型、Skills、MCP、浏览器、CLI、远控分散 | 老板/超级管理员看到能力市场、启用状态、风险级别、调用次数、失败率、最近审计 |
| P0-8 | Skills 进化治理 | Skill 能力缺版本/评测/审批/回滚 | Skill 创建、升级、自我改进提案、评测、审批、灰度、回滚全部进入治理流；agent 只能提案，不能无审批自改生产能力 |

---

## 3. 流程

### Step 0 · PRD vs 现实差分

产出 `docs/audit/12-enterprise-agent-governance/00-prd-reality-gap.md`：

- 当前 RBAC/订阅/隐私模式/LLM/MCP/Skills/桌面远控各自在哪里做判断。
- 哪些高风险能力还没有统一审批。
- 哪些 agent/tool 路径可能直接接触真实密钥或无边界文件系统。
- HiClaw 借鉴项：Manager/Leader/Worker/Human、ChannelPolicy、Gateway consumer token、SharedArtifactStore，哪些适合本项目 P0。

### Step 1 · 数据模型与迁移

建立最小模型：

- `agent_managers`：组织/项目级协调者。
- `agent_teams`：部门/项目/客户事项团队。
- `agent_workers`：执行单元、runtime、risk profile、capability scope。
- `human_participants`：用户、外部服务方和可见范围。
- `agent_channel_policies`：group/DM/workspace allow/deny。
- `capability_routes`：LLM/MCP/Skill/CLI/browser/desktop-control route 与 allowed consumers。
- `capability_route_token_leases`：短期 route token 的 hash、consumer、scope、过期和撤销状态；不保存原始 token。
- `agent_approvals`：审批状态、过期、撤销、二次确认。
- `agent_audit_events`：请求、拒绝、批准、执行、失败、撤销、接管。

当前本地进展：

- `backend/src/models/agent_governance.py` 已建立 AgentManager、AgentTeam、AgentWorker、HumanParticipant、AgentChannelPolicy、CapabilityRoute、CapabilityRouteTokenLease、AgentApproval 和 AgentAuditEvent。
- `backend/alembic/versions/040_add_agent_governance_control_plane.py` 已提供上述 9 张表的 upgrade/downgrade，并在 PostgreSQL 上为 `agent_audit_events` 创建 update/delete 拒绝 trigger。
- `backend/tests/test_agent_governance_models.py` 已锁住模型注册、CapabilityRoute 不保存真实密钥/原始 token、TokenLease 只保存 hash、组织级 route 唯一约束、复合租户外键、跨组织写入失败、审计不可变监听和迁移无敏感列。
- `backend/alembic/versions/041_add_skill_governance_persistence.py` 已新增 SkillGovernanceProposal、SkillEnabledVersion 和 SkillGovernanceAuditEvent 持久化表；审计表同样在模型监听器和 PostgreSQL trigger 层拒绝 update/delete。
- `backend/src/services/agent_approval_service.py` 已补 DB-backed 高风险 AgentApproval service，覆盖创建审批、授权角色审批/驳回、过期 fail-closed、撤销 fail-closed、action/route 匹配、workspace-control 未批准先拒绝、运行时未接入 fail-closed、已批准工作室 artifact list/create/export、artifact 递归脱敏和审计写入；`backend/tests/test_agent_approval_service.py` `8 passed`。
- `backend/src/api/routes/agent_approvals.py` 已补正式高风险智能体审批 API，覆盖创建、列表/详情、pending count、audit-events、audit-export、workspace-control、approve/reject/revoke、validate、workspace artifacts list/create/export 和组织 CapabilityRoute list/update；`backend/tests/test_agent_approval_api.py` `7 passed`。
- 后续仍需把这些模型接入完整 Human-in-the-loop 工作室、真实 approved MCP connector 演练、LLM/browser/desktop-control 能力链路和跨进程撤销失权证据；当前前端已先补最小高风险审批工作台入口。

### Step 2 · Policy Engine

实现统一入口：

```text
can_execute_capability(actor, org, capability, risk_level, data_scope, privacy_mode, device, channel, approval)
```

必须返回：

- `allowed: true/false`
- `reason_code`
- `human_message`
- `required_action`（subscribe / request_approval / switch_mode / pair_device / contact_admin）
- `audit_event_id`

当前本地进展：

- `backend/src/services/capability_policy_engine.py` 已补统一能力决策入口 `CapabilityPolicyEngine.can_execute_capability()`，把订阅 feature、角色、权限、风险级别、隐私模式、数据范围、设备信任、通道策略、CapabilityRoute 状态和 AgentApproval 审批状态串为单次可审计决策，并写入 `AgentAuditEvent`。
- `backend/tests/test_capability_policy_engine.py` 已覆盖通过路径、订阅缺失、权限缺失、绝密/本地模式拒绝 networked/external 能力、未受信设备拒绝桌面控制、通道策略拒绝、L3/L4 高风险能力审批前拒绝/审批后放行，以及员工浏览器填表被拒、部门管理员报表 Agent 放行、老板桌面远控审批、超级管理员撤销 MCP route 后 route/token 失权、外部服务方材料包边界五类权限回归；当前 `11 passed`。
- `scripts/commercial-readiness-gate.sh --with-local-tests` 已加入 unified capability policy engine tests。该切片只关闭服务层统一判定，不替代完整 browser automation、desktop-control 执行链路接入和真实 runtime evidence。

### Step 3 · Gateway/Consumer Token 模型

- Agent/Worker 不直接读取真实密钥。
- 每个 Worker/CapabilityRoute 分配短期 consumer token。
- 撤销 route 后，agent 下一次调用立即 401/403。
- LLM/MCP/CLI/browser/desktop-control 都必须经过 route policy。

当前本地进展：

- `backend/src/services/agent_governance_service.py` 已提供 DB-backed route token service：创建 CapabilityRoute、签发短期 token、持久化 `CapabilityRouteTokenLease.token_hash`、跨 service 实例验证、consumer 绑定验证、撤销 route 后下一次验证失败并写 `AgentAuditEvent`。
- `backend/src/services/agent_governance_service.py` 已补组织级 CapabilityRoute 策略 CRUD 底座：管理员可列出/更新 route status、consumer、scope、risk、TTL 和 policy；policy 会递归脱敏 token/secret/password/credential/api_key 字段；禁用 route 会撤销现有 lease，并让下一次 token validate fail-closed。
- `backend/src/services/mcp_client_service.py` 已在 `call_tool` 前接入 DB-backed route token；staging/production 默认 fail-closed，开发/测试可用 `MCP_TOOL_ROUTE_TOKEN_REQUIRED=true` 提前演练。
- `backend/src/api/routes/cli.py` 已在 CLI `/execute` 前接入 DB-backed route token，并新增 `/cli/route-token` 供桌面端按 API Key `key_id` consumer 获取短期 token；staging/production 默认 fail-closed，开发/测试可用 `CLI_ROUTE_TOKEN_REQUIRED=true` 提前演练；consumer 绑定到 API Key `key_id`，并按命令 scope 校验 `cli:read/chat/export`。
- `desktop/src/commands/cli.rs` 已在 CLI execute 前尝试获取短期 route token，并在调用 `/cli/execute` 时传递 `X-Capability-Route-Token`；开发环境 route 缺失时保持兼容，商业环境由后端 fail-closed。
- `backend/src/services/llm_route_governance.py`、`backend/src/agents/base.py` 和 `backend/src/api/routes/chat.py` 已把 REST/SSE/WebSocket Chat Agent LLM runtime 接入 DB-backed route token：staging/production 默认 fail-closed，开发/测试可用 `LLM_ROUTE_TOKEN_REQUIRED=true` 提前演练；scope 固定为 `llm:chat`，`/chat/route-token` 可按当前用户 consumer 签发短期 token，WebSocket 首包、连接 header 或单条消息 payload 可传递 route token，Agent 同步/流式模型调用在真实 HTTP 前校验 token。
- `backend/src/services/crawler_service.py` 已在 `crawler_service.fetch()` 的 robots/http 访问前接入 DB-backed browser route token；staging/production 默认 fail-closed，开发/测试可用 `BROWSER_FETCH_ROUTE_TOKEN_REQUIRED=true` 提前演练；scope 固定为 `browser:fetch`，route 撤销后下一次 fetch 在触网前拒绝；`due_diligence_service.py` 已移除执行信息/信用中国/裁判文书查询的直接 Playwright fallback，只允许走合规 crawl service 或返回无外部证据。
- `backend/src/agents/base.py` / `workforce.py` / `task_context.py` 已支持通过 `mcp_route_context`/contextvars 将 route token 传递到真实 MCP tool execution。
- `backend/tests/test_agent_governance_service.py` 已覆盖 hash-only lease、原始 token 不入审计、组织隔离、consumer/scope 拒绝、过期 fail-closed、consumer mismatch、route 撤销后下一次调用失败，以及组织策略更新脱敏/禁用撤销 lease。
- `backend/tests/test_mcp_route_governance.py` 已覆盖 MCP 开发态兼容、商业环境缺 token fail-closed、DB route token 放行、route revoke 后拒绝和 consumer mismatch 拒绝。
- `backend/tests/test_cli_route.py` 已覆盖 CLI 开发态兼容、商业环境缺 token fail-closed、DB route token 放行、`/cli/route-token` 签发和 consumer mismatch 拒绝。
- `backend/tests/test_llm_route_governance.py` 已覆盖 LLM runtime 商业环境缺 token fail-closed、DB route token 放行、route revoke 后在模型 HTTP 前拒绝、流式模型调用触网前拒绝、WebSocket route-token credential 提取、WebSocket-like contextvar 流式传递和 `/chat/route-token` 用户绑定签发。
- `backend/tests/test_crawler_compliance.py` 已覆盖浏览器/爬虫商业环境缺 token fail-closed、DB route token 放行、route revoke 后在 robots/http 前拒绝。
- `scripts/commercial-readiness-gate.sh --with-local-tests` 已加入 `agent governance service tests`、`MCP route governance tests`、`CLI route governance tests`、`LLM route governance tests` 与 `crawler browser route governance tests`。
- RAG direct LLM 已补：`RAGService.generate/expand_query/_extract_entities/stream_query` 在直接调用 OpenAI 或本地模型前会校验 DB-backed `llm:chat` route token，REST Knowledge RAG、同步 Chat RAG 和 WebSocket RAG 均会传递 route context；`backend/tests/test_llm_route_governance.py` 已覆盖缺 token 触网前拒绝、DB route token 放行与 route 撤销后拒绝。
- 后续仍需把完整 browser automation、desktop-control 高风险真实调用链全部切到该服务，并补真实 approved MCP connector 演练、跨进程/多实例撤销传播证据。

### Step 4 · Human-in-the-loop 工作室

- 高风险任务创建可审计工作室。
- 老板/超级管理员可旁听、暂停、接管、终止。
- 普通员工只能看自己发起或被授权的工作室。
- 外部服务方只能看授权材料包和沟通区。

当前本地进展：

- `AgentApprovalService` 已补后端 service 级审批底座：普通员工可发起待审批请求；只有 owner/boss/super_admin/org_admin/admin 可决定或撤销；审批过期、撤销、未批准、action mismatch、route mismatch 和 route disabled/revoked 都会 fail-closed 并写 `AgentAuditEvent`。
- `backend/src/api/routes/agent_approvals.py` 已补正式 API：创建审批、按组织/本人 scope 列表与详情、pending count、audit-events、audit-export、approve/reject/revoke、workspace-control fail-closed、执行前 validate、workspace artifacts list/create/export，并由 `backend/tests/test_agent_approval_api.py` 覆盖未登录拒绝、普通员工不能自批、管理员批准后 validate 放行、撤销后 fail-closed、审批审计时间线/导出、运行时未接入时暂停/接管/终止拒绝、已批准工作室成果记录/导出和 payload/artifact 脱敏。
- `frontend/src/pages/AgentApprovalWorkspace.tsx` 已补最小 Human-in-the-loop 高风险审批入口：按状态筛选、展示风险动作/route/payload 预览、批准/驳回/撤销、审批审计时间线、JSON 导出和已批准工作室控制入口，并接入 `/agent-approvals` API、桌面侧边栏、移动协作导航；能力策略面板已按当前组织角色过滤可见工具，老板/Owner/超级管理员/admin 类角色看全量，普通员工只看基础能力和可申请能力，高风险/full-only 工具保持隐藏；`frontend/e2e/agent-approval-workspace.spec.ts` 覆盖桌面审计/导出/批准动作、运行时未接入时控制 fail-closed、员工能力中心可见边界和移动端视口不横向溢出。
- `scripts/commercial-readiness-gate.sh --with-local-tests` 已加入 `agent approval service tests`、`agent approval API tests` 与 `frontend agent approval workspace e2e`。
- 已批准工作室的最小 artifact-first 成果流已补：管理员可记录脱敏 summary artifact、列表查看和 JSON 导出，前端工作台可查看/新增/导出工作室成果。仍缺完整工作室旁听、真实暂停/接管/终止执行效果、长任务 artifact 编辑/跨端恢复和真实执行链路接入。

### Step 5 · 前端能力中心

- 能力列表：基础问答、知识库、文档草稿、浏览器执行、CLI harness、软件/原型、远控桌面、MCP、Skills。
- 每个能力展示：订阅要求、可用角色、风险级别、隐私模式限制、版本、owner、评测状态、最近调用、失败率、审计入口。
- 老板/超级管理员可启用/禁用能力，部门管理员只能申请部门级能力。

当前本地进展：

- 最小 Agent 治理工作台中的能力策略面板已完成角色可见性收口：全量角色可见全部注册工具；普通员工只见低风险基础能力和需要审批的可申请能力；MCP 管理、远控桌面等高风险/full-only 能力在员工视角隐藏；`loginAsRole` Playwright harness 已能模拟 employee/admin 角色并锁住该边界。组织能力策略面板已接入 `/agent-approvals/capability-routes`，全量角色可查看并启用/禁用 CapabilityRoute，禁用会走后端策略更新和 lease 撤销；套餐购买联动、部门级申请流、完整策略编辑器和真实 connector 演练仍待后续闭环。

### Step 6 · Skill Evolution Gate

当前本地进展：

- `backend/src/services/skill_evolution_service.py` 已补最小本地门禁：draft proposal、required eval checks、授权角色审批、灰度、回滚和审计。
- `backend/src/services/skill_service.py` 已支持在治理模式下只返回当前 enabled version。
- `backend/tests/test_skill_evolution_service.py` 与 `backend/tests/test_skill_service.py` 已覆盖 agent 不能自启生产版本、评测失败/缺失拒绝审批、越权审批拒绝、灰度百分比边界、回滚后下一次技能匹配回到上一版本。
- `backend/src/services/skill_governance_service.py` 已把 Skill 进化门禁生产化为 DB-backed SkillGovernance：proposal、required eval、授权审批、灰度启用、回滚、enabled version 查询、组织隔离和审计事件都可跨 service 实例持久化；`backend/src/api/routes/skill_governance.py` 已补正式 API，覆盖提案、列表/详情、enabled version、评测、审批、灰度、回滚、audit-events 和 audit-export；`backend/tests/test_skill_governance_models.py`、`backend/tests/test_skill_governance_service.py` 与 `backend/tests/test_skill_governance_api.py` 共 `16 passed`。
- 仍需后续把 AgentApproval/AgentAuditEvent/SkillGovernance 接入完整 browser automation 和 desktop-control 执行链路、组织级能力中心 UI、真实 CapabilityRoute 撤销联动、记忆治理和商业发布证据；RAG direct LLM 的 route-token 代码级边界已收口，但还需纳入完整商业运行时演练。

- 定义 `SkillEvolutionProposal`：来源失败案例、用户反馈、评测失败、人工建议或 agent 观察。
- Proposal 只能生成草案、测试和风险说明；不得自动修改 enabled Skill。
- 升级前必须通过 eval suite、权限回归、隐私模式回归、注入防护和审计日志检查。
- 老板/Owner 或超级管理员审批后才能灰度启用组织级或高风险 Skill。
- 回滚/禁用后，对应 CapabilityRoute 下一次调用必须失败并写审计。

---

## 4. 输出物

```
docs/audit/12-enterprise-agent-governance/
├─ 00-prd-reality-gap.md
├─ 01-prd-coverage.md
├─ 02-issues.md
├─ 03-fixes.md
├─ 04-test-additions.md
└─ 05-followups.md
```

附加：

- `docs/security/agent-governance-policy.md`
- `docs/architecture/agent-control-plane.md`
- `docs/release/evidence/agent-governance-smoke.md`

---

## 5. 风险护栏

- **默认最小权限**：组织开通后只开放 L0/L1 基础能力；高级能力需要订阅和管理员启用。
- **真实密钥隔离**：Agent/Worker 不得持有真实 API key、GitHub PAT、财税接口 key、浏览器账号密码。
- **高风险动作审批**：L3/L4 必须审批；L5 默认禁止。
- **绝密模式**：外部 MCP、云端模型、浏览器执行、远控外传默认拒绝。
- **外部专业服务方**：只能访问授权材料包，不得跨客户检索。
- **不可关闭审计**：老板/超级管理员也不能关闭审计；只能设置保留期和脱敏策略。
- **自我进化不越权**：agent 可以总结失败、提出 Skill 改进、生成测试和提交审批，但不能直接启用高风险能力、修改生产 prompt 或扩大数据权限。
- **不新增依赖**：P0 先用现有数据库、服务层、审计表和对象存储模式实现。

---

## 6. 完成标准

- [x] `capability_policy_engine` 服务层覆盖订阅、角色、权限、风险级别、隐私模式、设备信任、通信策略和审批状态；真实 LLM、完整浏览器自动化和 desktop-control 运行时链路接入仍需后续闭环。
- [x] AgentManager / AgentTeam / AgentWorker / HumanParticipant / ChannelPolicy / CapabilityRoute / TokenLease / Approval / AuditEvent 模型与 migration 有 upgrade/downgrade。
- [x] AgentApproval service/API 和最小前端工作台具备创建、列表/count、审批/驳回/撤销、过期、action/route 匹配、执行前 validate、组织/本人 scope、审批审计时间线、审批审计 JSON 导出、已批准工作室 artifact list/create/export、运行时未接入时 workspace-control fail-closed、移动视口回归和审计回归；完整工作室和真实执行链路接入仍未完成。
- [ ] Worker/Agent 不持有真实密钥；MCP tool execution、CLI `/execute`、REST/SSE/WebSocket Chat Agent LLM runtime、RAG direct LLM、桌面端 CLI route-token 获取/传递和浏览器/爬虫 fetch 入口已有 DB-backed route-token fail-closed 代码级回归，完整 browser automation、desktop-control 和真实 approved connector 演练仍待闭环。
- [x] 五类权限回归通过：员工浏览器填表被拒、部门管理员创建部门报告 agent、老板批准桌面远控、超级管理员撤销 MCP route、外部服务方只能看授权材料包；真实运行时 connector/工作室证据仍需后续闭环。
- [x] 能力中心最小可见性已按角色收口：老板/Owner/超级管理员/admin 看全量，普通员工只见基础能力和可申请项；组织级 CapabilityRoute 策略已具备最小 list/update API、policy 脱敏、禁用即撤销 lease 和前端启用/禁用面板；订阅购买联动、部门申请流、完整策略编辑器和真实 connector 演练仍待闭环。
- [x] Skill 进化提案、评测门禁、管理员审批、灰度启用和回滚禁用已有本地与 DB-backed 正反向测试；组织级 UI、真实执行链路失权和商业发布证据仍未闭环。
- [x] 高风险工作室已具备最小 artifact-first 成果记录、查看和导出代码级闭环。
- [ ] 高风险工作室支持完整旁听、真实暂停/接管/终止执行效果、artifact 编辑/跨端恢复和真实运行时证据。
- [ ] 后端 pytest、前端 lint/build/test、release evidence secret scan 通过。
