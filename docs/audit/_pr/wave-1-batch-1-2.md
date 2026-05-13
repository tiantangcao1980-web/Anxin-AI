# PR：V2 守卫层加固 + LLM 组织隔离 + 认证入口加固（波次 1 第一+第二批）

> 来自审计计划：[docs/audit/plan.md](../PLAN.md) 波次 1
> 任务：TASK-01（认证入口部分收口）+ TASK-02（V2 路由真分离 + 三态运行）+ TASK-04（A2UI/WS 鉴权）+ TASK-09 P0-1/P0-2（尽调守卫 + 匿名聊天 token 拆分）+ S6（LLM 隔离）
> 类型：安全加固 + Bug 修复，**不引入新功能、不改商业化代码、不动 prompts/webhook/密钥**

---

## 摘要

收口 PROJECT_STATUS Phase 1-5 中实质未完工的 V2 守卫缺口：

1. `/pro` 路由无 provider 守卫 → 加 `requirePrimaryClient`
2. ProLayout 12 个导航路径指向根路径而非 `/pro/*` → 全部迁移
3. `/pro` index 重定向 BUG（指向 `/lawyer-dashboard` 根路径）→ 修为 `/pro/dashboard`
4. ModeGate `setMode(HYBRID)` 一键绕过订阅 → 改为引导跳设置页
5. PrivacyContext fail-open（`?? true`/catch setMode/非 2xx 放行）→ 三处全改 fail-closed
6. PrivacyContext 默认端口 `8003` 与项目其他位置 `8001` 不一致 → 统一
7. LLM 配置组织隔离 falsy bug（`if org_id:` 在 None 时跳过过滤）→ 加 `require_org_filter=True` 默认 fail-closed
8. 尽调路由无模式/订阅守卫 → 新建 `mode_deps.py` 提供 `require_mode + require_subscription_feature`，10 个写入路由全部加守卫
9. 匿名聊天室创建接口一次返回双边 token → 拆分为用户创建、律师认领、各自重取 token
10. Chat WebSocket / A2UI action 缺少用户上下文 → 增加首包 token 鉴权与 `ctx.user_id` 传递
11. A2UI 协议缺少版本与未知组件降级 → 增加 `protocolVersion` 与前端占位渲染
12. 聊天超长输入会进入完整 AI 链路 → `ChatMessage.content` 增加 10,000 字符边界
13. reset-password / resend-verification 未强制 CAPTCHA → 后端入口 + 前端提交补齐 CAPTCHA token
14. reset token 虽为高熵但未绑定请求上下文 → 增加 IP/UA hash 绑定与单次消费回归
15. 认证敏感限流 Redis 故障会降级为内存限流 → staging/production 与 `AUTH_REDIS_FAIL_CLOSED=true` 下返回 503 + `Retry-After`
16. refresh token blacklist fail-closed 缺少回归 → 补 Redis 故障拒绝换新 token 测试
17. Web auth token 仍长期写 localStorage → 改为 access token 内存态、refresh cookie/legacy 一次性迁移、启动 silent refresh
18. reset token 仍为进程内 dict → 新增 `password_reset_tokens` DB 表 + Alembic 迁移，仅持久化 SHA-256 hash

---

## 改动清单

### 后端

```
backend/src/core/mode_deps.py                  新建（115 行）
backend/src/api/routes/llm.py                  修改 19+ 7-
backend/src/services/llm_service.py            修改 26+ 5-
backend/src/api/routes/due_diligence.py        修改 31+ 11-（10 个写入路由加双守卫）
backend/src/api/routes/anonymous_chat.py       双 token 拆分 + 参与方校验
backend/src/api/routes/chat.py                 WS 首包鉴权 + 聊天内容长度上限
backend/src/api/routes/chat_handlers/*.py      A2UI handler 注入 user_id
backend/src/services/a2ui_protocol.py          协议版本字段
backend/tests/test_llm_org_isolation.py        新建（5 个测试）
backend/tests/test_mode_subscription_guards.py 新建（8 个测试）
backend/tests/test_anonymous_chat_token_split.py 新建（8 个测试）
backend/tests/test_a2ui_handler_auth.py        新建（6 个测试）
backend/tests/test_a2ui_protocol_version.py    新建（5 个测试）
```

