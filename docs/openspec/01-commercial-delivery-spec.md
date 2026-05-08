# OpenSpec — 商业交付总规范

> 日期：2026-05-08
> 范围：将安心 AI 法务从当前 V2 架构骨架推进到可商业交付候选版。
> 前置：`docs/audit/00-platform/06-gitnexus-knowledge-graph.md` 已确认索引可用边界。

## 0. 产品定位与全设备智能助手规范

商业交付候选版必须同时满足两个定位：一是面向中小企业经营风险的法务、财务、税务、合规和舆情平台；二是桌面优先、移动协同、可扩展模型/Skills/MCP/知识库的全设备智能助手。

| 角色/端侧 | 目标用户 | 必须可交付的价值 |
|---|---|---|
| 企业需求方 | 中小企业老板、股东、高管、行政、人事、财务、法务/合规兼岗人员 | 用 AI 低成本处理日常合同、劳动人事、回款、税务、工商、尽调、舆情和内部办公问题；重大事项可转可信专业人士 |
| 专业服务方 | 律师、律所、税务师、税务师事务所、财务顾问、会计/审计人员及机构 | 通过资质认证、服务目录、利益冲突检查、SLA、评价、线索归因和结算获得可信客户 |
| 桌面客户端 | 企业用户、专业服务人员、平台运营人员 | 成为主要工作站：安装包、本地加密库、本地模型、独立知识库、文件拖拽分析、任务队列、Skills/MCP 配置和审计日志 |
| 移动端/小程序 | 企业用户和服务方外勤/随身场景 | 成为随身助手：咨询、审批、通知、材料查看、跨设备会话继续，并可安全远程控制已配对桌面客户端 |
| 平台运营端 | 审核、风控、客服、商业运营 | 供需匹配质量、资质审核、投诉处理、舆情处置、推广获客、数据脱敏和发布证据可追踪 |

平台能力合同：

- **AI 处理日常，专业人员处理重大事项**：高金额合同、劳动争议、税务稽查、行政处罚、诉讼仲裁、重大舆情、股权融资、并购重组等场景必须给出专业协助入口和授权材料包。
- **专业协助通道不只覆盖律师**：当前 P0 可先把律师/律所做实，但模型、接口和文档必须预留 legal / tax / accounting / finance / compliance 服务类型。
- **桌面主工作站是未来重点**：桌面端必须可安装、可本地运行、可本地加密、可接本地模型和本地知识库；不能只作为 WebView 外壳。
- **移动端是助手和远控端**：移动端除具备核心工作能力外，必须支持设备配对、远程命令、状态回传、取消/撤销、敏感动作二次确认和审计。
- **用户可配置任意模型、Skills、MCP**：系统必须支持组织/个人维度的 provider、endpoint、model、key、skill、MCP Server 和权限策略配置。
- **独立知识库与本地模型保障数据安全**：个人/组织/项目/客户知识库必须有来源、引用、权限、版本和本地缓存；绝密/本地模式默认禁止云端调用、外部 MCP 调用和数据外传。
- **企业智能体必须管得住**：组织用户默认只开放基础能力；完整能力必须受订阅、老板/Owner、超级管理员、角色、风险级别、隐私模式、设备信任、通信策略和审批状态共同约束。
- **Agent/Worker 不持有真实密钥**：借鉴 HiClaw 的 Manager/Leader/Worker/Human、Human-in-the-loop、声明式通信策略和 AI Gateway credential isolation，LLM/MCP/Skills/浏览器/CLI/桌面远控都必须经统一 CapabilityRoute 和短期 consumer token。
- **交互体验必须像可信 AI 工作台**：借鉴 Codex/Claude 的公开产品体验原则，长任务要过程可见、证据可点、artifact 可编辑、可打断可恢复、能力可发现。
- **Skills 和智能体允许进化但必须受控**：Skill 创建、升级、自我改进提案、评测、审批、灰度、回滚和记忆治理必须进入能力中心和审计，不允许 agent 无审批自改生产能力。
- **舆情监测与推广获客是商业价值入口**：舆情监测要连接风险预警、处置建议和人工服务转介；推广获客必须标识清楚、授权清楚、来源可追踪、反骚扰。

## 1. 商业交付定义

本项目达到商业交付候选版，必须同时满足：

