# 2026-04-03 安全审计记录

## 状态

- 状态：进行中（已进入收口阶段）
- 目标：对认证、授权、上传、WebSocket、回调、配置与多租户隔离进行全面扫描
- 范围：`backend/src`、`frontend/src`、配置文件、项目状态文档

## 当前遗留问题（截至 Batch 9）

### P0 / 高优先级遗留

- `S-001` 仓库历史中的真实密钥泄露风险仍需真实轮换与 Git 历史治理。
- `S-003` 密码重置链路仍使用 6 位数字码，缺少高熵单次 token、邮箱/用途绑定与尝试次数收敛。
- `S-004` Redis 异常时已从直接放行改为本地回退，但认证和风控链路仍未做到严格 fail-closed。
- `S-006` 支付与电签 webhook 目前是通用时间戳 HMAC 骨架，尚未切换到各渠道官方验签协议。
- `S-007` 前端仍将 access token / refresh token 写入 `localStorage`，XSS 下仍存在会话接管风险。
- `S-011` LIC 已加内网拦截和域白名单，但重定向策略、白名单粒度和最终落点约束仍可继续加强。
- `S-012` `sync` 已有最小安全实现，但仍缺持久化、签名、冲突策略和正式数据模型。
- `S-104` LLM 配置接口的组织隔离问题仍未进入本轮修复，普通已登录用户的可见范围需要继续收口。

### P1 / 持续优化遗留

- `S-002` 登录 / 注册 / 忘记密码已接入 Turnstile，但重发验证码、重置密码等敏感入口尚未统一接入挑战。
- `S-010` 协作会话详情、成员、快照、提交已收口，列表接口是否需要继续细化可见性仍待评估。
- `S-108` 数据中心当前按 owner 收口，但数据模型仍缺 org 维度。
- `S-034` 尽调趋势/快照已按用户快照过滤，缓存状态仅对普通用户收紧，整体边界仍可继续细化。
- `S-201` 匿名聊天仍是公开创建且单次返回双方 token 的设计。
- `S-202` IM 仍有 URL token 使用场景，尚未统一切到首包认证或短期 ticket。
- `S-203` 文档/知识库/合同等上传入口的校验策略仍未完全统一。
- `S-204` 部分状态文档仍需随实现持续同步，避免后续再次出现“文档领先或滞后于代码”。

## 已完成修复（截至当前）

### Batch 1：协作通道 + 文档/知识库/案件归属

- 已修复：
  - 协作主 WebSocket 改为首包 `auth` 消息携带 token 鉴权，不再信任 query 参数身份
  - 协作 HTTP 备用接口增加登录与协作成员校验
  - 协作会话详情、成员列表、快照、提交接口增加成员访问限制
  - 文档详情、更新、删除、版本历史按 `org_id` 做归属限制
  - 知识库详情、文档列表、搜索、语义搜索、导出、更新、删除等接口开始传递 `user_id/org_id` 到服务层
  - 案件关联文档时增加文档所属组织校验
- 对应问题：
  - 7 / 8 / 9 / 10 / 10.1 / 12.1

### Batch 2：后端权限边界收口

- 已修复：
  - AI 旁听 `status/insights/summary/link-case` 增加发起人校验
  - 获客分析接口收口到当前组织，非平台管理员不可跨组织查询
  - 订阅创建与订阅报表限制客户端自带 `org_id`
  - 数据中心列表按 owner 收口，存储接口限制可设置的 `access_level`
  - 审批列表与详情增加当前用户/当前组织范围过滤
  - 功能开关后台列表对 `ORG_ADMIN` 增加组织过滤
  - 舆情模块监控/记录/预警详情与操作接口增加组织归属校验
- 对应问题：
  - 16 / 20 / 23 / 24 / 25 / 26 / 27 / 28 / 29 / 30 / 32

### Batch 3：认证辅助链路 + 外联面收口

- 已修复：
  - `forgot-password` 增加频率限制
  - 微信/支付宝 OAuth 回调增加 `state` 校验，非法/过期 state 返回 400
  - Token 黑名单 Redis 异常时降级为本地黑名单，而不是直接放行
  - 频率限制 Redis 异常时降级为本地内存限流，而不是直接放行
  - LIC 抓取接口增加 URL 校验，禁止 localhost、私网、保留地址
  - `sync` 整组占位接口增加登录要求，并统一返回 503，避免在未完成前暴露数据面
