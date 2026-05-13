# 商业交付审计摘要

> 日期：2026-05-09
> 范围：从当前代码现状推进到商业交付候选版的证据总览。

## 1. 目标到证据清单

| 用户目标/显式要求 | 当前证据 | 状态 |
|---|---|---|
| 使用 OpenSpec/规范完成项目规范 | `docs/openspec/01-commercial-delivery-spec.md`、`docs/openspec/02-commercial-delivery-test-spec.md` 和 `docs/openspec/00-intelligent-assistant-platform-spec.md` 已存在并持续更新；2026-05-08 已把中小企业双边平台、桌面主工作站、移动远控、本地模型/知识库、任意 LLM/Skills/MCP 配置写入规范 | 已完成当前定位版 |
| 建立商业发布门禁 | `scripts/commercial-readiness-gate.sh` 已建立，`docs/release/evidence/` 外部证据模板已建立；`scripts/sandbox-evidence-runner.py` 已补支付/电签脱敏预检和可选 live 采集入口；`scripts/desktop-release-package.sh` 和 `scripts/desktop-release-preflight.sh` 已补桌面 signed/notarized release 前置条件预检；`backend/tests/test_sandbox_evidence_runner.py` 覆盖 live 确认门、脱敏写出和外部证据槽；当前预期失败以阻止缺少 `Status: complete` 证据时误发布 | 已完成 gate 和采集入口，商业证据未齐 |
| 按规范推进开发与测试 | 已收口 TASK-01/02/05/06/07/09/10/11c 的若干 P0/P1 切片；TASK-11a 桌面 MVP 已补 `docs/audit/11a-desktop-mvp/00..05.md` 审计包并纳入 `desktop-mvp-local-gate.sh`；TASK-11b 桌面同步新增注入式 SQLite push/pull/retry 代码级闭环；后端全量 `467 passed, 1 skipped, 17 warnings in 36.11s`，前端 lint/tsc 当前通过，最新完整本地门禁中 Vitest `12 files / 45 tests passed` | 进行中 |
| 形成商业交付准备包 | 本摘要、completion audit、release readiness、rollback runbook、security/privacy checklist、test evidence 已补齐 | 已完成当前版本 |
| 补充 UI/UX 与真实状态审计 | `docs/audit/current-state-ui-ux-audit-2026-05-08.md` 已按移动端、小程序、桌面端拆出 P0/P1 问题，并补充中小企业需求方、专业服务方、全设备智能助手和高可信试点门槛 | 已完成审计基线 |
| 参考项目与智能体治理升级 | `docs/references/agentic-platform-benchmark-2026-05-08.md`、`docs/openspec/00-intelligent-assistant-platform-spec.md` 和 `task-12-agent-control-plane-skill-evolution.md` 已吸收 Hermes/OpenClaw/HiClaw/DeepTutor/CLI-Anything/RAG-Anything/browser-use/Scrapling，并补充 Codex/Claude 式可信会话体验、Skills 进化与智能体自我改进治理 | 已完成规范基线，代码实现待执行 |

## 2. 当前已收口的高风险面

- 认证与 token：Web access token 内存化、refresh cookie、reset token hash 持久化、CAPTCHA 覆盖、关键 Redis fail-closed 切片已落。
- 模式/订阅守卫：`/pro` provider 守卫、ModeGate/PrivacyContext fail-closed、LLM 组织隔离、后端 mode/subscription guard 已落。
- 文档/对象存储：`object_storage_service`、文档上传/删除/版本更新、合同附件对象存储生命周期、上传校验、模板边界、协作离线合并、导出大小保护已落。
- 合同/电签：状态机、版本 diff/回滚、审查锁/超时、webhook 并发幂等、e签宝/法大大 provider 代码级官方协议、官方 webhook 验签和审计双写已落。
- 支付/订阅/IM：微信支付 v3/支付宝 RSA2 代码级协议、退款幂等、订阅状态机、双客户端订阅隔离、IM 首包鉴权和离线 ACK 已落。
- 同步底座：后端 `/api/v1/sync/*` 已从进程内存改为 `SyncLog` 持久化 append-only 日志，覆盖用户隔离、增量拉取、过期版本冲突和 artifact session 隔离；桌面端已从前端 Tauri SQL 改为 Rust SQLCipher/keyring 本地库路径，前端通过 secure SQL commands 读取本地 `sync_log`、push/pull 并写回 SQLCipher，fresh/legacy SQLite migration smoke、SQLCipher plaintext migration 单测、local installed-profile keyring/reopen smoke 和 100/500 本地性能基线已通过，unsigned debug macOS `.app` bundle self-test/runtime startup/WebView page-load smoke、unsigned release packaged sync loopback smoke 已通过，`scripts/desktop-release-preflight.sh` 已生成脱敏 artifact 并定位签名/公证/正式产物缺口，`SyncStatus` 已有最小冲突处理对话框，`/sync-conflicts` 已有 merge 编辑页，失败记录已有代码级指数退避和人工介入标记，`scripts/desktop-sqlite-security-gate.sh` 已通过。仍缺 signed/notarized installer、packaged-profile migration 实装证据、signed packaged runtime 性能、共享预发后端 sync transcript 和跨端连续会话验证。
- 移动/小程序局部：移动端多处假数据 fallback 移除，messages/tasks 详情页已改为真实 loading/empty/error 状态，尽调和知识库搜索提交后已改为页面内结果摘要卡；移动找律师已从纯列表升级为匿名咨询创建、AI 摘要、律师选择、匿名聊天室和委托 API 的转化链路；小程序 `mock_token` 移除并接 `wx.login -> code2session`；小程序首页/个人中心主入口已移除空路径和“功能开发中”死胡同；小程序语义 token 层已补并由 mini-program navigation/design token guard 保护；`scripts/mobile-device-smoke.sh` 已通过本地测试、tsc、mobile result surface guard、mobile lawyer conversion guard、Taro build、WeChat DevTools CLI project smoke、fake fallback guard、navigation boundary guard 和 design token guard；2026-05-09 移动 production `npm audit --omit=dev` 已通过定向 overrides 再次清零。