- 中小企业需求方、专业服务方、桌面端、移动/小程序端的核心路径不再依赖 mock 或仅 UI 骨架。
- 桌面主工作站、移动随身助手/远程控制、LLM/Skills/MCP/知识库可配置路径有验收证据。
- 可信会话体验有验收证据：长任务时间线、工具状态、引用证据、artifact 编辑、暂停/恢复/取消/接管、跨设备继续和能力中心。
- 企业智能体治理有验收证据：普通员工边界、老板/Owner 和超级管理员完整控制、外部服务方材料包边界、高风险审批、route token 撤销、工作室旁听/接管/终止。
- 三态运行模式（本地/混合/云端）具备后端守卫、前端门控、订阅策略和失败语义一致性。
- 认证、授权、token、Webhook、对象存储、同步、支付/电签等高风险面有测试证据。
- 对外文档、部署手册、回滚预案、灰度方案齐全。
- 全量测试与关键 E2E 可重复运行，失败项被明确列为阻断或非阻断。

## 2. 当前事实基线

已确认可用：

- 后端默认全量 pytest 当前达到 `736 passed, 1 skipped, 12 warnings in 44.61s`；`test_comprehensive_flow` 作为显式 opt-in smoke，需 `RUN_COMPREHENSIVE_FLOW=1` 才运行。
- 前端 `lint`、`npm test` 与 `build` 可通过，最新完整本地门禁中 Vitest 为 `12 files / 45 tests passed`，`npm run build` 当前通过。
- 角色访问 E2E 当前达到 `10 passed, 10 skipped`。
- 移动/小程序本地门禁：`bash scripts/mobile-device-smoke.sh` 通过，移动 Vitest `8 files / 27 tests passed`，移动 tsc、Expo doctor `17/17`、mobile production npm audit、小程序 tsc/build、WeChat DevTools CLI project smoke、mobile result surface guard、refresh auth guard、mobile/mini privacy network guard、fake fallback guard、mini-program navigation boundary guard 和 mini-program design token guard 均为 exit `0`。
- 桌面端 `cargo check` 可通过。
- GitNexus 索引复验：当前精确统计以 `.gitnexus/meta.json` 为准；最终商业 release 前必须重新证明 `capabilities.vectorSearch.status=vector-index`、embedding meta count 与 `gitnexus cypher` count 非零且一致，并让 direct binary 的 `status/cypher/detect-changes` 与当前 commit 一致；当前 direct CLI repo 解析未通过，semantic query 不作为唯一放行依据。
- 本地/混合/云端与可配置模型已有架构基础：`docs/ARCHITECTURE_V2.md` 已定义本地模式数据不离开设备、Ollama/LM Studio 等自配置本地模型，以及 Enterprise 自定义 LLM endpoint；后端存在 `src/services/llm_service.py`、`src/services/private_llm_service.py`、`src/api/routes/llm.py`，桌面存在 `desktop/src/commands/local_llm.rs`。
- MCP/Skills 已有代码基础：后端存在 `backend/src/mcp_server.py`、`backend/src/api/routes/mcp_routes.py`、`backend/src/services/mcp_client_service.py`、`backend/src/models/mcp_config.py`、`backend/src/services/skill_service.py`；这些证明扩展底座存在，但尚不能证明“任意 Skills/MCP 商业可配置”已经闭环。
- 独立知识库已有代码基础：后端存在 `backend/src/services/knowledge_management.py`、`backend/src/services/knowledge_service.py`、`backend/src/api/routes/knowledge.py`；仍需把本地知识库、组织知识库、来源引用、离线索引和移动/桌面可视化配置纳入发布验收。
- 桌面/移动本地安全已有局部基础：桌面 SQLCipher/keyring、offline queue 和 local LLM 命令已有代码级证据；移动 `privacy-context` 已覆盖 LAN Ollama 等本地模型语义；后端同步路由已补移动远控 DB-backed 配对、授权、命令队列、host 领取、状态回传、取消和递归脱敏审计控制面；桌面 Tauri IPC 已补确认配对、领取命令和回传状态的 host 客户端。仍缺完整的桌面主工作站配置面、真实后台自动轮询/执行器、真实跨设备联调和真机/packaged runtime 证据。
- 商业发布门禁脚本 `scripts/commercial-readiness-gate.sh` 已建立；当前预期为 FAIL，用于防止在外部证据未齐时误判 Go。
- 支付/电签沙箱证据采集入口 `scripts/sandbox-evidence-runner.py` 已建立；默认只做脱敏配置预检，live 调用必须显式传 `--live --confirm-live-side-effects`。
- 第一波 V2 守卫已完成：`/pro` provider 守卫、ModeGate/PrivacyContext fail-closed、LLM 组织隔离、尽调模式/订阅守卫、匿名聊天 token 拆分、A2UI/WS 鉴权。
- TASK-09 P0-7 已收口：尽调搜索缓存新增 `org_id` scope，缓存读写、维度状态、失效、编排器和 deep research 路径均按组织过滤；无组织普通用户态请求 fail-closed；跨组织同公司缓存隔离回归已落地。
- TASK-09 P0-4 已收口：风险评分保持数据驱动且确定性，新增顶层 `score/factors/explain` 解释契约，前端风险预警面板可渲染因子贡献条。
- TASK-09 P0-3/P0-6 已代码级收口：`crawler_service.fetch()` 统一白名单、robots、合法 UA 与 host 频控，频控默认 1 req/s/host 且强制下限 0.5 req/s/host；预发网络真实 dry-run 仍是发布证据。
- TASK-09 P0-5 已代码级收口：调查入口新增 "尽调 / 舆情 / 法规监测 / 普通搜索" 四类强路由，并接入 `ChatService._decide_route()`；200 条 JSONL 离线评测当前意图准确率 `1.000`、企业名抽取准确率 `1.000`。
- TASK-08a 已代码级收口核心风险：案件状态机阻断非法跳转，`closed/cancelled` 终态只读，状态变更写事件；任务列表/更新/删除/流转按 `created_by/assignee/admin` 服务层收口。
- TASK-08b 已代码级收口核心风险：律师撮合/案源市场在 local 模式固定拒绝，投标入口强制利益冲突检查并在命中时 409 阻断，同分律师匹配用曝光轮询避免先到先得。
- TASK-01 已部分收口：reset-password/resend-verification CAPTCHA 覆盖、reset token IP/UA 上下文绑定、高熵 token 前端输入适配、reset token DB 持久化且仅存 hash、认证限流 Redis fail-closed、refresh token blacklist fail-closed 回归、Web 端 access token 内存化、refresh token 不再进入 localStorage、旧 localStorage token 启动迁移清理。
- 前端 API 请求已统一透传 `X-Privacy-Mode`：`frontend/src/lib/api.ts` 新增 mode 快照与 `buildApiHeaders`，PrivacyContext、api-adapter、流式/上传/后台/支付/电签/模板/画布直连 fetch 已接入；移动端请求层也会透传 `X-Privacy-Mode`，且 `local` 模式在 fetch 前 fail-closed；小程序请求层透传同名 header，`local` / `top-secret` 会在 `Taro.request` 前 fail-closed，登录入口会在 `Taro.login` 前阻断。
- TASK-10 S8 已收口：IM WebSocket URL 不再携带 access token，改为连接后首包 `auth` 鉴权。
- TASK-10 P0-6 已收口：订阅新增显式状态机与 `subscription_events` 审计表，覆盖待支付、试用转付费、续费、退款过期和非法终态 409。
- TASK-10 P0-7 已收口：`create_subscription` 服务层原生写入 `client_type` 与套餐适用端校验，需求方/服务方订阅的支付、退款、事件日志互不串线；`MySubscription` 前端已按需求方/服务方双栏展示，不再只消费第一条订阅；`Pricing` 已按所选端侧过滤 `client_type` / `both` 套餐，避免用户选到后端会拒绝的跨端套餐。
- TASK-10 P0-8 已收口：IM 消息增加 conversation 内递增 `sequence`，WebSocket 首包可携 `last_ack_message_id` 拉离线增量；前端 `useIMWebSocket` 会在认证首包携带用户维度 ACK 游标，收到实时/离线消息后自动发送 `ack`，并在服务端 `ack_ok` 后持久化游标。
- TASK-11c P0-2/P0-3/P0-4 已部分收口：移动端 `approvals/[id].tsx` 不再用静默 fallback 假审批，`cases.tsx` 已复核为错误三态，首页任务/审批/通知不再用假数据兜底，聊天欢迎语移出消息历史，设置页移除误导性 mock 标记，`messages/[id].tsx` 和 `tasks/[id].tsx` 已移除 fallback 对话/任务并显示真实 loading/empty/error 状态；移动端尽调和知识库搜索已从 Alert-only 反馈改为页面内结果摘要卡；小程序 `Profile` 登录失败不再写入 `mock_token` 或提示体验模式，且本地/绝密模式会在 `Taro.login` 前阻断；后端新增 `/api/v1/auth/wechat/code2session`，按微信小程序 `wx.login` code 换取 openid 后签发本地 JWT，且不向客户端下发 `session_key`。小程序首页资讯接口失败/为空时不再渲染假新闻 fallback，隐私阻断时显示明确空状态；首页与个人中心主入口已去掉空路径/“功能开发中”死胡同，改由 AI 助手承接合同审查、找律师、合规自检和案件协助。`scripts/mobile-device-smoke.sh` 已建立本地门禁，覆盖移动测试、移动 tsc、mobile result surface guard、小程序 tsc/build、mini privacy boundary guard、mini navigation boundary guard、fake fallback guard 和 mini-program design token guard。

