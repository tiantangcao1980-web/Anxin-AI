# 安心智能助手 · 产品蓝图（2026-05-22）

> 日期：2026-05-22
> 状态：当前权威总体规划（替换早期"全员上 Web"蓝图）
> 适用范围：产品 / 设计 / 前端 / 桌面 / 移动 / 后端 / 运维
> 维护责任：产品 owner，发布前必须复核此文件

---

## 1. 目标重定义

之前的项目把 Web、桌面、移动、小程序四端都按"全功能产品"做，结果信息架构、视觉、功能在四端之间反复漂移。本蓝图把项目重新框定为**飞书 / 企业微信式的"客户端为主、Web 仅作官网与后台"产品形态**。

| 端 | 角色 | 完整度目标 |
|---|---|---|
| 🖥 **桌面客户端**（Tauri 2 + Rust） | **主工作站**（飞书桌面端定位） — 智能体工作台、知识库、本地隐私、远控、长任务时间线 | 商业级 |
| 📱 **移动客户端**（Expo RN） | **随身助手 + 桌面远控**（飞书移动端定位） — 消息 / 任务 / 工作台 / 我 4 tab | 商业级 |
| 🌐 **Web**（React + Vite） | **官网 + 管理后台 + 帮助中心** — 不再承担工作台 | 官网级 |
| 🗨 **小程序 / UniApp** | 轻量入口（扫码登录、消息提醒、远控授权、订阅查询） | MVP |
| ☁️ **后端云服务**（FastAPI） | 三个核心域：`auth` / `user-sync` / `im` + 业务域 API | 商业级 |

> **决策**：Web 端不再承担"日常工作台"，所有 persona / 任务 / 知识库 / 文档协作主入口收敛到桌面 + 移动。Web 上的 `/chat`、`/case-center`、`/management` 等业务路由保留兼容性（重定向到下载页），不再继续投入设计。

---

## 2. 参考产品

| 维度 | 飞书 | 企业微信 | 我们采用 |
|---|---|---|---|
| 桌面布局 | 左侧条 + 频道列表 + 右内容 | 左侧主导航 + 中列表 + 右内容 | **三栏**（左导航条 56px + 中列表 280-320px + 右内容） |
| 移动 tab | 消息 / 文档 / 工作台 / 通讯录 | 消息 / 通讯录 / 工作台 / 我 | **4 tab**：消息 / 任务 / 工作台 / 我 |
| 主色 | #3370FF（蓝） | #2C68FF（蓝） | 保留**琥珀橙 #F97316** 作为 brand，**新增 #1664FF 作为 IM 蓝**（用于消息高亮、链接、信息提示） |
| 圆角 | 6px / 8px / 12px（克制） | 4px / 8px | **8px 卡片 / 12px 弹层 / 16px 大块** —— 比当前 16px/24px 收一档 |
| 字号 | 14px 正文 / 16 标题 / 12 弱 | 14 正文 / 16 标题 | 沿用现有 14/16/20/24/32 层级 |
| 头像 | 圆形 32-40px | 圆形 36px | 圆形 32 / 36 / 40px，统一所有人物 / 智能体头像 |
| 状态色 | 在线圆点 + 文本 | 在线圆点 | 圆点 + 文本 + 颜色三态（在线/忙碌/离线） |
| 长任务 | 飞书 Chat 内 inline 卡片 | — | **长任务时间线**（来自 Codex/Claude 范式） |

> **关键差异**：飞书/企微以 IM 为锚，我们以**智能体工作流 + IM**为锚。所以"消息"tab 同时承载：人和人沟通 / 人和 agent 沟通 / agent 远控授权与状态推送。

---

## 3. 三端 IA（信息架构）

### 3.1 桌面客户端（主工作站）

**外壳**：

```
┌───────┬──────────────────┬─────────────────────────────────┐
│ 左侧条 │ 中列表 / 频道     │ 右侧内容（artifact-first）       │
│  56px │  280-320px       │  自适应                          │
├───────┼──────────────────┼─────────────────────────────────┤
│ 头像    消息列表 / 智能体  │  当前对话 / 任务 / 文档 / 知识图谱  │
│ 消息    任务列表           │                                   │
│ 任务    文档库             │                                   │
│ 工作台   知识库             │                                   │
│ 知识    设置               │                                   │
│ ─────                    │                                   │
│ 设置                     │                                   │
└───────┴──────────────────┴─────────────────────────────────┘
       ↑ 顶部窗口装饰（macOS 红绿黄 / Windows minimize/maximize/close）
       ↓ 底部状态栏（同步状态 + 模式 + 在线状态 + 命令面板入口 Cmd/Ctrl+K）
```

