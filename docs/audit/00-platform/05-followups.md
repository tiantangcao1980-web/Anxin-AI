# 任务 0 产出物 5 — Followups（沉淀到 hierarchical-memory）

> 目的：把任务 0 产出的不在本次审计范围内、但需要长期跟进的事项沉淀为 memory 条目
> 触发：每个任务完成后，由执行者 `python3 ~/.claude/skills/hierarchical-memory/scripts/memory-cli.py add-bugfix/add-feature` 写入

---

## 1. 待沉淀为 bugfix（修复型经验）

### F1 — V2 守卫层缺失类问题的识别模式

**症状**：路由 + UI shell 已建立，但守卫层（feature flag / role check / subscription check）缺失或绕过

**关键词**：`/pro 守卫缺失` / `ModeGate 绕过` / `setMode 直接调用`

**修复模式**：
- 守卫必须分两层：路由层（ProtectedRoute feature 参数）+ UI 层（ModeGate / SubscriptionGate）
- "切换模式"按钮永远走 `requestModeSwitch`，不允许直接 `setMode`
- API 兜底必须 fail-closed（默认拒绝），不允许 `?? true` 默认放行

**相关文件**：
- frontend/src/App.tsx
- frontend/src/components/mode/ModeGate.tsx
- frontend/src/context/PrivacyContext.tsx
- frontend/src/components/pro/ProLayout.tsx

**沉淀命令**（任务 2 完成后执行）：
```bash
python3 ~/.claude/skills/hierarchical-memory/scripts/memory-cli.py add-bugfix \
  --symptom "V2 守卫层缺失：路由壳建立但订阅/角色守卫绕过" \
  --root-cause "Phase 1-5 完成度评估混淆了'路由配置完成'和'守卫层接通'" \
  --fix "守卫两层（路由 + UI）+ 切换走 requestModeSwitch + API fail-closed" \
  --files "frontend/src/App.tsx,frontend/src/components/mode/ModeGate.tsx,frontend/src/context/PrivacyContext.tsx" \
  --tags "v2,guard,subscription,frontend"
```

---

### F2 — 服务层 `if x:` 与 `if x is not None:` 的隐蔽 bug

**症状**：路由层加了组织隔离 `org_id = getattr(user, 'org_id', None)`，但服务层 `if org_id:` 在 None 时跳过过滤，等于无过滤查询

**关键词**：`Falsy bug` / `if value: 漏掉 None` / `LLM 配置组织隔离`

**修复模式**：
- 任何"如果传了过滤参数就过滤、否则不过滤"的服务方法，过滤判断必须用 `is not None`
- 更安全的设计：服务方法不接受"可选过滤"，由调用方决定是否传，传了就必须有值
- 对 RBAC 类隔离：超级管理员走专门的 `list_all_*` 方法，普通用户走 `list_by_org`，禁止"一个方法两种行为"

**相关文件**：
- backend/src/services/llm_service.py:288
- backend/src/api/routes/llm.py:177

**沉淀命令**（任务 2 完成后执行）：
```bash
python3 ~/.claude/skills/hierarchical-memory/scripts/memory-cli.py add-bugfix \
  --symptom "S-104 修复后普通无 org 用户仍能查到所有租户配置" \
  --root-cause "服务层 if org_id 在 None 时短路，等价于无过滤" \
  --fix "改 is not None；或拆分 list_all_* / list_by_org" \
  --files "backend/src/services/llm_service.py,backend/src/api/routes/llm.py" \
  --tags "rbac,multi-tenant,falsy-bug"
```

---

### F3 — 密钥治理 SOP（5 步原子化流程）

**症状**：`.env` 已 push 到 GitHub，需要轮换 + 历史清理

**关键词**：`secret leak` / `git filter-repo` / `git history rotate`

**修复模式**：见 `02-secret-rotation-sop.md` 的 Step 1-5。关键原则：
- 先生成新凭据 + 验证可用，再失效旧凭据
- "旧凭据失效"和"Git 历史清理"必须绑成原子操作
- GitHub fork 单独处理，不能漏

**沉淀命令**（任务 0 完成后执行）：
```bash
python3 ~/.claude/skills/hierarchical-memory/scripts/memory-cli.py add-bugfix \
  --symptom "GitHub 已 push 含真实密钥的 .env" \
  --root-cause ".gitignore 加入 .env 之前已发生 commit + push" \
  --fix "5 步流程：盘点→定级→生成新→失效旧+清历史→验证+加固" \
  --files ".env,.gitignore,docs/audit/00-platform/02-secret-rotation-sop.md" \
  --tags "security,secret,git-history,p0"
```

