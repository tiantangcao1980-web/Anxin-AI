# 安心智能助手 · 安全架构白皮书

> 适用对象：客户安全 / 法务 / IT 评估人员
> 文档版本：v1（2026-05-14）
> 关联：[skills-sandbox-design.md](./skills-sandbox-design.md) · [enterprise-cluster-design.md](./enterprise-cluster-design.md) · [security-audit.md](./security-audit.md)

## 一、设计哲学

"**AI 不能成为新的攻击面**"——安心智能助手把"安全"刻进每一层，不是事后补丁。

三条铁律：

1. **fail-closed by default** —— 任一权限校验失败立即拒绝执行，不降级、不静默
2. **最小权限、最小数据** —— 按 GB/T 35273 五级分类，Skill 按 manifest 静态声明所需权限
3. **审计可追溯** —— 每次能力调用都留痕，含权限决策、数据指纹、操作主体

## 二、威胁模型

| 威胁来源 | 攻击路径 | 我们的缓解 |
|---|---|---|
| 恶意用户 | 越权调用敏感能力 | 六层闸门 + 角色绑定 + 部门继承 |
| 不可信 Skill | 提权 / 数据外泄 / 资源滥用 | 五分层沙箱 + 签名 + 配额 + 网络隔离 |
| 被泄密的 Agent 凭证 | LLM Prompt 注入 | Agent Governance + 工具调用白名单 + 审批 |
| 内部人员越权 | 跨租户访问 | 多租户行级隔离 + 跨租户访问审计 |
| 供应链攻击 | 引入恶意依赖 | 依赖锁定 + cryptography 高危 CVE 跟踪 |
| 端点失控 | 设备 Token 泄露 | 设备指纹 + 风险检测 + Redis 黑名单 |
| 网络中间人 | 抓包改包 | TLS 强制 + JWT + 安全头 |

## 三、六层权限闸门

每次能力调用串行经过：

```
[订阅校验] → [角色校验] → [权限校验] → [风险分级] → [隐私模式] → [设备信任]
     ↓             ↓             ↓             ↓             ↓             ↓
   fail        fail        fail        fail        fail        fail
   closed      closed      closed      closed      closed      closed
```

每层细节：

| 层 | 入口 | 失败动作 |
|---|---|---|
| 订阅 | [`CapabilityPolicyEngine`](../../backend/src/services/capability_policy_engine.py) | 引导升级 |
| 角色 | [`core/deps.py:UserRole`](../../backend/src/core/deps.py) 9 种角色 | 403 |
| 权限 | `Permission` 枚举（read:cases / write:contracts 等） | 403 |
| 风险 | [`agent_governance_service.py`](../../backend/src/services/agent_governance_service.py) L0-L5 | 触发审批 |
| 隐私 | [`security_config.py`](../../backend/src/core/security_config.py) 本地/混合/云端 | 自动路由到合规存储 |
| 设备 | 设备指纹 + 行为基线 | 二次挑战 |

## 四、Skill 沙箱五分层

未声明 tier 的 Skill 默认 **T3**（最严容器隔离）。

| Tier | 隔离方式 | 资源 | 网络 | 适用 |
|---|---|---|---|---|
| **T0** | Prompt-only，LLM 消费 SKILL.md | — | — | 76 个 markdown skill |
| **T1** | In-process（受信） | 全进程共享 | 继承 | 平台官方 + ed25519 签名 skill |
| **T2** | Subprocess（`setrlimit` + 限定 PATH） | 1 核 / 512MB / 30s | 默认 none | 平台测试期 skill |
| **T3** | Container（Docker） | 可配，默认 1 核 / 512MB / 64MB tmpfs | 默认 none | 第三方 / 用户自定义 |
| **T4** | Remote 沙箱（E2B / CodexCloud） | 提供商策略 | 受控 | 重计算 / 不能落 NAS |

**T3 默认硬编码安全参数**：

```bash
docker run --rm \
  --user 65534:65534 \
  --cap-drop=ALL \
  --security-opt no-new-privileges \
  --read-only \
  --tmpfs /tmp:size=64m \
  --pids-limit 256 \
  --memory <X>m --memory-swap <X>m \
  --cpus <Y> \
  --network none \
  -v <workdir>:/workspace:rw \
  ...
```

签名校验（`SignatureVerifier`）：
- T1 必须签名（ed25519）
- 公钥通过 `SKILL_SANDBOX_PUBLISHER_KEYS` 环境变量分发
- fingerprint 排除 signature 字段（避免签发自循环）

配额闸门（`QuotaTracker`）：
- 每租户每日三维上限：calls / compute_ms / concurrent
- T0/T1 默认不计费，T2-T4 必查
- Redis 实装支持多 worker 共享

## 五、企业内网集群权限模型

**核心算法**：

```
effective_permissions(user, scope=dept_d) =
  ROLE_PERMISSIONS[user.role]                                    # 旧字段 fallback
∪ ROLE_PERMISSIONS[r] for r in role_bindings(user, scope ⊇ dept_d)
∪ ROLE_PERMISSIONS[r] for r in role_bindings(user 所属部门链, scope ⊇ dept_d)
∪ ROLE_PERMISSIONS[r] for r in role_bindings(user 所属群组, scope ⊇ dept_d)
```

**继承方向**：父部门 → 子部门**单向向下**，避免向上传播触发越权。

