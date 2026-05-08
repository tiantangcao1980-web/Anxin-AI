# 任务 0 产出物 1 — PRD 承诺 vs 代码现实差分

> 来源：本人对 18 处代码点位的逐一实测核查
> 对照基线：`PROJECT_STATUS.md`（2026-04-16 V2 升级章节 + 2026-04-03 安全审计章节）+ `PRODUCT_ROADMAP.md` + `README.md`
> 目的：把"标完成"和"实际可用"之间的偏差变成可执行的修复任务清单
> 注意：本文档不指控 PROJECT_STATUS 撒谎，PROJECT_STATUS 在第 70-188 行已经诚实列出了 P0 钉子。本文档是补充"Phase 1-5 完成度"和"V2 商业化就绪"之间的隐藏缺口

---

## 1. V2 三大变革的实质就绪度

### 1.1 双客户端分离（C 端需求方 / B 端服务方）

| PROJECT_STATUS 写的 | 代码现实 | 修复后 | 差分严重度 |
|---|---|---|---|
| Phase 1：「前端路由拆分 `/pro/*` 服务方端 + `/pro/login` 独立入口」 | `/pro` 路由仅用 `<ProtectedRoute>` 包裹，未做 provider/role 检查 | ✅ 2026-05-04 已修：`requirePrimaryClient="provider"` + 老用户字段为空时按 role 推断（4 个 e2e 验证） | ~~🔴 P0~~ → ✅ |
| Phase 2：「ProLayout 服务方端独立布局」 | 所有侧边栏 `to` 字段指向根路径而非 `/pro/*` 子路径 | ✅ 2026-05-04 已修：12 个导航 path 全部加 `/pro/` 前缀 + isActive 判定对齐 + index 重定向 BUG（指向根路径）修复 | ~~🔴 P0~~ → ✅ |
| 关键决策：「同一 users 表，通过 `primary_client` 字段区分默认客户端」 | User 表已有字段，但前端无"按 primary_client 强制引导"的逻辑 | ⏳ 部分：ProtectedRoute 已支持守卫；登录后强制引导仍待补 | 🟠 P1 |

**实质就绪度评估**：60% → **85%**。守卫层 + 路由层完成，登录后强制引导是剩余 15%。

**修在哪**：任务 2 已落 80%，剩余"登录后引导"留 P1

---

### 1.2 三态运行模式（本地/混合/云端）

| PROJECT_STATUS 写的 | 代码现实 | 修复后 | 差分严重度 |
|---|---|---|---|
| Phase 1：「ModeGate 组件（4 种门控策略）」 | DefaultFallback 的"切换运行模式"按钮直接 `setMode(PrivacyMode.HYBRID)`，**无订阅检查** | ✅ 2026-05-04 已修：删除一键 setMode，改为 `navigate('/settings?tab=privacy')` 引导走 `requestModeSwitch` | ~~🔴 P0~~ → ✅ |
| Phase 3：「PrivacyContext 模式切换与订阅联动」 | `?? true` 默认放行；catch 块 `setMode` 在 API 失败时直接切换；非 2xx 也放行 | ✅ 2026-05-04 已修 fail-closed：`?? false`、catch 不再 setMode、非 2xx 拒绝 | ~~🔴 P0~~ → ✅ |
| Phase 3：默认 API 端点 | 默认 `http://localhost:8003/api/v1`，项目其他位置用 `8001` | ✅ 2026-05-04 已修：统一 `8001` | ~~🟡 P2~~ → ✅ |
| TASK-09 P0-1：尽调路由无 mode/订阅守卫 | due_diligence.py 仅 `Depends(get_current_user_required)` | ✅ 2026-05-04 已修：新建 `mode_deps.py` 提供 `require_mode + require_subscription_feature`，10 个写入路由全部加守卫，8 个测试覆盖 | ~~🔴 P0~~ → ✅ |
| 后端 mode 透传 | 修复前请求未把前端 mode 透传到后端 | ✅ 2026-05-06 已修：`buildApiHeaders` 统一注入 `X-Privacy-Mode`，PrivacyContext mode 变更同步 API 快照，流式/上传/后台/支付/电签/模板/画布直连 fetch 已接入 | ~~🟠 P1~~ → ✅ |