- 对应问题：
  - 2 / 3 / 4 / 5 / 13.1 / 22

### Batch 4：实时协作与通讯边界收口

- 已修复：
  - RTC 房间创建要求当前用户必须属于对应 IM 会话
  - RTC 获取 room token / 结束房间时增加参与者校验
  - RTC 房间列表对普通用户仅返回其可访问的房间，平台管理员保留全量可见
  - IM 用户搜索默认只返回同组织活跃用户，平台管理员保留全局可见
- 对应问题：
  - 17 / 18

### Batch 5：外部回调与任务访问边界

- 已修复：
  - 微信支付 webhook 增加 HMAC-SHA256 基础签名校验
  - 支付宝 webhook 增加 HMAC-SHA256 基础签名校验
  - 电签 webhook 增加 HMAC-SHA256 基础签名校验
  - 未配置 secret 时，仅非生产环境允许放行，生产环境默认拒绝
  - OA 审批发起接口忽略客户端传入的 `initiator_id`，改为绑定当前登录用户
  - LIC 抓取任务增加 `owner_id`，状态查询按任务所有者限制
  - LIC WebSocket 进度流增加 token 鉴权和任务所有者校验
- 对应问题：
  - 6 / 20 / 13 / 13.1

### Batch 6：认证链路人机校验接入

- 已修复：
  - 后端新增 CAPTCHA 校验服务，支持 Cloudflare Turnstile
  - `/auth/features` 公开返回 `captcha_enabled / captcha_provider / captcha_site_key`
  - 登录、注册、忘记密码在 CAPTCHA 开启时要求提交 `captcha_token`
  - 登录页在后端开启 CAPTCHA 时动态加载 Turnstile 并在登录/注册/忘记密码表单显示验证组件
- 对应问题：
  - 2

### Batch 7：Webhook 防重放与 LIC 白名单

- 已修复：
  - Webhook 基础签名校验升级为 `X-Webhook-Timestamp + HMAC(timestamp.body)` 模式
  - 支付与电签增加简单防重放缓存，同一签名重复投递会被拒绝
  - LIC 抓取新增显式域白名单 `LIC_ALLOWED_HOSTS`
  - 配置白名单时，仅允许命中白名单的域名或子域被抓取
- 对应问题：
  - 6 / 13.1

### Batch 8：剩余业务越权面收口

- 已修复：
  - 审批通过/驳回操作要求当前用户必须是该审批的有效审批人
  - 尽调单条调查详情与调查报告仅允许记录所有者访问
  - 尽调风险趋势与快照对比按用户快照归属过滤
  - 尽调缓存状态/缓存失效对普通用户默认关闭，仅管理员可查看全局缓存
  - 律师评价增加同一咨询/委托记录的重复评价拦截
  - `sync` 从统一 `503` 封口升级为按用户和设备隔离的最小安全实现
- 对应问题：
  - 12 / 28 / 31 / 33 / 34

### Batch 9：控制面与外部入口收官

- 已修复：
  - OA 通知接口忽略客户端传入的 `user_id`，统一绑定当前登录用户
  - MCP 工具列表改为仅平台管理员可见，普通登录用户不再能枚举内部工具能力
  - 公开 `/health` 仅返回最小化 `status` 字段，并补回归测试锁定该行为
- 对应问题：
  - 19 / 20 / 21

## 验证证据

- 后端测试通过：
  - `pytest backend/tests/test_security_authorization_guards.py backend/tests/test_case_service.py -q`
  - `pytest backend/tests/test_chat.py -q`
  - `pytest backend/tests/test_security_authorization_guards.py backend/tests/test_case_service.py backend/tests/test_chat.py backend/tests/test_sentiment.py -q`
  - `pytest backend/tests/test_auth_surface_hardening.py backend/tests/test_auth_roles_permissions.py backend/tests/test_security_authorization_guards.py backend/tests/test_case_service.py backend/tests/test_chat.py backend/tests/test_sentiment.py -q`
  - `pytest backend/tests/test_realtime_authorization_guards.py backend/tests/test_auth_surface_hardening.py backend/tests/test_security_authorization_guards.py backend/tests/test_chat.py -q`
  - `pytest backend/tests/test_external_surface_guards.py -q`
  - `pytest backend/tests/test_auth_surface_hardening.py backend/tests/test_auth_roles_permissions.py -q`
  - `pytest backend/tests/test_external_surface_guards.py -q`（时间戳/重放/白名单增强后复验）
  - `pytest backend/tests/test_external_surface_guards.py -q`（OA/MCP/health 收口后复验）
  - `pytest backend/tests/test_business_authorization_guards.py backend/tests/test_review_authorization_api.py -q`
  - `pytest backend/tests/test_sync_api_security.py backend/tests/test_auth_surface_hardening.py -q`
