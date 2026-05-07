# TASK-07 · Test Additions

更新时间：2026-05-06

## 新增测试

| 文件 | 覆盖点 |
|---|---|
| `backend/tests/test_knowledge_rag_security.py` | PII 出口脱敏、KB 权限过滤、无 `kb_ids` 时不扫全局 collection、hybrid 关键词检索隔离、RAG sources 脱敏、citation graph 脱敏 |
| `backend/tests/test_knowledge_management_security.py` | 知识管理接口读写权限分层、无组织用户 fail-closed、案例经验/模板/统计出口脱敏、组织分桶隔离 |
| `backend/tests/eval/test_rag_quality_smoke.py` | `eval/rag_quality.py` 生成 recall@5/10/20、MRR、NDCG@10 smoke baseline |
| `backend/tests/eval/test_citation_link_audit.py` | 引用 source shape、导出文档/chunk/anchor 存在性巡检，且缺失 chunk 时失败 |
| `frontend/src/components/knowledge-center/source-preview-utils.test.ts` | RAG 引用 chip 标签、文档 ID 优先级、外部 URL fallback、anchor 高亮切分 |
| `frontend/src/components/knowledge-graph/graphPerformance.test.ts` | 1k 节点/2k+ 边图谱自动降采样、选中节点上下文保留、渲染边端点安全 |
| `frontend/e2e/rag-source-links.spec.ts` | 司法智库入口、RAG 回答、来源按钮、文档预览、anchor 高亮 |
| `frontend/e2e/knowledge-graph-performance.spec.ts` | 1k 节点图谱桌面/移动视口降采样、FPS >= 30、canvas 非空与截图证据 |

## 已跑命令

```bash
cd backend && ./.venv/bin/pytest -q tests/test_knowledge_rag_security.py tests/eval/test_rag_quality_smoke.py tests/eval/test_citation_link_audit.py
```

结果：`11 passed in 1.68s`。

```bash
cd backend && ./.venv/bin/pytest -q tests/eval/test_rag_quality_smoke.py tests/eval/test_citation_link_audit.py
```

结果：`4 passed in 0.51s`，覆盖 live predictions export 状态识别。

```bash
cd backend && ./.venv/bin/pytest -q tests/test_knowledge_management_security.py
```

结果：`5 passed in 2.29s`。

```bash
cd backend && ./.venv/bin/pytest -q
```

结果：`449 passed, 1 skipped, 17 warnings in 28.60s`。

```bash
cd frontend && npm run lint
cd frontend && npm run test
cd frontend && npm run build
```

结果：lint exit 0；当前最新 Vitest `10 files / 34 tests passed`；build exit 0，保留既有 Vite warning。

```bash
cd frontend && npx playwright test e2e/rag-source-links.spec.ts --project=chromium
```

结果：`1 passed`。

```bash
cd frontend && npx playwright test e2e/knowledge-graph-performance.spec.ts --project=chromium
```

结果：`1 passed`；截图输出到 `frontend/test-results/knowledge-graph-performanc-a74e2-图谱在桌面和移动视口下自动降采样且-canvas-非空-chromium/`。

```bash
cd backend && ./.venv/bin/ruff check --select E,F,I,W src/services/citation_tracker.py src/services/pii_service.py src/services/knowledge_service.py tests/test_knowledge_rag_security.py tests/eval/test_rag_quality_smoke.py tests/eval/test_citation_link_audit.py ../eval/rag_quality.py ../scripts/audit_citation_links.py
```

结果：`All checks passed!`

## 未覆盖

- 已跑 live Qdrant smoke；固定 15 chunk 语料验证 Qdrant + embedding plumbing，并导出 `eval/rag_live_predictions_smoke.json` / `eval/rag_live_baseline_smoke.json`。
- 已跑内建法律知识库 full50 live 检索：42 个 chunk、50 条问题、recall@10 `1.000`、MRR `1.000`、NDCG@10 `0.997`，并写出 release artifacts。
- Playwright 已覆盖 mock API 下的引用点击、文档预览、chunk 高亮；外部客户知识库数据复跑保留为上线后质量扩展。
- 已跑 mock 1k 图谱桌面/移动 FPS 与 canvas 非空 smoke；真实业务图谱数据仍建议在预发环境复跑。
- 全量 backend pytest 已跑；剩余警告为既有 Pydantic V2 deprecated validator、SQLAlchemy async cancel warning 和 Redis close deprecation。
