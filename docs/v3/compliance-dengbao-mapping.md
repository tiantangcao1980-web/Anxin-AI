# 等保 2.0 三级 + GB/T 35273-2020 对照清单

> 适用对象：信息安全审核、私有化客户安全评估
> 文档版本：v1（2026-05-14）
> 关联：[security-whitepaper.md](./security-whitepaper.md) · [skills-sandbox-design.md](./skills-sandbox-design.md) · [enterprise-cluster-design.md](./enterprise-cluster-design.md)

## 一、说明

本清单按 **GB/T 22239-2019《信息安全技术 网络安全等级保护基本要求》三级** 的章节顺序逐项对照，给出本平台的**实装位置 + 状态**。

状态符号：
- ✅ **已实装**：代码已合入，可演示
- 🔄 **建设中**：设计已就绪，开发中
- ⚪ **客户配合**：依赖客户运维（如机房物理安全）

## 二、安全通用要求

### 8.1 安全物理环境

| 控制项 | 实装 | 状态 |
|---|---|---|
| 8.1.1 物理位置选择 | ⚪ 私有化部署，客户机房 | ⚪ |
| 8.1.2 物理访问控制 | ⚪ 客户机房门禁 | ⚪ |
| 8.1.3-8.1.5 防盗 / 防火 / 防水 | ⚪ 客户机房 | ⚪ |
| 8.1.6 防静电 / 温湿度 | ⚪ 客户机房 | ⚪ |
| 8.1.7 电力供应 | ⚪ 客户机房 UPS | ⚪ |
| 8.1.8 电磁防护 | ⚪ 客户机房 | ⚪ |

### 8.2 安全通信网络

| 控制项 | 实装 | 状态 |
|---|---|---|
| 8.2.1 网络架构 | 后端 + worker + DB + Redis 分层；NetworkPolicy default-deny；[helm chart](../../deploy/enterprise-onprem/helm/anxin-enterprise/) | ✅ |
| 8.2.2 通信传输 | 全站 TLS 1.2+，nginx 强制 HTTPS | ✅ |
| 8.2.3 可信验证 | 跨服务调用 JWT + Bearer + jti 黑名单 | ✅ |

### 8.3 安全区域边界

| 控制项 | 实装 | 状态 |
|---|---|---|
| 8.3.1 边界防护 | nginx 仅暴露 80/443；K8s NetworkPolicy；[networkpolicy.yaml](../../deploy/enterprise-onprem/helm/anxin-enterprise/templates/networkpolicy.yaml) | ✅ |
| 8.3.2 访问控制 | 六层闸门（订阅/角色/权限/风险/隐私/设备）；[security-whitepaper §三](./security-whitepaper.md) | ✅ |
| 8.3.3 入侵防范 | rate_limit + CAPTCHA + WAF（nginx 配置） | ✅ |
| 8.3.4 恶意代码防范 | Skill 沙箱五分层 + ed25519 签名；[skills-sandbox-design.md](./skills-sandbox-design.md) | ✅ |
| 8.3.5 安全审计 | 全量 audit_log + Prometheus 指标 | ✅ |

### 8.4 安全计算环境

| 控制项 | 实装 | 状态 |
|---|---|---|
| 8.4.1 身份鉴别 | JWT + Redis 黑名单 + 密码策略最小 8 字符 + Argon2id | ✅ |
| 8.4.1.b 多因子 | 邮箱验证码 + 短信（已实装）；TOTP 计划中 | 🔄 |
| 8.4.2 访问控制 | RBAC + 部门继承 + role_bindings；[enterprise-cluster-design.md](./enterprise-cluster-design.md) | ✅ |
| 8.4.3 安全审计 | audit_log 表 + 不可篡改 WAL 归档 | ✅ |
| 8.4.4 入侵防范 | 镜像漏洞扫描 + cryptography 高危 CVE 跟踪 | ✅ |
| 8.4.5 恶意代码防范 | Skill 沙箱 T3 默认 + 容器 read-only + cap-drop ALL | ✅ |
| 8.4.6 可信验证 | T1 Skill 必须 ed25519 签名 | ✅ |
| 8.4.7 数据完整性 | TLS + 数据库 checksums + WAL | ✅ |
| 8.4.8 数据保密性 | TLS + 静态加密（pg）+ 字段级（敏感字段） | ✅ |
| 8.4.9 数据备份恢复 | [BACKUP.md](../../deploy/enterprise-onprem/BACKUP.md) pg_dump 模板 + 异地副本 | ✅ |
| 8.4.10 剩余信息保护 | 容器 ephemeral + workdir 强制清理（terminate 幂等） | ✅ |
| 8.4.11 个人信息保护 | GB/T 35273 五级分类；DSAR 端点 [privacy.py](../../backend/src/api/routes/privacy.py) | ✅ |

### 8.5 安全管理中心

| 控制项 | 实装 | 状态 |
|---|---|---|
| 8.5.1 系统管理 | Admin 后台 17+ 个管理页；[AdminEnterprise.tsx](../../frontend/src/pages/admin/AdminEnterprise.tsx) | ✅ |
| 8.5.2 审计管理 | audit_log 查询 + Grafana 看板 | ✅ |
| 8.5.3 安全管理 | super_admin 权限 + 双人审批（高风险操作） | ✅ |
| 8.5.4 集中管控 | K8s + Prometheus 多集群标签；可对接客户 SOC | ✅ |

### 8.6 安全管理制度 / 机构 / 人员

—— 客户自行制定，本平台提供技术支撑（审批流、审计、培训材料）。

### 8.7 安全建设管理

