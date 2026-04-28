# V3 综合安全审计报告（2026-04-28）

> 审计基线：v3/main HEAD = `cea6489`（chore(p11-health) — 全量回归）
> 审计范围：v3 9 大新增模块（fetch / sandbox / app_authorization / im_gateway / im_pairing / persona / agent_tasks / sentiment / webhook_security）+ 既有 P0-P3 鉴权基线
> 工具：pip-audit 2.x、npm audit、人工 grep/Read 审查、git-history 扫描

---

## 摘要

| 维度 | 结果 |
|------|------|
| OWASP Top 10 通过 / 中风险 / 高风险 | **3 / 4 / 3** |
| 后端依赖漏洞（pip-audit） | **35 个 / 13 个包**（含 1 个 GHSA-高危 + 多个 CVE-2026 高危） |
| 前端依赖漏洞（npm audit） | **31 个**（critical 1 / high 19 / moderate 10 / low 1） |
| 历史凭据泄漏 | **🔴 是** — DashScope / MiniMax JWT / JWT_SECRET / LLM Fernet Key 全部在 git 历史中存在 |
| 整体评级 | **🔴 高风险**（凭据泄漏 + 多个 SSRF/Webhook 默认放行 / 关键依赖未升级） |

**Top 3 立即行动**：
1. **旋转所有泄漏密钥**（DashScope / MiniMax / JWT / Fernet / DB / MinIO / Neo4j），并对 git 历史做 BFG 清洗或 force-push 重写
2. **加 SSRF 防护**到 FetchService（IP 白名单 / 拒绝内网 + 元数据 IP / 限制 scheme）
3. **修复飞书签名校验空 key 放行** + 增加 timestamp 时间戳防 replay

---

## OWASP Top 10 详情

### A01 Broken Access Control — 🟢 通过
- **检查模块**：persona_anxin/legal/contract/dd/finance/sales/market/ecommerce/content、im、im_pairing、sentiment、app_authorizations、agent_tasks、fetch
- **抽样结果**：每个 v3 路由都注入 `Depends(get_current_user_required)` 或 `Depends(require_permission(...))`；IM 配对审批 endpoint 用 `get_admin_user` 守卫；fetch 审计 endpoint 用 `_require_admin(user)` 二次校验。
- **跨用户隔离**：`agent_tasks` / `app_authorizations` 在 service 层均按 `user_id` 过滤；OAuth callback 通过 state→user_id 绑定。
- **轻微问题**：5 法务 persona endpoint 仅检查登录态，没有针对"专业资质"的二次校验；P10/P11 风险层应规划"律师身份+执业证号"白名单。
- **推荐**：(1) 给 `persona_legal` / `persona_dd` 增加 `require_permission(VERIFY_LAWYER)` 之类的资质门；(2) 在 `persona_*` service 层 enforce `tenant_id` 隔离日志。

### A02 Cryptographic Failures — 🟡 中风险
- **正面**：
  - `TokenStore` 用 `cryptography.fernet.Fernet` + `MultiFernet` 支持 key rotation；
  - JWT secret 在 `production` 模式下若仍是默认值会 fail-fast；
  - 飞书 payload 解密用 AES-256-CBC + SHA256(encrypt_key)。
- **风险**：
  - `JWT_SECRET_KEY` 默认 `"your-super-secret-jwt-key-change-in-production"`，在 development 下自动 `secrets.token_urlsafe(32)`，但**重启后改变** → 已签发 JWT 立刻失效；应持久化到 secrets manager。
  - `OAUTH_TOKEN_ENCRYPTION_KEY` 必填，但**没在启动期 fail-fast** — 直到首次 OAuth callback 才崩溃。
  - Redis 缓存的 OAuth state 用明文存储 user_id（TTL 600s 可接受），但**没启用 Redis ACL/TLS** 时存在内网窃听风险。
- **推荐**：(1) 启动期校验所有加密 key；(2) 文档化 Fernet key 的持久化与轮换 SOP；(3) 生产 Redis 强制 `requirepass` + TLS。

### A03 Injection — 🟢 通过（细节扎实）
- **SQL Injection**：v3 新增模块全部走 SQLAlchemy ORM；唯一 raw SQL 在 `historical_wenshu.py` 用 f-string 拼 `self._table`，但 `__init__` 已用 `_SAFE_TABLE_NAME.match(table_name)` regex 校验，且 case_id/keyword 全部走 `:bind` 参数化。**无 injection 风险**。
- **Command Injection**：`LocalProvider.exec` 强制 `cmd: list[str]` + `_validate_cmd` 拒绝非 str / NUL 字节 + 显式禁用 `shell=True`，从源头阻断。
- **SSRF**：见 A10。

