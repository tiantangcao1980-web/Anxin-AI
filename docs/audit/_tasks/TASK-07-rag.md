# TASK-07 RAG / 知识库 / 图谱

> 波次 2 · 工时估 3-4 天
> 前置依赖：任务 0（基础设施）；建议任务 6 已经起步（部分语料走对象存储抽象层）
> 必读：`../PLAN.md`、`../00-platform/01-prd-reality-gap.md`、`../00-platform/03-cross-cutting-gaps.md`

---

## 1. 范围

### 要碰的文件
- 后端服务层：
  - `backend/src/services/legal_rag.py`
  - `backend/src/services/rag_service.py`
  - `backend/src/services/agent_rag_service.py`
  - `backend/src/services/vector_store.py`
  - `backend/src/services/reranker_service.py`
  - `backend/src/services/chunking_service.py`
  - `backend/src/services/legal_corpus_loader.py`
  - `backend/src/services/legal_citation.py`
  - `backend/src/services/knowledge_service.py`
  - `backend/src/services/knowledge_management.py`
  - `backend/src/services/graph_service.py`
  - `backend/src/services/entity_extraction_service.py`
  - `backend/src/services/search_dedup_service.py`
  - `backend/src/services/citation_tracker.py`
- 后端路由：
  - `backend/src/api/routes/knowledge.py`
  - `backend/src/api/routes/knowledge_management.py`
- 前端：
  - `frontend/src/pages/KnowledgeBase.tsx`
  - `frontend/src/pages/KnowledgeGraph.tsx`
  - `frontend/src/components/knowledge-center/`
  - `frontend/src/components/knowledge-graph/`

### 不要碰的文件
- `backend/src/prompts/`（任何 prompt 改动需用户先看 diff）
- 文档/合同/案件等其他业务模块的服务（仅复用其只读接口）
- `frontend/src/lib/design-tokens.ts`
- 已有向量库的物理数据文件（重建必须先备份）

---

## 2. 必修 P0（带文件:行号 + 期望状态）

| # | 关键位置 | 现状 | 期望 |
|---|---|---|---|
| P0-1 | `legal_rag.py` / `rag_service.py` 召回主流程 | 没有 recall@k / MRR 基准 | 新增 `eval/rag_quality.py`：固定问题集 → 跑 recall@k(k=5/10/20)、MRR、NDCG@10；CI 里跑 smoke 子集 |
| P0-2 | `citation_tracker.py` + 前端引用展示 | 引用回链有断链/锚定不准 | 100% 引用可点击 → 跳转到原文 chunk 高亮位置；增加链接健康巡检脚本 |
| P0-3 | `frontend/src/components/knowledge-graph/` + `graph_service.py` | 大数据量节点全量渲染卡顿 | 节点 > 200 自动降采样 / 力导向降级到 2D；引入虚拟化或聚类视图，FPS ≥ 30 @ 1k 节点 |
| P0-4 | `knowledge.py` / `knowledge_management.py` 检索接口 | PII 不脱敏 + 跨组织可见 | 命中前 RBAC 过滤 + 命中后 PII 脱敏（手机号/身份证/邮箱）；写组织隔离测试 |
| P0-5 | `reranker_service.py` + chunking 配置 | top-k / reranker 阈值未调 | 基于 P0-1 基准做 top-k 扫描（5/10/20）+ rerank 阈值（0.3/0.5/0.7），出最佳组合 + 文档化 |

---

## 3. 流程（Step 0-6）

### Step 0 · PRD vs 代码差分（强制）
产出 `docs/audit/07-rag/00-prd-reality-gap.md`：
- PROJECT_STATUS / ROADMAP 中"RAG 已完成、知识图谱已上线"vs 实测召回质量与回链可点击率的差距
- legal_rag 与 agent_rag_service 角色边界是否模糊（双轨 / 谁是主入口）
- 列 PII 与组织隔离的当前最差路径

### Step 1 · 检索复用
- `/hierarchical-memory find-feature "RAG 召回评估 recall MRR"`
- `/hierarchical-memory find-bugfix "向量库重建 备份"`
- `/iterative-retrieval` 按 路由 → 服务 → 向量层 → 前端 分层读