- 前端构建通过：
  - `cd frontend && npm run build`
- 新增回归：
  - `backend/tests/test_security_authorization_guards.py`
  - `backend/tests/test_auth_surface_hardening.py`
  - `backend/tests/test_realtime_authorization_guards.py`
  - `backend/tests/test_external_surface_guards.py`
- 当前已知非阻断告警：
  - 前端构建仍有 `lottie-web` 的 `eval` 告警，和本次权限修复无直接关联

## 说明

- 下方“已确认高风险问题 / 已确认越权与边界缺口”保留的是本轮审计期间的原始发现留档，便于追溯问题来源。
- 这些条目并不表示它们当前都仍未修复；当前状态请优先以本文件“当前遗留问题”和 `docs/archive/legacy-root-docs/2026-04-03-security-remediation-matrix.md` 为准。

## 已确认高风险问题

### 1. 仓库中存在已提交的真实密钥

- 证据：
  - `/.env` 已被 Git 跟踪
  - `.gitignore` 虽然忽略 `.env`，但仓库内已有已跟踪文件
- 影响：
  - 仓库历史中的密钥可能已泄露
  - 需要立即轮换并考虑清理历史
- 证据位置：
  - `/.env`
  - `/.gitignore`

### 2. 注册/登录/找回密码缺少人机校验

- 现状：
  - 登录、注册、找回密码、重发验证码均未接入验证码挑战或人机校验
  - 重置密码依赖 6 位邮箱验证码
  - `forgot-password` 未见后端限流依赖
- 影响：
  - 容易被撞库、爆破、邮箱轰炸和自动化注册滥用
- 证据位置：
  - `/backend/src/api/routes/auth.py`
  - `/frontend/src/pages/Login.tsx`

### 2.1 验证码/重置码强度与绑定关系不足

- 现状：
  - 邮箱验证码和密码重置码都为 6 位数字
  - 两类 token 都保存在进程内存字典中，并以“验证码本身”作为 key
  - 重置密码接口仅提交 `token + new_password`，未再次绑定邮箱、会话或一次性挑战上下文
- 影响：
  - 容易被枚举和碰撞放大风险
  - 服务重启会丢失所有验证码状态
  - 找回密码链路缺少更高熵的一次性令牌
- 证据位置：
  - `/backend/src/api/routes/auth.py`

### 3. Redis 故障时安全控制降级为放行

- 现状：
  - Token 黑名单查询失败时返回未拉黑
  - 限流检查失败时允许请求通过
  - 认证依赖在黑名单校验异常时回退到不带黑名单的 `verify_token`
- 影响：
  - Redis 不可用时，已注销 token、已撤销 token、敏感接口限流都可能失效
- 证据位置：
  - `/backend/src/core/security.py`
  - `/backend/src/core/deps.py`

### 4. OAuth state 未校验

- 现状：
  - 获取微信/支付宝 OAuth URL 时会生成 `state`
  - 回调接口接收 `state`，但未验证
- 影响：
  - 存在登录 CSRF 和流程混淆风险
- 证据位置：
  - `/backend/src/api/routes/auth.py`

### 5. 前端将 access token / refresh token 存入 localStorage

- 现状：
  - `access_token`、`refresh_token` 都会写入浏览器持久存储
- 影响：
  - 一旦发生 XSS，会话令牌可被直接窃取
- 证据位置：
  - `/frontend/src/lib/api.ts`
  - `/frontend/src/lib/store.ts`
  - `/frontend/src/pages/Login.tsx`

### 6. 支付与电子签 Webhook 缺少验签

- 现状：
  - 微信支付、支付宝、电子签回调仍为未验签占位实现
- 影响：
  - 一旦后续接入真实状态更新，外部可伪造回调
