# -*- coding: utf-8 -*-
"""
法律数据导入管道

将采集器产出的 ParsedDocument 列表导入到项目知识库体系中：
  ParsedDocument → KnowledgeService.index_document() → PostgreSQL + Qdrant

支持：
- 幂等导入（基于 external_id + content_hash）
- 自动选择分块策略
- 批量导入与进度报告
- 版本管理（法规更新时递增版本）
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from loguru import logger

# 将项目 backend/src 加入路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy import select, update
from src.core.database import async_session_maker
from src.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeType

# 导入时延迟加载服务，避免循环依赖
_knowledge_service = None
_vector_store = None


async def _get_knowledge_service(db):
    """延迟导入 KnowledgeService"""
    from src.services.knowledge_service import KnowledgeService
    return KnowledgeService(db)


# ==================== 分块策略映射 ====================

KNOWLEDGE_TYPE_CHUNKING_MAP = {
    "law": "legal_article",
    "regulation": "legal_article",
    "interpretation": "legal_article",
    "template": "paragraph",
    "letter": "paragraph",
    "litigation": "paragraph",
    "compliance": "recursive",
    "policy": "recursive",
    "case": "recursive",
    "article": "recursive",
    "other": "recursive",
}


# ==================== 导入管道 ====================


class ImportPipeline:
    """法律数据导入管道"""

    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self._stats = {
            "total": 0,
            "imported": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "error_details": [],
        }

    async def import_documents(
        self,
        documents: list,
        kb_name: str,
        knowledge_type: str = "law",
        description: str = "",
        is_public: bool = True,
        batch_size: int = 50,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        批量导入文档到知识库。

        Args:
            documents: ParsedDocument 列表（或 dict 列表）
            kb_name: 知识库名称（不存在则创建）
            knowledge_type: KnowledgeType value
            description: 知识库描述
            is_public: 是否公开
            batch_size: 每批处理数量
            chunk_size: 分块大小（None 则使用默认值）
            chunk_overlap: 分块重叠（None 则使用默认值）

        Returns:
            导入统计信息
        """
        self._stats = {
            "total": len(documents),
            "imported": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "error_details": [],
        }

        async with async_session_maker() as db:
            try:
                ks = await _get_knowledge_service(db)

                # 1. 获取或创建知识库
                kb_id = await self._ensure_knowledge_base(
                    db, kb_name, knowledge_type, description, is_public
                )

                if not kb_id:
                    return {"success": False, "error": "无法创建知识库", **self._stats}

                # 2. 选择分块策略
                chunking_strategy = KNOWLEDGE_TYPE_CHUNKING_MAP.get(
                    knowledge_type, "recursive"
                )

                # 3. 分批导入
                total = len(documents)
                for batch_start in range(0, total, batch_size):
                    batch = documents[batch_start : batch_start + batch_size]
                    batch_num = batch_start // batch_size + 1
                    total_batches = (total + batch_size - 1) // batch_size

                    self._report(
                        f"正在导入第 {batch_num}/{total_batches} 批 ({len(batch)} 条)...",
                        int(batch_start / total * 100),
                    )

                    for doc in batch:
                        await self._import_single_document(
                            db,
                            ks,
                            kb_id,
                            doc,
                            chunking_strategy,
                            chunk_size,
                            chunk_overlap,
                        )

                    # 每批次后提交
                    await db.commit()

                self._report(
                    f"导入完成: {self._stats['imported']}新增, "
                    f"{self._stats['updated']}更新, "
                    f"{self._stats['skipped']}跳过, "
                    f"{self._stats['errors']}失败",
                    100,
                )

                return {"success": True, "kb_id": kb_id, **self._stats}

            except Exception as e:
                logger.error(f"导入管道异常: {e}")
                await db.rollback()
                return {"success": False, "error": str(e), **self._stats}

    async def _ensure_knowledge_base(
        self,
        db,
        name: str,
        knowledge_type: str,
        description: str,
        is_public: bool,
    ) -> Optional[str]:
        """获取或创建知识库，返回 kb_id"""
        # 查找同名同类型的知识库
        result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.name == name,
            )
        )
        kb = result.scalars().first()

        if kb:
            logger.info(f"使用已有知识库: {name} (id={kb.id})")
            return kb.id

        # 创建新知识库
        try:
            kt = KnowledgeType(knowledge_type)
        except ValueError:
            kt = KnowledgeType.OTHER

        kb = KnowledgeBase(
            name=name,
            description=description,
            knowledge_type=kt,
            is_public=is_public,
            vector_collection=f"kb_{name.replace(' ', '_').lower()}",
        )
        db.add(kb)
        await db.flush()
        logger.info(f"已创建知识库: {name} (id={kb.id}, type={knowledge_type})")
        return kb.id

    async def _import_single_document(
        self,
        db,
        ks,
        kb_id: str,
        doc,
        chunking_strategy: str,
        chunk_size: Optional[int],
        chunk_overlap: Optional[int],
    ):
        """导入单个文档"""
        try:
            # 提取字段（支持 ParsedDocument 对象或 dict）
            if isinstance(doc, dict):
                doc_id = doc.get("doc_id", "")
                title = doc.get("title", "")
                content = doc.get("content", "")
                source = doc.get("source", "")
                source_url = doc.get("source_url", "")
                c_hash = doc.get("content_hash", "")
                law_category = doc.get("law_category", "")
                effective_date = doc.get("effective_date", "")
                issuing_authority = doc.get("issuing_authority", "")
                tags = doc.get("tags", [])
                extra_metadata = doc.get("extra_metadata", {})
            else:
                doc_id = doc.doc_id
                title = doc.title
                content = doc.content
                source = doc.source
                source_url = doc.source_url
                c_hash = doc.content_hash
                law_category = doc.law_category
                effective_date = doc.effective_date
                issuing_authority = doc.issuing_authority
                tags = doc.tags
                extra_metadata = doc.extra_metadata

            if not content or not title:
                self._stats["skipped"] += 1
                return

            # 幂等检查：按 external_id 查找
            existing = None
            if doc_id:
                result = await db.execute(
                    select(KnowledgeDocument).where(
                        KnowledgeDocument.external_id == doc_id,
                        KnowledgeDocument.knowledge_base_id == kb_id,
                        KnowledgeDocument.status == "active",
                    )
                )
                existing = result.scalars().first()

            if existing:
                if existing.content_hash == c_hash:
                    self._stats["skipped"] += 1
                    return
                else:
                    # 内容有变更：标记旧版本为 superseded
                    existing.status = "superseded"
                    await db.flush()
                    self._stats["updated"] += 1

            # 执行索引
            metadata = {
                "law_category": law_category,
                "effective_date": effective_date,
                "issuing_authority": issuing_authority,
                "source_url": source_url,
                "tags": tags,
                **(extra_metadata or {}),
            }

            result = await ks.index_document(
                kb_id=kb_id,
                title=title,
                content=content,
                source=source,
                metadata=metadata,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                chunking_strategy=chunking_strategy,
            )

            if result.get("success"):
                # 更新新文档的扩展字段
                new_doc_id = result["doc_id"]
                await db.execute(
                    update(KnowledgeDocument)
                    .where(KnowledgeDocument.id == new_doc_id)
                    .values(
                        external_id=doc_id,
                        content_hash=c_hash,
                        source_url=source_url,
                        law_category=law_category,
                        effective_date=effective_date,
                        issuing_authority=issuing_authority,
                        tags=tags if tags else None,
                    )
                )
                self._stats["imported"] += 1
            else:
                self._stats["errors"] += 1
                self._stats["error_details"].append(
                    f"{title}: {result.get('error', 'unknown')}"
                )

        except Exception as e:
            self._stats["errors"] += 1
            title_str = title if isinstance(doc, dict) else getattr(doc, "title", "?")
            self._stats["error_details"].append(f"{title_str}: {str(e)}")
            logger.error(f"导入文档失败 [{title_str}]: {e}")

    def _report(self, message: str, progress: int):
        logger.info(f"[ImportPipeline] {message} ({progress}%)")
        if self.progress_callback:
            try:
                self.progress_callback("import", message, progress)
            except Exception:
                pass


