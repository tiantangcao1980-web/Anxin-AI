# TASK-11a 桌面端 MVP 三件套（窗口外观 + 全局快捷键快速问答 + 拖拽分析）

> 波次 4 · 工时估 5-7 天
> 前置依赖：任务 0（密钥治理 SOP 完成）、任务 1（认证 + token 存储确定）、任务 11b（同步引擎，拖拽落地的文件需要有去处）
> 下游依赖：任务 11c（移动端跨设备延续要先确认桌面会话语义）
> 必读：`../PLAN.md`、`../00-platform/01-prd-reality-gap.md`、`../00-platform/03-cross-cutting-gaps.md` §1 缺口 C、`PRODUCT_ROADMAP.md` 桌面端 P0-1 / P0-2 / P0-3、`DESIGN.md` 跨平台一致性章节

> 2026-05-08 定位补充：桌面端是项目未来的主要工作站，不只是 WebView 外壳。MVP 除窗口、快捷问答、拖拽分析外，还必须预留本地模型、独立知识库、Skills/MCP 配置入口，以及移动端远程控制桌面的 host 能力。
> 2026-05-09 goal 修订：所有后续开发优先聚焦桌面端本地可执行功能和治理门禁；移动端/小程序排在桌面主工作站收口之后，按 uni-app 迁移路线推进。

---

## 1. 范围

### 要碰的文件

- 桌面 Tauri 配置 + Rust 入口：
  - `desktop/tauri.conf.json`
  - `desktop/src/main.rs`
  - **新建** `desktop/src/window_management.rs`
- 桌面 Rust commands：
  - `desktop/src/commands/global_shortcut.rs`（已注册快捷键，需补窗口呼出 / 隐藏逻辑）
  - `desktop/src/commands/tray.rs`
  - `desktop/src/commands/local_llm.rs`（只读/轻接入：展示本地模型状态，不重写模型服务）
  - **新建** `desktop/src/commands/file_drop.rs`
  - **预留/新建** `desktop/src/commands/remote_control.rs`（移动端配对、远程命令确认和执行状态回传；具体队列依赖 11b）
- 共享前端（桌面壳复用 Web 前端）：
  - **新建** `frontend/src/pages/QuickQuery.tsx`（精简对话窗口）
  - **新建** `frontend/src/components/desktop/`（桌面专用组件目录：标题栏 / 托盘提示 / 拖拽 overlay / 本地能力状态）
  - `frontend/src/App.tsx`（仅加 `/desktop/quick-query` 路由，不动其他）
- 扩展与配置入口（按现有能力轻接入，不在本任务重写后端）：
  - `backend/src/api/routes/llm.py`、`backend/src/api/routes/mcp_routes.py`、`backend/src/services/skill_service.py`
  - `backend/src/api/routes/knowledge.py`、`backend/src/services/knowledge_management.py`
  - `frontend/src/components/settings/OfflineResourceManager.tsx`（如存在则复用本地资源状态）
- 桌面图标 / 托盘 icon 资源：
  - `desktop/icons/`（仅在缺资源时补，不重做）

### 不要碰的文件

- `desktop/src/services/sync_engine.rs` / `desktop/src/commands/sync.rs`（任务 11b 处理，本任务只在拖拽落地时调用其接口）
- `frontend/src/lib/design-tokens.ts`（设计 tokens 全局唯一源，不动）
- `backend/src/prompts/` 任一文件
- `frontend/src/lib/store.ts`（任务 1 token 存储已迁移，不重做）
- 任何 payment / billing / subscription 文件
- 桌面签名 / 公证 / 自动更新通道（必须用户执行）

---

## 2. 必修 P0（带文件:行号 + 期望状态）

