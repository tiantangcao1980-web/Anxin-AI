# 回滚预案

> 日期：2026-05-06
> 适用范围：商业交付候选版前后的代码、配置、数据库、支付、电签、对象存储和多端发布。

## 1. 总原则

- 每个渠道独立灰度，不做 big-bang。
- 回滚优先级：配置开关回滚 -> 流量切回旧路径 -> 数据修复脚本 -> 代码回滚。
- 不删除生产数据；任何 destructive 操作必须先备份和演练。
- 失败回调不得直接返回 success 掩盖问题，必须进入可重试/可审计状态。

## 2. 配置级回滚

| 能力 | 回滚开关/动作 | 期望效果 |
|---|---|---|
| 电签 provider | `ESIGN_PROVIDER=mock` 或切回已验证渠道 | 停止真实电签新流程创建 |
| 电签官方 webhook | `ESIGN_OFFICIAL_WEBHOOK_ENABLED=false` | 切回通用 HMAC 回归路径 |
| 微信支付官方 webhook | `WECHAT_PAY_OFFICIAL_WEBHOOK_ENABLED=false` | 切回非官方验签路径，仅用于紧急回归 |
| 支付宝官方 webhook | `ALIPAY_OFFICIAL_WEBHOOK_ENABLED=false` | 切回非官方验签路径，仅用于紧急回归 |
| webhook retry worker | `WEBHOOK_RETRY_WORKER_ENABLED=false` | 停止后台自动重试，保留手动重试 |
| 对象存储 | `OBJECT_STORAGE_BACKEND=local` | 从 MinIO/S3 切回本地存储，仅适合非生产或维护窗口 |
| refresh body compat | `AUTH_REFRESH_BODY_COMPAT_ENABLED=true` | 临时恢复旧客户端 refresh 兼容 |

## 3. 数据库回滚

发布前必须对以下迁移做 upgrade/downgrade 演练：

- `028_add_password_reset_tokens.py`
- `029_add_document_object_storage_fields.py`
- `030_add_webhook_received.py`
- `031_add_contract_esign_flow_mapping.py`
- `032_add_webhook_retry_schedule.py`
- `033_add_refund_idempotency_key.py`
- `034_add_subscription_events.py`
- `035_add_im_message_sequence.py`
- `036_add_contract_versions.py`
- `037_add_contract_attachments.py`

回滚顺序：

1. 停止写流量或开启维护页。
2. 备份数据库和对象存储元数据。
3. 确认无进行中的支付/电签回调处理。
4. 按迁移逆序 downgrade。
5. 运行关键读路径 smoke。
6. 恢复流量。

## 4. 渠道回滚

### 支付

- 新订单创建失败：关闭对应 provider，保留订单为 `pending/failed`，不自动退款。
- 回调验签失败激增：暂停官方 webhook 开关，导出失败记录，用 Admin `/admin/webhooks` 逐条重试。
- 退款幂等冲突：保留同 key 返回，不重新发起渠道退款。

### 电签

- 创建签署流程失败：切回 `mock` 或只允许草稿/审批，不进入真实签署。
- 回调事件无法映射：将事件记录为 failed，保留原合同状态，不直接推进到 `signed`。
- 已签文件下载失败：不归档，保留 `signed` 或 `pending_archive` 类业务状态，待渠道恢复后补拉。

### 对象存储

- 上传失败：API 返回 5xx/4xx，不写伪文件路径。
- 下载失败：保留对象 key，不删除 DB 元数据。
- MinIO/S3 故障：暂停上传入口，允许已缓存/本地对象读取。

## 5. 前端/移动回滚

- Web：回滚到上一构建产物，确认 `frontend/dist/index.html` 对应版本。
- 小程序：通过微信平台回退版本；登录失败不得写 `mock_token`。
- 移动端：应用商店回滚不可即时生效，需 feature flag 降级高风险入口。
- 桌面端：自动更新必须支持禁用更新和回退下载链接。

## 6. 回滚验收

回滚完成后必须记录：

- 触发原因、开始/结束时间、影响用户量。
- 使用的配置开关、迁移版本、代码版本。
- 数据一致性检查结果。
- 后续修复 issue 和复盘 owner。

