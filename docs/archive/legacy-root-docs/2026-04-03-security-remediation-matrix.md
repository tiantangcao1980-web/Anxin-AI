# 2026-04-03 安全整改矩阵

## 使用说明

- 本文档将审计问题按编号、风险级别、影响范围、证据位置、建议修复进行汇总
- 目标：为后续 P0/P1 修复提供直接执行清单
- 对应详细证据请参考 `docs/archive/legacy-root-docs/2026-04-03-security-audit-record.md`

## 当前进展

- 2026-04-03 Batch 1 已开始落地：
  - 协作会话详情/成员列表/快照/提交接口增加成员校验
  - 协作主 WebSocket 改为首包 token 鉴权，不再信任 query `user_id`
  - 协作文档 HTTP 备用接口增加登录与成员校验
  - 文档 API 增加 `org_id` 归属校验
  - 知识库 API 开始将 `user_id/org_id` 传入服务层并做访问限制
  - 案件关联文档增加文档归属校验
  - 已补针对性回归测试并通过
- 2026-04-03 Batch 2 已开始落地：
  - AI 旁听记录按发起人校验读取与关联权限
  - 获客分析按当前用户组织收口，非平台管理员不可跨组织查询
  - 订阅创建与订阅报表增加组织范围限制
  - 数据中心列表按 owner 收口，存储接口限制可设置的访问等级
  - 审批列表与审批详情增加当前用户/组织范围过滤
  - 功能开关后台列表对 `ORG_ADMIN` 增加组织过滤
  - 舆情模块监控/记录/预警详情与操作接口增加组织归属校验
  - 已通过现有后端回归和前端构建验证
- 2026-04-03 Batch 3 已开始落地：
  - `forgot-password` 增加频率限制
  - OAuth 回调增加 `state` 校验
  - Token 黑名单与限流在 Redis 不可用时改为本地回退控制，而不是直接放行
  - LIC 抓取接口增加 localhost/私网/保留地址拦截
  - `sync` 占位接口增加登录要求并统一返回 503
  - 已新增认证/外联面安全回归并通过
- 2026-04-03 Batch 4 已开始落地：
  - RTC 房间创建 / 加入 token / 结束房间 / 房间列表增加 IM 参与者授权
  - IM 用户搜索默认限制为同组织用户
  - 已新增实时面权限回归并通过
- 2026-04-03 Batch 5 已开始落地：
  - 支付 / 电签 webhook 增加基础签名校验
  - OA 审批发起人绑定当前用户
  - LIC 任务增加 owner 维度，状态与实时流按 owner 校验
  - 已新增外部入口安全回归并通过
- 2026-04-03 Batch 6 已开始落地：
  - 后端接入 Turnstile 验证能力
  - 登录 / 注册 / 忘记密码在开启 CAPTCHA 时要求验证码 token
  - 登录页动态加载并渲染 Turnstile 组件
  - 已通过认证回归和前端构建验证
- 2026-04-03 Batch 7 已开始落地：
  - Webhook 校验升级为时间戳 + HMAC，并增加简单防重放缓存
  - LIC 抓取支持显式域白名单
  - 已通过外部入口回归和前端构建验证
- 2026-04-03 Batch 8 已开始落地：
  - 审批动作要求当前有效审批人
  - 尽调详情/报告/趋势/快照对比按所有权收口
  - 尽调缓存状态与缓存失效对普通用户默认关闭
  - 律师评价增加重复评价拦截
  - `sync` 升级为按用户和设备隔离的最小安全实现
  - 已通过业务越权回归和前端构建验证
- 2026-04-03 Batch 9 已开始落地：
  - OA 通知接口忽略客户端 `user_id`，统一绑定当前登录用户
  - MCP 工具列表改为仅平台管理员可见
  - `/health` 公网响应锁定为最小化 `status` 字段
  - 已通过外部入口回归复验

## 已完成修复映射

