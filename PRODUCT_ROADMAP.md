# 安心 AI 法务 — 多端产品路线图

> 最后更新：2026-05-09
> 负责人：产品 + 工程
> 状态：桌面端代码级 MVP 与本地门禁推进中；商业发布仍缺签名/真机/外部 API 证据

---

## 1. 产品定位

**一句话定位**：一款面向律师与法务团队的"AI 法务助手"，以对话为核心入口，覆盖合同审查、合规自检、案件管理、知识检索、证据梳理与律师协作的全流程。

**差异点**：
- 区别于通用 AI（Claude、ChatGPT）— 内置法务专业提示、法规知识库、法律文书模板
- 区别于传统 SaaS 法务（律盾、法大大）— AI 原生交互、桌面常驻、本地增强
- 区别于个人 AI 工具（ClawX、Qclaw）— 场景专业化、结构化业务流、团队协作

**对标产品**：
- **桌面交互形态**：Claude Desktop、ClawX、Qclaw
- **业务深度**：法大大、律盾、Thomson Reuters Westlaw
- **AI 原生理念**：Notion AI、Cursor、Codex

---

## 2. 三端分工

```
┌──────────────────────────────────────────────────────────────────┐
│                         安心 AI 法务 产品矩阵                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🌐 Web 版 (Cloud Edition)                                        │
│     - 产品官网 + 定价 + 订阅 + 计费                                 │
│     - 完整业务功能（Chat/案件/合同/图谱/协作/律师匹配）                │
│     - 云端知识库 + 多人协作 + 数据同步                              │
│     - 目标用户：企业用户、律所、新客户首次体验                         │
│                                                                  │
│  💻 桌面端 (Desktop Edition, Tauri)                                │
│     - 系统托盘常驻 + Cmd+Shift+Space 全局呼出                       │
│     - AI 对话快捷入口（类 ClawX/Spotlight 风格）                    │
│     - 本地文档审查（合同拖入即析）                                    │
│     - 三种模式：绝密本地 / 混合 / 云端                                │
│     - 本地 LLM 集成（私有化场景）                                    │
│     - 目标用户：日常重度使用的律师、企业法务                           │
│                                                                  │
│  📱 移动端/小程序 (Mobile + Mini Program, uni-app)                  │
│     - 外出办公场景（出庭/会见/差旅）                                  │
│     - 快速 AI 咨询 + 案件状态查看 + 消息审批                          │
│     - 语音输入 + 拍照识别                                           │
│     - 目标用户：移动办公的律师、法务总监                              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 2.1 Web 版定位（现有）

**核心场景**：
- 新用户了解产品、试用、订阅
- 企业账户管理、席位分配、计费中心
- 团队协作场景（多人编辑合同、案件分配、审批流）
- 完整业务管理（案件中心、管理中心、知识图谱、舆情监测）

**技术栈**：React + TypeScript + Vite + TailwindCSS + FastAPI

**部署**：Docker Compose / Kubernetes / 静态托管

---

### 2.2 桌面端（当前 P0 优先）

**核心场景**：
- 日常 AI 法务咨询（呼出即用，不打断当前工作流）
- 合同拖入即审查（利用桌面原生文件拖拽）
- 本地文档管理（离线、隐私敏感场景）
- 系统托盘常驻，未读消息提醒

**技术栈**：Tauri v2 + Rust + 共享 Web 前端代码

**三种工作模式**（桌面端已有 secret-free runtime config + 前端 PrivacyContext 对齐；signed runtime 证据待补）：
| 模式 | 数据存储 | AI 推理 | 适用场景 |
|------|----------|---------|----------|
| 🔒 绝密模式 | 本地 SQLite | 本地 LLM | 敏感案件、国企法务 |
| 🔄 混合模式 | 本地 + 云端（脱敏）| 云端 LLM | 日常办公（推荐） |
| ☁️ 云端模式 | 云端 | 云端 LLM | 团队协作优先 |

**当前代码级能力**（截至 2026-05-09；不等于商业发布完成）：
- ✅ Tauri v2 架构搭建（`desktop/`）
- ✅ 系统托盘（模式切换、立即同步、退出）
- ✅ 深度链接（`anxin://` 协议）
- ⏳ 自动更新（`tauri-plugin-updater`；商业自动更新通道需签名/发布证据）
- ✅/⏳ 本地 SQLCipher 数据库（Rust-owned SQLCipher/keyring、本地/unsigned release smoke 已有；signed packaged-profile 证据待补）
- ✅/⏳ 离线任务队列 + 同步引擎（代码级、unsigned packaged loopback、跨设备续接 rehearsal 已有；shared-staging/signed runtime 证据待补）
- ✅ 本地 LLM 集成（`commands/local_llm.rs`）
- ✅ 生物识别认证（`tauri-plugin-biometric`）
- ✅/⏳ **全局快捷键 Cmd+Shift+Space + Quick Query 独立窗口**（代码/浏览器证据已有；packaged 200ms 和真实本地模型 smoke 待补）

