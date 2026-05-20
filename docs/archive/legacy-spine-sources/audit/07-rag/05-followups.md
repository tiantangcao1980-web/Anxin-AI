# TASK-07 · Followups

更新时间：2026-05-06

## P0 下一步

1. 跑 live vector baseline
   - 已完成：固定 smoke corpus 通过 live Qdrant + 当前 embedding 配置生成 `eval/rag_live_predictions_smoke.json` 和 `eval/rag_live_baseline_smoke.json`。
   - 待完成：从真实业务知识库导出/检索 full 50 条，复跑 recall@5/10/20、MRR、NDCG@10。
   - 待完成：从真实 `rag_service.query()` 或生产等价链路导出 `retrieved_chunk_ids` 和 `cited_law_refs`。

2. 引用 100% 可点击的剩余闭环
   - 已完成：RAG source 字段扩展、`KnowledgeBase.tsx` 入口、`SmartSearch.tsx` 可点击来源、文档预览、anchor 高亮、纯函数测试、Playwright 浏览器 E2E、导出文档/chunk/anchor 巡检。
   - 待完成：用真实业务知识库导出复跑 citation link audit 和 Playwright smoke。

3. top-k/reranker 调参
   - 参数矩阵：top-k 5/10/20 × reranker threshold 0.3/0.5/0.7。
   - 目标：recall@10 提升 >= 5pp 或 MRR 提升 >= 0.05；否则文档化不调整原因。

## 交付风险

- 当前 smoke baseline 不能作为商业召回质量承诺。
- live Qdrant smoke 只能证明 Qdrant + embedding plumbing 可用，不能替代真实业务知识库质量基线。
- RAG 引用回链已代码级闭环；真实业务数据复跑前，不可把 P0-2 宣传为商业级闭环。
- 图谱已完成代码级 1k 降采样/FPS smoke；真实业务图谱数据复跑前，不应宣传“生产大规模图谱已验证”。