| 问题编号 | 当前状态 | 说明 |
|---|---|---|
| S-008 | 已修复 | 第二套协作 WebSocket 改为 token 鉴权，不再信任 query 身份 |
| S-009 | 已修复 | 协作 HTTP 备用接口增加登录与成员校验 |
| S-010 | 部分修复 | 协作会话详情/成员/快照/提交已收口，列表是否进一步细化可继续评估 |
| S-002 | 部分修复 | 登录 / 注册 / 忘记密码已接入 Turnstile 能力；其余敏感入口是否统一接入仍可继续推进 |
| S-004 | 部分修复 | Redis 故障时已有本地回退控制，但更严格的 fail-closed 策略仍可继续加强 |
| S-005 | 已修复 | OAuth 回调增加 state 校验 |
| S-006 | 部分修复 | Webhook 已增加时间戳与简单防重放骨架，真实渠道官方签名协议仍可继续加强 |
| S-011 | 部分修复 | LIC 已支持内网拦截与显式域白名单，重定向策略和更细粒度规则仍可继续加强 |
| S-012 | 部分修复 | sync 已升级为按用户/设备隔离的最小实现，但正式持久化、签名与冲突策略仍可继续加强 |
| S-105 | 已修复 | RTC 房间相关接口已增加参与者授权与房间可见性过滤 |
| S-106 | 已修复 | IM 用户搜索默认按组织过滤，平台管理员保留全局视图 |
| S-101 | 已修复 | 知识库路由开始传递 user/org 上下文并在服务层校验 |
| S-102 | 已修复 | 文档详情/更新/删除/版本历史已按 org 限制 |
| S-103 | 已修复 | 案件关联文档前校验文档 org |
| S-107 | 已修复 | AI 旁听记录读取与关联受 started_by 约束 |
| S-108 | 部分修复 | 数据中心列表按 owner 收口，后续仍建议加入 org 维度 |
| S-109 | 已修复 | 获客分析非平台管理员固定到当前组织 |
| S-110 | 已修复 | 订阅报表非平台管理员固定到当前组织 |
| S-111 | 已修复 | ORG_ADMIN 功能开关后台列表已按组织过滤 |
| S-112 | 已修复 | OA 审批发起人与通知目标均已绑定当前登录用户 |
| S-113 | 已修复 | MCP 工具列表已改为仅平台管理员可见 |
| S-114 | 已修复 | 公网 `/health` 仅返回最小化状态字段 |
| S-013 | 已修复 | LIC 任务状态和 WebSocket 进度已按 owner 限制 |
| S-028 | 已修复 | 审批列表与详情增加用户/组织范围过滤 |
| S-031 | 已修复 | 律师评价必须基于真实服务关系，且相同记录不可重复评价 |
| S-032 | 已修复 | 舆情监控/记录/预警详情与操作增加 org 校验 |
| S-033 | 已修复 | 尽调单条详情和报告生成已按所有权收口 |
| S-034 | 部分修复 | 尽调趋势/快照对比已按用户快照收口，缓存状态默认对普通用户关闭 |

## 当前遗留问题清单

### P0 / 高优先级

| 编号 | 当前状态 | 遗留点 | 下一步建议 |
|---|---|---|---|
| S-001 | 未修复 | Git 历史中的真实密钥泄露风险仍在 | 立即轮换全部相关密钥；评估历史清理与访问审计 |
| S-003 | 未修复 | 密码重置仍为 6 位数字码，缺少高熵单次 token 与上下文绑定 | 改为高熵一次性令牌；绑定邮箱/用途/有效期；限制尝试次数 |
| S-004 | 部分修复 | Redis 异常时已有本地回退，但认证/刷新/高敏感限流未 fail-closed | 敏感认证链路改成严格拒绝或更保守降级 |
| S-006 | 部分修复 | 仅实现通用时间戳 HMAC + 简单防重放 | 切换到微信/支付宝/电签官方签名协议并增强重放保护 |
| S-007 | 未修复 | 前端 access/refresh token 仍在 `localStorage` | 迁移到 HttpOnly Cookie 或显著收紧会话与 CSP/XSS 面 |
| S-011 | 部分修复 | LIC 已有白名单与重定向落点校验，但策略粒度仍偏粗 | 继续细化域策略、重定向链控制和审计 |
| S-012 | 部分修复 | `sync` 为最小安全实现，尚未持久化和签名化 | 设计正式存储、签名、版本/冲突解决模型 |
| S-104 | 未修复 | LLM 配置接口组织隔离仍未收口 | 普通用户仅见本组织配置；ORG_ADMIN 也需限域 |

