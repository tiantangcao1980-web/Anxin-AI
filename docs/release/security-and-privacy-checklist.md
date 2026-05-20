# 安全与隐私发布清单

> 日期：2026-05-09
> 判定：发布前必须逐项复核。当前有若干项仍未达到 Go 条件。

## 1. 认证与会话

| 检查项 | 当前状态 | 发布要求 |
|---|---|---|
| access token 不长期存 localStorage | Web 源码已改为内存 access token | 移动/桌面策略仍需审计 |
| refresh token HttpOnly cookie | 已完成 Web 主路径，body compat 默认关闭 | 发布前确认旧客户端迁移窗口 |
| reset token 只存 hash | 已完成 | 继续保留 IP/UA/过期审计 |
| Redis 敏感入口 fail-closed | 认证限流和 refresh blacklist 已覆盖 | session/CAPTCHA 仍需补全审计 |
| 小程序登录 | `wx.login -> code2session -> JWT`，不下发 `session_key` | 需要真机/测试环境 7 天验证 |

## 2. 权限与租户隔离

- LLM 配置必须按组织隔离；当前 LLM provider 配置 API 已补创建绑定当前组织、读取/更新/删除/设为默认/启停/测试已保存配置前按组织 scope 查找、默认配置只清同组织默认项，以及响应仅返回 `api_key_masked` 的回归测试；前端组织级模型配置入口已收束到治理后台“模型治理”，我的设置不再承载组织级 LLM/MCP 凭据 CRUD，模型配置面板编辑元数据时省略 `api_key`，避免把空输入或遮罩值写回为真实密钥；MCP/工具连接已迁入治理后台“系统集成”；superuser 全局例外后续变更仍必须保留显式测试。
- Skills connector 配置必须按组织隔离；当前 `skill_connector_configs` 只保存 connector 元数据与加密后的 `encrypted_fields`，`/skill-governance/connectors` 为管理员级 CRUD，响应和审计只暴露 `credential_keys`，元数据更新默认保留已保存凭据，只有显式传入 `credentials` 才替换或清空；Agent 治理工作台前端也只展示 key 名，编辑已有连接器默认不回传 `credentials`，新增/替换/清空均由显式凭据动作触发。
- 任意 LLM provider/endpoint/model/key、Skills 和 MCP Server 配置必须按组织/用户 scope 隔离，启用前有最小权限说明，调用后有审计日志。
- 当前 CLI Key 与 execute 已写入审计日志，CLI `/execute` 已在 staging/production 默认要求 DB-backed route token 并按 API Key `key_id` 绑定 consumer，后端 `/cli/route-token` 与桌面端 execute 前 route-token 获取/传递已补；MCP Server 管理 API 已收紧到 `manage:system`，管理动作写入脱敏审计，独立 MCP Server 在 staging/production 默认关闭；外部 MCP 连接已补 stdio 默认关闭、stdio command/command-line/env allowlist、SSE scheme/host allowlist 和子进程不继承全量环境变量的基线；MCP tool execution 已在 staging/production 默认要求 DB-backed route token，并支持 Agent context 传递到真实 `call_tool`；REST/SSE/WebSocket Chat Agent LLM runtime 与 RAG direct LLM 已在 staging/production 默认要求 DB-backed `llm:chat` route token，`/chat/route-token` 可签发用户绑定短期 token，WebSocket auth 首包、连接 header 或单条消息 payload 可传递 route-token，REST Knowledge RAG、同步 Chat RAG 和 WebSocket RAG 会传递 route context，Agent 同步/流式模型调用以及 RAG generation/query expansion/entity extraction/stream generation 均在真实 HTTP/本地模型调用前 fail-closed；浏览器/爬虫 fetch 已在 staging/production 默认要求 DB-backed `browser:fetch` route token，并在 robots/http 触网前 fail-closed；尽调执行信息/信用中国/裁判文书查询已移除直接 Playwright fallback，只走合规 crawl service 或返回无外部证据；桌面 CLI/sync/Harness IPC、本地同步桥、统一 API fetch、WebView 全局 fetch 与 WebSocket 已补 TopSecret data-network guard；移动端请求层已透传 `X-Privacy-Mode` 且 local 模式在 fetch 前 fail-closed，移动端 `/desktop-control` local 模式不检查网络，hybrid/cloud 读取 `/sync/remote-control/status` 与 `/sync/remote-control/audit-events` 安全闸，并且只有 confirmed pairing 才能申请短期 route token 后入队 `desktop.status_probe`、刷新状态、取消 queued/claimed 探针和展示脱敏审计时间线；小程序请求层已透传 `X-Privacy-Mode`，local/top-secret 会在 `Taro.request` 前 fail-closed，登录入口会在 `Taro.login` 前阻断；Tauri 原生 HTTP 插件和前端 HTTP 插件包已移除，默认 capability 不再启用 `http:*`、`shell:allow-open` 或宽泛 `opener:*`，CSP 已收紧并由 `scripts/desktop-network-surface-gate.sh` 守住；设置页工作站入口已用 `desktopWorkstationModel` 锁住 TopSecret 下同步/远控 action disabled，桌面 host 可见控制面也会在 TopSecret/非桌面预览下禁用确认配对、safe-probe 和取消命令；后端 `/sync/remote-control/*` 已补 DB-backed 配对、桌面确认、pairing-scoped `desktop:control` route token、safe-probe-only 命令队列、非 safe-probe 入队 403 拒绝和 `unsupported_command_type` 审计、host 领取、running/completed/failed 状态回传、取消和递归脱敏审计，并锁住绝密/本地模式、缺二次确认、缺配对或缺 route token 的请求；桌面端已补受登录态 bearer token、route token 和 TopSecret guard 约束的 confirm/claim/status IPC host 客户端，单次 host cycle、bounded host poll 和 env-gated 后台 safe-probe daemon 只允许 safe probe completed，未知命令 failed/unsupported，daemon 在 TopSecret 或缺登录/测试 bearer 时网络前阻断，且本地 mock 后端测试覆盖 claim -> running -> completed safe-probe 回路；agent capability policy 已补未注册工具 fail-closed、订阅 feature、角色 permission、隐私模式、设备信任、通道策略和审批上下文判定，服务层 `CapabilityPolicyEngine` 已把订阅、角色、权限、风险、隐私、设备、通道、CapabilityRoute 和 AgentApproval 合并为单次可审计决策，并在 agent MCP tool list、Harness 可用工具列表与 runtime tool call 前二次判权；短期 route-token broker 已补 hash-only storage、scope check、revocation next-call failure、expiration 和 audit event 代码级防线；Agent 控制面持久化模型与迁移已补，覆盖复合租户外键、TokenLease hash-only、raw token 不入库和审计 update/delete 防线；DB-backed AgentGovernanceService 已补跨实例验证、跨服务实例撤销后长生命周期 worker session 刷新、组织隔离、consumer/scope 拒绝、过期和 route 撤销后下一次调用失败；发布前仍需把 CapabilityRoute/TokenLease/AgentApproval/AgentAuditEvent 接入完整 browser automation、desktop-control 运行时、补工具调用细粒度审计、真实 approved MCP connector runtime 证据、商业多进程撤销运行时证据、signed runtime daemon 运行证据与高风险真实执行器、桌面 signed/notarized packaged runtime 出站拦截复验和移动/小程序真机出站证据。
- 审批流已补本地授权防线：普通成员不能批量审批他人/跨组织审批；审批列表按用户/组织 scope 过滤；`admin` 按 `org_admin` 语义只管本组织，只有 `super_admin` 可全局；模板写入仅限 `admin/org_admin/super_admin` 且模板读取/使用按创建者或全局管理员过滤；过期审批不能 approve/reject/batch 继续执行。AgentApprovalService 和 `/agent-approvals` API 已补高风险智能体审批的创建、组织/本人 scope、payload 脱敏、授权角色审批/驳回、撤销、执行前 validate、过期/撤销 fail-closed、action/route 匹配、审计写入、scoped audit-events API、audit-export API、已授权 observe 只读旁听快照、默认 pause/takeover/terminate workspace-control fail-closed，以及显式 `workspace_runtime.mode=local_rehearsal` 的无外部副作用本地控制 rehearsal；前端最小 Agent Approval 工作台已补状态筛选、风险动作/payload 预览、批准/驳回/撤销、审批审计时间线、审批审计 JSON 导出、旁听快照、运行时未接入时控制动作拒绝提示和移动端视口回归。商业发布前仍需补真实暂停/接管/终止执行效果和组织级模板 schema。
- Skills 进化已补本地与 DB-backed SkillGovernance gate：agent 只能创建 draft proposal；required eval checks 未齐或失败时拒绝审批；审批角色限制为 owner/boss/super_admin/org_admin/admin；灰度绑定具体版本；回滚后 `SkillService` governed 版本过滤立即回到上一版本；`/skill-governance` proposal/eval/approval/gray/rollback/enabled-version/audit 与 connector credential backend/front-end CRUD 已有组织隔离、凭据保留/替换/清空和脱敏回归；商业发布前仍需补组织级能力中心完整 UI、记忆治理、真实执行链路 route/token 撤销联动、真实 connector runtime 证据和运行时审计导出。
- 企业组织默认只开放 L0/L1 基础能力；完整能力必须同时满足订阅/购买状态、老板或 Owner/超级管理员授权、角色权限、风险级别、隐私模式、设备信任、通信策略和审批状态。
- Agent/Worker 不得持有真实 API key、PAT、财税接口密钥、浏览器账号密码或桌面本地密钥；必须通过 Gateway/密钥服务发放短期 consumer token 或 route token，撤销后下一次调用必须 401/403 并写审计；当前 `capability_route_service` 已提供本地最小 broker，CapabilityRoute/TokenLease/AgentApproval/AgentAuditEvent 持久化模型与迁移、DB-backed route-token 服务、MCP tool execution route-token 边界、CLI route-token 签发/execute 传递边界、REST/SSE/WebSocket Chat Agent LLM route-token 边界、RAG direct LLM route-token 边界以及浏览器/爬虫 fetch route-token 边界已补，商业发布前还需完整 browser automation/desktop-control 真实能力调用链集成和商业运行时商业运行时跨进程撤销失权证据。
- 外部资源清单不得保存真实凭据或证书内容；`docs/release/external-resource-requirements.json` 只允许记录 env 名、runner 参数、artifact 字段、账号/设备标签和命令引用，`scripts/validate-external-resource-requirements.cjs` 会拒绝 `value/api_key/private_key/token/session_key/password` 等真实值字段，并检查 P0 env 与 `.env.example` / `backend/.env.example` 同步。
- 高风险智能体动作必须进入可审计工作室，支持旁听、暂停、接管、终止、导出 artifact；外部专业服务方只能访问授权材料包和沟通区。
- 文档、合同、附件、知识库、订阅、IM conversation 必须按 org/user/client_type 隔离。
- 专业服务市场、案件、任务、风险调查、舆情和获客仍需逐模块 P0 权限矩阵；P0 先覆盖律师/律所，后续扩展税务/财务服务方。
- A2UI/action 必须带鉴权上下文，未知组件/事件不能白屏。

