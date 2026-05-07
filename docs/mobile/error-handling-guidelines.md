# 移动端错误处理规范

> 日期：2026-05-07
> 范围：React Native 移动端与微信小程序。目标是防止静默 fallback、mock success、假数据列表再次进入发布路径。

## 1. 统一原则

- 加载中必须呈现 loading，不提前渲染假内容。
- 空数据必须呈现 empty state，不用示例数据填充。
- 后端或网络失败必须呈现 error state，并提供重试入口。
- 认证失败、权限不足、资源不存在、网络失败必须用不同文案。
- 不允许在生产路径写入 `mock_token`、`fake success`、`fallback*` 数据。
- 小程序 `wx.login -> code2session` 只接收 JWT，不允许前端获得或持久化 `session_key`。

## 2. 移动端错误文案

| 场景 | 用户文案 | 行为 |
|---|---|---|
| 401 | 登录已过期，请重新登录 | 清理本地 token 后跳转登录 |
| 403 | 无权限查看该内容 | 停留当前页，展示权限说明 |
| 404 | 内容不存在或已被删除 | 展示空态，不重试轮询 |
| Network request failed | 网络连接失败，请检查后重试 | 展示重试按钮 |
| 5xx / unknown | 加载失败，请稍后重试 | 展示重试按钮并记录 telemetry |

现有证据：`mobile/src/features/workflow/detail-model.test.ts` 覆盖 401、403、404、network 和默认错误映射。

## 3. 页面状态模型

每个远程数据页面应显式维护四态：

| 状态 | 条件 | UI |
|---|---|---|
| loading | 首次请求未完成 | loading skeleton 或 spinner |
| ready | 有真实数据 | 正常业务 UI |
| empty | 请求成功但数据为空 | EmptyState + 可选刷新 |
| error | 请求失败 | ErrorState / EmptyState variant + 重试 |

禁止模式：

```ts
catch {
  setItems(mockItems)
}
```

允许模式：

```ts
catch (error) {
  setItems([])
  setError(getDetailLoadErrorMessage(error, '加载失败'))
}
```

## 4. 发布前静态守卫

发布前至少运行：

```bash
bash scripts/mobile-device-smoke.sh
rg -n "fallbackMessages|fallbackTask|mock_token|session_key|假数据|体验模式|mock success|fake success" mobile/app mobile/src mini-program/src
```

期望：

- `scripts/mobile-device-smoke.sh` 通过。
- 静态 grep 对生产源码无命中。
- `session_key` 只允许出现在后端服务/测试中，不能出现在 `mini-program/src`。

## 5. 真机验收要求

本规范不能替代真机证据。商业发布前仍需记录：

- iOS：登录、审批详情、消息/任务详情、网络失败重试。
- Android：登录、审批详情、消息/任务详情、网络失败重试。
- 微信开发者工具或真机：`wx.login -> code2session -> JWT`、资讯空态、登录失败提示。
- 跨设备：桌面开始会话后，移动端能看到 `last_message` 和草稿/未读状态。