| 控制项 | 实装 | 状态 |
|---|---|---|
| 8.7.1 定级 | 三级 | ✅ |
| 8.7.2 备案 | 客户负责 | ⚪ |
| 8.7.3 安全方案设计 | 本文档 + security-whitepaper.md | ✅ |
| 8.7.4 产品采购使用 | 全量开源 + 商用授权 | ✅ |
| 8.7.5 自行软件开发 | TDD + 单测覆盖 180+ tests | ✅ |
| 8.7.6 外包软件开发 | 不外包 | ✅ |
| 8.7.7 工程实施 | 私有化标准 SOW；on-prem 部署手册 | ✅ |
| 8.7.8 测试验收 | 渗透测试报告（季度）+ 第三方代码审计 | 🔄 |
| 8.7.9 系统交付 | 完整文档 + 培训 + 7×24 一线支持 | ✅ |
| 8.7.10 等级测评 | 客户自行委托测评机构 | ⚪ |
| 8.7.11 服务供应商 | 不涉及 | ⚪ |

### 8.8 安全运维管理

—— 客户自行制定运维 SOP；本平台提供：

- Grafana 看板模板
- 告警规则模板
- 备份脚本模板（[BACKUP.md](../../deploy/enterprise-onprem/BACKUP.md)）
- 应急响应手册（[security-whitepaper.md §十一](./security-whitepaper.md)）

## 三、GB/T 35273-2020《个人信息安全规范》

| 章节 | 要求 | 实装 | 状态 |
|---|---|---|---|
| 5.2 收集 | 最小必要原则 | 表单仅收集业务必要字段；用户可拒绝 | ✅ |
| 5.3 收集同意 | 明示授权 | 注册页 + Skill 安装弹窗双重同意 | ✅ |
| 5.5 个人敏感信息 | 单独同意 + 加密 | DataClassification 字段级加密 | ✅ |
| 6.1 存储期限 | 最短必要 | 数据保留策略；audit_log ≥ 180 天 | ✅ |
| 6.3 去标识化 | 必要时去标识 | 跨境 / 共享场景默认脱敏 | ✅ |
| 7.2 使用限制 | 不超原同意范围 | 权限闸门强制 | ✅ |
| 7.3 委托处理 | 协议约定 + 监督 | SOW 模板 | ✅ |
| 7.5 共享 / 转让 | 单独同意 + 评估 | 默认禁用，开启需 super_admin 审批 | ✅ |
| 7.6 公开披露 | 单独同意 | 默认禁用 | ✅ |
| 8.1 通知 | 告知用户 | 站内信 + 邮件 + 隐私政策更新提前 30 天 | ✅ |
| 8.2 查询权 | 提供查询 | `GET /api/v1/privacy/me/data` | ✅ |
| 8.3 更正权 | 提供更正 | `PATCH /api/v1/auth/me` | ✅ |
| 8.4 删除权 | 提供删除 | `DELETE /api/v1/privacy/me/data` | ✅ |
| 8.5 撤回同意权 | 提供撤回 | 用户中心 + DSAR 邮箱 | ✅ |
| 8.6 注销账户 | 提供注销 | `DELETE /api/v1/auth/me` | ✅ |
| 8.7 数据可携带权 | 结构化导出 | DSAR 导出 JSON / CSV | ✅ |
| 9.1 安全事件管理 | 应急响应 | [security-whitepaper §十一](./security-whitepaper.md) | ✅ |
| 9.2 影响评估 | DPIA | 隐私影响评估模板 | ✅ |

## 四、GDPR / CCPA 跨境

| 要求 | 实装 |
|---|---|
| 数据访问权（Art. 15 / CCPA §1798.100） | DSAR 端点 |
| 更正权（Art. 16） | 用户中心 |
| 被遗忘权（Art. 17 / CCPA §1798.105） | DSAR 端点 + 软删后 90 天物理清除 |
| 限制处理权（Art. 18） | 账户冻结 + Skill 沙箱拒新执行 |
| 数据可携带权（Art. 20） | DSAR 导出 |
| 反对权（Art. 21） | 选择退出营销 |
| 自动决策 / Profiling 拒绝权（Art. 22 / CCPA） | AI 输出非最终决策声明 |
| 跨境传输（SCC / 标准合同条款） | 私有化客户数据不出境 |

## 五、关键不足与改进路线

| 不足 | 计划 | 负责人 |
|---|---|---|
| 8.4.1.b 多因子 TOTP 尚未实装 | 2026 Q3 完成 | Backend |
| 8.7.8 渗透测试季度未启动 | 2026 Q3 第一次 | Security |
| ISO 27001 体系认证 | 2026 Q4 完成 | Compliance |
| 飞书 / 钉钉 / 企微 SSO 单点（非通讯录） | 2027 Q1 | Backend |

---

**附录 · 落地文件清单**

| 类别 | 文件 |
|---|---|
| 权限模型 | [enterprise-cluster-design.md](./enterprise-cluster-design.md) |
| 沙箱设计 | [skills-sandbox-design.md](./skills-sandbox-design.md) |
| 安全审计 | [security-audit.md](./security-audit.md) |
| 备份恢复 | [BACKUP.md](../../deploy/enterprise-onprem/BACKUP.md) |
| AirGap 部署 | [AIRGAP.md](../../deploy/enterprise-onprem/AIRGAP.md) |
| LDAP 同步 | [LDAP_SYNC.md](../../deploy/enterprise-onprem/LDAP_SYNC.md) |
| 可观测性 | [observability-deploy.md](./observability-deploy.md) |
