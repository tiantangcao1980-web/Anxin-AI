# 安心智能助手 V3 — 16 周分阶段路线图（实际进度版）

> 从 V2「安心智能助手」升级到 V3「安心智能助手」，以**最小可用循环**为单位推进。每个阶段都能独立交付价值，不阻塞下一阶段。

> **当前状态（2026-04-27）**：P0–P7 全部 ✅ 落地，**31 commits / 61 个 v3 API endpoint / 543+ pytest**。原计划 16 周排期，实际并行压缩到 **2 天集中冲刺**完成主体骨架；后续 P8+ 进入打磨 + 落地阶段。

相关文档：[ARCHITECTURE](./ARCHITECTURE.md) · [AGENT_PERSONAS](./AGENT_PERSONAS.md) · [INTEGRATIONS](./INTEGRATIONS.md) · [V3_DELIVERY_SUMMARY](./V3_DELIVERY_SUMMARY.md)

---

## 总览（实际版 Gantt）

```
         2026-04-26      2026-04-27                  2026-04-28+
P0  ✅✅           品牌切换（已上线）
P1     ✅✅          IA + 占位页 + 后端 3 模块骨架 + 6 大文档
P2        ✅         异步任务 MVP（TaskOrchestrator）
P3           ✅      IM 通道（飞书 adapter 真）+ 配对授权 + 沙箱
P4              ✅   OAuth 框架 + 5 provider
P5                 ✅ Skills 运行时 + 4 office skill
P6                    ✅ FetchService 4 层 + 法律 + 电商源
P7                       ✅ 5 user-facing personas
P8                          🚧 进行中：bug 修 + 健康度 + 前端 + 文档
P9+                            🔜 5 法务 persona / 知识库 / E2E / 生产部署
```

---

## P0  品牌切换 ✅ 已完成（2026-04-26）

| 项 | 内容 |
|---|---|
| **完成日期** | 2026-04-26 |
| **目标** | 从「安心智能助手」品牌切换到「安心智能助手」 |
| **实际交付** | ✅ 8 个文件品牌名/Logo 替换<br>✅ App 内品牌文案统一<br>✅ 三端启动页 / about 页更新 |
| **风险** | 无 |
| **验收** | 用户在桌面 / 移动 / 小程序 / Web 任一端打开 App 看到的都是「安心智能助手」 |

---

## P1  侧边栏 IA + 占位页 + 后端骨架 + 文档 ✅ 已完成（2026-04-26）

| 项 | 内容 |
|---|---|
| **完成日期** | 2026-04-26 |
| **目标** | 把 36 页 重排为 10 personas 主导的 IA + 后端 3 模块骨架 + 6 大核心文档 |
| **实际交付** | ✅ 桌面 + Web 侧边栏：v3 IA 重构（feature flag 切换）<br>✅ 7 个 v3 占位页（tasks / capabilities × 6）<br>✅ 后端三模块骨架：`task_orchestrator` / `im_gateway` / `skill_registry`<br>✅ 6 大核心文档：ARCHITECTURE / AGENT_PERSONAS / CAPABILITY_MATRIX / ROADMAP / INTEGRATIONS / SKILLS_INVENTORY（89K 字符 / 1724 行） |
| **关键 commits** | `d32828b` `76fd039` `c7e1332` `ce8277f` `14cfceb` `8b04e52` |
| **验收** | feature flag 开启后，侧边栏切换到 v3 IA，10 personas 一级入口可见 |

---

## P2  异步任务 MVP（TaskOrchestrator + Celery） ✅ 已完成（2026-04-27）

| 项 | 内容 |
|---|---|
| **完成日期** | 2026-04-27 |
| **目标** | 长任务（> 10s）从同步对话转异步执行 |
| **实际交付** | ✅ 后端：`task_orchestrator/` 真实装（service / state_machine / celery_app / events / worker）<br>✅ Alembic 028: `agent_tasks` 表<br>✅ 8 个 task endpoint（list / create / update / status / delete / transition / batch / kanban-stats）<br>✅ 前端任务中心业务化：列表 + Timeline + 审批 + Mock 适配<br>✅ App.tsx 去重 V3TasksPage 与 /v3/tasks 路由 |
| **关键 commits** | `9a1d9a7` `bc26418` `a0b61dc` |
| **沿用** | sandbox 执行已统一到 P3 SandboxExecutor |
| **验收** | 通过 v3 task API 创建异步任务，状态机 + Celery worker 正确流转 |

