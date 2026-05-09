# 商业交付就绪评估

> 日期：2026-05-09
> 判定：Not ready for commercial launch.
> 口径：代码级绿灯不等于商业交付绿灯。发布需要真实渠道、真机、回滚、运营证据，以及中小企业双边平台与全设备智能助手定位的端到端证据。
> 持久目标：`docs/release/goal-contract-commercial-readiness.md`。当前执行顺序为桌面端功能与本地门禁优先，移动 App/小程序随后按 uni-app 统一端迁移；外部 API 先以可替换测试数据和 sandbox contract 完成功能测试，真实密钥到位后再联调。

## 1. 发布判定

| 维度 | 当前状态 | 发布判定 |
|---|---|---|
| 后端默认回归 | `736 passed, 1 skipped, 12 warnings in 44.61s` | 通过代码级门槛 |
| 前端 lint/build/test/security | lint/tsc 通过、最新完整本地门禁中 Vitest `13 files / 51 tests passed`，生产依赖 `npm audit --omit=dev` 已写入 `docs/release/evidence/artifacts/frontend-npm-audit-prod-20260507.json` 且 `0` vulnerabilities；保留既有 Vite chunk/eval warning 作为性能/打包优化项 | 通过当前门槛 |
| GitNexus 知识图 | 当前 `.gitnexus/meta.json` 有非零 embeddings，但 direct GitNexus CLI repo 解析/cypher 复验失败且索引落后于最新本地提交；它只作为最终发布索引卫生与历史上下文，不能推动或替代主线代码、测试、UI/UX、渠道和真机证据 | 最终 release 前再做 commit-scoped 复验；主线推进不再围绕 embedding 排障 |
| 支付真实渠道 | 微信/支付宝代码级协议已落，`scripts/sandbox-evidence-runner.py` 已提供脱敏预检/live 采集入口，runner 安全测试已覆盖 live 确认门和脱敏写出；staging/production 已禁止 mock/未知 provider 静默回落，缺沙箱/证书轮换/重试证据 | 阻断 |
| 电签真实渠道 | e签宝/法大大代码级协议已落，`scripts/sandbox-evidence-runner.py` 已提供脱敏预检/live 采集入口，runner 安全测试已覆盖 live 确认门和脱敏写出；staging/production 已禁止 mock/未知 provider 静默回落，flow 操作已按当前用户组织过滤合同，缺商户沙箱/事件目录/灰度证据 | 阻断 |
| 桌面同步 | 后端 `SyncLog` 持久化增量日志 + Rust SQLCipher/keyring 本地库 + 注入式同步闭环测试 + SQLite migration SQL fresh/legacy temp DB smoke + local installed-profile keyring/reopen smoke + SQLite 100/500 本地性能基线 + debug binary self-test + 冲突管理页 + 代码级重试退避 + `scripts/desktop-sqlite-security-gate.sh` 安全门禁通过；`SyncStatus` 冲突弹窗已改为字段差异摘要 + 原始数据折叠详情，桌面工具栏同步/冲突入口已改为稳定尺寸、不换行状态文案和冲突数字胶囊，托盘模式菜单/tooltip 已移除 emoji 依赖并有回归测试；既有 artifact 记录过 unsigned debug macOS `.app` bundle self-test/runtime/WebView page-load，但 fresh local 复跑当前 AppKit abort，不能作为稳定 passing evidence；`desktop/Entitlements.plist` 已切到 production APNs entitlement；`scripts/desktop-release-package.sh --dry-run` 和 `scripts/desktop-release-preflight.sh` 已写出脱敏预检并新增 `hdiutil` / DiskManagement probe；unsigned release `.app` + DMG 已在 unsandboxed macOS 环境构建通过；unsigned release packaged runtime self-test/startup/WebView page-load smoke 已通过；unsigned release packaged-profile plaintext-to-SQLCipher/keyring reopen 和 SQLCipher 100/500 performance smoke 已通过；签名/公证、signed installer/signed packaged-profile migration/signed packaged runtime 性能/跨端连续会话未闭环 | 阻断 |
| RAG/案件/专业服务/风险 | RAG P0-2 引用回链已有代码级闭环，live Qdrant smoke 已跑，内建法律知识库 full50 已跑通 `42` chunks / `50` questions / recall@10 `1.000` / MRR `1.000` / NDCG@10 `0.997`，`knowledge_management` RBAC/PII 已补，图谱 1k 降采样/FPS smoke 已补；案件状态机/任务 owner、律师市场 local guard/冲突阻断/公平轮询、尽调缓存 org 隔离、风险评分解释性、爬虫合规入口、200 条意图路由评测已补；知识管理持久化、案件/市场全矩阵、税务/财务等专业服务方预留、舆情转专业处置与获客闭环仍未闭合 | 部分完成 |
| 移动/小程序真机 | `scripts/mobile-device-smoke.sh` 已通过本地门禁：移动端 `8 files / 37 tests`、tsc、mobile result surface guard、mobile lawyer conversion guard、desktop-control status endpoint/local-mode no-network regressions、Expo config/SDK/Metro config guard、小程序 tsc/build、mini-program privacy boundary guard、mini-program navigation boundary guard、WeChat DevTools CLI project smoke、refresh auth guard、mobile/mini privacy network guard、fake fallback guard、mini-program design token guard；`npx expo-doctor` `17/17 checks passed`；2026-05-09 artifact `mobile-mini-code-smoke-20260509.json` 记录移动 production `npm audit --omit=dev` 已通过 `@babel/plugin-transform-modules-systemjs@7.29.4`、`fast-uri@3.1.2` 等定向 overrides 清零，并保持 `release_evidence_complete=false`；`scripts/mobile-ios-simulator-smoke.sh` 已生成 iPhone 17 Simulator + Expo Go 支持性 app-run 证据并完成 `iOS Bundled`，但 artifact 明确 `release_evidence_complete=false`；messages/tasks 详情页已移除静默假数据兜底；小程序首页/个人中心主入口不再有空路径或“功能开发中”死胡同；尽调与知识库搜索入口已改为真实 API + 加载/错误态 + 页面内结果摘要卡；移动端找律师已具备匿名咨询转化链路，不再只是律师列表；移动端 `/desktop-control` local 模式不发网络请求，confirmed pairing 下可先申请短期 route token 再只入队 `desktop.status_probe`，后端也会拒绝非 safe-probe 命令入队并写 `unsupported_command_type` 审计，并支持刷新 queued 命令状态、取消 queued/claimed 探针和查看脱敏审计时间线，且仍不伪造桌面执行成功；移动/小程序 refresh-token 已避免弱网误清会话；小程序 local/top-secret 会在数据请求与登录前 fail-closed；2026-05-09 已决定后续移动 App/小程序统一转向 uni-app，旧 `mobile/` Expo 与 `mini-program/` Taro 标记 legacy；`apps/uni-mobile/` 首版基座已通过 `scripts/uni-mobile-smoke.sh`，包含 typecheck、`4 files / 10 tests`、production npm audit `0`、H5 build 和 WeChat Mini Program build；仍缺真实/官方 iOS 设备故事、Android、交互式微信开发者工具、DCloud App 云打包/签名、跨设备连续会话和完整真机验收 | 阻断 |
| 全设备智能助手定位 | 后端已有 LLM、private LLM、MCP、Skills、knowledge 代码底座；CLI Key 已绑定登录用户与最小 scope，并写入 key/execute 审计，CLI route-token 签发与桌面端 execute 前获取/传递已补；MCP 管理 API 已收紧到 `manage:system`，管理动作写入脱敏审计，独立 MCP 商业环境默认关闭；MCP 外部连接已补 stdio 默认关闭、command/command-line/env allowlist、SSE scheme/host allowlist 和子进程最小环境；LLM 配置 API 已补组织级 CRUD 边界、默认配置同组织隔离和 API key 遮罩响应；前端 Settings 与后台模型配置页已复用组织级 `/llm/configs` 面板，遮罩展示已保存密钥，编辑元数据时不回传 `api_key`，新增或显式替换时才发送密钥；后端 `/skill-governance/connectors` 已补 Skills connector 组织级凭据配置 CRUD，保存 `encrypted_fields`，响应和审计只暴露 `credential_keys`，元数据编辑默认保留已保存密钥；Agent 治理工作台已补 Skills connector 前端凭据体验，编辑元数据默认保留密钥，新增/替换/清空均走受控 payload，界面只展示 `credential_keys`；agent capability policy 已补未知工具 fail-closed、订阅/权限/隐私/设备/通道/审批上下文、服务层单次可审计统一能力决策和 MCP tool runtime 二次判权；桌面已有 local LLM 命令、SQLCipher/keyring、本地队列，以及 TopSecret CLI/sync/Harness IPC、本地同步桥、统一 API fetch、WebView 全局 fetch/WebSocket 出站 guard；Tauri 原生 HTTP 插件、前端 HTTP 插件包、活跃 `http:*` capability、宽泛 shell/opener launch capability 和宽松 CSP 已由 `scripts/desktop-network-surface-gate.sh` 收紧；移动已有隐私模式和本地模型语义；`/settings?tab=workstation` 已补桌面主工作站最小入口、本地 LLM/模型数量/离线队列、知识库/MCP 只读探针、移动远控安全闸和 secret-free 环境配置档 CRUD，并用模型测试锁住绝密模式下同步/远控不启用、知识库/MCP 数据网络探针跳过、非桌面预览不启用本地模型/同步/远控动作；后端 `/sync/remote-control/*` 已补 DB-backed 移动远控控制面和 host lifecycle API，锁住本地/绝密模式、桌面确认、CapabilityRoute route-token、safe-probe-only 命令队列、非 safe-probe 入队拒绝和审计、host 领取、running/completed/failed 状态回传、取消和递归脱敏审计；桌面 Tauri IPC host 客户端已能按登录态 bearer token 调用 confirm/claim/status API，且单次 host cycle 只完成 safe probe、未知命令 failed/unsupported，并新增 bounded safe-probe poll 命令，由 TopSecret guard 与 payload/状态/轮询配置单测锁住；移动端 `/desktop-control` 已接入该安全闸，confirmed pairing 下只允许申请短期 route token 并入队 `desktop.status_probe`，并可刷新/取消未终态探针、查看脱敏审计时间线，不提供假执行成功；Playwright 已覆盖 direct/legacy route、tab URL 写回、非桌面禁用态、模拟桌面运行时探针、环境配置档保存/编辑/应用/删除和移动宽度不越界 | 真实 provider 密钥联调、任意 Skills/MCP 可配置验收、真实 approved MCP connector 演练、真正常驻后台 daemon 与高风险真实执行器、真实移动远控跨设备联调、绝密模式 signed packaged runtime 出站复验证据仍缺 |
| 可信会话与 Skills 进化 | OpenSpec 已纳入 Codex/Claude 式过程可见、artifact-first、可打断/恢复和能力可发现体验；本地 `SkillEvolutionService` 已覆盖 proposal、required eval、授权审批、灰度、回滚、审计和 governed `SkillService` 版本过滤；DB-backed `SkillGovernanceService` 与 `/skill-governance` API 已覆盖 proposal、required eval、授权审批、灰度启用、回滚、enabled version 持久化、组织隔离、API scope、audit-events、audit-export、append-only audit 和 migration upgrade/downgrade；AgentApproval/AgentAuditEvent 模型、AgentApprovalService 和 `/agent-approvals` API 已补，覆盖高风险审批创建、组织/本人 scope、授权角色审批/驳回、撤销、执行前 validate、过期/撤销 fail-closed、action/route 匹配、payload 脱敏、审计写入、scoped audit-events API、audit-export API、workspace-control fail-closed、workspace artifact list/create/export，以及组织 CapabilityRoute list/update、policy 脱敏和禁用撤销 lease；MemoryLayer 已补 governed session artifact 写入入口，local/top-secret 模式拒绝持久化、org/user scope 与 consent 必填、artifact payload 递归脱敏，并由 `backend/tests/test_memory_governance.py` 锁住；前端最小 `Agent 治理工作台` 已支持审批列表/count、状态筛选、风险 payload 预览、批准/驳回/撤销、审批审计时间线、审批审计 JSON 导出、运行时未接入时控制动作拒绝提示、按组织角色过滤的能力策略可用/可申请/隐藏工具可视化、组织 route 启用/禁用、工作室成果查看/新增/导出、Skill 提案创建、评测、批准、灰度、审计时间线、审计 JSON 导出、Skill connector 凭据保留/替换/清空/删除、桌面侧边栏入口和移动协作导航高亮，并有 Playwright 桌面/移动回归；2026-05-09 `scripts/agent-governance-smoke.sh` 已写出 `agent-governance-code-smoke-20260509.json`，覆盖 docs scan、后端治理回归、桌面 remote-control host、前端 Skill connector 凭据模型和前端治理工作台，但明确 `release_evidence_complete=false` / `runtime_evidence_complete=false` | 长任务时间线、runtime 产物生成、artifact 编辑、跨设备恢复、完整记忆治理 UI/运行时接入、完整 Human-in-the-loop 旁听、真实暂停/接管/终止执行效果、真实执行链路失权和商业发布证据仍缺 |
| 发布证据脱敏 | `scripts/release-evidence-secret-scan.sh` 已纳入商业门禁，当前 `docs/release/evidence/` 未发现明文私钥、access/refresh token、手机号或身份证号 | 通过当前门槛；后续新增真实日志/JSON 后必须复跑 |

