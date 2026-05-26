# 桌面端独立安装 / 首启体验 / LLM 配置方案（2026-05-22）

> 日期：2026-05-22
> 配套：[产品蓝图 §3.1](2026-05-22-product-blueprint.md) · [实施方案 L3](2026-05-22-implementation-plan.md) · [DESIGN.md §10](../../DESIGN.md)
> 适用范围：桌面客户端（Tauri 2 + Rust）的分发、安装、首次启动、LLM 配置
> 权威级别：⭐⭐⭐ 桌面分发与首启体验权威

---

## 1. 目标

把桌面端做成"**装上就能用**的本地优先 AI 助手"，对齐飞书 / 企微的开箱体验：

1. **独立安装包**：macOS dmg / Windows exe (NSIS) / Linux deb + AppImage，单文件双击安装，**不依赖外部 Docker / Python / Node**
2. **运行环境集成**：内置必要服务（SQLCipher / keyring / 可选嵌入式后端），首启自动初始化
3. **LLM 配置可自定义**：支持 OpenAI / Anthropic / 通义 / DeepSeek / 混元 / Ollama（本地）/ LMStudio（本地）等 provider；用户可填 API key 或选本地模型
4. **未配置 → 强提示**：首启检测无可用 LLM 时，触发 OnboardingWizard 的 LLM 配置步骤；运行时检测则在顶部挂"未配置 LLM"横幅 + 进入 chat 时弹引导
5. **首次引导页**：4 步 wizard — 欢迎 → 隐私模式 → LLM 配置 → 完成；持久化到本地，二次启动不再弹

---

## 2. 分发矩阵

| 平台 | 包格式 | Tauri target | 签名要求 | 安装位置 |
|---|---|---|---|---|
| macOS Intel | `.dmg` + `.app` | `x86_64-apple-darwin` | Apple Developer ID + notarization | `/Applications/安心智能助手.app` |
| macOS Apple Silicon | `.dmg` + `.app` | `aarch64-apple-darwin` | 同上 | 同上 |
| Windows 10/11 x64 | `.msi`（默认）+ `.exe`（可选 NSIS） | `x86_64-pc-windows-msvc` | EV / Standard Code Signing Cert | `C:\Program Files\安心智能助手\` |
| Linux x64 | `.deb` + `.AppImage` | `x86_64-unknown-linux-gnu` | 可选 GPG | `/opt/anxin-assistant/` |

**当前状态**：`desktop/tauri.conf.json` 已配 `"targets": "all"`，`desktop-release-package.sh` 支持 `app,dmg` bundle 模式。需要补：

- [ ] Windows MSI / NSIS 打包脚本
- [ ] Linux AppImage 配置
- [ ] Tauri `updater.endpoints` 从 `https://api.anxin-legal.com` 改为 `https://api.anxinai.com`
- [ ] Tauri `updater.pubkey` 配置（生成 + 入 secret store）

---

## 3. 运行环境集成

### 3.1 内嵌依赖（已就绪）

| 能力 | 实现 | 状态 |
|---|---|---|
| 本地 SQLCipher | `rusqlite = { features = ["bundled-sqlcipher-vendored-openssl"] }` | ✅ |
| 系统 keyring | `keyring = { features = ["apple-native", "windows-native", "sync-secret-service"] }` | ✅ |
| 全局快捷键 | `tauri-plugin-global-shortcut` | ✅ |
| 生物识别（Touch ID / Windows Hello） | `tauri-plugin-biometric` | ✅ |
| 系统托盘 | Tauri 2 built-in | ✅ |
| 通知 | `tauri-plugin-notification` | ✅ |
| 自动更新 | `tauri-plugin-updater` | ⚠️ endpoint + pubkey 待修 |
| 窗口位置持久 | `tauri-plugin-window-state` | ✅ |

### 3.2 后端运行模式（三选一）

桌面端的后端访问有三种模式，由 `services::runtime_config` 的 `backend_url` 决定：

| 模式 | backend_url | 适用 |
|---|---|---|
| **嵌入式（sidecar）** | `http://127.0.0.1:<随机>` | 默认推荐 — 桌面随安装包带后端二进制 |
| **本地 dev** | `http://localhost:8001` | 开发调试 |
| **远程** | `https://api.anxinai.com` | 企业部署 / 用户主动切换 |

**当前缺口**：桌面包**没有 sidecar**，即默认走"远程"，本地优先模式无后端可用。

**推荐方案 — sidecar Python 后端**：

```toml
# desktop/tauri.conf.json (bundle.resources 注入)
{
  "bundle": {
    "externalBin": ["binaries/anxin-backend"],
    "resources": {
      "binaries/anxin-backend": "binaries/anxin-backend"
    }
  }
}
```

