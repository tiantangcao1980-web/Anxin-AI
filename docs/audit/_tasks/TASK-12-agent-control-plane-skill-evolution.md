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
- 后端服务：
  - **新建** `backend/src/services/agent_governance_service.py`
  - **新建** `backend/src/services/capability_policy_engine.py`
  - **新建** `backend/src/services/agent_approval_service.py`
  - **新建** `backend/src/services/agent_audit_service.py`
  - 改造 `backend/src/services/mcp_client_service.py`、`skill_service.py`、`llm_service.py`、`private_llm_service.py`
- 后端路由：
  - **新建** `backend/src/api/routes/agent_governance.py`
  - **新建** `backend/src/api/routes/capability_routes.py`
  - **新建** `backend/src/api/routes/agent_approvals.py`
- 前端：
  - **新建** `frontend/src/pages/AgentGovernance.tsx`
  - **新建** `frontend/src/pages/CapabilityCenter.tsx`
  - **新建** `frontend/src/components/agent-governance/`
  - `frontend/src/components/pro/ProLayout.tsx`（增加治理入口，仅老板/超级管理员可见）
- 桌面/移动协同：
  - `frontend/src/components/desktop/`（显示当前 agent 能力、风险级别、审批状态、执行审计）
  - `mobile/app/desktop-control/`（消费审批和远控状态，不在本任务实现底层远控）
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
| P0-3 | 真实密钥隔离 | 持久化 route-token lease 已只存 hash，跨服务实例可验证；MCP/LLM/CLI/browser/desktop-control 真实调用链尚未全部改造 | Agent/Worker 只拿短期 consumer token 或等价 route token；真实 API key/PAT/财税凭据只在密钥服务/网关侧 |
| P0-4 | 高风险审批 | 高风险动作缺统一审批模型 | L3/L4 能力必须创建 approval request；老板/超级管理员或授权管理员批准后才能执行；过期/撤销 fail-closed |
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
- 后续仍需把这些模型接入 service/API/UI、真实 MCP/LLM/CLI/browser/desktop-control 能力链路、Human-in-the-loop 工作室和跨进程撤销失权证据。

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

### Step 3 · Gateway/Consumer Token 模型

- Agent/Worker 不直接读取真实密钥。
- 每个 Worker/CapabilityRoute 分配短期 consumer token。
- 撤销 route 后，agent 下一次调用立即 401/403。
- LLM/MCP/CLI/browser/desktop-control 都必须经过 route policy。

当前本地进展：

- `backend/src/services/agent_governance_service.py` 已提供 DB-backed route token service：创建 CapabilityRoute、签发短期 token、持久化 `CapabilityRouteTokenLease.token_hash`、跨 service 实例验证、撤销 route 后下一次验证失败并写 `AgentAuditEvent`。
- `backend/tests/test_agent_governance_service.py` 已覆盖 hash-only lease、原始 token 不入审计、组织隔离、consumer/scope 拒绝、过期 fail-closed 和 route 撤销后下一次调用失败。
- `scripts/commercial-readiness-gate.sh --with-local-tests` 已加入 `agent governance service tests`。
- 后续仍需把 MCP/LLM/CLI/browser/desktop-control 真实调用链全部切到该服务，并补跨进程/多实例撤销传播证据。

### Step 4 · Human-in-the-loop 工作室

- 高风险任务创建可审计工作室。
- 老板/超级管理员可旁听、暂停、接管、终止。
- 普通员工只能看自己发起或被授权的工作室。
- 外部服务方只能看授权材料包和沟通区。

### Step 5 · 前端能力中心

- 能力列表：基础问答、知识库、文档草稿、浏览器执行、CLI harness、软件/原型、远控桌面、MCP、Skills。
- 每个能力展示：订阅要求、可用角色、风险级别、隐私模式限制、版本、owner、评测状态、最近调用、失败率、审计入口。
- 老板/超级管理员可启用/禁用能力，部门管理员只能申请部门级能力。

### Step 6 · Skill Evolution Gate

当前本地进展：

- `backend/src/services/skill_evolution_service.py` 已补最小本地门禁：draft proposal、required eval checks、授权角色审批、灰度、回滚和审计。
- `backend/src/services/skill_service.py` 已支持在治理模式下只返回当前 enabled version。
- `backend/tests/test_skill_evolution_service.py` 与 `backend/tests/test_skill_service.py` 已覆盖 agent 不能自启生产版本、评测失败/缺失拒绝审批、越权审批拒绝、灰度百分比边界、回滚后下一次技能匹配回到上一版本。
- 仍需后续把本地门禁生产化为数据库持久化 SkillGovernance，并把 AgentApproval/AgentAuditEvent 接入真实执行链路、组织级能力中心 UI、真实 CapabilityRoute 撤销联动和记忆治理。

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

- [ ] `capability_policy_engine` 覆盖订阅、角色、权限、风险级别、隐私模式、设备信任、通信策略和审批状态。
- [x] AgentManager / AgentTeam / AgentWorker / HumanParticipant / ChannelPolicy / CapabilityRoute / TokenLease / Approval / AuditEvent 模型与 migration 有 upgrade/downgrade。
- [ ] Worker/Agent 不持有真实密钥；撤销 CapabilityRoute 后下一次调用失败并写审计。
- [ ] 五类权限回归通过：员工浏览器填表被拒、部门管理员创建部门报告 agent、老板批准桌面远控、超级管理员撤销 MCP route、外部服务方只能看授权材料包。
- [ ] 能力中心只对老板/超级管理员展示全量能力；普通员工只见基础能力和可申请项。
- [ ] Skill 进化提案、评测门禁、管理员审批、灰度启用和回滚禁用有正反向测试。
- [ ] 高风险工作室支持旁听、暂停、接管、终止和 artifact 导出。
- [ ] 后端 pytest、前端 lint/build/test、release evidence secret scan 通过。
