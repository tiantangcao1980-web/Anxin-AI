# SSO / SAML / OAuth 接入

> 关联：[docs/v3/enterprise-cluster-design.md §5](../../docs/v3/enterprise-cluster-design.md) ·
> [LDAP_SYNC.md](./LDAP_SYNC.md)

## 当前支持

| 协议 | 状态 | 备注 |
|---|---|---|
| **本地账号 + 密码** | ✅ 内置 | 默认 |
| **LDAP / AD bind** | ✅ 见 LDAP_SYNC | 同步用户 + 自带 bind 登录 |
| **OAuth2（微信 / 支付宝）** | ✅ 内置 | SaaS / 公网客户用 |
| **SAML 2.0** | 🚧 P3 | 计划接入 |
| **OIDC** | 🚧 P3 | |
| **飞书 / 钉钉 / 企业微信 单点** | 🚧 P3 | 通讯录 + 单点 |
| **CAS** | 🚧 P4 | 高校 / 政企历史栈 |

## 接入约定

无论哪种 SSO，**身份必须最终映射到本地 `users` 表**（不直接信任 IdP 声明的 role）。

1. **IdP 声明**：`subject` / `email` / `groups[]`
2. 系统侧：用 `email` 找到 / 自动创建 `users` 行（`login_type=saml` 或 `oidc`）
3. **角色 / 权限不从 IdP 取**，由 `role_bindings` 决定 —— IdP 只证明"你是谁"，不证明"你能干什么"
4. 退出 / 撤销：本地标记 `is_active=false` 立即生效（不依赖 IdP token 过期）

## P3 SAML 设计要点（待实施）

- 库：[python3-saml](https://github.com/SAML-Toolkits/python3-saml)
- 端点：`/api/v1/auth/saml/login` · `/api/v1/auth/saml/acs` · `/api/v1/auth/saml/metadata`
- 证书放 `deploy/enterprise-onprem/certs/saml/`
- 配置走 `SAML_*` 环境变量或 yaml 文件
- SP 元数据自动生成，IdP 元数据上传
- 时钟偏移 ±5 min
- AssertionConsumerService 必须 HTTPS

## P3 飞书 / 钉钉 单点

- 飞书：[App H5 单点登录](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/sso-h5-redirect-login)
- 钉钉：扫码登录 + 通讯录同步
- 单点登录后立刻同步当次会话的组织架构变更（增量）

## 暂未支持的请求

请提工单时附：

- IdP 类型 / 版本
- 元数据 XML 样例（脱敏）
- 必需的属性映射
- 是否需要 SLO（单点登出）
