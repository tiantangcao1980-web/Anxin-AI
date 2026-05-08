# 安全与隐私发布清单

> 日期：2026-05-08
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

- LLM 配置必须按组织隔离，superuser 例外必须有测试。
- 任意 LLM provider/endpoint/model/key、Skills 和 MCP Server 配置必须按组织/用户 scope 隔离，启用前有最小权限说明，调用后有审计日志。
- 当前 CLI Key 与 execute 已写入审计日志，CLI `/execute` 已在 staging/production 默认要求 DB-backed route token 并按 API Key `key_id` 绑定 consumer，后端 `/cli/route-token` 与桌面端 execute 前 route-token 获取/传递已补；MCP Server 管理 API 已收紧到 `manage:system`，管理动作写入脱敏审计，独立 MCP Server 在 staging/production 默认关闭；外部 MCP 连接已补 stdio 默认关闭、stdio command/command-line/env allowlist、SSE scheme/host allowlist 和子进程不继承全量环境变量的基线；MCP tool execution 已在 staging/production 默认要求 DB-backed route token，并支持 Agent context 传递到真实 `call_tool`；桌面 CLI/sync/Harness IPC、本地同步桥、统一 API fetch、WebView 全局 fetch 与 WebSocket 已补 TopSecret data-network guard；移动端请求层已透传 `X-Privacy-Mode` 且 local 模式在 fetch 前 fail-closed，移动端 `/desktop-control` local 模式不检查网络、hybrid/cloud 只读取 `/sync/remote-control/status` 安全闸；小程序请求层已透传 `X-Privacy-Mode`，local/top-secret 会在 `Taro.request` 前 fail-closed，登录入口会在 `Taro.login` 前阻断；Tauri 原生 HTTP 插件和前端 HTTP 插件包已移除，默认 capability 不再启用 `http:*`、`shell:allow-open` 或宽泛 `opener:*`，CSP 已收紧并由 `scripts/desktop-network-surface-gate.sh` 守住；设置页工作站入口已用 `desktopWorkstationModel` 锁住 TopSecret 下同步/远控 action disabled；后端 `/sync/remote-control/*` 已锁住未配置、绝密/本地模式、缺二次确认、缺配对、缺 route token 和缺队列/审计时 fail-closed；agent capability policy 已补未注册工具 fail-closed、订阅 feature、角色 permission、隐私模式、设备信任、通道策略和审批上下文判定，并在 agent MCP tool list、Harness 可用工具列表与 runtime tool call 前二次判权；短期 route-token broker 已补 hash-only storage、scope check、revocation next-call failure、expiration 和 audit event 代码级防线；Agent 控制面持久化模型与迁移已补，覆盖复合租户外键、TokenLease hash-only、raw token 不入库和审计 update/delete 防线；DB-backed AgentGovernanceService 已补跨实例验证、组织隔离、consumer/scope 拒绝、过期和 route 撤销后下一次调用失败；发布前仍需把 CapabilityRoute/TokenLease/AgentApproval/AgentAuditEvent 接入 LLM/browser/desktop-control 运行时、补工具调用细粒度审计、真实 approved MCP connector 演练、桌面 signed/notarized packaged runtime 出站拦截复验和移动/小程序真机出站证据。
- 审批流已补本地授权防线：普通成员不能批量审批他人/跨组织审批；审批列表按用户/组织 scope 过滤；`admin` 按 `org_admin` 语义只管本组织，只有 `super_admin` 可全局；模板写入仅限 `admin/org_admin/super_admin` 且模板读取/使用按创建者或全局管理员过滤；过期审批不能 approve/reject/batch 继续执行。商业发布前仍需补正式 Agent Approval 工作室、审批审计导出和组织级模板 schema。
- Skills 进化已补本地 Skill Evolution Gate：agent 只能创建 draft proposal；required eval checks 未齐或失败时拒绝审批；审批角色限制为 owner/boss/super_admin/org_admin/admin；灰度绑定具体版本；回滚后 `SkillService` governed 版本过滤立即回到上一版本；AgentApproval/AgentAuditEvent 模型已补；商业发布前仍需补 SkillGovernance 持久化、组织级能力中心 UI、记忆治理、真实执行链路 route/token 撤销联动和审计导出。
- 企业组织默认只开放 L0/L1 基础能力；完整能力必须同时满足订阅/购买状态、老板或 Owner/超级管理员授权、角色权限、风险级别、隐私模式、设备信任、通信策略和审批状态。
- Agent/Worker 不得持有真实 API key、PAT、财税接口密钥、浏览器账号密码或桌面本地密钥；必须通过 Gateway/密钥服务发放短期 consumer token 或 route token，撤销后下一次调用必须 401/403 并写审计；当前 `capability_route_service` 已提供本地最小 broker，CapabilityRoute/TokenLease/AgentApproval/AgentAuditEvent 持久化模型与迁移、DB-backed route-token 服务、MCP tool execution route-token 边界以及 CLI route-token 签发/execute 传递边界已补，商业发布前还需 LLM/browser/desktop-control 真实能力调用链集成和跨进程撤销失权证据。
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
- 本地/绝密模式下，云端模型、外部 MCP、同步上传、移动远控外传默认 fail-closed；只有用户显式授权后才允许出站。当前桌面 CLI/sync/Harness IPC、本地同步桥、统一 API fetch、WebView 全局 fetch 和 WebSocket 已有代码级 guard，Tauri/前端 HTTP 插件面、宽泛 shell/opener launch capability 和宽松 CSP 已由 `scripts/desktop-network-surface-gate.sh` 收紧；工作站 UI 在 TopSecret 下不启用同步/远控动作，只允许进入本地能力或治理视图；后端远控 API 在本地/绝密模式、缺配对、缺 route token、缺二次确认和缺命令队列/审计时不入队；signed/notarized packaged runtime 出站拦截、外部脚本运行时复验和移动真机证据仍需补齐。
- 移动远程控制桌面必须有设备配对、权限范围、命令过期、取消/撤销、敏感动作二次确认和审计日志；未授权设备不能读取本地文件、密钥或知识库内容。
- 外部抓取必须遵守 robots、UA、频控和法定数据源白名单。

## 6. 发布前必须完成

- `docs/audit/00-platform/04-ci-security-scan.md` 中 CI/security scan 待确认项需要落地或形成豁免。
- 前端生产依赖 `cd frontend && npm audit --omit=dev --json` 已清零并保存到 `docs/release/evidence/artifacts/frontend-npm-audit-prod-20260507.json`；当前采用补丁级升级和定向 overrides，避免将 `picomatch` v2 链全局强升到 v4。
- 移动端 `cd mobile && npm audit --omit=dev` 已清零；当前通过 `@xmldom/xmldom@0.8.13`、`@expo/cli -> tar@7.5.14`、`@expo/metro-config -> postcss@8.5.14`、`cacache -> tar@7.5.14` 定向 overrides 修复。`tar@7.5.14` 跨过 Expo CLI 声明的 semver 范围，后续 Expo SDK/package 改动必须保留 `npx expo-doctor`、`npx expo install --check` 和真机 smoke。
- 全仓 secret scan/gitleaks 至少跑一次，并保存结果。
- 发布证据目录脱敏扫描 `bash scripts/release-evidence-secret-scan.sh` 必须通过，并纳入 `scripts/commercial-readiness-gate.sh`。
- 全仓 `rg` 检查 mock/fallback/token 泄露关键字。
- 生产密钥轮换 SOP 演练一次，更新 `docs/audit/00-platform/02-secret-rotation-sop.md`。
- 安全审计 owner 对 P0 未闭合项签字。
