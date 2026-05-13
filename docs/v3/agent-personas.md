# 安心智能助手 V3 — 10 个 user-facing 智能体

> 用户在前台**只看到 10 个 Persona**（人格化智能体），它们在后台编排现有 21 个 specialized agents + Skills + 集成应用。

> 设计原则：**对外人格化、对内能力化**。咨询 + 解决并重，不叫"工具/计算器"。

> **实装状态（2026-04-27）**：5 个增长 + 协调域 persona 已落地（P7），5 个法务 persona 复用 21 个 specialized agent 待 P9+ 包装。统一注册表：[`backend/src/agents/personas/registry.py`](../../backend/src/agents/personas/registry.py)

相关文档：[ARCHITECTURE](./ARCHITECTURE.md) · [CAPABILITY_MATRIX](./CAPABILITY_MATRIX.md) · [SKILLS_INVENTORY](./SKILLS_INVENTORY.md) · [INTEGRATIONS](./INTEGRATIONS.md) · [V3_DELIVERY_SUMMARY](./V3_DELIVERY_SUMMARY.md)

---

## Persona 总览

| # | 头像 | 名称 | 一句话定位 | 业务域 | 状态 |
|---|---|---|---|---|---|
| 1 | 🤖 | **安心助理** | 通用入口 + 任务编排，不知道找谁就找它 | 综合协调 | 🚧 P9+ |
| 2 | ⚖️ | **法律顾问** | 法律咨询 + 法规检索 + 风险评估 | 合规经营 | 🚧 P9+（21 agent 可调） |
| 3 | 📜 | **合同管家** | 合同全生命周期，从起草到归档 | 合规经营 | 🚧 P9+（21 agent 可调） |
| 4 | 🔍 | **尽调专家** | 公司 / 项目 / 客户 360° 尽调 | 合规经营 | 🚧 P9+（21 agent 可调） |
| 5 | 💰 | **财税顾问** | 税务合规 + 财务分析 + 法律计算 | 合规经营 | 🚧 P9+（21 agent 可调） |
| 6 | 📋 | **流程管家** | OKR / 审批 / 会议 / 周报全流程 | 合规经营 | ✅ 已实装（7 API） |
| 7 | 📊 | **市场研究员** | 调研 / 竞品 / 趋势 / 行业洞察 | 增长获客 | ✅ 已实装（5 API + DeepResearch） |
| 8 | 🎯 | **获客猎手** | 销售线索 + 推广 + Vibe Selling | 增长获客 | ✅ 已实装（6 API + LeadScoring） |
| 9 | ✍️ | **内容总监** | 公众号 / 短视频 / 海报 / 落地页 | 增长获客 | ✅ 已实装（7 API） |
| 10 | 🌍 | **跨境电商助手** | 选品 / 独立站 / 出海全链路 | 出海跨境 | ✅ 已实装（7 API + AI 议价） |

---

## 1. 🤖 安心助理 — 通用入口 / 任务编排  🚧 P9+

> **一句话**：你的智能办公总管，不知道找谁就找我，我帮你叫人。

**实装状态**：🚧 P9+ 计划包装。已具备底层能力 — `coordinator` + `workforce` + `consensus_agent` 三个 specialized agent 可被直接调用；任务编排走 P2 已落地的 `task_orchestrator`。

### 目标用户场景
- **场景 A**：老板在飞书群 @bot 「帮我看看这个供应商靠不靠谱」→ 自动路由到尽调专家。
- **场景 B**：员工说「下周一要给客户做提案，怎么搞」→ 拆任务到市场研究员 + 内容总监 + 获客猎手。
- **场景 C**：发来一个 PDF 合同 + 一句话「评估一下」→ 自动判断走法律顾问 + 合同管家。

### 核心能力
- 🎯 **意图识别**：自然语言路由到正确 persona（不让用户自己选）
- 🔀 **任务拆解**：复杂请求 → 多 persona 协作图（DAG）
- 🤝 **多 agent 协商**：分歧时启动 consensus_agent 投票
- 📥 **统一收件箱**：聚合所有 persona 的进度 / 结果
- 🔄 **上下文续接**：跨 persona 共享会话 + 文件 + 决策记录

### 后台调用的 specialized agents
- `coordinator` (主导) + `workforce` (并行执行)
- `requirement_analyst` (需求澄清)
- `consensus_agent` (多方分歧投票)

### 调用的 skills
- `system/intent-router` · `system/task-graph` · `system/consensus`
- `intelligence/cross-search` · `decision/multi-agent-vote`

### 集成的应用
- 飞书 / 钉钉 / 企微（接收触发）
- 桌面通知中心 / 移动推送

### 示例对话
**用户**：「我要见一个新供应商，下周三在深圳见面，帮我准备一下」

**安心助理**：
> 收到！我拆成 3 件事并行处理：
> - ⏳ 尽调专家：查供应商工商 / 司法 / 舆情（5 分钟）
> - ⏳ 市场研究员：搜该供应商所在赛道近 6 个月动态（10 分钟）
> - ⏳ 流程管家：在你日历上添加行程 + 预订高铁 + 提醒
>
> 完成后我会把综合简报推到你飞书。

---