仍为商业交付阻断：

- 后端 refresh request-body 兼容窗口已 sunset：默认只接受 HttpOnly Cookie，`AUTH_REFRESH_BODY_COMPAT_ENABLED=true` 才临时接受 body token。
- 文档/合同对象存储底座已接入：`object_storage_service.py` 提供 `local`/`minio` 适配，`DocumentService` 上传/删除/版本更新、合同保存与 `ContractAttachment` 上传/下载 URL/删除均已写真实对象；历史 `file_path` backfill 已由迁移 029 覆盖；剩余为生产 MinIO 凭据轮换与跨环境 URL 策略验证。
- S9 上传入口校验已收口：`read_validated_upload_file` 统一调用 `FileValidator.validate_file`，`documents.py`、`knowledge.py`、`contracts.py` 的 UploadFile 入口均覆盖扩展名、MIME、大小与 magic number 校验；非法上传以 4xx 拒绝。
- TASK-06 P0-4 模板渲染边界已收口：合同模板仍保持无 eval/Jinja 的自研正则插值，`TemplateRenderRequest` + `TemplateEngine.validate_variables` 校验变量白名单、类型、长度和总大小；变量值统一 HTML/Markdown 转义，非法 select、嵌套 party、`__class__` 类变量名和超长文本均以 422 拒绝，渲染产物超限以 413 拒绝。
- TASK-06 P0-5 协作离线合并已收口：`DocumentOperation` 支持 `base_version/baseVersion`，离线客户端基于旧版本提交的 insert/delete/replace 会按服务器历史操作转换位置；旧实时客户端不传版本时保持当前 position 语义，operation 广播 payload 的 timestamp 已转 ISO 字符串。
- TASK-06 P0-6 大文档导出保护已收口：`ContractExportService` 对导出源内容与生成文件均执行大小限制，默认 50MB，`CONTRACT_EXPORT_MAX_BYTES` 可调但最高 200MB；合同下载超限返回 413，正常输出通过 64KB chunk 迭代给 `StreamingResponse`。
- TASK-06 P0-7 历史文档对象存储迁移已收口：`029_document_object_storage` 升级时会把旧 `documents.file_path` / `document_versions.file_path` 回填到 `object_key`，并默认 `storage_backend='local'`；本地 SQLite 已验证升级和 downgrade 去列。
- TASK-05 P0-1 合同生命周期状态机已收口：`LEGAL_TRANSITIONS` 覆盖全部 `ContractStatus`，合同审查、手动 API 转换与 e签 webhook 写回均走 `ContractLifecycleStateMachine.transition`；非法转换保持原状态并通过 API 409 暴露。
- TASK-05 P0-4 合同版本 diff/回滚已收口：`ContractVersion` 记录审查应用与回滚版本，后端提供版本列表、段落 diff、rollback API，前端合同审查面板提供版本时间线、比较、diff 和回滚；rollback 创建新草稿版本并经状态机拒绝法律终态回退。
- TASK-05 P0-5 审查并发/超时与 webhook 并发幂等已收口：合同审查按合同/版本加短租约锁，默认 90s 超时后落 `review_failed` 并允许重试；已验证 webhook 处理在持久幂等表外加 processing lock，重复并发事件只执行一次业务写回。
- TASK-05 P0-6 合同附件对象存储已收口：`ContractAttachment` 记录附件元数据，上传走统一文件校验和对象存储 put，列表/下载/下载 URL/删除均按组织隔离，上传/下载/删除双写审计；前端合同审查页已提供附件上传、下载和删除控件。
- TASK-05 P0-2/P0-3 电签官方协议代码级已收口：e签宝 provider 已实现官方签名头、创建/启动流程、签署链接、状态查询、下载、撤销；法大大 provider 已实现 FASC V5.1 access token、签署任务、actor 链接、状态详情、下载 URL、取消；e签宝 `X-Tsign-Open-*` 回调与法大大 `X-FASC-*`/`bizContent` webhook 均进入统一幂等回写并写审计。仍阻断：真实商户沙箱 7 天、账号事件订阅清单、签署文件下载/撤销真实证据、灰度放量记录。
- 支付 webhook 与电签 webhook 的通用 HMAC 路径已可分别回写订单/订阅、合同签署状态；`webhook_received` 持久化幂等表、重复通知跳过、Admin `/admin/webhooks` 查询/筛选/手动重试入口、Prometheus webhook 指标、电签 `flow_id → Contract` 持久映射、失败 webhook backoff 调度与可配置后台 worker、统一 `webhook_handler.py` 和稳定 `PaymentWebhookEvent` / `ESignWebhookEvent` 已落地，微信/支付宝/电签官方通知 id 已可作为幂等键。微信支付 v3 Native 下单/查单/关单/退款请求与同步响应 RSA-SHA256 验签、微信支付 v3 回调 RSA-SHA256 验签/资源解密、支付宝 `alipay.trade.page.pay/query/refund/close` 签名请求与同步响应/异步通知 RSA2 验签、e签宝与法大大官方电签协议代码级适配、退款 `idempotency_key` 唯一约束/同 key 100 并发回归、订阅 `pending/trial/active/past_due/cancelled/expired` 状态机与 `subscription_events` 审计、双客户端订阅隔离、IM 离线增量与 ACK 前后端协议已具备可测试实现。仍阻断：真实渠道沙箱闭环、微信平台证书/公钥轮换验证、电签账号事件映射和灰度证据。
- 同步后端日志已从进程内存升级为 `SyncLog` 持久化 append-only 增量日志，并覆盖用户隔离、冲突报告和 artifact session 隔离；桌面端已改为 Rust SQLCipher/keyring 本地库路径，前端通过 Tauri secure SQL commands 读取本地 `sync_log`、push/pull 并写回 SQLCipher，迁移 SQL 可在 fresh/legacy 临时 SQLite DB 中执行通过，SQLCipher plaintext migration 单测通过，local installed-profile keyring/reopen smoke 通过，SQLite 100/500 本地同步性能基线已通过，`SyncStatus` 已有 keep-local/keep-remote 最小冲突对话框，`/sync-conflicts` 已有 merge 编辑页，失败记录已有代码级指数退避和 `needs_human` 标记，Rust init schema 与前端同步 schema 已对齐，Tauri debug no-bundle、binary self-test、unsigned release `.app`/DMG、unsigned release packaged runtime self-test/startup/WebView page-load smoke 和 unsigned release packaged-profile SQLCipher/keyring migration/performance smoke 可通过，`scripts/desktop-sqlite-security-gate.sh` 已通过桌面加密/keyring 代码级门禁。仍阻断：signed/notarized installer、signed packaged-profile migration 实装证据、signed packaged runtime 性能和跨端连续会话。
- API shape 不能依赖 GitNexus `shape_check` 自动证明，必须用测试覆盖。

