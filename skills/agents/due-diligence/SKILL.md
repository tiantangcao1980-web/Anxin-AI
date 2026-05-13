---
name: due-diligence
description: 尽职调查 Agent。基于公司名/统一信用代码做工商、诉讼、舆情、关联关系扫描
version: 0.1.0
type: agent
owner: legal-team
triggers:
  - 尽调
  - 尽职调查
  - 公司背景
  - 调查这家公司
  - 这家公司怎么样
  - 有没有诉讼
risk_level: medium
data_classification: confidential
modes:
  - hybrid
  - cloud
required_tools:
  - investigation_orchestrator
  - web_search
  - knowledge_base_search
  - sentiment_signals
optional_references:
  - reference.md
  - checklist.md
---

# 尽职调查 Agent

## 1. 用途
对企业做"工商基本信息 → 诉讼涉案 → 舆情 → 关联关系 → 风险评分"五维扫描，输出可读报告 + A2UI 卡片。

## 2. 何时触发
- 用户消息含公司名/统一信用代码 + 调查意图
- `chat_due_diligence_routing` 强路由命中

## 3. SOP（占位）
1. 实体抽取（公司名/USCC）→ 验证存在性
2. `investigation_orchestrator.run()` 触发并行抓取
3. 结果聚合 → `risk-assessor` 计算风险分
4. 输出 A2UI `due_diligence_summary` 事件

## 4. 输出契约
```json
{
  "company": {"name": "...", "uscc": "...", "status": "..."},
  "litigation": {"count": 0, "high_risk": false, "samples": []},
  "sentiment": {"score": 0, "trend": "stable", "alerts": []},
  "relations": [...],
  "risk_score": 0.0,
  "summary": "..."
}
```

## 5. 失败处理
- 公司名抽取失败 → 反问用户精确公司名
- 抓取超时 → 部分返回 + `incomplete: true`
- 触发对方反爬 → 自动降低频率，不重试硬怼

## 6. 关联
- 旧 prompt：`backend/src/prompts/agents/due_diligence.txt`（46 行）
- service：`investigation_orchestrator`、`investigation_data_store`
- 测试：`tests/test_due_diligence_intent.py`、`tests/test_chat_due_diligence_routing.py`

> ⚠️ 抓取频控参数任何调整必须先评估对方反爬阈值，不可一次性放大并发。
