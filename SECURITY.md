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

## 残留 CVE 清单（2026-05-15 快照）

下列告警**经评估为非阻塞**，已加固到不直接暴露生产代码路径。每次发布前需 review 一次。

### 后端（Python）

| 包 | CVE / GHSA | 上游约束 | 缓解措施 |
|---|---|---|---|
| `litellm` | GHSA-xqmj-j6mv-4862 | 受 `camel-ai` 上游联合锁，所有可用版本均 ≤1.83.6 | 已在 `pyproject.toml` 注释中标记；不暴露用户可控输入路径 |
| `lxml` 5.x | CVE-2026-41066 | 受 `crawl4ai (<0.7)` 上限锁 lxml<6 | FetchService 仅消费内部受信源；用户输入走 selectolax 解析 |
| `pillow` 10.x | CVE-2026-25990 / 40192 | 受 `crawl4ai` 上限锁 pillow<11 | 仅内部图像处理用，不接收用户上传到该路径 |

详见 [docs/v3/P16_DEPENDENCY_UPGRADE.md](docs/v3/P16_DEPENDENCY_UPGRADE.md)。

### 移动端（Expo SDK 52）

剩余 10 项 moderate 全在 Expo CLI / Metro 工具链（`@expo/cli`、`@expo/metro-config`、`@expo/plist` 等），**仅构建期使用，不进入 RN 设备 bundle**。下一步：跟随 Expo SDK 53/54/55 滚动升级清零。

关键 high 已通过 `package.json` overrides 修复：

```json
"overrides": {
  "@babel/plugin-transform-modules-systemjs": "^7.29.4",
  "@xmldom/xmldom": "^0.9.10",
  "fast-uri": "^3.1.2",
  "tar": "^7.5.15"
}
```

### 小程序（Taro 4.2）

**prod-only critical/high 已清零**。

| 残留 | 严重 | 说明 |
|---|---|---|
| `esbuild` <0.25 dev server bind | moderate | 仅本地 dev 暴露；`taro build --type weapp` 不依赖 |
| `webpack` AutoPublicPathRuntimeModule DOM clobbering | moderate | dev-only 体现；prod chunk 已经 hash 化 |
| `webpack-dev-server` source code leak | moderate | dev-only |
| 其余 13 项 moderate | moderate | 均为 `@tarojs/*` 间接 dev 依赖，待 Taro 4.x patch 滚动消化 |

关键 critical 已通过 overrides 修复：

```json
"overrides": {
  "webpack": "5.89.0",
  "swiper": "^12.1.2",
  "lodash-es": "^4.17.23"
}
```

### 后端 hash 用法复核

- 11 处 `hashlib.md5` 用作 cache key / point_id 等**非密码学场景**，可接受。
- ⚠ [esign_service.py:439](backend/src/services/esign_service.py:439) `hashlib.md5(body).digest()` 用于电子签 body 摘要 — 请确认是否为第三方平台（如 e-签宝旧版 ESL）API 强制要求；如可替换建议改为 SHA-256。

### Tauri CSP

`desktop/tauri.conf.json` CSP 仍指向旧域名 `*.anxin-legal.com`，需要随 `anxinai.com` 域名切换同步更新（P13 计划项）。