**实质就绪度评估**：50% → **90%**。前端绕过点、后端尽调守卫、订阅判定 fail-closed、前端请求头透传均已收口；剩余 10% 是移动端/桌面端模式选择与订阅语义的跨端复核。

**修在哪**：任务 2 + 任务 9 P0-1 已落；Web API header 透传已由 `frontend/src/lib/api.ts` / `PrivacyContext.tsx` / 直连 fetch 接入完成。

---

### 1.3 订阅商业化

| PROJECT_STATUS 写的 | 代码现实 | 差分严重度 |
|---|---|---|
| Phase 5：「V2 订阅购买 API（/billing/v2/subscribe，连接支付系统，年付 8 折）」 | API 路由存在。`WeChatPayProvider` 已补 Native 下单/查单/关单/退款请求与同步响应验签，`AlipayProvider` 已补 page.pay/query/refund/close 签名请求与同步响应验签；仍未用真实沙箱凭据跑通支付平台闭环 | 🔴 P0 |
| 已开始落地 Batch 5：「微信支付 / 支付宝 / 电签 webhook 增加基础签名校验」 | 支付通用 HMAC webhook 已接 `payment_webhook_service.py`，电签通用 HMAC webhook 已接 `esign_webhook_service.py`；可分别回写订单/订阅与合同签署状态。微信支付 v3 / 支付宝 RSA2 回调验签、e签宝 provider/官方 HMAC 回调、法大大 FASC provider/webhook 代码级协议已落；仍缺真实商户沙箱、账号事件映射与灰度证据 | 🔴 P0 |
| Batch 7：「支付 / 电签 webhook 升级为时间戳 + HMAC 校验，并增加简单防重放缓存」 | 校验机制、通用业务回写、`webhook_received` 持久化幂等、Admin `/admin/webhooks` 查询/手动重试、Prometheus 指标、电签 flow 映射、失败自动重试/backoff、微信支付 v3/支付宝 RSA2 回调验签、e签宝官方 HMAC 回调验签、微信/支付宝官方请求与同步响应验签代码已有最小闭环；仍缺真实沙箱闭环 | 🔴 P0 |
| 关键决策：「订阅与客户端独立计费，兼职律师可同时订阅 Pro + Lawyer Pro」 | ✅ 2026-05-06 已修：服务层原生写入 `client_type`，校验套餐适用端，同一用户需求方/服务方订阅可并存且支付/退款事件隔离；前端 `MySubscription` 已按需求方/服务方双栏展示，`Pricing` 已按当前端侧过滤可购买套餐 | ✅ |

**实质：订阅商业化在订单创建侧（DB + 模型 + API 路由）就绪，支付/电签通用 webhook 回写已能推进本地订单/订阅/合同状态，持久化幂等、Admin 查询/手动重试、Prometheus 指标、失败自动重试/backoff、微信/支付宝官方回调验签、e签宝/法大大电签代码级官方协议、官方请求与同步响应验签、订阅状态机、双客户端订阅隔离、前端展示与套餐过滤、IM 离线 ACK 前后端协议均已落地；但微信/支付宝/电签真实沙箱回归、证书/公钥/事件轮换验证、账号事件映射和灰度证据未完工。当前仍不能宣称真实付费或真实电签全链路可商用。**

**修在哪**：任务 5（电签）+ 任务 10（支付 + 订阅）

---

## 2. 2026-04-03 安全审计的 10 个钉子

PROJECT_STATUS 第 71-86 行 + 162-168 行明确列出。本节是对每个钉子的代码现实核查 + 严重度复评。

