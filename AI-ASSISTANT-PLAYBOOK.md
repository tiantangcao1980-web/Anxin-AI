# 安心智能助手 · AI 工作助理方法论（Playbook）

> **本文档总结了我们从 Anthropic 两个旗舰参考实现移植的方法论：**
> - [`anthropics/claude-for-legal`](https://github.com/anthropics/claude-for-legal) — 12 个法务实践域插件
> - [`anthropics/claude-for-financial-services`](https://github.com/anthropics/claude-for-financial-services) — 11 个金融工作流 agent
>
> 这两个仓库展示了「**对外 persona 化、对内能力化**」「**冷启动访谈 → 执业画像 → skill 调用**」「**Cowork 插件 + Managed Agents API 双部署**」三套范式。
> 本文是把这三套范式落地到 Anxin AI 的操作手册。

---

## 一、四层产品架构

```
┌─────────────────────────────────────────────────────────┐
│ ① Marketplace                                           │
│    .claude-plugin/marketplace.json                      │
│    — 注册全部 10 个 persona 插件 + 4 个 cookbook        │
├─────────────────────────────────────────────────────────┤
│ ② Persona Plugins（用户可见的 10 个智能体）             │
│    plugins/<persona>/                                   │
│      ├ .claude-plugin/plugin.json                       │
│      ├ CLAUDE.md          ← 执业画像（cold-start 生成） │
│      ├ skills/             ← 可调 skill                 │
│      └ agents/             ← 该 persona 拥有的 cookbook │
├─────────────────────────────────────────────────────────┤
│ ③ Vertical Skills（21 个 specialized agent + 4 Office）│
│    skills/legal/  finance/  office/                     │
├─────────────────────────────────────────────────────────┤
│ ④ Managed-Agent Cookbooks（无人值守）                   │
│    managed-agent-cookbooks/<name>/agent.yaml            │
│    — 通过 Anthropic Managed Agents API 部署             │
│    — 或落地到 backend/src/tasks/managed_agents/         │
└─────────────────────────────────────────────────────────┘
```

**核心原则**：
- 「**用户只看到 10 个 persona**」（对外人格化）
- 「**每个 persona 后台编排 N 个 skill / agent**」（对内能力化）
- 「**所有外发动作必须经过人工 confirm**」（draft-only）

---

## 二、新接入团队的 60 秒上手路径

```bash
# A. Claude Code CLI（推荐开发者）
/plugin marketplace add /Volumes/安心科技02/Pproject/Anxin-AI
/plugin install legal-advisor@anxin-ai
/plugin install contract-steward@anxin-ai
/legal-advisor:cold-start-interview        ← ❶ 必须先跑

# B. 桌面工作站（用户）
1. 打开 Anxin AI Desktop（Tauri）
2. 系统托盘 → 设置 → 智能体插件市场 → 选择 persona → 安装
3. 第一次进入聊天前，桌面会强制弹出冷启动访谈向导
4. 访谈结束后，CLAUDE.md 写入 plugins/<persona>/CLAUDE.md

# C. Managed Agent（无人值守 / 计划任务）
export ANTHROPIC_API_KEY=sk-ant-...
bash scripts/deploy-managed-agent.sh regulation-monitor
bash scripts/deploy-managed-agent.sh contract-renewal-watcher
bash scripts/deploy-managed-agent.sh ar-aging-watcher --local   # 本地 Celery
```

---

## 三、Cold-Start Interview（冷启动访谈）—— 质量的命门

这是 Anthropic 两个旗舰仓库最重要的设计模式之一。它解决了一个核心问题：**为什么通用 AI 给出的法律 / 财务建议很空泛？因为它不知道你公司的「红线」「术语」「升级阈值」。**

### 访谈流程（6 块）

1. **团队基线**：公司名、行业、规模、SOP 位置
2. **法域 / 监管**：默认中国大陆，标注跨境涉及国家与特许行业
3. **术语与文风**：必须用 / 禁用的术语；正式 / 商务 / 口语化
4. **升级阈值**：金额 / 风险 / 法域三轴的「自动 / 提醒 / 升级」边界
5. **集成系统**：IM / ERP / CRM / OA / 知识库
6. **模板上传**：3–5 份代表性文档，AI 提炼结构与口径

访谈结束后，AI 写入 `plugins/<persona>/CLAUDE.md`。**所有 skill 在执行前会自动读取该文件**——这是输出从「通用 ChatGPT」变成「你公司专属顾问」的关键。

跳过冷启动会发生什么？所有 `/<persona>:*` 命令会输出风险提示并以最保守口径作答，但不再「定制化」。

---

## 四、Skill Frontmatter 规范

```yaml
---
name: contract-review                              # 唯一标识，kebab-case
description: 智能合同审查技能…                     # 一句话；显示在 /<plugin>:<skill> 自动补全
argument-hint: 上传合同 + 说明诉求                 # 用户提示
user-invocable: true                               # 是否允许直接 /<plugin>:<skill> 调用
access-level: practice                             # team | practice | firm
output-format: docx | md | xlsx                    # 输出形式
requires-research: true                            # 是否需要 connector
requires-practice-profile: true                    # 是否依赖 CLAUDE.md
triggers:                                          # 自动触发关键词（中英文混合）
  - 合同审查
  - contract review
version: 1.0.0
---
```

---

## 五、Slash Command 命名

所有用户面 slash 命令必须遵循 `/<plugin>:<skill>` 模式，例如：

| 命令 | 说明 |
|---|---|
| `/legal-advisor:cold-start-interview` | 法律顾问冷启动访谈 |
| `/contract-steward:review` | 合同审查 |
| `/contract-steward:amendment-history` | 修订历史追踪 |
| `/dd-expert:company-dd` | 公司尽调 |
| `/finance-tax-advisor:tax-compliance` | 税务合规自检 |
| `/market-researcher:deep-research` | 深度市场研究 |
| `/cross-border-ecom:amazon-listing` | Amazon listing 生成 |

注：现有 `skills/legal/*` 与 `skills/finance/*` 已经实装的 skill 会**被插件复用**，不需要重复实现。例如 `/contract-steward:review` 内部调用 `skills/legal/contract-review/SKILL.md`。

---

## 六、Managed Agent Cookbook（无人值守）

Anthropic 仓库把以下场景从「用户对话」改造成了「后台计划任务」：

| Anthropic 仓库 | 场景 | Anxin 对应 cookbook |
|---|---|---|
| claude-for-legal | reg-monitor | `regulation-monitor`（中国法规监控） |
| claude-for-legal | renewal-watcher | `contract-renewal-watcher`（合同续约） |
| claude-for-legal | docket-watcher | 暂未落地（中国诉讼案件号检索） |
| claude-for-financial | gl-reconciler | 暂未落地（总账对账） |
| claude-for-financial | month-end-closer | 暂未落地（月结） |
| claude-for-financial | kyc-screener | 部分落地（dd-expert/company-dd） |
| 新增 | AR 风控 | `ar-aging-watcher` |
| 新增 | 跨境定价 | `cross-border-pricing-radar` |

每个 cookbook 的 `agent.yaml` 必须声明：
- `trigger.cron`（Asia/Shanghai 时区）
- `tools`（白名单）
- `dataSources`（数据源）
- `humanGate`（人工守门规则）
- `guardrails`（至少 draft-only + source-attribution）

部署：`bash scripts/deploy-managed-agent.sh <name>` 或 `--local` 走本地 Celery。

---

## 七、风险守门（Guardrails）—— 不变量

> 这些规则**永不放松**。即使用户授权也不绕过。

1. **Draft-only** — AI 仅产出草稿；外发 / 盖章 / 上架 / 转账 / 调价等动作必须人工 confirm。
2. **Source attribution** — 每条结论必须附数据源（URL + 抓取时间戳 / 文件名 + 页码 / 法规第 X 条）。
3. **Jurisdiction transparency** — 涉及法域必须显式声明；默认中国大陆；跨境强制人工复核。
4. **Privilege handling** — 律师 / 客户特权通讯不写入共享知识库；只入私有命名空间。
5. **No PII leak** — 个人身份号 / 银行卡 / 手机号在写入或外发前自动脱敏。
6. **Conservative defaults** — 风险偏好默认「保守」，由 CLAUDE.md 显式上调到「平衡 / 激进」。
7. **No autonomous money / contract action** — Stripe 退款、合同盖章、Amazon 调价等动作 **必须双人审批**。

---

## 八、对应到现有 V3 实施代码

| 本文档概念 | V3 代码位置 |
|---|---|
| Persona 注册表 | `backend/src/agents/personas/registry.py` |
| Specialized agent | `backend/src/agents/specialized/` |
| Skill registry | `backend/src/skills/registry.py` |
| Skill executor | `backend/src/skills/executor.py` |
| Task orchestrator | `backend/src/orchestration/task_orchestrator.py` |
| OAuth framework | `backend/src/oauth/` |
| Sandbox | `backend/src/sandbox/local_provider.py` |
| Managed agent celery | `backend/src/tasks/managed_agents/` |

迁移 / 接线表见 `docs/v3/skills-inventory.md`。

---

## 九、扩展指南（添加第 11 个 persona）

```bash
# 1. 复制脚手架
cp -r plugins/anxin-assistant plugins/<new-persona>
# 2. 编辑 plugin.json / README.md / CLAUDE.md（移除占位）
# 3. 在 .claude-plugin/marketplace.json 增加注册项
# 4. 在 docs/v3/agent-personas.md 增加章节
# 5. 在 backend/src/agents/personas/registry.py 注册
# 6. 跑校验
python3 scripts/claude-plugin-validate.py plugins/<new-persona>
# 7. 跑 backend 单测
make test
```

## 十、扩展 / 添加 Managed Agent Cookbook

```bash
# 1. 在 managed-agent-cookbooks/<name>/ 新建 agent.yaml + README.md
# 2. 在 marketplace.json managedAgentCookbooks[] 追加
# 3. 在 backend/src/tasks/managed_agents/<name>.py 落地 Celery task（可选，本地执行需要）
# 4. 跑校验
python3 scripts/claude-plugin-validate.py managed-agent-cookbooks/<name>
# 5. 部署
bash scripts/deploy-managed-agent.sh <name>
```

---

## 十一、Backend ↔ Plugin 同步

任何 plugin 结构变更（新增 skill / cookbook / 改 metadata）后跑：

```bash
python3 scripts/sync-plugins-to-backend.py
```

会刷新 `backend/src/agents/personas/_plugin_index.py`（不要手改），供 `/api/personas` 读出 11 个插件的 slash 命令、cookbook、CLAUDE.md 路径。

CI 守门：

```bash
python3 scripts/sync-plugins-to-backend.py --check
# 若 _plugin_index.py 过期会 exit 1
```

## 十二、Builder Hub · 第三方 Skill 信任层

[plugins/builder-hub/](plugins/builder-hub/) 提供社区 skill 的发布 / 发现 / 安装管道。三个 slash 命令构成完整治理：

- `/builder-hub:skill-scan` — 扫描单个 SKILL.md（隐藏内容 / 注入 / 越权 / license / 时效 / 体积）
- `/builder-hub:skill-installer` — 安装前**强制**走 scan + 用户 confirm
- `/builder-hub:skill-publish` — 发布到 anxin-ai-official 注册表，含签名 + 撤回

所有动作写 `.claude/builder-hub-audit.jsonl`。Trust Level 矩阵 + Hard-Fail 规则见 [plugins/builder-hub/README.md](plugins/builder-hub/README.md)。

## 十三、Managed Agent 落地路径

每个 cookbook 现在双链：

```
managed-agent-cookbooks/<name>/agent.yaml        ← 单一真相源（spec）
        │
        ├── 云端：scripts/deploy-managed-agent.sh <name>
        │       → POST https://api.anthropic.com/v1/agents
        │
        └── 本地：scripts/deploy-managed-agent.sh <name> --local
                → backend/src/services/task_orchestrator/managed_agents/<name>.py
                  + Celery beat 自动调度（cron 同步自 agent.yaml）
```

Celery 任务桩位置：`backend/src/services/task_orchestrator/managed_agents/`，4 个 cookbook 已经各有一个 `<name_underscore>.py` 文件，调用约定见该目录 README。

启动 worker + beat：
```bash
cd backend
celery -A src.services.task_orchestrator.celery_app:celery_app worker -l info -Q agent_tasks
celery -A src.services.task_orchestrator.celery_app:celery_app beat   -l info
```

## 十四、技能治理 + 权限管理边界（核心）

> **目录入口**：[docs/governance/](docs/governance/) · [policy/](policy/) · [backend/src/services/governance/](backend/src/services/governance/)

### 14.1 三层结构

```
┌──────────────────────────────────────────────┐
│ Doctrine   docs/governance/*.md              │  ← 为什么这么做
│   SKILL-LIFECYCLE / AUTHZ-MODEL /            │
│   DATA-BOUNDARY / AUDIT-LOG-SPEC /           │
│   TRUST-LEVELS                               │
├──────────────────────────────────────────────┤
│ Policy     policy/*.yaml                     │  ← 具体是什么
│   access-matrix / trust-levels /             │
│   data-classification / jurisdiction-rules / │
│   tool-allowlist / pii-redaction /           │
│   skill-lifecycle                            │
├──────────────────────────────────────────────┤
│ Code       backend/src/services/governance/  │  ← 运行时强制
│   policy_loader (热重载 + 快照)              │
│   authz       (PDP)                          │
│   audit       (JSONL + DB 双写)              │
│   data_classifier (PII + 5 级分类)           │
│   tool_scope  (PEP 第三层)                   │
│   trust       (verified/community/untrusted) │
│   skill_lifecycle (DRAFT→...→REVOKED 状态机) │
│   deps        (FastAPI require_scope)        │
└──────────────────────────────────────────────┘
```

### 14.2 PDP / PEP 调用链

```
HTTP request
   │
   ▼
[PEP-1] FastAPI dep require_scope("skill.contract.review")
   │
   ▼
[PDP] governance.authz.decide(subject, action, resource, context)
   │  ── 步骤：role-deny → role-grant → global-gates → clearance → jurisdiction
   ▼
ALLOW / DENY / REQUIRE_STEP_UP / REQUIRE_CONFIRM   +  reasons[]
   │
   ├── DENY            → HTTP 403
   ├── REQUIRE_STEP_UP → HTTP 401 (前端拉 MFA)
   ├── REQUIRE_CONFIRM → 业务进入"草稿 + push to inbox"流程
   └── ALLOW
        │
        ▼
   [PEP-2] services/skill_executor 调用前再过 authz（PDP）
        │
        ▼
   [PEP-3] sandbox provider 内调用 tool 时过 tool_scope.enforce_tool_call
        │
        ▼
   [PEP-4] connector 外发动作前再次 confirm 守门
        │
        ▼
   audit.write_event(...)  ← JSONL + DB
```

### 14.3 数据 5 级 + 法域 + PII

- **L1 public** 公开法规
- **L2 internal** 公司 SOP
- **L3 confidential** 合同 / 客户名单 / 未公开财报
- **L4 restricted** PII / 银行账号 / 客户尽调底稿
- **L5 privileged** 律师/客户特权通讯 — **永不入共享 KB**

**法域**：默认 CN；跨境（CN ↔ EU / US）触发 `REQUIRE_STEP_UP`，必须人工 confirm + 走 SCC / 适当措施。

**PII**：12 种识别（身份证 / 手机 / 银行卡 / 邮箱 / 护照 / 车牌 / SSN / IBAN / CVV / GPS / 统一社会信用代码 / 税号）；写入 LLM 前自动脱敏 + `<PII:type=...>` marker。

### 14.4 Skill 生命周期 5 状态

```
DRAFT → REVIEW → PUBLISHED → DEPRECATED → REVOKED
                   │              │
                   ▼              ▼
                REJECTED   (12 周缓冲后)
```

迁移守门：覆盖率 ≥ 80% · scan 0 hard-fail · reviewer 双签 · shadow 24h 无异常。
撤回：写入 `.claude/builder-hub/revoked.json`，全网客户端拒绝该版本。

### 14.5 信任三级 + 工具白名单

| Trust | 安装 | 调用 | 外发 / 写 | 公网 |
|---|---|---|---|---|
| verified  | 自动 | 按 matrix | allow | allow |
| community | 提示 | 永远 confirm | confirm | allowlist |
| untrusted | 须 --trust-untrusted | 永远 confirm | **deny** | **deny** |

工具按类别（read_only / read_write_local / network_egress / external_send / shell / llm_call）授权；每个 persona 有默认 allow / confirm / deny 矩阵，per-skill 可显式覆盖；网络访问可附 host allowlist。

### 14.6 审计与重放

- **JSONL** `.claude/audit/YYYY-MM-DD.jsonl` append-only + 每事件 fingerprint
- **DB**（P10 接通）便于查询
- 关键事件：`skill.execute / authz.decide / data.access / policy.change / lifecycle.change / external.send`
- 法证留存：合规相关 10 年；普通调用 1 年；privileged 7 年
- 重放：`python3 scripts/audit-replay.py --trace-id ... --verify-fingerprint`

### 14.7 治理日常运维三大命令

```bash
# 提交前自检（CI 必跑）
python3 scripts/governance-lint.py

# PR 时 access-matrix 变更可视化
python3 scripts/access-matrix-diff.py --base main

# 重放 / 取证审计
python3 scripts/audit-replay.py --user usr_xxx --since 2026-04-01 --verify-fingerprint
```

### 14.8 修改 policy 的流程（不可绕过）

1. 改对应 `policy/*.yaml`
2. `python3 scripts/governance-lint.py` 通过
3. `python3 scripts/access-matrix-diff.py` 在 PR description 贴 diff
4. 至少 1 reviewer（涉及 `governance.*` / `lifecycle.*` 必 2 reviewer）
5. CI 合并触发 policy snapshot 写入 `.claude/policy-snapshots/<id>/`
6. 后端 reload — `kill -HUP <gunicorn pid>` 或 `make backend-reload-policy`

### 14.9 与已有 backend 衔接表

| 已有 | 治理升级后 |
|---|---|
| `core/deps.py UserRole` | 不动；映射到 `access-matrix.yaml § roles` |
| `app_authorization` OAuth | connector 调用前过 `authz.decide(connector.<provider>.<action>)` |
| `skill_registry` / `skill_executor` | 调用入口包一层 `audit_log` 装饰器 + `decide()` |
| FastAPI auth | 加 `Depends(require_scope("..."))` |
| Sandbox provider | 加 `enforce_tool_call(...)` |
| Audit | 启用 `governance.audit` JSONL（即用） |

## 变更日志

| 日期 | 变更 |
|---|---|
| 2026-05-14 | **初版**：从 Anthropic claude-for-legal / financial-services 移植 — marketplace + 10 personas + 4 cookbooks + CONNECTORS + 守门规则。 |
| 2026-05-14 | **第二轮**：21 个真实业务 skill 落地 + cookbook 引用 + sync-plugins-to-backend + Celery 桩 + Builder Hub 信任层。校验通过 11 personas。 |
| 2026-05-14 | **第三轮 · 治理 + 权限**：5 份 doctrine + 7 份 policy yaml + 8 个 backend governance 模块（PDP/PEP/Audit/分类/PII/Trust/Lifecycle）+ 3 个治理脚本 + 18 个 pytest。SKILL.md frontmatter 治理字段覆盖 34 个 skill；cookbook agent.yaml 加 governance section。 |

## 参考

- Anthropic. *Claude for Legal*. <https://github.com/anthropics/claude-for-legal>
- Anthropic. *Claude for Financial Services*. <https://github.com/anthropics/claude-for-financial-services>
- 本仓库 [`docs/v3/agent-personas.md`](docs/v3/agent-personas.md) — Persona 详细说明
- 本仓库 [`docs/v3/skills-inventory.md`](docs/v3/skills-inventory.md) — Skill 清单
- 本仓库 [`CONNECTORS.md`](CONNECTORS.md) — 数据源与连接器
- 本仓库 [`plugins/builder-hub/`](plugins/builder-hub/) — 社区 skill 信任层
