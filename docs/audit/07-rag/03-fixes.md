# TASK-07 · Fixes

更新时间：2026-05-06

## 本轮修复

1. 后端知识检索权限收口
   - `KnowledgeService._access_filter()` 统一公开/本人/同组织过滤。
   - `search()`、`hybrid_search()`、`rag_query()` 先取可访问 KB collection，再执行检索。
   - 用户态 `kb_ids=None` 不再隐式查询全局 `legal_knowledge` collection。

2. PII 出口脱敏
   - `pii_service.scrub_for_output()` 对字符串、dict、list 递归处理。
   - 手机号：`13812345678` -> `138****5678`。
   - 身份证：`11010119900101123X` -> `110101********123X`。
   - 邮箱：`zhang.san@example.com` -> `z***@example.com`。
   - search/RAG/citation graph 均已接入。

3. 质量基准
   - 新增 `eval/rag_quality.py`。
   - 新增 `eval/rag_golden_set.jsonl`，共 50 条，覆盖 contract / labor / compliance / litigation。
   - 新增 `eval/rag_predictions_smoke.json` 和 `eval/rag_baseline.json`。
   - 新增 pytest smoke，确保 CI 可跑 recall@k、MRR、NDCG@10。
   - 新增 `eval/rag_live_qdrant_smoke.py`，用 live Qdrant + 当前 embedding 配置跑固定 smoke corpus。
   - 新增 `eval/rag_live_predictions_smoke.json` 和 `eval/rag_live_baseline_smoke.json`。
   - `rag_quality.py` 已能区分 offline predictions 与 live predictions export。

4. 引用链接巡检
   - 新增 `scripts/audit_citation_links.py`。
   - 新增 `eval/citation_sources_smoke.json`。
   - 新增 `eval/citation_documents_smoke.json`。
   - 巡检从 source shape 扩展到导出文档/chunk/anchor 存在性。
   - 生成 `docs/audit/07-rag/citation-link-health-report.md`。

5. 引用来源可点击预览
   - `rag_service.build_context()` 的 sources 补齐 `doc_id`、`chunk_id`、`source_url`、`content_snippet`、`anchor_text`、`chunk_start` 和 `chunk_end`。
   - `SmartSearch.tsx` 将 RAG sources 从文本 chip 改为可点击按钮。
   - `KnowledgeBase.tsx` 挂载“智慧搜索”入口，形成用户可进入的产品路径。
   - 有 `doc_id` 时调用 `/knowledge/documents/{doc_id}` 打开文档预览并高亮 `anchor_text`；只有 `source_url` 时打开外部来源。
   - 新增 `source-preview-utils.ts` 和对应 Vitest，锁住 source label、文档定位、外部 URL fallback 和 anchor 高亮切分。
   - 新增 `frontend/e2e/rag-source-links.spec.ts`，覆盖“司法智库 -> 智慧搜索 -> RAG问答 -> 来源按钮 -> 文档高亮”浏览器路径。

6. 知识管理接口安全收口
   - `knowledge_management` 路由改为 `READ_KNOWLEDGE` / `WRITE_KNOWLEDGE` 分层，不再只要求登录。
   - 无 `org_id` 用户访问知识管理接口时 fail-closed，避免退化到共享 `default` 分桶。
   - 案例经验、模板、推荐和统计出口统一接入 `pii_service.scrub_for_output()`。
   - 案例经验和自定义模板 ID 改为 UUID，避免同秒创建时 ID 碰撞。

7. 知识图谱大图渲染降级
   - 新增 `graphPerformance.ts`，渲染层默认最多保留 200 节点、600 边。
   - 降采样保留选中/中心节点邻域、高关联节点，并按类型轮转补齐，避免大图只剩单一类型。
   - `ForceGraphCanvas` 和 `KnowledgeGraphExplorer` 均接入渲染计划；大图模式下降低粒子数量和 warmup/cooldown ticks。
   - 新增 `graphPerformance.test.ts`，用 1k 节点/2k+ 边锁住自动降采样与选中上下文保留。
   - 新增 `knowledge-graph-performance.spec.ts`，在桌面和移动视口验证 1k 图谱自动降采样、FPS >= 30、canvas 非空，并输出截图。

