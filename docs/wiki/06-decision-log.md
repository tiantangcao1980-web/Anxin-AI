---
name: 关键决策日志
description: 为什么我们这样设计（按时间倒序）
audience: AI agents · 改设计前必读
last_updated: 2026-05-14
maintainer: 任何架构决策落地时追加
---

# 06 · 关键决策日志

> **格式约定**：按时间**倒序**（最新在最上）。每条决策包含 What / Why / Trade-off / Status。
> **改设计前**：先检查这里有没有相关决策，避免推翻已有共识。

---

## 2026-05-14 · LLM Wiki + Spine 双层文档体系

**What**：建立 `docs/wiki/`（AI 入口，8 文件 < 1500 行）+ `docs/<SPINE>.md`（人类权威，5 份）双层结构。

**Why**：
- 项目文档曾散落在 15+ 子目录、187 个 .md 文件，新成员（人或 AI）找权威文档要 30 分钟
- 多份文档对同一问题各执一词（如 ROADMAP.md vs PRODUCT_ROADMAP.md vs docs/v3/roadmap.md）
- AI 智能体接手成本高，需要"高密度入口"快速识别现状

**Trade-off**：
- ✅ 单一真相源，避免 sync 负担
- ✅ AI 接手 30 秒入手
- ❌ 双层带来"何时更新哪一层"的判断成本（解决：Wiki = 当前状态 / 高频更新；Spine = 长期权威 / 低频更新）
- ❌ 老旧文档归档不能完全删，git 还在追踪历史（接受）

**Status**: ✅ 落地中

---

## 2026-05-14 · 三大单一真相源澄清

**What**：明确 AGENTS.md / DESIGN.md / docs/standards/ 的边界，写入 [docs/standards/README.md](../standards/README.md)。

**Why**：
- 之前 frontend-standard.md 和 DESIGN.md 都谈"图标系统"，互相不引用
- 设计变更时不知道改哪个

**仲裁规则**：
1. **Agent 行为** → AGENTS.md（运行时单一真相源）
2. **视觉 / UI** → DESIGN.md（设计单一真相源）
3. **工程规范** → docs/standards/（13 份分领域规范）
4. 冲突时：AGENTS > DESIGN > standards

**Status**: ✅ 已合并 (`d8c07cf1`)

---

## 2026-05-14 · 六层框架基线引入（Harrison Chase 模型）

**What**：从 `claude/jovial-greider-7843d2` 抽取并适配，把 Agent 拆成 Model / Harness / Context / Traces / Eval / Ops 六个可演化对象。

**Why**：
- 之前 Agent 改造是"横向铺平"（加 persona / 加 skill），没有"纵向能力建设"
- 单元测试覆盖好但 Agent 行为质量没有持续验证
- PR Review 只有 trufflehog，缺业务侧把关

**Trade-off**：
- ✅ Output Validator 从软警告 → CRITICAL 拒发 / FAIL retry
- ✅ Trace 从内存 → 持久化 + PII scrub
- ✅ Eval 从 0 → 25 case + baseline + PR Gate compare
- ✅ PR Review 从 1 → 4 reviewer 并行
- ❌ 引入 9 个新模块，初期可能有遗漏（接受，列入 P0/P1 followups）

**Status**: ✅ H0-O2 + H1 全部基线（commits `56137019` + `9b902494`）。Phase B-G (2026-05-14) 把 P0/P1 followups 全部清零: policy_engine 主路径接入 (T2) + context_engine 收口 (T3) + cost_tracker 配额 (T6) + task_engine 三路径 (T7) + capability_negotiator API 化 (T8) + tool_registry × Skills (T10) + CREAO Slice 1-3 (T5/A3/A9) + Slice 2.5 LLM (G7) + 政务签章 placeholder (F)。

---

## 2026-05-13 · UI/UX 优化 3 周路线图

**What**：[docs/plans/2026-05-13-ui-ux-optimization-roadmap.md](../plans/2026-05-13-ui-ux-optimization-roadmap.md) 把 UI/UX 拆成 5 块（跨端 token / 关键流程闭环 / 三态视觉 / 可信 AI 交互 / 移动专项），3 周完成。

**Why**：P9-P13 都依赖体验门槛，再不修就会带着假成功上线。