| # | 文件 | 现状 | 期望（对齐 ROADMAP） |
|---|---|---|---|
| P0-1 | `desktop/tauri.conf.json` + `desktop/src/main.rs` + 新建 `desktop/src/window_management.rs` | 默认 Tauri 窗口（系统标题栏 + 边框） | macOS：自定义标题栏（hidden titleBarStyle + 拖拽区 + 红黄绿按钮原位）；Windows：`decorations: false` 去边框 + 自绘标题栏；统一透明毛玻璃（macOS vibrancy / Windows acrylic） |
| P0-2 | `desktop/src/commands/global_shortcut.rs` + 新建 `frontend/src/pages/QuickQuery.tsx` | 快捷键 `Cmd+Shift+Space` 已注册，但呼出后只是普通主窗口 | 呼出独立的精简对话窗口（400×500 居中、无标题栏、ESC 关闭、失焦自动隐藏）；流式回答；用户回车提交 → 流式完成 → 1.5s 后自动隐藏 |
| P0-3 | `desktop/src/commands/tray.rs` + 新建 `desktop/src/commands/file_drop.rs` | 托盘存在，无文件拖入处理 | 文件拖到托盘图标即 emit `desktop://file-drop`；按扩展名路由（PDF / DOCX → 合同审查；TXT / MD → 文档摘要）；落地路径走任务 11b 的同步引擎 offline_tasks 队列；UI 弹"已加入待分析队列"提示 |
| P0-4 | `frontend/src/components/desktop/TitleBar.tsx`（新建） | 无 | 跨平台一致的自绘标题栏：macOS 显示窗口标题居中 + 红黄绿按钮原位；Windows 显示标题左对齐 + 自绘最小化/最大化/关闭 |
| P0-5 | `desktop/src/main.rs` 启动 | 当前模式选择/绝密本地状态在前端 localStorage | 桌面启动时从 SQLite `sync_state` 读取 `mode`（绝密 / 混合 / 云端），与前端 PrivacyContext 对齐（不重做模式切换逻辑，仅打通启动加载） |
| P0-6 | `frontend/src/components/desktop/` + `desktop/src/commands/local_llm.rs` + LLM/knowledge/MCP/skill routes | 已有零散本地模型、知识库、MCP/Skill 底座，但桌面没有主工作站统一入口 | 桌面壳展示当前隐私模式、本地模型状态、知识库状态、Skills/MCP 状态和配置入口；不允许在绝密模式下诱导云端调用 |
| P0-7 | 新建 `desktop/src/commands/remote_control.rs` + 11b command queue | 移动端远控桌面未定义 | 桌面作为 remote-control host：展示配对请求、权限范围、远程命令确认、执行状态、取消/撤销入口和审计日志；高风险动作必须二次确认 |
| P0-8 | `frontend/src/components/desktop/DesktopWorkstationPanel.tsx` + `frontend/src/lib/tauri-bridge.ts` | 工作站只有只读状态入口，缺最小配置写入面 | 桌面客户端可本地切换绝密/混合/云端模式、配置后端环境地址，非桌面预览只读；URL 校验拒绝非 http/https；绝密模式仍不开放数据网络 |

---

## 3. 流程（Step 0-5）

### Step 0 · PRD vs 代码差分（强制）

产出 `docs/audit/11a-desktop-mvp/00-prd-reality-gap.md`：
- ROADMAP 桌面端 P0-1 / P0-2 / P0-3 vs 当前桌面代码三件套实测能力差距
- 列横切缺口 C（同步引擎）对本任务 P0-3 的影响（拖拽分析的文件无处可放就是死代码）
- 跨平台一致性：桌面端的标题栏 / 字号 / 间距与 `frontend/src/lib/design-tokens.ts` 是否漂移
- 新定位差分：桌面主工作站、本地模型、独立知识库、Skills/MCP 配置和移动远控 host 当前有哪些代码基础、哪些仍只是规范预留

### Step 1 · 检索复用

- `/hierarchical-memory find-feature "Tauri 自定义标题栏 macOS Windows"`
- `/hierarchical-memory find-feature "Tauri 全局快捷键 精简窗口"`
- `/hierarchical-memory find-feature "Tauri 托盘文件拖拽"`
- `/iterative-retrieval` 按 `tauri.conf.json → main.rs → commands/* → frontend/pages/*` 分层读