- 证据位置：
  - `/backend/src/api/routes/payments.py`
  - `/backend/src/api/routes/esign.py`

## 已确认越权与边界缺口

### 7. 协作编辑存在未鉴权 HTTP 备用接口

- 现状：
  - 协作 HTTP 备用接口可直接提交操作、创建评论、列出评论、解决评论、查询在线用户
  - 这些接口未要求登录，也未校验成员关系
- 影响：
  - 可伪造任意用户进行评论、操作注入、在线状态探测
- 证据位置：
  - `/backend/src/api/routes/collaboration_ws.py`

### 8. 协作会话存在公开元数据接口

- 现状：
  - 会话列表、会话详情、协作者列表接口未要求登录
- 影响：
  - 可能泄露协作会话 ID、文档 ID、协作者信息和活动情况
- 证据位置：
  - `/backend/src/api/routes/collaboration.py`

### 9. 知识库路由调用服务时未传入用户上下文，服务层资源归属校验失效

- 现状：
  - 多个知识库接口虽然要求登录，但调用 `KnowledgeService` 时没有传 `user.id` / `user.org_id`
  - `KnowledgeService.get_knowledge_base`、`get_document`、`update_document`、`delete_knowledge_base`、`export_knowledge_base` 等方法本身缺少强制资源归属校验
- 影响：
  - 可能发生跨租户知识库读取、修改、删除、导出
- 证据位置：
  - `/backend/src/api/routes/knowledge.py`
  - `/backend/src/services/knowledge_service.py`

### 10. 文档服务缺少资源归属校验

- 现状：
  - 文档详情、更新、删除、版本历史等路由只要求登录
  - `DocumentService.get_document/update/delete` 未按 `org_id` / `created_by` 过滤
- 影响：
  - 已登录用户可能通过文档 ID 访问或修改其他组织文档
- 证据位置：
  - `/backend/src/api/routes/documents.py`
  - `/backend/src/services/document_service.py`

### 10.1 案件与文档关联存在跨组织挂接风险

- 现状：
  - 案件接口会先校验案件归属
  - 但 `CaseService.link_document` 只按 `document_id` 取文档，不校验文档 `org_id`
  - 成功关联后，可通过案件文档列表读取该文档元数据与摘要
- 影响：
  - 已登录用户若获知其他组织文档 ID，可能将外部文档挂到自己案件并读取
- 证据位置：
  - `/backend/src/api/routes/cases.py`
  - `/backend/src/services/case_service.py`

## 已确认实时通道问题

### 11. IM WebSocket 将 JWT 放在 URL 中

- 现状：
  - IM WebSocket 使用 `?token=...` 建连
- 影响：
  - Token 易进入浏览器历史、代理日志、服务日志
- 证据位置：
  - `/frontend/src/hooks/useIMWebSocket.ts`
  - `/backend/src/api/routes/im.py`

### 12. 协作 WebSocket 认证后仍信任客户端声明身份

- 现状：
  - 服务端在 `join` 消息中继续接受客户端提交的 `user_id` / `user_name`
- 影响：
  - 存在冒名和用户态污染风险
- 证据位置：
  - `/backend/src/api/routes/collaboration_ws.py`

### 12.1 第二套协作 WebSocket 完全依赖 query 参数冒充身份

- 现状：
  - `/collaboration/ws/{session_id}` 直接使用 query 参数中的 `user_id` / `nickname` / `color`
  - 若数据库中不存在该协作者，会自动创建并赋予 `editor` 角色
  - 未要求登录，也未校验当前用户是否属于该会话
- 影响：
  - 任意人只要知道 `session_id` 就可能伪造身份接入协作会话并写入协作者记录
- 证据位置：
  - `/backend/src/api/routes/collaboration.py`

### 13. LIC WebSocket 无认证

- 现状：
  - 任务状态查询 HTTP 需要登录，但对应 WebSocket 进度流不需要认证
- 影响：
  - 如果 task_id 可预测或泄露，可能造成任务进度信息泄露
- 证据位置：
  - `/backend/src/api/routes/lic.py`

### 13.1 LIC 抓取接口允许已登录用户驱动服务端访问任意 URL

- 现状：
  - `POST /lic/crawl` 接收客户端提交的 `url`
  - 后端使用 Playwright 直接访问该 URL，并抓取页面内容后入库
  - 未见目标地址白名单、私网地址拦截、协议限制或重定向限制
