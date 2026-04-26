# 安心智能助手 V3 — 16 周分阶段路线图

> 从 V2「安心法务」升级到 V3「安心智能助手」，以**最小可用循环**为单位推进。每个阶段都能独立交付价值，不阻塞下一阶段。

> 总周期：**16 周**（P0 已完成，P1 进行中，P2–P7 共 ~17 周排期，并行可压缩到 13 周）。

相关文档：[ARCHITECTURE](./ARCHITECTURE.md) · [AGENT_PERSONAS](./AGENT_PERSONAS.md) · [INTEGRATIONS](./INTEGRATIONS.md)

---

## 总览（Gantt 简版）

```
周 →  W1  W2  W3  W4  W5  W6  W7  W8  W9  W10 W11 W12 W13 W14 W15 W16
P0  ✅✅
P1     🚧🚧
P2        ▓▓▓▓▓▓▓▓▓
P3                 ▓▓▓▓▓▓
P4                       ▓▓▓▓▓▓        (与 P3 部分并行)
P5                             ▓▓▓▓▓▓
P6                                   ▓▓▓▓▓▓
P7                                         ▓▓▓▓▓▓▓▓▓▓▓▓
后续 ───────────── Agent 三层重构 / Evolver / RAG-Anything → 持续
```

---

## P0  品牌切换 ✅ 已完成

| 项 | 内容 |
|---|---|
| **周期** | 已完成 |
| **目标** | 从「安心法务」品牌切换到「安心智能助手」 |
| **交付物** | ✅ Logo / 名称 / 域名（anxinfawu.com 保留 + 新仓库 Anxin-Smart-Assistant）<br>✅ App 内品牌文案统一<br>✅ 三端启动页 / about 页更新 |
| **风险** | 无 |
| **验收** | 用户在桌面 / 移动 / 小程序 / Web 任一端打开 App 看到的都是「安心智能助手」 |

---

## P1  侧边栏 IA + 占位页 🚧 进行中

| 项 | 内容 |
|---|---|
| **周期** | 2 周 |
| **目标** | 把现有 36 页 重排为 10 personas 主导的 IA，未上线功能用占位页表态 |
| **交付物** | 桌面 + Web 侧边栏：10 personas 一级入口<br>每 persona 有占位页（hero + 能力清单 + 「敬请期待」CTA）<br>移动端导航更新（5 个底部 + 抽屉访问完整 10 个）<br>小程序：保留核心 3 个 persona 入口<br>路由表 + 命名规范文档 |
| **风险** | - 现有 51 routes 有些无对应 persona，需要分类归并 → 通过路由 redirect 兼容<br>- 用户习惯打破，需要顶部一次性提示「IA 已升级」 |
| **验收** | 任意用户打开 App，看到的都是 10 个 personas，不再是 V2 的法务模块树 |

---

## P2  异步任务 MVP（TaskOrchestrator + Sandbox）

| 项 | 内容 |
|---|---|
| **周期** | 3 周 |
| **目标** | 长任务（> 10s）从同步对话转异步执行，参考 Codex / Dispatch / Devin 范式 |
| **交付物** | 后端：`TaskOrchestrator` + `TaskQueue (Celery + Redis)` + `SandboxExecutor`<br>桌面：托盘任务中心 + 进度通知 + 完成提醒<br>移动：推送通道 + 任务列表<br>沙箱：macOS sandbox-exec / Linux firejail / Docker 兜底<br>SSE / WebSocket 实时进度推送<br>任务失败回滚 + 重试策略 |
| **风险** | - 沙箱跨平台差异大 → 优先 macOS + Docker 兜底<br>- 长任务的 LLM 上下文管理 → 用 hierarchical memory 切片<br>- 任务可观测性差 → OpenTelemetry 全链路埋点 |
| **验收** | 用户在桌面发起一个「尽调任务」，关闭 App 后再打开能继续看到进度并接收完成通知 |

---

## P3  IM 通道（飞书优先）