### Step 2 · P0-1 窗口外观

1. `tauri.conf.json` 给主窗口加 `decorations: false`、`transparent: true`、`titleBarStyle: "Overlay"`（macOS）
2. 新建 `desktop/src/window_management.rs`：包含 `apply_macos_vibrancy()` / `apply_windows_acrylic()` / 平台分支
3. `main.rs` 启动时按 `cfg!(target_os)` 调用对应函数
4. 前端新建 `frontend/src/components/desktop/TitleBar.tsx`，路由壳 / 主页面顶部嵌入
5. macOS 上验证红黄绿按钮原位、拖拽区 36px 高
6. Windows 上验证最小化/最大化/关闭按钮可点击、双击标题栏切换最大化

### Step 3 · P0-2 全局快捷键 → 快速问答

1. `commands/global_shortcut.rs` 已注册 `Cmd+Shift+Space`，新增：触发时检查独立窗口是否存在；不存在则 `WindowBuilder::new("quick-query", "/desktop/quick-query")` 创建（400×500，居中，无标题栏，always_on_top）
2. 失焦事件（`on_window_event`）→ 自动 `hide()`
3. ESC 键 → 关闭（前端处理）
4. 新建 `frontend/src/pages/QuickQuery.tsx`：复用现有 `useChat` / 流式 SSE hook，不重写；UI 仅一个输入框 + 流式回答区域；提交 → 流式回答 → 完成 1.5s 后 emit `desktop://hide-quick-query`
5. Rust 端监听 `desktop://hide-quick-query` 调用窗口 `hide()`

### Step 4 · P0-3 拖拽到托盘 → 自动分析

1. 新建 `desktop/src/commands/file_drop.rs`：`on_tray_drop(paths: Vec<PathBuf>)`
2. 按扩展名路由：`.pdf|.docx|.doc` → 合同审查；`.txt|.md` → 文档摘要；其他 → 弹提示"暂不支持此格式"
3. 调用任务 11b 的同步引擎 `offline_tasks` 队列：`enqueue_task(entity_type="document", operation="analyze", payload={path, type})`
4. 同时 emit 前端事件 `desktop://file-queued`
5. 前端 `frontend/src/components/desktop/FileDropToast.tsx` 展示"已加入待分析队列：xxx.pdf"

### Step 5 · 验证 + 沉淀

- `/verification-loop`：`cargo check`（桌面）+ `cargo clippy`（无新增 warning）+ tsc + lint（前端）+ `npm run build`
- 跨平台手测：macOS 14+（Apple Silicon + Intel）+ Windows 11 各跑一遍三件套
- 性能基线：快捷键呼出 → 窗口显示 < 200ms；托盘拖拽 → 提示出现 < 500ms
- `/designdna` 校验桌面壳与 `DESIGN.md` 跨平台一致性章节是否漂移
- `add-feature --name "tauri-desktop-mvp-trio" --pattern "自定义标题栏 + 全局快捷键精简窗口 + 托盘拖拽" --files ...`
- 更新 `PRODUCT_ROADMAP.md`：把 P0-1 / P0-2 / P0-3 标"已完成（待 50 用户灰度 14 天）"

---

## 4. 输出物

```
docs/audit/11a-desktop-mvp/
├─ 00-prd-reality-gap.md
├─ 01-prd-coverage.md
├─ 02-issues.md
├─ 03-fixes.md
├─ 04-test-additions.md
└─ 05-followups.md
```

附加：
- `docs/desktop/window-styling.md`（macOS / Windows 平台分支说明 + 截图）
- `docs/desktop/quick-query-flow.md`（Cmd+Shift+Space 全链路时序图）

---

## 5. 风险护栏