### P1 / 收尾优化

| 编号 | 当前状态 | 遗留点 | 下一步建议 |
|---|---|---|---|
| S-002 | 部分修复 | CAPTCHA 仅覆盖登录/注册/忘记密码 | 将重发验证码、重置密码等敏感入口也统一纳入挑战 |
| S-010 | 部分修复 | 协作列表接口可见性仍可继续细化 | 评估是否按组织/成员/文档范围进一步裁剪列表 |
| S-108 | 部分修复 | 数据中心仅按 owner 收口，模型缺 org 维度 | 在数据模型中补 org 字段并统一按 owner/org/role 判定 |
| S-034 | 部分修复 | 尽调快照/趋势/缓存相关边界仍不完全一致 | 继续补 API 级授权回归并统一访问规则 |
| S-201 | 未修复 | 匿名聊天仍公开创建且单次返回双方 token | 拆分 token 投递与单边可见控制 |
| S-202 | 未修复 | IM 仍有 URL token 使用 | 改为首包认证或短期 ticket |
| S-203 | 未修复 | 上传入口校验策略未统一 | 抽取统一 validators 并覆盖所有上传路径 |
| S-204 | 持续风险 | 文档与实现可能再次偏移 | 每批修复结束强制同步状态与验证记录 |

## 最近验证

- `pytest backend/tests/test_security_authorization_guards.py backend/tests/test_case_service.py -q`
- `pytest backend/tests/test_chat.py -q`
- `pytest backend/tests/test_security_authorization_guards.py backend/tests/test_case_service.py backend/tests/test_chat.py backend/tests/test_sentiment.py -q`
- `pytest backend/tests/test_auth_surface_hardening.py backend/tests/test_auth_roles_permissions.py backend/tests/test_security_authorization_guards.py backend/tests/test_case_service.py backend/tests/test_chat.py backend/tests/test_sentiment.py -q`
- `pytest backend/tests/test_realtime_authorization_guards.py backend/tests/test_auth_surface_hardening.py backend/tests/test_security_authorization_guards.py backend/tests/test_chat.py -q`
- `pytest backend/tests/test_external_surface_guards.py -q`
- `pytest backend/tests/test_auth_surface_hardening.py backend/tests/test_auth_roles_permissions.py -q`
- `pytest backend/tests/test_external_surface_guards.py -q` (replay/allowlist update)
- `pytest backend/tests/test_external_surface_guards.py -q` (OA/MCP/health 收口后复验)
- `pytest backend/tests/test_business_authorization_guards.py backend/tests/test_review_authorization_api.py -q`
- `pytest backend/tests/test_sync_api_security.py backend/tests/test_auth_surface_hardening.py -q`
- `cd frontend && npm run build`

## 历史整改建议留档

以下为审计初期形成的原始整改建议表，保留用于追溯问题来源与当时的修复优先级判断。当前真实状态请以上方“已完成修复映射”和“当前遗留问题清单”为准。

## P0 立即处理（原始建议）

