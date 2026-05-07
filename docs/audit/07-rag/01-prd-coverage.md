# TASK-07 · PRD Coverage

更新时间：2026-05-07

| P0 | 目标 | 覆盖状态 |
|---|---|---|
| P0-1 质量基准 | `eval/rag_quality.py` + recall@5/10/20、MRR、NDCG@10 | 已完成内建 release baseline：50 条 golden、42 个 corpus chunk、live Qdrant predictions、baseline JSON、pytest 保护均已落地；recall@10 `1.000`、MRR `1.000`、NDCG@10 `0.997` |
| P0-2 引用回链 | 100% 可点击、chunk 高亮、健康巡检 | 代码级完成：RAG source 字段、司法智库入口、前端可点击预览/anchor 高亮、Playwright 浏览器 E2E、导出文档/chunk/anchor 巡检和前端纯函数测试已落地；外部客户知识库数据复跑为上线后质量扩展 |
| P0-3 图谱性能 | >200 节点降采样，1k 节点 FPS >= 30 | 已完成代码级：`graphPerformance.ts` 渲染计划 + 1k 节点 Vitest + Playwright 桌面/移动 canvas/FPS smoke |
| P0-4 RBAC + PII | 命中前权限过滤，命中后脱敏，组织隔离测试 | 已完成后端核心路径：search、hybrid_search、rag_query、citation graph |
| P0-5 调参 | 基于 P0-1 跑 top-k/reranker 扫描 | 当前内建 baseline 达标；外部客户知识库接入后再跑 top-k/reranker 扫描 |

## 已覆盖代码路径

- `backend/src/services/knowledge_service.py`
  - `_access_filter()` 使用 `is not None`。
  - `_load_accessible_kbs()` 统一加载可访问 KB。
  - `search()`、`hybrid_search()`、`rag_query()` 不再默认查全局 collection。
  - 检索/RAG 响应递归走 `pii_service.scrub_for_output()`。
- `backend/src/services/pii_service.py`
  - 新增不可逆出口脱敏。
  - 身份证先于手机号匹配，避免身份证内部号段被局部误遮盖。
  - 邮箱纳入 `scrub()` 和 `scrub_for_output()`。
- `backend/src/services/citation_tracker.py`
  - citation 返回值、graph nodes、graph sink 名称统一 PII 脱敏和长度限制。
- `backend/src/services/rag_service.py`
  - RAG sources 补齐 `doc_id`、`chunk_id`、`source_url`、`anchor_text`、`chunk_start`、`chunk_end` 和 `content_snippet`。
- `frontend/src/components/knowledge-center/SmartSearch.tsx`
  - RAG sources 从纯文本改为可点击按钮，支持打开文档预览并高亮命中的 anchor。
- `frontend/src/pages/KnowledgeBase.tsx`
  - “司法智库”页新增“智慧搜索”入口，避免 `SmartSearch` 只存在于未挂载组件中。
- `frontend/src/components/knowledge-center/source-preview-utils.ts`
  - 引用标签、文档 ID、外部 URL 和 anchor 高亮切分抽成纯函数。
- `scripts/audit_citation_links.py`
  - 从 source shape 巡检扩展为可选导出文档/chunk/anchor 存在性巡检。
- `eval/rag_live_qdrant_smoke.py`
  - 启动 live Qdrant/embedding plumbing smoke，写入临时 collection 并导出 predictions。
- `eval/rag_quality.py`
  - 能识别 live predictions export，避免把 live 导出误标为 offline。
- `eval/export_builtin_legal_full50.py`
  - 从内建法律语料导出 42 个 chunk 和 50 条 golden，避免 smoke 数据冒充商业基线。
- `eval/rag_live_qdrant_full50.py`
  - 运行 full50 preflight、Qdrant live indexing/query 和 predictions 导出。

## 覆盖证据

- `backend/tests/test_knowledge_rag_security.py`
- `backend/tests/eval/test_rag_quality_smoke.py`
- `backend/tests/eval/test_rag_full50_runner.py`
- `backend/tests/eval/test_citation_link_audit.py`
- `frontend/src/components/knowledge-center/source-preview-utils.test.ts`
- `frontend/e2e/rag-source-links.spec.ts`
- `backend/tests/eval/test_rag_quality_smoke.py`
