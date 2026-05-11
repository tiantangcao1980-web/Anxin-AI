# P13-B 跨模态知识图谱构建（KG）

> 借鉴 [HKUDS RAG-Anything](https://github.com/HKUDS/RAG-Anything) 的实体抽取 + 跨模态关系映射思想，
> 把 P13-A 的多模态切片（文本 / 图像 / 表格 / 公式 / 公章 / 签字）整合到 Neo4j 知识图谱里。

## 模块组成

| 文件 | 职责 |
|---|---|
| `base.py` | 数据契约：`Entity`, `Relation`, `KGResult`, `EntityType`(11), `RelationType`(7), `Modality`, `KGBuilder` 抽象基类 |
| `ontology.py` | 法律领域本体（关键词 / 正则 / 分类器） |
| `entity_extractor.py` | LLM-first + 关键词 fallback 实体抽取 |
| `relation_mapper.py` | 同模态 + 跨模态关系映射（`cross_modal=True`） |
| `belongs_to_chain.py` | 文档 → 章 → 节 → 条 → 款 → 项 层级链 |
| `neo4j_writer.py` | 批量 UNWIND MERGE 写入 Neo4j（幂等） |
| `builder.py` | `LegalKGBuilder` 总编排 |

## 与 P13-A 的衔接

`EntityExtractor` / `RelationMapper` 通过 `SegmentLikeProtocol` 消费 P13-A 的
`IngestResult.segments`，所需字段：

```python
segment_id: str
modality: str          # text/image/table/formula/seal/signature
content: str           # 文本内容（图像/表格等也带 OCR 后文本）
metadata: dict         # 例如 {"name": "甲方公章", "page": 3}
```

P13-A 的 `IngestResult.structure` 用于 `BelongsToChainBuilder`，期望形如：

```python
{
  "document": {"id": "...", "title": "..."},
  "outline": [{"id": "ch_1", "level": "chapter", "title": "...", "children": [...]}]
}
```

无 `outline` 时退化为 `ARTICLE_REGEX` 抓 "第 N 条" 的两层链。

## 与 P13-C 的衔接

`KGResult.cross_modal_relations()` 给 retrieval re-rank 用：

- 用户问"合同里有没有甲方公章" → P13-C 检索到文本段命中
- 走 KG 找该段的 `ATTACHED_TO`/`cross_modal=True` 边，定位到对应公章 segment
- 把 image segment + 文本段一起送入 LLM 答题

`belongs_to_chain` 的 `BELONGS_TO` 边用于"沿链向上拉父章上下文"——命中第三条时连同第一章
一起召回。

## 真 LLM 接入的成本估算

按合同/法规文档典型规模估：

| 文档类型 | 切片数 | 每片输入 | LLM 输入总 token | 输出 | 单文档总成本（Claude Sonnet） |
|---|---|---|---|---|---|
| 单页合同（~3 KB 文本） | 6-10 | ~600 token | ~5K | ~1K | ~$0.018 |
| 30 页商业合同（~50 KB） | 60-100 | ~600 token | ~50K | ~10K | ~$0.18 |
| 100 页尽调报告 | 200 | ~600 token | ~150K | ~25K | ~$0.50 |

> 估算基于 prompt 模版（~150 token 固定开销）+ 4000 字截断、Claude 3.5 Sonnet
> $3 / MT in、$15 / MT out。
> 走 **Hunyuan / DeepSeek-V3.2** 价格约为 1/10。

成本优化：
1. `mode="mock"` 离线模式仅用关键词，零 LLM 成本——关系映射阶段总是不耗 LLM
2. 段落级缓存（`entity_id` md5 键）——同名实体只抽取一次
3. 大文档分批：`max_chars_per_call=4000`，按段并发

## API

| 路由 | 描述 |
|---|---|
| `POST /api/v1/rag/kg/build` | 从 ingest_task_id（P13-A 产出）构建 KG |
| `GET /api/v1/rag/kg/{kg_id}/entities` | 列出实体 |
| `GET /api/v1/rag/kg/{kg_id}/relations` | 列出关系 |
| `GET /api/v1/rag/kg/{kg_id}/cross-modal` | 仅跨模态关系（用于前端可视化） |

构建结果默认保存在内存索引（`_KG_INDEX`），生产可按需替换为持久化存储。