**信息架构边界**（避免本机运行与治理后台冗余）：
- 本机运行只处理“我这台设备如何运行”：本机模式、后端地址、本地模型默认项、本机通知、离线队列和只读状态探针。
- 治理后台只处理“组织/平台如何治理”：用户角色、组织、安全审计、系统集成、模型治理、计费和发布运维。
- 若底层复用同一 API/组件，界面文案必须标明作用域；本机运行不承载组织级凭据治理，治理后台不承载本机运行模式切换。

**MVP 发布剩余任务**（优先级递减）：
- [~] **P0-1**：Tauri 窗口外观优化 — 代码级 chrome/titlebar gate 已有；macOS/Windows 截图、vibrancy/acrylic 视觉验收和 signed runtime 待补
- [~] **P0-2**：全局快捷键呼出后的"快速问答"模式 — 独立 Quick Query 窗口已实现；packaged 快捷键实测、P95 < 200ms 和真实 local model smoke 待补
- [~] **P0-3**：文件拖拽分析 — WebView drop + SQLCipher offline queue + redacted toast 已实现；真实托盘图标 drop、P95 < 500ms 和 signed runtime 待补
- [~] **P1-1**：本地 LLM 模型管理界面 — 本机运行已补默认本地模型选择、Ollama/兼容端点模型清单、secret-free 持久化和 Quick Query 默认模型读取；一键下载、真实模型 smoke 和 packaged runtime 证据待补
- [~] **P1-2**：原生通知 — 桌面端已补本机 OS 通知 IPC、权限状态/授权请求 IPC、本机运行测试通知、TopSecret local-only 边界和门禁覆盖；真实 signed runtime 系统偏好权限、托盘/后台触发、跨设备/服务端推送证据待补
- [~] **P1-3**：离线模式优化 — 已补本机离线队列列表、失败任务重新入队、文件路径脱敏摘要和本地门禁；完全脱网业务闭环、shared-staging 同步和 signed runtime 证据待补
- [ ] **P2-1**：dmg / msi 签名分发（Apple Developer ID / notarization / Windows certificate 外部输入）
- [ ] **P2-2**：自动更新通道（stable/beta，需签名产物与灰度记录）

---

### 2.3 移动端/小程序（桌面收口后按 uni-app 推进）

**核心场景**：
- 律师出庭、会见客户、差旅期间的 AI 查询
- 管理者随时查看案件进展、审批状态
- 语音输入 + 拍照识别证据材料

**技术栈**：uni-app + TypeScript。旧 `mobile/` Expo 与 `mini-program/` Taro 目录保留为 legacy/回归参考，后续新移动能力优先进入 `apps/uni-mobile/`。

**已有代码级基座**：
- ✅ `apps/uni-mobile/` 首版基座：typecheck、契约测试、H5 build、WeChat Mini Program build 已通过
- ✅ legacy mobile/mini 本地 smoke、fake fallback guard、隐私模式 no-network guard 已有
- ✅ cross-device continuation code rehearsal 已证明后端/桌面 adapter/uni-app sync client 的代码级续接
- ⏳ DCloud App 云打包/签名、真实 iOS/Android、交互式微信开发者工具和共享预发账号跨设备连续会话仍待补

**待实现**：
- [ ] uni-app 移动端专用布局（底部 Tab 导航、44px 触摸目标、safe-area）
- [ ] 语音输入集成（浏览器 Web Speech API + 原生 fallback）
- [ ] 拍照识别（原生相机插件）
- [ ] 推送通知（APNs / FCM）
- [ ] DCloud App 云打包 / iOS TestFlight / Android 渠道 / 微信小程序体验版验收

---

## 3. 阶段性里程碑

