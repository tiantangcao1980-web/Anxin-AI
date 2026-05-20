# 路线图 — 单一真相源

> **状态**：本文是「安心智能助手」路线图的**单一权威来源**。
> **版本**：2026-05-14 · V3 P0-P7 已交付后基线
> **历史来源**：合并自根目录 `ROADMAP.md` + `PRODUCT_ROADMAP.md` + `docs/v3/roadmap.md` + `docs/v3/v3-delivery-summary.md`。原文归档到 [docs/archive/legacy-spine-sources/](archive/legacy-spine-sources/) 与 [docs/archive/legacy-root-roadmaps/](archive/legacy-root-roadmaps/)。
> **更新规则**：P 级推进时更新（预期每 2 周）。当前阻断 / 下一步顺序见 [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)。

---

## 目录

1. [路线图演进历史](#1-路线图演进历史)
2. [V3 阶段目标（P0-P21）](#2-v3-阶段目标p0-p21)
3. [当前完成度快照](#3-当前完成度快照)
4. [全设备交付里程碑](#4-全设备交付里程碑)
5. [风险登记册](#5-风险登记册)
6. [下一步顺序（至 P13）](#6-下一步顺序至-p13)

---

## 1. 路线图演进历史

| 阶段 | 内容 | 状态 | 归档位置 |
|---|---|---|---|
| **v1.0 法务版** | 法律垂直 SaaS（"安心法务"，曾上线 anxinfawu.com） | ✅ 已完成 | [docs/archive/legacy-root-roadmaps/ROADMAP.md](archive/legacy-root-roadmaps/) |
| **v2.0 多端分化** | 桌面 / 移动 / 小程序 / Web 形态分化 | ✅ 已完成 | [docs/archive/legacy-root-roadmaps/PRODUCT_ROADMAP.md](archive/legacy-root-roadmaps/) |
| **V3 智能助手统一** | 全链路升级（"安心智能助手"，目标域名 anxinai.com） | 🚧 P0-P7 ✅；P8-P13 进行中 | 本文 |

详见 ADR：[docs/adr/001-v3-anxin-assistant-upgrade.md](adr/001-v3-anxin-assistant-upgrade.md)。

---

## 2. V3 阶段目标（P0-P21）

V3 共规划 22 个 P 级阶段（P0-P21），覆盖品牌升级 → 主体骨架 → 商业试点 → 生态扩展。

### 2.1 已交付（P0-P7 + Harness H0-O2 ✅）

| P 级 | 内容 | 关键交付 | 状态 |
|---|---|---|---|
| **P0** | 品牌升级 | v1/v2「安心法务」→ V3「安心智能助手」 | ✅ 2026-04-27 |
| **P1** | IA + 后端骨架 | 10 personas 侧边栏 + 后端 3 核心模块 + 6 篇文档 | ✅ |
| **P2** | 异步任务 MVP | `TaskOrchestrator` + Celery + 8 endpoint | ✅ |
| **P3** | IM 通道 + 沙箱 | 飞书真实接入 + 4 占位 + 配对授权 24h + LocalProvider | ✅ |
| **P4** | OAuth 应用授权 | 通用框架 + 5 provider + KMS（Fernet）加密 | ✅ |
| **P5** | Skills 运行时 | `skill_registry` + `skill_executor` + 4 office skill | ✅ |
| **P6** | 信息获取栈 | FetchService 4 层 + 5 法律源 + 5 电商源 | ✅ |
| **P7** | 5 业务 persona | 流程 / 市场 / 获客 / 内容 / 跨境电商 | ✅ |
| **H0** | Harness 接入体检 | [docs/audit/harness/00-integration-matrix.md](audit/harness/00-integration-matrix.md) | ✅ |
| **H1** | enforcement 主路径强制接入 | chat 主路径接 output_validator | ✅ 2026-05-14 |
| **C1** | Context 三层标准化 | AGENTS.md + skills/_template + context-architecture | ✅ |
| **C2** | 5 Agent skill 化 | skills/agents/legal-advisor 完整示范 + 4 骨架 | ✅ |
| **T1** | Trace 落盘 + 聚类 | trace_sink + PII 8 类 scrub + cluster_id | ✅ |
| **T2** | trace → test 转换 | trace_to_test/converter.py | ✅ |
| **E1** | 金标准评测集 | 25 case + 4 维度 + baseline + PR Gate | ✅ |
| **O1** | 4 reviewer PR Gate | ai-review.yml + CODEOWNERS | ✅ |
| **O2** | 自愈闭环 | severity + dispatcher + path safety + cron 骨架 | ✅ |

### 2.2 进行中 / 待启动（P8-P13）

| P 级 | 内容 | 状态 | 阻断 |
|---|---|---|---|
| **P8** | baseline 打磨 + 健康度 + 前端集成 + 文档同步 | 🚧 | 含 UI/UX 3 周计划 |
| **P9** | 5 法务 persona 上层包装（21 specialized agent 已就绪） | 🔜 | 等 P8 体验门槛 |
| **P10** | 知识库新版（RAG-Anything + MinerU 多模态） | 🔜 | - |
| **P11** | 团队协作 / 多租户 / RBAC 可视化 | 🔜 | - |
| **P12** | 5 personas × 三端 E2E 全覆盖 | 🔜 | 等真机 |
| **P13** | 切换到 `anxinai.com` 域名 | 🔜 | DNS / 证书 / OAuth callback 迁移 |

### 2.3 远期规划（P14-P21）

| P 级 | 内容 | 状态 |
|---|---|---|
| **P14** | 桌面 GA（macOS + Windows + Linux 签名 / 公证） | 🔜 |
| **P15** | 安全审计 OWASP + 依赖 + 密钥 + 渗透 | 部分完成（详见 [docs/v3/security-audit.md](archive/legacy-spine-sources/v3/security-audit.md)） |
| **P16** | 依赖升级 + 漏洞修复（含 GHSA-xqmj-j6mv-4862） | 部分完成（CAMEL-AI 剥离已解锁） |
| **P17** | 政府试点 v1.0（高可信门槛全过） | 🔜 |
| **P18** | 中小企业试点 v1.5（合规 + 经营双引擎） | 🔜 |
| **P19** | 律师 / 税务师 / 财务顾问入驻 v2.0 | 🔜 |
| **P20** | 海外市场（跨境电商 + 出海合规深化） | 🔜 |
| **P21** | 智能体生态（第三方 Skill 上架 / 治理） | 🔜 |

---

## 3. 当前完成度快照

### 3.1 数字快照（2026-05-14）

```
V3 阶段：              P0-P7 ✅ (8/22 阶段)
六层框架：             H0-O2 + H1 ✅ (9/9 基线)
后端 API endpoint:     61/61 ✅
后端 pytest:           543+ (89 H1 相关 ✅)
Persona（用户可见）:   10/10 ✅
Specialized agent:     21/21 ✅
Office skill:          4/4 ✅
法律源:                5/5 ✅
电商源:                5/5 ✅
OAuth provider:        5/5 ✅
IM 真接入:             1/5 (飞书 ✅)
文档规范:              13/13 ✅
品牌一致性:            100% ✅
CAMEL-AI 剥离:         100% ✅
图标体系一致性:        47% 🚧 (80 文件待迁)
桌面签名:              0% 🚫 (阻断)
真机证据:              0% 🚫 (阻断)
政务签章接入:          代码 placeholder ✅ / 商务待启动 🟡
支付 / 电签商业化:     0% ⏬ 降为 P3 (PMF 后启动, 2026-05-14 调整)
```

### 3.2 完成度矩阵（按域）

| 域 | 实装 | 测试 | 文档 | 证据 |
|---|---|---|---|---|
| 后端 API | ✅ | ✅ | ✅ | ⚠️ 部分 |
| 智能体层 | ✅ | ✅ | ✅ | ✅ |
| 六层 Harness | ✅ | ✅ | ✅ | ✅ |
| Skills | ✅ | ✅ | ✅ | ✅ |
| OAuth | ✅ | ✅ | ✅ | ⚠️ live 缺 |
| IM | 飞书 ✅ / 4 占位 | ✅ | ✅ | ⚠️ live 缺 |
| FetchService | ✅ | ✅ | ✅ | ✅ |
| RAG | ✅ | ✅ | ✅ | ⚠️ full50 待 |
| Web 前端 | ✅ | ✅ | ✅ | ✅ |
| 桌面 | ✅ | ✅ | ✅ | 🚫 签名缺 |
| 移动 | ✅ | ✅ | ✅ | 🚫 真机缺 |
| 小程序 | ✅ | ✅ | ✅ | ⚠️ smoke 缺 |
| CI / Gate | ✅ | ✅ | ✅ | ✅ |
| 文档规范 | ✅ | n/a | ✅ | ✅ |

---

## 4. 全设备交付里程碑

### 4.1 四个里程碑

```
M1: 桌面 MVP（unsigned + functional）   ← 已达成
   ├ 系统托盘 / 快捷键
   ├ SQLCipher 加密
   └ 本地 / 混合 / 云端三态切换

M2: 桌面正式发布（signed + notarized）  ← 🚫 阻断中（等 Apple Developer）
   ├ macOS 公证
   ├ Windows 代码签名
   └ 自动更新

M3: 移动 / 小程序 GA                    ← 🚧 等真机证据
   ├ iOS App Store
   ├ Android Play Store
   ├ 微信小程序审核
   └ UniApp 跨端验证

M4: 多端闭环（远控 + 数据同步）         ← 🔜 等 M2 + M3
   ├ 桌面 ↔ 移动配对授权
   ├ 跨设备状态同步
   └ 离线缓存与冲突解决
```

### 4.2 当前所处里程碑

**M1 ✅** → 正在冲刺 **M2 + M3**（并行）→ 后达成 M4。

---

## 5. 风险登记册

| ID | 风险 | 影响 | 概率 | 缓解 | 状态 |
|---|---|---|---|---|---|
| R-01 | Apple Developer 账号未批 | M2 阻断 | 中 | 备选 self-host distribution | 🚧 跟踪中 |
| R-02 | 支付/电签商业化沙箱凭证 | 商业化阶段才需, **不再阻断 PMF**; 政务签章 placeholder 已就位 | 中 (从高降级) | 待 PMF 验证后启动 | ⏬ 2026-05-14 降级 |
| R-03 | 真机预约排期 | M3 阻断 | 中 | 提前排期 + 远程真机租赁 | 🚧 跟踪中 |
| R-04 | Alembic 三 head | 数据库迁移路径混乱 | 中 | merge head 在 peaceful-goodall 合并前完成 | 🚧 计划中 |
| R-05 | 图标体系迁移工作量 | UI 一致性 | 低 | 每批 ≤ 20 文件 + lint 强制 | 🚧 进行中 |
| R-06 | RAG full50 baseline 未跑通 | P10 推进受阻 | 中 | 优先级抬升到 P8.C | 🚧 计划中 |
| R-07 | 法务 persona 准确率 | P9 体验风险 | 中 | eval baseline 必跑 + 4 维度门禁 | 🚧 待 P9 |
| R-08 | 政府试点合规审查 | P17 阻断 | 中 | 提前对接合规咨询机构 | 🔜 未启动 |
| R-09 | 中小企业付费意愿 | P18 商业可行性 | 中 | 先 1-2 行业垂直突破（制造业） | 🔜 未启动 |
| R-10 | 第三方 Skill 治理 | P21 生态扩展风险 | 低 | Eval baseline + AI Review Gate 复用 | 🔜 未启动 |

---

## 6. 下一步顺序（至 P13）

### 6.1 P0（立即可做，无外部依赖）

1. **图标体系收口** — 80 文件 `lucide-react` → `@/lib/icons`（每批 ≤ 20 文件）
2. **Harness P0 followup**：
   - `policy_engine` 主路径接入（统一 `_check_mcp_tool_policy`）
   - `context_engine` vs `context_compressor` 二选一
3. **UI/UX P0**：假成功修复（详见 [docs/audit/ui-ux-audit-2026-05-08.md](audit/ui-ux-audit-2026-05-08.md)）

### 6.2 P1（等条件就绪可做）

1. **peaceful-goodall CREAO Slice 1 合并**（alembic head 合并后）
2. **cost_tracker 用户配额阻断**
3. **task_engine 扩展到合同 / 尽调 / 批量文档**

### 6.3 P2（远期）

1. **capability_negotiator 统一桌面 / 前端 / 服务**
2. **anxinai.com 域名切换**（P13）

详细任务表见 [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)。

---

## 附录 · 归档与原文

- **原 ROADMAP.md（根，291 行）**：[docs/archive/legacy-root-roadmaps/ROADMAP.md](archive/legacy-root-roadmaps/ROADMAP.md)
- **原 PRODUCT_ROADMAP.md（根，235 行）**：[docs/archive/legacy-root-roadmaps/PRODUCT_ROADMAP.md](archive/legacy-root-roadmaps/PRODUCT_ROADMAP.md)
- **原 docs/v3/roadmap.md（218 行）**：[docs/archive/legacy-spine-sources/v3/roadmap.md](archive/legacy-spine-sources/v3/roadmap.md)
- **原 docs/v3/v3-delivery-summary.md（269 行）**：[docs/archive/legacy-spine-sources/v3/v3-delivery-summary.md](archive/legacy-spine-sources/v3/v3-delivery-summary.md)

---

> **维护提示**：P 级推进时更新本文 + 同步 [docs/wiki/03-current-state.md](wiki/03-current-state.md)。