| 编号 | 风险 | 问题 | 影响面 | 核心证据 | 建议修复 |
|---|---|---|---|---|---|
| S-001 | Critical | 已提交真实密钥的 `.env` 仍被 Git 跟踪 | 全局密钥泄露 | `/.env`, `/.gitignore` | 立即轮换全部密钥；移除追踪；评估 Git 历史清理 |
| S-002 | High | 注册/登录/找回密码缺少 CAPTCHA / 人机校验 | 认证入口 | `backend/src/api/routes/auth.py`, `frontend/src/pages/Login.tsx` | 登录、注册、忘记密码、重发验证码、重置密码统一接入 Turnstile/hCaptcha |
| S-003 | High | 验证码/重置码仅 6 位数字，重置链路未绑定额外上下文 | 认证入口 | `backend/src/api/routes/auth.py` | 改为高熵单次 token；绑定邮箱/用途/会话；落 Redis；限制尝试次数 |
| S-004 | High | Redis 故障时限流与 token 黑名单降级为放行 | 全局认证与风控 | `backend/src/core/security.py`, `backend/src/core/deps.py` | 敏感接口改 fail-closed；至少认证与刷新链路不允许无保护放行 |
| S-005 | High | OAuth `state` 未校验 | 第三方登录 | `backend/src/api/routes/auth.py` | 服务端持久化并验证 `state`；失败拒绝回调 |
| S-006 | High | 支付/电子签 webhook 未验签 | 外部回调 | `backend/src/api/routes/payments.py`, `backend/src/api/routes/esign.py` | 上线前完成签名校验与重放保护 |
| S-007 | High | 前端将 access/refresh token 写入 localStorage | Web 前端会话 | `frontend/src/lib/api.ts`, `frontend/src/lib/store.ts` | 改 HttpOnly Cookie 或至少缩短 refresh 生命周期并加强 CSP/XSS 防护 |
| S-008 | Critical | 第二套协作 WebSocket 信任 query 参数身份并自动写协作者记录 | 协作通道 | `backend/src/api/routes/collaboration.py` | 移除 query 身份；统一使用服务器认证态；校验会话成员关系 |
| S-009 | High | 协作 HTTP 备用接口未鉴权 | 协作通道 | `backend/src/api/routes/collaboration_ws.py` | 全部加认证和成员校验；无业务必要则直接下线 |
| S-010 | High | 协作会话元数据接口公开 | 协作通道 | `backend/src/api/routes/collaboration.py` | 列表/详情/协作者/快照接口统一要求认证并校验成员 |
| S-011 | High | LIC 抓取接口允许任意 URL，存在 SSRF | 外联抓取 | `backend/src/api/routes/lic.py`, `backend/src/services/crawler_service.py` | 加目标域白名单、私网阻断、协议限制、重定向限制、审计 |
| S-012 | Critical | 同步接口整体未鉴权且为占位实现 | 客户端数据面 | `backend/src/api/routes/sync.py` | 未完成前禁止暴露；至少要求用户+设备认证并增加签名/版本校验 |

## P1 优先修复（原始建议）