---

## P3  IM 通道（飞书优先）+ 配对授权 + 沙箱 ✅ 已完成（2026-04-27）

| 项 | 内容 |
|---|---|
| **完成日期** | 2026-04-27 |
| **目标** | 飞书 IM 真实装 + 配对授权 24h 窗口 + 沙箱执行器骨架 |
| **实际交付** | ✅ 飞书 adapter 真实现（事件订阅 / 卡片消息 / 签名验证 / 卡片模板）<br>✅ IM gateway 注册表（飞书真 + 钉钉/企微/Slack/Telegram 占位 adapter）<br>✅ IM 配对授权 24h 窗口（pairing service + 5 API + Celery 过期清理 worker）<br>✅ Alembic 029: IM gateway 表（im_bindings / pairing_requests）<br>✅ 沙箱执行器骨架：`sandbox_executor/` + LocalProvider 可用实装（其他 Docker / E2B / Codex Cloud 占位）<br>✅ 前端 5 IM 渠道页业务化（飞书 / 钉钉 / 企微 / Slack / Telegram）<br>✅ 前端配对授权页业务化（待审核 + 已授权双段 + 24h 倒计时） |
| **关键 commits** | `b7fe5ac` `32eb84d` `dcdf098` `96cbd1f` `c3766fb` |
| **验收** | 飞书事件回调可触发 → 进入配对授权流程 → 24h 内可绑定 |

---

## P4  OAuth 应用授权框架 + 5 provider ✅ 已完成（2026-04-27）

| 项 | 内容 |
|---|---|
| **完成日期** | 2026-04-27 |
| **目标** | 上线 OAuth 集成框架 + 首批 5 个 provider |
| **实际交付** | ✅ 通用 OAuth 框架（base / oauth_flow / token_store 加密 / registry / models）<br>✅ Alembic 030: `app_authorizations` + `app_authorization_tokens` 表<br>✅ 6 个 app_authorization API（providers / list / authorize / callback / refresh / delete）<br>✅ **5 个 provider 实装**：飞书（5 endpoint 真 API）/ 钉钉 / Notion / Shopify（HMAC 回调验证）/ Amazon SP-API (mock placeholder via base)<br>✅ 前端应用授权页业务化：30+ provider OAuth 卡片市场 + 8 分类 + 搜索 + Mock |
| **关键 commits** | `0c2f123` `d80bcaf` `eed05cc` `fd5da78` `0f3e718` `da47e19` |
| **未实装** | Salesforce / HubSpot / 法大大 / 北大法宝 等仍在 P5+ 排期 |
| **验收** | 用户在应用市场点击 5 大 provider 卡片可走 OAuth 完整流程 |

---

## P5  Skills 运行时 + 4 office skill ✅ 已完成（2026-04-27）

| 项 | 内容 |
|---|---|
| **完成日期** | 2026-04-27 |
| **目标** | Skills 不再写死，运行时动态加载 + 4 office skill 移植 |
| **实际交付** | ✅ `skill_registry/` 真实装：pyyaml + watchdog 文件监听 + 热加载（loader / validators / models / registry）<br>✅ `skill_executor/` 新模块：装饰器 + executor + models<br>✅ 6 个 skills API（list / detail / triggers/match / upload / toggle / execute）<br>✅ **4 个 office skill 移植**（cowork-anthropic 兼容）：<br>　• `skills/office/docx/` (helpers + 3 templates + 5 tests)<br>　• `skills/office/xlsx/` (helpers + 3 templates + 5 tests)<br>　• `skills/office/pptx/` (4 templates + 5 tests)<br>　• `skills/office/pdf/` (OCR + 4 templates + 5 tests)<br>✅ 前端技能页业务化：50+ skill 跨 13 域 + 分组侧栏 + 详情抽屉 + 上传 + 试运行 |
| **关键 commits** | `2131da2` `ef088b6` `9962d75` `89561d6` `217d867` `d3600f8` |
| **验收** | 新 skill yaml 文件放入 `skills/` 目录，watchdog 热加载后立即出现在 UI |

