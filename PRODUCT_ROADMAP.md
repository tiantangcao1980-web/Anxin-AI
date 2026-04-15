# 安心 AI 法务 — 多端产品路线图

> 最后更新：2026-04-15
> 负责人：产品 + 工程
> 状态：P0 桌面端 MVP 推进中

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
│  📱 移动端 (Mobile Edition, Tauri iOS/Android)                     │
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

**三种工作模式**（已实现于 `desktop/src/models/`）：
| 模式 | 数据存储 | AI 推理 | 适用场景 |
|------|----------|---------|----------|
| 🔒 绝密模式 | 本地 SQLite | 本地 LLM | 敏感案件、国企法务 |
| 🔄 混合模式 | 本地 + 云端（脱敏）| 云端 LLM | 日常办公（推荐） |
| ☁️ 云端模式 | 云端 | 云端 LLM | 团队协作优先 |

**已完成能力**（截至 2026-04-15）：
- ✅ Tauri v2 架构搭建（`desktop/`）
- ✅ 系统托盘（模式切换、立即同步、退出）
- ✅ 深度链接（`anxin://` 协议）
- ✅ 自动更新（`tauri-plugin-updater`）
- ✅ 本地 SQLite 数据库（`tauri-plugin-sql`）
- ✅ 离线任务队列 + 同步引擎（`desktop/src/services/`）
- ✅ 本地 LLM 集成（`commands/local_llm.rs`）
- ✅ 生物识别认证（`tauri-plugin-biometric`）
- ✅ **全局快捷键 Cmd+Shift+Space**（本次新增）

**待实现 MVP 任务**（优先级递减）：
- [ ] **P0-1**：Tauri 窗口外观优化 — 自定义 macOS 标题栏、去除 Windows 边框、透明毛玻璃效果
- [ ] **P0-2**：全局快捷键呼出后的"快速问答"模式 — 精简输入框，对话完即隐藏
- [ ] **P0-3**：文件拖拽到系统托盘 → 自动分析（合同审查 / 文档摘要）
- [ ] **P1-1**：本地 LLM 模型管理界面（Ollama 集成，一键下载 Qwen/Llama）
- [ ] **P1-2**：原生通知 — 案件进展、风险预警推送
- [ ] **P1-3**：离线模式优化 — 核心功能完全脱网可用
- [ ] **P2-1**：dmg / msi 签名分发
- [ ] **P2-2**：自动更新通道（stable/beta）

---

### 2.3 移动端（P1 推进）

**核心场景**：
- 律师出庭、会见客户、差旅期间的 AI 查询
- 管理者随时查看案件进展、审批状态
- 语音输入 + 拍照识别证据材料

**技术栈**：Tauri iOS/Android + 共享 Web 前端代码 + 移动端专用 UI 壳

**已有配置**：
- ✅ `package.json` 中的 `tauri:android:*` / `tauri:ios:*` 脚本
- ✅ `tauri.conf.json` 支持移动端深度链接

**待实现**：
- [ ] 移动端专用布局（底部 Tab 导航、44px 触摸目标、safe-area）
- [ ] 语音输入集成（浏览器 Web Speech API + 原生 fallback）
- [ ] 拍照识别（原生相机插件）
- [ ] 推送通知（APNs / FCM）
- [ ] App Store / Google Play 上架流程

---

## 3. 阶段性里程碑

### M1（当前 → 4 周后）：桌面端 MVP 发布
- ✅ 设计系统统一（已完成 Batch 1-4）
- ✅ Tauri 全局快捷键（已完成）
- [ ] P0-1 ~ P0-3 完成
- [ ] 内测版 DMG 签名、Windows MSI 打包
- [ ] 50 个种子用户灰度测试

### M2（M1 + 4 周）：桌面端正式发布
- [ ] 官网发布下载页
- [ ] 订阅系统对接
- [ ] 自动更新上线
- [ ] 用户反馈闭环（内嵌反馈面板 → 后端 AIAssistantFeedback）

### M3（M2 + 8 周）：移动端 Beta
- [ ] iOS / Android 移动端 UI 适配
- [ ] TestFlight / 应用宝 Beta
- [ ] 核心场景（AI 查询、案件查看、消息）

### M4（M3 + 4 周）：多端闭环
- [ ] 三端数据实时同步
- [ ] 跨设备会话继续（桌面开始 → 手机继续）
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