- **签名 / 公证 / 分发**：dmg 公证 / msi 签名 / 自动更新通道任何动作必须用户执行，本任务只交付未签名的开发构建
- **灰度**：dmg / msi 打包后用户先 50 个种子用户灰度跑至少 14 天，无 P0 反馈再扩量
- **不动同步引擎**：任务 11b 未交付前，P0-3 拖拽落地的 `offline_tasks` 入队是"写入本地 SQLite 排队"，不会真正上行；`offline_tasks` schema 必须等任务 11b 的 migration 落地后再依赖
- **跨平台**：macOS 14+ / Windows 11 是基线；macOS 12 / Windows 10 是 best-effort，不阻断
- **不动**：design-tokens / store.ts token 存储 / payment / prompts
- **快捷键冲突**：`Cmd+Shift+Space` 在部分输入法占用，启动时若注册失败要 graceful 降级（弹提示让用户改键），不能 panic
- **托盘拖拽**：Tauri 当前对托盘 drop 平台支持不一致，Linux 可能需要 best-effort，不在 MVP 阻断范围

---

## 6. 完成标准（DoD）

- [ ] macOS 14+ 自定义标题栏：红黄绿按钮原位、36px 拖拽区、vibrancy 毛玻璃
- [ ] Windows 11 自定义标题栏：最小化/最大化/关闭按钮可点击、acrylic 毛玻璃、双击标题栏切换最大化
- [ ] `Cmd+Shift+Space` 呼出 < 200ms；流式回答完成 1.5s 后窗口自动隐藏；ESC 关闭；失焦自动隐藏
- [ ] 拖拽 PDF / DOCX 到托盘 → 提示"已加入待分析队列"；提示出现 < 500ms
- [ ] 拖拽 .txt / .md 走文档摘要分支；不支持的扩展名给明确提示
- [ ] `frontend/src/components/desktop/` 新增组件全部不引入硬编码颜色 / padding（`/designdna` 校验通过）
- [ ] 桌面 `cargo clippy` 无新增 warning；前端 build 无新增警告
- [ ] 桌面主工作站入口可见本地模型、知识库、Skills/MCP 和隐私模式状态；绝密模式不展示会导致数据出站的默认动作
- [ ] 桌面主工作站配置面可切换运行模式、保存后端环境地址，并由单测/e2e 锁住非桌面只读、URL 校验和绝密模式远控阻断
- [ ] 移动远控 host 最小闭环：配对请求、权限说明、远程命令确认、执行状态、取消/撤销和审计日志至少有开发环境 smoke
- [ ] 跨平台手测脚本：macOS + Windows 各跑一遍三件套，截图归档到 `docs/desktop/`
- [ ] `docs/audit/11a-desktop-mvp/01..05.md` 全产出
- [ ] 经验沉淀到 hierarchical-memory（add-feature 至少 1 条，记录三件套的 Tauri 平台分支模式）

2026-05-08 本地收口记录：`frontend/src/components/desktop/DesktopWorkstationPanel.tsx`、`desktopWorkstationModel.ts`、`desktopWorkstationModel.test.ts`、`frontend/src/pages/settingsTabs.ts` 和 `settingsTabs.test.ts` 已补桌面主工作站最小可见入口；`/settings?tab=workstation` 展示隐私模式、本地模型、知识库、Skills/MCP、同步和移动远控状态；绝密模式下同步/远控 action disabled，非桌面预览下本地模型/同步/远控 action disabled，测试锁住无 unsafe outbound enabled action 和历史 `privacy` tab 映射。同日继续接入现有 Tauri IPC 和受治理前端 API，只读展示本地 LLM 可用性、模型数量、离线任务队列、知识库数量/文档数、MCP 服务/启用/工具缓存统计，并在绝密模式下跳过知识库/MCP 数据网络探针、把移动远控标为阻断或待验收而非可用。此记录只覆盖 P0-6 的最小入口和局部状态探针，不关闭完整 DoD；仍需完整配置面、移动远控 host、跨平台截图和 signed runtime 证据。

2026-05-08 浏览器级补证：`frontend/e2e/settings-workstation.spec.ts` 已覆盖 direct `/settings?tab=workstation`、legacy `/settings?tab=privacy`、tab URL 写回、非桌面预览禁用本地模型/同步/远控动作、模拟桌面运行时本地模型/知识库/MCP/队列探针，以及 iPhone 14 视口下工作站资源卡不越界；同轮修复 `McpSettingsPanel` 对非数组响应的防御性处理和 Settings 移动端 min-content 横向溢出。

