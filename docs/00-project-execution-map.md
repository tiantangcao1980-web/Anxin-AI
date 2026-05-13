# 项目推进总索引

> 日期：2026-05-14
> 状态：当前权威导航（Spine + Wiki 双层文档体系基线）
> 用途：作为后续设计、开发、测试、发布、试点和复盘的入口文件。
>
> 2026-05-14 重大更新：完成文档单一信源化 — 5 份 Spine 替代 170+ 历史源文档，同步上线 LLM Wiki 供 AI 智能体接手。

---

## 1. 当前权威结构 — 一图看清

```
                ┌─────────────────────────────────┐
                │   人类协作主干（Spine, docs/*.md）  │
                │   长文 / 权威 / 一锤定音           │
                └─────────────────────────────────┘
                  │       │       │       │       │
                  ▼       ▼       ▼       ▼       ▼
              REQUIREMENTS ARCH  ROADMAP DEV_PLAN RELEASE_GATE
                  │       │       │       │       │
                  └───────┴───┬───┴───────┴───────┘
                              │
                ┌─────────────▼─────────────────┐
                │   AI 接手副本（Wiki, docs/wiki/）  │
                │   高密度 / 30 秒上手 / 高频更新     │
                └───────────────────────────────┘

                ┌───────────────────────────────┐
                │  Agent 行为单一真相源 (AGENTS.md) │
                │  视觉设计单一真相源 (DESIGN.md)    │
                │  工程规范 (docs/standards/)       │
                └───────────────────────────────┘
```

---

## 2. 五大 Spine（人类协作主干）

| 文档 | 用途 | 仲裁优先级 |
|------|------|----:|
| [`REQUIREMENTS.md`](REQUIREMENTS.md) | 需求 / 商业定义 / 红线 / NOT-doing 清单 | 1（最高） |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | 系统架构 / 6 层模型 / 多平台 / 三态运行 / 关键流程 | 2 |
| [`ROADMAP.md`](ROADMAP.md) | 历史 + P0–P21 + 里程碑 + 风险登记册 | 3 |
| [`DEVELOPMENT_PLAN.md`](DEVELOPMENT_PLAN.md) | 当前批次 T1–T10 + 6 lane 并行 + 48h 冲刺 + 执行规范 | 4 |
| [`RELEASE_GATE.md`](RELEASE_GATE.md) | 5 维评测 / lane 测试 / 门禁命令 / 证据清单 / Go-NoGo | 5 |

**冲突仲裁规则**：REQUIREMENTS > ARCHITECTURE > ROADMAP > DEVELOPMENT_PLAN > RELEASE_GATE。当 Spine 与归档文档冲突时一律以 Spine 为准。

---

## 3. LLM Wiki（AI 智能体 30 秒接手入口）

放在 [`docs/wiki/`](wiki/)，共 9 份高密度文件，单文件 ≤ 250 行：

| 编号 | 文件 | 用途 |
|------|------|------|
| 00 | [`README.md`](wiki/README.md) | Wiki 入口 + 30 秒项目识别表 |
| 01 | [`01-project-snapshot.md`](wiki/01-project-snapshot.md) | 一页快照：What / Who / Why / How |
| 02 | [`02-quick-context.md`](wiki/02-quick-context.md) | 工作目录树 / 核心概念 / 常用命令 / API 入口表 |
| 03 | [`03-current-state.md`](wiki/03-current-state.md) | 当前状态 / P0/P1/P2 优先级（最高频更新） |
| 04 | [`04-architecture-map.md`](wiki/04-architecture-map.md) | 6 层架构 ASCII / 多平台 / 三态 / 关键流程时序 |
| 05 | [`05-domain-glossary.md`](wiki/05-domain-glossary.md) | 业务术语 / Persona 表 / 命名规范 |
| 06 | [`06-decision-log.md`](wiki/06-decision-log.md) | 倒序架构决策 What / Why / Trade-off / Status |
| 07 | [`07-common-pitfalls.md`](wiki/07-common-pitfalls.md) | "不要做 X" 分域清单 |
| 08 | [`08-ai-onboarding-flow.md`](wiki/08-ai-onboarding-flow.md) | 5 步接手流 + 场景剧本 |