---

## P6  信息获取栈（FetchService 4 层 + 多源）✅ 已完成（2026-04-27）

| 项 | 内容 |
|---|---|
| **完成日期** | 2026-04-27 |
| **目标** | 信息获取做成一等公民能力，覆盖 99% 公开信息抓取 |
| **实际交付** | ✅ FetchService 4 层门面（`backend/src/services/fetch/`）：<br>　• L1: HTTP + BS4（`tiers/l1_http.py`）<br>　• L2: crawl4ai（`tiers/l2_crawl4ai.py`）<br>　• L3: HeadlessX self-host 反检测（`tiers/l3_headlessx.py` + `headlessx_client/`）<br>　• L4: 官方 API（按 source 实现）<br>✅ URL 路由 + 合规审计（`router.py` / `compliance/` / `robots.py` / `rate_limiter.py`）<br>✅ 4 个 fetch API（fetch / batch / audit / sources）<br>✅ **4 法律源**（合规版）：`pkulaw` / `wkinfo` / `flk_npc_gov`（国家法律法规库）/ `credit_china`（信用中国）/ `historical_wenshu`（历史文书库）<br>✅ **5 电商源**：`shopify`（真）+ `amazon_sp` / `shopee` / `tiktok_shop` / `alibaba_1688`（mock 占位） |
| **关键 commits** | `4d53e3e` `2ce0533` `b7c05ea` `e17a69b` |
| **验收** | 一行调用 `fetch(url)`，按 URL 自动选层并完成抓取，全链路审计 |

---

## P7  5 user-facing personas ✅ 已完成（2026-04-27）

| 项 | 内容 |
|---|---|
| **完成日期** | 2026-04-27 |
| **目标** | 上线 5 个增长 + 协调域 personas（流程 / 市场 / 获客 / 内容 / 出海） |
| **实际交付** | ✅ `PersonaRegistry`（`backend/src/agents/personas/registry.py`）+ `BasePersona`<br>✅ **5 personas 真实装**（每个一个 .py + 模型文件 + API + 测试）：<br>　• 📋 流程管家（`operations_manager.py`，7 API）<br>　• 📊 市场研究员（`market_researcher.py` + DeepResearch 迭代算法，5 API）<br>　• 🎯 获客猎手（`lead_hunter.py` + LeadScoring 模型，6 API）<br>　• ✍️ 内容总监（`content_director.py`，7 API）<br>　• 🌍 跨境电商助手（`ecommerce_assistant.py` + AI 议价，7 API）<br>✅ Persona 通用 API（`personas.py`：list / detail / chat） |
| **关键 commits** | `3445501` `0c69b83` `9de3895` `8b785a8` `2624335` |
| **未实装** | 5 个法务 persona（安心助理 / 法律顾问 / 合同管家 / 尽调专家 / 财税顾问）— 已有 21 个 specialized agent 可直接复用，待 P9+ 包装 |
| **验收** | 通过 `/api/v3/personas` 看到 5 实装 + 5 占位；调用 chat / 业务 API 可走完整流程 |

---

## P8  打磨 + 文档同步 + 健康度 + 前端集成 🚧 进行中（2026-04-28+）

| 子阶段 | 内容 | 状态 |
|---|---|---|
| **P8-A** | 修 baseline bug：alembic head 收口 / 异步事务 / 缓存策略 | 🚧 |
| **P8-B** | 健康度盘点：测试覆盖 / lint / build / 性能基线 | 🚧 |
| **P8-C** | 前端 personas 落地页：5 personas 各一个详情页 + 入口 + Mock | 🚧 |
| **P8-D** | 文档同步：docs/v3/ 全量更新到 P0–P7 实际交付（**本任务**） | 🚧 → ✅ |