| # | 钉子 | 当前代码 | 实质严重度 | 修在哪 |
|---|---|---|---|---|
| S1 | 仓库中存在已提交的真实密钥 | `.env` 已被 Git 跟踪。轮换前必须先列影响面（涉及哪些第三方 API key、token、DB 凭据） | 🔴 P0（阻塞） | 任务 0 SOP |
| S2 | 邮箱验证码/密码重置码仍为 6 位数字，重置链路未绑定额外上下文 | ✅ **2026-05-06 已修复**：密码重置 token 已改高熵、单次消费、15min 过期、IP/UA hash + email/channel 绑定；`_reset_tokens` 已迁移到 `password_reset_tokens` DB 表且只存 SHA-256 hash | ✅ | 任务 1 |
| S3 | 前端 access/refresh token 持久化到 `localStorage` | ✅/⏳ **2026-05-06 Web 已修复**：`frontend/src` 已清零 auth token localStorage 读写；浏览器 access token 仅内存，refresh token 走 HttpOnly cookie；后端 refresh body 兼容默认关闭，仅 `AUTH_REFRESH_BODY_COMPAT_ENABLED=true` 临时开启。剩余：移动端/桌面端 token 策略复核 | 🟠 P1（剩跨端） | 任务 1 |
| S4 | Redis 故障下认证 fail-closed 不严格 | ✅/⏳ **2026-05-06 部分修复**：认证敏感 rate-limit 在 staging/production 或 `AUTH_REDIS_FAIL_CLOSED=true` 下返回 503 + `Retry-After`；refresh blacklist fail-closed 已补回归；剩余 CAPTCHA/session-table Redis 状态待审 | 🟠 P1 | 任务 1 |
| S5 | 支付/电签 webhook 仍未切到各渠道官方签名协议 | 通用 HMAC、微信支付 v3 SHA256-RSA、支付宝 RSA2、e签宝 provider/回调 HMAC、法大大 FASC provider/webhook 代码级协议已上；仍缺真实沙箱、账号事件映射与灰度证据 | 🔴 P0 | 任务 5 + 任务 10 |
| S6 | LLM 配置接口缺少组织隔离 | ✅ **2026-05-04 已修复**：服务层加 `require_org_filter=True` 默认 fail-closed；`if org_id:` → `if org_id is not None:`；路由层超管/普通用户分流。5 测试覆盖 | ~~🔴 P0~~ → ✅ | ~~任务 2~~ |
| S7 | 匿名聊天创建接口公开，单次返回双方 token | ✅ **2026-05-05 已修复**：拆分为 POST /rooms（要登录 + consultation 所有者）+ POST /rooms/{id}/lawyer-join（matched_lawyer 校验）+ GET /rooms/{id}/my-token；响应模型移除 lawyer_token 字段。8 测试覆盖 | ~~🔴 P0~~ → ✅ | ~~任务 9~~ |
| S8 | IM 原 URL token 使用场景 | ✅ **2026-05-06 已修复**：`useIMWebSocket` 建连 URL 不再携带 token；后端 `/im/ws` 改为 10s 内必须发送 `auth` 首包，成功后返回 `auth_ok`；IM 离线增量和 ACK 前后端协议已补，新增后端 WebSocket/离线 ACK 回归与前端 hook 单测 | ~~🔴 P0~~ → ✅ | 任务 10 |
| S9 | 上传入口校验未统一到共享校验器 | ✅ **2026-05-06 已修复**：新增 `read_validated_upload_file` 路由层共享 helper，统一调用 `FileValidator.validate_file`；`documents.py`、`knowledge.py` 单/批量上传、`contracts.py` 解析/流式审查/上传审查入口均接入扩展名、MIME、大小和 magic number 校验；8 个 API 回归覆盖非法扩展、非法 MIME、超限和伪造 PDF，相关文档/授权/对象存储回归 `28 passed` | ✅ | 任务 6 |
| S10 | CAPTCHA 仅覆盖登录/注册/忘记密码，重发验证码和重置密码未覆盖 | ✅/⏳ **2026-05-06 部分修复**：重发邮箱验证码、重置密码提交已强制 CAPTCHA 并有前后端回归；短信验证码 resend API 仍需确认 | 🟠 P1 | 任务 1 |