### 前端

```
frontend/src/components/auth/ProtectedRoute.tsx 加 requirePrimaryClient（+role 推断）
frontend/src/App.tsx                            /pro 加守卫 + index 重定向修复
frontend/src/components/pro/ProLayout.tsx       12 path 迁到 /pro/*
frontend/src/components/mode/ModeGate.tsx       移除 setMode(HYBRID)，改 navigate
frontend/src/context/PrivacyContext.tsx         fail-closed + 端口 8001
frontend/src/components/a2ui/A2UIRenderer.tsx   未知组件降级展示
frontend/e2e/role-access.spec.ts                +4 个 V2 e2e case
frontend/e2e/helpers/session.ts                 seedAuthState 加 primary_client
```

### 文档

```
docs/audit/plan.md 等 22 份审计文档（计划+SOP+任务提示词+提案+PR 模板）
```

---

## 测试证据

### 后端 pytest

```
$ ./.venv/bin/pytest -q
348 passed, 1 skipped, 4 warnings in 43.39s
```

本次验证还单独跑过目标测试：

```bash
$ ./.venv/bin/pytest -q \
  tests/test_llm_org_isolation.py \
  tests/test_mode_subscription_guards.py \
  tests/test_a2ui_handler_auth.py \
  tests/test_a2ui_protocol_version.py \
  tests/test_anonymous_chat_token_split.py
32 passed in 3.01s
```

新增测试矩阵：

| 测试 | 验证内容 | 状态 |
|---|---|---|
| test_normal_user_without_org_sees_nothing | 无 org 用户 fail-closed | ✅ |
| test_org_user_only_sees_own_org | org 隔离生效 | ✅ |
| test_superuser_can_see_all | 超管放行 | ✅ |
| test_unknown_org_id_does_not_leak | 边界：未匹配 UUID 不泄露 | ✅ |
| test_default_require_org_filter_is_true | 默认 fail-closed | ✅ |
| test_require_mode_superuser_bypasses | 超管放行 | ✅ |
| test_require_mode_free_user_no_header_falls_back_to_local | 老客户端无头降级 | ✅ |
| test_require_mode_pro_user_with_hybrid_header_passes | 付费 hybrid 通过 | ✅ |
| test_require_mode_pro_user_with_local_header_blocked | 付费但选 local 拦截 | ✅ |
| test_require_mode_invalid_header_falls_back | 非法头按缺失处理 | ✅ |
| test_require_subscription_feature_superuser_bypasses | 超管放行 | ✅ |
| test_require_subscription_feature_free_user_blocked | 免费拒绝 | ✅ |
| test_require_subscription_feature_pro_user_passes | 付费通过 | ✅ |
| test_create_room_response_excludes_lawyer_token | 匿名聊天室不再返回对方 token | ✅ |
| test_lawyer_join_requires_matched_lawyer | 律师认领必须匹配 matched_lawyer | ✅ |
| test_a2ui_handler_rejects_when_user_id_missing | A2UI action 缺 user_id 拒绝 | ✅ |
| test_a2ui_message_includes_protocol_version | A2UI 消息携带协议版本 | ✅ |
| test_chat_message_too_long | 超长聊天消息边界拒绝 | ✅ |
| test_reset_password_requires_captcha_when_enabled | 重置密码提交必须 CAPTCHA | ✅ |
| test_resend_verification_requires_captcha_when_enabled | 重发验证必须 CAPTCHA | ✅ |
| test_password_reset_token_is_high_entropy_single_use_and_context_bound | 高熵 reset token 单次 + IP/UA 绑定 | ✅ |
| test_auth_rate_limit_fails_closed_when_redis_down | 登录限流 Redis 故障返回 503 | ✅ |
| test_forgot_password_rate_limit_fails_closed_when_redis_down | 忘记密码限流 Redis 故障返回 503 | ✅ |
| test_refresh_token_blacklist_fails_closed_when_redis_down | refresh blacklist Redis 故障拒绝换新 token | ✅ |