---

### F4 — Webhook"校验通过 + 业务回写"分离设计

**症状**：webhook 签名校验已加，但业务状态机未推进

**关键词**：`webhook 不更新订单` / `webhook handler 骨架` / `idempotency`

**修复模式**：
- 统一 webhook_handler 服务已落地：验签/解析后的 payload 统一进入 `handle_verified_webhook`，再做幂等查重、业务回写、失败记录和提交边界
- `webhook_received` 表 + idempotency_key 幂等 + Admin `/admin/webhooks` 查询/手动重试 + Prometheus 指标 + 失败自动重试/backoff 已完成；微信支付 v3/支付宝 RSA2 回调验签、e签宝 provider/官方 HMAC 回调、法大大 FASC provider/webhook、稳定 `PaymentWebhookEvent` / `ESignWebhookEvent` 与官方通知 id 幂等已落；后续必须补真实商户沙箱、账号事件映射与灰度证据
- 业务回写失败已可通过后台 worker 按 backoff 重试，生产启用前需接入告警
- 前端 Admin 页面可视化仍需补齐

**相关文件**：
- backend/src/api/routes/payments.py:308
- backend/src/api/routes/esign.py:337
- backend/src/services/webhook_handler.py

**沉淀命令**（任务 5/10 完成后执行）：
```bash
python3 ~/.claude/skills/hierarchical-memory/scripts/memory-cli.py add-bugfix \
  --symptom "支付/电签官方渠道仍缺持久幂等与真实协议闭环" \
  --root-cause "通用 HMAC 回写、webhook_received 幂等、统一 webhook_handler、Admin 查询/手动重试、指标、flow 映射、自动重试 worker、微信/支付宝官方验签、e签宝 provider/回调 HMAC、法大大 FASC provider/webhook 与稳定事件对象已补，但真实商户沙箱、账号事件映射和灰度证据仍未统一" \
  --fix "官方协议适配 + 渠道沙箱闭环" \
  --files "backend/src/api/routes/payments.py,backend/src/api/routes/esign.py,backend/src/services/webhook_events.py,backend/src/services/payment_webhook_service.py,backend/src/services/esign_webhook_service.py,backend/src/services/official_webhook_security.py,backend/src/services/webhook_retry_service.py,backend/src/services/webhook_retry_worker.py,backend/src/services/webhook_handler.py" \
  --tags "webhook,payment,esign,idempotency"
```

---

## 2. 待沉淀为 feature（新功能/最佳实践）

### G1 — 对象存储抽象层（MinIO/S3 双后端）

**功能**：统一文件读写抽象层，业务模块不再直接接 MinIO/S3

**模式**：
- 新建 `backend/src/services/object_storage_service.py`
- 接口：`put / get / delete / presigned_url / move`
- 配置：`STORAGE_BACKEND=minio|s3|local`，env 切换
- DB 字段：`object_key`（替代 `file_path`）+ `storage_backend`

**相关文件**：见 `03-cross-cutting-gaps.md` 缺口 A

**沉淀命令**（任务 6 完成后执行）：
```bash
python3 ~/.claude/skills/hierarchical-memory/scripts/memory-cli.py add-feature \
  --name "Object Storage Abstraction Layer" \
  --pattern "Service-level abstraction with env-switchable backend (minio/s3/local), atomic put/get/delete/presigned_url interface" \
  --files "backend/src/services/object_storage_service.py" \
  --tags "storage,minio,s3,abstraction"
```

---

### G2 — 桌面同步引擎（offline-first）

**功能**：SQLite 本地队列 + push/pull/conflict 三件 + 自动重试

**模式**：见 `03-cross-cutting-gaps.md` 缺口 C

**沉淀命令**（任务 11b 完成后执行）：
```bash
python3 ~/.claude/skills/hierarchical-memory/scripts/memory-cli.py add-feature \
  --name "Desktop Offline-First Sync Engine" \
  --pattern "SQLite offline_tasks queue + push (batch 100) + pull (since_version) + last-writer-wins conflict + exponential backoff retry" \
  --files "desktop/src/services/sync_engine.rs,desktop/src/commands/sync.rs,desktop/migrations/001_offline_queue.sql" \
  --tags "desktop,sync,offline-first,sqlite,tauri"
```

---

### G3 — 三态运行 + 订阅守卫"三层联动"

**功能**：Mode + Subscription + Feature flag 三层守卫的统一接口

