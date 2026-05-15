# 隐私模式 fail-closed 真机 / DevTools Smoke

## 目的

验证 P21A 隐私守门重建（commits `0949c127` + `9e3ed74a`）在 WeChat 开发者工具运行时下行为正确，为 PR #5 留下可审计的发版前录证。

## 一次性前置（首次跑前）

### 1. 微信开发者工具开启 CLI / 自动化

打开 **微信开发者工具 → 设置 → 安全**：

- ✅ 开启「服务端口」（默认 26527）

打开 **微信开发者工具 → 设置 → 通用**：

- ✅ 开启「自动化协议」（automation）

> 如果忘记开，`smoke:privacy` 会在 launch 阶段超时。

### 2. 登录开发者账号

工具必须保持登录态（绑定一个真实 AppID 的开发者账号即可，不需要把项目 AppID 改成真实的）。

### 3. 装依赖

```bash
cd mini-program
npm install
```

`miniprogram-automator` 已加入 devDependencies（^0.12.1）。

## 一次跑通

```bash
cd mini-program
npm run build:weapp      # 产出 dist/，自动写入 touristappid 占位
npm run smoke:privacy    # 启动 IDE、自动操作、截图、写报告
```

## smoke 做了什么

| Step | 行为 | 期望 |
|---|---|---|
| 1 | reLaunch `/pages/me/index`，默认 `standard` 模式，发一次 `apiClient.get('/auth/me')` | 请求被 wx.request 正常发出（无论 200/401/5xx 都算"出门了"） |
| 2 | 点击菜单首项「🛡️ 隐私模式」，截图 ActionSheet | 出现 3 档选项 |
| 3 | 写入 `local` 模式，再发请求 | 在 `client.ts` 内被 `assertMiniProgramDataNetworkAllowed` throw `MiniProgramPrivacyNetworkBlockedError`，wx.request 永不发出 |
| 4 | 切到 `top-secret`，再发请求 | 同上被守门拦截 |
| 5 | 回退 `standard`，再发请求 | 网络恢复正常 |

## 产物位置

跑完后到 `docs/release/evidence/artifacts/mini-program-privacy-smoke/`：

```
01-standard-me.png       — 标准模式下的「我的」页面
02-switch-modal.png      — ActionSheet 弹出
03-local-banner.png      — 本地模式下页面顶部琥珀色横幅
04-blocked-console.png   — top-secret 模式控制台截图
report.json              — 各 step probe 结果 + 整体 PASS/FAIL
```

`report.json` 示例：

```json
{
  "status": "PASS",
  "steps": [
    { "step": "standard",         "expect": "request fires", "actual": {"ok": true} },
    { "step": "local",            "expect": "BLOCKED",
      "actual": {"ok": false, "name": "MiniProgramPrivacyNetworkBlockedError"} },
    { "step": "top-secret",       "expect": "BLOCKED",
      "actual": {"ok": false, "name": "MiniProgramPrivacyNetworkBlockedError"} },
    { "step": "recover-standard", "expect": "request fires", "actual": {"ok": true} }
  ]
}
```

## 常见问题

**Q: launch 超时 / "automatorReady" 不响应**
A: 检查"设置 → 安全 → 服务端口"和"设置 → 通用 → 自动化协议"是否都开了。

**Q: 工具弹出 "AppID 不合法"**
A: `dist/project.config.json` 已写 `touristappid` 走游客模式，正常跳过。如未生效，请重跑 `npm run build:weapp`。

**Q: `cliPath` 不对（不在 macOS / 自定义安装位置）**
A: 编辑 `scripts/privacy-mode-smoke.js` 顶部 `CLI_PATH` 常量。
   - Windows: `C:\\Program Files\\Tencent\\微信web开发者工具\\cli.bat`
   - Linux: 暂无官方支持

**Q: probe 全部 `{ok: false}`**
A: 看 `report.json` 的 `actual.message` —— 如果是网络层错（fetch failed / TIMEOUT）说明守门没拦住或网络真的有问题；如果是 `MiniProgramPrivacyNetworkBlockedError` 说明守门工作正常。

## 接入 CI

`commercial-readiness-gate.sh` 或 `mobile-device-smoke.sh` 后续可以把 `npm run smoke:privacy` 加进去（需 CI runner 装 WeChat DevTools 才行，目前是本地手动跑）。

录证完成后把 `mini-program-privacy-smoke/` 目录的 4 张 PNG + `report.json` 附到 PR comment 即可关单。