## 2. 必须补齐的商业证据

### 渠道沙箱

- 微信支付：下单、查单、关单、退款、支付成功回调、平台证书/公钥轮换、失败重试。
- 支付宝：page.pay、query、refund、close、异步通知、notify_id 重试。
- e签宝：创建/启动流程、签署链接、状态查询、签署完成回调、撤销、签署文件下载。
- 法大大：access token、sign-task create、actor url、detail、download url、cancel、FASC 回调事件。

### 产品闭环

- 桌面端本地数据 push/pull 已有 Rust SQLCipher/keyring 代码路径、注入式 push/pull/retry 测试、SQLite migration SQL fresh/legacy temp DB smoke、SQLCipher plaintext migration 单测、local installed-profile keyring/reopen smoke、SQLite 100/500 本地性能基线、debug binary migration/table/security self-test、冲突管理页、代码级 retry/backoff、桌面 SQLite 安全门禁、production APNs entitlement、release package dry-run、signed/notarized release preflight、unsigned release `.app`/DMG build、unsigned release packaged runtime smoke、unsigned release packaged-profile migration smoke 和 unsigned release packaged SQLCipher performance smoke；还需配置签名/公证身份，产出 signed/notarized release `.app`/DMG、补 signed packaged-profile plaintext migration 实装证据、signed packaged runtime 性能和跨端连续会话证据。
- 桌面主工作站统一入口已补最小可见状态：用户可在设置页看到隐私模式、本地模型、独立知识库、Skills/MCP、跨端同步和移动远控状态，且绝密模式不会展示会导致数据出站的可执行同步/远控动作；非桌面预览下，本地模型、同步和移动远控保持 disabled，避免把浏览器/手机误呈现为桌面控制台；桌面运行时下已通过现有 Tauri IPC 和受治理前端 API 只读展示本地 LLM 可用性、模型数量、离线队列、知识库数量/文档数和 MCP 服务/启用/工具缓存统计，绝密模式会跳过知识库/MCP 数据网络探针，并把移动远控保持在安全闸/待验收状态；浏览器级 e2e 已覆盖 workstation/legacy privacy route、URL 写回、模拟桌面运行时探针、secret-free 环境配置档 CRUD 和 iPhone 14 视口资源卡不越界；后端 LLM 配置 API 已补组织级 CRUD 边界、同组织默认配置隔离和 API key 遮罩响应；前端 Settings 与后台模型配置页已复用组织级 `/llm/configs` 面板，遮罩展示已保存密钥，编辑元数据时不回传 `api_key`，新增或显式替换时才发送密钥；后端 `/skill-governance/connectors` 已补 Skills connector 组织级凭据配置 CRUD，保存 `encrypted_fields`，响应和审计只暴露 `credential_keys`，元数据编辑默认保留已保存密钥；Agent 治理工作台已补 Skills connector 前端凭据体验，支持创建、编辑、保留/替换/清空凭据、启停和删除，列表只展示键名；后端移动远控 API 已补 DB-backed 配对、桌面确认、route-token、命令队列、host 领取、running/completed/failed 状态回传、取消和递归脱敏审计，桌面 Tauri IPC host 客户端已能确认配对、领取命令、回传状态、显式运行 safe-probe 单次循环，并新增有间隔/次数/limit 上限的 bounded safe-probe poll，移动端 `/desktop-control` 已把该安全闸推进到 safe-probe 入队、撤销与审计可见面：只在 confirmed pairing 同时具备 `desktop_device_id` 和 `pairing_id` 时申请短期 route token 并入队 `desktop.status_probe`，可刷新命令状态、取消 queued/claimed 探针并查看脱敏审计时间线，同时保留 local 零网络和“不声称已执行”的边界；当前 CLI/MCP、外部 MCP allowlist、MCP tool execution route-token、CLI `/execute` route-token、CLI route-token 签发与桌面端 execute 前获取/传递、REST/SSE/WebSocket Chat Agent LLM route-token、RAG direct LLM route-token、桌面 IPC TopSecret guard、WebView/API data-network guard、Tauri/前端 HTTP 插件移除、CSP 收紧、agent capability policy、服务层 unified capability policy engine、短期 route-token broker、Agent 控制面模型/迁移、DB-backed AgentGovernanceService、AgentApprovalService、DB-backed SkillGovernanceService、`/agent-approvals` API、`/skill-governance` API、Harness 能力策略 API 和最小 Agent 治理工作台已先做最小权限/fail-closed 加固，模型层已包含复合租户外键、TokenLease/SkillEnabledVersion 边界、hash-only token 和审计不可变防线，服务/API/UI 层已覆盖跨实例验证、组织隔离、consumer/scope 拒绝、consumer mismatch、过期、route 撤销后下一次调用失败、统一能力决策审计、按组织角色过滤的能力策略可用/可申请/隐藏工具展示、高风险审批组织/本人 scope、普通员工自批拒绝、管理员 approve/revoke、执行前 validate、过期/撤销/action/route mismatch 拒绝、payload 脱敏、审批审计时间线、审批审计 JSON 导出、workspace-control 未接入运行时前 fail-closed、Skill proposal/eval/approval/gray/rollback 持久化、Skill API scope、Skill 前端提案/评测/批准/灰度/审计导出、Skill connector 凭据保留/新增/替换/删除且不渲染明文 secret、桌面控制拒绝提示、桌面批准动作和移动端不横向溢出；2026-05-09 已补桌面工作站配置档 CRUD：桌面客户端可本地切换绝密/混合/云端模式、保存 http/https 后端环境地址，并创建/编辑/应用/删除不含密钥的常用环境配置档，非桌面预览保持只读，且绝密模式远控仍显示阻断；但还缺真实 provider 密钥联调、完整 browser automation 和 desktop-control 运行时集成、真实 approved MCP connector 演练、signed packaged runtime 出站复验、工具调用细粒度审计和真实能力链路撤销后立即失权；移动远控桌面还需补真正常驻后台 daemon、高风险真实执行器、真实跨设备联调和真机证据。
- REST/SSE/WebSocket Chat Agent LLM runtime 与 RAG direct LLM 已补 DB-backed `llm:chat` route-token gate，`/chat/route-token` 可签发用户绑定短期 token，WebSocket 可通过 auth 首包、连接 header 或单条消息 payload 传递 route-token，REST Knowledge RAG、同步 Chat RAG 与 WebSocket RAG 会把 route context 传入 `RAGService`，商业环境下 Agent 同步/流式模型调用以及 RAG generation/query expansion/entity extraction/stream generation 都会在真实 HTTP/本地模型调用前 fail-closed；当前证据是 `backend/tests/test_llm_route_governance.py` `11 passed`。浏览器/爬虫 fetch 入口也已补 DB-backed `browser:fetch` route-token gate：商业环境下授权发生在 robots/http 触网前，缺 token、consumer/scope 不匹配或 route 撤销都会 fail-closed；尽调执行信息/信用中国/裁判文书查询已移除直接 Playwright fallback，只走合规 crawl service 或返回无外部证据；当前证据是 `backend/tests/test_crawler_compliance.py` `7 passed`，`backend/tests/test_due_diligence_intent.py` + `backend/tests/test_chat_due_diligence_routing.py` `21 passed`，仍不替代完整 browser automation、desktop-control 和真实 connector runtime 证据。
- 可信 AI 交互还需补长任务过程可见、工具状态、证据引用、runtime 产物生成、artifact 编辑、真实暂停/恢复/接管/终止执行效果、命令面板和跨设备继续证据；Skills 进化已有本地和 DB-backed proposal/eval/approval/gray release/rollback/audit gate、版本过滤测试、最小前端治理面板、组织 route 启用/禁用面板、workspace artifact 面板和 workspace-control fail-closed 回归；记忆治理已补 local/top-secret 拒绝、org/user/consent gate 和 artifact 脱敏的代码级入口，但还需补完整策略编辑器、订阅/部门申请流、真实运行时接入、真实执行链路失权和商业发布证据。
- RAG 权限过滤、PII 脱敏、source 字段、前端引用预览/高亮、Playwright 点击证据、导出文档/chunk/anchor 巡检、live Qdrant smoke 和内建法律知识库 full50 live baseline 已有证据。
- 案件状态机、任务 owner、律师市场 local guard/利益冲突/公平轮询已有核心正反向测试；仍需律所 RBAC 全矩阵、案源市场 8 API 打勾、Playwright 三角联通，以及税务师/税务事务所/财务顾问/会计审计等专业服务方模型预留证据。
- 风险调查已补尽调缓存 org 隔离、风险评分解释性、crawler 合规入口和 200 条意图路由评测；仍需在预发网络补真实 dry-run 日志。
- 移动端和小程序真机覆盖登录、审批、消息/任务详情、会话延续、错误态；本地 fake fallback guard、iOS Simulator Expo Go app-run 和 `apps/uni-mobile` 代码级基座 smoke 已过，但真实/官方 iOS、Android、交互式微信开发者工具、DCloud App 云打包/签名、跨设备和桌面远控证据仍需补齐。2026-05-09 起新功能按 uni-app 统一端推进，旧 Expo/Taro 端只做安全修复和迁移提取，删除必须等 uni-app 同等能力、测试和真机/DevTools 证据补齐。