### 前端

```
$ npm run lint       # exit 0
$ npm run build      # tsc && vite build, built in 12.90s
```

新增 e2e：

```bash
$ npx playwright test e2e/role-access.spec.ts
10 passed, 10 skipped in 8.5s
```

说明：第一次运行时复用了端口 3001 上的旧 Vite 进程，导致运行时代码仍是旧路由并失败；关闭旧进程后由 Playwright 启动新 dev server，测试通过。

| e2e | 验证内容 |
|---|---|
| V2: 需求方端用户访问 /pro/* 会被引导回 /chat | requirePrimaryClient 守卫 |
| V2: 服务方端律师访问 /pro/dashboard 应正常进入 | provider 通行 |
| V2: /pro 根路径重定向到 /pro/dashboard | index BUG 修复 |
| V2: 老用户字段为空时按 role 推断 | 兼容性 |


```text
changed_files: 62
changed_symbols: 493
affected_processes: 50
risk_level: critical
```

受影响流程集中在登录/注册/重置密码、TokenStorage/App 启动恢复、路由守卫、IM/协作/admin token 消费、A2UI handler 相关调用链；已由 auth/A2UI 目标测试、前端 Vitest、lint/build 与角色访问 E2E 覆盖核心行为。

---

## 实质就绪度变化

参见 [01-prd-reality-gap.md](../00-platform/01-prd-reality-gap.md)：

| 维度 | 修复前 | 修复后 |
|---|---|---|
| V2 双客户端分离 | 60% | **85%** |
| V2 三态运行 + 订阅 | 50% | **75%** |
| LLM 多租户隔离 | "已修复"实漏 | **✅ 加固完成** |
| 尽调路由守卫 | 0% | **80%**（前端透传留 P1） |
| 匿名聊天室身份边界 | 双 token 泄露 | **✅ token 拆分 + 参与方校验** |
| A2UI/WS action 边界 | 无用户上下文 | **✅ 首包鉴权 + user_id 透传** |

---

## 风险评估

| 风险 | 等级 | 缓解 |
|---|---|---|
| 现有 `/lawyer-dashboard` 等根路径外链失效 | 🟡 中 | 用户已收藏的旧 URL（极少）会跳到 /chat 而非 /pro/dashboard。建议在前端加 redirect map（followup） |
| 老客户端不传 X-Privacy-Mode 头 | 🟢 低 | 已设计 fail-safe：按订阅 allowed_modes[0] 推断，免费用户落到 local 触发 403 |
| 老用户 primary_client 字段为空 | 🟢 低 | ProtectedRoute 按 role 推断（lawyer/partner/paralegal/platform_lawyer → provider） |
| LLM list_configs 接口调用方未传 require_org_filter | 🟢 低 | 默认 True（fail-closed），调用方需显式传 False 才能查全部 |

---

## 不在本 PR 内的 P0（待后续 PR）

- TASK-01 剩余：session/CAPTCHA Redis 状态 fail-closed 审计、移动端/桌面端 token 策略复核、reset token 过期记录清理任务；本轮已完成 Web token localStorage 清零、refresh body 兼容默认关闭、持久 reset token hash 表、高熵 reset token、reset/resend CAPTCHA、认证限流 Redis fail-closed 与 refresh blacklist fail-closed 回归
- TASK-10：支付/电签 webhook 官方协议 + 真实渠道沙箱 + 订阅状态机（基础持久化幂等、Admin 查询/手动重试、Prometheus 指标与自动重试/backoff 已落）
- 任务 0：密钥治理 SOP 执行（用户操作）
- 移动端/桌面端模式选择与订阅语义复核；Web 端 `X-Privacy-Mode` 透传已由 `buildApiHeaders` + PrivacyContext 快照完成

---

## 建议合并策略

1. 自动 CI（如已开 gitleaks）应自动拦截带 secret 的 commit
2. 合并后建议跑一次 e2e（playwright role-access.spec.ts）确认守卫真生效
3. 部署前确认 `/lawyer-dashboard` 无外链依赖（如有，加 301 重定向到 `/pro/dashboard`）

---

## Co-Authored-By

```
Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```