| 项 | 内容 |
|---|---|
| **周期** | 2 周 |
| **目标** | 用户在飞书群里 @bot 即可触发任务，结果以卡片回推 |
| **交付物** | 飞书机器人接入（事件订阅 + 卡片消息 + 文件上传）<br>飞书 OAuth 登录 + 用户绑定<br>群内 @bot 路由到正确 persona<br>飞书卡片模板：进度 / 结果 / 错误 / 审批<br>钉钉 / 企微 复用同一 Gateway 抽象（占位实现）<br>Slack 适配（出海团队用） |
| **风险** | - 飞书企业自建 vs 开放平台 → 兼容两套<br>- 多群 / 多组织数据隔离 → 引入 tenant_id<br>- 频控限制 → 队列削峰 |
| **验收** | 在飞书群 @bot 「帮我查 XX 公司」可在 60s 内得到带链接的卡片回复 |

---

## P4  OAuth 应用市场首批 5 个（与 P3 部分并行）

| 项 | 内容 |
|---|---|
| **周期** | 2 周 |
| **目标** | 上线 OAuth 集成框架 + 首批 5 个最优先的应用 |
| **交付物** | 统一 OAuth 框架（KMS 凭证存储、自动 refresh、最小授权）<br>**首批 5 个集成**：飞书、钉钉、企微、Notion、Shopify<br>应用市场 UI（卡片 + 启用 / 停用 / 重新授权）<br>每个集成对应的 skill / agent 调用文档 |
| **风险** | - 各应用 OAuth 协议差异 → 抽象 IntegrationProvider 接口<br>- token 失效时优雅降级<br>- 数据回流增量同步策略 |
| **验收** | 用户在应用市场点击「连接飞书」完成授权后，对应 persona 立即可调用飞书数据 |

---

## P5  Skills 运行时加载

| 项 | 内容 |
|---|---|
| **周期** | 2 周 |
| **目标** | Skills 不再写死在代码里，支持运行时动态加载 + 热更新 + 版本管理 |
| **交付物** | Skills 注册表（数据库 + 文件系统）<br>Skill schema 定义（cowork-anthropic + Accio + 自建 三种来源）<br>Skill 运行时（Python entry point + 沙箱）<br>UI：Skill 浏览器 / 启用 / 配置参数<br>首批接入 13 个域 ~50 个 skills（详见 [SKILLS_INVENTORY](./SKILLS_INVENTORY.md)） |
| **风险** | - skill 之间依赖管理 → 显式声明 deps + 自动安装<br>- 第三方 skill 安全性 → 签名 + 权限白名单<br>- 性能 → 懒加载 + LRU 缓存 |
| **验收** | 新 skill 文件放入指定目录，重启服务（或热加载）后自动出现在 UI 可被 persona 调用 |

---

## P6  信息获取栈 + HeadlessX self-host

| 项 | 内容 |
|---|---|
| **周期** | 2 周 |
| **目标** | 把信息获取做成一等公民能力，覆盖 99% 公开信息抓取需求 |
| **交付物** | 信息获取分级（API / HTTP / crawl4ai / HeadlessX）<br>HeadlessX self-host（Docker 部署 + 反检测策略）<br>crawl4ai 集成 + 多代理池<br>统一 `intelligence/fetch` skill 接口（智能选型）<br>合规层：robots.txt 检查 + 频控 + UA 标识 + 审计日志 |
| **风险** | - 反爬升级要持续维护<br>- IP 池成本 → 第一阶段共享 + 后期按需独立<br>- 合规边界 → 法务团队制定红线清单 |
| **验收** | 一行代码 `fetch(url)`，自动选最优策略并完成抓取，失败可回退 |

---

## P7  跨境电商 + 销售 agent