## 3. 支付、电签与 webhook

- 所有官方 webhook 必须验签和校验时间窗。
- `webhook_received` 必须以官方 event id / notify id 做幂等。
- 失败事件必须进入 failed/retry，不允许假 success。
- 支付和电签真实沙箱未完成前，不允许标记商业 Go。
- 密钥包括 `WECHAT_PAY_*`、`ALIPAY_*`、`ESIGN_BAO_*`、`FADADA_*`，必须完成轮换演练。

## 4. 数据与文件

- 上传入口必须校验扩展名、MIME、大小和 magic number。
- 对象存储 key 不允许 path traversal。
- 下载 URL 必须有过期时间和权限校验。
- 合同已签/归档状态必须双写审计并可追溯 provider event。
- 历史 `file_path -> object_key` 迁移必须有备份和 downgrade。

## 5. 隐私与日志

- 不在日志中输出 access/refresh token、session key、支付私钥、电签 app secret。
- 生产日志中手机号、身份证号、统一社会信用代码、银行卡/订单敏感字段需要脱敏。
- `docs/release/evidence/` 中保存的沙箱日志、回调摘录和 JSON 证据必须先通过 `scripts/release-evidence-secret-scan.sh`，不得包含明文密钥、access/refresh token、手机号或身份证号。
- RAG/尽调缓存必须带 org namespace，不能跨组织复用。
- 本地/绝密模式下，云端模型、外部 MCP、同步上传、移动远控外传默认 fail-closed；只有用户显式授权后才允许出站。当前桌面 CLI/sync/Harness IPC、本地同步桥、统一 API fetch、WebView 全局 fetch 和 WebSocket 已有代码级 guard，Tauri/前端 HTTP 插件面、宽泛 shell/opener launch capability 和宽松 CSP 已由 `scripts/desktop-network-surface-gate.sh` 收紧；工作站 UI 在 TopSecret 下不启用同步/远控动作，只允许进入本地能力或治理视图，且远控 host 控制面在 TopSecret/非桌面预览下禁用配对确认、安全探针和取消命令；后端远控 API 已有 DB-backed pairing/route-token/safe-probe-only queue/host-claim/status/cancel/audit 控制面，本地/绝密模式、缺配对、缺 route token、缺二次确认或非 safe-probe 命令时不入队；桌面 IPC host 客户端在 TopSecret 下会先被 data-network guard 阻断，显式单次 host cycle、bounded poll 和 env-gated 后台 safe-probe daemon 只处理 safe probe，且 daemon 在 TopSecret 或缺登录/测试 bearer 时网络前阻断；signed/notarized packaged runtime 出站拦截、外部脚本运行时复验、signed runtime daemon 运行证据、高风险真实执行器和移动真机证据仍需补齐。
- 跨会话记忆和 agent workspace artifact 不得在 local/top-secret 模式持久化；必须带 org/user scope、明确 purpose/retention 和用户或组织 consent，payload 必须先递归脱敏。当前 `MemoryLayer.set_governed_session_artifact` 已补代码级门禁并由 `backend/tests/test_memory_governance.py` 覆盖，后续仍需接入完整 runtime/UI 和真实撤销失权证据。
- 移动远程控制桌面必须有设备配对、权限范围、命令过期、取消/撤销、敏感动作二次确认和审计日志；未授权设备不能读取本地文件、密钥或知识库内容。
- 外部抓取必须遵守 robots、UA、频控和法定数据源白名单。

