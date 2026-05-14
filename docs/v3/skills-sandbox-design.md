# Skills 沙箱方案设计

> 文档状态：**Draft v1**（2026-05-14）
> 关联：[skills-inventory.md](./skills-inventory.md) · [architecture.md](./architecture.md) · `backend/src/services/skill_registry/` · `backend/src/services/sandbox_executor/`
> 责任人：Backend Platform

## 1. 背景与目标

现状（见调研报告 §1）：
- 已有 `SkillRegistry` 加载 SKILL.md（76 个）、`SkillExecutor` 把 skill body 当作 prompt 注入 LLM
- 已有 `sandbox_executor` Provider 抽象（Local / Docker / E2B / CodexCloud）用于通用任务隔离
- 缺口：**SKILL.md → 沙箱**的桥接层、**信任分级**、**资源/网络/权限白名单**、**审计闭环**

Skills 沙箱要解决的核心问题：

1. **可执行代码的 skill**（office/docx、pdf、xlsx、scripts、用户自定义脚本）以怎样的方式安全执行
2. **第三方/社区 skill** 一键安装后默认在哪种信任级别下跑
3. **企业内租户**怎样授权某个 skill 访问某些资源（文件、网络、内部 API、其他 skill）
4. **失败/超时/越权**怎样审计回放

非目标：
- 不替代现有 prompt-only skill 的 `SkillExecutor` 执行路径（继续保留为 Tier 0）
- 不在本期实现 WASM/Firecracker；以 subprocess + Docker 起步

## 2. 信任分级（Trust Tier）

| Tier | 名称 | 执行方式 | 资源限额 | 网络 | 适用场景 |
|---|---|---|---|---|---|
| **T0** | Prompt-only | LLM 直接消费 skill body（现有路径） | — | — | 76 个 markdown skill，无代码 |
| **T1** | In-process（受信） | 直接 import 调用，仅资源监控 | 全进程共享 | 继承 | 平台官方且经签名的 skill（如 `office/docx`） |
| **T2** | Subprocess 沙箱 | `LocalProvider`：子进程 + `resource.setrlimit` + 受限 PATH | CPU 1 核 / RAM 512MB / 30s | 默认 `none`，可 allowlist | 平台测试期 skill / 内部代码 skill |
| **T3** | Container 沙箱 | `DockerProvider`：只读 rootfs + seccomp + cgroup | 可配 | 默认 `none` | 第三方 / 用户自定义 / 不可信代码 |
| **T4** | Remote 沙箱 | `E2BProvider` / `CodexCloudProvider` | 提供商策略 | 受控 | 重计算 / 不能落到 NAS 的工作负载 |

**降级原则**：未声明 tier 的 skill 默认 **T3**（最严）。要降到 T1/T2 必须显式 + 经过 `SkillGovernanceService` 审批 + 签名。

## 3. SKILL.md 元数据扩展

在现有 frontmatter 基础上**新增** `sandbox` 块（向后兼容，缺省即为 T0 prompt-only）：

```yaml
---
name: pdf-extract-tables
description: 从 PDF 中抽取表格为 CSV
version: 1.0.0
type: code              # prompt | code | hybrid（新增）
category: office
triggers: [pdf, 抽取表格]
personas: [enterprise_user, lawyer]
requires_apps: []

sandbox:
  tier: T2                     # T0 | T1 | T2 | T3 | T4
  entrypoint: pdf_extract:run  # 仅 code/hybrid 必填，module:func 形式
  runtime: python3.11          # T2/T3 时用于选择 provider 镜像
  resource_limits:
    cpu_millicores: 1000
    memory_mb: 512
    disk_mb: 1024
    timeout_sec: 30
  network:
    mode: none                 # none | allowlist | full（仅 dev）
    allowed_hosts: []
  filesystem:
    read: ["/workspace/inputs"]
    write: ["/workspace/outputs"]
  permissions:                 # 显式声明所需能力 — 用户安装时一次性授权
    - read:documents
    - write:documents
  egress_secrets: []           # 允许注入的 secret 名（不允许任意环境变量）

signature:                     # T1 必填；T2-T3 可选
  algo: ed25519
  publisher: anxin-platform
  sig: "base64(...)"
---
```

