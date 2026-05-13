# 安心智能助手 — 项目开发与优化计划书（修订版）

> 版本：v2.0（2026-05-04）
> 制定基础：基于本人对 18 处具体代码点位的逐一核查 + PROJECT_STATUS / PRODUCT_ROADMAP / DESIGN.md 的对齐
> 上一版基础：用户初版 11 任务并行计划（已识别出 4 处偏差，本版修订）
> 适用范围：本计划仅约束本次审计 + 优化 + 桌面/移动端 MVP 推进；不替代 ROADMAP.md 的产品规划

---

## 0. 一句话定位

把项目从**"v0.9.x 内测版 + V2 架构骨架"**推到**"V2 内测可用 → V2 商业化首版"**两个里程碑，分别对应 P0 钉子收口、P1 生产闭环。

**当前不应对外宣称 "V2 生产就绪"**。这是本计划书的执行起点，不是结论。

### 0.1 2026-05-09 持久目标修订

- 新的 goal contract 见 `docs/release/goal-contract-commercial-readiness.md`。
- 执行顺序调整为：**桌面端本地可执行功能和治理门禁优先**，移动 App/小程序随后按 uni-app 统一端迁移推进。
- 外部 API、签名和真机资源不阻塞本地功能开发：先用 provider contract、fixture、sandbox runner 和脱敏 artifact 验证函数级/流程级能力；真实密钥、证书和设备由用户后续提供后再完成联调与 release evidence。
- UI/UX 顺序为功能先闭环、再商业级打磨；任何假成功、静默 fallback 或把未完成外部证据渲染为完成态都阻断上线。

---

## 1. 项目实情（决定优先级的真相）

### 1.1 PROJECT_STATUS 自身是诚实的

`PROJECT_STATUS.md` 第 70-188 行已明确列出"当前仍待处理的高风险问题"+"边界与设计遗留"。读这份文档不会被骗。

### 1.2 但"Phase 1-5 已完成"和"代码现实"之间存在结构性偏差

| Phase 1-5 承诺 | 代码现实 | 严重程度 |
|---|---|---|
| 双客户端分离（`/pro` 服务方端独立路由） | ✅ Web `/pro` provider 守卫与 ProLayout `/pro/*` 导航已收口；仍需补充 Pro 端完整 E2E 覆盖 | 🟠 P1（剩测试面） |
| 三态运行 + 订阅商业化 | ✅ Web ModeGate 直接切换、PrivacyContext fail-open 与直连 fetch privacy header 已收口；仍需移动端/桌面端模式语义复核 | 🟠 P1（剩跨端面） |
| S-104 LLM 配置组织隔离已修复 | ✅ `LLMService.list_configs` 组织隔离已 fail-closed，并有回归测试 | 🟢 已收口 |
| 文档管理（上传/版本/协作） | ✅/⏳ 对象存储底座已接：`object_storage_service.py` + `029_document_object_storage` + 文档上传/删除/版本更新/合同保存真实写入；剩余 MinIO 凭据轮换、历史 backfill、IM/尽调/案件/模板/A2UI 附件入口切换 | 🟠 P1（剩扩展面） |
| 桌面端"绝密本地"模式 + 同步引擎 | 后端 `/api/v1/sync/*` 已有 `SyncLog` 持久化增量日志；Rust IPC 直连同步已补代码级 SQLCipher push/pull fallback，TopSecret/未登录仍 fail-closed，不再伪造 `Ok(0)`；packaged runtime push/pull/conflict/retry、跨设备延续和 signed packaged runtime 证据仍未闭合 | 🟠 P1 |
| 支付 / 电签 webhook 升级到 HMAC | ✅ 支付/电签通用 HMAC 路径已分别回写订单/订阅、合同签署状态；`webhook_received` 持久化幂等表、Admin `/admin/webhooks` 查询/手动重试入口、Prometheus webhook 指标、电签 flow 映射、失败 webhook 自动重试/backoff、统一 `webhook_handler.py`、稳定 `PaymentWebhookEvent` / `ESignWebhookEvent`、微信支付 v3/支付宝 RSA2 回调验签、微信/支付宝下单查询退款关单请求与同步响应验签、e签宝 provider/官方 HMAC 回调、法大大 FASC provider/webhook 代码级协议已落；仍缺真实商户沙箱闭环、账号事件映射与灰度证据 | 🔴 P0（真实渠道仍阻断） |