### A04 Insecure Design — 🟡 中风险
- **正面**：IM 配对 24h 窗口 + Celery beat 每 10 分钟扫过期；OAuth state 一次性使用 + Redis TTL 600s；OAuth refresh 失败显式标 `EXPIRED`。
- **风险**：
  - **沙箱默认 LocalProvider** — `SANDBOX_PROVIDER: str = "local"`，生产若忘配置会以 root 身份执行任意代码（虽然 cmd 有 list 校验，但仍跑在宿主机用户）。
  - LocalProvider **未真正 enforce** `spec.cpu_limit / memory_limit / disk_quota`，只是写入 metadata。
  - IM 配对 `requester_id` 是 IM 平台的 OPENID/UnionID — 若 webhook 被伪造，攻击者可凭借单条 webhook 触发管理员审批界面（虽然审批仍需 admin 同意）。
- **推荐**：(1) 生产环境 startup 校验 `SANDBOX_PROVIDER != "local"` 或显式 opt-in；(2) LocalProvider 文档"仅开发"+ `prod` 模式启动 raise；(3) 给 IM 配对加 webhook 签名+nonce 校验。

### A05 Security Misconfiguration — 🟡 中风险
- **CORS**：`allow_origins` 来自 `settings.CORS_ORIGINS`（默认仅 localhost + tauri），未硬编码 `"*"`，正确。
- **Debug**：`DEBUG: bool = False` / `DEV_MODE: bool = False` 默认关，但是 `dev_mode` 注释提示"启用后允许无 Token 访问 API" — 必须 prod 强制 `False`。
- **Verbose Errors**：多处 `raise HTTPException(status_code=500, detail=str(e))` 把异常 stack 暴露给客户端（如 `app_authorizations.py`、`fetch.py` 的 502/500 路径）。
- **Tauri CSP**：未在仓库根/`desktop/` 下找到自定义 CSP 配置（Tauri 默认 CSP 已较严，但建议显式）。
- **推荐**：(1) prod 启动时 assert `not DEBUG and not DEV_MODE`；(2) 把 `detail=str(e)` 改成"内部错误，请提供 trace_id"；(3) 给 desktop 增加显式 `tauri.conf.json#security.csp`。

### A06 Vulnerable Components — 🔴 高风险
- **后端 35 处**（详见下方依赖漏洞清单）。重点：
  - `cryptography 46.0.3` — 3 个 CVE-2026 高危
  - `pyjwt 2.10.1` — CVE-2026-32597
  - `litellm 1.83.0` — GHSA-xqmj-j6mv-4862
  - `pypdf 6.6.0` — 12 个 CVE/GHSA
  - `lxml 5.4.0` / `pillow 10.4.0` — 多个 CVE
- **前端 31 处**：`vite 7.0-7.3.1`（3 个 high CVE，含 path traversal + WS 任意文件读）、`rollup 4.0-4.58`（path traversal 写）、`lodash`（critical：原型污染 + 命令注入）。
- **推荐**：(1) 后端 `uv lock --upgrade`，逐包评估 breaking change；(2) 前端 `npm audit fix`（不 force）+ vite/rollup 升 minor；(3) lodash 必须升 4.17.21+；(4) CI 增加 pip-audit + npm audit gate。

### A07 Identification and Authentication Failures — 🟡 中风险
- **正面**：access token 2h + refresh token 7d，refresh 流程显式标 `EXPIRED`；Redis token 黑名单（Redis 不可用降级）；密码策略最小 8 + 大小写+数字。
- **风险**：
  - 没看到 2FA/TOTP 代码（仅在 schema/description 偶尔提及），律师/管理员账号建议强制启用。
  - `verify_token` 对 Redis 不可用静默降级到无黑名单 — 主动 logout/换密 后旧 token 仍有效到 expire。
- **推荐**：(1) 至少为 `super_admin` / `org_admin` / `partner` 强制 2FA；(2) Redis 不可用时 admin 端点直接 503，而非降级。

### A08 Software and Data Integrity Failures — 🟡 中风险
- **WebhookSecurity (Shopify/通用)**：HMAC-SHA256 + timestamp ±300s + replay 缓存（in-memory dict）— 设计正确。
- **隐患**：
  - `if not secret: return not settings.is_production()` — 非生产直接放行（开发可，生产因 `is_production()` 返回 False 而拒绝；但需保证 `ENVIRONMENT=production` 真设置）。
  - replay cache 在**内存**而非 Redis — 多 worker 部署下，攻击者可能通过命中不同 worker 重放。