## 6. 发布前必须完成

- `docs/archive/legacy-spine-sources/audit/00-platform/04-ci-security-scan.md` 中 CI/security scan 待确认项需要落地或形成豁免（历史扫描清单，仍生效）。
- 前端生产依赖 `cd frontend && npm audit --omit=dev --json` 已清零并保存到 `docs/release/evidence/artifacts/frontend-npm-audit-prod-20260507.json`；当前采用补丁级升级和定向 overrides，避免将 `picomatch` v2 链全局强升到 v4。
- 移动端 `cd mobile && npm audit --omit=dev` 已清零；当前通过 `@xmldom/xmldom@0.8.13`、`@babel/plugin-transform-modules-systemjs@7.29.4`、`fast-uri@3.1.2`、`@expo/cli -> tar@7.5.14`、`@expo/metro-config -> postcss@8.5.14`、`cacache -> tar@7.5.14` 定向 overrides 修复。`tar@7.5.14` 跨过 Expo CLI 声明的 semver 范围，后续 Expo SDK/package 改动必须保留 `npx expo-doctor`、`npx expo install --check` 和真机 smoke。
- 全仓 secret scan/gitleaks 至少跑一次，并保存结果。
- 发布证据目录脱敏扫描 `bash scripts/release-evidence-secret-scan.sh` 必须通过，并纳入 `scripts/commercial-readiness-gate.sh`。
- 全仓 `rg` 检查 mock/fallback/token 泄露关键字。
- 生产密钥轮换 SOP 演练一次，更新 `docs/archive/legacy-spine-sources/audit/00-platform/02-secret-rotation-sop.md`（演练新增内容需要回写到当前活跃 SOP）。
- 安全审计 owner 对 P0 未闭合项签字。