**结论**：PROJECT_STATUS 不是不可信，而是"标完成"和"商业化可上线"之间还差一层。本计划书的目标就是把这层缺口补上。

### 1.3 已就绪的真实基线（不要重做）

- 后端默认测试当前最新 `467 passed, 1 skipped, 17 warnings in 36.11s`（Codex 实测；PROJECT_STATUS 写的 172 passed 是较早数字，不必纠结；`test_comprehensive_flow` 已改为 opt-in smoke）
- 前端 lint + 最新完整本地门禁 Vitest `12 files / 45 tests passed` + build 通过；角色访问 e2e `10 passed / 10 skipped`
- 移动/小程序本地门禁通过：移动 Vitest 8 files / 37 tests passed，移动 tsc、mobile result surface guard、mobile lawyer conversion guard、Expo doctor 17/17、mobile production npm audit 0、小程序 tsc/build、mini-program privacy boundary guard、mini-program navigation boundary guard、WeChat DevTools CLI project smoke、refresh auth guard、mobile/mini privacy network guard、fake fallback guard 和 mini-program design token guard 均通过；2026-05-09 已用定向 overrides 清掉 `@babel/plugin-transform-modules-systemjs` 与 `fast-uri` 新增审计项
- 桌面端 cargo check 通过
- 设计系统 A(95+/100)，硬编码颜色/padding/tracking 已清零

### 1.4 已知非阻断问题

- 后端 Ruff 与 mypy 已清零 —— 后续保持 zero-baseline，任何非零结果都阻断 release readiness
- 前端 build 有 lottie-web `eval` 警告 + 大 chunk + 动态/静态导入混用 —— 优化期处理
- 中文环境 + UTF-8 编码、Git 提交信息中英文混排 —— 已是项目现状，不变

---

## 2. 双轨工作法（每个任务都按这个走）

```
Track A · 功能完备性
  A1  从 PRD/PROJECT_STATUS/DESIGN.md 抽出本模块"承诺清单"
  A2  与代码实现做三角对齐（路由 / 服务 / 前端 / 测试）
  A3  跑端到端用户故事（pytest + playwright）
  A4  功能缺口 → 修复 / 补开发；写"验收门槛"清单

Track B · 质量四件套
  B1  代码质量   — code-review + simplify + coding-standards
  B2  性能       — 关键路径基准 + N+1/索引/缓存/流式
  B3  安全       — security-review，对齐 PROJECT_STATUS 钉子
  B4  稳定性     — 错误边界、超时/重试/幂等、降级、可观测
```

### 强制 Step 0（每个任务都必须有）

**PRD vs 代码真实性差分** —— 每个任务开始前先输出 `00-prd-reality-gap.md`，把 PROJECT_STATUS 标"已完成"但代码里是 TODO/绕过/退化的项列出来。否则审计在过期地图上找路。

### Skills 编排顺序

```
1. /hierarchical-memory find-feature / find-bugfix
2. /iterative-retrieval 按"路由 → 服务 → 模型 → 前端 → 测试"分层读
3. /code-review + 领域 skill（/backend-patterns / /frontend-patterns / /api-design / /database-patterns）
4. /security-review（对照 PROJECT_STATUS 的 10 个钉子）
5. /verification-loop（pytest + tsc + lint + build）
6. /tdd-workflow 补单测；/e2e-testing 补 Playwright
7. /designdna（仅前端模块）— 用 DESIGN.md 做合规校验，不重设计
8. /simplify 收尾；/hierarchical-memory add-feature/add-bugfix 沉淀
```

### 输出物（每个任务统一目录）

```
docs/audit/<NN-module>/
  ├─ 00-prd-reality-gap.md     PRD 承诺 vs 代码现实差分
  ├─ 01-prd-coverage.md        Track A 三角对齐
  ├─ 02-issues.md              P0/P1/P2 问题清单（功能 + 质量四件套合并）
  ├─ 03-fixes.md               本轮修复变更说明
  ├─ 04-test-additions.md      补的测试 + 覆盖率前后对比
  └─ 05-followups.md           遗留 → 沉淀到 hierarchical-memory
```

---