- 影响：
  - 存在 SSRF / 内网探测 / 对内部控制面发起浏览器级请求的风险
- 证据位置：
  - `/backend/src/api/routes/lic.py`
  - `/backend/src/services/crawler_service.py`

## 已确认设计缺陷

### 14. 匿名聊天房间创建接口公开，且单次响应返回双方 token

- 现状：
  - 创建匿名聊天室无需登录
  - 单个调用方会拿到 `user_token` 和 `lawyer_token`
  - 房间和 token 仅保存在进程内存中，未见过期治理
- 影响：
  - 调用方可同时模拟双方身份
  - 服务重启丢状态
  - URL token 继续存在泄露风险
- 证据位置：
  - `/backend/src/api/routes/anonymous_chat.py`

## 校验不一致问题

### 15. 上传校验策略不一致

- 现状：
  - 文档主上传接口有扩展名与大小校验
  - 知识库上传/批量上传、合同解析/流式审查等接口未统一复用 `validators.py`
  - `validators.py` 中已有更完整的文件校验逻辑，但路由层未统一使用
- 影响：
  - 不同入口的安全强度不一致，容易形成旁路
- 证据位置：
  - `/backend/src/api/routes/documents.py`
  - `/backend/src/api/routes/knowledge.py`
  - `/backend/src/api/routes/contracts.py`
  - `/backend/src/core/validators.py`

## 已确认的内部信息暴露问题

### 16. LLM 配置接口缺少租户过滤

- 现状：
  - `LLMConfig` 模型存在 `org_id`
  - `LLMService.list_configs()` 支持按 `org_id` 过滤
  - 但路由层普通已登录用户访问 `/llm/configs`、`/llm/configs/default`、`/llm/configs/{id}` 时未传入 `user.org_id`
  - 返回结果中还会包含 `api_base_url`、`local_endpoint`、`api_key_masked`
- 影响：
  - 普通已登录用户可能看到全局或其他组织的模型配置、内网服务地址和密钥指纹信息
- 证据位置：
  - `/backend/src/models/llm_config.py`
  - `/backend/src/services/llm_service.py`
  - `/backend/src/api/routes/llm.py`

### 17. RTC 房间接口缺少参与者级授权

- 现状：
  - 创建 RTC 房间时仅要求登录，不校验当前用户是否属于 `conversation_id`
  - 任意已登录用户可为任意 `room_name` 获取加入 token
  - 任意已登录用户可结束任意房间，并可列出所有活跃房间
- 影响：
  - 存在通话窃听、房间枚举、未授权加入和拒绝服务风险
- 证据位置：
  - `/backend/src/api/routes/rtc.py`
  - `/backend/src/services/rtc_service.py`

### 18. IM 用户搜索未按组织过滤

- 现状：
  - IM 用户搜索接口返回所有活跃用户的姓名、邮箱、头像、部门、角色
  - 未见按 `org_id` 或业务可见性过滤
- 影响：
  - 已登录用户可能枚举系统内其他组织用户目录，造成隐私和组织结构信息泄露
- 证据位置：
  - `/backend/src/api/routes/im.py`

### 19. 健康检查端点公开暴露基础设施状态

- 现状：
  - `/health` 为公开端点
  - 返回 PostgreSQL、Redis、Qdrant、MinIO、Neo4j 的状态和延迟
- 影响：
  - 可被用于外部侦察内部基础设施组成和运行状态
- 证据位置：
  - `/backend/src/api/routes/health.py`

### 20. OA 集成接口允许已登录用户代他人发通知或发起审批

- 现状：
  - `/integrations/notify` 接收客户端提交的 `user_id`
  - `/integrations/approval/create` 接收客户端提交的 `initiator_id`
  - 路由层未见这些字段与当前登录用户的绑定校验
- 影响：
  - 在真实 OA 接入后，存在代他人发送通知、伪造审批发起人的风险
- 证据位置：
  - `/backend/src/api/routes/integrations.py`
  - `/backend/src/services/oa_integration_service.py`

### 21. MCP 工具列表对所有已登录用户开放

- 现状：
  - MCP 服务的增删改连为管理员接口
  - 但 `/mcp/tools` 对任意已登录用户开放，直接返回当前已连接服务器的工具清单
