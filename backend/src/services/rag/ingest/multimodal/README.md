# RAG 多模态接入（P13-A）

借鉴 [HKUDS/RAG-Anything](https://github.com/HKUDS/RAG-Anything) 架构，为
"安心智能助手 V3"补足"难解析文档分支"：合同 PDF、扫描件、公章图、证据
照片、财务报表 Excel 截图。

## 模块边界

```
rag/ingest/multimodal/
├── base.py                # MultimodalIngestor 抽象 + ParsedSegment / IngestResult
├── mineru_adapter.py      # MinerU 适配器（mock + 真接入 TODO）
├── modality_router.py     # text / image / table / formula / seal 分流
├── seal_detector.py       # 公章识别（mock：red_ratio 启发式）
├── table_extractor.py     # markdown ↔ 二维表
├── formula_recognizer.py  # LaTeX 清洗 + mathpix/nougat 接入位点
└── layout_preserver.py    # 章 / 节 / 条 / 款 / 项 层级正则
```

## 与并行工单的衔接

| 工单 | 输出 | 衔接契约 |
|---|---|---|
| P13-A（本工单） | `IngestResult.segments`（统一 schema） | 唯一上游 |
| P13-B（KG） | 节点 / 关系图谱 | 消费 `segments` + `structure` |
| P13-C（VLM Query） | 多模态检索 | 消费 `segments`（image/table/formula） |
| P13-D（前端 dashboard） | 解析进度 / 结果展示 | 消费 `IngestResult.statistics` |

P13-A **只生产 segment**，不调用 P13-B/C 的代码；这些模块互相通过
`IngestResult` 数据契约解耦。

## 真接入 MinerU 的复杂度

- **依赖体积**：`pip install magic-pdf` ≈ 2 GB（含 paddle / detectron2 / 模型权重）。
- **首次启动**：模型懒加载 5-15 秒。
- **GPU 加速可选**：CPU 也能跑，PDF 单页约 2-5 秒。
- **接入成本**：~1 工作日（SDK），主要耗时在 ``content_list`` → ``ParsedSegment``
  字段映射 + 边界 case（加密 PDF、扫描件 OCR 失败、超大文档分页流式）。

详细接入计划见各模块 ``TODO(p13a-real)`` 注释。

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/rag/ingest/multimodal` | 上传文件 → 异步入队 → 返回 `task_id` |
| GET  | `/api/v1/rag/ingest/{task_id}`   | 查询解析状态 + 结果 |

异步任务后端当前用内存 store（mock）；接 Celery 见 ``rag_ingest`` 路由
``TODO(p13a-celery)`` 注释。
