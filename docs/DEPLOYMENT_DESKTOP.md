# 安心法务桌面端发版指南（macOS · Windows · Linux）

本文是桌面端代码签名、公证、自动更新、CI 发版的完整 runbook，
对齐 Tauri v2 官方推荐流程与中国大陆出海合规要求。

> 每次发版前完整按 **「一次性准备」→ 「每版本操作」→ 「验证」** 执行。

---

## 0. 交付门槛（硬指标）

| 指标 | 商业要求 |
|---|---|
| 代码签名 | macOS Developer ID 签名 + Apple Notarization；Windows EV/OV 代码签名证书 |
| 自动更新 | Tauri Updater 签名公私钥对，签名 manifest；后端 `/api/v1/updates/{target}/{arch}/{version}` 提供最新版信息 |
| 平台覆盖 | macOS arm64+x86_64 / Windows x64 / Linux x64 (deb+AppImage) |
| 发版流水线 | GitHub Actions tag-driven，产物签名后自动上传 release + 生成 `latest.json` |
| 回滚策略 | 上一稳定版保留至少 90 天；updater 支持指定 min_version 禁更 |

---

## 1. 一次性准备

### 1.1 申请代码签名证书

#### macOS（Apple Developer Program）

1. 登录 https://developer.apple.com 加入 Developer Program（$99/年）
2. 证书页创建：
   - **Developer ID Application**（用于 DMG 安装包 / `.app` bundle 签名）
   - **Developer ID Installer**（可选，如果分发 `.pkg`）
3. 下载 `.cer` → 双击导入钥匙串 → **导出为 `.p12`（带密码）**
4. 记录：
   - `APPLE_SIGNING_IDENTITY`：`Developer ID Application: 您的公司名称 (TEAMID)`
   - `APPLE_TEAM_ID`：10 位团队 ID
   - `APPLE_ID` + `APPLE_APP_SPECIFIC_PASSWORD`（AppleID 后台生成 app 专用密码，用于 notarization）

#### Windows（EV/OV 证书）

1. 向 **DigiCert / Sectigo / GlobalSign** 申请：
   - **EV 代码签名证书**（推荐，浏览器/SmartScreen 信任度高；需 USB 硬件 token）
   - **OV 代码签名证书**（较便宜，需累积信誉）
2. 硬件 token 到手后：
   - 安装 **SafeNet Authentication Client**
   - 用 `certutil -user -store My` 找到 `Thumbprint`
3. 记录：
   - `WINDOWS_CERTIFICATE_THUMBPRINT`：40 位 hex
   - `WINDOWS_CERTIFICATE_PASSWORD`（SafeNet token PIN）

#### Linux

Linux 不强制签名，但建议为 AppImage 提供 GPG 签名：
1. `gpg --full-generate-key`（RSA 4096，不过期）
2. `gpg --export-secret-keys --armor KEYID > linux-signing.asc`

### 1.2 生成 Tauri Updater 密钥对

```bash
# 使用 tauri CLI 生成
cd desktop
pnpm tauri signer generate -w ~/.tauri/anxin-updater.key
# 会产生：
# - private key: ~/.tauri/anxin-updater.key
# - public key:  ~/.tauri/anxin-updater.key.pub
```

将**公钥**内容贴入 `desktop/tauri.conf.json`：

```json
{
  "plugins": {
    "updater": {
      "pubkey": "粘贴公钥 base64 字符串",
      "endpoints": [
        "https://api.anxinlegal.com/api/v1/updates/{{target}}/{{arch}}/{{current_version}}"
      ]
    }
  }
}
```

**私钥**只保存在 CI secret：`TAURI_SIGNING_PRIVATE_KEY` + `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`。

### 1.3 GitHub Actions Secrets 配置

在仓库 **Settings → Secrets and variables → Actions** 添加：

| Secret | 来源 | 备注 |
|---|---|---|
| `APPLE_SIGNING_IDENTITY` | 1.1 Apple | 完整字符串 |
| `APPLE_CERTIFICATE` | 1.1 `.p12` 的 base64 | `base64 -i cert.p12 \| pbcopy` |
| `APPLE_CERTIFICATE_PASSWORD` | `.p12` 密码 | |
| `APPLE_TEAM_ID` | 1.1 Apple | |
| `APPLE_ID` | Apple ID 邮箱 | |
| `APPLE_APP_SPECIFIC_PASSWORD` | 1.1 Apple | 用于 notarization |
| `WINDOWS_CERTIFICATE` | `.pfx` base64 | 若 EV 硬件 token 则需用 SSL.com CodeSign Tool 替代 |
| `WINDOWS_CERTIFICATE_PASSWORD` | 证书密码 | |
| `TAURI_SIGNING_PRIVATE_KEY` | 1.2 私钥内容 | |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | 私钥密码 | |

### 1.4 `tauri.conf.json` 填入签名配置

