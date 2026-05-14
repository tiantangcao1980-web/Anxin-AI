# V3 安心智能助手

> 权威级别：⭐⭐⭐ 执行权威
> 适用范围：所有 V3 实施工作

## 一句话

V3 = 项目从"安心智能助手"升级为"**安心智能助手**"，覆盖法务/财务/税务/合规/增长/出海全链路，10 personas + AI Agent 底层驱动 + 桌面/移动/本地/OTA 全端，已完成 P0-P7 主体骨架（31 commits / 61 API / 543+ pytest）。

## 文档索引

| 入口 | 用途 |
|---|---|
| [v3-delivery-summary.md](./v3-delivery-summary.md) | ⭐ 一页纸总览：commits 时间线 / API 列表 / 上手指南 |
| [architecture.md](./architecture.md) | 6 层架构 + 模块清单 + 已实装 vs 规划 |
| [agent-personas.md](./agent-personas.md) | 10 persona 定位、能力、API、实装状态 |
| [capability-matrix.md](./capability-matrix.md) | 4 横 × 4 纵能力矩阵 |
| [roadmap.md](./roadmap.md) | P0-P21 完整路线 + 风险登记册 |
| [integrations.md](./integrations.md) | 34+ OAuth provider / 6 IM 适配器 / 数据源 |
| [skills-inventory.md](./skills-inventory.md) | 13 域 76+ skills + 4 office 实装路径 |
| [skills-sandbox-design.md](./skills-sandbox-design.md) | Skills 沙箱方案（信任分级 T0-T4 / SandboxManifest / 审计） |
| [enterprise-cluster-design.md](./enterprise-cluster-design.md) | 企业内网集群（部门 / 成员 / 角色绑定 / 权限继承 / 私有化部署） |
| [security-whitepaper.md](./security-whitepaper.md) | 客户向安全架构白皮书（六层闸门 / 沙箱 / 数据分级 / 应急响应） |
| [compliance-dengbao-mapping.md](./compliance-dengbao-mapping.md) | 等保 2.0 三级 + GB/T 35273 全条对照清单 |
| [security-audit.md](./security-audit.md) | P15 OWASP / 依赖 / 密钥 / 高风险点 |
| [ci-pipeline.md](./ci-pipeline.md) | 5 端 GHA workflow + nightly smoke |
| [observability-backend.md](./observability-backend.md) / [-frontend.md](./observability-frontend.md) / [-deploy.md](./observability-deploy.md) | 三端可观测性 |
| [health.md](./health.md) / [health-p11.md](./health-p11.md) | 系统健康检查 / 治理 P11 进度 |
| [p8-baseline-fixes.md](./p8-baseline-fixes.md) | P8 基线修复 |
| [p16-dependency-upgrade.md](./p16-dependency-upgrade.md) | 依赖升级 |

## 阅读顺序（新人）

1. [v3-delivery-summary.md](./v3-delivery-summary.md) — 拿到一页纸全景
2. [agent-personas.md](./agent-personas.md) — 理解 10 personas 业务定位
3. [architecture.md](./architecture.md) — 看后端怎么组织
4. [roadmap.md](./roadmap.md) — 看当前 P8+ 在做什么
5. 按域深入 [integrations](./integrations.md) / [skills-inventory](./skills-inventory.md) / [capability-matrix](./capability-matrix.md)

## 与其他 docs/ 的关系

- 本目录 = V3 智能助手**实施细节**（HOW）
- [../openspec/00-intelligent-assistant-platform-spec.md](../openspec/00-intelligent-assistant-platform-spec.md) = V3 **产品合同**（WHAT to deliver）
- [../strategy/](../strategy/) = V3 **战略定位**（WHY）
- [../audit/](../audit/) = V3 **审计与任务执行**

## 维护

- V3 推进进度更新到 [roadmap.md](./roadmap.md)
- 新增 persona / skill / integration 同步更新对应清单
- 重大决策走 [../adr/](../adr/)（如未创建可临时记录到 [v3-delivery-summary.md](./v3-delivery-summary.md)）
