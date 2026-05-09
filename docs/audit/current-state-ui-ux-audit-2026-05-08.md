# 2026-05-08 真实开发状态与 UI/UX 审计

> 主要服务对象：中小企业老板/高管/行政/人事/财务等需求方，以及律师、律所、税务师、税务师事务所、财务顾问、会计/审计人员等专业服务方；当地政府和公共服务协同场景可作为高可信试点受益方。
> 审计口径：代码级事实优先，文档和 release evidence 必须与当前代码、测试、门禁输出一致；不允许用 mock/fake/live 替代品宣称商业完成。
> 使用方法：本报告用于多智能体并行开发前的基线确认。确认后可按本文 lane 拆分任务。

## 1. 审计方法

| 方法 | 本次用法 | 结论边界 |
|---|---|---|
| Super Skill / Superpowers | 使用 `code-review`、`ai-review-gates`、`documentation`、`checkpoint-rollback-safety`、`design-craft-gate` 的审计口径 | 先做事实核对、风险门禁和文档清理，不在审计阶段改业务逻辑 |
| 代码级阅读 | 重点读后端支付/电签/OA、桌面同步、移动/小程序入口、桌面同步 UI、跨端 token 文档 | 发现 P0/P1 真实缺口，见下表 |
| 本地验证 | 复用并补跑后端、前端、移动、小程序、桌面、release evidence 命令 | 代码级基线强，但商业证据仍阻断 |
| UI/UX 审计 | 按移动端、小程序、桌面分端检查交互闭环、触控、token、错误态、发布证据 | 用户反馈的设计问题成立，且存在政府交付风险 |
| 产品定位复核 | 对照中小企业需求方、专业服务方、桌面主工作站、移动远控、本地模型/知识库、Skills/MCP 可配置目标 | 当前代码已有底座，但距离“全面智能助手平台”仍缺配置面、远控协议和发布级证据 |
| 可信 AI 交互复核 | 借鉴 Codex/Claude 的过程可见、artifact-first、可打断/恢复、能力可发现体验 | 当前对话与多端体验仍偏功能入口堆叠，需要把长任务时间线、证据、可恢复状态和能力中心纳入 P0/P1 |

## 2. 当前真实结论

| 维度 | 现实状态 | 判定 |
|---|---|---|
| 代码质量 | Backend Ruff/mypy、frontend lint/test/build、mobile test/typecheck、mini tsc、desktop cargo check 均已通过本轮复验 | 代码级可继续推进 |
| 商业发布 | `commercial-readiness-gate.sh --quick` 在 clean baseline 仍因 Not ready 和 payment/e-sign/desktop/mobile evidence pending 失败 | 不能 Go |
| 政府交付 | 仍有 mock 默认、真实沙箱缺口、签名/公证缺口、真机缺口、UI/UX 一致性缺口 | 不能对政府用户宣称可上线 |
| 文档状态 | 发布文档大体完整，但部分 dirty worktree/GitNexus 陈述曾停留在历史快照 | 本轮已开始更正 |
| UI/UX | 移动端、微信小程序、桌面端均存在跨端 token 漂移、关键流程未闭环或用户可见粗糙面 | 必须列入 P0/P1 |
| 产品定位 | 已从单一 AI 法务工具升级为中小企业经营风险平台 + 全设备智能助手 | 需求和 OpenSpec 需同步更新 |

## 3. 需求与现实差异表

