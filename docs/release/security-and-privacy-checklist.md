# 安全与隐私发布清单

> 日期：2026-05-07
> 判定：发布前必须逐项复核。当前有若干项仍未达到 Go 条件。

## 1. 认证与会话

| 检查项 | 当前状态 | 发布要求 |
|---|---|---|
| access token 不长期存 localStorage | Web 源码已改为内存 access token | 移动/桌面策略仍需审计 |
| refresh token HttpOnly cookie | 已完成 Web 主路径，body compat 默认关闭 | 发布前确认旧客户端迁移窗口 |
| reset token 只存 hash | 已完成 | 继续保留 IP/UA/过期审计 |
| Redis 敏感入口 fail-closed | 认证限流和 refresh blacklist 已覆盖 | session/CAPTCHA 仍需补全审计 |
| 小程序登录 | `wx.login -> code2session -> JWT`，不下发 `session_key` | 需要真机/测试环境 7 天验证 |

## 2. 权限与租户隔离

- LLM 配置必须按组织隔离，superuser 例外必须有测试。
- 文档、合同、附件、知识库、订阅、IM conversation 必须按 org/user/client_type 隔离。
- 律师市场、案件、任务、风险调查仍需逐模块 P0 权限矩阵。
- A2UI/action 必须带鉴权上下文，未知组件/事件不能白屏。

## 3. 支付、电签与 webhook

- 所有官方 webhook 必须验签和校验时间窗。
- `webhook_received` 必须以官方 event id / notify id 做幂等。
- 失败事件必须进入 failed/retry，不允许假 success。
- 支付和电签真实沙箱未完成前，不允许标记商业 Go。
- 密钥包括 `WECHAT_PAY_*`、`ALIPAY_*`、`ESIGN_BAO_*`、`FADADA_*`，必须完成轮换演练。

## 4. 数据与文件

- 上传入口必须校验扩展名、MIME、大小和 magic number。
- 对象存储 key 不允许 path traversal。
- 下载 URL 必须有过期时间和权限校验。
- 合同已签/归档状态必须双写审计并可追溯 provider event。
- 历史 `file_path -> object_key` 迁移必须有备份和 downgrade。

## 5. 隐私与日志

- 不在日志中输出 access/refresh token、session key、支付私钥、电签 app secret。
- 生产日志中手机号、身份证号、统一社会信用代码、银行卡/订单敏感字段需要脱敏。
- `docs/release/evidence/` 中保存的沙箱日志、回调摘录和 JSON 证据必须先通过 `scripts/release-evidence-secret-scan.sh`，不得包含明文密钥、access/refresh token、手机号或身份证号。
- RAG/尽调缓存必须带 org namespace，不能跨组织复用。
- 外部抓取必须遵守 robots、UA、频控和法定数据源白名单。

## 6. 发布前必须完成

- `docs/audit/00-platform/04-ci-security-scan.md` 中 CI/security scan 待确认项需要落地或形成豁免。
- 前端生产依赖 `cd frontend && npm audit --omit=dev --json` 已清零并保存到 `docs/release/evidence/artifacts/frontend-npm-audit-prod-20260507.json`；当前采用补丁级升级和定向 overrides，避免将 `picomatch` v2 链全局强升到 v4。
- 移动端 `cd mobile && npm audit --omit=dev` 已清零；当前通过 `@xmldom/xmldom@0.8.13`、`@expo/cli -> tar@7.5.14`、`@expo/metro-config -> postcss@8.5.14`、`cacache -> tar@7.5.14` 定向 overrides 修复。`tar@7.5.14` 跨过 Expo CLI 声明的 semver 范围，后续 Expo SDK/package 改动必须保留 `npx expo-doctor`、`npx expo install --check` 和真机 smoke。
- 全仓 secret scan/gitleaks 至少跑一次，并保存结果。
- 发布证据目录脱敏扫描 `bash scripts/release-evidence-secret-scan.sh` 必须通过，并纳入 `scripts/commercial-readiness-gate.sh`。
- 全仓 `rg` 检查 mock/fallback/token 泄露关键字。
- 生产密钥轮换 SOP 演练一次，更新 `docs/audit/00-platform/02-secret-rotation-sop.md`。
- 安全审计 owner 对 P0 未闭合项签字。
