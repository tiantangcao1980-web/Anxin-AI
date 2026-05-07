# PROPOSAL · RAG 召回质量基准 + 引用回链 100% 可点

> 任务来源：`docs/audit/_tasks/TASK-07-rag.md` 中 P0-1 / P0-2 / P0-4
> 范围：仅写文档，不改代码；落地动作在后续 PR 中执行
> 关联：`docs/audit/PLAN.md` §1（"必修 P0"通用规约）

---

## 1. 现状盘点

### 1.1 关键链路（grep + 读源码）

| 层 | 文件 | 关键事实 |
|---|---|---|
| 配置 | `backend/src/core/config.py:194-198` | `RAG_TOP_K=5`、`RAG_SCORE_THRESHOLD=0.5`、`RAG_CONTEXT_MAX_LENGTH=4000` |
| RAG 总入口（A 路） | `backend/src/services/rag_service.py:803-809` | 默认 `RAGMode.RERANK`，`top_k=5`、`rerank_top_k=5` |
| RAG 法务专用（B 路） | `backend/src/services/legal_rag.py:108-141` | 默认 `mode="hybrid"`、`max_results=10`，三路 RRF（local/global/vector），权重 `[0.4, 0.3, 0.3]` |
| 向量层 | `backend/src/services/vector_store.py:391-456` | `query_points()`，默认 `top_k=settings.RAG_TOP_K=5`，`score_threshold=0.5` |
| Reranker | `backend/src/services/reranker_service.py:462-472` | **默认 `RerankerType.NONE`**（即未启用），仅在 `LOCAL` 模式下用 `BAAI/bge-reranker-base` |
| 引用追踪 | `backend/src/services/citation_tracker.py:23-69` | `Citation` 仅含 `source_name / article / paragraph / item`，**没有 `source_url` 也没有 `chunk_id`** |
| Chunk 元数据 | `backend/src/services/knowledge_service.py:365-376` | 写入 `chunk_id = f"{doc_id}_{i}"`、`start_index/end_index`，但 `source_url` 不沉淀到向量库 payload |
| 检索 API | `backend/src/api/routes/knowledge.py:325-369, 403-431` | 入参 `top_k=10`（搜索）/`top_k=5`（RAG），传 `org_id=user.org_id` |
| 隔离判断 | `backend/src/services/knowledge_service.py:65, 100` | `if org_id and kb.org_id and ...` —— **truthy 判断，违反 PLAN 要求的 `is not None`** |
| PII | `backend/src/services/pii_service.py` | 已有手机/身份证脱敏器，但 `rag_query` / `search` / `citation_tracker` 路径上**没有任何调用** |
| 前端 RAG 引用 | `frontend/src/components/knowledge-center/SmartSearch.tsx:198-209` | `sources.map` 渲染成 `<span>`，**纯文字、无 `onClick`、无 href**，引用回链可点击率 = 0% |
| 测试 | `backend/tests/` | 仅有 `test_a2ui_action_coverage.py`，**没有任何 RAG 召回质量基准用例** |

### 1.2 必读问题答案

- **Top-k**：默认 5（全局）；`legal_rag` 内部上调到 10 后再 RRF 取前 N。**值偏小**，导致 long-tail query 召回不足。
- **Reranker**：实例化时默认 `NONE`，模型参数写死 `BAAI/bge-reranker-base` 但不会生效；`weight_original=0.3 / weight_rerank=0.7`，`score_threshold=0.0`（不过滤）。
- **Citation → 文档源**：`citation_tracker.extract_citations()` 只用正则匹配文本中的 "《xx》第 N 条"，**不与向量库中的 `chunk_id` 做 join**，也不返回 `source_url`。
- **前端是否可点**：否。`<span>` 纯展示，没有跳转。
- **是否有质量基准**：无。无 `eval/rag_quality.py`，无 recall@k / MRR / NDCG 用例，无黄金问题集。
- **PII + 隔离**：组织过滤是 `if org_id and ...`（truthy），未登录或 org_id 缺失会绕过；PII 脱敏未在检索/RAG 出口接管。

---

## 2. P0-1 召回质量基准设计

### 2.1 黄金问题集

- **位置**：新增 `backend/eval/rag_golden_set.jsonl`（一行一条）
- **规模**：≥ 50 条（DoD 下限），目标 80-100 条
- **覆盖类目**（每类 ≥ 12 条）：
  - 合同合规：劳动合同解除、股权代持、违约金调整
  - 法律法规：民法典物权 / 合同 / 侵权三编、公司法、个保法
  - 诉讼程序：管辖、举证责任、诉讼时效
  - 司法解释 + 判例：最高院公报案例、法释类
- **字段**：

  ```json
  {
    "id": "Q-0001",
    "category": "contract",
    "query": "试用期内员工拒绝签订劳动合同，公司能否解除合同？",
    "relevant_doc_ids": ["doc_uuid_a", "doc_uuid_b"],
    "relevant_chunk_ids": ["doc_uuid_a_3", "doc_uuid_b_0"],
    "expected_law_refs": ["劳动合同法:第10条", "劳动合同法:第39条"],
    "difficulty": "medium",
    "annotator": "legal_team_alice"
  }
  ```