| 目标/规范 | 文档目标 | 代码/证据现实 | 差异 | 落地动作 |
|---|---|---|---|---|
| 商业交付 ready | release evidence 全部 `Status: complete`，商业门禁通过 | 支付、电签、桌面 runtime、移动/小程序仍 pending | 证据不齐，门禁正确失败 | 保持 No-Go，补真实沙箱、signed/notarized desktop、真机证据后再改状态 |
| 政府场景可信交付 | 生产路径不能静默 mock，失败必须可审计 | 支付和电签 provider factory 已在 staging/production 禁止 `mock` 和未知 provider 静默回落；`test_payment_provider_clients.py`、`test_esign_provider_clients.py` 已覆盖商业环境 fail-closed | 代码级误配伪成功风险已收口；真实支付/电签沙箱、证书轮换、回调重试证据仍缺 | 保持 guard，补真实沙箱和脱敏 evidence 后才允许 release complete |
| OA 通知可靠性 | 审批/通知不能伪成功 | 飞书、钉钉、企微在 staging/production 缺凭据时抛 `OAProviderConfigError`；尚未真实接入的状态查询/组织同步能力在商业环境 fail-closed；`test_oa_integration.py` 已覆盖 | 代码级 mock 通知/审批伪成功已收口；真实 OA 状态查询、组织同步、审计和渠道演练仍不足 | 保持商业环境 hard fail，补真实 API 能力或继续显式不可用 |
| 桌面同步可信 | 本地 SQLCipher/keyring 和云同步必须真实 push/pull | 前端 secure SQL 路径已有进展；Rust IPC 直连同步已从 fail-closed fallback 推进到代码级 SQLCipher push/pull 写回路径，且不再返回 `Ok(0)` 假成功；跨设备延续和 packaged runtime 证据仍未闭合 | 假成功风险已清除，Rust IPC fallback 代码级已补，但商业级跨端同步仍未完成 | 继续补 packaged runtime push/pull/conflict/retry、移动远控和 signed packaged runtime 验收 |
| 移动端关键流程 | 智能调查和法律智库应可完成搜索/详情 | `mobile/app/(tabs)/investigation.tsx` 已用 `useEffect` 加载最近调查/热点，并调用 `/due-diligence/company` 渲染页面内结果卡；`mobile/app/(tabs)/knowledge.tsx` 已调用 `/knowledge/search` 并渲染检索摘要卡；`scripts/mobile-device-smoke.sh` 已有 mobile result surface guard 防回归 | 代码级入口已收口，但真实/官方 iOS、Android 和交互式微信验收仍缺 | 保持代码级 guard，后续补真机 transcript 和跨设备连续会话证据 |
| 小程序验收 | 微信端应有真实登录和设备证据 | WeChat DevTools CLI project smoke 通过，但 evidence 仍 pending；host probe 仅证明工具存在 | 还没有真实小程序交互闭环 | 用官方 appid/测试账号补交互式 DevTools 或真机 transcript |
| 跨端设计系统 | Web/desktop/mobile/mini token 应统一 | `docs/design/cross-platform-token-drift.md` 已记录 Web `hsl(25 95% 53%)` 与 mobile/mini `#D4A574` 漂移 | 品牌和状态语义跨端不一致 | 冻结 token contract，再分端迁移硬编码颜色 |
| 移动端视觉质量 | 状态色、错误态、空态应可维护 | `rg` 显示 mobile 多处 hardcoded hex，如 `mobile/app/find-lawyer.tsx:165`、`contracts.tsx:178`、`cases.tsx:165` | 暗色、无障碍和品牌统一风险 | 把 status/domain colors 纳入 `Colors`，补截图验收 |
| 桌面 UX | 同步冲突应给非技术用户可理解的决策界面 | `SyncStatus` 冲突弹窗已从双栏 JSON 改为字段差异摘要 + 原始数据折叠详情；托盘菜单/tooltip 已移除 emoji 依赖；toolbar 同步/冲突按钮已提升到稳定尺寸和不换行文案 | 政务用户难理解，桌面专业感不足 | 后续补 signed/packaged runtime 截图验收 |
| 前端发布质量 | 构建应可解释、性能可控 | frontend build 通过但有 `lottie-web` eval、dynamic/static import mixing、chunks >500KB | 不阻断代码级，但影响政府内网/低配机器体验 | 列为 P1 性能和打包治理 |
| 全设备智能助手定位 | 桌面是主工作站，移动是随身助手和桌面远控端；用户可配置任意模型、Skills、MCP 和独立知识库 | LLM/MCP/Skills/knowledge/local LLM 已有后端和桌面基础，但桌面配置面、移动远控协议、真机/packaged runtime 证据未闭合 | 产品定位已清晰，代码和证据还没到完成态 | 新增 OpenSpec，调整 TASK-11a/11b/11c，把配置、远控、本地安全列为验收 |
| Codex/Claude 式交互体验 | 长任务过程透明、证据可点、artifact 可编辑、用户可暂停/恢复/接管、能力可发现 | 目前各端没有统一任务时间线、artifact-first 工作台、能力命令面板和跨设备恢复验收 | 体验会显得“能聊但不够可靠”，不利于老板/高管/政府试点用户信任 | 在 TASK-03、TASK-11a/11c、TASK-12 中加入可信会话体验验收 |
| Skills 与智能体自我进化 | Skill 可以持续升级，agent 可以从失败中总结改进，但必须受评测、审批、审计和回滚管控 | `skill_service` 等底座存在，但缺 lifecycle、eval gate、approval、rollback 和 memory governance | 若无治理，强能力进化可能变成不可控风险 | 新增 Skill Evolution Gate，agent 只能提案和评测，不能直接自改生产能力 |

