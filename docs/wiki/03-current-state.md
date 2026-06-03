---
name: 当前状态与下一步
description: 最高频更新的"现在在哪 / 接下来做什么"
audience: AI agents · 每次接手必读
last_updated: 2026-05-14 (Phase F + Gate 调整)
maintained_by: 每完成一个阶段任务即更新本文
---

# 03 · 当前状态与下一步

> **本文是 Wiki 中最常更新的文件**。新 AI 接手第一件事：读本文，知道现在做什么。

---

## 🎯 当前在哪（2026-05-14, Phase A-F + Gate 调整全部落地）

### Phase B-F 累计交付（48 commit, 领先 main 48）

| Phase | 内容 | 状态 |
|---|---|---|
| **Phase A** | 文档单一信源化 (170+→5 Spine + 9 Wiki + 101 归档) | ✅ |
| **Phase B** | T1-T10 P0-P2 (图标 / policy_engine / context_engine / cost_tracker / task_engine / capability / Skills) | ✅ |
| **Phase C** | A1-A10 优化批 (ModeGate 实战 / build chunk / CREAO Slice 1-3 / Tauri command 等) | ✅ |
| **Phase D** | E1-E8 卫生批 (incident 注入 / fail-closed / cron / Skill runtime gate / mypy 严检) | ✅ |
| **Phase E** | G1-G7 技术债清零 (trace_id / watchdog / /pro routes / 测试隔离 / mypy 历史债 / 移动卡片 / Slice 2.5 LLM) | ✅ |
| **Phase F** | 产品方向调整 — 签约/支付降 P3, 政务签章 (GDCA/粤企签) placeholder + gate deferred status | ✅ |

### 完整模块清单

| 域 | 完成度 | 关键文件 |
|---|---|---|
| 后端 API | 61 v3 endpoint ✅ | [backend/src/api/routes/](../../backend/src/api/routes/) |
| 智能体层 | 10 persona + 21 specialized ✅ | [backend/src/agents/](../../backend/src/agents/) |
| **六层 Harness + Phase B/C 新增 6 模块** | 14 个 ✅ (含 incident_collector / incident_hook / triage_service / builder_service / context_compressor 入 harness / 政务 esign provider placeholder) | [docs/audit/harness/](../audit/harness/) |
| **CREAO 自愈闭环** | Slice 1 + 2 + 2.5 + 3 全栈 ✅ | [backend/src/harness/triage_service.py](../../backend/src/harness/triage_service.py), [builder_service.py](../../backend/src/harness/builder_service.py) |
| Skills 运行时 | 4 office + watchdog 热加载 + **required_tools runtime gate (E5)** ✅ | [skills/](../../skills/) |
| OAuth / IM | 5 provider + 飞书真接入 ✅ | [backend/src/services/im_*.py](../../backend/src/services/) |
| FetchService | 4 层 + 5 法律源 + 5 电商源 ✅ | [backend/src/services/fetch/](../../backend/src/services/) |
| 多模态 RAG | MinerU + KG + VLM ✅ | [backend/src/services/rag/](../../backend/src/services/) |
| **测试** | **pytest 1866/1866** ✅ (从 1847 + 4 failed → 1866 + 0 failed) | [backend/tests/](../../backend/tests/) |
| **mypy** | harness/services 主要模块 **0 errors** ✅ (从 31 → 0) | — |
| AI Review Gate | 4 reviewer + CODEOWNERS ✅ | [.github/workflows/ai-review.yml](../../.github/workflows/ai-review.yml) |
| 文档规范 | 13 份 standards ✅ | [docs/standards/](../standards/) |
| **政务签章** | GDCA + 粤企签 Provider 框架占位🟡（未接入·调用即 raise ESignProviderConfigError，待商务对接凭据） | [backend/src/services/esign_service.py](../../backend/src/services/esign_service.py), [docs/integrations/guangdong-gov-signature.md](../integrations/guangdong-gov-signature.md) |

### 进行中 / 仍需推进

| P 级 | 内容 | 状态 | 阻断 |
|---|---|---|---|
| **P8.A** | 桌面签名/公证证据 | 🚫 外部 | Apple Developer 账号 / Windows 签名证书 |
| **P8.B** | UI/UX 优化 (4 项 P0 已完成本会话) | 🚧 持续 | 移动响应式/a11y/token 已加固; UI 三层目录整理仍待 |
| **P8.C** | RAG full50 baseline | 🚫 外部 | corpus 50 份样本文档准备 |
| **P8.D** | 政务签章接入 (仅框架占位🟡, 未接入, 商务待启) | 🟡 商务推动 | GDCA NDA + 粤商通入驻 |
| **P8.D'** | 商业化支付/电签 | ⏬ **降 P3** (2026-05-14) | PMF 验证后启动 |
| **P9** | 5 法务 persona | ✅ | — (复核完成) |
| **P10** | RAG-Anything 知识库新版 | 🚧 持续 | — |
| **P11/P12/P13** | RBAC / 三端 E2E / anxinai 域名 | 🔜 远期 | 客户进场 / B 档资源 / DNS |

