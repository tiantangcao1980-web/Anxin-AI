# ADR-001: V3 升级为"安心智能助手"

> 日期：2026-04-26
> 状态：已采纳
> 决策人：产品 + 工程团队

## 背景

项目 V1 / V2 定位为"安心法务"（已上线 anxinfawu.com），但实际客户需求涵盖：

- 法务（合同 / 合规 / 诉讼）
- 财务（账务 / 税务）
- 经营管理（流程 / 审批 / 任务）
- 增长（市场研究 / 获客 / 内容）
- 出海（跨境电商 / 供应链）

继续以"法务"作为单一垂直定位会丢失商业机会。同时 AI Agent 技术成熟到可以承载 multi-persona 编排。

## 考虑过的方案

### 方案 A：扩展"法务"边界，新增财税子模块
- 优点：品牌延续性强
- 缺点：用户认知锚定在"法律"，跨域销售困难

### 方案 B：全新品牌"安心智能助手"，10 personas 全覆盖
- 优点：定位清晰、技术架构跟随、可对标 Hermes/OpenClaw
- 缺点：原品牌积累需要迁移；技术工作量大

### 方案 C：建立子品牌矩阵（法务版 / 财税版 / 出海版分别独立）
- 优点：垂直深入
- 缺点：开发成本 3 倍、运营成本 3 倍、用户跨域需多账号

## 决策

**采纳方案 B**：升级为"安心智能助手"。

执行路径（P0-P21）：

- **P0** 品牌切换 ✅
- **P1** IA 重构 + 后端 3 模块骨架 + 6 大核心文档 ✅
- **P2** 异步任务编排（TaskOrchestrator + Celery）✅
- **P3** IM 通道（飞书优先）+ 沙箱执行器 ✅
- **P4** OAuth 应用授权框架 ✅
- **P5** Skills 运行时 + 4 office skill ✅
- **P6** FetchService 4 层 + 5 法律源 + 5 电商源 ✅
- **P7** 5 user-facing personas（流程/市场/获客/内容/出海）✅
- **P8** 健康度打磨 🚧
- **P9** 5 法务 persona user-facing 包装 🔜
- **P10** RAG-Anything 多模态 🔜
- **P11** 团队协作 / 多租户 / RBAC 🔜
- **P12** E2E 全覆盖 🔜
- **P13** 切到 anxinassistant.com 域名 🔜

## 影响

### 正面
- 商业模式扩展到 6 业务域
- 技术架构对齐 AI Agent 时代主流
- 单一账号跨域协同
- V3 31 commits / 61 API / 543+ pytest 已完成

### 负面
- 已上线 anxinfawu.com 用户需迁移引导
- 技术栈复杂度上升（新增 Celery / IM Gateway / OAuth 框架）
- 文档/规范需重建（本轮治理已完成）

### 后续行动
- ✅ V2 + V3 合并到 `integration/v3-merge-20260512`
- ⏳ V3 → main → anxinassistant.com 域名切换（P13）
- ⏳ 旧 anxinfawu.com 30 天 redirect 平滑过渡

## 参考

- [docs/v3/v3-delivery-summary.md](../v3/v3-delivery-summary.md) — V3 交付总览
- [docs/v3/roadmap.md](../v3/roadmap.md) — P0-P21 路线
- [docs/openspec/00-intelligent-assistant-platform-spec.md](../openspec/00-intelligent-assistant-platform-spec.md) — 平台合同
- [docs/strategy/product-architecture-and-requirements-2026-05-08.md](../strategy/product-architecture-and-requirements-2026-05-08.md) — 产品定位
