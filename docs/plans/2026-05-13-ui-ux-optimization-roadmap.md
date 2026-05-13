# UI/UX 审计与优化路线图（下一阶段前置任务）

> 日期：2026-05-13
> 状态：规划中（下一阶段开发的前置门槛）
> 适用范围：产品 / 设计 / 前端 / 移动 / 桌面全团队
> 权威级别：⭐⭐⭐ 执行权威

## 1. 背景

V3 主体骨架（P0-P7）已交付，进入 P8 打磨期。**在 P9-P13 业务深化前，必须先完成全端 UI/UX 审计与优化**，否则后续功能会建在不一致的视觉与交互基础上。

本路线图把 2026-05-08 UI/UX 审计（[../audit/ui-ux-audit-2026-05-08.md](../audit/ui-ux-audit-2026-05-08.md)）中的 P0/P1 问题转化为可执行的工作流。

## 2. 与 V3 路线图的关系

```
P7 完成（2026-04-27）
   │
   ▼
P8 打磨（进行中）
   │
   ▼
UX-1 全端 UI/UX 审计与优化 ◄── 本文档定义的工作（必须先完成）
   │
   ▼
P9 5 法务 persona 包装
P10 知识库新版 RAG-Anything
P11 团队协作
P12 E2E 全覆盖
P13 域名切换
```

**门禁**：UX-1 未完成前，不启动 P9-P13。

## 3. 工作流分层

### 3.1 UX-1.A 跨端设计 token 统一

| 任务 | 责任端 | 输入 | 输出 | 完成标准 |
|---|---|---|---|---|
| 审计 Web 硬编码颜色 | frontend | grep 全仓 `text-\[#`、`bg-\[#` | 清零报告 | 0 残留 |
| 审计 mobile 硬编码 | mobile | grep `color:.*#` `style.*Color` | 清零报告 | 0 残留 |
| 审计 mini-program 暗色 | mini-program | 检查 Taro 主题适配 | 暗色完整覆盖 | 双主题 100% |
| 审计 uni-mobile token 漂移 | apps | 比对 design-tokens | 漂移修复列表 | 0 漂移 |
| 统一品牌主色到新品牌 | design + 全端 | 安心智能助手品牌色板 | 新色板 + 各端实现 | 一致性测试通过 |

详见 [../design/cross-platform-token-drift.md](../design/cross-platform-token-drift.md)。

### 3.2 UX-1.B 关键流程闭环

按 audit/ui-ux-audit 列出的 P0 问题：

| 问题 | 端 | 现状 | 目标 |
|---|---|---|---|
| 假成功提示 | mobile | 部分操作 toast 立即"成功"但实际未完成 | 改为真实 loading → 真实结果 |
| 关键入口可发现性 | 桌面 | 全局快捷键 / 命令面板未上 | Cmd+K 命令面板上线 |
| 错误态不可恢复 | 全端 | error toast 后无重试入口 | 统一 ErrorState 含 onRetry |
| 文档协作冲突 UX | Web | 冲突时无清晰提示 | merge 编辑器 + 引用对照 |
| 政府高可信试点门槛 | 全端 | 部分功能 mock fallback | 移除所有假数据 |

### 3.3 UX-1.C 三态视觉模式

按 [docs/architecture-v2.md](../architecture-v2.md) 的三态：

| 模式 | UI 标识 | 用户感知 |
|---|---|---|
| 🔒 本地 | 顶部状态栏 + 锁图标 | "数据不出设备" |
| 🔄 混合 | 顶部状态栏 + 双向箭头 | "敏感本地、其他云端" |
| ☁️ 云端 | 顶部状态栏 + 云图标 | "全云端最佳体验" |

切换模式必须二次确认 + 显示影响范围。

### 3.4 UX-1.D 可信 AI 交互体验

借鉴 Codex / Claude / Hermes Agent 的原则（[openspec/00-intelligent-assistant-platform-spec.md §3.9](../openspec/00-intelligent-assistant-platform-spec.md)）：