---

## 🚦 下一步顺序（按优先级，已重排）

### 业务方推动（不阻断当前 PMF 验证）

1. **GDCA 政务签 商务对接** — NDA + 商务合同 + 测试凭据 (2-4 周)
2. **粤商通企业实名入驻** — 法人代表认证 + 开发者权限申请 (2-4 周)
3. **Apple Developer 账号 / Windows 代码签名证书** — 桌面发布前必须
4. **真机预约 (iOS + Android)** — P12 三端 E2E 前置

### 工程层仍可推进 (剩余技术债)

1. **UI 三层目录整理** — `components/ui/` + `common/` + `ui-unified/` 三套并存, 立 ADR 收敛
2. **page=tab 子组件迁移** — `Cases.tsx` 等 tab 内容子组件命名误导, 迁到 `components/case-management/`
3. **cost_tracker 真 write-through** — 当前 5min flush + restore 可用, 极端高并发场景可升 Redis ZADD
4. **审批 UX 链路** — REQUIRE_APPROVAL → 工单 → chat unblock 完整 UX
5. **i18n** — 全站国际化 (战略级别, 短期不必)

### 真 PMF 验证维度 (产品验收)

- Agent 主路径用户体验 (chat 流程 / persona 切换 / 推理引用)
- RAG 引用链路 UI (citation chip / 跳转)
- 协作编辑空状态 / 错误态
- 多端体验一致性 (Web / Desktop / Mobile)
- CREAO 自愈数据流真实触发 (incidents → triage → builder 整个链路在生产环境跑出第一条 GitHub Issue 草稿)

---

## ⚠️ 当前已知阻断（已大幅缩减）

| 阻断 | 影响 | 解除条件 |
|---|---|---|
| Apple Developer 账号未发放 | 桌面签名 / 公证证据缺 | 行政申请通过 (P0) |
| Windows 代码签名证书未发放 | Windows 发布阻断 | 证书申请 (P0) |
| GDCA 政务签 商务未启动 | 政务签章接入空白 | 业务方 NDA + 商务对接 (P2) |
| 粤商通企业入驻未启动 | 中小企政务签约空白 | 法人认证 + 开发者权限 (P2) |
| 真机预约未排期 | iOS/Android 真机 transcript 缺 | 行政预约设备 (P1) |
| RAG full50 corpus | full50 baseline 跑不通 | corpus 准备 (P2) |
| ~~Alembic 双 head~~ | ~~阻断新 migration~~ | ✅ Phase A T5-prep 合并 + Phase F 同步 |
| ~~支付/电签沙箱凭证~~ | ~~live 证据~~ | ⏬ **Phase F 已降为 P3** (PMF 后启动) |

---

## 📊 完成度快照（数字, 2026-05-14 终极）

```
后端 API endpoint:        61/61   ✅ 100%
后端 pytest:              1866/1866 ✅ 100% (从 89/89+543 起累计扩展)
后端 mypy 主要模块:        0 errors ✅ (harness/services 严检)
前端测试文件:              100+    ✅
前端 lint:                零错误  ✅
前端 tsc / build:          clean / 10.59s ✅
桌面 Rust cargo check:    通过 ✅
alembic head:             单一 head (047_user_token_usage) ✅
Persona 实装:             10/10   ✅
六层框架:                 14 个模块 ✅ (六层 + 8 个 Phase B/C 新增)
CREAO 自愈闭环:           Slice 1+2+2.5+3 全栈 ✅
Skills 域:                4 office + 5 法律 + 5 电商
文档规范:                 13/13   ✅
品牌一致性:               100%    ✅
图标体系一致性:           100%    ✅ (Phase B T1 收口 + ESLint 防回归)
政务签章框架占位:        2 渠道占位 (GDCA + 粤企签) 🟡 未接入·调用即 raise，待商务对接凭据
桌面签名:                 0%      🚫 (Apple Developer 阻断)
真机证据:                 0%      🚫 (设备阻断)
商业化支付/电签:           Phase F 降为 P3 ⏬ (PMF 后)
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
