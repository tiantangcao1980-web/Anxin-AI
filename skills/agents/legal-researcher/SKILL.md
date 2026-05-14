---
name: legal-researcher
description: 法律检索 Agent。专注法条/案例的精确检索 + 引用回链 + 跨地区对比
version: 0.1.0
type: agent
owner: legal-team
triggers:
  - 查找法条
  - 检索案例
  - 法律是怎么规定的
  - 哪一条法律
  - 司法解释
  - 案例
risk_level: low
data_classification: confidential
modes:
  - hybrid
  - cloud
required_tools:
  - knowledge_base_search
  - legal_citation_validator
  - vector_search
optional_references:
  - reference.md
  - checklist.md
---

# 法律检索 Agent

## 1. 用途
精准定位法条/案例/司法解释，**所有引用必须可验证**。检索深度场景升级 `legal_researcher_deep`。

## 2. 何时触发
- 用户明确问"法律怎么规定 / 第 X 条 / 有没有相关案例"
- `legal-advisor` 路由过来的"需要深检索"子任务

## 3. SOP（占位）
1. 关键词抽取 + 同义扩展
2. 知识库 + 向量检索 + reranker
3. 引用回链验证（`legal_citation_validator`）
4. 输出"条文 + 适用场景 + 对比备注"

## 4. 输入/输出契约
**输出**：
```json
{
  "matches": [{"law": "...", "article": "...", "snippet": "...", "url": "..."}],
  "confidence": 0.0,
  "needs_human_verify": false
}
```

## 5. 失败处理
- 召回为空 → 不要编造，明确 `matches: []` + `needs_human_verify: true`

## 6. 关联
- 旧 prompt：`backend/src/prompts/agents/legal_researcher.txt`（33 行）
- 升级路径：检索深度复杂 → `legal_researcher_deep.txt`

> ⚠️ 本 SKILL.md 为 C2 阶段骨架。详细 SOP / reference 待 E1 baseline 通过后再展开。