**临时授权**：`role_bindings.expires_at` 严格过期，解析器一次性扫描判定。

**跨租户隔离**：所有租户表带 `org_id`，ORM 层强制 filter，缺失即测试失败。

## 六、数据分级（GB/T 35273-2020 对照）

| 级别 | 含义 | 加密 | 留痕 | 跨境 |
|---|---|---|---|---|
| **PUBLIC** | 公开信息 | TLS | 访问审计 | 允许 |
| **INTERNAL** | 内部使用 | TLS + 数据库静态加密 | 访问 + 修改审计 | 允许 |
| **CONFIDENTIAL** | 受控 | TLS + 字段级加密 | 访问 + 修改审计 + 离开租户审批 | 经审批 |
| **SENSITIVE** | 敏感 | TLS + 字段级加密 + 端到端 | 实时审计 + SOC 联动 | 禁止 |
| **TOP_SECRET** | 绝密 | TLS + 字段级 + 客户主密钥 | 全链路审计 + 双人解密 | 禁止 |

落到代码：[`security_config.py`](../../backend/src/core/security_config.py) `DataClassification` 枚举。

## 七、网络与传输

- 全站 TLS 1.2+，HSTS preload
- JWT access token 2h + refresh 7d + Redis 黑名单
- 安全头：CSP / X-Frame-Options / Referrer-Policy / X-Content-Type-Options（[index.html](../../frontend/index.html)）
- CAPTCHA：登录 / 注册 / 密码重置都接 Turnstile（生产）

## 八、审计与可观测

| 指标 | 实装 | 看板 |
|---|---|---|
| Skill 沙箱执行 | `audit_log{event_type=skill_sandbox_execute}` | Prometheus + Grafana |
| 沙箱拒绝 | `skill_sandbox_denied_total{reason}` | Grafana 告警 |
| 沙箱 OOM / 超时 | `skill_sandbox_oom_total / timeout_total` | Grafana 告警 |
| LDAP 同步 | `audit_log{event_type=ldap_sync}` | 日志 + Grafana |
| 权限决策 | `audit_log{event_type=permission_decision}` | 日志 |
| 跨租户尝试 | `audit_log{event_type=cross_tenant_denied}` | 实时告警 |

详见 [observability-deploy.md](./observability-deploy.md)。

## 九、合规对照

- **GB/T 35273-2020** ：完整对照见 [compliance-dengbao-mapping.md](./compliance-dengbao-mapping.md)
- **等保 2.0 三级** ：完整对照见 [compliance-dengbao-mapping.md](./compliance-dengbao-mapping.md)
- **GDPR / CCPA** ：DSAR、被遗忘权、可携带权 已实装于 [privacy.py](../../backend/src/api/routes/privacy.py)
- **ISO 27001** ：体系建设中（计划 2026 Q4 完成认证）

## 十、密钥与凭证管理

| 类别 | 存放 | 轮转 |
|---|---|---|
| JWT_SECRET | K8s Secret / Vault | 每 90 天 |
| 数据库密码 | K8s Secret | 每 180 天 |
| Skill 发布方公钥 (ed25519) | `SKILL_SANDBOX_PUBLISHER_KEYS` env | 按需 |
| LDAP bind password | K8s Secret | 跟随企业策略 |
| OIDC client_secret | K8s Secret | 跟随 IdP 策略 |
| E2B / CodexCloud API key | K8s Secret | 每 90 天 |

所有 secrets 不入代码、不入 git；CI/CD 走 sealed-secrets / external-secrets-operator。

## 十一、应急响应

1. **撤销 Token**：把 jti 加入 Redis 黑名单（`/api/v1/auth/logout-all`）
2. **撤销 Skill**：`PUT /api/v1/skills/{name}/toggle {enabled: false}`，运行时立即拒新执行
3. **撤销角色**：`DELETE /api/v1/enterprise/role-bindings/{id}`
4. **断网 / 断电话**：`docker compose stop nginx`（外网入口），数据库读写不丢
5. **取证**：审计日志 + WAL 归档完整，按合规要求保留 ≥ 180 天

## 十二、安全测试

| 类型 | 状态 |
|---|---|
| OWASP Top 10 自检 | ✅ [security-audit.md](./security-audit.md) |
| 依赖 CVE 扫描 | ✅ pip-audit + npm audit + 定期升级 |
| 静态分析 | ✅ Ruff / mypy / ESLint --max-warnings 0 |
| 单元测试覆盖率 | ✅ 后端 180+ tests 全过 |
| 渗透测试 | 🔄 计划季度一次（私有化客户可定制） |
| Bug Bounty | 🔄 计划 2026 Q3 启动 |

## 十三、安全联络

- `security@anxin.ai` —— 漏洞披露 / DSAR / 应急
- 安全 SLA：高危 24h 响应，中危 72h，低危 7d
- 加密通信：可用 PGP，公钥见 https://anxin.ai/.well-known/security.txt

---

**附录 A · 缩写与术语**

| 术语 | 含义 |
|---|---|
| Skill | 能力原子，文件式 SKILL.md 加载 |
| Persona | 业务智能体（10 个） |
| Manifest | SKILL.md 的 sandbox 块声明 |
| Tier | 沙箱信任分级（T0-T4） |
| Role Binding | 主体 × 角色 × 作用域 |
| DSAR | Data Subject Access Request 数据主体请求 |