### M1（当前 → 4 周后）：桌面端 MVP 发布
- ✅ 设计系统统一（已完成 Batch 1-4）
- ✅ Tauri 全局快捷键 + Quick Query 代码级链路（已完成，packaged 性能待补）
- ✅/⏳ P0-1 ~ P0-3 代码级和本地门禁已推进；signed runtime、平台手测、性能证据待补
- [ ] 内测版 DMG 签名、公证、Windows MSI 打包/签名
- [ ] 50 个种子用户灰度测试

### M2（M1 + 4 周）：桌面端正式发布
- [ ] 官网发布下载页
- [ ] 订阅系统对接
- [ ] 自动更新上线
- [ ] 用户反馈闭环（内嵌反馈面板 → 后端 AIAssistantFeedback）

### M3（M2 + 8 周）：uni-app 移动端/小程序 Beta
- [ ] uni-app iOS / Android / H5 / 微信小程序 UI 适配
- [ ] DCloud 云打包、TestFlight、Android 渠道和微信体验版
- [ ] 核心场景（AI 查询、案件查看、消息、桌面续接）

### M4（M3 + 4 周）：多端闭环
- [ ] 三端数据实时同步
- [ ] 跨设备会话继续（桌面开始 → 手机继续；当前只有代码级 rehearsal，缺 signed/shared-staging/真机证据）
- [ ] 企业版功能（团队订阅、席位管理、审计日志）

---

## 4. 设计系统跨平台一致性

**唯一真相源**：`frontend/src/lib/design-tokens.ts` + `DESIGN.md`

**跨平台策略**：
```
design-tokens.ts
  ↓
┌─────────────┬──────────────┬──────────────┐
│    Web      │   Desktop    │    Mobile    │
│ Tailwind    │ Tailwind +   │ Tailwind +   │
│ (full)      │ DesktopShell │ MobileShell  │
│             │ adaptations  │ adaptations  │
└─────────────┴──────────────┴──────────────┘
```

**平台差异化适配**：
- **Web**：标准 spacing、桌面级信息密度、鼠标交互优先
- **Desktop**：更紧凑的 padding（节省窗口空间）、自定义标题栏、全局快捷键反馈
- **Mobile**：更大 touch target（≥44px）、底部导航、safe-area-inset、单手可达

---

## 5. 本次 UI 治理成果（2026-04-15）

### 已完成工作
- ✅ **heading token** 对齐 DESIGN.md 精确规范（text-h1/h2/h3）
- ✅ **CenterLayout** 统一组件新建（CaseCenter、ManagementCenter）
- ✅ **PageContainer** 新增 `embedded` prop 解决嵌套标题重复
- ✅ **EmptyState / LoadingState / ErrorState** 三组统一状态组件
- ✅ **92% 页面** 使用标准布局容器（PageContainer / CenterLayout）
- ✅ **硬编码颜色类** 从 572 清零至 0
- ✅ **硬编码 padding** 从 34 清零至 0
- ✅ **tracking-wide/wider** 从 15 清零至 0
- ✅ **font-bold / semibold** 从 184/260 降至 92/91（合理数据值保留）
- ✅ **Tauri 全局快捷键** Cmd+Shift+Space 注册

### 设计系统健康度
- **Before**：B+ (81/100)
- **After**：**A (95+/100)**

---

## 6. 风险与对齐

### 技术风险
- **Tauri 2 生态成熟度**：部分插件（如 biometric）仍在演进，需关注 breaking change
- **macOS 公证**：分发需 Apple Developer ID，流程配置完成（`Entitlements.plist`）
- **Windows 代码签名**：需 EV 证书，否则 SmartScreen 警告

### 产品风险
- **三端维护成本**：共享前端代码降低风险，但平台差异化代码需严格守护
- **用户期望对齐**：桌面端是否作为"主要产品"还是"辅助工具"需产品团队决策

### 对齐事项
- 桌面端是否内置完整业务功能（案件/合同/协作）还是仅 AI 对话 + 文档分析？
- 移动端是否支持离线（复用桌面端同步引擎）？
- 订阅体系是否统一三端（Web 付费 → Desktop/Mobile 自动解锁）？

---

## 7. 参考资料

- 设计规范：`DESIGN.md`
- 前端治理执行计划：`docs/frontend-design-execution-plan.md`
- Tauri 文档：https://v2.tauri.app
- 对标产品：ClawX、Qclaw、Claude Desktop、Cursor、Codex