## 3. 分阶段目标

### Phase 0 — 可信索引与规范冻结

目标：
- GitNexus 索引可查询且边界清晰。
- 本 OpenSpec 与测试规范冻结。
- 任何后续开发必须引用对应任务与验收项。

完成条件：
- `docs/audit/00-platform/06-gitnexus-knowledge-graph.md` 存在。
- `docs/openspec/01-commercial-delivery-spec.md` 与 `docs/openspec/02-commercial-delivery-test-spec.md` 存在。
- 当前工作区改动通过 `git status` 归类：索引配置、规范文档、业务代码改动分别说明。

### Phase 1 — P0 安全与商业模式守卫

范围：
- `docs/audit/_tasks/TASK-01-auth.md`
- `docs/audit/_tasks/TASK-02-mode-llm.md`

必须完成：
- 高熵单次密码重置 token。
- token 存储迁移，不再把生产 access/refresh token 长期放 localStorage。（Web 源码已完成；后端 refresh body 兼容默认关闭；移动端/桌面端策略仍需收尾审计）
- Redis 敏感认证入口 fail-closed。（认证限流 + refresh blacklist 已完成本轮；剩余 session/CAPTCHA Redis 状态待审）
- CAPTCHA reset-password/resend-verification 覆盖。（已完成本轮）
- `/pro` 路由真实 provider 守卫。（已完成本轮）
- ModeGate/PrivacyContext fail-closed。（已完成本轮）
- LLM 配置组织隔离。（已完成本轮）
- 后端 `require_mode` / subscription guard。（已完成本轮）