| 编号 | 风险 | 问题 | 影响面 | 核心证据 | 建议修复 |
|---|---|---|---|---|---|
| S-101 | High | 知识库路由未传 user/org 上下文，服务层隔离失效 | 知识库 | `backend/src/api/routes/knowledge.py`, `backend/src/services/knowledge_service.py` | 所有读写接口传 `user.id/org_id`；服务层强制校验 |
| S-102 | High | 文档详情/更新/删除/版本历史缺少组织归属校验 | 文档管理 | `backend/src/api/routes/documents.py`, `backend/src/services/document_service.py` | 所有 `get/update/delete/get_versions` 按 `org_id` 过滤 |
| S-103 | High | 案件关联文档时未校验文档归属 | 案件/文档 | `backend/src/api/routes/cases.py`, `backend/src/services/case_service.py` | 关联前校验 `document.org_id == user.org_id` |
| S-104 | High | LLM 配置接口缺少组织隔离 | 模型配置 | `backend/src/api/routes/llm.py`, `backend/src/services/llm_service.py` | 普通用户仅能看本组织可见配置；ORG_ADMIN 也要限域 |
| S-105 | High | RTC 房间接口缺少参与者级授权 | 音视频 | `backend/src/api/routes/rtc.py` | 绑定 conversation 参与者；限制 room token 发放与结束房间权限 |
| S-106 | High | IM 用户搜索未按组织过滤 | 用户目录 | `backend/src/api/routes/im.py` | 至少按 org 过滤；必要时增加最小搜索长度和可见性规则 |
| S-107 | High | AI 旁听记录缺少所有权校验 | 会议纪要 | `backend/src/api/routes/meeting_assistant.py` | conversation_id 和 record_id 路由统一校验 `started_by == current_user` |
| S-108 | High | 数据中心列表仅按角色过滤，不按 owner/org 隔离 | 数据中心 | `backend/src/api/routes/datacenter.py`, `backend/src/services/data_center_service.py` | 数据模型加入 org 维度；列表/读取同时校验 owner/org/role |
| S-109 | High | 获客分析接口允许客户端指定任意 org_id | 分析报表 | `backend/src/api/routes/acquisition_analytics.py` | 非平台管理员强制使用当前用户 org_id |
| S-110 | High | 订阅报表允许按任意 org_id 查询 | 计费报表 | `backend/src/api/routes/billing.py`, `backend/src/services/subscription_service.py` | 非平台管理员忽略客户端 org_id，仅用当前组织 |
| S-111 | Medium | 功能开关后台列表对 ORG_ADMIN 未做组织过滤 | 灰度配置 | `backend/src/api/routes/feature_flags.py`, `backend/src/services/feature_flag_service.py` | ORG_ADMIN 仅查看与本 org 相关的 flags |
| S-112 | Medium | OA 集成接口允许代他人发通知或发起审批 | 外部集成 | `backend/src/api/routes/integrations.py` | `initiator_id/user_id` 绑定当前用户，或限制管理员专用 |
| S-113 | Medium | MCP 工具列表对所有登录用户开放 | 控制面能力暴露 | `backend/src/api/routes/mcp_routes.py` | 至少改管理员可见，或返回租户级裁剪结果 |
| S-114 | Medium | 健康检查公开暴露内部组件状态 | 运维面 | `backend/src/api/routes/health.py` | 公网仅返回简版健康；详细状态仅内部或管理员可见 |

## P2 设计优化（原始建议）

| 编号 | 风险 | 问题 | 影响面 | 核心证据 | 建议修复 |
|---|---|---|---|---|---|
| S-201 | Medium | 匿名聊天创建接口公开且同次返回双方 token | 匿名咨询 | `backend/src/api/routes/anonymous_chat.py` | 改成服务端分别投递 token；增加过期与单边可见控制 |
| S-202 | Medium | IM/协作仍有 URL token 使用 | WebSocket | `backend/src/api/routes/im.py`, `frontend/src/hooks/useIMWebSocket.ts` | 改首包认证或短期 ticket |
| S-203 | Medium | 上传校验策略不一致 | 文件入口 | `backend/src/api/routes/documents.py`, `backend/src/api/routes/knowledge.py`, `backend/src/api/routes/contracts.py` | 统一复用 `validators.py`，包含大小/MIME/扩展名/文件头 |
| S-204 | Medium | 功能或状态文档与真实实现存在偏差 | 文档治理 | `PROJECT_STATUS.md` | 修复前避免将未落地能力标记为完成 |

## 修复批次建议

### 批次 1：认证与网关边界

- S-001, S-002, S-003, S-004, S-005, S-007

### 批次 2：协作/实时通道

- S-008, S-009, S-010, S-105, S-202

### 批次 3：多租户与资源归属

- S-101, S-102, S-103, S-104, S-107, S-108, S-109, S-110, S-111

### 批次 4：外联与控制面

- S-006, S-011, S-012, S-112, S-113, S-114

## 备注

- 当前矩阵基于静态审计结果
- 修复时建议每一批次都补对应回归测试与越权测试