- **飞书签名**：`verify_signature` 在 `not encrypt_key` 时**直接返回 True 放行所有未签名请求**（注释里也承认）— 这是危险的 backward-compat 默认。
- **推荐**：(1) WebhookSecurity 的 `_seen_signatures` 改 Redis；(2) 飞书 `verify_signature` 改成"无 key → 拒绝"或显式 require setting 开关；(3) 校验 `X-Lark-Request-Timestamp` 时戳新鲜度。

### A09 Security Logging and Monitoring Failures — 🟢 通过
- FetchService 每次抓取写 `AuditRecord`（90d 保留 + 管理员可查 + stats）；
- agent_tasks 有 event_log；
- 鉴权失败 log warning（包含 user/role/missing perms）。
- **不足**：无统一 SIEM 出口（loguru → 文件 / stdout），生产建议接入 Loki/ES。

### A10 SSRF — 🔴 高风险（最关键）
- **FetchService 完全暴露给登录用户**（`POST /api/v1/fetch`），URL 类型仅 `url: str`（无 `pydantic.HttpUrl` 校验）。
- **L1HttpTier** 用 `httpx.AsyncClient(follow_redirects=True)` 直接请求用户 URL — **没有任何 IP 黑名单**：
  - 可达 `http://169.254.169.254/latest/meta-data/`（AWS/阿里云元数据 → IAM 凭据）
  - 可达 `http://metadata.google.internal/`
  - 可达 `http://10.x.x.x` / `192.168.x.x` / `127.0.0.1` / `localhost`
  - 可达 `file://` ❓（httpx 不直接支持 file://，但 redirect 可被滥用）
  - 可达 `gopher://` / `dict://` ❓（httpx 默认拒绝，但需显式核实）
- **`compliance/blocklist.py`** 只拦截了 `wenshu.court.gov.cn` / 微信 / Shopify admin — **没有 IP / 协议 黑名单**。
- **响应回显**：抓取结果 `text` / `extracted` 直接返回给调用方 — 攻击者可读取响应。
- **推荐（P0 修复）**：
  ```python
  # FetchRequestIn
  url: HttpUrl  # 自动校验 scheme ∈ {http, https}

  # FetchService.fetch 入口前
  parsed = urlparse(request.url)
  if parsed.scheme not in {"http", "https"}: reject
  # DNS 解析后检查 IP 是否私有/保留
  ip = socket.gethostbyname(parsed.hostname)
  if ipaddress.ip_address(ip).is_private or is_link_local or is_loopback:
      reject SSRF_PRIVATE_IP
  # disable redirect or whitelist redirect target
  ```

---

## 依赖漏洞清单

### 后端（pip-audit，35 / 13 个包）

| Package | Version | Severity (推断) | CVE / Fix |
|---------|---------|-----------------|-----------|
| crawl4ai | 0.4.24 | 高 | CVE-2025-28197 / CVE-2026-26216 / CVE-2026-26217 → 0.8.0 |
| cryptography | 46.0.3 | 高 | CVE-2026-26007 / 34073 / 39892 → 46.0.7 |
| ecdsa | 0.19.1 | 中 | CVE-2024-23342 / CVE-2026-33936 → 0.19.2 |
| litellm | 1.83.0 | 高 | GHSA-xqmj-j6mv-4862 → 1.83.7 |
| lxml | 5.4.0 | 中 | CVE-2026-41066 → 6.1.0 |
| pillow | 10.4.0 | 中 | CVE-2026-25990 / 40192 → 12.2.0 |
| protobuf | 6.33.4 | 中 | CVE-2026-0994 → 6.33.5 |
| pyasn1 | 0.6.2 | 低 | CVE-2026-30922 → 0.6.3 |
| **pyjwt** | 2.10.1 | **高** | CVE-2026-32597 → 2.12.0 |
| pypdf | 6.6.0 | 中-高 | 12 个 CVE/GHSA → 6.10.2 |
| python-dotenv | 1.2.1 | 低 | CVE-2026-28684 → 1.2.2 |
| python-multipart | 0.0.21 | 中 | CVE-2026-24486 / 40347 → 0.0.26 |
| requests | 2.32.5 | 中 | CVE-2026-25645 → 2.33.0 |

### 前端（npm audit，31 / 1022 deps）