2026-05-08 远控 host 补证：`desktop/src/services/remote_control_host.rs` 与 `desktop/src/commands/remote_control.rs` 已在单次 safe-probe host cycle 基础上新增 bounded safe-probe host poll：轮询间隔、最大轮询次数和每次 claim limit 都有上限，且仍只完成 `ping/status_probe`，未知/高风险命令继续 failed/unsupported。`cd desktop && cargo test remote_control` 当前 `8 passed`，`cd desktop && cargo check` 通过。此记录只降低 host 侧轮询缺口，不关闭完整 DoD；仍需真正常驻后台 daemon、桌面确认 UI、真实跨设备 host callback、signed runtime 和真机/设备证据。

2026-05-09 goal-driven 收口记录：`frontend/src/components/desktop/DesktopWorkstationPanel.tsx` 已补“工作站配置”写入面，桌面运行时可切换绝密/混合/云端模式并保存后端环境地址；`frontend/src/components/desktop/desktopWorkstationModel.ts` 与 `desktop/src/commands/app_mode.rs` 均新增 http/https URL 校验，拒绝 `local://` 等非后端环境地址，避免绕过 UI 直接写入无效 IPC 配置；`frontend/src/lib/tauri-bridge.ts` 新增 `setBackendUrl` IPC wrapper。`frontend/e2e/settings-workstation.spec.ts` 已覆盖桌面 runtime mock 下的模式切换、后端地址保存、绝密模式远控阻断和移动宽度回归；`cd desktop && cargo test app_mode` 为 `2 passed`。这关闭的是最小配置写入面，不等于完整 LLM/MCP/Skills connector 凭据 CRUD 或 signed runtime 证据完成。

2026-05-09 桌面运行配置持久化记录：`desktop/src/services/runtime_config.rs` 新增 secret-free `runtime-config.json` 合约，只保存 `schemaVersion`、`mode` 和 `backendUrl`，不保存 token、API key 或 connector secret；`desktop/src/lib.rs` 启动时从 Tauri app data 加载并回填 Rust 共享状态，`switch_mode` / `set_backend_url` 写入前先校验并落盘。`cd desktop && cargo test runtime_config` 为 `5 passed`，`cd desktop && cargo check` 通过。此轮补齐的是模式/后端地址的跨重启持久化；P0-5 中更完整的 PrivacyContext / SQLite `sync_state` 对齐、完整 connector 凭据 CRUD、signed runtime 和跨设备证据仍未关闭。

2026-05-09 PrivacyContext 对齐记录：`frontend/src/context/PrivacyContext.tsx` 在 Tauri 桌面环境中监听 `useAppModeStore`，将 Rust/桌面 store 的 `top-secret` 映射到业务门控使用的 `PrivacyMode.LOCAL`，`hybrid` / `cloud` 保持对应，避免桌面已恢复绝密模式但 `ModeGate` 仍按 HYBRID 放开找律师、舆情、IM、案源市场等云端/混合入口。`frontend/src/context/PrivacyContext.test.ts` 锁住映射和未知值回退；`cd frontend && npm test -- PrivacyContext.test.ts` 为 `3 passed`，`cd frontend && npm exec tsc -- --noEmit` 通过。此项补齐 P0-5 的前端门控对齐片段，仍不关闭完整 signed runtime 和跨设备证据。

2026-05-09 MCP connector 凭据保留记录：`frontend/src/pages/mcpSettingsModel.ts` 新增保存 payload 规则，编辑既有 MCP connector 元数据时默认不提交 `env`，避免后端 masked response 只有 `env_keys` 时把已保存密钥清空；只有创建或显式“替换环境变量”才提交 `env`。`frontend/src/pages/Settings.tsx` 仅展示 env key 名，新输入的 secret 使用 password input 且列表中不显示 secret 前缀；`frontend/src/lib/api.ts` 补齐 `env_keys` 类型。`cd frontend && npm test -- mcpSettingsModel.test.ts` 为 `3 passed`，`cd frontend && npm run lint` 和 `cd frontend && npm exec tsc -- --noEmit` 通过。此项降低 connector 配置 CRUD 的本地凭据风险，真实 approved MCP connector 演练仍未关闭。