`anxin-backend` 通过 [PyInstaller](https://pyinstaller.org/) 或 [Nuitka](https://nuitka.net/) 把 `backend/src/api/main.py` 打包为单文件可执行。Tauri 启动时 `app.shell().sidecar("anxin-backend").spawn()`。

**简化路径**：若不打包后端，则桌面在 `local`/`hybrid` 模式下仍能用（SQLCipher + 本地 LLM 直连），只是协作 / 远控 / 云同步等需 `cloud` 模式 + 远程后端。

> 决策（2026-05-22）：**M3 先实现"无 sidecar 也可用"**（local 模式 + 直连云端），sidecar 嵌入推到 M4 之后。原因：sidecar 涉及打包体积 +200MB、CI 复杂度、跨平台 Python 兼容性，先把首启体验/LLM 配置闭环。

---

## 4. LLM 配置流

### 4.1 支持的 Provider

| Provider | 类型 | API key 来源 | 状态 |
|---|---|---|---|
| OpenAI | 远程 | 用户填 `sk-...` | ✅ |
| Anthropic | 远程 | 用户填 `sk-ant-...` | ✅ |
| 通义千问 | 远程 | 用户填 DashScope key | ✅ |
| DeepSeek | 远程 | 用户填 | ✅ |
| 混元 | 远程 | 用户填腾讯云 SecretId/SecretKey | ✅ |
| **Ollama**（本地） | 本地 | 检测 `http://localhost:11434` | ✅ `PrivateLLMSetup.tsx` |
| **LMStudio**（本地） | 本地 | 检测 `http://localhost:1234` | ✅ |
| 企业自建 | 远程 | 自定义 endpoint + key | ✅ |

### 4.2 配置入口（统一）

桌面端 LLM 配置只有 **1 个入口**（避免分裂）：

```
左侧导航 · 设置 → AI 模型 / 自定义 LLM
```

页面包含：
1. **当前可用模型卡片**：显示已配置 provider + 测试连通性按钮
2. **添加 provider**：选择 OpenAI / Anthropic / 通义 / ... / Ollama → 填表（endpoint + api_key + 选模型）
3. **本地 LLM 检测**：自动扫描 Ollama / LMStudio 在本机运行
4. **默认模型选择**：从已配置中选 1 个为 default
5. **隐私模式联动**：`local` 模式只允许本地 LLM；`hybrid` 允许混合；`cloud` 任意

### 4.3 未配置检测策略

```ts
// frontend/src/lib/llm-status.ts
export async function checkLLMConfigured(): Promise<{
  configured: boolean
  hasLocal: boolean
  hasRemote: boolean
  defaultProvider?: string
}> {
  const configs = await llmConfigsApi.list()
  const defaultConfig = await llmConfigsApi.getDefault().catch(() => null)
  return {
    configured: configs.length > 0 && !!defaultConfig,
    hasLocal: configs.some(c => c.provider === 'ollama' || c.provider === 'lmstudio'),
    hasRemote: configs.some(c => ['openai', 'anthropic', 'qwen', 'deepseek', 'hunyuan'].includes(c.provider)),
    defaultProvider: defaultConfig?.provider,
  }
}
```

**触发点**：

| 时机 | 行为 |
|---|---|
| App 启动后（Layout mount） | 调 `checkLLMConfigured`，若 `configured = false` → 顶部挂 `LlmNotConfiguredBanner` |
| 进入 `/chat` 页面 | 若未配置 → 不渲染 chat 界面，渲染"请先配置 LLM"占位 + 跳转按钮 |
| 进入 `/v3/personas/*` 工作台 | 同上 |
| Onboarding 第 3 步 | 必填一个 provider 才能 next |

### 4.4 Banner 设计

参照 DESIGN §10.6 聊天气泡规范的"系统提示"风格：

```
┌──────────────────────────────────────────────────────────────────────┐
│ ⚠ 还未配置 AI 模型。需要配置至少一个 LLM 才能使用智能对话。            │
│                                                  [配置模型]  [关闭] │
└──────────────────────────────────────────────────────────────────────┘
```

- 背景：`bg-warning/10`
- 边：`border-warning/40` 左 4px
- 关闭后 24 小时内不再弹（localStorage 记忆）
- 持久关闭：放在"设置 → 提醒"

---

## 5. 首次引导（OnboardingWizard）

### 5.1 触发逻辑

```ts
// 持久化 key
const ONBOARDING_KEY = 'anxin.onboarding.completed.v1'

// 触发：App 启动后，Layout mount，且：
//   - localStorage.getItem(ONBOARDING_KEY) !== 'true'
//   - 已登录（authStore.user 非 null）
//   - 不在 /login /admin /pro 等独立路由
```

### 5.2 4 步骤

**Step 1：欢迎**

- Logo + 品牌橙渐变背景
- 标题：「欢迎使用安心智能助手」
- 副：「一个 App 搞定法务 / 财务 / 税务 / 合规 / 经营管理 / 内容产出 / 出海跨境」
- 卡片网格（飞书风简洁）：10 personas 一句话介绍
- 按钮：「开始配置」

**Step 2：选择隐私模式**

参照 [`docs/openspec/00-intelligent-assistant-platform-spec.md`](../openspec/00-intelligent-assistant-platform-spec.md) 的三态模式：

| 模式 | 卡片标题 | 副标题 | 适合 |
|---|---|---|---|
| 🔒 本地 | 完全本地 | 「数据不出设备，AI 也在本机运行」 | 高保密 / 离线场景 |
| 🔄 混合 | 智能混合 | 「敏感数据本地，AI 协作云端」（推荐） | 大部分用户 |
| ☁️ 云端 | 全云端 | 「最佳体验，全云端协作」 | 团队 / 跨设备 |

用户选定后写入 `runtime_config.mode`。

**Step 3：配置 LLM**

根据 step 2 的选择决定可选 provider：
- `local` → 只显示 Ollama / LMStudio（含安装指引）
- `hybrid` / `cloud` → 显示全部 provider

UI 与 `PrivateLLMSetup.tsx` 共用组件，但简化为 1 个 provider 配置即可继续。

- 「跳过」按钮：允许跳过，但 banner 会持续提示
- 「下一步」按钮：必须保存至少 1 个 provider 才可继续

**Step 4：完成 + 引导**

- ✅ 已配置完成图标
- 列出 4 个常用入口卡片（消息 / 任务 / 工作台 / 知识）
- 按钮：「开始使用」→ 跳到 `/chat`，标记 onboarding 完成

### 5.3 持久化

```ts
// 完成时
localStorage.setItem(ONBOARDING_KEY, 'true')
localStorage.setItem('anxin.onboarding.completedAt', new Date().toISOString())

// Tauri 端额外写到 store（多端一致）
await invoke('set_app_setting', { key: 'onboarding.completed', value: 'true' })
```

二次启动直接跳过 wizard，进入主界面。

### 5.4 重置入口

「设置 → 关于 → 重新查看引导」 → 清 `localStorage` + Tauri store，下次启动重弹。

---

## 6. UI 风格（飞书风）

OnboardingWizard 必须严格遵守 DESIGN §10：

- **布局**：全屏 modal（`fixed inset-0`）+ 中心卡片（max-width 720px，圆角 12px = `--radius-xl`）
- **步骤指示器**：顶部进度条 `1/4 → 2/4 → ...`，飞书风扁平
- **按钮**：主按钮 brand 橙；次按钮 ghost；进度按钮无浮动动画（与 s9 token 收紧一致）
- **图标**：lucide-react，统一 20/24px
- **不使用**：渐变背景、emoji、大插图

---

## 7. 实施清单（本周 M3 前置）

| 任务 | 文件 | 优先 |
|---|---|---|
| 1. 修 `tauri.conf.json` updater endpoint 域名 | `desktop/tauri.conf.json` | P0 |
| 2. 新增 `frontend/src/lib/llm-status.ts` | 新文件 | P0 |
| 3. 新增 `frontend/src/components/onboarding/OnboardingWizard.tsx` | 新文件 | P0 |
| 4. 新增 `frontend/src/components/onboarding/LlmNotConfiguredBanner.tsx` | 新文件 | P0 |
| 5. App.tsx 挂载 OnboardingWizard（在 Layout 内） | `frontend/src/App.tsx` | P0 |
| 6. 删除孤儿 `frontend/src/components/WelcomeGuide.tsx`（被 OnboardingWizard 取代） | 删除 | P1 |
| 7. Chat / Persona Workspace 检测 LLM 未配置时占位 | `frontend/src/pages/Chat.tsx` | P1 |
| 8. Tauri sidecar 嵌入式后端 PoC | `desktop/scripts/` | P3（推到 M5 后） |

---

## 8. 验收（DoD）

- [ ] 桌面 dev 启动 → 出现 OnboardingWizard 第 1 步
- [ ] 选择隐私模式 → 配置 LLM → 完成 → 跳 `/chat`
- [ ] 二次启动不弹 wizard
- [ ] 主动清掉默认 LLM → 顶部出现 banner，`/chat` 显示占位而非 chat 界面
- [ ] 「设置 → 重新查看引导」重置生效
- [ ] `desktop-release-package.sh --dry-run` 输出包含 onboarding/LLM 资源
- [ ] 桌面打包 dmg 装到干净 macOS，首启 wizard 正常

---

## 9. 关联

- 实施方案 L3：[`docs/plans/2026-05-22-implementation-plan.md`](2026-05-22-implementation-plan.md)
- 产品蓝图 §3.1：[`docs/plans/2026-05-22-product-blueprint.md`](2026-05-22-product-blueprint.md)
- DESIGN §10：[`DESIGN.md`](../../DESIGN.md)
- 桌面同步引擎：[`docs/desktop/sync-engine-design.md`](../desktop/sync-engine-design.md)
- 桌面 SQLite 加密：[`docs/desktop/sqlite-encryption-strategy.md`](../desktop/sqlite-encryption-strategy.md)