---

## 4. 三大单一真相源（与 Spine 并列，不可降级）

| 真相源 | 路径 | 范畴 |
|------|------|------|
| **Agent 行为** | [`AGENTS.md`](../AGENTS.md) | 22 智能体红线 / 路由 / 反 slop / 协作约定 |
| **视觉设计** | [`DESIGN.md`](../DESIGN.md) | Design token / Icon / 配色 / 排版 |
| **工程规范** | [`standards/`](standards/) | 13 份规范：命名 / 文档 / Git / 代码 / API / DB / 前/后端 / 测试 / 安全 / 注释 / Review |

---

## 5. 仍然活跃的领域文档（未归档）

| 路径 | 用途 |
|------|------|
| [`adr/`](adr/) | 架构决策记录（v3 升级 / Harness / 双客户端） |
| [`audit/harness/`](audit/harness/) | 六层框架（Model/Harness/Context/Traces/Eval/Ops）持续审计 |
| [`audit/ui-ux-audit-2026-05-08.md`](audit/ui-ux-audit-2026-05-08.md) | UI/UX 审计差异清单（P9-P13 前置门槛） |
| [`design/`](design/) | 跨端 token drift 等设计专题 |
| [`desktop/`](desktop/) | 桌面工作站设计 / 远控 / 同步 |
| [`mobile/`](mobile/) | 移动端配对授权 / 错误态 / 推送 |
| [`v3/`](v3/) | 运维参考（observability / CI / health / integrations / capability-matrix / skills-inventory / agent-personas / p8 / p16 / security-audit） |
| [`release/`](release/) | 证据物料 / runbook / external-* / checklist JSON |
| [`references/`](references/) | 外部对标 / 行业基准 |
| [`context-architecture.md`](context-architecture.md) | Context 三层（AGENTS.md / skills/ / memory）加载顺序 |
| [`issues/`](issues/) | 历史 issue 截图 |
| [`RESOURCES.md`](RESOURCES.md) | 当前 icon / 排版 / 字体栈配置 |

---

## 6. 历史源文档归档（仅供溯源）

- [`archive/legacy-spine-sources/`](archive/legacy-spine-sources/) — 101 份被 5 份 Spine 取代的源文档（openspec / strategy / v3 已替代部分 / architecture-v2 / audit 模块 / plans / release 已替代部分）
- [`archive/legacy-root-roadmaps/`](archive/legacy-root-roadmaps/) — 根目录旧 ROADMAP / PRODUCT_ROADMAP
- [`archive/legacy-root-docs/`](archive/legacy-root-docs/) — 早期"AI法务智能体系统"年代根目录文档
- [`references/legacy/`](references/legacy/) — 历史 README / DEPLOY / ROADMAP 参考

> ⚠️ 归档文档只能用于追溯历史决策，**不作为当前开发、测试、发布的依据**。

---

## 7. 后续 11 个推进环节