2026-05-09 MCP 后端契约补证：`backend/tests/test_external_surface_guards.py` 新增 MCP update 回归，覆盖“创建时带 secret env、更新时省略 env、响应仍只返回 `env_keys`、数据库 env 保留、更新审计只记录 env key 不记录 secret 值”。`backend/.venv/bin/pytest -q backend/tests/test_external_surface_guards.py -k "mcp_server_update_preserves_masked_env_when_omitted or mcp_server_create_writes_masked_audit_log"` 为 `2 passed`，`backend/.venv/bin/ruff check backend/tests/test_external_surface_guards.py` 通过。此项把前端凭据保留规则锁到后端 masked response / audit 契约上，仍不等于真实 approved connector runtime 演练完成。

2026-05-09 桌面快问代码级闭环记录：`desktop/src/commands/quick_query.rs` 新增独立 `quick-query` 窗口合约，`desktop/src/lib.rs` 的 Cmd/Ctrl+Shift+Space 全局快捷键改为切换 420x540、无标题栏、always-on-top 的 `/desktop/quick-query` 快问窗口，主窗口不再被快捷键隐藏；`frontend/src/pages/QuickQuery.tsx` 与 `frontend/src/pages/quickQueryModel.ts` 新增精简快问页，top-secret/hybrid 桌面模式走 `local_llm_chat`，cloud/web fallback 走既有 chat stream/send API，并通过 `hide_quick_query_window` 支持关闭、ESC、失焦和回答完成后自动隐藏。`cd desktop && cargo test quick_query` 为 `2 passed`，`cd frontend && npm test -- quickQueryModel.test.ts` 为 `4 passed`，`cd frontend && npx playwright test e2e/quick-query.spec.ts --project=chromium` 为 `1 passed`。此项关闭 P0-2 的代码级主链路，不等于 packaged runtime 快捷键实测、200ms 呼出性能、真实本地模型手测或 signed runtime 证据完成。

2026-05-09 文件拖入分析入队代码级记录：`desktop/src/commands/file_drop.rs` 新增 `queue_file_drop_paths` Tauri 命令和 `desktop://file-queued` 事件，按扩展名把 `.pdf/.doc/.docx` 路由为 `contract_review`、`.txt/.md` 路由为 `document_summary`，不支持的扩展名返回明确原因；支持文件会写入 Rust SQLCipher/keyring 管理的 `offline_tasks` 队列，完整本地路径只保存在加密队列 payload 中，事件/返回值只暴露文件名、task id、task type 和动作标签。`frontend/src/lib/tauri-bridge.ts` 新增 `queueFileDropPaths` 桥接类型。此项关闭 P0-3 的分类和本地入队代码级底座，不等于平台级“拖到托盘图标”手势、前端 toast、500ms 性能或 packaged runtime 证据完成。

2026-05-09 文件拖入 toast 反馈记录：`frontend/src/lib/tauri-bridge.ts` 新增 `listenFileDropQueued` typed listener，复用既有 `listenEvent` Tauri 事件封装监听 `desktop://file-queued`；`frontend/src/App.tsx` 在桌面运行时注册全局监听，并通过 Sonner success/warning toast 展示“已加入待分析队列”“部分文件已加入队列”或“不支持文件”；`frontend/src/lib/desktopFileDropEvents.ts` 抽出 toast 摘要模型，单测覆盖单文件、多文件、混合失败和空 report，且不暴露本地路径。验证：`cd frontend && npm test -- desktopFileDropEvents.test.ts` 为 `4 passed`，`npm exec tsc -- --noEmit` 和 `npm run lint` 通过。此项关闭 P0-3 的前端可见反馈代码级缺口；真实平台级托盘 drop 手势、500ms 提示性能、packaged runtime 和 signed runtime 证据仍未关闭。