### Phase 2 — 核心业务闭环

范围：
- `TASK-03-agents`
- `TASK-04-a2ui`
- `TASK-05-contract`
- `TASK-06-document`
- `TASK-07-rag`

必须完成：
- 对话/A2UI/action 不越权。
- 文档对象存储抽象层落地。
- 合同附件、文档版本、代码级电签 provider/webhook 状态可追溯；真实电签沙箱证据与 RAG 引用链路继续作为 Phase 2 剩余门槛。
- 模板与文书生成达到可交付草案质量门槛。

### Phase 3 — 商业化与多角色协同

范围：
- `TASK-08a-case-task`
- `TASK-08b-lawyer-market`
- `TASK-09-risk-investigation`
- `TASK-10-billing-im`

必须完成：
- 案件/任务状态机清晰。
- 专业服务市场利益冲突与权限模型真实有效；P0 先覆盖律师/律所，P1/P2 预留税务师、税务事务所、财务顾问、会计/审计人员。
- 尽调/舆情/匿名咨询边界收口；舆情监测必须连接风险告警、处置建议、材料包和专业服务转介。
- 推广获客功能必须有授权、广告/推荐标识、线索来源、反骚扰和服务方结算证据。
- 订阅、支付、退款、IM/RTC 通知形成状态机与幂等闭环，并区分企业侧 AI 套餐、专业服务按次/项目计费和服务方获客产品。

