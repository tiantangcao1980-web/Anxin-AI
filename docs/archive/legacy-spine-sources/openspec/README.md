# OpenSpec — 产品与交付规范

> 权威级别：⭐⭐⭐ 执行权威
> 角色：定义"交付什么"（WHAT to deliver），是商业门禁、PR 评审、试点验收的合同依据

## 文档清单

| 文件 | 角色 | 关系 |
|---|---|---|
| [00-intelligent-assistant-platform-spec.md](./00-intelligent-assistant-platform-spec.md) | **平台合同** — 桌面主工作站 / 移动远控 / 本地模型 / 知识库 / Skills / MCP / 治理 / 智能体进化 | 01 的上层 |
| [01-commercial-delivery-spec.md](./01-commercial-delivery-spec.md) | **商业候选版规范** — 阶段目标、统一开发规则、交付物 | 02 的上层 |
| [02-commercial-delivery-test-spec.md](./02-commercial-delivery-test-spec.md) | **测试规范** — 每个任务、端侧、发布前的必跑测试矩阵 | — |

## 阅读路径

1. **新人 / 评审** → 先读 [00](./00-intelligent-assistant-platform-spec.md) 了解平台合同
2. **PR / 实施** → 对照 [01](./01-commercial-delivery-spec.md) 检查交付清单
3. **发布前** → 走 [02](./02-commercial-delivery-test-spec.md) 测试矩阵

## 与其他文档的边界

| 本目录答 | 别处答 |
|---|---|
| 必须交付什么、必须满足哪些边界 | 怎么实现：[../v3/](../v3/) |
| 验收标准是什么 | 当前进度：[../audit/summary.md](../audit/summary.md) |
| 哪些是发布门槛 | 发布证据：[../release/](../release/) |

## 维护

- 平台合同（00）变更必须经产品 + 高层评审
- 商业交付规范（01）变更需对齐 [../audit/plan.md](../audit/plan.md) 进度
- 测试规范（02）随测试体系演进同步更新

## 历史

OpenSpec 文档体系于 **2026-05-08** 建立，作为商业发布前的统一交付依据。