## Baseline

当前商业质量 baseline 已补内建法律知识库 full50 live 检索；旧 smoke 结果继续保留为 Qdrant + embedding plumbing 诊断，不作为商业 release baseline。

| 模式 | 问题数 | recall@5 | recall@10 | recall@20 | MRR | NDCG@10 | Citation F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| built-in/full50-live-qdrant | 50 | 1.000 | 1.000 | 1.000 | 1.000 | 0.997 | 0.544 |
| smoke/offline | 10 | 0.950 | 0.950 | 0.950 | 0.900 | 0.871 | 0.933 |
| smoke/live-qdrant | 10 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.650 |

按类别：

| 类别 | 问题数 | recall@10 | MRR | NDCG@10 |
|---|---:|---:|---:|---:|
| contract | 4 | 1.000 | 0.875 | 0.908 |
| labor | 4 | 1.000 | 0.875 | 0.868 |
| compliance | 1 | 1.000 | 1.000 | 1.000 |
| litigation | 1 | 0.500 | 1.000 | 0.613 |

## Verification

```bash
python3 eval/rag_quality.py --golden eval/rag_golden_set.jsonl --predictions eval/rag_predictions_smoke.json --out eval/rag_baseline.json --smoke --run-label rag-quality-smoke-baseline-2026-05-06
./backend/.venv/bin/python eval/rag_live_qdrant_smoke.py --out eval/rag_live_predictions_smoke.json --collection rag_eval_smoke_live_20260506
python3 eval/rag_quality.py --golden eval/rag_golden_set.jsonl --predictions eval/rag_live_predictions_smoke.json --out eval/rag_live_baseline_smoke.json --smoke --run-label rag-live-qdrant-smoke-2026-05-06
python3 scripts/audit_citation_links.py --sources eval/citation_sources_smoke.json --documents eval/citation_documents_smoke.json --out docs/audit/07-rag/citation-link-health-report.md
cd backend && ./.venv/bin/pytest -q tests/test_knowledge_rag_security.py tests/eval/test_rag_quality_smoke.py tests/eval/test_citation_link_audit.py
cd backend && ./.venv/bin/pytest -q tests/test_knowledge_management_security.py
cd backend && ./.venv/bin/pytest -q
cd backend && ./.venv/bin/ruff check --select E,F,I,W src/services/citation_tracker.py src/services/pii_service.py src/services/knowledge_service.py tests/test_knowledge_rag_security.py tests/eval/test_rag_quality_smoke.py tests/eval/test_citation_link_audit.py ../eval/rag_quality.py ../scripts/audit_citation_links.py
cd frontend && npm run lint
cd frontend && npm run test
cd frontend && npm run build
cd frontend && npx playwright test e2e/rag-source-links.spec.ts --project=chromium
cd frontend && npx playwright test e2e/knowledge-graph-performance.spec.ts --project=chromium
```

结果：

- RAG smoke baseline：`recall@10=0.950`，`MRR=0.900`，`NDCG@10=0.871`。
- RAG live Qdrant smoke：`indexed_chunks=15`，`predictions=10`，`recall@10=1.000`，`MRR=1.000`，`NDCG@10=1.000`，`citation_f1=0.650`。
- Citation link smoke：`total=3`，`clickable=3`，`broken_rate=0.00%`，`missing_targets=0`，`missing_anchors=0`。
- RAG targeted pytest：11 passed。
- Knowledge management security pytest：5 passed。
- Backend full pytest：449 passed, 1 skipped, 17 warnings in 28.60s。
- Ruff selected checks：All checks passed。
- Frontend lint：exit 0。
- Frontend Vitest：当前最新 10 files / 34 tests passed。
- Frontend build：exit 0，保留既有 Vite 动态导入、chunk size 和 `lottie-web` eval warning。
- RAG source Playwright：1 passed。
- Knowledge graph 1k Playwright：1 passed，覆盖桌面/移动视口、FPS >= 30、canvas 非空和截图证据。
