# -*- coding: utf-8 -*-
"""
RAG-Anything 风格的检索增强子系统

包结构（按 PR 拆分推进）：
- ``ingest/multimodal/`` —— P13-A：MinerU 解析 + 多模态切片（含 IngestResult/Segment 协议）
- ``kg/`` —— P13-B：跨模态知识图谱构建（实体抽取 + 关系映射 + Neo4j 写入）
- ``query/`` —— P13-C：基于 KG 的检索与 re-rank（VLM 增强）

P13-A 引入多模态文档解析子模块（``ingest.multimodal``），与现有
``backend/src/services/chunking_service.py`` 形成"难解析文档分支"
的并行管线，不耦合现有纯文本切块逻辑。

P13-B 仅消费 P13-A 产出的 ``IngestResult.segments`` 协议，对其他子模块零侵入。
P13-C 通过 typing.Protocol 抽象消费 P13-A/B 上游，零 import 耦合。
"""
