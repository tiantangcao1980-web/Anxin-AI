# 数据边界 Doctrine

> 数据出 / 入边界时必须穿过三道闸门：**分级 → 法域 → PII 脱敏**。
> 本 doctrine 解释为什么，[`policy/data-classification.yaml`](../../policy/data-classification.yaml) 与 [`policy/jurisdiction-rules.yaml`](../../policy/jurisdiction-rules.yaml) 写下具体规则。

## 一、数据分级（5 级）

| Level | 名称 | 示例 | 写入 LLM Prompt | 共享知识库 | 跨租户 |
|---|---|---|---|---|---|
| **L1** | `public` | 公开法规、政府公告 | ✅ | ✅ | ✅ |
| **L2** | `internal` | 内部 SOP、文档模板 | ✅ | ✅ | ❌ |
| **L3** | `confidential` | 合同、客户名单、未公开财报 | ✅（默认本地模型）| 仅本租户 | ❌ |
| **L4** | `restricted` | 个人敏感信息、银行账号 | ⚠ 须先脱敏 | ❌ | ❌ |
| **L5** | `privileged` | 律师 / 客户特权通讯、商业秘密 | ❌ | ❌ | ❌ |

### 默认分级（落到 [`policy/data-classification.yaml`](../../policy/data-classification.yaml)）

- 合同正文：L3
- 含个人身份信息的合同：L4
- 律师函 / 律师备忘 / 谈判策略：L5
- 工商 / 司法公开数据：L1
- 内部周报 / OKR：L2
- 应收账款表 / 发票明细：L3
- 客户尽调底稿：L4
- 银行流水 / 收付款单：L4
- 跨境支付明细：L4

## 二、法域边界

### 默认行为

- **默认法域**：CN（中国大陆）
- **跨境数据流向**必须显式声明，**强制人工 confirm**
- 跨境流动支持的方向（按现行法规）：
  - `CN ↔ HK`（个人信息出境标准合同 SCC 备案）
  - `CN → SG / Global`（重要数据走 CAC 评估，非重要数据走 SCC）
  - `EU → CN`（GDPR Art. 46 适用条款 + 中国接收方接受程度）
  - `US → CN`（无特殊限制，但部分行业有 ITAR / EAR 受限）

### 法域上下文字段

每条 LLM 输入 / 输出 / 工具调用必须打 `jurisdiction` 标签。规则：

| 数据源国家 | 处理国家 | 标签 | 守门 |
|---|---|---|---|
| CN | CN | `CN` | ALLOW |
| CN | EU | `CN→EU` | REQUIRE_CONFIRM + 法务批 |
| EU | CN | `EU→CN` | REQUIRE_CONFIRM + GDPR 路径验证 |
| US | CN | `US→CN` | REQUIRE_CONFIRM + ITAR 检查 |
| Global | CN | `*→CN` | 默认 ALLOW（带法域标签） |

具体见 [`policy/jurisdiction-rules.yaml`](../../policy/jurisdiction-rules.yaml)。

## 三、PII 脱敏

### 触发条件

任一字段命中下表 → 写入 LLM Prompt 前自动脱敏；外发前二次校验：

| 字段类型 | 识别正则 / 算法 | 脱敏策略 |
|---|---|---|
| 大陆身份证号 | `^\d{17}[\dXx]$` | `110********1234` 保头 3 尾 4 |
| 大陆手机号 | `^1[3-9]\d{9}$` | `138****1234` |
| 银行卡号 | Luhn 16-19 位 | `6222****1234` |
| 邮箱 | RFC 5322 | `t***@example.com` |
| 护照号 | `^[A-Z]\d{8}$` | `E****1234` |
| 车牌号 | 中国车牌正则 | `京A****5` |
| 美国 SSN | `\d{3}-\d{2}-\d{4}` | `***-**-1234` |
| 欧盟 IBAN | IBAN checksum | `DE89****0532013000` |
| 信用卡 CVV | 3-4 位 | **整段拒绝**（永不写入） |
| GPS 坐标（高精度）| ±0.0001 | 降精到 ±0.01 |

### 脱敏后写入 LLM 时

附加 marker：`<PII:type=phone>138****1234</PII>`。模型看到 marker 后**禁止还原**；如必须还原（如填表），由 PEP 在响应渲染阶段查 KMS 还原。

### 例外

特定 skill 可在 frontmatter 声明 `pii-handling: keep-raw` 并附 `pii-justification`，仅以下场景允许：

- KYC 验证（dd-expert / kyc skill）
- 实名制合规上报（finance-tax-advisor / tax-filing）

允许后仍走双签 + L4 数据分级。

## 四、律师 / 客户特权（Privilege）

**永不写入共享知识库 / 跨租户 / LLM 训练数据**。

### 识别

- 来源标签为 `attorney-client` / `attorney-work-product` 的文档
- 文件名 / 头部含 "PRIVILEGED & CONFIDENTIAL" / "ATTORNEY WORK PRODUCT"
- 由律师 persona 主动标注

### 处理

- 仅写入 **私有命名空间** `tenants/<tid>/privileged/`
- 检索仅返回给同一律师 / 客户对
- 离开命名空间需要 `governance.policy.write` 权限（即 super_admin 手动批准）

## 五、数据生命周期

| 阶段 | 守门 |
|---|---|
| 采集 | 标 `source` + `classification` + `jurisdiction` |
| 存储 | L3+ 走 SQLCipher / AES-256 / KMS；L5 单独 vault |
| 处理 | PEP 校验 `subject.clearance ≥ resource.classification` |
| 共享 | 跨租户禁止 ≥ L3；跨法域必须 confirm |
| 销毁 | 按 [`policy/retention.yaml`](../../policy/retention.yaml) 自动过期 |
| 备份 | 与生产同分级；不降级 |

## 六、与 backend 的衔接

`backend/src/services/governance/data_classifier.py` 提供：

```python
classify(text: str) -> Classification  # 返回 (level, pii_findings, jurisdiction_hints)
mask(text: str, *, target_level: Classification) -> str  # 脱敏
unmask(masked: str, *, subject: User) -> str  # 仅 PEP + 授权后可调
```

## 七、应急响应

数据泄漏 / 误外发 / 越权访问触发后：

1. **30 分钟内** — Builder Hub 自动撤回相关 skill；冻结相关 token；写 incident log
2. **2 小时内** — 法务发起 incident review；评估是否触发监管报告
3. **24 小时内** — 跨境数据出境 → 必须报 CAC（按《个人信息保护法》§ 43）
4. **72 小时内** — GDPR 涉及 → 报 EU DPA

详细预案见 [SECURITY.md](../../SECURITY.md) + [docs/release/incident-runbook.md](../release/incident-runbook.md)。
