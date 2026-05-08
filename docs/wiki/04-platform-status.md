# 全端状态

## Web 端

状态：beta 后期。

已具备：

- 用户端主路由
- 律师/律所 Pro 端
- 后台管理端
- AI 聊天和工作台
- 合同管理
- 文档工作台
- 案件中心
- 找律师/案源市场
- 知识库和知识图谱
- 尽调/舆情入口
- IM / 音视频入口
- 订阅和模式门控

验证结果：

- `frontend npm run lint` 通过
- `frontend npm run build` 通过

已知问题：

- `lottie-web` 的 `eval` 构建告警
- `vendor-three`、`vendor-livekit`、`vendor-editor` 等 chunk 较大
- `api.ts` 和 `api-adapter.ts` 存在动静态 import 混用导致分包收益有限

## 后端

状态：主线可用，商业证据收口中。

已具备：

- FastAPI 路由体系
- SQLAlchemy 模型和迁移
- 认证/授权
- 合同、文档、知识库、订阅、支付、电签、IM、同步等服务
- 大量 pytest 回归

验证结果：

- 后端默认全量回归最近记录为 `467 passed, 1 skipped, 17 warnings`
- 商业门禁中的 mypy zero-baseline、RAG、支付/电签 provider/webhook/refund/action-audit、release artifact/evidence/checklist/lanes 等切片通过

重点风险：

- 外部支付/电签 sandbox 配置与真实回调证据
- webhook 官方协议、幂等和关键动作审计需要在 sandbox 对账复验
- 密钥治理
- token 存储策略
- 新提交后需要重跑 GitNexus，避免索引漂移

## 桌面端

状态：内测可用，正式分发前仍需签名/公证和真实包验收。

已具备：

- Tauri 2.x 项目结构
- 系统托盘
- 全局快捷键
- 窗口状态记忆
- 深链
- 通知、文件、剪贴板、Store、SQLite 插件
- 本地/混合/云端模式状态

验证结果：

- `desktop cargo check` 与 `cargo test` 通过
- 本地 installed-profile SQLCipher/keyring smoke、unsigned release app+DMG、unsigned packaged runtime/profile/performance smoke 已作为支持性证据通过

主要缺口：

- 本地 SQLite 同步路径需要统一
- 自动更新 pubkey / 发布链路未闭环
- signed/notarized installer、signed packaged-profile migration、signed packaged runtime 性能和跨设备连续会话缺证据
- CSP 仍允许 `unsafe-eval`

## 移动 App

状态：代码级 smoke 稳定，真机商业验收未完成。

已具备：

- Expo Router
- 登录/注册/找回密码
- 移动收件箱
- 聊天
- 案件/合同/任务/审批/消息/通知
- 找律师
- 设置

验证结果：

- `mobile npm test` 通过，`7 files / 19 tests passed`
- mobile TypeScript、Expo config/SDK guard、Expo doctor `17/17`、mobile production npm audit 均通过

主要缺口：

- iOS app-run、Android 真机/模拟器和跨设备连续会话 transcript 缺失
- 移动远程控制桌面仍需设备配对、命令下发、撤销/二次确认和审计证据
- 不具备 Web/桌面完整工作台和后台能力

## 微信小程序

状态：代码级 smoke 通过，交互式微信验收未完成。

已具备：

- 首页
- 聊天
- 个人中心
- Taro WeChat build
- `wx.login -> code2session -> JWT` 登录链路
- 首页资讯空态不再使用假新闻 fallback

验证结果：

- mini-program TypeScript 与 `build:weapp` 通过
- WeChat DevTools CLI project smoke 通过
- refresh auth guard、mobile/mini privacy network guard、fake fallback guard、mini-program navigation boundary guard、mini-program design token guard 通过

主要缺口：

- 合同审查、找律师、合规自检等首页快捷入口仍开发中
- 页面数量少
- 交互式微信开发者工具或真机 transcript、正式 appid 环境和跨设备连续会话证据缺失