### Phase 4 — 多端交付

范围：
- `TASK-11a-desktop-mvp`
- `TASK-11b-sync-engine`
- `TASK-11c-mobile-design`

必须完成：
- 桌面端是可安装主工作站：快速问答、拖拽分析、本地加密库、本地模型、独立知识库、Skills/MCP 配置入口和本地/混合/云端模式状态一致。
- 同步引擎 push/pull/conflict 真实可用，并支持跨设备会话、移动远控命令、审批确认和执行状态回传。
- 移动端/小程序关键场景不依赖 mock token；移动端必须具备随身助手能力和安全远程控制桌面客户端能力。
- 远程控制必须通过设备配对、权限确认、敏感动作二次确认、取消/撤销、审计日志和端到端加密/通道安全验收。

### Phase 5 — 企业智能体治理

范围：
- `TASK-12-agent-control-plane-skill-evolution.md`

必须完成：
- 统一 `capability_policy_engine`，覆盖 `subscription + role + permission + risk_level + privacy_mode + device_trust + channel_policy + approval_state`。
- 建立 AgentManager、AgentTeam、AgentWorker、HumanParticipant、ChannelPolicy、CapabilityRoute、Approval、AuditEvent 数据模型和迁移。
- Agent/Worker 不持有真实密钥；真实密钥只在 Gateway/密钥服务侧，Agent 只拿可撤销短期 route token。
- 高风险任务进入 Human-in-the-loop 工作室，可旁听、暂停、接管、终止并导出证据。
- 能力中心按老板/Owner、超级管理员、部门管理员、普通员工、外部专业服务方展示不同能力、限制和申请入口。
- Skill Evolution Gate 覆盖 Skill 版本、owner、评测、审批、灰度、回滚和自我改进提案；agent 只能提案、生成测试和提交审批，不能自行启用生产能力。