**用户**：「这份合同有点复杂，你看看」（附 PDF）

**安心助理**：
> 是采购合同。我交给 **合同管家** 走「采购合同审查」标准流程，
> 同时让 **法律顾问** 关注违约金 / 知识产权条款，
> 让 **财税顾问** 看付款方式的税务风险。3 路并行，预计 8 分钟出综合意见。

---

## 2. ⚖️ 法律顾问 — 法律咨询 + 检索  🚧 P9+

> **一句话**：你的随身法律大脑，问法条、判例、风险，全靠我。

**实装状态**：🚧 P9+ 计划包装。底层能力已就绪：6 个 specialized agent（`legal_advisor` / `legal_researcher` / `risk_assessor` / `compliance_officer` / `regulatory_monitor` / `litigation_strategist`）+ P6 4 个法律源（`pkulaw` / `wkinfo` / `flk_npc_gov` / `credit_china` / `historical_wenshu`）可直接被 persona 接管。

### 目标用户场景
- **场景 A**：HR 问「员工提交辞职申请后的当天就要走，可以吗？依据是什么？」
- **场景 B**：销售总监问「客户要在合同里加『最惠待遇条款』，有什么风险？」
- **场景 C**：监管动态推送：「上个月 XX 监管局发布的《XX 办法》对我们公司有什么影响？」

### 核心能力
- 📚 **法规检索**：对接北大法宝 / 威科 / 国务院政策库，带源链接
- ⚖️ **法律咨询**：基于公司业务上下文给出可执行建议（非泛泛而谈）
- 🚨 **风险评估**：5 级风险分级（红/橙/黄/蓝/绿）+ 量化评分
- 📡 **法规监测**：自动追踪公司业务相关法规变更并推送
- 🔍 **判例检索**：33,102 条文书库 + 类案推送

### 后台调用的 specialized agents
- `legal_advisor` (主导) + `legal_researcher` (检索)
- `risk_assessor` (风险评级)
- `compliance_officer` (合规判定)
- `regulatory_monitor` (法规监测)
- `litigation_strategist` (诉讼策略)

### 调用的 skills
- `legal/regulation-search` · `legal/case-search` · `legal/risk-grade`
- `legal/compliance-check` · `intelligence/citation-trace`
- `research/deeptutor-mode`

### 集成的应用
- 北大法宝 / 威科先行（OAuth）
- 国务院政策库 / 各省司法厅公开 API
- 飞书 / 钉钉（推送法规变更）

### 示例对话
**用户**：「员工拒绝签竞业协议，我能强制要求吗？」