校验规则（在 `skill_registry/validators.py` 扩展）：

1. `type=code` 必须有 `sandbox.entrypoint`
2. `tier=T1` 必须有 `signature`
3. `network.mode=full` 仅 `ENVIRONMENT=development` 通过
4. `permissions` 必须是已知 `Permission` 枚举值
5. 任何 `..` / 绝对路径越界 → 拒绝注册

## 4. 运行时架构

```
┌──────────────────────────────────────────────────────────────┐
│                     SkillExecutor (现有)                       │
│  T0 prompt-only：直接组 prompt 调 LLM                          │
└───────┬──────────────────────────────────────────────────────┘
        │ type=code/hybrid
        ▼
┌──────────────────────────────────────────────────────────────┐
│              SkillSandboxRunner（新增）                       │
│  1. 解析 SKILL.md.sandbox / 校验 tier 合法性                   │
│  2. 权限闸门：调用 CapabilityPolicyEngine                       │
│  3. tier 路由：T1 in-process / T2-T4 → SandboxProviderRegistry │
│  4. 资源 / 网络 / 文件系统 限额 → SandboxSpec                  │
│  5. 注入审计上下文（user_id, tenant, skill_name, version）     │
│  6. 收集 ExecResult + 落 audit_log + 计 prometheus 指标         │
└───────┬──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│       SandboxProviderRegistry（现有）                          │
│  Local / Docker / E2B / CodexCloud                            │
└──────────────────────────────────────────────────────────────┘
```

### 4.1 关键模块新增（落到 `backend/src/services/`）

```
skill_sandbox/
├── __init__.py              # 公开 API
├── manifest.py              # SandboxManifest 解析 + 校验
├── runner.py                # SkillSandboxRunner（核心）
├── policy_gate.py           # 与 CapabilityPolicyEngine 衔接
└── audit.py                 # 沙箱执行审计 / Prometheus 指标
```

### 4.2 `SkillSandboxRunner.execute()` 时序

```
caller (chat / agent / api)
   │
   ├─► registry.get(skill_name)              # 现有
   ├─► manifest = SandboxManifest.from_skill(skill)
   ├─► policy_gate.check(user, manifest)     # 6 层校验（订阅/角色/权限/风险/隐私/设备）
   │       └─► 失败：返回 SkillResult(SKIPPED, reason)
   ├─► tier 路由：
   │     T1 → in_process_run(...)
   │     T2 → local_provider.provision + exec
   │     T3 → docker_provider.provision + exec
   │     T4 → e2b/codex_cloud.provision + exec
   ├─► 收集 ExecResult
   ├─► audit.record(execution, manifest, result)
   └─► 返回 SkillResult
```

## 5. 权限模型

复用 `core/deps.Permission` 枚举 + 现有 `CapabilityPolicyEngine`，**不引入新的权限语言**。Skill 安装时把 `manifest.permissions` **静态绑定到调用者的角色权限交集**，运行期不再扩权。

| 检查项 | 出处 |
|---|---|
| 订阅是否解锁该 tier | `capability_policy_engine` |
| 用户角色是否含 manifest.permissions | `core/deps.has_permission` |
| 风险级别（依据 tier 推断 L0-L5） | `agent_governance_service` |
| 隐私模式（本地/混合/云端 vs tier） | `security_config` |

**Fail-closed**：任何一项校验失败 → `SkillResult(status=SKIPPED, error=...)`，落 audit_log，**不抛 5xx**。

## 6. 网络隔离

- T2 `LocalProvider`：通过环境变量约束 + 进程级 `socket` monkey-patch（已实装于 `local_provider.py`，本期不改）。**默认 `mode=none`**
- T3 `DockerProvider`：`--network=none` 或自建 user-defined network + iptables egress allowlist
- T4 `E2BProvider`：用提供商 SDK 的网络策略

