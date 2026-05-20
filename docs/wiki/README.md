---
name: LLM Wiki 入口
description: 为接手项目的 AI 智能体设计的 30 秒上手入口
audience: AI agents / new contributors
last_updated: 2026-05-14
---

# 安心智能助手 LLM Wiki

> **给 AI 智能体的项目接手指南**。读完本文 30 秒可回答：这是什么？现在到哪一步？接下来做什么？

---

## 🚀 30 秒速识

| 维度 | 答案 |
|---|---|
| **项目名** | 安心智能助手 / Anxin AI |
| **域名** | anxinai.com（目标）· anxinfawu.com（v1/v2 历史） |
| **定位** | 面向中国成长型制造企业（中小为主）的全链路 AI 经营助理 |
| **范围** | 法务 / 财税 / 合规 / 经营 / 调研获客 / 内容产出 / 出海跨境 — 一站式 |
| **形态** | 桌面工作站（Tauri 2）+ 移动 / 小程序（Expo·Taro·UniApp）+ Web（React 18）+ API（FastAPI） |
| **阶段** | V3 P0-P7 ✅ 已交付；P8-P13 🚧 进行中；下一里程碑：商业试点（政府/中小企业） |
| **代码量** | ~5500 文件 / 后端 543+ pytest / 前端 100+ 测试文件 / 22 个 Agent persona / 21 specialized agent |
| **6 层框架** | Model / Harness / Context / Traces / Eval / Ops — H0-O2 全部基线 ✅ |

---

## 📚 Wiki 文件索引（按读取顺序）

| # | 文件 | 用途 | 何时读 |
|---|---|---|---|
| 1 | [01-project-snapshot.md](01-project-snapshot.md) | 一页项目快照（What / Why / Who） | 第一次接手 |
| 2 | [02-quick-context.md](02-quick-context.md) | 给 LLM 的最小上下文（核心概念 + 文件位置） | 想"快速干活"时 |
| 3 | [03-current-state.md](03-current-state.md) | 当前进度与下一步（最常更新） | 每次接手必读 |
| 4 | [04-architecture-map.md](04-architecture-map.md) | 架构地图 + 关键文件路径 | 写代码前 |
| 5 | [05-domain-glossary.md](05-domain-glossary.md) | 业务/技术术语表 | 看到不认识的名词时 |
| 6 | [06-decision-log.md](06-decision-log.md) | 关键决策日志（why we chose X） | 改设计前 |
| 7 | [07-common-pitfalls.md](07-common-pitfalls.md) | 常见陷阱（don't do X） | 提交前 |
| 8 | [08-ai-onboarding-flow.md](08-ai-onboarding-flow.md) | 新 AI 的 5 步上手流程 | 不知从哪开始时 |

---

## 🔗 与 Spine 文档的关系

LLM Wiki **不**取代权威 Spine 文档；它是**高密度入口**：

```
Wiki（短、给 AI）→ 指向 → Spine（长、给人 / 权威）→ 指向 → 源码
```

| Spine（权威长文） | Wiki 对应入口 |
|---|---|
| [docs/REQUIREMENTS.md](../REQUIREMENTS.md) | [01-project-snapshot](01-project-snapshot.md) + [05-domain-glossary](05-domain-glossary.md) |
| [docs/ARCHITECTURE.md](../ARCHITECTURE.md) | [04-architecture-map](04-architecture-map.md) |
| [docs/ROADMAP.md](../ROADMAP.md) | [03-current-state](03-current-state.md) |
| [docs/DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) | [03-current-state](03-current-state.md) + [08-ai-onboarding-flow](08-ai-onboarding-flow.md) |
| [docs/RELEASE_GATE.md](../RELEASE_GATE.md) | [07-common-pitfalls](07-common-pitfalls.md) |

---

## ⚡ AI 接手最快路径

```
1. 读本文（30s）               → 知道在哪
2. 读 03-current-state（1min）  → 知道现在做什么
3. 读 08-ai-onboarding-flow     → 知道下一步具体怎么动手
4. 按需跳 Spine / 源码          → 写代码
```

---

## 📝 维护规则（给 AI 自己）

- **本目录 8 个文件总行数 < 1500 行**，超出说明在堆积冗余，需重构
- **任何长内容都放 Spine**，Wiki 只放"高密度结论 + 锚点"
- **每个 commit 修改超过 3 个领域代码时**，更新 [03-current-state.md](03-current-state.md)
- **关键架构决策**：记录到 [06-decision-log.md](06-decision-log.md)（按时间倒序）
- **遇到坑/教训**：记录到 [07-common-pitfalls.md](07-common-pitfalls.md)

> **本 Wiki 是给 AI 看的**，所以可以使用术语缩写、表格、清单 — 不需要人类自然语言展开。
