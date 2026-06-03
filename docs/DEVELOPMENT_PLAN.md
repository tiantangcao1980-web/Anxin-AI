# 开发计划 — 单一真相源

> **状态**：本文是当前开发计划的**单一权威来源**。
> **版本**：2026-05-14 · 文档大整合后的开发起点
> **历史来源**：合并自 `docs/audit/summary.md` + `docs/audit/_tasks/README.md` + `docs/plans/2026-05-13-ui-ux-optimization-roadmap.md` + `docs/release/48-hour-commercial-delivery-plan.md`。原文归档到 [docs/archive/legacy-spine-sources/](archive/legacy-spine-sources/)。
> **更新规则**：任务优先级变更时更新（预期每周）。完成的任务移到"已完成"或归档。

---

## 目录

1. [当前执行现状](#1-当前执行现状)
2. [近期优先级清单（P8-P10）](#2-近期优先级清单p8-p10)
3. [多 Lane 并行执行地图](#3-多-lane-并行执行地图)
4. [本轮（2026-05-14）下一批任务](#4-本轮2026-05-14下一批任务)
5. [商业发布冲刺计划（48h 倒排）](#5-商业发布冲刺计划48h-倒排)
6. [任务执行规范](#6-任务执行规范)

---

## 1. 当前执行现状

### 1.1 5 维度快照

| 维度 | 完成度 | 关键阻断 |
|---|---|---|
| **后端** | ✅ 100%（61 v3 endpoint + 543+ pytest） | - |
| **前端** | 🚧 95%（图标体系待收口 47%） | 80 文件待迁 |
| **桌面** | 🚧 80%（unsigned 已 OK，签名缺） | Apple Developer 账号 |
| **移动 / 小程序** | 🚧 70%（code smoke OK，真机缺） | 真机预约 |
| **发布证据** | 🚧 50%（5 类已采，3 类缺） | 真机 live (支付/电签已降为 P3 商业化阶段) |

### 1.2 完成 ✅ / 进行中 🚧 / 待启动 🔜

```
✅ V3 P0-P7 主体骨架
✅ 六层框架 H0-O2 + H1（chat 主路径接 enforcement）
✅ 13 份开发规范
✅ AGENTS.md / DESIGN.md / standards/ 三大单一真相源
✅ 品牌升级收尾（安心法务 → 安心智能助手）
✅ CAMEL-AI 全量剥离
✅ LLM Wiki + 5 Spine 文档（本轮）

🚧 P8 baseline 打磨（UI/UX 3 周计划进行中）
🚧 图标体系 80 文件迁移
🚧 桌面签名 / 公证（阻断）
⏬ 支付 / 电签商业化沙箱（已降为 P3, PMF 后启动；政务签章仅框架占位🟡，未接入·调用即 raise，待商务对接 GDCA/粤企签凭据）
🚧 真机证据采集（阻断）

🔜 P9 5 法务 persona 上层包装
🔜 P10 RAG-Anything 知识库新版
🔜 P11 多租户 RBAC 可视化
🔜 P12 5 personas × 三端 E2E
🔜 P13 anxinai.com 域名切换
```

---

## 2. 近期优先级清单（P8-P10）

### 2.1 P8 — baseline 打磨（本轮主战场）

#### P8.A 桌面同步引擎 + 签名 / 公证

| 子任务 | 状态 | 阻断 | 文件 |
|---|---|---|---|
| 同步引擎设计 | ✅ | - | [docs/desktop/sync-engine-design.md](desktop/sync-engine-design.md) |
| 同步引擎实装 | 🚧 | - | `desktop/src-tauri/src/sync/` |
| 同步协议 | ✅ | - | [docs/desktop/sync-engine-protocol.md](desktop/sync-engine-protocol.md) |
| Runbook | ✅ | - | [docs/desktop/sync-engine-runbook.md](desktop/sync-engine-runbook.md) |
| macOS 签名 / 公证 | 🚫 | Apple Developer 账号 | 等账号 |
| Windows 代码签名 | 🚫 | 证书 | 等证书 |

#### P8.B UI/UX 优化（3 周计划）

详见 [docs/plans/2026-05-13-ui-ux-optimization-roadmap.md](plans/2026-05-13-ui-ux-optimization-roadmap.md)。

| 子任务 | 状态 | 优先级 |
|---|---|---|
| 跨端 token 统一 | 🚧 | P0 |
| 关键流程闭环（假成功 → 真实状态）| 🚧 | P0 |
| 三态视觉（本地/混合/云端 视觉区分） | 🔜 | P1 |
| 可信 AI 交互（来源链路 / 工具调用透明） | 🔜 | P1 |
| 移动专项（真机适配） | 🔜 | P2 |
| 图标体系收口（80 文件迁移） | 🚧 | P0 |

#### P8.C RAG 质量与引用链路

| 子任务 | 状态 | 阻断 |
|---|---|---|
| full50 baseline 真实跑通 | 🚧 | corpus 准备 |
| 引用链路完整性测试 | 🔜 | full50 后 |
| 多模态（MinerU）准确率 | 🚧 | - |

#### P8.D 支付 / 电签 ⬇️ 产品方向调整 (2026-05-14) — 降为 P3 商业化阶段

**用户决策** (2026-05-14):
> 签约和支付等设置付费的功能其实可以先不作为项目核心任务，因为目前我们的核心任务是先把项目的核心功能先验证了，再能谈后续的商业化。签约可以引入政府的平台。

**当前定位**:
- ✅ **核心任务优先**: 核心功能 (Agent / RAG / 协作 / 知识库) PMF 验证先做
- 🟡 **签约入口**: 接入广东省政务签章 (GDCA + 粤企签) 而非商业化 e签宝/法大大
  - 见 [docs/integrations/guangdong-gov-signature.md](integrations/guangdong-gov-signature.md)
  - 代码层仅有**框架占位** Provider (`ESIGN_PROVIDER=gdca/yueqishang`)，**未接入**：未配置凭据时调用任何方法立即 raise `ESignProviderConfigError`（fail-fast，不会静默假成功），实际对接待业务方对接 GDCA / 粤企签凭据后推动
- 🔴 **商业化支付**: 微信/支付宝沙箱凭证暂搁置, PMF 验证后再启动

| 子任务 | 优先级 | 状态 | 阻断 |
|---|---|---|---|
| GDCA 政务签 Provider 框架占位 | P2 | 🟡 框架占位（未接入·调用即 raise，待商务对接 GDCA 凭据） | 业务方 NDA + 商务 |
| 粤企签 / 粤商通 Provider 框架占位 | P2 | 🟡 框架占位（未接入·调用即 raise，待商务对接粤企签凭据） | 数字广东开发者权限 |
| GDCA 真实接入 | P2 | 🚫 | GDCA 测试凭据 |
| 粤企签真实接入 | P2 | 🚫 | 粤商通入驻 + 开发者权限 |
| e签宝 / 法大大 商业化电子签 | P3 | 🟡 placeholder 已写好, 暂不启用 | PMF 验证后启动 |
| 微信/支付宝沙箱 | P3 | 🟡 placeholder 已写好, 暂不启用 | PMF 验证后启动 |
| preflight 命令集 | P3 | ✅ | [release/evidence-collection-runbook](release/evidence-collection-runbook.md) |

### 2.2 P9 — 5 法务 persona 上层包装 ✅ 实现已完成 (2026-05-14 复核)

| 子任务 | 文件 | 状态 |
|---|---|---|
| 法律顾问 persona 上层接口 | `backend/src/agents/personas/legal_advisor.py` | ✅ |
| 合同管家 persona 上层接口 | `backend/src/agents/personas/contract_steward.py` | ✅ |
| 尽调专家 persona | `backend/src/agents/personas/due_diligence_expert.py` | ✅ |
| 财税顾问 persona | `backend/src/agents/personas/tax_finance_advisor.py` | ✅ |
| 安心助理（万能入口）| `backend/src/agents/personas/anxin_assistant.py` | ✅ |
| 5 法务 persona eval baseline | `backend/evals/legal/` | 🚧（持续完善） |

复核结论（2026-05-14）：P9 代码已完整实现，DEVELOPMENT_PLAN 原标记 `🔜` 为陈旧状态。剩余只在 eval baseline corpus 的持续完善与真实业务回放上。

### 2.3 P10 — RAG-Anything 知识库新版

依赖：P8.C RAG baseline 通过。

| 子任务 | 状态 |
|---|---|
| RAG-Anything 调研 | ✅ |
| MinerU 多模态深度集成 | 🚧 |
| 跨模态 KG（图 + 向量 + 多模态） | 🚧 |
| VLM 重排 | 🔜 |
| Dashboard | 🚧 |

---

## 3. 多 Lane 并行执行地图

为了多人 / 多 AI 并行开发，把当前工作分成 6 个 Lane，**写入域不重叠**。

| Lane | 域 | 写入范围 | Completion Gate |
|---|---|---|---|
| **Lane 1** | 政务签章 / 商业化支付 | `backend/src/services/esign_service.py` (GDCA/粤企签 框架占位), `backend/src/services/payment_service.py` | 政务接入 0 个🟡（仅框架占位，未接入·调用即 raise，待商务对接凭据）, 商业化沙箱降为 P3 |
| **Lane 2** | 桌面 | `desktop/`, `docs/desktop/` | signed + notarized package ✅ |
| **Lane 3** | RAG / 案件 / 律师市场 | `backend/src/services/rag/`, `backend/src/agents/personas/legal_*`, `frontend/src/pages/legal/` | full50 baseline ✅ + 5 persona eval ✅ |
| **Lane 4** | 移动 / 小程序 | `mobile/`, `mini-program/`, `apps/uni-mobile/` | 真机 transcript ✅ + 小程序 smoke ✅ |
| **Lane 5** | 发布门禁 | `scripts/`, `docs/release/`, `.github/workflows/` | `commercial-readiness-gate.sh` 全过 ✅ |
| **Lane 6** | UI/UX 优化 | `frontend/`, `docs/design/`, `frontend/src/lib/icons/` | 图标体系 100% ✅ + 假成功 0 ✅ |

详细 Lane 配置见 [docs/release/commercial-delivery-lanes.json](release/commercial-delivery-lanes.json)。

---

## 4. 本轮（2026-05-14）下一批任务

按优先级 + 可执行性排序。每项标注 **OWNER**、**EFFORT**、**DEPENDS_ON**。

### 4.1 立即开始（P0 · 无阻断）

#### 任务 T1：图标体系收口（80 文件迁移）

- **OWNER**：AI agent（可并行）
- **EFFORT**：4 批，每批 ≤ 20 文件，每批 1-2 小时
- **DEPENDS_ON**：无
- **写入范围**：`frontend/src/**/*.tsx` + `frontend/src/lib/icons/index.ts`
- **完成标准**：
  - [ ] 全仓 `grep "from 'lucide-react'" frontend/` 为空
  - [ ] 新增 ESLint 规则 `no-direct-lucide-import`
  - [ ] `npm run lint` 全过
  - [ ] `npm run build` 全过
- **执行顺序**：Pages → Components → 子组件 → 工具

#### 任务 T2：Harness P0 followup A — `policy_engine` 主路径接入

- **OWNER**：AI agent
- **EFFORT**：2-3 小时
- **DEPENDS_ON**：无
- **写入范围**：
  - `backend/src/harness/policy_engine.py`（扩展）
  - `backend/src/agents/base.py`（重构 `_check_mcp_tool_policy`）
  - `backend/tests/test_harness_policy_enforcement.py`（新增 case）
- **完成标准**：
  - [ ] `_check_mcp_tool_policy` 逻辑迁移到 `policy_engine.check_tool_call`
  - [ ] `base.py` 改为薄包装调用 policy_engine
  - [ ] 新增 ≥ 5 个测试用例覆盖策略边界
  - [ ] 全量 `pytest tests/test_harness*` 89 用例继续通过

#### 任务 T3：Harness P0 followup B — `context_engine` vs `context_compressor` 二选一

- **OWNER**：AI agent
- **EFFORT**：3-4 小时
- **DEPENDS_ON**：无
- **写入范围**：
  - 决策记录到 [wiki/06-decision-log.md](wiki/06-decision-log.md)
  - 保留方扩展 + 弃方删除
  - 主路径切到保留方
- **完成标准**：
  - [ ] 决策记录写明 why（覆盖率 / 测试 / 主路径用例对比）
  - [ ] 弃方文件物理删除
  - [ ] 主路径切换无回归

#### 任务 T4：UI/UX P0 — 假成功修复

- **OWNER**：AI agent + 用户审核
- **EFFORT**：8-12 小时
- **DEPENDS_ON**：UI/UX audit 已完成
- **写入范围**：`frontend/src/` 关键流程页面
- **完成标准**：
  - [ ] 所有"提交成功 / 创建成功"toast 必有真实状态 check
  - [ ] 异步任务页面必显示进度（非 spin loader 假装）
  - [ ] 详见 [docs/audit/ui-ux-audit-2026-05-08.md](audit/ui-ux-audit-2026-05-08.md) P0 清单

### 4.2 ✅ 已完成（Phase B + Phase C, 2026-05-14）

#### T5：peaceful-goodall CREAO Slice 1 合并 ✅

- alembic prep + 主体 cherry-pick (1672 行 18 文件)
- commit: `5ace776c` (prep) + `2fa3c039` (主体)

#### T6：cost_tracker 用户配额阻断 ✅

- 本地 LLM `char/4` 估算 + 用户级累计 + `check_user_quota` API + `QuotaExceededError`
- T6 二阶段: chat_service 主路径前置门禁 + admin 双层豁免 (env + features_override)
- commit: `7e581079` + `d190682c`

#### T7：task_engine 扩展（合同 / 尽调 / 批量文档）✅

- contract_service.review_contract / due_diligence_service.investigate_company / batch_document_service.execute_batch 三路径接入状态机
- commit: `ca6e0ebb`

#### T8：capability_negotiator 统一桌面 / 前端 / 服务 ✅

- T8 二阶段: ModeGate 改 useCapabilities hook + featureKey
- A1: 8 调用点实战接入 + 后端补 6 个 user-facing key
- A5: Tauri `negotiate_capabilities` command (云端委托 + 本地兜底)
- commit: `1875e738` + `3eed0283` + `d79a477e`

#### T10：tool_registry 与 Skills 协同 ✅

- T10: SKILL.md `required_tools` 字段 + `validate_required_tools()`
- E5: SkillRegistry.register 运行时 gate auto-disable 缺失依赖
- commit: `13f93532` + `1da62db5`

### 4.3 ✅ Phase C 额外完成的 P1/P2 优化（A1-A10）

| 任务 | commit |
|---|---|
| A1 ModeGate 实战接入 | `3eed0283` |
| A2 vite manualChunks 拆分超大 vendor | `8fd8e6e2` |
| A3 CREAO Slice 2 Triage Service | `084825a9` |
| A4 cost_tracker DB 持久化 + Celery cron | `e299d3ce` |
| A5 Tauri command + AdminIncidents 深化 | `d79a477e` |
| A6 policy REQUIRE_APPROVAL 自动建工单 | `ff5ce9ea` |
| A7 trace `_policy_info` 审计 | `a0f14c41` |
| A8 context_compressor 入 harness 命名空间 | `4761bc63` |
| A9 CREAO Slice 3 Builder | `85802cc4` |
| A10 incidents 二级 burst 限频 | `9f3d2825` |

### 4.4 ✅ Phase D 额外完成的卫生 + 收尾任务（E1-E5 + E2）

| 任务 | commit |
|---|---|
| E1 IncidentCollector 注入 3 个失败信号 hook 主路径 | `3b09ba9c` |
| E2 cost_tracker 每 5min snapshot Celery beat | `5a20f29a` |
| E3 output_validator fail-closed 复核 | `8784c3bc` |
| E4 全量 pytest 卫生 + 3 项 Phase A 归档遗漏修复 | `1a3d71fa` |
| E5 Skill required_tools runtime gate | `1da62db5` |

### 4.5 候补 / 外部资源依赖

| 项 | 阻断 |
|---|---|
| T9 / P13 anxinai.com 域名 | DNS / 证书 |
| 桌面 macOS 签名 | Apple Developer 账号 |
| 桌面 Windows 签名 | 代码签名证书 |
| 支付 / 电签 / OA 真实沙箱 | 渠道方审批 |
| 移动真机 transcript | 测试机房排期 |
| RAG full50 baseline | corpus 准备 |
| P11 多租户 RBAC | 客户进场触发 |
| P12 5 personas × 三端 E2E | B 档全部到位 |

---

## 5. 商业发布冲刺计划（48h 倒排）

当外部资源（Apple Developer / 支付电签 / 真机）就绪时启动。

| 时间窗 | 内容 | 必出 |
|---|---|---|
| **0-6h** | 工作树清点 + 外部资源最终申请 | `release-worktree-inventory.py` PASS |
| **6-18h** | 支付/电签 preflight + 后端回归 | preflight artifacts |
| **18-30h** | 支付/电签 live + 桌面 unsigned/signed build | sandbox transactions |
| **30-42h** | 真机证据采集（iOS + Android）+ 桌面 notarization | device transcripts |
| **42-48h** | 最终门禁 + Go/No-Go 决策 | `commercial-readiness-gate.sh` PASS |

详见 [RELEASE_GATE.md](RELEASE_GATE.md)。

---

## 6. 任务执行规范

### 6.1 每个任务的标准动作

```
1. 读 wiki/03-current-state + 本文相应任务
2. 读相关 standards
3. 写代码（按 standards）
4. 加测试（必须）
5. 自查命令
6. 单一主题 commit
7. push（阶段任务 / 关键任务前后）
8. 完成后更新 wiki/03-current-state + 本文标记
```

### 6.2 commit / push 节奏

- **每个子任务**：1 个 commit
- **每个 T 任务（T1-T10）完成**：commit + push
- **每个 P 级里程碑**：commit + push + 更新 wiki/03 + 更新 ROADMAP

### 6.3 测试节奏

| 修改范围 | 必跑测试 |
|---|---|
| `backend/src/harness/*` 或 `backend/src/agents/*` | `pytest tests/test_harness* tests/test_chat.py` |
| `backend/src/api/routes/*` | 对应路由测试 + integration test |
| `backend/src/services/rag/*` | `pytest tests/test_rag*` + （重要变更）`evals/rag_full50.py` |
| `frontend/src/*` | `npm run lint && npm run build` |
| `desktop/*` | `cargo clippy && cargo test` |
| `mobile/*` | `npm run typecheck && npm run test` |

### 6.4 不可破坏的红线

参见 [wiki/07-common-pitfalls.md](wiki/07-common-pitfalls.md)。重申：
- ❌ 不绕过 `_check_mcp_tool_policy`
- ❌ 不提交密钥
- ❌ 不删 alembic migration 不 merge head
- ❌ 不 force push 共享分支

---

## 附录 · 归档与原文

- **原 docs/audit/summary.md（43 行）**：[docs/archive/legacy-spine-sources/audit/summary.md](archive/legacy-spine-sources/audit/summary.md)
- **原 docs/audit/_tasks/README.md**：[docs/archive/legacy-spine-sources/audit/_tasks-README.md](archive/legacy-spine-sources/audit/_tasks-README.md)
- **原 docs/plans/2026-05-13-ui-ux-optimization-roadmap.md（165 行）**：[docs/archive/legacy-spine-sources/plans/](archive/legacy-spine-sources/plans/)
- **原 docs/release/48-hour-commercial-delivery-plan.md（99 行）**：[docs/archive/legacy-spine-sources/release/](archive/legacy-spine-sources/release/)

---

> **维护提示**：完成的 T 任务移到"已完成"区或归档；新发现的任务追加到对应 Lane；优先级变更同步 [wiki/03-current-state.md](wiki/03-current-state.md)。
