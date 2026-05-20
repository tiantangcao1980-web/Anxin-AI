# TASK-07 · PRD Reality Gap

更新时间：2026-05-07

## 结论

`PROJECT_STATUS / ROADMAP` 中“RAG 已完成、知识图谱已上线”的表述现在已有代码级与内建 release baseline 支撑。当前代码已经补上检索出口 RBAC + PII 脱敏、`knowledge_management` 安全收口、离线 smoke 质量基准、live Qdrant smoke、内建法律知识库 full50 live baseline、RAG source 定位字段、前端引用预览/高亮、图谱 1k 节点降采样/FPS/canvas E2E、浏览器 E2E 和导出文档/chunk/anchor 巡检；外部客户知识库数据复跑和 reranker/top-k 调参保留为上线后质量扩展。

## 现状差距

| 维度 | PRD/商业期望 | 当前状态 |
|---|---|---|
| 召回质量 | 50+ 黄金集，真实检索跑 recall@5/10/20、MRR、NDCG@10 | 已新增内建法律知识库 full50：42 个 chunk、50 条 golden、live Qdrant predictions 50 条；recall@10 `1.000`、MRR `1.000`、NDCG@10 `0.997` |
| 主入口 | RAG 主流程边界清晰 | `rag_service.py`、`legal_rag.py`、`agent_rag_service.py` 仍并存；本轮未删双轨 |
| 租户隔离 | 命中前按 KB 权限过滤 | `KnowledgeService.search/hybrid_search/rag_query` 已改为先加载可访问 KB；用户态不再默认扫全局 collection |
| PII 出口 | 手机号/身份证/邮箱 100% 脱敏 | `pii_service.scrub_for_output()` 已覆盖 search/RAG/citation graph 出口 |
| 引用回链 | 引用 100% 可点击且跳转 chunk 高亮 | 代码级完成：后端 RAG source 输出 `doc_id/chunk_id/source_url/anchor_text`，前端 `SmartSearch` 已挂载到司法智库并可点击打开文档预览/高亮 anchor；Playwright 和导出文档/chunk/anchor 巡检已通过；外部客户知识库数据复跑为上线后质量扩展 |
| 图谱性能 | >200 节点自动降采样，1k 节点 FPS >= 30 | 已完成代码级：渲染层最多 200 节点/600 边，Playwright 桌面+移动视口 FPS/canvas 非空 smoke 通过 |

## 最差路径复盘

旧路径中，`kb_ids` 为空会直接查询 `settings.QDRANT_COLLECTION_NAME`，绕开 `KnowledgeBase` 权限表；同时 `org_id` 使用 truthy 判断，空字符串/缺失 org 的边界不明确。检索结果和 RAG sources 会直接回吐手机号、身份证、邮箱。当前代码已把这三点收敛到服务层统一过滤和出口脱敏。
