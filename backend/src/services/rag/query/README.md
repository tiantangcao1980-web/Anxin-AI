# P13-C VLM 增强 Query

借鉴 [HKUDS RAG-Anything](https://github.com/HKUDS/RAG-Anything) 的 VLM-Enhanced Query 模式：检索时把命中段附带的图（合同附件图 / 证据照片 / 公章 / 财务表截图）一起喂给 VLM 作答，返回带 `visual_grounding` 的结构化引文响应。

## 模块结构

| 文件 | 职责 |
|------|------|
| `base.py` | 数据类（`MultimodalQueryRequest` / `RetrievedSegment` / `VLMQueryResponse`）+ 上游依赖 Protocol |
| `multimodal_retriever.py` | 向量+BM25 → KG boost → 模态扩展 → 模态加权重排 → top_k |
| `modality_weighted_ranker.py` | 默认权重 + 关键词触发的动态权重表 |
| `vlm_query_engine.py` | 命中段附图 → base64 → GPT-4o vision；不支持时降级纯文本 |
| `citation_aggregator.py` | DeepTutor 风格引文（扁平 + 按文档分组） |

## 流程

```
MultimodalQueryRequest
        │
        ▼
MultimodalRetriever
  ├─ VectorSearcher.search          ← P13-A 多模态切片
  ├─ ModalityExpander.expand         ← cross_modal 关系
  ├─ KGBooster.boost                 ← P13-B 知识图谱
  └─ ModalityWeightedRanker.rerank
        │
        ▼  list[RetrievedSegment]
VLMQueryEngine.query
  ├─ 拆 text / visual segments
  ├─ images → base64 → VLMClient.chat_with_vision
  │       支持 vision → 真 VLM
  │       不支持      → 纯文本降级
  └─ CitationAggregator.aggregate
        │
        ▼
VLMQueryResponse(answer, citations, visual_grounding, confidence, vlm_used)
```

## 与 P13-A / P13-B 的衔接

本模块只通过 `Protocol` 依赖上游：

- `VectorSearcher`：由 P13-A 实现（落地后改为消费 `chunking_service.search_multimodal()`）
- `KGBooster`：由 P13-B 实现（落地后改为消费 KG 实体命中）
- `ModalityExpander`：由 P13-A 实现（落地后改为查 cross_modal 关系表）

在三者完成前，路由层用 stub 实现注入；测试覆盖 mock 行为。

## 模态默认权重

| Modality | Weight |
|----------|-------:|
| text     | 1.00   |
| table    | 0.90   |
| formula  | 0.85   |
| image    | 0.70   |
| seal     | 0.60   |

按 query 关键词动态调整：

- "公章" / "印鉴" / "盖章" → seal=1.00
- "金额" / "增值税" / "总价" → table=1.00, formula=0.95
- "条款" / "义务" → text=1.00, image=0.50
- "证据" / "照片" → image=1.00
- "公式" / "计算" → formula=1.00

## VLM 成本估算

按典型法律咨询 query：

- 文本上下文：top_k=10 段，每段 ≤ 400 字符 ≈ 4 KB → 约 1500-2500 input tokens
- 图片：上限 4 张（image / seal），每张以 GPT-4o vision low-detail 计 ≈ 85 tokens；high-detail ≈ 765 tokens（按 768×768）→ 4 张 high ≈ 3000 tokens
- 输出 ≈ 400-800 tokens

**单次调用 ≈ 5-7K tokens**。GPT-4o 目前 input ≈ $2.5 / 1M, output ≈ $10 / 1M → 单次 **约 $0.02-0.04**（≈ 0.15-0.30 元）。开了 vision 是纯文本的 2-3×。控成本手段：

- `max_images=4`（已默认）
- 命中视觉模态才走 VLM；否则降级
- `enable_vlm=False` 用 `/text-only` 端点，价格回到纯文本水平
- 可在 `vlm_query_engine.system_prompt` 之外再压缩 `max_chars_per_seg`

## API endpoints

挂载于 `/api/v1/rag/query`：

- `POST /multimodal`：完整多模态 query
- `POST /text-only`：仅文本（fallback / 不开 VLM）
- `GET  /health`：检索器组件 + VLM vision 能力

## 测试

```
backend/tests/test_multimodal_retriever.py
backend/tests/test_vlm_query_engine.py
backend/tests/test_modality_weighted_ranker.py
backend/tests/test_citation_aggregator.py
backend/tests/test_rag_query_api.py
```

均使用 mock，不依赖真实 vector store / LLM。