## 4. UI/UX 分端审计

### 4.1 移动端

| 优先级 | 问题 | 证据 | 建议 |
|---|---|---|---|
| P0 | 智能调查初始加载使用 `useState` 执行副作用 | `mobile/app/(tabs)/investigation.tsx` 当前已改为 `useEffect` + `loadData`；`mobile-device-smoke` 的 result surface guard 保护入口结果展示 | 已代码级收口；真机弱网/重复提交体验仍需设备验收 |
| P0 | 智能调查、法律智库提交后只 `console.log` | `mobile/app/(tabs)/investigation.tsx` 当前调用 `/due-diligence/company`，`mobile/app/(tabs)/knowledge.tsx` 当前调用 `/knowledge/search`，并均有页面内结果摘要卡 | 已代码级收口；真实后端数据、权限和真机 transcript 仍需补 |
| P1 | 品牌主色、状态色硬编码过多 | `mobile/src/constants/colors.ts:1`、`rg` hardcoded hex 结果 | 统一 `brand/status/domain` token，迁移页面级颜色 |
| P1 | 暗色和错误态不一致 | `docs/design/cross-platform-token-drift.md:29` | 给错误/成功/info 背景补 token，暗色下做截图验收 |
| P1 | 真机证据缺失 | `docs/release/evidence/mobile-device-smoke.md:14` | iOS Simulator 已可用，先跑 iOS app-run transcript；Android 需补 AVD 或真机 |

### 4.2 微信小程序

| 优先级 | 问题 | 证据 | 建议 |
|---|---|---|---|
| P0 | 真实 appid/交互验收缺失 | `docs/release/evidence/mobile-device-smoke.md:16` | 用正式测试 appid、测试账号和后端 staging 记录登录、审批、消息、错误态 |
| P1 | token 层已补，但品牌主色仍与 Web canonical 漂移 | `mini-program/src/styles/design-tokens.scss:5` | 确认主色方向后同步 SCSS/TS token |
| P1 | 暗色模式策略未定 | `docs/design/cross-platform-token-drift.md:29` | 明确“不支持暗色”或补 dark token，不要保持隐性不一致 |
| P2 | SCSS 与 TS token 双文件维护 | `mini-program/src/styles/design-tokens.scss`、`design-tokens.ts` | 后续可引入构建期生成，但不作为当前 P0 |

### 4.3 桌面端

| 优先级 | 问题 | 证据 | 建议 |
|---|---|---|---|
| P0 | 桌面云同步数据面仍未商业闭环 | `desktop/src/services/sync_engine.rs:191` 已 fail-closed；`docs/release/evidence/desktop-runtime-smoke.md` 仍 pending | 继续实现/验证真实 push/pull、跨设备延续和 signed packaged runtime，不允许把 unsupported 当完成 |
| P1 | 冲突弹窗直接展示 JSON | `frontend/src/components/mode-switcher/SyncStatus.tsx` 已改为字段差异摘要，原始 JSON 放入高级详情折叠 | 已代码级收口；后续需桌面截图/打包 runtime 复核 |
| P1 | toolbar 同步按钮偏小，冲突按钮文案拥挤 | `frontend/src/components/mode-switcher/SyncStatus.tsx` 已使用 `min-h-9/min-w-9`、不换行状态文案和冲突数字胶囊；`sync-status-ui.test.ts` 锁住按钮尺寸与文案 contract | 已代码级收口；后续需桌面截图/打包 runtime 复核 |
| P1 | 托盘菜单用 emoji 表意 | `desktop/src/services/tray.rs` 已改为纯文本模式标签和 tooltip，并补 `cargo test tray` 回归 | 已代码级收口；后续需 signed/packaged runtime 菜单截图复核 |
| P0 | signed/notarized package 缺失 | `docs/release/evidence/desktop-runtime-smoke.md:3` | 取得签名/公证输入后跑 signed packaged runtime/profile/performance |

## 5. 面向高可信客户与政府试点的额外门槛

