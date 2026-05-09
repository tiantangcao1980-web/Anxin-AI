# 商业交付持久目标契约

> 日期：2026-05-09
> 工作流：goal-driven-workflow
> 状态：active

## Objective

基于现有审计与升级目标，将 Anxin-Smart-Legal-Services 推进到尽可能接近商业交付上线要求：优先完成桌面端本地可执行功能、治理、测试和发布门禁；移动端和小程序端随后按 uni-app 迁移路线推进；外部 API、签名和真机资源以可替换测试数据与清晰接入点先完成函数级和流程级验证，待真实密钥后联调。

## First Action

1. 读取并计数规格与审计输入。
2. 把新增约束同步到发布与审计计划。
3. 从桌面主工作站配置面开始实现本地可执行功能闭环。

## SDD Context Loaded

| 输入 | 当前计数 |
|---|---:|
| `docs/openspec/*.md` | 3 files |
| `openspec/` 根目录 | 不存在 |
| OpenSpec `SHALL/MUST/GIVEN/WHEN/THEN` 关键字 | 0 |
| 审计任务/DoD/P0 信号 | 359 |

## Scope

- 桌面优先：`desktop/`、`frontend/src/components/desktop/`、`frontend/src/pages/Settings.tsx`、桌面相关 e2e 与 release evidence。
- 治理与门禁：Agent/Skill/CapabilityRoute、release checklist、commercial readiness gate、external evidence 模板。
- 外部 API：支付、电签、LLM/embedding、对象存储、短信/邮件、搜索/尽调等先用 provider contract、sandbox runner、fixture 和脱敏 artifact 验证，不把真实 secret 写入仓库。
- 移动与小程序：后续按 `docs/mobile/uni-app-migration-plan.md` 新建 `apps/uni-mobile/`；旧 `mobile/` 与 `mini-program/` 只做安全修复、回归保护和迁移提取。
- UI/UX：功能先闭环；最终所有关键桌面、移动、治理入口必须达到商业级信息密度、专业审美、响应式与可访问交互。

## Constraints

- 不引入新依赖，除非用户明确要求。
- 现有测试失败不能通过削弱、删除或跳过测试来修。
- 不把 API key、证书、私钥、真实手机号、身份证号、合同原文或后台截图原图写入仓库。
- `Status: complete` 只能在真实证据齐全后修改；不能用 mock/fake artifact 冒充商业证据。
- TopSecret/local 模式下任何数据网络动作必须 fail-closed。
- 桌面端先于移动端和小程序端；移动新功能不得继续扩展 legacy Expo/Taro 客户端。

## Done When

1. 桌面主工作站功能：有本地可执行配置面、状态探针、离线/同步/远控安全闸与对应 `frontend`/`desktop` 测试证据。
2. 外部 API 接入：支付、电签、LLM/embedding 等 provider 都有可替换测试数据、runner 或 contract test，真实 secret 只作为后续联调输入。
3. 治理闭环：Agent/Skill/MCP/CLI/LLM/Browser/Desktop-control route-token 与审批/审计/撤销路径有测试和 UI 入口。
4. 发布门禁：`scripts/commercial-readiness-gate.sh --quick` 只因真实外部证据缺失而失败；本地可执行 gate 全部通过并记录到 `docs/release/test-evidence.md`。
5. UI/UX：关键桌面工作流不横向溢出、按钮/控件语义清楚、状态不假成功，后续设计打磨有明确 issue 和验收图。
6. Completion audit：`docs/release/completion-audit.md` 能把每个阻断项映射到文件、命令、artifact 或外部负责人输入。

## Stop If

- `git status --short` 出现与当前目标无关且无法解释的用户改动。
- 任一 release evidence 被改成 `Status: complete` 但仍含 `pending/TBD/缺/待` 或空 artifact reference。
- 商业环境路径使用 mock/fake provider 替代真实 fail-closed 或 sandbox contract。
- TopSecret/local 模式测试发现数据网络动作实际发出。
- 需要真实外部凭据、签名身份、真机设备或生产后台权限才能继续同一条执行链路。
- 新实现要求新增依赖或改变认证/计费/隐私边界，但没有对应测试和审计记录。

## Token Budget

用户没有指定固定 token budget；本目标在 Codex goal 工具中不设置硬预算。每轮执行保持短反馈、强证据和可提交增量，直到达成或遇到可机械检测的 Stop 条件。