## 3. 全局护栏（任何任务都不得逾越）

| 类别 | 必须停下来等用户决策 |
|---|---|
| 密钥 | 不动 secret；不 git filter-repo；不 force push；只产出 SOP 等用户执行 |
| 商业化 | 任何改 payment_service / billing / subscription 的代码 PR 提交前必须用户先看 |
| webhook | 不允许 big-bang 切换；必须给灰度方案，且分渠道一个一个来 |
| Prompts | `backend/src/prompts/` 任一文件改动前必须 diff 给用户 |
| 桌面签名 | dmg 公证 / msi 签名 / 自动更新通道任何动作必须用户执行 |
| 设计系统 | `frontend/src/lib/design-tokens.ts` 不得在没有用户同意下修改 |
| 数据库 | 改 schema 必须给 alembic 迁移 + 回滚脚本；不动生产数据 |
| Git | 不 push、不 force push、不 amend 已发布 commit |

每个任务的提示词最后都会重复提醒该任务相关的护栏。

---

## 4. 任务列表（12 组任务，按波次执行）

### 波次 0：阻塞（独占）

| # | 任务 | 必须命中 | 工时 |
|---|---|---|---|
| 0 | 全局基础设施（Secret/CI/Docker/Migration） | #1 .env 泄露 + Git 历史治理 + 镜像加固 + CI 安全扫描 | 1 天（纯文档+SOP） |

### 波次 1：阻塞型核心（任务 0 完成后并行）

| # | 任务 | 必须命中 |
|---|---|---|
| 1 | 认证 + 权限 + CAPTCHA | #2 6 位重置码、#3 token 存储、#4 Redis fail-closed、#10 CAPTCHA 全覆盖 |
| 2 | 三态运行 / 私有 LLM / Compute Router + V2 路由真分离 | #6 LLM org 隔离（路由+服务层都修）、ModeGate 绕过、PrivacyContext 失败兜底、`/pro` 守卫 + ProLayout 导航迁到 `/pro/*` |

### 波次 2：核心业务（波次 1 通过后并行）

| # | 任务 | 必须命中 |
|---|---|---|
| 3 | AI 智能体 + 对话 + Prompt | 协调器路由准确率、prompt 注入防护、流式断线 |
| 4 | A2UI 协议 + 工作台 | action 越权、未知事件降级、协议版本兼容 |
| 5 | 合同全生命周期 + 电子签 | #5 webhook 切官方协议（电签部分）+ webhook 业务回写 |
| 6 | 文档 + 协作编辑 + 模板 | 模板注入、CRDT 合并、上传校验统一、对象存储真实接入（依赖任务 0）|
| 7 | RAG / 知识库 / 图谱 | 召回质量、引用回链、检索接口 PII 脱敏 |

### 波次 3：业务深度（波次 2 通过后并行）

| # | 任务 | 必须命中 |
|---|---|---|
| 8a | 案件 + 任务 | 案件状态机、任务 owner 收口 |
| 8b | 找律师 + 案源市场 + 律所端 | 利益冲突、撮合公平、律所 RBAC |
| 9 | 合规 / 风险 / 尽调 / 舆情 / 资讯 | 抓取合规、调查路由命中率、#7 匿名聊天双 token、尽调缓存 org 维度 |
| 10 | 订阅 + 计费 + 支付 + IM/RTC + 通知 | #5 支付 webhook 切官方协议+业务回写、#8 IM URL token、退款幂等、订阅状态机 |

### 波次 4：多端

| # | 任务 | 必须命中 |
|---|---|---|
| 11a | 桌面端 P0-1/P0-2/P0-3 三件套 | 自定义标题栏 / 全局快捷键快速问答 / 拖拽分析 |
| 11b | 同步引擎（后端底座 + 前端 Tauri SQL 最小 push/pull + 冲突合并页 + 代码级指数重试已补） | Tauri runtime smoke、加密、性能基线 |
| 11c | 移动端 + 小程序 uni-app 统一端迁移 + 设计系统跨平台校验 | uni-app 基座、旧 Expo/Taro legacy 清理、底部 Tab / 44px / safe-area / DesignDNA 一致性 |

### 波次 5：企业智能体治理