---

## P9+ 后续阶段

### P9 — 5 法务 persona 上层包装

| 项 | 内容 |
|---|---|
| **目标** | 5 个法务 persona（安心助理 / 法律顾问 / 合同管家 / 尽调专家 / 财税顾问）user-facing 包装 |
| **路径** | 复用现有 21 个 specialized agents：legal_advisor / contract_reviewer / due_diligence / tax_compliance 等 |
| **预计周期** | 2–3 周 |

### P10 — 知识库新版

| 项 | 内容 |
|---|---|
| **目标** | RAG-Anything (HKUDS) + MinerU 多模态接入；引文锚点；跨文档联检 |
| **关键** | Qdrant 多模态向量；DeepTutor 模式 |
| **预计周期** | 4–6 周 |

### P11 — 团队协作功能

| 项 | 内容 |
|---|---|
| **目标** | 多人 / 多租户共享：tenant_id 全链路 + RBAC + 审计可视化 |
| **预计周期** | 3–4 周 |

### P12 — E2E playwright 全量

| 项 | 内容 |
|---|---|
| **目标** | 5 personas × 主流程 × 桌面/移动/Web 三端 E2E 全覆盖 |
| **预计周期** | 2 周 |

### P13 — 生产部署到 anxinai.com

| 项 | 内容 |
|---|---|
| **目标** | 域名切换 anxinai.com → anxinai.com；CDN / TLS / Nginx 同步 |
| **关键** | 双域名平滑过渡（30 天 redirect 兼容） |
| **预计周期** | 1 周 |

### Beyond P13 — Agent 三层重构 / Evolver / 国际化

- Agent 三层重构（L1 Persona / L2 Orchestrator / L3 Specialized 显式契约）
- Evolver 学习闭环（任务完成 → 经验回流，EvoMap 范式）
- 国际化（出海团队需求）
- 私有化部署优化（合规客户专属环境）
- LLM 路由 / 缓存 / 成本优化

---

## 风险登记册（P0-P7 复盘 + 后续）

| # | 风险 | 等级 | 现状 | 缓解 |
|---|---|---|---|---|
| 1 | 沙箱跨平台兼容差 | 🟡 | LocalProvider 可用，Docker / E2B / Codex Cloud 仍占位 | P9+ 补 Docker provider |
| 2 | OAuth 凭证泄露 | 🟢 | KMS / 加密 token_store 已落地 | 持续审计 |
| 3 | 反爬升级持续打击 | 🟡 | HeadlessX 已接入，但 IP 池未完整 | 第 1 阶段共享 + 后期独立 |
| 4 | 多 agent 协商性能 | 🟡 | 5 personas 串行为主 | P9+ 异步 + 缓存 |
| 5 | LLM 成本失控 | 🟡 | 路由策略未上 | 配预算告警 + 缓存 |
| 6 | IM 多租户隔离 | 🟡 | tenant_id 已落表 | 全链路 RBAC 待补 |
| 7 | 跨境合规 | 🔴 | 5 电商源中 4 个 mock 占位 | P9+ 接入真 API + 法务复核 |
| 8 | IA 切换不适应 | 🟢 | feature flag 灰度 | 顶部提示已加 |
| 9 | Skills 第三方安全 | 🟡 | 仅本地 yaml，无第三方接入 | P10+ 签名 + 沙箱 |
| 10 | 5 法务 persona 缺位 | 🟡 | P9+ 排期 | 已有 21 agent 可直接调用兜底 |

---

## 验收节奏（每阶段必须）

每阶段完成必须满足：

- [x] P0–P7 已逐阶段交付，commits 可追溯
- [ ] 端到端 demo 视频（P8 补录）
- [x] 文档同步更新（本次 P8-D 完成）
- [ ] 内部 dogfood 至少 5 人参与 1 周（P8 启动）
- [ ] 灰度上线策略（10% → 50% → 100%）（P13 生产部署时执行）

---

上次更新：2026-04-27（P0-P7 完成 + P8-D 文档同步）