**模式**：
- ModeGate：从 PrivacyMode 判断（与订阅独立）
- SubscriptionGate：从 v2/can-access-feature API 判断
- FeatureFlagGate：从 feature_flags 模型判断
- 三者 AND 关系，缺一不可

**沉淀命令**（任务 2 完成后执行）：
```bash
python3 ~/.claude/skills/hierarchical-memory/scripts/memory-cli.py add-feature \
  --name "Three-Layer Guard (Mode + Subscription + Feature)" \
  --pattern "ModeGate + SubscriptionGate + FeatureFlagGate AND-composed; failure mode is fail-closed not fail-open" \
  --files "frontend/src/components/mode/ModeGate.tsx,backend/src/middleware/subscription.py" \
  --tags "v2,guard,subscription,feature-flag"
```

---

## 3. 待沉淀为 reference（外部参考）

### R1 — git-filter-repo 官方文档

```bash
python3 ~/.claude/skills/hierarchical-memory/scripts/memory-cli.py add-reference \
  --name "git-filter-repo: history rewrite tool" \
  --url "https://github.com/newren/git-filter-repo" \
  --note "比 BFG 更新更安全。用于 secret 历史清理。安装: brew install git-filter-repo" \
  --tags "git,security,tool"
```

### R2 — gitleaks 自定义规则文档

```bash
python3 ~/.claude/skills/hierarchical-memory/scripts/memory-cli.py add-reference \
  --name "gitleaks 自定义规则" \
  --url "https://github.com/gitleaks/gitleaks#configuration" \
  --note "TOML 格式，支持 [[rules]] + [allowlist]。本项目放在 .gitleaks.toml" \
  --tags "security,gitleaks,ci"
```

### R3 — GitHub Secret Removal Policy

```bash
python3 ~/.claude/skills/hierarchical-memory/scripts/memory-cli.py add-reference \
  --name "GitHub: 私密信息删除政策" \
  --url "https://docs.github.com/en/site-policy/content-removal-policies/github-private-information-removal-policy" \
  --note "用于联系 GitHub Support 删除已被 fork 的 commit cache" \
  --tags "github,security,leak-response"
```

---

## 4. 待沉淀为 project（项目元信息）

### P1 — 当前 V2 实质就绪度评级

```bash
python3 ~/.claude/skills/hierarchical-memory/scripts/memory-cli.py add-project \
  --name "Anxin V2 真实就绪度（2026-05-04）" \
  --content "PROJECT_STATUS 标 Phase 1-5 完成。但实测：双客户端 60%、三态订阅 50%、合约支付链路 30%。详见 docs/audit/00-platform/01-prd-reality-gap.md" \
  --tags "v2,readiness,audit,2026-05"
```

### P2 — 18 处已核查代码点位（事实清单快照）

```bash
python3 ~/.claude/skills/hierarchical-memory/scripts/memory-cli.py add-project \
  --name "Anxin 18 处审计核查点位" \
  --content "见 docs/audit/PLAN.md 附录 A。每个点位带文件路径 + 行号 + 现状描述 + 修复任务归属" \
  --tags "audit,checklist,2026-05"
```

---

## 5. 待 cross-search 的关键词（未来开发触发）

下次开发以下功能/遇到以下症状时，先执行：

```bash
python3 ~/.claude/skills/hierarchical-memory/scripts/memory-cli.py cross-search "<关键词>"
```

**触发关键词**：
- 密钥泄露 / secret leak / git history secret
- V2 守卫 / pro guard / subscription gate / mode gate bypass
- LLM 多租户 / multi-tenant / org_id falsy
- Webhook / payment webhook / esign webhook / idempotency
- 桌面同步 / offline sync / SQLite queue / desktop tauri sync
- 对象存储 / MinIO / S3 / file storage abstraction
- 模式切换 / privacy mode / hybrid cloud local
- 匿名聊天 / anonymous chat / consultation token
- IM URL token / WebSocket auth / first-frame auth
- localStorage token / refresh token storage / httpOnly cookie

---

## 6. 不沉淀的事

按 hierarchical-memory 规则，**不**沉淀：
- 具体代码片段（PR diff / commit hash / 行号）—— 这些 git history 自带
- 项目结构 / 文件路径约定 —— 看代码即知
- 临时调试方案 —— 一次性解决了就丢

**只沉淀**：经验级的"模式"和"教训"。

---

> 文档作者：Claude Code
> 状态：等待对应任务完成 → 由执行者按节奏写入 hierarchical-memory
