# Tauri Updater Keys

> 安心智能助手桌面端自动更新签名密钥
> 生成时间：2026-05-22
> 算法：minisign (rsign)

## 文件

| 文件 | 用途 | 是否入仓 |
|---|---|---|
| `anxin-updater.key.pub` | **公钥** — 客户端校验更新包签名 | ✅ 已入仓（也写入 `tauri.conf.json` → `plugins.updater.pubkey`） |
| `anxin-updater.key` | **私钥** — CI/maintainer 签名 release | ❌ `.gitignore` 排除，仅 CI secret + maintainer 持有 |

## CI 配置

发布流水线（GitHub Actions / GitLab CI）需要：

```bash
# Secret 注入
export TAURI_SIGNING_PRIVATE_KEY="$(cat anxin-updater.key)"  # 或直接传 base64 内容
export TAURI_SIGNING_PRIVATE_KEY_PASSWORD=""                  # 当前 keypair 无密码（生产环境强烈建议设密码）
cargo tauri build
```

## 重新生成

⚠️ **重新生成会让所有已发布客户端无法验证新更新**，慎重。

```bash
cd desktop
cargo tauri signer generate --ci -w keys/anxin-updater.key
# 把新公钥内容写入 tauri.conf.json plugins.updater.pubkey
```

## 升级密钥（带密码版本）

生产环境推荐：

```bash
cargo tauri signer generate -w keys/anxin-updater.key --password 'YOUR_STRONG_PASSWORD'
```

然后在 CI 设置 `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` secret。

## 关联

- 桌面 bootstrap 方案：[docs/plans/2026-05-22-desktop-bootstrap.md §2](../../docs/plans/2026-05-22-desktop-bootstrap.md)
- Tauri updater 文档：https://v2.tauri.app/plugin/updater/
