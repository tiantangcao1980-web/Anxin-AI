# 安心法务项目 Wiki

> 更新时间：2026-05-06  
> 来源：当前仓库源码、GitNexus 索引、已运行的本地验证命令。

这份 Wiki 是 Codex 生成的本地项目知识库，用来快速理解项目真实状态，而不是替代源码或测试结果。

## 快速导航

- [项目总览](./01-project-overview.md)
- [架构与模块](./02-architecture.md)
- [功能完成度](./03-functionality-status.md)
- [全端状态](./04-platform-status.md)
- [本地运行与预览](./05-local-runbook.md)
- [验证与质量基线](./06-verification.md)
- [GitNexus 使用说明](./07-gitnexus.md)
- [上线风险与收口路线](./08-release-risks.md)

## 一句话结论

安心法务已经形成较完整的 Web 主产品和后端业务骨架，合同审查、知识库权限、认证、订阅门控、后台管理等主线不是空壳；但支付、电签、桌面同步、移动端深功能和生产安全策略仍未达到正式 1.0 商用交付标准。

当前更准确的状态是：

| 载体 | 状态 |
|---|---|
| Web 用户端 / Pro 端 / 后台 | beta 后期，可进入验收收口 |
| 后端 API / 服务层 | 主线真实，外部渠道仍需生产化 |
| 桌面端 | Tauri 内测壳可用，同步/更新/分发未闭环 |
| 移动 App | Expo MVP 已成型，深功能断点明显 |
| 微信小程序 | 轻量入口版，功能覆盖较浅 |

## 如何阅读

1. 先看 [项目总览](./01-project-overview.md) 和 [功能完成度](./03-functionality-status.md)。
2. 要启动项目，看 [本地运行与预览](./05-local-runbook.md)。
3. 要判断能不能发布，看 [验证与质量基线](./06-verification.md) 和 [上线风险与收口路线](./08-release-risks.md)。
4. 要使用 GitNexus，看 [GitNexus 使用说明](./07-gitnexus.md)。