### 2.2 指标

- **recall@k**（k = 5/10/20）：`|relevant ∩ retrieved_topk| / |relevant|`
- **MRR**：第一条命中 relevant 的倒数排名
- **NDCG@10**：等级化相关度（命中 article+paragraph 全对 = 3，仅 article 对 = 2，仅同部门法 = 1，否则 0）
- **citation accuracy**：生成回答中提取的 `Citation.full_reference` 与 `expected_law_refs` 的 F1

### 2.3 自动化跑分脚本

- **位置**：`backend/eval/rag_quality.py`（独立脚本 + 可被 pytest 包装）
- **接口**：
  ```python
  python -m backend.eval.rag_quality --golden eval/rag_golden_set.jsonl \
       --mode hybrid --top-k 10 --rerank --out eval/baseline_$(date +%F).json
  ```
- **输出**：`eval/rag_baseline.json`（含 per-category + 总指标 + 配置 hash）
- **CI smoke**：`backend/tests/eval/test_rag_smoke.py` 抽样 ≤ 10 条，断言 `recall@10 ≥ baseline_recall - 0.05`（防退化）
- **跑通顺序**：先跑 baseline → 再做 P0-5 调参（top-k 5/10/20 × rerank 阈值 0.3/0.5/0.7）→ 出对比表

---

## 3. P0-2 引用回链 100% 可点

### 3.1 前端现状

`SmartSearch.tsx:202-206`：

```tsx
{ragAnswer.sources.map((s, i) => (
  <span ...>{s.title || s.source || `来源 ${i+1}`}</span>
))}
```

- 无 `onClick` / `href` / `data-doc-id`，无法跳转
- `s` 字段从后端 `RAGContext.sources` 透传，目前仅含 `index/id/title/source/content_snippet/score`

### 3.2 后端现状

`citation_tracker.Citation.to_dict()` 输出字段：`text/source_type/source_name/article/paragraph/item/confidence/verified/reference`，**缺 `doc_id` / `chunk_id` / `source_url` / `start_index`**。

`rag_service.build_context():403-410` 写入 `sources[i]`：`index/id/title/source/content_snippet/score`，同样**缺定位字段**。

### 3.3 修法方向（不在本文档落地）

1. **后端 Source 模型扩展**（新增字段，不改旧字段）：
   - `doc_id`（KnowledgeDocument.id）
   - `chunk_id`（来自 vector payload）
   - `chunk_start / chunk_end`（来自分块 metadata）
   - `source_url`（KnowledgeDocument.source_url，已有列）
   - `anchor_text`（chunk 前 30 字，用于前端 fuzzy 高亮兜底）
2. **citation_tracker 增强**：与向量库 + `KnowledgeDocument` 表做 join，让正则提取出的 `《xx》第 N 条`回填到具体 `chunk_id`。
3. **前端**：
   - `<span>` → `<a onClick={openSourceDrawer(s.doc_id, s.chunk_id, s.anchor_text)}>`
   - 复用 `KnowledgeBaseManager.tsx` 既有文档详情抽屉，传 `chunk_id` 滚动 + 高亮
   - 外链型 `source_url` 用 `target="_blank" rel="noopener"`
4. **链接健康巡检脚本**：`scripts/audit_citation_links.py`
   - 拉所有 `KnowledgeDocument`，回放最近 N 天 RAG 日志的 `sources`
   - 校验每条 `doc_id/chunk_id` 都在库且未删除
   - 输出 `docs/audit/07-rag/citation-link-health-report.md`，断链率必须 = 0%

### 3.4 缺失场景排查

| 场景 | 现状是否可点 | 修后期望 |
|---|---|---|
| RAG 回答里 `sources[i]` | 否 | 是（doc 抽屉 + chunk 高亮）|
| 法条正则匹配（无入库） | 否 | 弱可点（跳到法条详情页或 fallback 搜索）|
| 司法解释 / 案号 | 否 | 弱可点（同上）|
| 跨知识库引用 | 否 | 是（带 kb_id 路由）|
| 用户已无权限的 doc | 否 | **保持不可点 + 提示"无权访问"**（不做静默 404）|

---

## 4. PII 脱敏（KB 中跨租户场景）