| 体验维度 | 实现要求 |
|---|---|
| **过程可见** | 长任务展示计划 → 步骤 → 工具调用 → 等待原因 → 失败原因 |
| **证据可点** | 法规/合同/资料/网页/知识库引用都有打开入口 |
| **可打断可恢复** | 暂停 / 继续 / 取消 / 接管；跨设备继续保留上下文 |
| **行动前确认** | 外部提交 / 批量发送 / 付费 / 远控 / 代码执行前显示影响 + 撤销方式 |
| **结果可编辑** | 合同 / 报告 / 原型作为 artifact 可编辑，不只是聊天文本 |
| **低噪音高密度** | 桌面偏工作台、移动偏随身助手，无营销大卡片 |
| **命令可发现** | 模型 / Skills / MCP / 知识库通过能力中心 + 命令面板发现 |

### 3.5 UX-1.E 移动端 / 小程序专项

| 端 | 任务 |
|---|---|
| **mobile (Expo RN)** | 真机视觉走查 iOS + Android；触控 ≥ 44px；推送通知体验；生物识别 UI |
| **apps/uni-mobile** | DCloud 云打包；H5 / iOS / Android / 微信小程序全覆盖；底部 tab 统一 |
| **mini-program** | 主包 < 2MB；分包优化；WeChat DevTools 交互证据 |

## 4. 时间表（建议 3 周）

| 周 | 工作 |
|---|---|
| **第 1 周** | UX-1.A 跨端 token 统一 + UX-1.E 移动端审计 |
| **第 2 周** | UX-1.B 关键流程闭环 + UX-1.C 三态视觉 |
| **第 3 周** | UX-1.D 可信 AI 交互 + 全端真机验收 |

## 5. 完成标准（DoD）

UX-1 整体完成需满足：

- [ ] 全端硬编码颜色 = 0
- [ ] 跨端 design token 漂移 = 0
- [ ] 移动端 + 小程序 + 桌面真机 / 模拟器视觉走查通过
- [ ] 关键流程（10 个，见 audit/ui-ux-audit）均有 loading/empty/error 三态
- [ ] 三态模式（本地/混合/云端）切换 UX 上线
- [ ] 命令面板 Cmd+K 上线
- [ ] 统一 ErrorState 组件覆盖率 ≥ 95%
- [ ] 政府试点测试通过（无 mock 假成功）
- [ ] 移动端真机截图 / 录屏入 [release/evidence/](../release/evidence/) artifact

## 6. 责任与协作

| 角色 | 职责 |
|---|---|
| 产品 | 优先级 + 验收 |
| 设计 | token 统一、视觉规范 |
| Frontend 团队 | Web + 桌面 UX |
| Mobile 团队 | RN + UniApp + 小程序 |
| QA | 真机走查 + 截图证据 |

## 7. 输出物

| 产物 | 位置 |
|---|---|
| 跨端 token 漂移清零证据 | [../design/cross-platform-token-drift.md](../design/cross-platform-token-drift.md) 更新 |
| 各端真机截图 | [../release/evidence/](../release/evidence/) |
| 完成度报告 | [../audit/](../audit/) 新增 ui-ux-completion-2026-XX.md |
| 决策记录 | [../adr/](../adr/) 新增 ADR（如涉及架构） |

## 8. 风险

| 风险 | 缓解 |
|---|---|
| 跨端 token 重构耦合度高 | 分端推进，先 Web / 桌面，再 mobile / 小程序 |
| 真机验收依赖设备 | 提前预约设备 + 并行多人 |
| 品牌色变更影响截图 / 文档 | 统一更新 [../../RESOURCES.md](../../RESOURCES.md) |

## 9. 与下一阶段衔接

UX-1 完成后启动：

- **P9** 5 法务 persona（建立在新视觉一致性上）
- **P10** RAG-Anything 多模态（设计组件已就位）
- **P11** 团队协作（artifact / 多人 UX 已统一）
- **P12** E2E 全覆盖（视觉回归基线建立）
- **P13** anxinassistant.com 域名切换（品牌视觉同步）

## 10. 维护

本路线图：
- 每周更新进度
- 完成后归档至 [../archive/](../archive/) 并新增完成报告
- 重要决策同步到 [../adr/](../adr/)

参考：
- [../audit/ui-ux-audit-2026-05-08.md](../audit/ui-ux-audit-2026-05-08.md)
- [../design/cross-platform-token-drift.md](../design/cross-platform-token-drift.md)
- [../v3/roadmap.md](../v3/roadmap.md)
- [../../DESIGN.md](../../DESIGN.md)
