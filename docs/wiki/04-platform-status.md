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

状态：主线可用，生产化收口中。

已具备：

- FastAPI 路由体系
- SQLAlchemy 模型和迁移
- 认证/授权
- 合同、文档、知识库、订阅、支付、电签、IM、同步等服务
- 大量 pytest 回归

验证结果：

- 抽样 32 个关键测试通过
- 文档中记录过后端全量回归 `430 passed, 1 skipped`

重点风险：

- 外部支付/电签生产配置
- webhook 官方协议和幂等
- 密钥治理
- token 存储策略
- 新增未提交文件尚未全部进入 GitNexus 图谱

## 桌面端

状态：内测可用，正式分发前仍需收口。

已具备：

- Tauri 2.x 项目结构
- 系统托盘
- 全局快捷键
- 窗口状态记忆
- 深链
- 通知、文件、剪贴板、Store、SQLite 插件
- 本地/混合/云端模式状态

验证结果：

- `desktop cargo check` 通过

主要缺口：

- 本地 SQLite 同步路径需要统一
- 自动更新 pubkey / 发布链路未闭环
- 打包签名、公证、安装包验收缺证据
- CSP 仍允许 `unsafe-eval`

## 移动 App

状态：MVP。

已具备：

- Expo Router
- 登录/注册/找回密码
- 移动收件箱
- 聊天
- 案件/合同/任务/审批/消息/通知
- 找律师
- 设置

验证结果：

- `mobile npm test` 通过，5 个文件 11 个测试

主要缺口：

- `npx tsc --noEmit` 当前失败，需要调整 TS module 配置或动态 import 写法
- 智能调查提交未接真实详情流
- 法律智库搜索未接结果页
- 微信登录仍提示即将开放
- 不具备 Web 的复杂工作台和后台能力

## 微信小程序

状态：早期入口版。

已具备：

- 首页
- 聊天
- 个人中心
- Taro H5 构建

验证结果：

- `mini-program npm run build:h5` 通过
- 包体检查通过

主要缺口：

- 合同审查、找律师、合规自检等首页快捷入口仍开发中
- 页面数量少
- 业务深度明显低于移动 App 和 Web