| 门槛 | 为什么重要 | 当前差距 |
|---|---|---|
| fail-closed | 政务通知、支付、电签、同步不能因配置缺失而伪成功 | 支付/电签/OA commercial mock fallback 已禁止；桌面同步旧假成功路径已 fail-closed；真实渠道和 signed runtime 证据仍缺 |
| 可审计证据链 | 需要追踪谁、何时、用什么环境完成验收 | release evidence 结构已有，但 payment/e-sign/desktop/mobile 仍 pending |
| 数据安全 | 本地密文、密钥托管、日志脱敏、权限隔离 | SQLCipher/keyring 代码级强；signed desktop 和跨设备证据不足 |
| 无障碍与可用性 | 政府窗口、基层人员、移动端现场使用需要高可读性 | token 漂移、硬编码颜色、触控真机证据不足 |
| 运维交接 | 需要安装、回滚、证书轮换、告警、应急方案 | runbook 初步有，真实演练日志不足 |

## 6. 可实施开发优化方案

| 阶段 | 目标 | 主要任务 | 验收 |
|---|---|---|---|
| Phase 0 清场与基线 | 不让旧文档、缓存、历史索引备份干扰开发 | 更新过时 dirty/GitNexus 陈述；保留 host probe；清理 ignored runtime/cache/旧 `.gitnexus.*` 备份 | 文档 validator、secret scan、`git diff --check` 通过 |
| Phase 1 P0 真实闭环 | 阻断政府交付的假成功和关键入口问题 | provider/OA production fail-closed 已代码级闭环；desktop old sync fallback 禁用；mobile investigation/knowledge 入口已代码级闭环；真机/DevTools evidence | 相关单测、mobile/mini smoke、desktop cargo/frontend tests、commercial gate 失败原因减少 |
| Phase 2 跨端 UI/UX | 让移动/小程序/桌面形成同一套专业体验 | token contract；移动硬编码颜色迁移；小程序暗色策略；桌面冲突管理和托盘菜单改造 | iOS/Android/WeChat/desktop 截图或 transcript，Design Craft gate 复验 |
| Phase 2.5 可信交互 | 把 Codex/Claude 风格工作台体验落进关键路径 | 长任务时间线、工具状态、引用证据、artifact 编辑、暂停/恢复/接管、能力中心和命令面板 | chat/agent e2e、桌面/移动 transcript、artifact 编辑和恢复测试 |
| Phase 3 商业证据 | 从代码级变成可交付证据 | payment/e-sign live sandbox；signed/notarized desktop；cross-device continuation；release runbook 演练 | 所有 evidence `Status: complete`，commercial gate quick 通过 |
| Phase 3.5 进化治理 | 让 Skills 和 agent 能持续改进但不越权 | Skill lifecycle、SkillEvolutionProposal、eval gate、管理员审批、灰度、回滚和记忆治理 | Skill 升级/拒绝/回滚回归测试，审计日志和能力中心证据 |
| Phase 4 政府试点 | 进入小范围真实用户验证 | 试点账号、审计日志、权限矩阵、告警、数据留存、培训材料 | 试点验收记录、问题清单、回滚演练 |

## 7. 确认后建议的多智能体 lane

| Lane | 角色 | 写入范围 | 首要产物 |
|---|---|---|---|
| Backend/Security | 后端与安全 | `backend/src/services/*`、相关 tests、release evidence | 真实 payment/e-sign sandbox、OA 真实 API/审计演练、商业 evidence 状态收口 |
| Desktop | 桌面与同步 | `desktop/src/**`、`frontend/src/components/mode-switcher/**`、desktop scripts | 禁用旧 fallback、冲突 UX、signed package evidence |
| Mobile | React Native | `mobile/app/**`、`mobile/src/**` | investigation/knowledge 闭环、token 迁移、iOS transcript |
| Mini Program | Taro/微信 | `mini-program/src/**`、mobile evidence | appid 环境、交互验收、token/dark 策略 |
| Release Evidence | 文档/门禁 | `docs/release/**`、`scripts/*validation*` | evidence 状态更新、外部输入清单、gate transcript |
| QA/UX | 测试与设计审计 | e2e、截图、审计文档 | 分端 UI/UX 验收报告和回归矩阵 |

## 8. 当前不建议立刻做的事

- 不建议把 payment/e-sign/mobile/desktop evidence 改为 complete，真实证据未齐。
- 不建议在没有政府方或业主确认时强行统一品牌主色，应先冻结 token contract。
- 不建议新增依赖解决 UI 问题，先复用现有 token、组件和测试。
- 不建议启动全量重构。先收 P0 假成功、关键入口、证据闭环。
