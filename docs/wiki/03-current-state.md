---
name: 当前状态与下一步
description: 最高频更新的"现在在哪 / 接下来做什么"
audience: AI agents · 每次接手必读
last_updated: 2026-05-14
maintained_by: 每完成一个阶段任务即更新本文
---

# 03 · 当前状态与下一步

> **本文是 Wiki 中最常更新的文件**。新 AI 接手第一件事：读本文，知道现在做什么。

---

## 🎯 当前在哪（2026-05-14）

### 已完成（V3 P0-P7 + Harness H0-O2）

| 域 | 完成度 | 关键文件 |
|---|---|---|
| 后端 API | 61 v3 endpoint ✅ | [backend/src/api/routes/](../../backend/src/api/routes/) |
| 智能体层 | 10 persona + 21 specialized ✅ | [backend/src/agents/](../../backend/src/agents/) |
| 六层 Harness | H0-O2 全部基线 ✅ | [docs/audit/harness/](../audit/harness/) |
| Skills 运行时 | 4 office + watchdog 热加载 ✅ | [skills/](../../skills/) |
| OAuth / IM | 5 provider + 飞书真接入 ✅ | [backend/src/services/im_*.py](../../backend/src/services/) |
| FetchService | 4 层 + 5 法律源 + 5 电商源 ✅ | [backend/src/services/fetch/](../../backend/src/services/) |
| 多模态 RAG | MinerU + KG + VLM ✅ | [backend/src/services/rag/](../../backend/src/services/) |
| 测试 | 543+ pytest / harness 89 ✅ | [backend/tests/](../../backend/tests/) |
| AI Review Gate | 4 reviewer + CODEOWNERS ✅ | [.github/workflows/ai-review.yml](../../.github/workflows/ai-review.yml) |
| 文档规范 | 13 份 standards ✅ | [docs/standards/](../standards/) |

### 进行中 / 待启动

| P 级 | 内容 | 状态 | 阻断 |
|---|---|---|---|
| **P8.A** | 桌面同步引擎 + 签名/公证证据 | 🚧 | 需 Apple Developer / 公证账号 |
| **P8.B** | UI/UX 优化（3 周计划） | 🚧 | [详见 plans/2026-05-13](../plans/2026-05-13-ui-ux-optimization-roadmap.md) |
| **P8.C** | RAG 质量与引用链路 | 🚧 | full50 baseline 缺真实跑通 |
| **P8.D** | 支付 / 电签真实沙箱 | 🚧 | 等沙箱凭证发放 |
| **P9** | 5 法务 persona 上层包装 | 🔜 | 等 P8 体验门槛 |
| **P10** | RAG-Anything 知识库新版 | 🔜 | - |

---

## 🚦 下一步顺序（按优先级）

### P0 — 立即可做（无外部依赖）

1. **图标体系收口** — 80 个文件 `lucide-react` → `@/lib/icons` 迁移
   - 文件清单：grep `from 'lucide-react'` 找
   - 每批 ≤ 20 文件 + 添加 lint `no-direct-lucide-import`
   - 价值：DESIGN.md §4 规则才能生效

2. **Harness P0 followup** — `policy_engine` 主路径接入
   - 当前 `_check_mcp_tool_policy` 已在 `backend/src/agents/base.py`
   - 需要：抽到 `harness/policy_engine.py` 统一收敛
   - 详见 [docs/audit/harness/03-h1-followups.md](../audit/harness/03-h1-followups.md)

3. **Harness P0 followup** — `context_engine` vs `context_compressor` 二选一
   - 当前两套并存
   - 决策依据：哪个被主路径用得更多 + 测试覆盖更全

4. **UI/UX P0** — 假成功修复
   - 详见 [docs/audit/ui-ux-audit-2026-05-08.md](../audit/ui-ux-audit-2026-05-08.md)

### P1 — 等条件就绪可做

1. **peaceful-goodall (CREAO Slice 1) 合并** — 等 P0 policy_engine 落定
2. **cost_tracker 本地 LLM 估算 + 用户配额阻断**
3. **task_engine 扩展到合同/尽调/批量文档**

### P2 — 远期

1. **capability_negotiator 统一桌面/前端/服务**
2. **anxinai.com 域名切换**（P13）

---

## ⚠️ 当前已知阻断

| 阻断 | 影响 | 解除条件 |
|---|---|---|
| Apple Developer 账号未发放 | 桌面签名 / 公证证据缺 | 行政申请通过 |
| 支付/电签沙箱凭证未发放 | live 证据缺 | 渠道方审批 |
| 真机预约未排期 | iOS/Android 真机证据缺 | 行政预约设备 |
| Alembic 双 head | 028/030/044 三 head 风险 | 在 peaceful-goodall 合并时处理 |

---

## 📊 完成度快照（数字）

```
后端 API endpoint:        61/61   ✅ 100%
后端 pytest:              89/89 (harness+chat) + 543 (full)  ✅
前端测试文件:              100+    ✅
Persona 实装（user-facing）: 10/10  ✅
Specialized agent:        21/21   ✅
六层框架（H0-O2 + H1）:    9/9     ✅
Skills 域:                4 office + 5 法律 + 5 电商
文档规范:                 13/13   ✅
品牌一致性:               100%    ✅（本轮收尾）
CAMEL-AI 剥离:            100%    ✅
图标体系一致性:           47%     🚧 (80 文件待迁)
桌面签名:                 0%      🚫 (阻断)
真机证据:                 0%      🚫 (阻断)
支付/电签 live:           0%      🚫 (阻断)
```

---

## 🔄 本轮（2026-05-14）已完成

10 commits ahead of `origin/main`，详见 [PROJECT_STATUS.md](../../PROJECT_STATUS.md)：

1. `57cc290e` 清理 5 处遗留「安心法务」活引用
2. `248735c0` 全量剥离 CAMEL-AI
3. `9d85e0af` 删除 6 个无引用前端页面 + 本地 SQLite
4. `56137019` 引入六层框架基线
5. `9b902494` chat 主路径接 enforcement
6. `bbcb04b6` peaceful-goodall 延后记录
7. `d8c07cf1` 三大单一真相源澄清
8. `fdd060da` 三大核心文档索引
9. `8597b1e2` 残留品牌字符串收口
10. `46ca85a9` 一致性验证 + 交接快照

---

## 📝 更新此文件的触发条件

- ✅ 完成一个 P 级任务
- ✅ 阻断项状态变化
- ✅ 新阻断出现
- ✅ 切换"下一步顺序"

更新方式：直接编辑本文，把 `last_updated` 改为当天日期。