| 环节 | 目标 | 主输入 | 输出 / 门禁 |
|---|---|---|---|
| 1. 目标与定位 | 冻结用户、场景、商业目标 | [`REQUIREMENTS.md §1-2`](REQUIREMENTS.md) | 目标变更必须更新 REQUIREMENTS Spine |
| 2. 需求规范 | 把需求拆成可验收条款 | [`REQUIREMENTS.md §3 能力合同`](REQUIREMENTS.md) | 每项需求有 RELEASE_GATE 对应测试入口 |
| 3. UI/UX 优化 ⭐**P9-P13 前置门槛** | 移动 / 小程序 / 桌面 / Web 统一体验 | [`audit/ui-ux-audit-2026-05-08.md`](audit/ui-ux-audit-2026-05-08.md) + [`design/cross-platform-token-drift.md`](design/cross-platform-token-drift.md) | 分端方案 + 截图 / 真机 transcript |
| 4. 架构与安全 | 权限 / 密钥 / 三态 / 同步 / 治理边界 | [`ARCHITECTURE.md §4 三态`](ARCHITECTURE.md) + [`release/security-and-privacy-checklist.md`](release/security-and-privacy-checklist.md) | 安全审查 + 迁移 + 回滚预案 |
| 5. 任务拆分 | 实施拆成并行 lane | [`DEVELOPMENT_PLAN.md §3 6 lane`](DEVELOPMENT_PLAN.md) + [`release/commercial-delivery-lanes.json`](release/commercial-delivery-lanes.json) | 每 lane 有 write_scope / 测试 / completion_gate |
| 6. 开发实施 | 小步开发 + 频繁推送 | [`DEVELOPMENT_PLAN.md §4 当前批次`](DEVELOPMENT_PLAN.md) | 代码 / 迁移 / 前端页面 / 桌面 / 移动实现 |
| 7. 单元与集成测试 | 用代码级测试锁行为 | [`RELEASE_GATE.md §2 lane`](RELEASE_GATE.md) + [`release/test-evidence.md`](release/test-evidence.md) | pytest / Vitest / Playwright / cargo / mini smoke |
| 8. UI/UX 验收 | 证明体验不是粗糙入口或假成功 | [`audit/ui-ux-audit-2026-05-08.md`](audit/ui-ux-audit-2026-05-08.md) | iOS / Android / WeChat / desktop 截图或 transcript |
| 9. 发布证据 | 采集沙箱 / 签名包 / 真机 / RAG / 静态质量证据 | [`release/evidence-collection-runbook.md`](release/evidence-collection-runbook.md) + [`release/external-inputs-checklist.md`](release/external-inputs-checklist.md) | evidence `Status: complete` 或明确 blocker |
| 10. 商业门禁 | 统一判断 Go / No-Go | [`RELEASE_GATE.md §4 命令`](RELEASE_GATE.md) + [`scripts/commercial-readiness-gate.sh`](../scripts/commercial-readiness-gate.sh) | quick / with-local-tests gate 通过或 No-Go |
| 11. 试点与进化 | 政府 / 中小企业试点 + Skills 进化 + 治理复盘 | [`references/agentic-platform-benchmark-2026-05-08.md`](references/agentic-platform-benchmark-2026-05-08.md) | Skill eval gate / 审批 / 回滚 / 试点问题清单 |

---

## 8. 每轮开工前检查

```bash
python3 scripts/release-worktree-inventory.py --json --fail-on-unknown
git diff --check
node scripts/validate-commercial-delivery-checklist.cjs
node scripts/validate-commercial-delivery-lanes.cjs
bash scripts/release-evidence-secret-scan.sh
```

商业发布前再运行：

```bash
bash scripts/commercial-readiness-gate.sh --quick
```

---

## 9. AI 智能体接手项目的推荐路径

> 从零到能修复一个 P0 问题，**预计 15 分钟**。详细流程见 [`wiki/08-ai-onboarding-flow.md`](wiki/08-ai-onboarding-flow.md)。

```
1. 读 wiki/01-project-snapshot.md     （30 秒识别项目）
2. 读 wiki/03-current-state.md         （知道现在做什么、还差什么）
3. 读 wiki/07-common-pitfalls.md       （知道不要踩什么坑）
4. 按需查 wiki/02 / 04 / 05 / 06        （命令 / 架构 / 术语 / 决策）
5. 修改前查 standards/ 对应规范 + AGENTS.md
6. 提交按 commit-convention，PR 按 review-checklist
```

---

## 10. 命名与归档规则

- **5 Spine** 永远在 `docs/` 根目录，文件名全大写 + 下划线（REQUIREMENTS / ARCHITECTURE / ROADMAP / DEVELOPMENT_PLAN / RELEASE_GATE）。
- **Wiki** 全部在 `docs/wiki/`，文件名 `NN-kebab-case.md`，编号 00-09 预留扩展。
- **领域文档** 在 `docs/<领域>/`（adr / audit / design / desktop / mobile / v3 / release / references / standards / wiki）。
- **归档** 在 `docs/archive/<归档批次>/`，每批次有 README 标明源文档与新 Spine 的映射。
- **新增重大文档时必须同步更新本 00-project-execution-map.md 与 wiki/03-current-state.md**。
