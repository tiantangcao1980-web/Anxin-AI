# 安全策略

## 报告漏洞

如发现安全漏洞，**不要在 GitHub 公开 issue 中讨论**。

**报告方式**：

- 邮件：security@anxin.example（待配置）
- 飞书私信项目安全负责人

收到报告后 48 小时内回应。

## 报告内容

请包含：

1. 漏洞类型（OWASP 分类）
2. 受影响组件 / 端点 / 路径
3. 复现步骤
4. 影响范围（数据 / 用户 / 系统）
5. 建议修复方案（如有）

## 处理流程

| 阶段 | 时长 | 动作 |
|---|---|---|
| 受理 | 48h | 确认收到并启动评估 |
| 评估 | 1 周 | 验证 + 风险定级 |
| 修复 | 视严重程度 | P0 立即；P1 ≤ 7 天；P2 ≤ 30 天 |
| 披露 | 修复后 30 天 | 必要时发布安全公告 |

## 已加固的安全面（V2 + V3 主线）

参见 [docs/audit/00-platform/02-secret-rotation-sop.md](docs/audit/00-platform/02-secret-rotation-sop.md) 与 [docs/v3/security-audit.md](docs/v3/security-audit.md)。

主要收口：

- ✅ JWT access token 内存化 + refresh HttpOnly Cookie
- ✅ CAPTCHA 覆盖登录 / 注册 / 忘密
- ✅ Redis fail-closed
- ✅ LLM 配置组织隔离
- ✅ /pro 服务方端守卫 + ModeGate / PrivacyContext fail-closed
- ✅ 对象存储 access_level + 上传校验统一
- ✅ 合同 webhook 验签（微信 v3 / 支付宝 RSA2 / e签宝 HMAC / 法大大 FASC）
- ✅ IM WebSocket 首包鉴权
- ✅ OAuth token KMS 加密存储
- ✅ Local 模式 fail-closed 默认拒绝出站

## 安全发布门禁

发布前必跑：

```bash
bash scripts/release-evidence-secret-scan.sh        # 密钥扫描
bash scripts/desktop-sqlite-security-gate.sh        # 桌面 SQLCipher
bash scripts/commercial-readiness-gate.sh --quick   # 商业门禁
```

详见 [docs/release/security-and-privacy-checklist.md](docs/release/security-and-privacy-checklist.md)。

## 智能体治理（V3 新增）

V3 引入企业智能体治理（L0-L5 风险分级 + 六层校验）：

`subscription + role + permission + risk_level + privacy_mode + device_trust`

任何能力调用前必须六层校验通过。详见 [docs/openspec/00-intelligent-assistant-platform-spec.md §3.7-3.8](docs/openspec/00-intelligent-assistant-platform-spec.md)。

## 合规

- 《人工智能生成合成内容标识办法》（2025.9.1 施行）合规已实施
- GB 45438-2025 AI 内容标识
- 《生成式人工智能服务管理暂行办法》备案

## 第三方依赖

- 后端：`safety check` / `pip-audit`
- 前端：`npm audit --omit=dev`
- 移动：`npm audit --omit=dev`
- 桌面：`cargo audit`

CI 每日跑一次依赖扫描，CVE 严重等级及以上自动开 issue。
