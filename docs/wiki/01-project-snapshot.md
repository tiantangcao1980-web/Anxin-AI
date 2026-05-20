---
name: 项目快照
description: 一页讲清项目是什么、为谁做、解决什么、当前形态
audience: AI agents
last_updated: 2026-05-14
---

# 01 · 项目快照

## What

**安心智能助手 (Anxin AI)** = 中国成长型制造企业的全链路 AI 经营助理。
**One App 搞定**：法务 / 财税 / 合规 / 经营 / 调研获客 / 内容产出 / 出海跨境。

## Who

- **付费方**：中小制造企业老板 / 高管
- **使用方**：行政 / 财务 / 法务兼岗人员
- **生态方**：律师 / 税务师 / 财务顾问（B2B2C 通道）

## Why

通用 AI 助手（ChatGPT/Claude/通义）解决不了：
1. **行业纵深**：中国法规 / 税务 / 合规深度（行业知识库 + 5 法律源 + 5 电商源）
2. **桌面/远控**：本地隐私 + 离线模型 + 桌面与移动远控配对
3. **可信会话**：来源链路 / 工具调用透明 / 智能体治理（六层 Harness）
4. **多 persona 协同**：10 个业务 persona + 22 内部 agent + 21 specialized agent

## How（产品形态）

```
┌─ 桌面（Tauri 2 / Rust / SQLCipher）   ← 主战场，本地 LLM + 远控
├─ 移动（Expo / RN 0.76 + UniApp + Taro）← 配对授权 24h + 离线缓存
├─ Web（React 18 / Vite 7）             ← 10 personas 工作台 + 后台 18 页
├─ API（FastAPI / SQLAlchemy 2.0 async）← 75 路由 / 61 个 v3 endpoint
└─ Agent 层（22 personas + 21 specialized）+ Harness 治理 + MCP 协议
```

## What's delivered (V3, 2026-04-27 → 2026-05-14)

| 阶段 | 内容 | 状态 |
|---|---|---|
| P0 | 品牌升级 安心法务 → 安心智能助手 | ✅ |
| P1 | IA 重构 + 后端骨架（10 persona / 3 核心模块 / 6 篇文档） | ✅ |
| P2 | 异步任务 MVP（TaskOrchestrator + Celery + 8 endpoints） | ✅ |
| P3 | IM 通道（飞书真 + 4 占位）+ 沙箱（LocalProvider） | ✅ |
| P4 | OAuth 框架（5 provider + Fernet 加密 token_store） | ✅ |
| P5 | Skills 运行时（4 office skill：docx/xlsx/pptx/pdf） | ✅ |
| P6 | FetchService 4 层（HTTP / crawl4ai / HeadlessX / 官方 API） | ✅ |
| P7 | 5 业务 persona 上线（流程/市场/获客/内容/跨境） | ✅ |
| **H0-O2** | **六层框架基线**（Model/Harness/Context/Traces/Eval/Ops）| ✅ |

## What's next (P8-P13)

- **P8** baseline 打磨 + UI/UX 优化 + 健康度 🚧
- **P9** 5 法务 persona 上层包装（21 specialized agent 已就绪）🔜
- **P10** RAG-Anything 知识库新版（多模态）🔜
- **P11** 多租户 / RBAC 可视化 🔜
- **P12** 5 personas × 三端 E2E 🔜
- **P13** 切换到 anxinai.com 域名 🔜

## 关键技术约束（必读）

- **品牌**：所有新代码用"安心智能助手 / Anxin AI"；"安心法务"仅在 v1/v2 历史叙事中合法
- **CAMEL-AI**：已全量剥离，迁至自研 Harness 层；新代码不要 `import camel`
- **图标**：所有前端图标统一从 `@/lib/icons` 导入（lucide-react），不直接 `from 'lucide-react'`
- **中文**：所有响应/注释中文；变量函数命名英文；commit type 英文 + 描述中文
- **测试**：变更需配套测试；后端 pytest / 前端 vitest / 桌面 cargo test / 移动 jest

## 一句话总结

> 给中国中小制造企业一个**桌面主战场 + 移动远控 + 多 persona 协同 + 行业纵深 + 可信治理**的 AI 助理，区别于"通用聊天框"。
