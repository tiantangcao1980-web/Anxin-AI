---
title: 历史 Spine 源文档归档（仅供溯源）
status: archived
archived_at: 2026-05-14
supersedes: 见每个子目录的"映射到新 Spine"说明
---

# 历史 Spine 源文档归档

> ⚠️ **本目录所有文档已被新 Spine 取代，仅保留供溯源、审计、回溯使用。不要按这里的文档做新决策。**

## 新 Spine 入口（权威）

| 主题 | 新文档 | 取代 |
|------|--------|------|
| 需求 / 商业定义 / 红线 | [`docs/REQUIREMENTS.md`](../../REQUIREMENTS.md) | `openspec/`, `strategy/` |
| 系统架构 / 6 层模型 | [`docs/ARCHITECTURE.md`](../../ARCHITECTURE.md) | `v3/architecture.md`, `architecture-v2.md` |
| 路线图 / P0–P21 | [`docs/ROADMAP.md`](../../ROADMAP.md) | `v3/roadmap.md`, 根目录 `ROADMAP.md`, `PRODUCT_ROADMAP.md` |
| 开发计划 / 当前批次 | [`docs/DEVELOPMENT_PLAN.md`](../../DEVELOPMENT_PLAN.md) | `plans/*.md`, `release/48-hour-*.md`, `release/goal-contract-*.md` |
| 发布门 / 5 维评测 / 证据清单 | [`docs/RELEASE_GATE.md`](../../RELEASE_GATE.md) | `release/commercial-delivery-readiness.md`, `release/completion-audit.md`, `audit/summary.md`, `audit/plan.md` |
| AI 智能体接手 / Wiki | [`docs/wiki/README.md`](../../wiki/README.md) | 全部审计模块的"快速接手"片段 |

## 子目录映射

```
legacy-spine-sources/
├── openspec/             → docs/REQUIREMENTS.md
├── strategy/             → docs/REQUIREMENTS.md（产品架构）+ docs/ARCHITECTURE.md（技术）
├── v3/                   → docs/ARCHITECTURE.md（6 层）+ docs/ROADMAP.md（P0–P21）
├── architecture/         → docs/ARCHITECTURE.md（旧 architecture-v2 内容已合并）
├── audit/                → docs/RELEASE_GATE.md（5 维评测整合）+ docs/wiki/03-current-state.md（活跃任务）
├── plans/                → docs/DEVELOPMENT_PLAN.md（合并 + 重写）
└── release/              → docs/RELEASE_GATE.md（仅整合"判断 + 清单"，保留运维 runbook 在 docs/release/ 主目录）
```

## 仍然活跃的 release/* 文档（未归档，保留在 `docs/release/`）

- `evidence/`（证据物料库）
- `evidence-collection-runbook.md`（证据采集 SOP）
- `external-inputs-checklist.md`（外部输入清单）
- `external-resource-handoff.md`（外部资源交接）
- `external-resource-requirements.json`（外部资源需求结构化数据）
- `mobile-error-state-release-notes.md`（移动端错误态发布说明）
- `rollback-runbook.md`（回滚 SOP）
- `security-and-privacy-checklist.md`（安全 / 隐私清单）
- `test-evidence.md`（测试证据汇总）
- `third-party-api-preparation.md`（三方 API 准备）
- `commercial-delivery-checklist.json` + `commercial-delivery-lanes.json`（lane 结构数据）
- `README.md`

## 何时翻阅本归档？

仅在以下情况：
1. 需要追溯某条决策的历史背景（例如 "为什么放弃 CAMEL-AI"）
2. 审计 / 法务 / 合规要求查阅历史交付承诺原文
3. 撰写"V2 → V3 演进史"类报告

否则一律以新 Spine（`docs/REQUIREMENTS.md` / `ARCHITECTURE.md` / `ROADMAP.md` / `DEVELOPMENT_PLAN.md` / `RELEASE_GATE.md`）为准。