# ==================== 便捷函数 ====================


async def import_from_json_file(
    json_path: str,
    kb_name: str,
    knowledge_type: str = "law",
    description: str = "",
) -> Dict[str, Any]:
    """
    从 JSON 文件导入文档到知识库。

    JSON 文件格式: ParsedDocument 字典列表
    """
    path = Path(json_path)
    if not path.exists():
        return {"success": False, "error": f"文件不存在: {json_path}"}

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return {"success": False, "error": "JSON 文件格式错误，应为列表"}

    pipeline = ImportPipeline()
    return await pipeline.import_documents(
        documents=data,
        kb_name=kb_name,
        knowledge_type=knowledge_type,
        description=description,
    )


# ==================== CLI 入口 ====================


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="法律数据导入管道")
    parser.add_argument("json_file", help="ParsedDocument JSON 文件路径")
    parser.add_argument("--kb-name", required=True, help="知识库名称")
    parser.add_argument("--type", default="law", help="知识类型 (law/regulation/template/...)")
    parser.add_argument("--description", default="", help="知识库描述")

    args = parser.parse_args()

    os.chdir(Path(__file__).resolve().parent.parent)

    result = asyncio.run(
        import_from_json_file(
            args.json_file,
            kb_name=args.kb_name,
            knowledge_type=args.type,
            description=args.description,
        )
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
