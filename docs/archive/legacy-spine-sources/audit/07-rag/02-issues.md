# TASK-07 · Issues

更新时间：2026-05-06

## 已关闭

| 编号 | 问题 | 处理 |
|---|---|---|
| RAG-SEC-01 | 用户态 `kb_ids=None` 时默认搜索全局 Qdrant collection，绕开 KB 权限表 | `KnowledgeService.search/rag_query` 改为加载可访问 KB collection |
| RAG-SEC-02 | `org_id` / `user_id` truthy 判断导致边界不清 | 服务层访问判断改为 `is not None` |
| RAG-SEC-03 | search/RAG sources 直接回吐手机号、身份证、邮箱 | 新增不可逆出口脱敏，并覆盖 search/hybrid/RAG |
| RAG-SEC-04 | 身份证可能先被手机号正则局部命中 | 身份证规则优先于手机号 |
| RAG-SEC-05 | citation graph 可能沉淀含 PII 的 source_name | citation 字段和 graph sink 做 PII 脱敏 + 长度限制 |
| RAG-QUAL-01 | 没有可复跑的 recall/MRR/NDCG smoke | 新增 `eval/rag_quality.py`、50 条黄金集、smoke baseline |
| RAG-AUTH-01 | `knowledge_management.py` 另一套知识管理接口未纳入 RBAC/PII 收口 | `knowledge_management` 路由改为读/写权限分层、无组织用户 fail-closed，服务出口接入 PII 脱敏 |
| RAG-GRAPH-01 | 图谱 1k 节点性能未验证 | 新增渲染层降采样计划、1k 节点 Vitest 和 Playwright 桌面/移动 FPS/canvas smoke |

## 仍未关闭

| 编号 | 风险 | 下一步 |
|---|---|---|
| RAG-LIVE-01 | `eval/rag_baseline.json` 不是 live Qdrant 运行结果 | 导出真实 RAG predictions 后复跑 full baseline |
| RAG-LINK-01 | 引用链接已完成 mock 数据下前端点击和导出文档/chunk/anchor 巡检，尚未用真实业务知识库复跑 | 用真实业务知识库导出复跑 citation link audit 与 Playwright smoke |
| RAG-TUNE-01 | top-k / reranker 阈值未调参 | 等 live baseline 后跑 5/10/20 × 0.3/0.5/0.7 扫描 |