| 项 | 内容 |
|---|---|
| **周期** | 4 周 |
| **目标** | 上线 P7-1 跨境电商助手 + P7-2 获客猎手 两个增长域 personas |
| **交付物** | **P7-1（2 周）跨境电商助手**：<br>- 自建 ecommerce_agent / selection_agent / oversea_compliance_agent<br>- Shopify / Amazon SP-API / 1688 集成<br>- 选品 / 独立站 / 出海合规 三个核心场景<br>- 参考 Accio Ecommerce Mind 范式<br><br>**P7-2（2 周）获客猎手**：<br>- 自建 lead_agent / vibe_seller / ad_optimizer<br>- Salesforce / HubSpot 集成<br>- Vibe Selling + AI-Trader 投放决策<br>- LinkedIn Sales Navigator 接入 |
| **风险** | - 跨境合规复杂（GDPR / VAT / 海关），需法律顾问深度配合<br>- AI-Trader 多 agent 协商性能 → 异步执行 + 缓存<br>- LinkedIn 反爬严格 → 走官方 API + Headless 兜底 |
| **验收** | 完成「制造业出海评估」+「广告投放优化」两个端到端 demo |

---

## 后续阶段（Beyond P7）

### Agent 三层重构

| 项 | 内容 |
|---|---|
| **目标** | 把现有 21 个 agents 重构为 L1 Persona + L2 Orchestrator + L3 Specialized 三层 |
| **关键** | 接口契约、上下文传递、能力声明、可观测性 |
| **周期** | 持续 4 周 |

### Evolver 学习闭环（EvoMap 范式）

| 项 | 内容 |
|---|---|
| **目标** | 任务完成 → 经验沉淀 → 下次任务自动复用，形成飞轮 |
| **关键** | 经验图谱、相似任务召回、A/B 验证 |
| **周期** | 持续 4-6 周 |

### RAG-Anything 多模态 (HKUDS)

| 项 | 内容 |
|---|---|
| **目标** | 接入 HKUDS RAG-Anything + MinerU，支持 PDF / 图 / 表 / 公式 / 视频帧 多模态检索 |
| **关键** | 索引存储（Qdrant + 多模态向量）、引文锚点、跨文档联检 |
| **周期** | 持续 4-6 周 |

### 其他持续项

- 三端体验对齐（桌面 / 移动 / 小程序 设计语言一致）
- 国际化（出海团队需求）
- 私有化部署优化（合规客户专属环境）
- 性能 + 成本优化（LLM 路由、缓存、请求合批）

---

## 风险登记册（Top 10）

| # | 风险 | 等级 | 缓解 |
|---|---|---|---|
| 1 | 沙箱跨平台兼容差 | 🔴 | 优先 macOS + Docker 兜底，Windows 用 WSL2 |
| 2 | OAuth 凭证泄露 | 🔴 | KMS 加密 + 最小授权 + 审计 |
| 3 | 反爬升级持续打击 | 🟡 | 多策略组合 + 官方 API 优先 |
| 4 | 多 agent 协商性能 | 🟡 | 异步 + 缓存 + 早停策略 |
| 5 | LLM 成本失控 | 🟡 | 路由（小模型先 / 大模型兜底） + 缓存 + 预算告警 |
| 6 | IM 通道多租户隔离 | 🟡 | tenant_id 全链路 + RBAC |
| 7 | 跨境合规风险 | 🔴 | 法务团队制定红线 + 法律顾问 persona 复核 |
| 8 | 用户 IA 切换不适应 | 🟡 | 顶部一次性提示 + 老路由保留 30 天 redirect |
| 9 | Skills 第三方安全 | 🔴 | 签名 + 权限白名单 + 沙箱 |
| 10 | 知识库版权 | 🟡 | 公开数据 + 用户授权 + 引文标注 |

---

## 验收节奏（每阶段必须）

每阶段完成必须满足：

- [ ] 至少 1 个端到端 demo 视频（≤ 3 分钟）
- [ ] 风险登记册更新
- [ ] 文档（含本路线图）同步更新
- [ ] 内部 dogfood 至少 5 人参与 1 周
- [ ] 灰度上线策略（10% → 50% → 100%）

---

上次更新：2026-04-26