| Package | Severity | CVE | Fix |
|---------|----------|-----|-----|
| **lodash** | **critical** | GHSA-fvqr-27wr-82fm（原型污染）+ GHSA-35jh-r3h4-6jhm（命令注入） | npm audit fix |
| vite (7.0-7.3.1) | high (×3) | path traversal map handling / fs.deny bypass / WS 任意文件读 | npm audit fix |
| rollup (4.0-4.58) | high | path traversal arbitrary file write | npm audit fix |
| postcss <8.5.10 | moderate | XSS via unescaped `</style>` | npm audit fix |
| picomatch | high | ReDoS via extglob | npm audit fix |
| braces <3.0.3 | high | uncontrolled resource consumption | npm audit fix |
| brace-expansion | moderate | DoS zero-step seq | npm audit fix |
| ajv <6.14.0 | moderate | ReDoS `$data` | npm audit fix |
| uuid <14.0.0 | moderate | buffer bounds | npm audit fix --force |
| 其他 22 项 | low-moderate | 略 | npm audit fix |

---

## 凭据与密钥（**🔴 重大事件**）

### 1. git 历史泄漏（确认）

| Commit | 文件 | 泄漏内容 |
|--------|------|----------|
| `ed8ea03` (2026-03-28) | `.env` | `LLM_API_KEY=SK_REDACTED_ROTATED_2026_04_28` (DashScope/通义)、备注里另含 MiniMax JWT、智谱 GLM key 等 |
| `b3700bb` (2026-03-30) | `backend/.env` | `LLM_API_KEY=SK_REDACTED_ROTATED_2026_04_28`、`OPENAI_API_KEY` 同上、`JWT_SECRET_KEY=dev-secret-key-change-in-prod`、`LLM_ENCRYPTION_KEY=XEV_-4SDguvdLOroAspqmV4bOo-DWhTgyiDE6wMeSjw=` (Fernet)、`ADMIN_INITIAL_PASSWORD=admin123`、`MINIO_SECRET_KEY=password`、`NEO4J_PASSWORD=password`、`DATABASE_URL` 含 `postgres:password` |

**当前**：`.gitignore` 已包含 `.env`，新 commit 不会再泄漏；但 git 历史中**任何 clone 该仓库的人都能拿到上述密钥**，必须假定已被外部获取。

### 2. 配置默认值审查

| Setting | 默认值 | 风险 |
|---------|--------|------|
| `JWT_SECRET_KEY` | `"your-super-secret-jwt-key-change-in-production"` | prod 启动 fail-fast，dev 自动随机 — 设计可接受 |
| `OAUTH_TOKEN_ENCRYPTION_KEY` | `""` | 启动期不校验，首次 OAuth 才崩 |
| `ADMIN_INITIAL_PASSWORD` | `None` | seed 脚本会读，未设可能跳过/默认 — 需 docs 强调 |
| `MINIO_SECRET_KEY` | `"password"` | 默认值即弱密码，prod 必须覆盖 |
| `NEO4J_PASSWORD` | `"password"` | 同上 |
| `DATABASE_URL` | `postgres:password` | 同上 |
| `INTEGRATION_API_KEY` | `None` | 多个 webhook 校验依赖 |

### 推荐
1. **立即旋转**所有泄漏的密钥（DashScope / MiniMax / OpenAI / Fernet / JWT / DB / MinIO / Neo4j）；
2. **清洗 git 历史**：`git filter-repo --invert-paths --path .env --path backend/.env --force`，然后 force-push（团队协调）；
3. **接入 secrets manager**（doppler / 阿里云 KMS / 1Password CLI），禁止任何 .env 入库；
4. **CI 增加 gitleaks / trufflehog 扫描** PR；
5. **启动期校验**：`OAUTH_TOKEN_ENCRYPTION_KEY` / `JWT_SECRET_KEY` / `INTEGRATION_API_KEY` 在 prod 模式必须非空且非默认。

---

## 高风险点重点审计

### SandboxExecutor — 🟡
- ✅ `cmd` 必须 `list[str]` + `_validate_cmd` 防 NUL；
- ✅ 显式 `shell=False`（`asyncio.create_subprocess_exec`）；
- ✅ `_resolve_inside` 防路径逃逸；
- ✅ `tempfile.mkdtemp(prefix="sbx_local_")` 不可预测；
- ✅ 超时强 kill；
- ❌ **资源限额（mem/cpu/disk）只是 spec metadata，LocalProvider 没用 ulimit / cgroups enforce**；
- ❌ **默认 `SANDBOX_PROVIDER=local`** — 生产忘记切 docker/e2b 就以宿主机用户身份跑。

**建议**：(1) prod 启动时 raise if local；(2) 用 `resource.setrlimit` (RLIMIT_AS / CPU / FSIZE) 在子进程 preexec_fn 设置硬上限；(3) `env={**os.environ, ...}` 改成最小化白名单避免泄漏宿主 secrets。