| # | 任务 | 必须命中 |
|---|---|---|
| 12 | 企业智能体工作台与治理引擎 | 订阅/角色/权限/风险/隐私/设备/通信策略/审批统一决策；Agent/Worker 不持真实密钥；高风险动作可旁听、暂停、接管、终止 |

> **关键修订**：原计划任务 8 把 5 模块打包，工时不平衡；任务 11 把"桌面 MVP + 同步 + 移动"打包，但同步是从零写。修订后任务 8 拆为 8a/8b，任务 11 拆为 11a/11b/11c。

---

## 5. 时间线（双轨制，纯估算，按"每天 1 名工程师投入" 计）

```
Day 0       任务 0          基础设施盘点 + SOP（用户审）
Day 1       用户执行密钥轮换 + Git 历史清理（按 SOP）
Day 2-3     波次 1 并行：任务 1 + 任务 2
Day 4-9     波次 2 并行：任务 3 / 4 / 5 / 6 / 7（5 个 worktree）
Day 10-13   波次 3 并行：任务 8a / 8b / 9 / 10
Day 14-20   波次 4：任务 11a + 11b + 11c
Day 21-28   波次 5：任务 12 企业智能体治理与能力中心
Day 29      汇总：合并 docs/audit/* → docs/audit/summary.md
                  对外发布"V2 内测可用"声明
Day 30-36   缓冲 + P2 质量基线（ruff/mypy 分层基线 + 性能调优）
```

**里程碑**：
- **M-A（Day 1 末）** —— 密钥治理收尾，所有泄露凭据失效
- **M-B（Day 9 末）** —— P0 全部钉子收口，"V2 内测可用"
- **M-C（Day 20 末）** —— 桌面 MVP + P1 生产闭环，"V2 商业化首版候选"
- **M-D（Day 28 末）** —— 企业智能体治理 P0 闭环，具备组织级能力中心和高风险控制面
- **M-E（Day 36 末）** —— 质量基线 + 性能调优收尾，"V2 商业化首版"

---

## 6. 任务索引（独立提示词文件）

每个任务一份独立 `_tasks/TASK-NN-*.md`，可直接复制到新会话执行（每个会话建议 `git worktree add`）。

| # | 文件 | 状态 |
|---|---|---|
| 0 | `_tasks/task-00-platform.md` | 待生成 |
| 1 | `_tasks/task-01-auth.md` | 已生成，部分执行 |
| 2 | `_tasks/task-02-mode-llm.md` | 已生成，核心守卫已执行 |
| 3 | `_tasks/task-03-agents.md` | 已生成 |
| 4 | `_tasks/task-04-a2ui.md` | 已生成，协议/WS 鉴权部分已执行 |
| 5 | `_tasks/task-05-contract.md` | 已生成 |
| 6 | `_tasks/task-06-document.md` | 已生成 |
| 7 | `_tasks/task-07-rag.md` | 已生成 |
| 8a | `_tasks/task-08a-case-task.md` | 已生成，案件状态机/终态只读/任务 owner 核心收口已执行；全矩阵与 Playwright 全流程仍待发布前扩展 |
| 8b | `_tasks/task-08b-lawyer-market.md` | 已生成，local 模式拒绝/利益冲突阻断/同分曝光轮询已执行；律所 RBAC 全矩阵与案源 8 API 打勾仍待扩展 |
| 9 | `_tasks/task-09-risk-investigation.md` | 已生成，匿名聊天/尽调守卫/尽调缓存 org 隔离/风险评分解释性/爬虫合规入口/意图路由评测已执行；预发网络真实 dry-run 仍是发布证据 |
| 10 | `_tasks/task-10-billing-im.md` | 已生成 |
| 11a | `_tasks/task-11a-desktop-mvp.md` | 已生成 |
| 11b | `_tasks/task-11b-sync-engine.md` | 已生成 |
| 11c | `_tasks/task-11c-mobile-design.md` | 已生成；2026-05-09 已同步 uni-app 统一端路线，旧 `mobile/` 和 `mini-program/` 标记 legacy；`apps/uni-mobile/` 首版基座已通过 typecheck、12 个契约测试、production audit、H5 和微信小程序构建；旧端模块删除待同等能力和真机/DevTools 证据 |
| 12 | `_tasks/task-12-agent-control-plane-skill-evolution.md` | 已生成，等待执行 |