**实质 P0 钉子从"7 个" → 实际 8 个（S6 在文档里标记进行中、但服务层修复不完整，等于退化漏洞）。**

---

## 3. 桌面端 / 移动端 / 多端同步的 PRD vs 现实

### 3.1 桌面端

PRODUCT_ROADMAP.md 第 86-95 行列出"已完成能力"，第 97-106 行列出"待实现 MVP 任务"。差分：

| ROADMAP 写的 | 代码现实 | 严重度 |
|---|---|---|
| ✅「离线任务队列 + 同步引擎」 | 旧 Rust IPC 假成功已清除：`sync.rs` 现在返回 unsupported/fail-closed 并报告本地待同步/冲突统计；`sync_engine.rs` 未启用 push/pull 时返回 Error，不再 `Ok(0)`。但真实云端 push/pull、跨设备延续、移动远控和 signed packaged runtime 证据仍未完成 | 🟠 **假成功已修，商业同步闭环仍未完成** |
| ✅「全局快捷键 Cmd+Shift+Space」 | 注册存在。但快捷键呼出后**没有"快速问答"模式**（即 P0-2 任务）—— 当前呼出后跳到主界面 | 🟠 P0-2 待开发 |
| [ ] P0-1：Tauri 窗口外观优化 | 未实现 | 🟠 P0 待开发 |
| [ ] P0-2：全局快捷键呼出后的"快速问答"模式 | 未实现 | 🟠 P0 待开发 |
| [ ] P0-3：文件拖拽到系统托盘 → 自动分析 | 未实现 | 🟠 P0 待开发 |

**实质：ROADMAP 把"已注册全局快捷键"当作 P0-2 完成，但完整 P0-2 需要"呼出 → 简化输入框 → 流式回答 → 完成即隐藏"的端到端体验。同步引擎更是把"框架已搭"当作"已完成"。**

**修在哪**：任务 11a（窗口/快捷键/拖拽）+ 任务 11b（同步引擎，从零写）

### 3.2 移动端

ROADMAP 第 109-127 行：

| ROADMAP 写的 | 代码现实 | 严重度 |
|---|---|---|
| ✅「`tauri.conf.json` 支持移动端深度链接」 | 配置存在 | — |
| [ ] 移动端专用布局 | ✅ 2026-05-06 已修 `approvals/[id].tsx` 静默 fallback：详情页改为 loading/error/empty 三态，按登录过期/无权限/不存在/网络错误展示明确文案；`cases.tsx` 已是错误三态且无假案件；首页任务/审批/通知不再用假数据兜底，聊天欢迎语移出消息历史，设置页移除误导性 mock 标记。剩余：底部 Tab/safe-area/44pt 触控、跨设备会话延续与真机手测仍未闭环 | 🟠 P1 |
| 当前 ROADMAP 把移动端整体标为 M3（M2 + 8 周）后启动 | 当前 mobile/ 目录已有部分代码但 Beta 未启动 | — |

### 3.3 小程序（mini-program）

未在 PRODUCT_ROADMAP.md 三端图（Web/Desktop/Mobile）中显式提及，但目录存在。

| 现状 | 严重度 |
|---|---|
| [profile/index.tsx](../../mini-program/src/pages/profile/index.tsx) 微信登录失败时写入 `mock_token_${Date.now()}` 并提示"体验模式"→ 生产环境会让用户误以为已登录 | ✅ 2026-05-06 已修：小程序端完全移除 mock token / 体验模式降级，登录改走 `wx.login` → `/api/v1/auth/wechat/code2session` → 后端真实 JWT；失败只展示明确错误，不写入本地 token |
| [index/index.tsx](../../mini-program/src/pages/index/index.tsx) 资讯接口失败/为空时使用 `fallbackNews` 假数据，无降级标识 | ✅ 2026-05-06 已修：小程序主页移除假新闻 fallback，接口为空或失败时展示明确空状态“暂无资讯 / 下拉刷新重试”，并保留 `console.warn` telemetry |