## 3. 发布前必须通过的命令

```bash
cd backend && ./.venv/bin/pytest -q
cd backend && ./.venv/bin/ruff check src tests
cd backend && ./.venv/bin/mypy src
cd backend && ./.venv/bin/pytest -q tests/test_config_commercial_guards.py tests/test_harness.py -k 'mcp or PolicyEngine or AgentMcpToolPolicy'
cd backend && ./.venv/bin/pytest -q tests/test_agent_governance_policy.py tests/test_capability_routes.py tests/test_agent_governance_models.py tests/test_agent_governance_service.py tests/test_mcp_route_governance.py
cd backend && ./.venv/bin/pytest -q tests/test_business_authorization_guards.py -k 'approval or template'
cd backend && ./.venv/bin/pytest -q tests/test_skill_evolution_service.py tests/test_skill_service.py tests/test_skill_governance_models.py tests/test_skill_governance_service.py tests/test_skill_governance_api.py
cd backend && ./.venv/bin/pytest -q tests/test_remote_control_fail_closed.py
cd frontend && npm run lint
cd frontend && npm test
cd frontend && npm run build
cd frontend && npx playwright test e2e/settings-workstation.spec.ts --project=chromium --project=mobile
cd frontend && npx playwright test e2e/agent-approval-workspace.spec.ts --project=chromium --project=mobile
cd frontend && npx playwright test e2e/role-access.spec.ts e2e/document-flows.spec.ts e2e/contract-lifecycle.spec.ts --project=chromium
bash scripts/mobile-device-smoke.sh
bash scripts/uni-mobile-smoke.sh \
  --out docs/release/evidence/artifacts/uni-mobile-base-smoke-YYYYMMDD.json
bash scripts/mobile-ios-simulator-smoke.sh \
  --out docs/release/evidence/artifacts/mobile-ios-simulator-expo-go-smoke-YYYYMMDD.json \
  --log-out docs/release/evidence/artifacts/mobile-ios-simulator-expo-go-smoke-YYYYMMDD.log
python3 scripts/sandbox-evidence-runner.py --scope payment --out docs/release/evidence/artifacts/payment-sandbox-preflight-YYYYMMDD.json
python3 scripts/sandbox-evidence-runner.py --scope esign --out docs/release/evidence/artifacts/esign-sandbox-preflight-YYYYMMDD.json
bash scripts/release-evidence-secret-scan.sh
cd desktop && cargo check
cd desktop && cargo test
bash scripts/desktop-sqlite-security-gate.sh
bash scripts/desktop-network-surface-gate.sh
bash scripts/desktop-runtime-smoke.sh --with-app-bundle \
  --out docs/release/evidence/artifacts/desktop-runtime-code-smoke-YYYYMMDD.json \
  --ui-log-out docs/release/evidence/artifacts/desktop-runtime-ui-smoke-YYYYMMDD.log
bash scripts/desktop-installed-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-installed-profile-smoke-YYYYMMDD.json
bash scripts/desktop-release-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-release-profile-unsigned-smoke-YYYYMMDD.json
bash scripts/desktop-release-preflight.sh --out docs/release/evidence/artifacts/desktop-release-preflight-YYYYMMDD.json
```