**Status**: 🚧 P8.B 进行中

---

## 2026-05-12 · V3 合并进商业交付主线

**What**：把 `v3/main` 分支 161 commits 合并进商业交付集成分支 `integration/v3-merge-20260512`。

**Why**：
- V3 独立演进太久，商业交付 scope 必须扩展为 V3（"安心智能助手"）而非 V2（"安心法务"）
- 合并规模：891 文件 / +132,433 行 / -15,139 行

**Trade-off**：
- ✅ scope 统一
- ❌ 合并冲突 26 个（人工解决）

**Status**: ✅ 合并完成（merge commit `a446429e`）

---

## 2026-05-08 · 全量剥离 CAMEL-AI

**What**：从依赖中移除 `camel-ai`，自研 Harness 层替代。

**Why**：
- CAMEL-AI 锁 `litellm <= 1.83.6`，无法升级修 GHSA-xqmj-j6mv-4862
- CAMEL-AI 实际只用了 ChatAgent + RolePlaying，没用上其他特性
- 自研 Harness 反而更贴合多端 + 多 provider 需求

**Trade-off**：
- ✅ 解锁 litellm 升级
- ✅ Harness 层更贴合业务
- ❌ 失去 CAMEL-AI 生态（接受 — 我们的场景不依赖其 RolePlay 机制）

**Status**: ✅ 已合并 (`248735c0`)。保留 `CamelModel` 向后兼容别名（5 处路由仍在用）。

---

## 2026-04-27 · 品牌升级：安心法务 → 安心智能助手

**What**：v1/v2 是法律垂直 SaaS（"安心法务"，曾上线 anxinfawu.com）。V3 升级为全链路 AI 助手（"安心智能助手"，目标域名 anxinai.com）。

**Why**：
- 法律垂直市场容量小（单价高但用户基数有限）
- 中小企业老板需要"一个 App 搞定所有事"
- V3 已经有 21 个 specialized agent，技术基础足以撑全链路

**Trade-off**：
- ✅ 市场容量扩大（中国中小制造企业 N 千万 vs 法务市场千万级）
- ✅ 复用已有 21 specialized agent
- ❌ 品牌切换成本（涉及全仓 30+ 文件修改 + 旧域名/认证迁移）

**Status**: ✅ V3 P0 已交付。详见 [docs/adr/001-v3-anxin-assistant-upgrade.md](../adr/001-v3-anxin-assistant-upgrade.md)

---

## 早期决策（仅供查阅）

详见 [docs/adr/](../adr/)：
- ADR 001: V3 安心智能助手升级
- ADR 002: 文档与命名标准

---

## 待决策

| 项 | 决策窗口 | 影响 | 负责 |
|---|---|---|---|
| ~~Alembic 三 head 合并策略~~ | ✅ 已决 (T5-prep `045_merge_030_044` + T5 主体 `046_add_incidents_table` + A4 `047_user_token_usage`) | 数据库迁移路径 | — |
| 图标库是否扩展到 lucide 之外 | 已收口 (T1 80 文件 @/lib/icons 统一) | 设计一致性 | DESIGN.md owner |
| ~~context_engine vs context_compressor~~ | ✅ 已决 (T3 收口 + A8 入 harness 命名空间) | Harness 主路径 | — |
| anxinai.com 域名切换时机 | P13 | DNS / 证书 / OAuth callback | 待 P12 后启动 |
| **GDCA 政务签 vs e签宝/法大大** | ✅ 已决 (Phase F 2026-05-14): 政务签优先 (P2), 商业化电签降 P3 等 PMF 后启动 | 签约能力路径 | 业务方推动 GDCA / 粤商通 |
| **UI 三层目录整理 (ui/ + common/ + ui-unified/)** | 下一里程碑 | 组件命名规范 | 待定 |

---

## 如何追加决策

```markdown
## YYYY-MM-DD · 决策标题

**What**: 一句话讲清决策内容

**Why**:
- 痛点 1
- 痛点 2

**Trade-off**:
- ✅ 收益
- ❌ 代价（要明说 — 没有 trade-off 的决策很少存在）

**Status**: ✅ 已落地 / 🚧 进行中 / 📋 计划中
```
