# 项目推进总索引

> 日期：2026-05-12
> 状态：当前权威导航（V3 合并后）
> 用途：作为后续设计、开发、测试、发布、试点和复盘的入口文件。
> 2026-05-12 更新：V3「安心智能助手」scope 已合并进商业交付主线，`docs/v3/` 权威文档已纳入导航。

## 1. 当前权威文件

后续推进项目时，优先依据下列文件，不再以根目录旧版 3-4 月文档作为当前事实来源。

| 用途 | 权威文件 | 作用 |
|---|---|---|
| V3 交付总览 | `docs/v3/V3_DELIVERY_SUMMARY.md` | 一页纸总览：commits 时间线 / 61 个 v3 API endpoint / 10 persona |
| V3 架构 | `docs/v3/ARCHITECTURE.md` | 6 层分层架构 + 模块清单 + 已实现 vs 规划 |
| V3 persona | `docs/v3/AGENT_PERSONAS.md` | 10 persona 定位、API endpoint 与实装状态 |
| V3 能力矩阵 | `docs/v3/CAPABILITY_MATRIX.md` | 4 横 × 4 纵能力矩阵 + 实装状态 |
| V3 路线图 | `docs/v3/ROADMAP.md` | P0-P21 完整路线 + 风险登记册 |
| V3 集成生态 | `docs/v3/INTEGRATIONS.md` | 34+ OAuth provider / IM 适配器 / 数据源清单 |
| V3 Skills 清单 | `docs/v3/SKILLS_INVENTORY.md` | 13 域 76+ skill + 4 office 实装路径 |
| V3 安全审计 | `docs/v3/SECURITY_AUDIT.md` | P15 OWASP Top 10 / 依赖 / 密钥 / 高风险点 |
| V3 可观测性 | `docs/v3/OBSERVABILITY_BACKEND.md`、`OBSERVABILITY_FRONTEND.md`、`OBSERVABILITY_DEPLOY.md` | Sentry + Prometheus + Grafana 三端 |
| V3 CI 流水线 | `docs/v3/CI_PIPELINE.md` | 5 端 GHA workflow + nightly smoke + bundle size guard |
| 产品定位 | `docs/strategy/product-architecture-and-requirements-2026-05-08.md` | 中小企业经营风险平台、全设备智能助手、企业智能体治理的统一定位 |
| 上层产品合同 | `docs/openspec/00-intelligent-assistant-platform-spec.md` | 桌面主工作站、移动远控、本地模型、独立知识库、Skills/MCP、可信会话和智能体进化 |
| 商业交付规范 | `docs/openspec/01-commercial-delivery-spec.md` | 商业候选版定义、阶段目标、统一开发规则和交付物 |
| 测试规范 | `docs/openspec/02-commercial-delivery-test-spec.md` | 每个任务、端侧和发布前的必跑测试矩阵 |
| 真实状态审计 | `docs/audit/summary.md` | 当前完成、阻断、风险和下一步顺序 |
| UI/UX 审计 | `docs/audit/ui-ux-audit-2026-05-08.md` | 移动端、小程序、桌面端问题清单和优化方案 |
| 外部项目借鉴 | `docs/references/agentic-platform-benchmark-2026-05-08.md` | Hermes/OpenClaw/HiClaw/DeepTutor/CLI-Anything/RAG-Anything/browser-use/Scrapling、Codex/Claude 体验原则 |
| 任务拆分 | `docs/audit/_tasks/README.md` | TASK-01..12 并行开发任务索引 |
| 发布就绪 | `docs/release/commercial-delivery-readiness.md` | Go/No-Go 判定和商业证据缺口 |
| 发布清单 | `docs/release/commercial-delivery-checklist.json` | prompt-to-artifact 成功标准 |
| 并行 lane | `docs/release/commercial-delivery-lanes.json` | 多智能体/多人并行执行的写入范围和 completion gate |
| 测试证据 | `docs/release/test-evidence.md` | 已有测试、未补证据和新增测试要求 |
| 安全隐私 | `docs/release/security-and-privacy-checklist.md` | 发布前安全、隐私、密钥、权限、智能体治理清单 |
| 归档说明 | `docs/archive/README.md` | 已归档历史文档列表和使用边界 |