```json
{
  "bundle": {
    "macOS": {
      "signingIdentity": "Developer ID Application: 您的公司 (TEAMID)",
      "providerShortName": null,
      "entitlements": "./Entitlements.plist"
    },
    "windows": {
      "certificateThumbprint": "{{WINDOWS_CERTIFICATE_THUMBPRINT}}",
      "digestAlgorithm": "sha256",
      "timestampUrl": "http://timestamp.digicert.com"
    }
  }
}
```

**Entitlements.plist** 已配置为 `production`（发布前仍需在 `desktop/Entitlements.plist` 检查 `aps-environment` 字段未回退）。

---

## 2. 每版本操作

### 2.1 版本号三处同步

每次发版必须同步：
- `desktop/Cargo.toml` → `[package].version`
- `desktop/tauri.conf.json` → `package.version`
- `frontend/package.json` → `version`

用一行脚本同步：

```bash
VERSION="1.2.3"
sed -i '' "s/^version = .*/version = \"${VERSION}\"/" desktop/Cargo.toml
jq ".package.version = \"${VERSION}\"" desktop/tauri.conf.json > tmp && mv tmp desktop/tauri.conf.json
jq ".version = \"${VERSION}\"" frontend/package.json > tmp && mv tmp frontend/package.json
```

### 2.2 打 tag 触发 CI

```bash
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin v1.2.3
```

CI (`.github/workflows/build-clients.yml`) 会并行跑 macOS / Windows / Linux 构建，产物签名并上传到 draft release。

### 2.3 生成 `latest.json` updater manifest

CI 最后一步用 Tauri CLI 生成：

```yaml
- name: Generate updater manifest
  run: |
    # 收集每平台签名 sig
    node scripts/build-updater-manifest.js \
      --version "$GITHUB_REF_NAME" \
      --pub-date "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      --release-dir ./release \
      > latest.json
    # 上传到 release
    gh release upload "$GITHUB_REF_NAME" latest.json
```

`latest.json` 示例（后端 `/api/v1/updates/{target}/{arch}/{current_version}` 返回同结构）：

```json
{
  "version": "1.2.3",
  "notes": "修复了 X 问题，新增 Y 能力",
  "pub_date": "2026-04-20T10:00:00Z",
  "platforms": {
    "darwin-aarch64": {
      "signature": "...",
      "url": "https://github.com/anxin/legal/releases/download/v1.2.3/anxin-legal_1.2.3_aarch64.app.tar.gz"
    },
    "darwin-x86_64": { "...": "..." },
    "windows-x86_64": { "...": "..." },
    "linux-x86_64": { "...": "..." }
  }
}
```

### 2.4 发布 release（从 draft → published）

1. 在 GitHub Release 页面检查产物完整（4 个平台 × 签名 OK）
2. 写发版说明（中英双语）
3. 点击 "Publish release"
4. CDN/镜像同步（如有）

---

## 3. 验证清单

每次发版完成后执行：

### 3.1 下载安装验证

- [ ] macOS：DMG 无 Gatekeeper 警告，`spctl -a -vv /Applications/安心法务.app` 返回 `accepted`
- [ ] Windows：MSI 无 SmartScreen 警告，证书链完整
- [ ] Linux：AppImage 可执行，deb 可通过 `apt install ./anxin-legal_1.2.3_amd64.deb` 安装

### 3.2 自动更新验证

1. 安装上一版本 `v1.2.2`
2. 发布 `v1.2.3`
3. 启动 v1.2.2，观察：
   - [ ] 启动后 10s 内弹出"有新版本"对话框
   - [ ] 点击"更新"→ 下载 → 签名验证 → 重启
   - [ ] 重启后版本变为 `v1.2.3`

### 3.3 回滚验证

- [ ] 通过后端 API 把 `min_version` 设为 `v1.2.4`，模拟 v1.2.3 被禁用
- [ ] 启动 v1.2.3 客户端，应收到"请升级"的强制提示或降级到 v1.2.2

---

## 4. 常见问题

**Q: Apple Notarization 失败，stdout 提示 "The signature algorithm SHA-1 is no longer valid"**
A: `tauri.conf.json.bundle.macOS.providerShortName` 必须留空或删除；钩子脚本用 `xcrun notarytool submit` 而非过时的 `altool`。

**Q: Windows EV token 在 GitHub Actions 跑不起来**
A: EV 硬件 token 只能在物理机。两种方案：
   - **自建 Windows runner**（建议），把 token 插在 runner 机上
   - **切到云 HSM**（如 SSL.com eSigner）

**Q: `pubkey` 留空，updater 会怎样**
A: Tauri 在运行时拒绝任何未签名的更新包，自动更新**功能性不可用**。必须填入。

**Q: 多个团队成员如何共享私钥**
A: 私钥不进仓库；集中存放在 1Password/Bitwarden 企业保险库，仅 release 管理员有权访问。CI 只读 secret。

---

## 5. 后端 Updater endpoint 参考实现

见 `backend/src/api/routes/updates.py`（本轮已创建）。