### Step 2 · 建质量基准（最优先）
- 设计黄金问题集（≥ 50 条，覆盖合同/合规/诉讼/法律法规四类）
- 跑当前 recall@5/10/20、MRR、NDCG@10，写入 `eval/rag_baseline.json`
- **不动 chunk 策略前先跑基线**——这是后续所有调优的对照

### Step 3 · 引用回链 + RBAC + PII
- 修 `citation_tracker.py` 锚点对齐；前端高亮匹配定位
- 检索接口入口加 org_id 过滤；服务层 `if org_id is not None`（不要 truthy 判断）
- 出口加 PII 脱敏中间件（复用已有或新建 `pii_redactor.py`）

### Step 4 · 调参 + 图谱性能
- top-k / rerank 阈值扫描（用 Step 2 基准）
- 图谱大数据量降级：节点聚类 / 视图层级 / 帧率监控

### Step 5 · 验证回路
- `/verification-loop`：pytest（含 RAG 评估 smoke）+ tsc + lint + build
- `/security-review`：对照 PROJECT_STATUS 跨组织隔离钉子
- 前端 Playwright：知识库搜索 + 引用跳转 + 图谱大节点降级三场景

### Step 6 · 沉淀
- `add-feature --name "rag_quality_baseline" --pattern "recall@k + MRR + NDCG"`
- `add-bugfix --symptom "知识库越权可见" --fix "org_id is not None + 出口脱敏"`
- 写 `docs/audit/07-rag/03-fixes.md` 时附 baseline 对比表

---

## 4. 输出物

```
docs/audit/07-rag/
├─ 00-prd-reality-gap.md
├─ 01-prd-coverage.md
├─ 02-issues.md
├─ 03-fixes.md            (含 baseline → 调优后对比表)
├─ 04-test-additions.md
└─ 05-followups.md
```

附加：
- `eval/rag_baseline.json` 与 `eval/rag_quality.py`（黄金问题集 + 评估脚本）
- `docs/audit/07-rag/citation-link-health-report.md`（引用回链可点击率）

---

## 5. 风险护栏

- **重建索引 = 高风险**：改 chunk 策略 / embedding 模型 / 向量维度任一，必须**先备份**现有向量库（Qdrant 快照 + 版本号），并写"双库并行 N 天 → 切换"流程
- **不动 prompt**：`backend/src/prompts/` 任一 prompt 改动需 diff 给用户
- **PII 脱敏**：脱敏规则改动会影响所有命中数据；先在 staging 全量回归
- **跨组织隔离**：服务层一律 `is not None`，不许 truthy；多写一组无 org 用户的负向测试用例
- **图谱降级**：默认阈值不能在生产关闭；切换前后录 FPS 对比视频/截图
- **不重做**：legal_rag 与 agent_rag_service 双轨边界由本任务收口，但不在本轮删任一文件，仅文档化主入口

---

## 6. 完成标准（DoD）

- [ ] `eval/rag_quality.py` + 50+ 黄金问题集落地；CI 跑 smoke 子集（≤ 10 条）
- [ ] baseline 报告：recall@10 / MRR / NDCG@10 数字记录在 `docs/audit/07-rag/03-fixes.md`
- [ ] 调优后 recall@10 提升 ≥ 5pp 或 MRR 提升 ≥ 0.05；如无提升，文档化原因
- [ ] 引用回链可点击率 = 100%（健康巡检脚本零断链）
- [ ] 知识图谱在 1k 节点下 FPS ≥ 30；> 200 节点自动降采样
- [ ] 检索接口跨组织越权用例 全部 403 / 空集；服务层使用 `is not None`
- [ ] PII 出口脱敏：手机号/身份证/邮箱 100% 命中
- [ ] 后端 pytest 全绿（baseline → +RAG smoke 用例）；前端 build 无新增警告
- [ ] Playwright 三场景全绿
- [ ] `docs/audit/07-rag/01..05.md` + baseline JSON + 链接健康报告全部产出
- [ ] 经验沉淀到 hierarchical-memory（add-feature + add-bugfix 至少各 1 条）