**修在哪**：任务 11c（移动端 + 小程序的 fallback 治理）

---

## 4. 测试统计的小偏差（无需大动）

| 文档说的 | 实测 | 备注 |
|---|---|---|
| PROJECT_STATUS：「后端全量回归 → `172 passed`」 | Codex 实测默认回归 `430 passed, 1 skipped, 10 warnings in 46.41s` | 文档落后于现实。修：完成 Day 21 汇总时同步更新 PROJECT_STATUS；`test_comprehensive_flow` 为 opt-in smoke |
| PROJECT_STATUS：「前端多角色访问控制 E2E：6/6」 | Codex 实测 `10 passed / 10 skipped` | 仍有 10 个 skipped，需要在任务 1/2/10 继续复活 |
| PROJECT_STATUS：「前端核心业务动作 E2E：8/8」 | 未在本次复测中复测 | 任务 5/6/8 各自需补充 |

---

## 5. 静态质量统计

| 项 | 当前数字 | 处置 |
|---|---|---|
| `ruff check src tests` | 历史快照 7873 errors；当前全仓 Ruff 已清零 | 保持零回退，任何新增 Ruff 错误均阻断 release readiness |
| `mypy src` | 历史快照 2002 errors；当前 backend mypy 已清零 | `scripts/mypy-baseline-check.sh` 默认 ceiling 为 `0`，任何非零 mypy 均阻断 release readiness |
| 前端 build 警告 | lottie-web `eval` + 大 chunk + 动态/静态导入混用 | P2 任务 11c 顺路处理 |

---

## 6. 与 PROJECT_STATUS 的对账提案

本次审计完成后，建议在 PROJECT_STATUS.md 加入一节：

```markdown
## 2026-05-XX V2 实质就绪度复盘（Claude Code 审计）

本节由独立审计补充，对 Phase 1-5 完成度做"实质就绪度"复评：

| Phase | 文档完成度 | 实质就绪度 | 关键差分 |
|---|---|---|---|
| Phase 1 双客户端 | 100% | 60% | /pro 守卫缺失、ProLayout 导航未迁移 |
| Phase 2 服务方布局 | 100% | 70% | 同上 |
| Phase 3 三态订阅 | 100% | 50% | ModeGate 一键绕过、PrivacyContext 失败放行 |
| Phase 4 案源市场 | 100% | 80% | 利益冲突已实现，撮合公平性待验证 |
| Phase 5 订阅购买 + 支付 | 100% | 75% | 支付渠道请求代码、同步响应验签、webhook 回写与 e签宝/法大大电签代码级官方协议已落；真实沙箱、证书/公钥/事件轮换、账号事件映射和灰度证据未闭环 |

参见 docs/audit/00-platform/01-prd-reality-gap.md 详细差分
```

待用户审阅后，由用户在合适时机回写到 PROJECT_STATUS。

---

## 7. 本文档的"再校验责任"

每次完成一个波次任务后，**必须重读本文档并更新对应行**：

- 任务 1 完成 → 更新表 2 中 S2/S3/S4/S10
- 任务 2 完成 → 更新表 1.1/1.2/2 中 S6
- 任务 5 完成 → 更新表 1.3/2 中 S5（电签部分）
- 任务 9 完成 → 更新表 2 中 S7
- 任务 10 完成 → 更新表 1.3/2 中 S5（支付部分）+ S8
- 任务 11b 完成 → 更新表 3.1
- 任务 6 完成 → 更新表 2 中 S9 + 附录中文档对象存储/模板渲染安全边界

每行"严重度"一旦从 🔴 降级到 ✅，必须在 PR 描述里贴上对应的失败测试 → 通过测试的截图。

---

> 文档作者：Claude Code
> 实测时间：2026-05-04
> 后续修订：每完成一个任务波次同步更新