## 2. 后续 12 个推进环节

| 环节 | 目标 | 输入文件 | 输出/门禁 |
|---|---|---|---|
| 1. 目标与定位 | 冻结用户、场景、商业目标和高可信试点边界 | `strategy/product-architecture-and-requirements-2026-05-08.md`、`openspec/00-intelligent-assistant-platform-spec.md` | 目标变更必须同步 OpenSpec |
| 2. 需求规范 | 把需求拆成可验收条款 | `openspec/01-commercial-delivery-spec.md`、`openspec/02-commercial-delivery-test-spec.md` | 每项需求有测试或证据入口 |
| 4. UI/UX 设计与优化 ⭐**前置门槛** | 统一移动端、小程序、桌面和 Web 工作台体验，**P9-P13 启动前必须完成** | `plans/2026-05-13-ui-ux-optimization-roadmap.md`（执行）、`audit/ui-ux-audit-2026-05-08.md`（差异）、`design/cross-platform-token-drift.md`、`standards/frontend-standard.md` | 分端优化方案、截图/真机 transcript |
| 5. 架构与安全 | 确认权限、密钥、本地模式、同步、知识库和治理边界 | `release/security-and-privacy-checklist.md`、`architecture-v2.md`、`architecture/*` | 安全审查、迁移方案、回滚方案 |
| 6. 任务拆分 | 把实施拆成可并行 lane | `audit/_tasks/README.md`、`release/commercial-delivery-lanes.json` | 每个 lane 有 write_scope、测试和 completion_gate |
| 7. 开发实施 | 按任务文档小步开发 | `audit/_tasks/TASK-*.md` | 代码、迁移、前端页面、桌面/移动实现 |
| 8. 单元与集成测试 | 先用代码级测试锁行为 | `openspec/02-commercial-delivery-test-spec.md`、`release/test-evidence.md` | pytest、Vitest、Playwright、cargo、mobile/mini smoke |
| 9. UI/UX 验收 | 证明体验不是粗糙入口或假成功 | `audit/ui-ux-audit-2026-05-08.md` | iOS/Android/WeChat/desktop 截图或 transcript |
| 10. 发布证据 | 采集真实沙箱、签名包、真机、RAG、静态质量证据 | `release/evidence-collection-runbook.md`、`release/external-inputs-checklist.md` | evidence `Status: complete` 或明确 blocker |
| 11. 商业门禁 | 统一判断能不能 Go | `release/commercial-delivery-readiness.md`、`scripts/commercial-readiness-gate.sh` | quick/with-local-tests gate 通过或保留 No-Go |
| 12. 试点与进化 | 政府/中小企业试点、Skills 进化、智能体治理复盘 | `references/agentic-platform-benchmark-2026-05-08.md`、`task-12-agent-control-plane-skill-evolution.md` | Skill eval gate、审批、回滚、试点问题清单 |

## 3. UI/UX 审计结论

已经完成 UI/UX 审计，并形成下一步优化方案：

- 主文件：`docs/audit/ui-ux-audit-2026-05-08.md`
- 覆盖端侧：移动端、微信小程序、桌面端、跨端设计 token、错误态、触控尺寸、桌面冲突管理、政府/高可信试点门槛。
- 下一步方向：先修 P0 假成功和关键入口，再做跨端 token、移动硬编码颜色、小程序暗色策略、桌面冲突 UX、可信会话时间线和 artifact-first 工作台。

## 4. 命名与归档规则

- 当前权威规范使用 `docs/openspec/00-*`、`01-*`、`02-*` 编号。
- 当前产品策略放在 `docs/strategy/`。
- 外部参考放在 `docs/references/`，历史 README/ROADMAP 类参考留在 `docs/references/legacy/`。
- 过时的根目录日期文档统一归档到 `docs/archive/legacy-root-docs/`。
- 归档文档只用于追溯历史决策，不作为当前开发、测试、发布的放行依据。

## 5. 每轮开工前检查

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