当前 Ruff 与 backend mypy 均已清零；`scripts/mypy-baseline-check.sh` 默认 ceiling 已降为 `0`，任何新增 mypy 错误都应阻断发布。`docs/release/evidence/static-quality-baseline.md` 已记录当前 owner、2026-05-20 过期策略和零回退规则。

## 4. 当前完成度审计

最新 prompt-to-artifact 审计见 `docs/release/completion-audit.md`。该审计明确当前目标尚未完成，阻断项集中在支付/电签真实沙箱、桌面 signed/packaged runtime 和移动/小程序真机。

商业发布 gate：

```bash
bash scripts/commercial-readiness-gate.sh --quick
```

当前该命令应当失败；RAG 内建 full50、桌面 SQLCipher/keyring 代码级门禁、unsigned release `.app`/DMG build、unsigned release packaged runtime smoke、unsigned release packaged-profile/performance smoke 和 signed/notarized release preflight 已通过，但只有当外部证据、桌面 signed/packaged-profile/performance/cross-device 证据、移动真机、企业智能体治理 runtime evidence、全仓质量基线和最终提交 GitNexus 复验全部补齐后才允许转 Go。
GitNexus metadata 是 commit-scoped，只用于最终发布索引卫生检查。`scripts/commercial-readiness-gate.sh` 仍会将 dirty worktree、direct CLI cypher integrity failure 和 indexed/current commit 不一致作为 release-blocking failure；但在当前开发主线上，GitNexus embedding 不再作为优先排障项，不能替代源码审查、测试、UI/UX、渠道或真机证据。