## 3. 仍阻断商业交付的缺口

| 阻断项 | 为什么阻断 | 下一步 |
|---|---|---|
| 真实支付/电签商户沙箱 | 当前代码级协议通过 fake client/单元测试，且已补 `scripts/sandbox-evidence-runner.py` 作为脱敏预检/live 采集入口；runner 已有 `4 passed` 覆盖 live 确认门、脱敏写出、env 模板同步和外部证据槽；2026-05-07 已写出 `payment-sandbox-preflight-20260507.json` 与 `esign-sandbox-preflight-20260507.json`，确认缺真实渠道配置、官方 webhook enable 和外部回调/重试/轮换证据；仍缺真实渠道响应、重试、证书/事件轮换证据 | 获取沙箱凭据和公网 callback 后跑 live runner，再按 `docs/release/commercial-delivery-readiness.md` 的渠道清单跑 7 天 |
| 桌面同步引擎 | 后端持久日志、Rust SQLCipher/keyring 最小 push/pull、secure SQL command path、Rust IPC `trigger_sync` fallback 代码级 SQLCipher push/pull、packaged-binary sync code smoke、packaged-binary sync loopback smoke、desktop strict Clippy、fresh/legacy SQLite migration smoke、SQLCipher plaintext migration 单测、local installed-profile keyring/reopen smoke、SQLite 100/500 本地性能基线、unsigned debug macOS `.app` bundle self-test/runtime startup/WebView page-load smoke、release preflight、冲突管理页、代码级重试退避、Rust init schema 对齐、Tauri debug build 和 `scripts/desktop-sqlite-security-gate.sh` 安全门禁已落；preflight 明确缺签名、公证和 signed runtime 证据；signed/notarized installer、共享预发后端 sync transcript、packaged runtime 性能与跨端连续会话未闭环 | 继续执行 TASK-11b 的发布级验收 |
| 桌面 MVP 工作站 | 窗口 chrome、快问、文件拖入队列、WebView drop、工作站配置、配置档 CRUD、PrivacyContext 对齐和远控 host safe-probe 控制面已有代码/浏览器/本地门禁证据；`docs/audit/11a-desktop-mvp/00..05.md` 已补齐并纳入桌面 MVP local gate | 补 signed packaged runtime、macOS/Windows 截图/视频、快捷键 200ms、托盘 drop 500ms、真实 local model、真实 approved connector 和真机远控证据 |
| RAG/引用质量 | TASK-07 已补后端 RBAC/PII、`knowledge_management` 读写权限/组织 fail-closed/出口脱敏、offline smoke 召回基线、live Qdrant smoke、RAG source 字段、司法智库入口、前端引用预览/高亮、图谱 1k 节点降采样/FPS/canvas E2E、Playwright 点击证据和导出文档/chunk/anchor 巡检；2026-05-07 内建法律知识库 full50 已跑通 `42` chunks / `50` questions，recall@10 `1.000`、MRR `1.000`、NDCG@10 `0.997`，且商业 preflight 会拒绝旧 smoke corpus 和 smoke-marked golden | 内建 RAG release baseline 已闭合；外部客户知识库 full50 可作为上线后质量扩展 |
| 案件/律师市场/风险调查 | TASK-08a/08b/09 核心代码级风险已收口：案件状态机、任务 owner、律师 local guard、利益冲突阻断、撮合公平、风险调查缓存/爬虫/意图均有测试；真实 crawler dry-run、律所 RBAC 全矩阵、案源 8 API、Playwright 全流程仍需补发布证据 | 继续补真实环境与全矩阵验收 |
| 移动端完整验收 | 本地 mobile/mini smoke 与 fake fallback guard 已通过；移动端/小程序最小触控 token 底座已补；小程序语义 token 层已补并迁移首页/聊天/个人中心；`docs/design/cross-platform-token-drift.md` 已产出三端 token 漂移清单并定位品牌主色和真机触控复核 P0；仍缺品牌主色最终统一、跨设备会话延续、真机验证 | 执行 TASK-11c 剩余 P0/P1 |

## 4. 推荐下一步顺序

1. TASK-11b 桌面同步引擎：补 signed/notarized installer、signed packaged-profile migration 实装证据、共享预发后端 sync transcript、signed packaged runtime 性能和移动端连续会话。
2. TASK-07 RAG 质量与引用链路：直接影响法务产品可用性，需要真实业务知识库 full50 和引用回链。
3. TASK-08a/08b 案件/律师市场：补全矩阵、案源 8 API 打勾和 Playwright 三角联通。
4. 获取支付/电签沙箱凭据后，启动真实渠道 7 天回归与灰度记录。