**allowlist** 仅在以下场景启用：
- 已声明在 `manifest.network.allowed_hosts`
- 主机匹配 `org_settings.skill_network_allowlist`（租户级二次确认）

## 7. 文件系统隔离

每次 `provision` 创建一个 ephemeral workdir（`/tmp/anxin-sbx-<id>` 或容器内 `/workspace`）：

| 路径 | 权限 |
|---|---|
| `${workdir}/inputs/` | 沙箱内 RO，由 runner 预先注入 |
| `${workdir}/outputs/` | 沙箱内 RW，runner 退出后回收 |
| `${workdir}/tmp/` | RW、`tmpfs`、大小受 `disk_mb` 限制 |
| 其他 | 不可见（chroot/mount namespace） |

退出后 **强制清理**（`terminate` 幂等）。

## 8. 审计与指标

### 8.1 审计日志

写入现有 `audit_service`，新增 `event_type=skill_sandbox_execute`，字段：

```
{
  "skill_name": "pdf-extract-tables",
  "skill_version": "1.0.0",
  "tier": "T2",
  "user_id": "...",
  "tenant_id": "...",
  "manifest_hash": "sha256:...",
  "exec_result": {"exit_code": 0, "duration_ms": 412, "killed_by_timeout": false},
  "denied_reason": null,
  "trace_id": "..."
}
```

### 8.2 Prometheus 指标

```
skill_sandbox_executions_total{skill, tier, outcome}      counter
skill_sandbox_duration_ms{skill, tier}                    histogram
skill_sandbox_denied_total{skill, reason}                 counter
skill_sandbox_oom_total{skill, tier}                      counter
```

详见 [observability-backend.md](./observability-backend.md)。

## 9. 安装流程（用户视角）

```
1) 上传/拉取 SKILL.md  ─►  /api/v1/skills/upload
2) 系统解析 manifest，展示「将获得权限：[...]、网络：none / xxx、资源：1c512m」
3) 用户点击「授权安装」
4) registry.register + 把 manifest 写入 audit 表（含 hash + 用户签字）
5) 后续每次 execute 时 runner 强制比对 manifest.hash，被篡改即拒绝
```

## 10. 路线图

| 阶段 | 里程碑 | 交付 |
|---|---|---|
| **P1**（本期） | T0/T2 全通 | `SkillSandboxRunner` + `LocalProvider` + manifest 解析 + audit + 单元测试 |
| **P2** | T3 容器 | DockerProvider 强化 + seccomp profile + 网络 allowlist iptables |
| **P3** | 签名 + Marketplace | ed25519 签名校验 + 一键安装 UI + 撤销 |
| **P4** | T4 远程 | E2B / CodexCloud 在生产环境的 quota + 计费集成 |
| **P5** | WASM | 评估 `wasmtime` / `wasmer` 替换部分 T3 场景 |

## 11. 安全核对清单（每次发布前）

- [ ] 默认 tier 是否 T3
- [ ] manifest.permissions 是否落到 audit
- [ ] T1 skill 是否签名校验通过
- [ ] `mode=full` 是否仅在 dev 通过
- [ ] 沙箱进程是否带 `PR_SET_NO_NEW_PRIVS`（Docker provider）
- [ ] workdir 清理是否 100% 覆盖（含异常路径）
- [ ] OOM / 超时是否记录指标

---

**附录 A：与 `agent_governance_service` 的边界**

`agent_governance` 负责「Agent 调用某个 capability 时的策略决策」，本设计把 skill 当作 capability 的一种特例：

- `agent_governance` → 是否允许 Agent 触发 skill
- `skill_sandbox` → skill 触发后以怎样的隔离粒度执行

两者通过 `manifest.permissions` 的同一份枚举对齐，不引入新的 ACL 语言。