外部证据模板位于 `docs/release/evidence/`，每份模板只有在对应真实证据齐全后才能把 `Status: pending` 改为 `Status: complete`。
并行采集执行清单见 `docs/release/evidence-collection-runbook.md`；支付、电签、桌面、RAG 和移动/小程序可以并行采集，但最终必须统一回到本文件和 `scripts/commercial-readiness-gate.sh`。
外部输入缺口集中见 `docs/release/external-inputs-checklist.md`，用于拆给支付/电签/桌面/RAG/真机负责人并行准备。
商业门禁会拒绝“顶部已标 complete，但 Owner/Environment/Date range 仍是 TBD、Required Scope 表格仍含 pending/TBD/缺失信号，或 artifact reference 为空”的 evidence 文件；不能只改状态行绕过验收。

## 5. Go/No-Go 标准

Go 条件：

- 所有 P0 任务关闭，且每项有测试/沙箱/真机证据。
- release 文档齐全并与当前代码一致。
- 支付、电签、对象存储、同步均有失败/重试/幂等/回滚测试。
- 桌面主工作站、移动远控、任意 LLM/Skills/MCP、独立知识库和绝密模式出站拦截均有可复跑证据。
- 长任务可信会话、artifact-first 工作流、可打断/恢复和 Skills 进化治理有可复跑证据。
- 生产密钥轮换、日志脱敏、审计和监控告警已演练。

No-Go 条件：

- 任一真实渠道仅有 mock/fake client 证据。
- GitNexus 图谱显示低风险但 `rg`/源码显示新增未入图符号。
- GitNexus metadata up-to-date 但工作树仍有未提交或未跟踪交付文件。
- 任一移动/小程序/桌面关键路径仍通过静默 fallback 掩盖后端错误。
- 数据迁移无 downgrade 或恢复演练。
