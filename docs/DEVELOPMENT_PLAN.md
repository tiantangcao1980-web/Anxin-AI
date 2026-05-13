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
| **发布证据** | 🚧 50%（5 类已采，3 类缺） | 支付/电签/真机 live |

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
🚧 支付 / 电签 live 沙箱（阻断）
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

#### P8.D 支付 / 电签真实沙箱

| 子任务 | 状态 | 阻断 |
|---|---|---|
| 支付沙箱凭证 | 🚫 | 渠道方审批 |
| 电签沙箱凭证 | 🚫 | 渠道方审批 |
| preflight 命令集 | ✅ | [release/evidence-collection-runbook](release/evidence-collection-runbook.md) |
| live 证据采集 | 🚫 | 等凭证 |

### 2.2 P9 — 5 法务 persona 上层包装

依赖：P8 体验门槛通过。

| 子任务 | 文件 | 状态 |
|---|---|---|
| 法律顾问 persona 上层接口 | `backend/src/agents/personas/legal_advisor.py` | 🔜 |
| 合同管家 persona 上层接口 | `backend/src/agents/personas/contract_steward.py` | 🔜 |
| 尽调专家 persona | `backend/src/agents/personas/due_diligence_expert.py` | 🔜 |
| 财税顾问 persona | `backend/src/agents/personas/tax_finance_advisor.py` | 🔜 |
| 5 法务 persona eval baseline | `backend/evals/legal/` | 🔜 |

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
| **Lane 1** | 支付 / 电签 | `backend/src/services/payment/`, `backend/src/services/esign/` | 真实沙箱 live 证据 ✅ |
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

### 4.2 排队中（P1 · 等条件）

#### 任务 T5：peaceful-goodall CREAO Slice 1 合并

- **DEPENDS_ON**：T2 完成（policy_engine 收敛后）
- **EFFORT**：4-6 小时（含 alembic head 合并）
- **写入范围**：18 文件 / 1666 行

#### 任务 T6：cost_tracker 用户配额阻断

- **DEPENDS_ON**：无（独立模块）
- **EFFORT**：6-8 小时

#### 任务 T7：task_engine 扩展（合同 / 尽调 / 批量文档）

- **DEPENDS_ON**：T2 完成
- **EFFORT**：1-2 天

### 4.3 候补（P2 · 长期）

- 任务 T8：capability_negotiator 统一桌面 / 前端 / 服务
- 任务 T9：anxinai.com 域名切换（P13）
- 任务 T10：tool_registry 与 Skills 协同改造

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
