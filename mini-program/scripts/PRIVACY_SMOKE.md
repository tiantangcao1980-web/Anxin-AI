# 隐私模式 fail-closed 录证

## 两条路径，按需选择

| 路径 | 命令 | 依赖 | 用途 |
|---|---|---|---|
| **A. vitest 单元/集成测试** | `npm test` | ❌ 无 IDE / 无 AppID | **CI / 日常**：直接调用生产代码 (client.ts / refresh.ts / auth.ts / privacy module)，断言 `Taro.request`/`Taro.login` 永不被调用 + Privacy 错误被 throw |
| **B. WeChat DevTools 真机 smoke** | `npm run smoke:privacy` | ✅ IDE 登录 + 真实 AppID | **发版前**：在真实工具栈中跑一次，截图录证 |

通常 **A 已能覆盖契约**，B 仅在需要"真机审计材料"时跑。

## 目的

验证 P21A 隐私守门重建（commits `0949c127` + `9e3ed74a` + `a678d354`）在小程序运行时下行为正确，为 PR #5 留下可审计的发版前录证。

## 路径 A · 单元/集成测试（推荐）

```bash
cd mini-program
npm test
```

期望输出：

```
 RUN  v4.1.6 …/mini-program
 Test Files  2 passed (2)
      Tests  14 passed (14)
```

覆盖契约：

| 测试组 | 用例数 | 验证 |
|---|---|---|
| `privacy.test.ts` | 9 | `assertMiniProgramDataNetworkAllowed` 在 local/top-secret 必 throw、standard 通过；`getStoredPrivacyMode` 默认回退；错误携带 mode；isError type guard |
| `privacy-integration.test.ts` | 5 | `apiClient.get` 在 local/top-secret 下 **Taro.request 调用次数 = 0**；standard 下 = 1；`X-Privacy-Mode` 头存在；`wechatMiniprogramLogin` 在 local 下 **Taro.login 调用次数 = 0** |

CI 友好 — 不依赖 IDE / AppID / 网络。

---

## 路径 B · WeChat DevTools 真机 smoke

### 一次性前置（首次跑前）

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

**Q: 工具弹出 "AppID 不合法" / smoke 报告 status=BLOCKED, blocker=jscore 不可达**
A: `dist/project.config.json` 默认写 `touristappid` 让 IDE 进游客模式，**但游客模式下 IDE 不真正编译项目**，automator 的 evaluate/page 操作会 timeout。需要把 appid 改为你账号下的**真实 AppID**（任意已注册的小程序 AppID 都可），再重跑：
```bash
sed -i '' 's/"appid": "touristappid"/"appid": "wx<your-real-appid>"/' dist/project.config.json
npm run smoke:privacy
```
如果只是需要"验证守门契约"而不是录真机视频证据，用**路径 A**即可，无需此步骤。

**Q: `cliPath` 不对（不在 macOS / 自定义安装位置）**
A: 编辑 `scripts/privacy-mode-smoke.js` 顶部 `CLI_PATH` 常量。
   - Windows: `C:\\Program Files\\Tencent\\微信web开发者工具\\cli.bat`
   - Linux: 暂无官方支持

**Q: probe 全部 `{ok: false}`**
A: 看 `report.json` 的 `actual.message` —— 如果是网络层错（fetch failed / TIMEOUT）说明守门没拦住或网络真的有问题；如果是 `MiniProgramPrivacyNetworkBlockedError` 说明守门工作正常。

## 接入 CI

`commercial-readiness-gate.sh` 或 `mobile-device-smoke.sh` 后续可以把 `npm run smoke:privacy` 加进去（需 CI runner 装 WeChat DevTools 才行，目前是本地手动跑）。

录证完成后把 `mini-program-privacy-smoke/` 目录的 4 张 PNG + `report.json` 附到 PR comment 即可关单。
