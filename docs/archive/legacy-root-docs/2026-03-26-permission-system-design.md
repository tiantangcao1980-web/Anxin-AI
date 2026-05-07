# 安心法务 — 权限体系设计文档

| 属性 | 值 |
|------|-----|
| 版本 | v1.0 |
| 日期 | 2026-03-26 |
| 状态 | 设计定稿 |
| 适用系统 | 安心法务 SaaS 平台 (Anxin Smart Legal Services) |

---

## 目录

1. [设计概述](#1-设计概述)
2. [权限模型架构](#2-权限模型架构)
3. [用户角色定义](#3-用户角色定义)
4. [功能权限矩阵](#4-功能权限矩阵)
5. [数据范围控制](#5-数据范围控制)
6. [匿名找律师隐私设计](#6-匿名找律师隐私设计)
7. [前端实现方案](#7-前端实现方案)
8. [数据库模型](#8-数据库模型)
9. [API 鉴权流程](#9-api-鉴权流程)
10. [审计与合规](#10-审计与合规)

---

## 1. 设计概述

### 1.1 设计目标

安心法务平台面向律师事务所、企业法务部门及个人用户，需要一套兼顾多租户隔离、细粒度权限控制和匿名隐私保护的权限体系。核心目标：

- **多租户安全隔离**：不同组织之间数据零交叉
- **最小权限原则**：每个角色只能访问完成其工作所需的最小资源集
- **匿名隐私保护**：用户找律师时可以选择匿名，信息逐级披露
- **灵活扩展**：支持角色自定义和权限动态调整
- **审计可追溯**：所有权限变更和敏感操作留有审计日志

### 1.2 当前系统现状

当前系统使用简单三级角色（`admin`、`member`、`viewer`），存储在 `users.role` 单字段中。本方案在此基础上进行扩展，保证向后兼容并平滑迁移。

---

## 2. 权限模型架构

采用 **RBAC + ABAC + 数据范围控制** 三层混合模型。

```
┌──────────────────────────────────────────────────────┐
│                  权限决策引擎                          │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │   RBAC   │  │   ABAC   │  │   Data Scope      │  │
│  │ 角色权限  │  │ 属性策略  │  │   数据范围控制     │  │
│  └────┬─────┘  └────┬─────┘  └────────┬──────────┘  │
│       │             │                  │              │
│       ▼             ▼                  ▼              │
│  ┌──────────────────────────────────────────────┐    │
│  │           最终权限 = RBAC ∩ ABAC ∩ Scope      │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

### 2.1 RBAC 层 — 基于角色的访问控制

- 用户 → 角色 → 权限（多对多）
- 支持角色继承：子角色自动拥有父角色的所有权限
- 角色绑定到租户/组织级别

### 2.2 ABAC 层 — 基于属性的访问控制

在 RBAC 基础上叠加动态属性条件，用于处理跨角色场景：

| 属性类别 | 示例属性 | 应用场景 |
|---------|---------|---------|
| 用户属性 | `user.verified`, `user.bar_license` | 律师执业证验证通过后才能接单 |
| 资源属性 | `case.sensitivity_level`, `doc.classification` | 绝密文件仅特定角色可见 |
| 环境属性 | `request.ip_range`, `request.time` | 仅办公网络可访问管理后台 |
| 关系属性 | `user.id == case.lawyer_id` | 只有案件负责律师才能查看 |

### 2.3 数据范围层 — Data Scope

控制 RBAC 权限的作用范围（详见第 5 节）：

| 范围级别 | 标识符 | 说明 |
|---------|--------|------|
| 全局 | `scope:global` | 平台所有数据 |
| 租户 | `scope:tenant` | 当前组织所有数据 |
| 部门 | `scope:department` | 所属部门及下级部门数据 |
| 个人 | `scope:self` | 仅本人创建/参与的数据 |

---

## 3. 用户角色定义

### 3.1 角色层级总览

```
Platform Layer
  └── super_admin（平台超级管理员）
  └── platform_lawyer（平台签约律师）

Tenant Layer
  └── org_admin（组织管理员）
  └── dept_admin（部门管理员）

Business Layer
  └── partner（合伙人）
  └── lawyer（律师）
  └── assistant（律师助理/法务助理）
  └── enterprise_user（企业用户）
  └── individual_user（个人用户）
```

### 3.2 各角色详细定义

#### ① super_admin — 平台超级管理员

| 维度 | 说明 |
|------|------|
| **角色标识** | `super_admin` |
| **典型用户** | 安心法务平台运营团队、CTO |
| **职责** | 平台全局运维，用户管理，系统配置，数据统计 |
| **权限范围** | `scope:global` — 全平台所有数据 |
| **可见菜单** | 全部菜单 + 管理后台（用户管理、组织管理、审计日志、系统配置、运维监控） |
| **特殊权限** | 创建/冻结组织、分配角色、查看所有审计日志、LLM 配置管理、系统健康监控 |

#### ② platform_lawyer — 平台签约律师

| 维度 | 说明 |
|------|------|
| **角色标识** | `platform_lawyer` |
| **典型用户** | 与安心平台签约合作的独立律师 |
| **职责** | 在平台接单大厅接受用户委托、提供在线法律咨询 |
| **权限范围** | `scope:self` + 已接案件的数据 |
| **可见菜单** | AI 对话、接单大厅、我的案件、案件协作群、知识库（只读）、收款管理 |
| **特殊权限** | 查看脱敏后的匿名咨询、接受委托、发起签约流程 |
| **准入条件** | ABAC 属性 `bar_license_verified = true`（执业证已认证） |

#### ③ org_admin — 组织管理员

| 维度 | 说明 |
|------|------|
| **角色标识** | `org_admin` |
| **典型用户** | 律所主任、企业法务总监 |
| **职责** | 管理本组织用户、部门结构、权限分配 |
| **权限范围** | `scope:tenant` — 本组织所有数据 |
| **可见菜单** | 全部业务菜单 + 组织管理（成员管理、部门管理、权限配置、组织统计） |
| **特殊权限** | 邀请/移除组织成员、创建部门、设置部门管理员、查看组织级审计日志 |

#### ④ dept_admin — 部门管理员

| 维度 | 说明 |
|------|------|
| **角色标识** | `dept_admin` |
| **典型用户** | 律所合伙人（管理团队）、企业法务部经理 |
| **职责** | 管理本部门成员和资源 |
| **权限范围** | `scope:department` — 本部门及下级部门数据 |
| **可见菜单** | 全部业务菜单 + 部门管理（成员管理、部门统计） |
| **特殊权限** | 管理部门成员角色、查看部门级统计 |

#### ⑤ partner — 合伙人

| 维度 | 说明 |
|------|------|
| **角色标识** | `partner` |
| **典型用户** | 律所高级合伙人、权益合伙人 |
| **职责** | 执行高价值法律业务、审批重要事项、监督案件质量 |
| **权限范围** | `scope:department` — 所负责团队的所有数据 |
| **可见菜单** | AI 对话、合同审查、案件管理、文档中心、尽调分析、知识库、审批流、案件协作群、统计报表 |
| **特殊权限** | 审批合同、审批费用申请、查看团队所有案件、分配案件 |

#### ⑥ lawyer — 律师

| 维度 | 说明 |
|------|------|
| **角色标识** | `lawyer` |
| **典型用户** | 律所执业律师、企业法务顾问 |
| **职责** | 日常法律业务执行 |
| **权限范围** | `scope:self` — 仅本人参与的案件/文档 |
| **可见菜单** | AI 对话、合同审查、案件管理（本人）、文档中心（本人）、尽调分析、知识库、案件协作群 |
| **特殊权限** | 发起合同审查、创建案件、上传文档、加入案件协作群 |

#### ⑦ assistant — 律师助理/法务助理

| 维度 | 说明 |
|------|------|
| **角色标识** | `assistant` |
| **典型用户** | 实习律师、法务助理、行政秘书 |
| **职责** | 辅助律师完成事务性工作 |
| **权限范围** | `scope:self` — 仅被分配的任务和授权的文档 |
| **可见菜单** | AI 对话（受限）、文档中心（只读+上传）、知识库（只读）、任务列表 |
| **特殊权限** | 不能独立创建案件，需由律师或合伙人授权 |

#### ⑧ enterprise_user — 企业用户

| 维度 | 说明 |
|------|------|
| **角色标识** | `enterprise_user` |
| **典型用户** | 企业 HR、采购经理、业务部门负责人 |
| **职责** | 发起法律咨询、提交合同审查请求、查看案件进度 |
| **权限范围** | `scope:self` — 本人发起的咨询和案件 |
| **可见菜单** | AI 对话、合同审查（提交）、我的案件、找律师、匿名咨询、知识库（公开）、学院 |
| **特殊权限** | 发起匿名咨询、一键委托+签约、查看案件进度 |

#### ⑨ individual_user — 个人用户

| 维度 | 说明 |
|------|------|
| **角色标识** | `individual_user` |
| **典型用户** | C 端普通用户、个体经营者 |
| **职责** | 基础法律咨询、简单合同审查 |
| **权限范围** | `scope:self` — 仅本人数据 |
| **可见菜单** | AI 对话（基础）、找律师、匿名咨询、学院（免费课程） |
| **特殊权限** | 每日 AI 对话限额、匿名咨询、一键委托 |
| **限制** | 无法使用合同深度审查、尽调分析等高级功能（付费解锁） |

---

## 4. 功能权限矩阵

### 4.1 权限标记说明

| 标记 | 含义 |
|------|------|
| ● | 完全访问（读写删） |
| ◐ | 有限访问（仅读或部分写） |
| ○ | 无权限 |
| △ | 需审批/授权后可用 |
| ★ | 管理权限（含配置） |

### 4.2 核心功能权限矩阵

| 功能模块 | super_admin | platform_lawyer | org_admin | dept_admin | partner | lawyer | assistant | enterprise_user | individual_user |
|---------|:-----------:|:---------------:|:---------:|:----------:|:-------:|:------:|:---------:|:---------------:|:---------------:|
| **AI 对话** |
| 基础对话 | ● | ● | ● | ● | ● | ● | ◐ | ● | ◐ |
| 多轮深度分析 | ● | ● | ● | ● | ● | ● | ○ | ◐ | ○ |
| 多 Agent 协作 | ● | ● | ● | ● | ● | ● | ○ | ○ | ○ |
| LLM 模型配置 | ★ | ○ | ◐ | ○ | ○ | ○ | ○ | ○ | ○ |
| **合同审查** |
| 提交合同 | ● | ● | ● | ● | ● | ● | △ | ● | ○ |
| AI 风险分析 | ● | ● | ● | ● | ● | ● | ◐ | ◐ | ○ |
| 合同对比 | ● | ● | ● | ● | ● | ● | ◐ | ○ | ○ |
| 合同审批 | ● | ○ | ● | ● | ● | ○ | ○ | ○ | ○ |
| 合同签署 | ● | ● | ● | ● | ● | ● | ○ | ● | ○ |
| 合同模板管理 | ★ | ○ | ● | ◐ | ◐ | ○ | ○ | ○ | ○ |
| **案件管理** |
| 创建案件 | ● | ● | ● | ● | ● | ● | △ | ● | ○ |
| 查看全部案件 | ● | ○ | ● | ◐ | ◐ | ○ | ○ | ○ | ○ |
| 查看本人案件 | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| 分配案件 | ● | ○ | ● | ● | ● | ○ | ○ | ○ | ○ |
| 案件进度更新 | ● | ● | ● | ● | ● | ● | ◐ | ○ | ○ |
| 案件归档/删除 | ● | ○ | ● | ◐ | ◐ | ○ | ○ | ○ | ○ |
| **知识库** |
| 浏览公开知识 | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| 浏览组织知识 | ● | ○ | ● | ● | ● | ● | ◐ | ○ | ○ |
| 上传/编辑知识 | ● | ○ | ● | ● | ● | ● | ○ | ○ | ○ |
| 知识图谱管理 | ★ | ○ | ● | ○ | ○ | ○ | ○ | ○ | ○ |
| **管理后台** |
| 平台总览 | ★ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| 用户管理 | ★ | ○ | ◐ | ○ | ○ | ○ | ○ | ○ | ○ |
| 组织管理 | ★ | ○ | ● | ○ | ○ | ○ | ○ | ○ | ○ |
| 系统配置 | ★ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| 审计日志 | ★ | ○ | ◐ | ○ | ○ | ○ | ○ | ○ | ○ |
| 系统健康监控 | ★ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ |

### 4.3 找律师与交易功能权限矩阵

| 功能模块 | super_admin | platform_lawyer | org_admin | dept_admin | partner | lawyer | assistant | enterprise_user | individual_user |
|---------|:-----------:|:---------------:|:---------:|:----------:|:-------:|:------:|:---------:|:---------------:|:---------------:|
| **找律师** |
| 发起找律师 | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ● | ● |
| 接单大厅 | ○ | ● | ○ | ○ | ● | ● | ○ | ○ | ○ |
| 匿名咨询 | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ● | ● |
| 查看脱敏案情 | ○ | ● | ○ | ○ | ● | ● | ○ | ○ | ○ |
| 一键委托+签约 | ○ | ● | ○ | ○ | ○ | ○ | ○ | ● | ● |
| **案件协作群** |
| 创建协作群 | ● | ● | ● | ● | ● | ● | ○ | ○ | ○ |
| 加入协作群 | ● | ● | ● | ● | ● | ● | △ | ● | ● |
| 群文件上传 | ● | ● | ● | ● | ● | ● | △ | ● | ○ |
| 群消息发送 | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| **审批流** |
| 发起审批 | ● | ○ | ● | ● | ● | ● | ○ | ○ | ○ |
| 审批处理 | ● | ○ | ● | ● | ● | ○ | ○ | ○ | ○ |
| 查看审批记录 | ● | ◐ | ● | ● | ● | ◐ | ○ | ○ | ○ |
| **支付/收款** |
| 发起支付 | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ● | ● |
| 收款管理 | ○ | ● | ◐ | ○ | ● | ● | ○ | ○ | ○ |
| 财务报表 | ★ | ○ | ● | ○ | ◐ | ○ | ○ | ○ | ○ |
| 平台佣金管理 | ★ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ |

---

## 5. 数据范围控制

### 5.1 四级数据范围

```
scope:global    ─ 平台全部数据（仅 super_admin）
  │
  └─ scope:tenant    ─ 本组织全部数据（org_admin）
       │
       └─ scope:department  ─ 本部门及下级部门数据（dept_admin, partner）
            │
            └─ scope:self   ─ 仅本人创建或被分配的数据（默认）
```

### 5.2 数据范围应用规则

| 数据类型 | super_admin | org_admin | dept_admin | partner | lawyer | assistant | enterprise_user | individual_user | platform_lawyer |
|---------|:-----------:|:---------:|:----------:|:-------:|:------:|:---------:|:---------------:|:---------------:|:---------------:|
| 案件 | 全局 | 租户 | 部门 | 部门 | 个人 | 个人(授权) | 个人 | 个人 | 个人(已接) |
| 合同 | 全局 | 租户 | 部门 | 部门 | 个人 | 个人(只读) | 个人 | — | 个人(已接) |
| 文档 | 全局 | 租户 | 部门 | 部门 | 个人 | 个人(授权) | 个人 | — | 个人(已接) |
| 用户信息 | 全局 | 租户 | 部门 | 部门 | — | — | — | — | — |
| 审计日志 | 全局 | 租户 | — | — | — | — | — | — | — |
| 知识库 | 全局 | 租户 | 部门 | 部门 | 个人+共享 | 只读 | 公开 | 公开 | 公开 |

### 5.3 文件分级制度

所有上传文件和文档按敏感等级分为四级：

| 分级 | 标识 | 说明 | 可见角色 |
|------|------|------|---------|
| 公开 | `public` | 知识库公共文章、法规文本、宣传材料 | 所有已登录用户 |
| 内部 | `internal` | 组织内部通知、标准模板、培训资料 | 本组织所有成员 |
| 机密 | `confidential` | 案件材料、合同文本、客户信息 | 案件参与人 + 直属上级 |
| 绝密 | `top_secret` | 高敏感诉讼材料、并购标的信息 | 仅明确授权人员 + partner + org_admin |

文件分级规则：

```python
# 自动分级策略
AUTO_CLASSIFICATION_RULES = {
    "top_secret": [
        "content contains 并购/收购/重组 AND case.sensitivity >= HIGH",
        "document_type == 'litigation_strategy'",
    ],
    "confidential": [
        "document_type IN ('contract', 'case_material', 'client_info')",
        "contains PII detected by PII scanner",
    ],
    "internal": [
        "uploaded_to organization knowledge base",
        "document_type IN ('template', 'internal_memo')",
    ],
    "public": [
        "published to public knowledge base",
        "document_type IN ('regulation', 'article')",
    ],
}
```

---

## 6. 匿名找律师隐私设计

### 6.1 四级信息披露模型

```
Level 0              Level 1              Level 2              Level 3
匿名咨询             意向沟通              正式委托              深度合作
────────►  用户主动选择 ►  签约确认 ►   双方约定 ►
```

#### Level 0 — 匿名咨询

| 项目 | 用户侧 | 律师侧 |
|------|--------|--------|
| **身份** | 匿名（系统生成化名，如"用户 A-3721"） | 律师公开信息（姓名、执业领域、评分） |
| **案情** | 用户填写案情描述 | 查看 **PII 脱敏后** 的案情摘要 |
| **联系方式** | 不暴露 | 不暴露个人联系方式，仅平台内沟通 |
| **沟通渠道** | 平台匿名消息通道 | 平台匿名消息通道 |

PII 自动脱敏规则（Level 0 生效）：

```
手机号:    138****5678     → 正则: 1[3-9]\d{9}
身份证:    310***********21 → 正则: \d{17}[\dXx]
姓名:      张**             → NER 识别 + 部分掩码
公司名:    **科技有限公司    → NER 识别 + 部分掩码
银行卡:    6222****8901     → 正则: \d{16,19}
地址:      **市**区****路   → NER 识别地址实体
邮箱:      z**@***.com      → 正则: [\w.-]+@[\w.-]+
```

#### Level 1 — 意向沟通

| 项目 | 变化 |
|------|------|
| **触发条件** | 用户主动点击"有意向沟通" |
| **用户选择披露** | 用户可自行选择揭示哪些信息：真实姓名、所在城市、行业领域 |
| **律师响应** | 律师可发送详细执业证信息、过往案例经验 |
| **沟通升级** | 开通一对一专属消息通道（仍在平台内） |
| **可撤回** | 用户可随时撤回已披露信息并退回 Level 0 |

#### Level 2 — 正式委托

| 项目 | 变化 |
|------|------|
| **触发条件** | 双方确认委托意向 + 电子签约 |
| **信息披露** | 双方互相公开完成签约所需的必要信息：真实姓名、联系方式、组织信息 |
| **数据权限** | 律师获得案件相关文档的读写权限 |
| **协作群** | 自动创建案件协作群 |
| **合规要求** | 签署电子委托合同、利益冲突检查 |

#### Level 3 — 深度合作

| 项目 | 变化 |
|------|------|
| **触发条件** | 双方在 Level 2 基础上约定扩大共享范围 |
| **信息披露** | 全部案件材料共享，包括历史文档、关联案件 |
| **数据权限** | 律师获得客户关联的所有相关文档访问权限 |
| **协作工具** | 开通文档协同编辑、语音/视频会议集成 |

### 6.2 隐私控制数据模型

```sql
-- 匿名咨询会话
CREATE TABLE anonymous_consultations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    alias_name      VARCHAR(50) NOT NULL,          -- 系统生成化名
    category        VARCHAR(50) NOT NULL,           -- 咨询类别
    raw_content     TEXT NOT NULL,                  -- 原始案情（加密存储）
    masked_content  TEXT NOT NULL,                  -- 脱敏后案情
    privacy_level   SMALLINT NOT NULL DEFAULT 0,    -- 0-3
    status          VARCHAR(20) NOT NULL DEFAULT 'open',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 信息披露记录（不可篡改审计链）
CREATE TABLE disclosure_records (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_id   UUID NOT NULL REFERENCES anonymous_consultations(id),
    from_user_id      UUID NOT NULL REFERENCES users(id),
    to_user_id        UUID NOT NULL REFERENCES users(id),
    disclosed_fields  JSONB NOT NULL,               -- {"real_name": true, "city": true}
    privacy_level     SMALLINT NOT NULL,             -- 披露发生时的级别
    is_revoked        BOOLEAN NOT NULL DEFAULT false,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at        TIMESTAMPTZ
);
```

### 6.3 PII 脱敏处理流程

```
用户输入案情描述
       │
       ▼
  ┌──────────┐
  │ PII 检测  │ ← NER 模型 + 正则引擎
  └────┬─────┘
       │ 检测到 PII 实体列表
       ▼
  ┌──────────────┐
  │ 脱敏规则引擎  │ ← 按实体类型选择掩码策略
  └────┬─────────┘
       │
       ├── 原文加密存储（AES-256-GCM） → anonymous_consultations.raw_content
       │
       └── 脱敏文本明文存储 → anonymous_consultations.masked_content
```

---

## 7. 前端实现方案

### 7.1 FeatureFlags 配置

```typescript
// src/config/feature-flags.ts

export type FeatureStatus = 'live' | 'dev' | 'planned' | 'restricted';

export interface FeatureFlag {
  key: string;
  name: string;
  status: FeatureStatus;
  requiredRoles: string[];         // 允许的角色列表
  requiredPermissions?: string[];  // 额外要求的权限 key
  minPlan?: 'free' | 'basic' | 'pro' | 'enterprise';  // 最低套餐
}

export const FEATURE_FLAGS: Record<string, FeatureFlag> = {
  // AI 法务
  'ai.chat.basic': {
    key: 'ai.chat.basic',
    name: 'AI 基础对话',
    status: 'live',
    requiredRoles: ['*'],
  },
  'ai.chat.multi_agent': {
    key: 'ai.chat.multi_agent',
    name: 'AI 多 Agent 协作',
    status: 'live',
    requiredRoles: [
      'super_admin', 'org_admin', 'dept_admin',
      'partner', 'lawyer', 'platform_lawyer',
    ],
  },
  'contract.review': {
    key: 'contract.review',
    name: '合同审查',
    status: 'live',
    requiredRoles: [
      'super_admin', 'org_admin', 'dept_admin',
      'partner', 'lawyer', 'platform_lawyer', 'enterprise_user',
    ],
  },
  'contract.compare': {
    key: 'contract.compare',
    name: '合同对比',
    status: 'live',
    requiredRoles: [
      'super_admin', 'org_admin', 'dept_admin',
      'partner', 'lawyer', 'platform_lawyer', 'assistant',
    ],
  },
  'find_lawyer': {
    key: 'find_lawyer',
    name: '找律师',
    status: 'live',
    requiredRoles: ['enterprise_user', 'individual_user'],
  },
  'order_hall': {
    key: 'order_hall',
    name: '接单大厅',
    status: 'live',
    requiredRoles: ['platform_lawyer', 'partner', 'lawyer'],
  },
  'anonymous_consult': {
    key: 'anonymous_consult',
    name: '匿名咨询',
    status: 'live',
    requiredRoles: ['enterprise_user', 'individual_user'],
  },
  'due_diligence': {
    key: 'due_diligence',
    name: '尽调分析',
    status: 'live',
    requiredRoles: [
      'super_admin', 'org_admin', 'dept_admin',
      'partner', 'lawyer', 'platform_lawyer',
    ],
    minPlan: 'pro',
  },
  'admin.panel': {
    key: 'admin.panel',
    name: '管理后台',
    status: 'live',
    requiredRoles: ['super_admin'],
  },
  'admin.org_manage': {
    key: 'admin.org_manage',
    name: '组织管理',
    status: 'live',
    requiredRoles: ['super_admin', 'org_admin'],
  },
  'approval.flow': {
    key: 'approval.flow',
    name: '审批流',
    status: 'live',
    requiredRoles: [
      'super_admin', 'org_admin', 'dept_admin', 'partner', 'lawyer',
    ],
  },
  'payment': {
    key: 'payment',
    name: '支付功能',
    status: 'dev',
    requiredRoles: ['enterprise_user', 'individual_user'],
  },
  'revenue': {
    key: 'revenue',
    name: '收款管理',
    status: 'dev',
    requiredRoles: ['platform_lawyer', 'partner', 'lawyer'],
  },
  'collaboration.realtime': {
    key: 'collaboration.realtime',
    name: '实时协同编辑',
    status: 'planned',
    requiredRoles: [
      'super_admin', 'org_admin', 'dept_admin',
      'partner', 'lawyer', 'platform_lawyer',
    ],
    minPlan: 'enterprise',
  },
};
```

### 7.2 权限检查 Hook

```typescript
// src/hooks/usePermission.ts

import { useMemo } from 'react';
import { useAppStore } from '@/lib/store';
import { FEATURE_FLAGS, FeatureStatus } from '@/config/feature-flags';

interface PermissionResult {
  allowed: boolean;
  status: FeatureStatus;
  reason?: 'no_role' | 'no_plan' | 'not_live' | 'no_permission';
}

export function usePermission(featureKey: string): PermissionResult {
  const user = useAppStore((s) => s.user);

  return useMemo(() => {
    const flag = FEATURE_FLAGS[featureKey];
    if (!flag) return { allowed: false, status: 'planned', reason: 'no_permission' };

    // 检查功能状态
    if (flag.status === 'planned') {
      return { allowed: false, status: 'planned', reason: 'not_live' };
    }

    // 检查角色
    const userRole = user?.role ?? 'anonymous';
    if (!flag.requiredRoles.includes('*') && !flag.requiredRoles.includes(userRole)) {
      return { allowed: false, status: flag.status, reason: 'no_role' };
    }

    return { allowed: true, status: flag.status };
  }, [featureKey, user?.role]);
}

export function useHasRole(...roles: string[]): boolean {
  const user = useAppStore((s) => s.user);
  return roles.includes(user?.role ?? '');
}
```

### 7.3 导航菜单动态渲染

```typescript
// src/config/navigation.ts

export interface NavItem {
  key: string;
  label: string;
  icon: string;
  path: string;
  featureKey: string;          // 对应 FEATURE_FLAGS 的 key
  children?: NavItem[];
  badge?: 'new' | 'beta' | 'soon';
}

export const NAV_ITEMS: NavItem[] = [
  // AI 法务
  {
    key: 'chat', label: 'AI 法务助手', icon: 'MessageSquare',
    path: '/chat', featureKey: 'ai.chat.basic',
  },
  {
    key: 'contract-review', label: '合同审查', icon: 'FileCheck',
    path: '/contract-review', featureKey: 'contract.review',
  },
  // 找律师（C 端）
  {
    key: 'find-lawyer', label: '找律师', icon: 'UserSearch',
    path: '/find-lawyer', featureKey: 'find_lawyer',
  },
  {
    key: 'anonymous', label: '匿名咨询', icon: 'Shield',
    path: '/anonymous-consult', featureKey: 'anonymous_consult',
  },
  // 接单大厅（律师端）
  {
    key: 'order-hall', label: '接单大厅', icon: 'Inbox',
    path: '/order-hall', featureKey: 'order_hall', badge: 'new',
  },
  // 智能协作
  {
    key: 'cases', label: '案件管理', icon: 'Briefcase',
    path: '/cases', featureKey: 'case.manage',
  },
  {
    key: 'documents', label: '文档中心', icon: 'FolderOpen',
    path: '/documents', featureKey: 'document.manage',
  },
  {
    key: 'approval', label: '审批中心', icon: 'CheckCircle',
    path: '/approvals', featureKey: 'approval.flow',
  },
  // 管理后台
  {
    key: 'admin', label: '管理后台', icon: 'Settings',
    path: '/admin', featureKey: 'admin.panel',
  },
];
```

渲染逻辑：

```tsx
// 在 Layout.tsx 中
function SidebarNav() {
  return (
    <nav>
      {NAV_ITEMS.map((item) => {
        const { allowed, status } = usePermission(item.featureKey);
        if (!allowed && status === 'planned') return null; // 规划中：隐藏
        if (!allowed) return null;                         // 无权限：隐藏

        return (
          <NavLink key={item.key} to={item.path}>
            <Icon name={item.icon} />
            <span>{item.label}</span>
            {status === 'dev' && <Badge variant="outline">开发中</Badge>}
            {item.badge === 'new' && <Badge>NEW</Badge>}
          </NavLink>
        );
      })}
    </nav>
  );
}
```

### 7.4 功能状态分级展示

| 状态 | UI 表现 | 用户交互 |
|------|---------|---------|
| `live` — 已上线 | 正常显示和交互 | 正常使用 |
| `dev` — 开发中 | 显示但带"开发中"标签，点击提示即将上线 | 禁用交互，显示预告 |
| `planned` — 规划中 | 不在菜单中显示 | 不可见 |
| `restricted` — 权限限制 | 显示但置灰，点击提示需要升级/申请权限 | 禁用交互，引导升级 |

---

## 8. 数据库模型

### 8.1 需要扩展的现有模型

当前 `User` 模型的 `role` 字段为单值字符串，需要扩展为多角色支持：

```sql
-- 1. 扩展 users 表
ALTER TABLE users
    ADD COLUMN dept_id         UUID REFERENCES departments(id),
    ADD COLUMN user_type       VARCHAR(20) NOT NULL DEFAULT 'individual',  -- individual/enterprise/lawyer/platform
    ADD COLUMN bar_license_no  VARCHAR(50),           -- 执业证号（律师角色）
    ADD COLUMN bar_verified    BOOLEAN DEFAULT false,  -- 执业证是否验证
    ADD COLUMN privacy_level   SMALLINT DEFAULT 0;     -- 当前隐私级别

-- 保留原 role 字段用于向后兼容，新系统读取 user_roles 表
```

### 8.2 新增核心权限表

```sql
-- 2. 角色定义表
CREATE TABLE roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        VARCHAR(50) UNIQUE NOT NULL,      -- super_admin, lawyer, etc.
    name        VARCHAR(100) NOT NULL,             -- 显示名称
    description TEXT,
    scope_level VARCHAR(20) NOT NULL DEFAULT 'self', -- global/tenant/department/self
    parent_id   UUID REFERENCES roles(id),           -- 角色继承
    is_system   BOOLEAN NOT NULL DEFAULT false,       -- 系统内置角色不可删除
    org_id      UUID REFERENCES organizations(id),    -- NULL 表示平台级角色
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. 权限定义表
CREATE TABLE permissions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        VARCHAR(100) UNIQUE NOT NULL,   -- 如 case.create, contract.review
    name        VARCHAR(200) NOT NULL,
    module      VARCHAR(50) NOT NULL,           -- 所属模块
    action      VARCHAR(20) NOT NULL,           -- create/read/update/delete/manage
    description TEXT,
    is_system   BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. 角色-权限关联表
CREATE TABLE role_permissions (
    role_id       UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    granted_by    UUID REFERENCES users(id),
    PRIMARY KEY (role_id, permission_id)
);

-- 5. 用户-角色关联表（支持多角色）
CREATE TABLE user_roles (
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id    UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    org_id     UUID REFERENCES organizations(id),    -- 角色在哪个组织生效
    dept_id    UUID REFERENCES departments(id),      -- 角色在哪个部门生效
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    granted_by UUID REFERENCES users(id),
    expires_at TIMESTAMPTZ,                          -- 临时授权过期时间
    PRIMARY KEY (user_id, role_id, COALESCE(org_id, '00000000-0000-0000-0000-000000000000'))
);

-- 6. 部门表
CREATE TABLE departments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name        VARCHAR(200) NOT NULL,
    parent_id   UUID REFERENCES departments(id),   -- 支持多级部门
    sort_order  INT DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(org_id, name, parent_id)
);

-- 7. 数据范围规则表（ABAC 策略存储）
CREATE TABLE data_scope_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    resource_type   VARCHAR(50) NOT NULL,     -- case/contract/document/knowledge
    scope_type      VARCHAR(20) NOT NULL,     -- global/tenant/department/self
    conditions      JSONB,                    -- ABAC 条件表达式
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 核心索引
CREATE INDEX idx_user_roles_user     ON user_roles(user_id);
CREATE INDEX idx_user_roles_role     ON user_roles(role_id);
CREATE INDEX idx_user_roles_org      ON user_roles(org_id);
CREATE INDEX idx_role_perms_role     ON role_permissions(role_id);
CREATE INDEX idx_departments_org     ON departments(org_id);
CREATE INDEX idx_departments_parent  ON departments(parent_id);
CREATE INDEX idx_data_scope_role     ON data_scope_rules(role_id);
```

### 8.3 初始角色种子数据

```sql
INSERT INTO roles (code, name, description, scope_level, is_system) VALUES
('super_admin',     '平台超级管理员', '平台全局运维与管理',          'global',     true),
('platform_lawyer', '平台签约律师',   '与平台签约的独立执业律师',    'self',       true),
('org_admin',       '组织管理员',     '组织内部管理与配置',          'tenant',     true),
('dept_admin',      '部门管理员',     '部门级管理',                 'department', true),
('partner',         '合伙人',         '律所高级合伙人',             'department', true),
('lawyer',          '律师',           '执业律师',                   'self',       true),
('assistant',       '律师助理',       '律师/法务助理',              'self',       true),
('enterprise_user', '企业用户',       '企业端法律服务使用者',        'self',       true),
('individual_user', '个人用户',       'C端普通用户',                'self',       true);
```

---

## 9. API 鉴权流程

### 9.1 请求鉴权链路

```
HTTP Request
  │
  ▼
① JWT Token 验证（现有 get_current_user_required）
  │
  ▼
② Token 黑名单检查（现有 verify_token_with_blacklist）
  │
  ▼
③ 加载用户角色列表（新增 → user_roles 表查询）
  │
  ▼
④ 权限检查（新增 → 功能权限匹配）
  │
  ▼
⑤ 数据范围过滤（新增 → SQL WHERE 条件注入）
  │
  ▼
⑥ ABAC 属性校验（新增 → 动态条件评估）
  │
  ▼
  允许/拒绝
```

### 9.2 后端权限装饰器设计

```python
# src/core/permissions.py

from functools import wraps
from fastapi import HTTPException, status

def require_permission(*permissions: str):
    """
    路由级权限检查装饰器。

    用法:
        @router.get("/cases")
        @require_permission("case.read")
        async def list_cases(user = Depends(get_current_user_required)):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('user') or kwargs.get('current_user')
            if not user:
                raise HTTPException(status_code=401, detail="未认证")

            user_permissions = await load_user_permissions(user.id)
            for perm in permissions:
                if perm not in user_permissions:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"缺少权限: {perm}"
                    )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(*roles: str):
    """角色级检查装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('user') or kwargs.get('current_user')
            if not user:
                raise HTTPException(status_code=401, detail="未认证")

            user_roles = await load_user_roles(user.id)
            if not any(r in user_roles for r in roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="角色权限不足"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### 9.3 数据范围 SQL 过滤

```python
# src/core/data_scope.py

from sqlalchemy import and_, or_

async def apply_data_scope(query, user, resource_type: str):
    """
    根据用户角色的数据范围自动注入 WHERE 条件。
    """
    scope = await get_user_scope(user.id, resource_type)

    if scope == 'global':
        return query  # 不加过滤

    if scope == 'tenant':
        return query.where(resource_model.org_id == user.org_id)

    if scope == 'department':
        dept_ids = await get_department_tree(user.dept_id)
        return query.where(
            or_(
                resource_model.dept_id.in_(dept_ids),
                resource_model.created_by == user.id,
            )
        )

    # scope == 'self'
    return query.where(
        or_(
            resource_model.created_by == user.id,
            resource_model.assignee_id == user.id,
        )
    )
```

---

## 10. 审计与合规

### 10.1 权限相关审计事件

以下操作必须记录到 `audit_logs` 表：

| 事件类型 | 说明 | 保留期限 |
|---------|------|---------|
| `role.assign` | 角色分配 | 3 年 |
| `role.revoke` | 角色撤销 | 3 年 |
| `permission.grant` | 权限授予 | 3 年 |
| `permission.deny` | 权限拒绝（被拦截的访问尝试） | 1 年 |
| `data_scope.override` | 数据范围临时调整 | 3 年 |
| `privacy.level_change` | 匿名咨询隐私级别变更 | 5 年 |
| `pii.disclosure` | PII 信息披露操作 | 5 年 |
| `doc.classification_change` | 文件密级变更 | 3 年 |

### 10.2 合规要求

- 所有权限变更操作需要二次确认（敏感操作需 MFA）
- 超级管理员操作需要记录操作理由
- 定期权限审查：每季度由 `org_admin` 确认成员权限是否合理
- 离职用户立即冻结账号并撤销所有活跃 Token
- 符合《个人信息保护法》和《数据安全法》相关要求

---

## 附录 A：角色迁移方案

从当前简单 `role` 字段迁移到新 RBAC 体系的步骤：

| 步骤 | 操作 | 影响 |
|------|------|------|
| 1 | 创建 `roles`、`permissions`、`user_roles` 等新表 | 无影响，新增表 |
| 2 | 插入系统内置角色和权限种子数据 | 无影响 |
| 3 | 编写迁移脚本：根据 `users.role` 值写入 `user_roles` | `admin` → `org_admin`，`member` → `lawyer`，`viewer` → `assistant` |
| 4 | 新增 `get_user_permissions()` 函数，优先读 `user_roles` 表 | 兼容旧逻辑 |
| 5 | 前端接入 `usePermission` Hook，逐模块切换 | 灰度上线 |
| 6 | 稳定运行 2 周后，废弃 `users.role` 字段 | 清理旧代码 |

## 附录 B：权限码编码规范

格式：`{module}.{resource}.{action}`

```
案件模块:     case.create / case.read / case.update / case.delete / case.assign
合同模块:     contract.submit / contract.review / contract.approve / contract.sign
文档模块:     document.upload / document.read / document.update / document.delete
知识库:       knowledge.read / knowledge.write / knowledge.manage
管理后台:     admin.user.manage / admin.org.manage / admin.config / admin.audit.read
找律师:       lawyer.find / lawyer.order_hall / lawyer.accept
匿名咨询:    consult.anonymous.create / consult.anonymous.respond
审批流:       approval.create / approval.process / approval.view
支付:         payment.create / payment.receive / payment.report
```