---

## 7. 风险与对齐（开工前需用户确认）

### 7.1 必须用户确认才能开工的事

- [ ] **密钥治理**：`.env` 泄露历史范围（多少个 commit、多久前提交、是否已被 fork/clone）
- [ ] **生产影响面**：当前是否有真实付费用户、订阅账号？修复 token 存储要不要让所有用户重新登录
- [ ] **灰度策略**：webhook 切官方协议的渠道顺序（建议先支付宝沙箱 → 微信沙箱 → 电签沙箱 → 灰度生产）
- [ ] **桌面端目标用户**：当前 50 个种子用户灰度有没有启动？
- [ ] **资源投入**：是单人执行（按本计划 30 天）还是多人并行（可压缩到 10-15 天）

### 7.2 计划本身的不确定性

- 任务 11b（同步引擎从零）工时估计偏乐观，可能要 7-10 天而不是 5 天
- 任务 11c 已在 2026-05-09 改为 uni-app 统一端迁移；新基座 + 双跑 + 旧 Expo/Taro 清理通常需要额外 7-14 天，取决于 DCloud/Apple/Android/微信小程序资源是否到位
- 任务 9 涉及爬虫合规，外部第三方约束（robots/数据源协议）可能要法务复核，超出本计划范围
- 后端 7873 个 ruff 错误的"分层基线"建立，本计划放在 P2，可能要再延一周

### 7.3 不在本计划内的事

- 产品功能新增（除非已在 PRD 列表里且缺失）
- 团队管理 / 招聘 / 商务对接
- 法务合规审查（律所合规、数据合规、跨境合规）
- 营销 / 运营 / 推广

---

## 8. 单一执行者与协作

本次"逐个落实"由 Claude Code 主导执行，分为：

| 类型 | Claude 可独立做 | 用户需介入 |
|---|---|---|
| 计划书 / SOP / 差分文档 / 测试用例 / 提示词 | ✅ | — |
| 代码改动（无业务风险，如修 LLM org 过滤、统一上传校验、补失败 test） | ✅ 写 + 跑测试 + diff | 看 diff 决定是否合 |
| 改 prompts / 改 webhook / 改 token 存储 / 改商业化 / 改 design-tokens | ❌ | ✅ 必须用户点头 |
| 密钥轮换 / git filter-repo / push / 桌面签名 / 部署 | ❌ | ✅ 必须用户执行 |

每完成一个任务/里程碑，Claude 会停下来汇报，让用户决定是否继续。

---

## 9. 与 hierarchical-memory 的协同

每个任务执行完毕后，按以下规则沉淀：

- 每修一个 P0 钉子 → `add-bugfix --symptom <症状> --fix <修复> --files <相关文件>`
- 每补齐一个功能缺口 → `add-feature --name <功能> --pattern <实现> --files <相关文件>`
- 每个里程碑结束 → `save-session anxin "<里程碑 + 主要变更>"`
- 长期沉淀 → `digest` / `evolve` / `health`

复用反馈 → `feedback --id <id> --outcome success|partial|failed`，让记忆系统自我校准。

---

## 10. 计划生效条件

本计划在用户**明确同意**后生效。同意流程：

1. 用户审阅本 `PLAN.md`
2. 用户审阅 `00-platform/01-prd-reality-gap.md` 等任务 0 产出物
3. 用户对"7.1 必须确认事项"逐项答复
4. Claude 根据回复调整计划（如时间线收缩 / 密钥处理顺序 / 资源投入）
5. 进入 Day 0 任务 0 执行

在用户答复 7.1 之前，Claude 仅完成"任务 0 的 5 个文档产出"（纯文本，零代码改动），不进入任务 1+。

---

## 附录 A：18 处已核查的代码点位（事实清单）