**5 个一级模块**（左侧条）：

| 模块 | 中列表 | 右内容 | 替代当前哪些页面 |
|---|---|---|---|
| 💬 **消息** | 会话列表（人 / agent / 群） | 对话窗 + Artifact 抽屉 | `Chat` `Messages` `IM` |
| ✅ **任务** | 任务列表 + 状态筛选 | 任务详情（步骤/工具/证据/可暂停恢复） | `Tasks` `V3TasksPage` `AgentApprovalWorkspace` |
| 🧰 **工作台** | 10 个 persona | persona 工作台（专属布局） | `PersonaWorkspacePage` 等 |
| 📚 **知识** | 文档库 / 知识图谱 / 智库 | 浏览 / 检索 / 编辑 | `KnowledgeBase` `KnowledgeGraph` `DocumentWorkbench` |
| ⚙️ **设置** | 账号 / 模型 / Skills / MCP / 同步 / 隐私 / 远控 | 设置详情 | `Settings` `PrivateLLMSetup` |

**说明**：
- 当前 frontend 的 52 个页面在桌面端**只暴露 5 个一级 + ~20 个二级**。其余（如`LawyerOnboarding` `FindLawyer` `CaseMarket` `Pricing` `ClientPortal`）从主入口移除，归类为：
  - **官网导流**（移到 Web）：`Pricing` `LawyerOnboarding` `FindLawyer` `CaseMarket` `ClientPortal`
  - **管理后台**（移到 Web `/admin`）：所有 admin/* 页面
  - **彻底废弃**：与"安心法务"律师 SaaS 强耦合的页面，归档到 `docs/archive/`

### 3.2 移动客户端（随身助手 + 远控）

**4 tab**（对齐飞书 / 企微）：

| Tab | 飞书对应 | 我们的内容 |
|---|---|---|
| 💬 **消息** | 消息 | 人 / agent / 群 / 系统通知（含远控授权确认） |
| ✅ **任务** | 文档 | agent 任务列表 + 进度 + 接管 |
| 🧰 **工作台** | 工作台 | 10 personas + 常用 Skills 快捷入口 |
| 👤 **我** | 通讯录 | 账号 / 订阅 / 设置 / 桌面配对状态 |

> 当前 mobile/app/(tabs) 已经是 4 tab（personas / tasks / capabilities / me），改名为 **消息 / 任务 / 工作台 / 我**，并把 `personas.tsx` 重命名为 `workbench.tsx`，把 `capabilities.tsx` 并入"我 → 高级能力"。

### 3.3 Web（官网 + 后台）

**站点结构**：

```
/                官网首页（产品介绍 + 下载入口 + 卖点）
/features        功能介绍
/personas        10 personas 介绍
/pricing         订阅方案
/download        客户端下载（macOS / Windows / Linux / iOS / Android）
/help            帮助中心
/legal/privacy   隐私政策
/legal/terms     用户协议
/login           登录（用于扫码/激活客户端，不做日常工作）
/admin/*         18 页管理后台（保留）
```

**业务路由全部 308 重定向到 `/download` 或 `/help`**：
- `/chat` → `/download?ref=chat`
- `/case-center` → `/download?ref=workbench`
- `/case-market` `/find-lawyer` `/lawyer-*` → 归档到 archive
- `/v3/*` `/agents` `/capabilities/*` → `/download?ref=workbench`
- `/pro/*` 律师 SaaS 子站 → 归档（v1/v2 律师 SaaS 与新定位不一致）

---

## 4. 后端云服务边界

把 74 个路由按**云服务域**收归到 3 个核心 + N 个业务，明确对外契约：

### 4.1 ☁️ Auth Service（注册 / 登录 / 会话 / SSO）

| 能力 | 路由 | 状态 |
|---|---|---|
| 注册（手机号 / 邮箱 / 邀请码） | `POST /auth/register` | ✅ |
| 登录（密码 / 验证码 / OAuth / 二维码） | `POST /auth/login` `POST /auth/qr/*` | ✅ |
| Token 刷新 | `POST /auth/refresh` | ✅ |
| 多设备会话管理 | `GET /auth/sessions` `DELETE /auth/sessions/:id` | 🚧 |
| MFA / 生物识别 | `POST /auth/mfa/*` | 🚧 |
| SSO（飞书 / 钉钉 / 企微 / Google） | `app_authorizations` 系列 | ✅ |
| 设备配对（移动 ↔ 桌面） | `POST /im-pairing/*` | ✅ |

**SLA**：可用性 ≥ 99.9%，p99 < 200ms。  
**安全**：JWT + Refresh，KMS 加密 refresh_token，速率限制 + 验证码挑战。

### 4.2 ☁️ User Sync Service（多设备数据同步）

| 能力 | 路由 | 状态 |
|---|---|---|
| 增量拉 / 推 | `GET/POST /sync/pull` `POST /sync/push` | 🚧（桌面 fail-closed） |
| 冲突解决 | `POST /sync/conflicts/resolve` | 🚧 |
| 设备清单 | `GET /sync/devices` | 🚧 |
| 远控信令 | `POST /im-pairing/control/*` | ✅ |

**契约**：
- 数据按 `entity_type + entity_id + lamport_clock` 同步；
- 桌面端 SQLCipher 本地优先，云端只存"用户允许的"数据（按 mode 决定）；
- 三态：`local` / `hybrid` / `cloud`，桌面 UI 顶部状态栏明示。

### 4.3 ☁️ IM Service（人 / agent / 群 / 远控信令）

| 能力 | 路由 | 状态 |
|---|---|---|
| 会话 / 消息 CRUD | `GET/POST /im/conversations*` | ✅ |
| 在线状态 | `GET /im/presence` `WS /im/ws` | 🚧 |
| 群组 | `POST /im/groups*` | 🚧 |
| Agent 消息渠道 | `services/im_gateway/`（飞书 / 钉钉 / 企微 / Slack / Telegram） | ✅ |
| 远控信令（移动 → 桌面） | `POST /im-pairing/control/exec` | ✅ |
| 音视频（LiveKit） | `POST /rtc/token` | ✅ |

**契约**：
- 协议：WebSocket（推送）+ REST（CRUD）+ 适配器（飞书/钉钉/企微/Slack/Telegram）；
- 消息类型：`text` / `image` / `file` / `task_card` / `artifact_ref` / `control_signal`；
- 在线状态三态：`online` / `busy` / `offline`，agent 单独有 `running` / `paused` / `error`。

### 4.4 业务域 API（保留，但不在云服务核心域）

业务域路由（contracts / cases / leads / due_diligence / esign / payments / billing / persona_* / rag_* / skill_* …）仍由后端提供，但**桌面 / 移动直接调用**，不需要每个端再封装一套客户端。

> 验证：在 IMPLEMENTATION 阶段把 `backend/src/services/` 里所有 `xxx_service.py` 按"云核心 / 业务 / 内部"分组，确保未来可拆出独立微服务。

---

## 5. 清理范围

### 5.1 文档清理

| 类别 | 处置 |
|---|---|
| `docs/v3/` 的 P0-P7 完成报告 | **保留**（追溯历史） |
| `docs/audit/` 的旧 12 域审计 | **保留**，但标记为"截至 2026-05-08 状态"，新计划以本文件为准 |
| `docs/plans/2026-05-09-workstation-admin-ia-boundary.md` | **归档**（被本文件取代） |
| `docs/plans/2026-05-13-ui-ux-optimization-roadmap.md` | **保留**（作为本蓝图的 UX 子计划） |
| `PROJECT_STATUS.md` 73KB 大杂烩 | **拆分**到 `docs/audit/summary.md` + `CHANGELOG.md`，本身归档 |
| `PRODUCT_ROADMAP.md` `ROADMAP.md` 双重路线图 | **合并**到 `docs/v3/roadmap.md`，根目录两份归档 |
| `RESOURCES.md` | **保留**（品牌资源），删除其中"安心法务"残留链接 |

### 5.2 代码清理

| 项 | 处置 |
|---|---|
| `frontend/src/pages/` 的律师 SaaS 残留（`FindLawyer` `CaseMarket` `LawyerOnboarding` `LawyerDashboard` `LawyerProfile` `ClientPortal` `Pricing` `MySubscription`） | Web 端**保留路由但只渲染"下载客户端"占位**，源码归档到 `frontend/src/pages/_legacy/` |
| `frontend/src/components/pro/` 服务方端布局 | **删除**（含 `/pro/*` 路由） |
| `frontend/src/components/a2ui/components/LawyerReferralCard.tsx` 等律师向卡片 | 删除 |
| 旧 `Layout.tsx` + V3 `LayoutV3.tsx` 双布局 | **统一**到 LayoutV3，删除 `VITE_V3_NAV` 开关 |
| `mobile/app/` 下 V2 老 tab（chat / collaboration / investigation / knowledge / profile / index） | **删除文件**（已经 `href: null` 隐藏，无引用即可清） |
| `apps/uni-mobile/` 全栈业务页面 | 收敛为：登录扫码 / 推送接收 / 远控授权 / 订阅查看，移除业务工作台 |
| `mini-program/` Taro | 同 UniApp |
| 各端 design token 漂移（mobile `#D4A574` vs web `#F97316`） | 统一到飞书风新 token，见 DESIGN.md |
| `frontend/src/index.css` 注释里的"安心法务" | 改为"安心智能助手" |
| `backend/src/core/config.py:434` `anxin-fawu.com` | 改为 `anxinai.com` 示例 |

### 5.3 文件/目录清理

| 路径 | 处置 |
|---|---|
| `docs/archive/legacy-root-docs/` 历史日期文档 | 维持归档 |
| `frontend/dist/` `frontend/playwright-report/` | gitignore（如未） |
| `backend/local_test.db` `backend/debug_*.py` | 移到 `backend/scripts/dev/` 或删除 |
| 根目录 `livekit.yaml.example` `.env.nas.example` 等多份 example | 收敛到 `deploy/examples/` |

---

## 6. 里程碑

| 里程碑 | 内容 | 验收 |
|---|---|---|
| **M1 规划与设计**（本周） | 产出 PLAN / DESIGN / IMPLEMENTATION 三文档；冻结飞书风 design token | 文档 review 通过 |
| **M2 清理**（本周末） | 旧品牌残留 0；废弃页面归档；双布局合并；token 漂移 = 0 | grep 检查通过 + 构建通过 |
| **M3 桌面 UI 升级**（次周） | 三栏布局 + 5 一级模块 + 命令面板 + 状态栏 | 桌面真机/打包 runtime 截图 |
| **M4 移动 UI 升级**（次周） | 4 tab 改名 + persona 工作台 + 远控授权 UI | iOS Simulator + Android transcript |
| **M5 Web 瘦身**（次次周） | 官网 + 后台 + 下载页；业务路由全部重定向 | 官网真机访问 + 后台 e2e |
| **M6 后端云服务收口**（次次周） | auth / sync / im 三个 README + OpenAPI 片段；契约测试 | OpenAPI 生成 + 集成测试 |
| **M7 验证 + 上线**（再次周） | `commercial-readiness-gate.sh --quick` 通过；签名包 + 公证；试点 | gate 通过 + 试点账号反馈 |

---

## 7. 不做的事（明确边界）

- ❌ 不再把"Web 工作台"做精，资源全部转到桌面 + 移动
- ❌ 不在本周引入新 UI 库（继续用 shadcn/Radix + Tailwind + lucide-react；Mobile 用现有 RN 样式）
- ❌ 不动律师服务方 SaaS 的旧代码，统一归档而不是重构
- ❌ 不在 UI 升级阶段做新功能，先把现有功能"做对"
- ❌ 不强行 100% 一致：飞书的色板是品牌身份，我们的橙色品牌身份必须保留，蓝色只用作辅助

---

## 8. 关联文档

- 设计规范：[DESIGN.md](../../DESIGN.md)（升级版，含飞书风新增）
- 实施方案：[docs/plans/2026-05-22-implementation-plan.md](2026-05-22-implementation-plan.md)
- UX 子计划：[docs/plans/2026-05-13-ui-ux-optimization-roadmap.md](2026-05-13-ui-ux-optimization-roadmap.md)
- 跨端 token：[docs/design/cross-platform-token-drift.md](../design/cross-platform-token-drift.md)
- 总索引：[docs/00-project-execution-map.md](../00-project-execution-map.md)