当前进展：
- 已补第一层 agent capability policy：未注册工具 fail-closed、显式 allowlist、订阅 feature、角色 permission、绝密模式、设备信任、通道策略、高风险审批上下文，以及 MCP tool list 过滤 + runtime 二次判权。
- MCP 外部连接已补商业环境 fail-closed allowlist 基线：stdio 默认关闭、command/command-line/env allowlist、SSE scheme/host allowlist 和子进程最小环境；短期 route-token broker 已补 hash-only storage、scope check、过期、撤销后下一次验证失败和审计；持久化 Agent/Team/Worker/Human/ChannelPolicy/CapabilityRoute/TokenLease/Approval/AuditEvent 模型与迁移已补，且有复合租户外键、raw token 不入库和审计 update/delete 防线；DB-backed AgentGovernanceService 已补 hash-only token lease、跨 service 实例验证、组织隔离、consumer 绑定和 route 撤销后下一次调用失败；AgentApprovalService 与 `/api/v1/agent-approvals` 已补高风险审批创建、组织/本人 scope、授权角色审批/驳回、撤销、执行前 validate、过期/撤销 fail-closed、action/route 匹配、payload 脱敏和审计测试；DB-backed SkillGovernance 与 `/skill-governance` API 已补 proposal/eval/approval/gray/rollback/enabled-version/audit 持久化、组织隔离、审计导出和 append-only 审计；前端最小 `Agent 治理工作台` 已接入审批、能力策略可用/阻断工具展示、Skill 提案/评测/批准/灰度/审计导出、桌面侧边栏和移动协作导航，并有 Playwright 桌面/移动回归；MCP tool execution 与 CLI `/execute` 已在商业环境接入 DB-backed route token，MCP 支持 Agent context 传递，CLI 按 API Key `key_id` 绑定 consumer 并校验 `cli:read/chat/export` scope，桌面端 CLI execute 会先申请短期 token并传递 `X-Capability-Route-Token`；移动远控控制面已补 pairing-specific `desktop:control` route token、命令队列、host 领取、running/completed/failed 状态回传、取消和递归脱敏审计，桌面端已有受 TopSecret guard 保护的 confirm/claim/status IPC 客户端；仍缺完整 Agent 控制面 UI、完整 Human-in-the-loop 旁听/暂停/接管/终止/artifact 工作室、真实 approved MCP connector 演练、LLM/browser/desktop-control route-token 运行时联动、真实桌面后台自动轮询/执行器、跨进程撤销后立即失权和商业发布证据。

## 4. 统一开发规则

- 每个任务先产出 `00-prd-reality-gap.md`，再改代码。
- 每个 P0 必须有失败测试先行或等价的回归证明。
- 改 schema 必须有 alembic migration 和 downgrade。
- 改支付、电签、密钥、prompt、桌面签名、公证、自动更新前必须单独审查。
- 改模型 provider、Skills/MCP 权限、知识库出站策略或移动远程控制桌面协议前必须单独做安全审查和隐私模式回归。
- 改 Agent control plane、CapabilityRoute、route token、审批流或工作室可见性前必须单独做安全审查、权限矩阵回归和审计日志回归。
- 改 Skill 生命周期、进化策略、记忆治理、自动改写 prompt 或自我改进流程前必须单独做评测门禁、权限回归和人工审批。
- 不新增依赖，除非任务文档明确要求且先记录理由。
- GitNexus 用作导航，不作为唯一事实；前端 JSX 与 Python warning 文件必须用 `rg` 补查。

## 5. 交付物清单

每个任务必须交付：

- 代码改动。
- 单元/集成/E2E 测试。
- `docs/audit/<NN-module>/00..05.md`。
- 变更说明、灰度方案、回滚方案。
- 验证命令与结果。

最终商业交付候选版必须额外交付：

- `docs/audit/SUMMARY.md`
- `docs/release/completion-audit.md`
- `docs/release/commercial-delivery-readiness.md`
- `docs/release/rollback-runbook.md`
- `docs/release/security-and-privacy-checklist.md`
- `docs/release/test-evidence.md`
- `scripts/gitnexus-index.sh`
- `scripts/commercial-readiness-gate.sh`
- `scripts/static-quality-baseline.sh`