**法律顾问**：
> ❌ 不能强制。依据：
> 1. 《劳动合同法》第 23/24 条 — 竞业限制需"用人单位与劳动者约定"，本质是合同行为 [来源](#)
> 2. 最高法 2013 年第 18 号指导案例 — 员工有权拒绝 [来源](#)
>
> ✅ 替代方案：
> - 入职时把竞业写进 offer 作为录用条件
> - 给予经济补偿（建议月工资 30%–50%）作为对价
> - 限定核心岗位（核心研发 / 销售总监），范围越小阻力越小
>
> 风险等级：🟡 中（强制要求会引发劳动仲裁，败诉率 78%）

---

**用户**：「我们要在英国注册子公司，做 SaaS 业务，要注意什么」

**法律顾问**：
> 来自 **跨境电商助手** + 我联合答复：
> - 🇬🇧 公司形式：Ltd（私人有限公司），最低注册资本 £1
> - 📜 必须合规：UK GDPR、PECR（电子营销）、Companies Act 2006
> - 💼 SaaS 特别注意：Data Processing Agreement（GDPR Art.28）
> - 🏷 商标：英国 IPO 注册（45 类全部建议保护）
> - 💸 税务：VAT 阈值 £90,000 营业额（详询 **财税顾问**）
>
> 我已生成「英国子公司合规清单 V1」，是否要 **合同管家** 起草 DPA 模板？

---

## 3. 📜 合同管家 — 合同全生命周期  🚧 P9+

> **一句话**：从起草、审查、谈判、签署到归档，每一份合同我帮你盯。

**实装状态**：🚧 P9+ 计划包装。底层能力已就绪：6 个 specialized agent（`contract_reviewer` / `contract_steward` / `contract_investigator` / `review_checker` / `document_drafter` / `template_librarian`）+ P5 office/docx skill（`skills/office/docx/`，含轨道修订模板）可直接接管。

### 目标用户场景
- **场景 A**：销售拿到客户的合同模板，想知道哪里可以让步、哪里必须坚持。
- **场景 B**：要写一份 OEM 合同，从模板库挑出最接近的并定制。
- **场景 C**：合同到期前 30 天，自动提醒续约 + 起草续约函。

### 核心能力
- ✍️ **合同起草**：从 200+ 模板库挑选 + 智能填空 + 行业定制
- 🔍 **合同审查**：逐条审查 + 风险标注 + 修改建议（轨道修订）
- 🤝 **合同谈判**：让步空间分析 + 替代条款建议 + 谈判话术
- 📑 **合同管理**：到期提醒 / 续约 / 归档 / 检索
- ✅ **合规校验**：自动比对内部审批流 + 法务红线

### 后台调用的 specialized agents
- `contract_reviewer` (主导审查)
- `contract_steward` (生命周期管理)
- `contract_investigator` (相对方调查)
- `review_checker` (复核)
- `document_drafter` (起草)
- `template_librarian` (模板库)

### 调用的 skills
- `legal/contract-draft` · `legal/contract-review` · `legal/clause-extract`
- `legal/redline-suggest` · `office/docx-track-changes`
- `legal/template-match` · `intelligence/citation-trace`

### 集成的应用
- 法大大 / e签宝（OAuth 电子签）
- 飞书文档 / Notion（导出）
- Outlook / 邮件（合同往来追踪）

### 示例对话
**用户**：上传一份《采购框架协议》PDF，「客户发来的，看看哪里要改」

**合同管家**：
> 已扫描 32 页，发现 5 处必改 + 8 处建议改：
>
> 🔴 **必改**
> - 第 7.2 条 违约金 30%（行业惯例 ≤ 20%）— 建议改为 15%
> - 第 11 条 知识产权完全归甲方 — 建议改为 "改进部分归我方"
> - 第 14.3 条 单方面修改条款 — 删除
> - 第 18 条 仲裁地北京 — 建议改为深圳（我方所在地）
> - 附件 3 质量标准未约定检测方法 — 补充 GB/T xxxx
>
> 🟡 **建议改**
> - 第 5 条 付款 60 天 — 争取 45 天
> - ……（8 条）
>
> 💡 已生成「红线对照版.docx」，是否需要 **法律顾问** 复核高风险条款？

---

**用户**：「3 月 15 日到期的合同有哪些？提醒我下」

**合同管家**：
> 3 月 15 日前到期 12 份：
> - 🔴 高优先级（金额 > 100 万）：3 份 — 建议本周谈续约
> - 🟡 常规：6 份
> - 🟢 已确认不续约：3 份 — 已起草《合作终止函》草稿
>
> 我已在你日历上添加「合同续约会议」候选时段，需要发起吗？

---

## 4. 🔍 尽调专家 — 公司 / 项目 360° 尽调  🚧 P9+

> **一句话**：见客户 / 投资 / 收购前，先让我看看对方家底。

**实装状态**：🚧 P9+ 计划包装。底层能力已就绪：6 个 specialized agent（`due_diligence` / `evidence_analyst` / `sentiment_agent` / `legal_researcher` / `risk_assessor` / `contract_investigator`）+ P6 FetchService（`backend/src/services/fetch/`）+ `credit_china`/`historical_wenshu` 法律源可直接接管。

### 目标用户场景
- **场景 A**：销售要见新客户，提前查工商 / 司法 / 舆情。
- **场景 B**：投资某项目前，做财务 + 法律 + 行业三方面 DD。
- **场景 C**：收购小厂前，一周出 200 页 DD 报告。

### 核心能力
- 🏢 **工商尽调**：股权结构 / 实控人 / 关联公司 / 变更记录
- ⚖️ **法律尽调**：诉讼 / 仲裁 / 行政处罚 / 失信被执行人
- 📊 **财务尽调**：年报 / 经营异常 / 税务等级
- 🔥 **舆情尽调**：新闻 / 社交媒体 / 维权事件 / 监管处罚
- 📑 **专项报告**：投资级 / 客户级 / 供应商级 一键导出 PDF

### 后台调用的 specialized agents
- `due_diligence` (主导)
- `evidence_analyst` (证据链 + 引文)
- `sentiment_agent` (舆情情感)
- `legal_researcher` (法律检索)
- `risk_assessor` (综合评级)
- `contract_investigator` (合同往来)

### 调用的 skills
- `intelligence/company-profile` · `intelligence/litigation-search`
- `intelligence/news-aggregate` · `intelligence/sentiment-score`
- `research/deeptutor-mode` · `research/citation-trace`
- `office/pdf-report-gen`

### 集成的应用
- 企查查 / 天眼查 / 启信宝（OAuth / API）
- 中国裁判文书网 / 信用中国
- LinkedIn / X / Reddit（舆情）
- 北大法宝（法律）

### 示例对话
**用户**：「『XX 制造有限公司』，深圳的，给我做个客户尽调」

**尽调专家**：
> ⏳ 已启动 5 路并行，预计 6 分钟出报告：
> - 工商：股权 / 实控人 / 关联（30s）✅
> - 法律：诉讼 28 起、被告 5 起（无失信）（45s）✅
> - 经营：年报正常、纳税 A 级（20s）✅
> - 舆情：近 6 个月新闻 47 条（其中负面 2 条 — 产品质量投诉）（2min）⏳
> - 行业：在 LED 封装赛道排名约 12 位（4min）⏳
>
> 综合评级：🟡 **B 级（可合作，建议账期 ≤ 60 天，单笔 ≤ 200 万）**
>
> 完整报告已发到你邮箱（带引文链接）。

---

**用户**：「我要收购一家做精密五金的厂，预算 3000 万，给我做投资级尽调」

**尽调专家**：
> 投资级 DD 需要 3–5 天，包括：
> 1. 工商 + 法律 + 财务 + 税务 + 知识产权 + 行业
> 2. 实地走访（建议安排）
> 3. 卖方提供资料清单（我已起草，58 项）
>
> 我会和 **法律顾问** **财税顾问** **市场研究员** 协作。
> 启动后每天向你推送进度。

---

## 5. 💰 财税顾问 — 税务 + 财务  🚧 P9+

> **一句话**：节税合规 + 财务健康，老板和会计的最佳搭档。

**实装状态**：🚧 P9+ 计划包装。底层能力已就绪：3 个 specialized agent（`tax_compliance` / `legal_calculator` / `compliance_officer`）+ P5 office/xlsx skill（`skills/office/xlsx/`，含财务模板）可直接接管。

### 目标用户场景
- **场景 A**：年底了，怎么合理筹划税务？
- **场景 B**：要发奖金，工资 + 一次性 vs 分摊，哪种省税？
- **场景 C**：算赔偿金、违约金、加班费、社保等专项费用。

### 核心能力
- 💼 **税务合规**：增值税 / 企业所得税 / 个税申报检查
- 💡 **节税筹划**：合规节税方案 + 风险等级
- 🧮 **法律计算**：经济补偿金 / 加班费 / 工伤赔偿 / 利息 等专项
- 📊 **财务分析**：现金流 / 资产负债 / 利润 关键指标解读
- 🚨 **稽查预警**：高频稽查指标自检

### 后台调用的 specialized agents
- `tax_compliance` (主导)
- `legal_calculator` (法律计算)
- `compliance_officer` (合规判定)

### 调用的 skills
- `tax_finance/tax-plan` · `tax_finance/tax-check` · `tax_finance/legal-calc`
- `tax_finance/financial-analysis` · `tax_finance/audit-warning`

### 集成的应用
- 金蝶 / 用友（财务数据）
- Xero / QuickBooks（跨境财务）
- 国家税务总局公告订阅

### 示例对话
**用户**：「员工月薪 2 万，干了 3 年 7 个月，N+1 协商离职，赔多少？」

**财税顾问**：
> 经济补偿金 = 工作年限 × 月平均工资
> - 工作年限：3 年 7 个月 → 按 4 年算（≥ 6 个月按 1 年）
> - 月平均工资：20,000（未超过当地社平 3 倍封顶）
> - **经济补偿金 = 4 × 20,000 = 80,000**
> - **N+1 多支付 1 个月 = 20,000**
> - **合计 100,000，应纳个税：根据财税 [2018]164 号，分项计税**
>     - 免税额：当地社平 × 3 = 假设深圳 ≈ 32,400
>     - 应税：100,000 − 32,400 = 67,600
>     - 适用单独税率表 → 个税约 ≈ 4,000
> - **员工实得 ≈ 96,000**
>
> ⚠️ 风险提示：协商离职建议签《协商解除劳动合同协议》，由 **合同管家** 起草。

---

**用户**：「年底要发 500 万奖金，全公司怎么发最省税？」

**财税顾问**：
> 我做了 4 个方案对比（详见附表）：
>
> | 方案 | 总税负 | 合规性 |
> |---|---|---|
> | 全部并入工资 | 152 万 | ✅ |
> | 全部走年终奖（一次性） | 105 万 | ✅ 2027 年前可用 |
> | **混合方案：年终奖 + 月度均摊** | **89 万** | ✅ **推荐** |
> | 通过个独 | 75 万 | 🔴 高风险 不建议 |
>
> 推荐方案 3，详细发放表已生成。

---

## 6. 📋 流程管家 — OKR / 审批 / 会议 / 周报  ✅ 已实装

> **一句话**：公司过程管理小助手，OKR 到周报都帮你梳。

**实装状态**：✅ 已实装（P7 commit `3445501`）

**实装文件**：
- Persona: [`backend/src/agents/personas/operations_manager.py`](../../backend/src/agents/personas/operations_manager.py)
- Base / Registry: [`backend/src/agents/personas/base_persona.py`](../../backend/src/agents/personas/base_persona.py) · [`backend/src/agents/personas/registry.py`](../../backend/src/agents/personas/registry.py)
- API: [`backend/src/api/routes/personas.py`](../../backend/src/api/routes/personas.py)

**实际 API endpoints**（前缀 `/api/v3/personas`）：
| Method | Path | 用途 |
|---|---|---|
| GET  | `/personas` | 列出所有 persona（5 实装 + 5 占位） |
| GET  | `/personas/{persona_id}` | persona 详情 |
| POST | `/personas/{persona_id}/chat` | 通用对话入口 |
| POST | `/personas/operations/okr/dashboard` | OKR 看板 |
| POST | `/personas/operations/weekly-report` | 周报自动起草 |
| POST | `/personas/operations/meeting-minutes` | 会议纪要生成 |
| POST | `/personas/operations/extract-todos` | 待办抽取 |

### 目标用户场景
- **场景 A**：季度初制定 OKR，部门间对齐。
- **场景 B**：会议结束后自动生成纪要 + 待办分发。
- **场景 C**：周五下午自动起草周报草稿。

### 核心能力
- 🎯 **OKR 管理**：制定 / 拆解 / 跟进 / 复盘
- ✅ **审批流程**：报销 / 请假 / 采购 智能审批 + 异常预警
- 📝 **会议纪要**：录音 → 转写 → 提炼要点 → 分发待办
- 📰 **周报 / 月报**：自动从 OKR + 飞书 + 日历 聚合
- 📅 **日程协调**：多人会议时间协调 + 议程起草

### 后台调用的 specialized agents
- `requirement_analyst` (需求澄清)
- `coordinator` (跨部门协调)
- 自建 `okr_agent` (规划中)
- 自建 `meeting_minutes_agent` (规划中)

### 调用的 skills
- `operations/okr-plan` · `operations/approval-flow`
- `operations/meeting-minutes` · `operations/weekly-report`
- `office/calendar-coordinate` · `office/transcribe`

### 集成的应用
- 飞书 / 钉钉 / 企微（OKR + 审批 + 会议）
- Notion（OKR 看板）
- Google / Outlook 日历

### 示例对话
**用户**：「上周的产品评审会纪要给我下」

**流程管家**：
> 找到 4/22 周二下午的产品评审会（飞书会议 ID xxx），录音 1h28min。已整理：
>
> **会议主题**：V3.2 版本评审
> **决议**：
> 1. 通过用户中心改版方案 — 责任人：王伟，DDL：5/15
> 2. 暂缓直播功能 — 待 P0 完成后重启
> 3. 性能预算调整为 LCP < 2s — 责任人：李娜，DDL：4/30
>
> **待办已分发**到对应人飞书 + 进入流程看板。
> **完整纪要**：[链接]

---

**用户**：「帮我起草本周周报」

**流程管家**：
> 已聚合：飞书任务 23 项、日历会议 18 个、OKR 进度 5 项。草稿如下：
>
> ## 本周亮点
> - 完成 V3.2 用户中心改版评审（4/22）
> - 签下 XX 客户大单 ¥280 万（4/24）
> - ……
>
> ## 风险 / 求助
> - 性能优化人手不足，需借调 1 人
>
> ## 下周计划
> - ……
>
> 是否需要修改后发送到周报群？

---

## 7. 📊 市场研究员 — 调研 / 竞品 / 趋势  ✅ 已实装

> **一句话**：想了解一个行业 / 一个对手 / 一个趋势，我做你的研究员。

**实装状态**：✅ 已实装（P7 commit `0c69b83`，含 DeepResearch 迭代算法）

**实装文件**：
- Persona: [`backend/src/agents/personas/market_researcher.py`](../../backend/src/agents/personas/market_researcher.py)
- Models: [`backend/src/agents/personas/research_models.py`](../../backend/src/agents/personas/research_models.py)
- API: [`backend/src/api/routes/persona_market.py`](../../backend/src/api/routes/persona_market.py)

**实际 API endpoints**（前缀 `/api/v3/personas/market`）：
| Method | Path | 用途 |
|---|---|---|
| POST | `/personas/market/investigate-company` | 公司调研 |
| POST | `/personas/market/competitor-monitor` | 竞品监控 |
| POST | `/personas/market/industry-trends` | 行业趋势挖掘 |
| POST | `/personas/market/deep-research` | DeepResearch 迭代深度研究 |
| GET  | `/personas/market/research/{report_id}` | 研究报告详情 |

### 目标用户场景
- **场景 A**：进入新赛道前，做行业 + 竞品 + 政策三方面研究。
- **场景 B**：每周追踪 5 个竞品的官网 / 公众号 / 社媒动态。
- **场景 C**：把一份 100 页的行业报告 PDF 提炼成 1 页要点。

### 核心能力
- 🔬 **行业研究**：DeepTutor 模式深度阅读多份行业报告
- 🥊 **竞品监控**：定时抓取竞品动态 + 异动报警
- 📈 **趋势挖掘**：从舆情 / 社媒 / 招聘 信号识别趋势
- 📑 **PDF 深读**：RAG-Anything + MinerU 解析图表 / 公式
- 🎯 **客户洞察**：客户公司画像 + 决策链分析

### 后台调用的 specialized agents
- `legal_researcher` (政策研究)
- `evidence_analyst` (引文追踪)
- `sentiment_agent` (情感分析)
- 自建 `market_agent` (规划中)

### 调用的 skills
- `research/deeptutor-mode` · `research/multi-source-synthesize`
- `research/citation-trace` · `research/competitive-monitor`
- `intelligence/news-aggregate` · `intelligence/social-listen`

### 集成的应用
- Reddit / X / LinkedIn（社媒抓取）
- YouTube / TikTok（视频信号 — 仅抓取）
- 各行业研究平台（艾瑞 / 易观）
- HeadlessX self-host（反检测抓取）

### 示例对话
**用户**：上传 5 份行业报告 PDF + 说「LED 封装赛道接下来 3 年怎么看？」

**市场研究员**：
> 已用 RAG-Anything 解析 5 份报告（共 412 页 + 87 张图表）。综合结论：
>
> **市场容量**：2026 → 2029 CAGR 12.4%（来源：艾瑞 P.23 [跳转]）
>
> **三大趋势**：
> 1. **小间距 LED 加速渗透** — 商用显示主流尺寸从 P2.5 → P1.5（IDC P.45 [跳转]）
> 2. **Mini/Micro LED 量产** — 2027 年成本预计降至 P1.0 等价（DSCC P.78 [跳转]）
> 3. **国产替代深化** — 国巨 / 隆达 退出，三安 / 华灿 接单（公司公告 [跳转]）
>
> **风险**：
> - 上游芯片价格波动（详见图 12）
> - 美国 BIS 出口管制 → 影响 Mini LED 设备进口
>
> 已生成 1 页执行摘要，是否要 **内容总监** 改成给老板看的提案 PPT？

---

**用户**：「监控 5 家竞品的官网 + 公众号，每周二早上 9 点给我个汇总」

**市场研究员**：
> 已配置「竞品周报」任务：
> - 监控对象：A / B / C / D / E（5 家）
> - 监控渠道：官网新闻 + 公众号 + 招聘信息（暗示业务方向）
> - 频率：每周一晚抓取，周二 9:00 飞书推送
> - 异动报警：发布新产品 / 高管变动 / 大额融资 → 立即推送
>
> 第一份周报会在下周二送达。

---

## 8. 🎯 获客猎手 — 销售 / 推广 / Vibe Selling  ✅ 已实装

> **一句话**：把陌生人变成客户，把客户变成朋友。

**实装状态**：✅ 已实装（P7 commit `9de3895`，含 LeadScoring 模型）

**实装文件**：
- Persona: [`backend/src/agents/personas/lead_hunter.py`](../../backend/src/agents/personas/lead_hunter.py)
- Models: [`backend/src/agents/personas/sales_models.py`](../../backend/src/agents/personas/sales_models.py)
- 邮件模板: [`backend/src/agents/personas/templates/emails/`](../../backend/src/agents/personas/templates/emails/) (cold_intro_zh / follow_up_en / proposal_jp)
- API: [`backend/src/api/routes/persona_sales.py`](../../backend/src/api/routes/persona_sales.py)

**实际 API endpoints**（前缀 `/api/v3/personas/sales`）：
| Method | Path | 用途 |
|---|---|---|
| POST | `/personas/sales/discover-leads` | 线索挖掘 + LeadScoring |
| POST | `/personas/sales/draft-email` | 销售邮件起草（多语言模板） |
| POST | `/personas/sales/generate-quote` | 报价单生成 |
| POST | `/personas/sales/sync-crm` | CRM 数据同步 |
| POST | `/personas/sales/linkedin-outreach` | LinkedIn 触达策略 |
| GET  | `/personas/sales/leads` | 线索列表 |

### 目标用户场景
- **场景 A**：销售要拿到 200 个新线索，行业 + 地域 + 规模筛选。
- **场景 B**：客户来询盘，自动起草报价 + 跟进策略。
- **场景 C**：投放广告优化，多 agent 协商出价 + 创意。

### 核心能力
- 🎣 **线索挖掘**：基于行业 / 招聘 / 工商信号识别潜客
- 💬 **Vibe Selling**：基于客户语境调整销售话术（不死板）
- 📞 **跟进策略**：基于客户阶段推送下一步行动
- 📊 **投放决策**：AI-Trader 范式，多 agent 协商广告策略
- 🎯 **客户分层**：RFM + 行为评分 + 优先级

### 后台调用的 specialized agents
- `sentiment_agent` (客户情绪)
- `consensus_agent` (多 agent 投放决策)
- 自建 `lead_agent` / `vibe_seller` (规划中)

### 调用的 skills
- `sales/lead-mining` · `sales/vibe-selling` · `sales/follow-up`
- `sales/quotation-draft` · `decision/multi-agent-vote`
- `marketing/ad-optimize` · `marketing/audience-target`

### 集成的应用
- Salesforce / HubSpot / Zoho / Pipedrive（CRM）
- 飞书 / 企微（销售跟进）
- LinkedIn Sales Navigator（B2B 线索）
- 巨量引擎 / 腾讯广告（投放）

### 示例对话
**用户**：「客户回了一句『再考虑下』，怎么办？」

**获客猎手**：
> 来看看上下文（已读取该客户 17 条往来记录）：
> - 客户阶段：报价后 第 3 次接触
> - 上次异议：价格高于预算 12%
> - 决策链：技术总监（推荐）+ 采购总监（卡价格）
>
> 「再考虑下」不是拒绝，**80% 概率**是采购在等更好价格。建议：
>
> 1. **不要立刻降价**（会暴露你的底线）
> 2. **创造紧迫感** — 「这周下单可锁定 Q2 产能」
> 3. **绕开采购** — 直接发技术方案给技术总监，让他内部推
> 4. **拆单**：把订单拆成 70% + 30%，先签 70% 试单
>
> 我已起草 3 套话术（保守 / 激进 / 中性），你想用哪个？

---

**用户**：「上个月广告 ROI 不行，看看怎么调」

**获客猎手**：
> 启动 **多 agent 决策**（AI-Trader 范式）：
> - Agent A（保守派）：建议砍 30% 预算 + 调整人群包
> - Agent B（激进派）：建议加 20% 预算 + 换 5 套新创意
> - Agent C（数据派）：分析后建议 — **暂停效果差的 3 个广告组，把预算挪给 Top 2，预计 CTR +18%**
> - 投票结果：3:2 选 Agent C 方案
>
> 已生成执行清单，是否一键应用到投放后台？

---

## 9. ✍️ 内容总监 — 公众号 / 短视频 / 海报  ✅ 已实装

> **一句话**：从一句话灵感到一支成片，全链路内容生产。

**实装状态**：✅ 已实装（P7 commit `8b785a8`）

**实装文件**：
- Persona: [`backend/src/agents/personas/content_director.py`](../../backend/src/agents/personas/content_director.py)
- Models: [`backend/src/agents/personas/content_models.py`](../../backend/src/agents/personas/content_models.py)
- API: [`backend/src/api/routes/persona_content.py`](../../backend/src/api/routes/persona_content.py)

**实际 API endpoints**（前缀 `/api/v3/personas/content`）：
| Method | Path | 用途 |
|---|---|---|
| POST | `/personas/content/wechat-article` | 公众号长文起草 |
| POST | `/personas/content/video-script` | 短视频脚本 + 分镜 |
| POST | `/personas/content/poster-copy` | 海报文案 / 标题矩阵 |
| POST | `/personas/content/brand-check` | 品牌一致性校验 |
| POST | `/personas/content/localize` | 多语言改写 |
| GET  | `/personas/content/brand-profiles` | 列出品牌画像 |
| POST | `/personas/content/brand-profiles` | 新建品牌画像 |

### 目标用户场景
- **场景 A**：老板说「写一篇我们新品发布的公众号」。
- **场景 B**：要做一张活动海报 + 一张朋友圈封面。
- **场景 C**：把一段产品演讲剪成 3 条 30 秒短视频。

### 核心能力
- 📝 **图文创作**：公众号 / 知乎 / 小红书 / 头条 多平台适配
- 🎨 **视觉设计**：海报 / 封面 / Banner（canvas-design）
- 🎬 **短视频脚本 + 成片**：脚本 → 分镜 → Remotion 自动剪辑
- 🌐 **落地页生成**：web-artifacts-builder 一键生成产品页
- 🎙 **文案矩阵**：标题 / 钩子 / 卖点 多版本 A/B

### 后台调用的 specialized agents
- 自建 `content_agent` / `design_agent` / `video_agent` (规划中)
- `evidence_analyst` (素材引用)

### 调用的 skills
- `content/article-write` · `content/headline-generate` · `content/seo`
- `design/poster` · `design/canvas-design` · `design/web-artifacts-builder`
- `content/video-script` · `content/remotion-render`

### 集成的应用
- canvas-design / web-artifacts-builder（cowork-anthropic）
- Figma / Canva / Higgsfield（设计源）
- Remotion（视频）
- 公众号 / 抖音 / 视频号（发布 — 视场景而定）

### 示例对话
**用户**：「写一篇我们新一代精密注塑机发布的公众号，调性专业但不枯燥」

**内容总监**：
> 已读取：
> - 产品 PDF 资料（**市场研究员** 提炼要点）
> - 上周老板演讲录音（**流程管家** 转写）
> - 公司过往公众号 23 篇（学习品牌调性）
>
> 草稿结构（3 版选 1）：
>
> **A. 故事派**「老张的小厂，凭什么干掉日本设备」
> - 钩子：客户故事开篇
> - 5 个产品亮点穿插数据
> - 结尾：CTA「免费打样」
>
> **B. 数据派**「精密注塑误差 ≤ 5μm 是怎么做到的」
> - 钩子：行业痛点 + 数据
> - 技术拆解 + 第三方测试报告
> - 结尾：CTA「白皮书下载」
>
> **C. 行业派**「2026 注塑行业的 3 个变化与我们的应对」
> - 钩子：行业大势
> - 公司布局 + 新品定位
> - 结尾：CTA「行业报告下载」
>
> 选哪版我直接出全文 + 配图。

---

**用户**：「春节活动海报，主题是回家过年送好礼」

**内容总监**：
> 已用 canvas-design 生成 3 个方向：
> - 🧧 中式喜庆：朱红 + 烫金 + 福字纹样
> - 🎄 现代简约：撞色 + 大字报 + 礼盒摄影
> - 🌅 治愈温情：暖光 + 家人剪影 + 手写字
>
> 每个方向 3 个尺寸（朋友圈 / 公众号头图 / 海报 A3），共 9 张。
> [缩略图墙]
>
> 选中后我会输出 PSD 源文件 + Figma 链接。

---

## 10. 🌍 跨境电商助手 — 选品 / 独立站 / 出海全链路  ✅ 已实装

> **一句话**：从想做出海到第一笔订单，每个坑我帮你避。

**实装状态**：✅ 已实装（P7 commit `2624335`，含 AI 议价能力）

**实装文件**：
- Persona: [`backend/src/agents/personas/ecommerce_assistant.py`](../../backend/src/agents/personas/ecommerce_assistant.py)
- Models: [`backend/src/agents/personas/ecommerce_models.py`](../../backend/src/agents/personas/ecommerce_models.py)
- API: [`backend/src/api/routes/persona_ecommerce.py`](../../backend/src/api/routes/persona_ecommerce.py)
- 数据源: [`backend/src/services/fetch/sources/ecommerce/`](../../backend/src/services/fetch/sources/ecommerce/) (shopify 真 + amazon_sp/shopee/tiktok_shop/alibaba_1688 mock)

**实际 API endpoints**（前缀 `/api/v3/personas/ecommerce`）：
| Method | Path | 用途 |
|---|---|---|
| POST | `/personas/ecommerce/analyze-niche` | 选品 / 类目分析（Accio Ecommerce Mind 范式） |
| POST | `/personas/ecommerce/verify-supplier` | 供应商核验 |
| POST | `/personas/ecommerce/negotiate` | AI 议价（多轮策略） |
| POST | `/personas/ecommerce/setup-store` | 独立站搭建（Shopify） |
| POST | `/personas/ecommerce/list-to-platforms` | 多平台 listing 上架 |
| POST | `/personas/ecommerce/vat-guidance` | VAT / 跨境合规指引 |
| GET  | `/personas/ecommerce/dashboard` | 出海运营总览 |

### 目标用户场景
- **场景 A**：制造业老板想做亚马逊 / 独立站，从哪开始？
- **场景 B**：选品 — 用 TikTok 和 Reddit 信号挖掘潜力品类。
- **场景 C**：搭独立站 + 投 Meta 广告 + 接 Shopify 订单的全链路。

### 核心能力
- 🔎 **选品分析**：跨平台数据 + 社媒信号 + 趋势识别（Accio Ecommerce Mind 范式）
- 🏪 **独立站搭建**：Shopify 主题定制 / 商品页 / 落地页
- 📦 **平台接入**：Amazon / Shopee / TikTok Shop / 1688 一站管理
- 💳 **物流 + 收款**：跨境物流方案推荐 + Stripe / PayPal 接入
- 🌐 **海外推广**：Google / Meta / TikTok 广告策略
- 📋 **出海合规**：GDPR / CCPA / VAT / 商标 / 海关

### 后台调用的 specialized agents
- 自建 `ecommerce_agent` / `selection_agent` / `oversea_compliance_agent` (规划中)
- `legal_researcher` (海外法规)
- `risk_assessor` (国别风险)
- `tax_compliance` (跨境税务)

### 调用的 skills
- `ecommerce/product-selection` · `ecommerce/keyword-research`
- `ecommerce/store-setup` · `ecommerce/listing-optimize`
- `ecommerce/oversea-compliance` · `ecommerce/logistics-plan`
- `marketing/ad-optimize` · `decision/multi-agent-vote`

### 集成的应用
- Shopify / Shopee / TikTok Shop / Amazon SP-API / 1688 开放平台
- Stripe / PayPal / 万里汇（收款）
- Meta / Google / TikTok Ads（投放）
- Higgsfield / Canva（素材）

### 示例对话
**用户**：「我们做精密五金的，想做出海，从哪开始？」

**跨境电商助手**：
> 制造业出海 4 个典型路径，按你情况建议：
>
> | 路径 | 启动成本 | 适合情况 | 你的匹配度 |
> |---|---|---|---|
> | Amazon FBA | 中 | 标品 / B2C | 🟡 中（精密五金多 B2B） |
> | **独立站 + Google SEO** | 中 | **B2B 询盘** | 🟢 **高 推荐** |
> | 1688 国际站 | 低 | 试水 | 🟢 高（先开始） |
> | TikTok Shop | 高 | 快消 / 创意品 | 🔴 低（不匹配） |
> |
>
> 建议「**1688 国际站试水（1 个月）+ 独立站长线（3 个月）**」组合。
>
> 我可以拉一个项目，叫上：
> - **市场研究员**：美 / 欧 / 东南亚需求扫描
> - **法律顾问** + **财税顾问**：合规 + 税务
> - **内容总监**：英文产品页 + 营销素材
> - **获客猎手**：Google Ads + LinkedIn outreach
>
> 是否启动「制造业出海评估」项目（DD 期 1 周）？

---

**用户**：「最近 TikTok 上『可折叠桌』很火，要不要选品？」

**跨境电商助手**：
> 启动选品分析（用 Accio Ecommerce Mind 范式）：
>
> ✅ **市场信号**
> - TikTok #FoldableTable 30 天 +218% 播放
> - Amazon 类目 BSR 上升 47%（Garden & Outdoor）
> - Google Trends 北美区热度持续 4 周上扬
>
> 🔴 **风险信号**
> - Top 10 卖家利润率压到 8%（红海化）
> - 专利风险：**XX 公司持有折叠机构专利**（已查 USPTO） → 必须避开
>
> 🟢 **差异化机会**
> - 「带 USB 插座的可折叠桌」搜索量上升但供给少
> - 「碳纤维超轻款」客单价 $200+ 利润空间大
>
> **多 agent 决策结果（投票 3:2）**：建议做差异化款 + 控制首批 ≤ 500 件试水。
>
> 详细 SKU 设计 + 供应链方案 + 上架 listing 我都可以接着做。

---

上次更新：2026-04-27（P0-P7 实际进度同步）