- **现状**：`pii_service.py` 已有 `PHONE / ID_CARD / EMAIL` 正则脱敏，但 `knowledge.py:325-369`（search）和 `:403-431`（rag_query）直接把 `KnowledgeDocument.content` / chunk 内容回吐，未走脱敏。
- **风险路径（最差）**：A 组织员工把含手机号/身份证的合同入库 → B 组织员工通过 `is_public=true` 或 `org_id` truthy 漏判 → 命中后明文回显。
- **修法方向**：
  1. 在 `KnowledgeService.search / rag_query` 出口加统一 `pii_service.scrub_pii()` 装饰：
     - 跨组织命中（`hit.org_id != user.org_id` 但 `is_public=True`）→ **强脱敏**
     - 同组织命中 → 按用户角色配置（默认弱脱敏，仅手机/身份证）
  2. `citation_tracker` 在写入 graph 前对 `source_name` 做长度限制 + PII 检测，避免人名手机号被建索引。
  3. 服务层组织过滤改 `is not None`（一并修 P0-4）：
     - `knowledge_service.py:65`：`if org_id is not None and kb.org_id is not None and ...`
     - `knowledge_service.py:100`：同上
     - 加无 org 用户的负向测试：跨组织查询应返回 403 / 空集

---

## 5. 实施步骤

| Step | 动作 | 产出 | 谁做 |
|---|---|---|---|
| S1 | 抓 `KnowledgeBase` / `KnowledgeDocument` 真数据，按 4 类挑 80 条 | `eval/rag_golden_set.jsonl` v1（人工标注） | 法务 + 后端 |
| S2 | 写 `eval/rag_quality.py` + smoke pytest | baseline JSON + CI 钩子 | 后端 |
| S3 | 跑 baseline，固化 `eval/rag_baseline.json`（不调参） | baseline 报告 | 后端 |
| S4 | 后端 Source 模型扩展（doc_id/chunk_id/source_url/anchor_text） | rag_service / citation_tracker / knowledge_service patch | 后端 |
| S5 | 前端 `SmartSearch.tsx` + 文档抽屉，引用变 `<a>` | UI patch | 前端 |
| S6 | 链接健康巡检脚本 + 报告 | `citation-link-health-report.md`（断链=0） | 后端 |
| S7 | PII 出口装饰 + 组织 `is not None` 修复 + 负向测试 | service patch + pytest | 后端 |
| S8 | top-k 扫描（5/10/20） × rerank 阈值（0.3/0.5/0.7） | `03-fixes.md` 调优对比表 | 后端 |
| S9 | Playwright：搜索 → 点引用 → 抽屉高亮三场景 | E2E case | 前端 |
| S10 | DoD 自检 + 文档化主入口（legal_rag vs rag_service） | `00-prd-reality-gap.md` 收口 | 全员 |

---

## 6. 工时估计

| 类别 | 工时（人日） |
|---|---|
| 黄金问题集标注（80 条） | 2.0（法务）+ 0.5（后端导出脚本）|
| `rag_quality.py` + baseline + smoke CI | 1.0 |
| Source 模型扩展（后端） | 0.5 |
| 前端引用可点 + 抽屉高亮 | 1.0 |
| 链接健康巡检脚本 | 0.5 |
| PII 出口 + `is not None` + 负向测试 | 1.0 |
| top-k / rerank 扫描 + 调优文档 | 0.5 |
| Playwright 三场景 | 0.5 |
| 文档收口（00-05.md + baseline 对比表） | 0.5 |
| **合计** | **7.5 人日**（与任务卡 3-4 天双人并行吻合）|

---

## 7. 风险护栏

1. **不重建索引**：本轮仅"读 + 评估 + 标注"，不动 chunk 策略 / embedding 维度；`vector_store.create_collection` 的 `recreate=True` 路径全程禁用。S4/S8 调参若需重建，按任务卡 §5 走"先备份 Qdrant 快照 → 双库并行 N 天 → 切换"。
2. **不动 prompt**：`backend/src/prompts/` 不在本提案范围；`LEGAL_RAG_SYSTEM_PROMPT`（`rag_service.py:73-86`）即便要调整，必须先 diff 给用户。
3. **PII 脱敏先在 staging 全量回归**：尤其是 `redaction_map` 是否在并发请求下保持单请求隔离（当前是 service 单例，存在跨请求污染风险，是另一颗钉子，本提案不修复，仅记入 `02-issues.md`）。
4. **组织隔离**：S7 改成 `is not None` 后，必须补"无 org 用户跨库读取应 403/空集"用例，否则禁止合并。
5. **前端引用跳转**：跨租户引用必须在权限校验后渲染，不能 client-side 静默 404；详情抽屉接口失败要明确报"无权访问"。
6. **基准回归门槛**：S8 调优若 `recall@10` 提升 < 5pp 且 `MRR` 提升 < 0.05，**不强推上线**，按 DoD 文档化原因。
7. **legal_rag 双轨**：`legal_rag.py` 与 `rag_service.py` 当前并存，本提案明确 `rag_service.RAGService` 为主入口（受 RAG_* 配置统一管理），`legal_rag.LegalRAGService` 退化为"内置法条索引兜底"，**本轮不删任一文件**，仅在 `00-prd-reality-gap.md` 文档化收口。

---

> 完成后请按任务卡 §3 Step 5/6 跑 verification-loop + security-review，并把基线 → 调优对比表写进 `docs/audit/07-rag/03-fixes.md`。