2026-05-09 WebView 文件拖放接入记录：`frontend/src/lib/tauri-bridge.ts` 新增 `listenDesktopFileDrops`，通过 Tauri v2 `getCurrentWebview().onDragDropEvent` 监听主窗口文件 drop，并复用 `queueFileDropPaths` 写入桌面离线队列；`frontend/src/App.tsx` 在 Tauri 桌面环境注册该监听，入队失败时展示错误 toast，成功路径仍由 `desktop://file-queued` 统一提示；`frontend/src/lib/desktopFileDropEvents.ts` 新增 `extractDesktopFileDropPaths`，只接受 `type="drop"` 且过滤非字符串/空路径。验证：`cd frontend && npm test -- desktopFileDropEvents.test.ts` 为 `5 passed`，`npm exec tsc -- --noEmit` 和 `npm run lint` 通过。此项关闭“拖到桌面主窗口即可入队”的代码级链路；托盘图标 drop 平台支持、500ms 真实性能、packaged runtime 和 signed runtime 证据仍未关闭。

2026-05-09 桌面标题栏基础记录：`desktop/src/lib.rs` 启动时在 Windows/Linux 对主窗口调用 `set_decorations(false)`，macOS 保持现有 `titleBarStyle: Overlay` + 原生交通灯；`frontend/src/components/desktop/TitleBar.tsx` 新增非 macOS 的最小化/最大化/关闭按钮，`frontend/src/components/Layout.tsx` 将其嵌入现有 60px 顶部拖拽栏右侧；`frontend/src/lib/tauri-bridge.ts` 新增 `minimizeCurrentWindow` / `toggleMaximizeCurrentWindow` / `closeCurrentWindow`，并在 `desktop/capabilities/default.json` 和生成 schema 中补 `core:window:allow-toggle-maximize`。验证：`cd desktop && cargo fmt`、`cargo check`、`cd frontend && npm exec tsc -- --noEmit`、`npm run lint` 通过。此项关闭 P0-4 的前端控制按钮代码级基础，不等于 macOS/Windows 实机标题栏截图、双击最大化、vibrancy/acrylic 或 signed packaged runtime 证据完成。

2026-05-09 标题栏双击交互记录：`frontend/src/components/desktop/titleBarModel.ts` 新增自绘标题栏平台判断与双击最大化判定，只有非 macOS Tauri 桌面且双击目标不是 button/link/input/select/textarea 或其交互祖先时才允许触发；`frontend/src/components/desktop/TitleBar.tsx` 复用该模型并在 `frontend/src/components/Layout.tsx` 的顶部拖拽栏 `onDoubleClick` 调用 `toggleMaximizeCurrentWindow`。验证：`cd frontend && npm test -- titleBarModel.test.ts` 为 `2 passed`，`npm exec tsc -- --noEmit` 和 `npm run lint` 通过。此项关闭 Windows/Linux 自绘标题栏“双击最大化/还原”的代码级缺口；Windows 实机点击、packaged runtime 和视觉验收仍需外部证据。

2026-05-09 窗口外观门禁记录：`docs/desktop/window-styling.md` 新增 macOS Overlay、Windows/Linux 自绘标题栏、顶部拖拽栏、窗口控制、capability 和待补实机证据说明；`scripts/desktop-window-chrome-gate.sh` 新增本地门禁，校验 `tauri.conf.json`、`desktop/src/lib.rs`、`frontend/src/components/Layout.tsx`、`TitleBar.tsx`、`titleBarModel.ts`、`titleBarModel.test.ts`、`desktop/capabilities/default.json` 与窗口外观文档保持一致。验证：`bash scripts/desktop-window-chrome-gate.sh` 为 `PASS`。此项把 P0-1/P0-4 从代码实现提升到可复跑的本地治理门禁；实机截图、vibrancy/acrylic 和 signed packaged runtime 仍需外部证据。