### FetchService SSRF — 🔴
见 A10 详述。最严重发现：
- 没拦内网 IP / loopback / 元数据 IP；
- `url: str` 不限 scheme；
- `follow_redirects=True` 可被 redirect 到内网；
- 响应原文回显给调用方。

### OAuth Callback — 🟢
- ✅ state CSRF 防护：32 字节 token_urlsafe + Redis TTL 600s + **一次性使用**（pop）；
- ✅ code 由 provider 一次性，OAuth 框架本身保证；
- ✅ token 加密入库（Fernet）；
- ⚠️ `redirect_uri` 来自请求 body — provider 侧已会校验白名单，但**本地** `_default_redirect_uri` 用 `APP_AUTH_REDIRECT_BASE_URL`，应在配置时 enforce HTTPS 且匹配 provider console。

### Webhook 签名 — 🟡
- ✅ WebhookSecurity HMAC + timestamp ±300s + replay cache（详见 A08）；
- ❌ 飞书 `verify_signature` 空 key 直接放行；
- ❌ replay cache 是 process-local dict — 多 worker 失效；
- ❌ 部分集成（如 Shopify HMAC）需逐个核实是否调用了 WebhookSecurity（建议附 grep 列表）。

---

## 优先级修复清单

### P0（紧急，<1 周内）
1. **轮换全部泄漏密钥** + 清洗 git 历史
2. **FetchService SSRF 防护**：HttpUrl 校验 + DNS-resolved-IP 黑名单（私有/链路/元数据）+ 禁止 follow redirect 到非白名单
3. **飞书 `verify_signature` 空 key 改拒绝**
4. **后端 cryptography / pyjwt / litellm 升级**

### P1（高，<1 月内）
5. 前端 `npm audit fix` + 升级 vite/rollup/lodash
6. SandboxProvider prod 默认改为 docker 或启动 fail-fast
7. WebhookSecurity replay cache 改 Redis
8. `OAUTH_TOKEN_ENCRYPTION_KEY` 启动期校验
9. 接入 secrets manager + CI gitleaks gate

### P2（中，<3 月内）
10. super_admin / partner 强制 2FA
11. 5 法务 persona endpoint 增加资质 check
12. LocalProvider rlimit / cgroup enforce + env 白名单
13. 统一异常脱敏（去掉 `detail=str(e)`）
14. Tauri 显式 CSP

---

## 健康度评分

| 维度 | 评级 | 主要短板 |
|------|------|----------|
| Backend Security | 🟡 → 🔴（凭据泄漏拉低） | SSRF / 依赖 / 历史密钥 |
| Frontend Security | 🟡 | vite/rollup/lodash 高危依赖 |
| DevOps Security | 🔴 | 无 secrets manager / 无 CI 漏扫 / 无 gitleaks gate |
| 整体 | 🔴 | 必须先做 P0 才能进 prod |

---

## 与 P8-B HEALTH 的协同

| HEALTH 检查项 | SECURITY_AUDIT 补全 |
|---------------|----------------------|
| import smoke | 不覆盖运行时鉴权链 — 补 A01 抽样 |
| 单测/集成 | 不覆盖第三方依赖 CVE — 补 A06 pip-audit/npm audit |
| typecheck | 不覆盖业务安全语义 — 补 A04/A10 设计审计 |
| HEALTH_P11 健康分 | 与 SECURITY 评级独立：HEALTH 看可运行性，SECURITY 看防御深度 |

建议：HEALTH P12+ 增加 `security_baseline` gate（pip-audit + npm audit + gitleaks + 默认密钥扫描），整合进 P8-B 报告。

---

## 下一步建议

### P15-fix（可立即修代码）
- A10 SSRF 防护（FetchRequestIn + L1HttpTier）
- 飞书 verify_signature 空 key 改拒绝
- WebhookSecurity replay cache → Redis
- OAUTH_TOKEN_ENCRYPTION_KEY 启动校验
- HTTPException detail 脱敏

### P15-design（需设计变更）
- Sandbox 默认 provider 调整 + LocalProvider 弃用路径
- 法务 persona 资质门设计
- 多 worker WebhookSecurity 状态共享
- 异常追踪 ID（trace_id）替代 stack 暴露

### P15-process（流程变更）
- 接入 secrets manager（doppler / 阿里云 KMS）+ 编写 secret rotation SOP（季度）
- CI gate：pip-audit / npm audit / gitleaks / trufflehog
- 入职/离职 checklist：rotation 触发条件
- 季度安全演练（SSRF / token leak / sandbox escape）