- 影响：
  - 可能向普通用户泄露内部工具能力、集成面和连接目标信息
- 证据位置：
  - `/backend/src/api/routes/mcp_routes.py`
  - `/backend/src/services/mcp_client_service.py`

### 22. 同步接口整体未鉴权且仍处占位状态

- 现状：
  - `/sync/push`、`/sync/pull`、`/sync/status`、`/sync/resolve`、`/sync/full-sync` 未要求登录
  - 代码注释明确写有 “TODO: 验证设备身份和用户权限”
  - 当前实现基本为占位，未见真实权限边界
- 影响：
  - 若启用到客户端数据面，可能形成批量数据同步、冲突篡改和全量导出入口
- 证据位置：
  - `/backend/src/api/routes/sync.py`

### 23. AI 旁听记录存在所有权校验缺口

- 现状：
  - 旁听记录列表按 `started_by` 过滤
  - 但 `status/{conversation_id}`、`insights/{conversation_id}`、`summary/{conversation_id}` 通过 `conversation_id` 直接读取记录
  - `link-case` 根据 `record_id` 更新关联关系时未校验 `started_by`
- 影响：
  - 已登录用户可能读取或修改不属于自己的旁听记录
- 证据位置：
  - `/backend/src/api/routes/meeting_assistant.py`
  - `/backend/src/services/meeting_assistant_service.py`
  - `/backend/src/models/meeting_record.py`

### 24. 数据中心服务缺少组织隔离，列表接口仅按角色过滤

- 现状：
  - 数据中心记录包含 `owner_id`，但没有 `org_id`
  - `list_data()` 仅依据角色等级过滤，不校验 owner 或组织
  - 高权限用户可列出所有达到其访问级别的数据资产元信息
- 影响：
  - 存在跨用户、跨组织的数据资产目录暴露风险
- 证据位置：
  - `/backend/src/api/routes/datacenter.py`
  - `/backend/src/services/data_center_service.py`

### 25. 获客分析接口允许客户端指定任意 `org_id`

- 现状：
  - 获客分析接口要求 `VIEW_ANALYTICS` 权限
  - 但 `org_id` 由客户端直接传入，服务层按该值查询
  - 未见把 `org_id` 强绑定到当前登录用户所属组织
- 影响：
  - 拥有分析权限的用户可能读取其他组织的获客统计
- 证据位置：
  - `/backend/src/api/routes/acquisition_analytics.py`
  - `/backend/src/services/acquisition_analytics_service.py`

### 26. 订阅报表接口允许按任意 `org_id` 查询

- 现状：
  - `/billing/reports/subscriptions` 仅要求 `VIEW_REPORTS`
  - 路由层直接接受客户端传入的 `org_id`
  - 服务层按该 `org_id` 返回订阅统计
- 影响：
  - 具备报表权限的用户可能读取其他组织的订阅与营收统计
- 证据位置：
  - `/backend/src/api/routes/billing.py`
  - `/backend/src/services/subscription_service.py`

### 27. 功能开关后台列表对 `ORG_ADMIN` 可能暴露全局配置

- 现状：
  - 功能开关后台接口允许 `ADMIN` / `ORG_ADMIN` / `SUPER_ADMIN`
  - `FeatureFlagService.list_all()` 返回所有开关
  - 路由层未按 `target_org_ids` 或当前用户组织过滤后台列表
- 影响：
  - 组织管理员可能看到不属于本组织的全局或其他组织灰度配置
- 证据位置：
  - `/backend/src/api/routes/feature_flags.py`
  - `/backend/src/services/feature_flag_service.py`

### 28. 审批列表与详情缺少租户/参与者范围约束

- 现状：
  - 审批列表接口允许按 `requester_id` / `approver_id` 过滤
  - 查询条件未强制绑定当前用户、当前组织或审批参与关系
  - 审批详情接口按 `approval_id` 直接返回
- 影响：
  - 已登录用户可能查看不属于自己的审批记录与审批详情
- 证据位置：
  - `/backend/src/api/routes/approvals.py`

### 29. 用户可为任意组织创建订阅

- 现状：
  - 创建订阅接口允许客户端提交 `org_id`
  - 路由层将 `req.org_id` 直接传给服务层
  - 未校验该组织是否属于当前用户或当前用户是否有为组织创建订阅的权限
