# -*- coding: utf-8 -*-
"""RAG 服务模块。

P13-A 引入多模态文档解析子模块（``ingest.multimodal``），与现有
``backend/src/services/chunking_service.py`` 形成"难解析文档分支"
的并行管线，不耦合现有纯文本切块逻辑。
"""