| # | 文件:行 | 现状 | 修在哪个任务 |
|---|---|---|---|
| 1 | [App.tsx:207](../../frontend/src/App.tsx) | `/pro` 仅 ProtectedRoute 无守卫 | 任务 2 |
| 2 | [ProLayout.tsx:30-68](../../frontend/src/components/pro/ProLayout.tsx) | 导航全指向根路径 | 任务 2 |
| 3 | [ModeGate.tsx:153](../../frontend/src/components/mode/ModeGate.tsx) | 直接 setMode(HYBRID) | 任务 2 |
| 4 | [PrivacyContext.tsx:68-86](../../frontend/src/context/PrivacyContext.tsx) | 默认 8003 + `?? true` + catch setMode | 任务 2 |
| 5 | [due_diligence.py:60](../../backend/src/api/routes/due_diligence.py) | 仅 get_current_user_required | 任务 9 |
| 6 | [lawyer_matching.py:71](../../backend/src/api/routes/lawyer_matching.py) | 仅 get_current_user_required | 任务 8b |
| 7 | [esign_service.py](../../backend/src/services/esign_service.py) | ✅ e签宝/法大大 provider 代码级官方协议已实现；真实商户沙箱与灰度证据待补 | 任务 5 |
| 8 | [esign_service.py:476-478](../../backend/src/services/esign_service.py) | 默认工厂返回 MockESignProvider | 任务 5 |
| 9 | [payment_service.py](../../backend/src/services/payment_service.py) | ✅ 微信支付 v3 Native 下单/查单/关单/退款、支付宝 page.pay/query/refund/close 签名请求与同步响应验签已实现；待真实沙箱验收与证书/公钥轮换验证 | 任务 10 |
| 10 | [payments.py](../../backend/src/api/routes/payments.py) | ✅ 通用 HMAC 后调用 `payment_webhook_service` 回写订单/订阅，并接 `webhook_idempotency_service` + `webhook_received` + Admin 查询/重试入口 + Prometheus 指标 + 失败自动重试/backoff + 微信支付 v3/支付宝 RSA2 回调验签；真实沙箱闭环待补 | 任务 10 |
| 11 | [esign.py](../../backend/src/api/routes/esign.py) | ✅ 通用 HMAC 后调用 `esign_webhook_service` 回写合同签署状态，并接 `webhook_idempotency_service` + `webhook_received` + `esign_flow_id` 映射；e签宝官方 HMAC 与法大大 FASC 回调验签已补，账号事件映射和沙箱灰度证据待补 | 任务 5 |
| 12 | [sync.rs](../../desktop/src/commands/sync.rs) | Rust IPC 直连同步 fallback 已补代码级 SQLCipher pending/failed push、accepted/conflict/failed 写回、pull 本地表写回和 cursor 更新时间；TopSecret/未登录仍 fail-closed；仍缺 packaged runtime 证据 | 任务 11b |
| 13 | [sync_engine.rs:191,199](../../desktop/src/services/sync_engine.rs) | Rust service push/pull 未启用时返回 Error，不再 `Ok(0)`；仍需真实云数据面或保持显式禁用 | 任务 11b |
| 14 | [document_service.py](../../backend/src/services/document_service.py) | ✅ 2026-05-06 已接 `object_storage_service`，上传/删除/更新不再是空 TODO | 任务 6 |
| 15 | [store.ts:272,281](../../frontend/src/lib/store.ts) | localStorage + persist 双重持久化 | 任务 1 |
| 16 | [useIMWebSocket.ts:71](../../frontend/src/hooks/useIMWebSocket.ts) | URL query token | 任务 10 |
| 17 | [anonymous_chat.py:136-169](../../backend/src/api/routes/anonymous_chat.py) | 公开创建 + 一次返回双 token | 任务 9 |
| 18 | [llm.py:177](../../backend/src/api/routes/llm.py) + [llm_service.py:288](../../backend/src/services/llm_service.py) | 服务层 `if org_id:` 错过 None 分支 | 任务 2 |

---

## 附录 B：本计划与现有文档的关系

- **本计划不替代**：`PROJECT_STATUS.md`（项目实时状态）、`PRODUCT_ROADMAP.md`（产品规划）、`DESIGN.md`（设计系统）、`docs/architecture-v2.md`（架构）
- **本计划补充**：在 PROJECT_STATUS "Phase 1-5 已完成" 之后，加入"V2 实质就绪度差分"
- **本计划完成后**：将"M-D 里程碑达成"写回 PROJECT_STATUS，移除 P0 钉子项

---

> 文档作者：Claude Code（基于 18 处代码点位实测 + 用户初版计划修订）
> 审阅状态：待用户审阅 → 同意后生效
> 修订记录：v2.0（2026-05-04）首发