- 影响：
  - 已登录用户可能为其他组织创建或污染订阅记录
- 证据位置：
  - `/backend/src/api/routes/billing.py`
  - `/backend/src/services/subscription_service.py`

### 30. 数据中心存储接口允许用户自行指定访问级别

- 现状：
  - 普通已登录用户调用 `/datacenter/store` 时可直接提交 `access_level`
  - 服务端未见对其可设置的最高等级进行限制
- 影响：
  - 可能形成“自封高敏资产”与权限模型混乱，放大后续访问控制复杂度
- 证据位置：
  - `/backend/src/api/routes/datacenter.py`
  - `/backend/src/services/data_center_service.py`

### 31. 律师评价创建未校验真实服务关系

- 现状：
  - 评价创建时允许提交 `consultation_id` / `delegation_id`
  - 服务层未校验评价人是否真实参与该咨询/委托，也未限制重复评价
- 影响：
  - 已登录用户可能对任意律师刷分、刷评或恶意评价
- 证据位置：
  - `/backend/src/api/routes/lawyer_matching.py`
  - `/backend/src/services/review_service.py`

### 32. 舆情模块详情/更新接口缺少组织归属校验

- 现状：
  - 监控配置详情、更新、删除、启停接口通过 `monitor_id` 直接操作
  - 舆情记录详情通过 `record_id` 直接读取
  - 预警详情/已读/处理通过 `alert_id` 直接操作
  - 服务层 `get_monitor/get_record/get_alert` 未按 `org_id` 过滤
- 影响：
  - 已登录用户可能横向读取或操作其他组织的舆情配置、记录和预警
- 证据位置：
  - `/backend/src/api/routes/sentiment.py`
  - `/backend/src/services/sentiment_service.py`

### 33. 尽调历史详情缺少所有权校验

- 现状：
  - 调查历史列表按 `user_id` 过滤
  - 但单条调查详情 `GET /investigations/{investigation_id}` 直接按主键读取
  - 报告生成接口 `POST /investigations/{investigation_id}/report` 也未校验该调查是否属于当前用户
- 影响：
  - 已登录用户可能读取或导出不属于自己的尽调调查结果
- 证据位置：
  - `/backend/src/api/routes/due_diligence.py`

### 34. 尽调快照/趋势/缓存状态接口存在弱边界

- 现状：
  - 企业快照列表会传入 `user_id`
  - 但风险趋势、快照对比、缓存状态、缓存失效等接口未见明确用户/组织边界
  - 多数接口以 `company_name` 或 `snapshot_id` 直接读取
- 影响：
  - 可能被用于探测其他用户调查过的企业、缓存状态或历史趋势
- 证据位置：
  - `/backend/src/api/routes/due_diligence.py`
  - `/backend/src/services/investigation_data_store.py`

## 与项目状态文档的偏差

- `PROJECT_STATUS.md` 当前写明“安全纵深防御”“验证码端点频率限制”“匿名聊天加固”等内容已完成
- 但本次代码审计发现：
  - `PROJECT_STATUS.md` 声明“.env 从 git 追踪中移除”，实际仓库仍可见已跟踪 `.env`
  - 仍缺少 CAPTCHA / 人机挑战
  - 找回密码端点缺少一致限流
  - 匿名聊天设计仍存在双 token 同回包与 URL token 风险
  - 协作和知识库/文档侧仍有未闭合的越权面

## 建议的立即处置顺序

1. 立刻轮换所有已提交到 `.env` 的真实密钥，并制定历史清理方案
2. 给登录、注册、找回密码、重发验证码、重置密码补齐 CAPTCHA / Turnstile
3. 将 Redis 故障时的认证敏感路径改为 fail-closed 或保守降级
4. 补齐 OAuth state 校验与 webhook 验签
5. 修复知识库、文档、协作接口的资源归属与成员关系校验
6. 清理 URL token，改为首包鉴权或短期票据

## 下一步待核验

- 文档、知识库、协作接口的实际可利用链是否能跨组织读写
- 任务类、审批类、聊天类接口是否还存在类似“路由已登录、服务层未隔离”的模式
- 前端是否存在更多可结合 token 存储放大的 XSS 落点
- 生产部署层是否对公开回调、WebSocket、认证端点补了额外网关防护
