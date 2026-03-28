"""
文档管理服务
"""

import hashlib
from datetime import datetime
from typing import Optional, List, BinaryIO
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from loguru import logger

from src.models.document import Document, DocumentVersion, DocumentType
from src.core.config import settings


class DocumentService:
    """文档管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def upload_document(
        self,
        name: str,
        file_content: bytes,
        mime_type: str,
        doc_type: str = "other",
        org_id: Optional[str] = None,
        case_id: Optional[str] = None,
        created_by: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list] = None,
    ) -> Document:
        """上传文档"""
        # 计算文件哈希
        file_hash = hashlib.sha256(file_content).hexdigest()
        file_size = len(file_content)
        
        # 生成存储路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = self._get_file_extension(mime_type)
        file_path = f"documents/{org_id or 'default'}/{timestamp}_{file_hash[:8]}{file_ext}"
        
        # TODO: 实际存储到MinIO/S3
        # 这里暂时模拟存储路径
        
        # 自动提取文本内容
        extracted_text = None
        try:
            from src.services.document_parser import parse_contract_document
            parse_result = await parse_contract_document(file_content=file_content, file_name=name)
            if parse_result and parse_result.get("text"):
                extracted_text = parse_result["text"]
                logger.info(f"文本提取成功: {name}, 长度: {len(extracted_text)}")
        except Exception as e:
            logger.warning(f"文本提取失败: {name}, 错误: {e}")
        
        document = Document(
            name=name,
            doc_type=DocumentType(doc_type) if doc_type in [e.value for e in DocumentType] else DocumentType.OTHER,
            description=description,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            file_hash=file_hash,
            org_id=org_id,
            case_id=case_id,
            created_by=created_by,
            tags=tags,
            version=1,
            is_latest=True,
            extracted_text=extracted_text,
        )
        
        self.db.add(document)
        await self.db.flush()
        
        logger.info(f"文档上传成功: {name}")
        return document
    
    def _get_file_extension(self, mime_type: str) -> str:
        """根据MIME类型获取文件扩展名"""
        mime_map = {
            "application/pdf": ".pdf",
            "application/msword": ".doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.ms-excel": ".xls",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "text/plain": ".txt",
            "image/jpeg": ".jpg",
            "image/png": ".png",
        }
        return mime_map.get(mime_type, ".bin")
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """获取文档详情"""
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()
    
    async def list_documents(
        self,
        org_id: Optional[str] = None,
        case_id: Optional[str] = None,
        doc_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Document], int]:
        """获取文档列表"""
        query = select(Document).where(Document.is_latest == True)
        count_query = select(func.count(Document.id)).where(Document.is_latest == True)
        
        conditions = []
        if org_id:
            conditions.append(Document.org_id == org_id)
        if case_id:
            conditions.append(Document.case_id == case_id)
        if doc_type:
            conditions.append(Document.doc_type == DocumentType(doc_type))
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(Document.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        documents = list(result.scalars().all())
        
        return documents, total
    
    async def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        document = await self.get_document(document_id)
        if not document:
            return False
        
        # TODO: 从存储中删除文件
        
        await self.db.delete(document)
        return True
    
    async def create_text_document(
        self,
        name: str,
        content: str,
        doc_type: str = "other",
        org_id: Optional[str] = None,
        case_id: Optional[str] = None,
        created_by: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list] = None,
    ) -> Document:
        """创建在线文本文档"""
        content_bytes = content.encode('utf-8')
        return await self.upload_document(
            name=name,
            file_content=content_bytes,
            mime_type="text/markdown", # 默认为 Markdown
            doc_type=doc_type,
            org_id=org_id,
            case_id=case_id,
            created_by=created_by,
            description=description,
            tags=tags
        )

    async def update_document_content(
        self,
        document_id: str,
        content: str,
        updated_by: Optional[str] = None,
        change_summary: Optional[str] = None
    ) -> Optional[Document]:
        """更新文档内容（创建新版本）"""
        document = await self.get_document(document_id)
        if not document:
            return None
            
        # 1. 保存旧版本
        old_version = DocumentVersion(
            document_id=document.id,
            version=document.version,
            file_path=document.file_path,
            file_size=document.file_size,
            file_hash=document.file_hash,
            created_by=document.created_by, # 这里简化，实际应记录谁创建了这个版本
            change_summary="Before update"
        )
        self.db.add(old_version)
        
        # 2. 更新当前文档
        content_bytes = content.encode('utf-8')
        file_hash = hashlib.sha256(content_bytes).hexdigest()
        file_size = len(content_bytes)
        
        # 生成新路径 (为了简单，还是覆盖文件，或者生成新文件)
        # 既然是全功能实现，我们应该生成新文件以保留历史
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 假设原文件名为 foo.md
        original_ext = Path(document.file_path).suffix
        new_path = f"{Path(document.file_path).stem}_v{document.version + 1}_{timestamp}{original_ext}"
        
        # TODO: 实际写入文件系统
        # with open(new_path, 'wb') as f:
        #     f.write(content_bytes)
            
        document.file_path = new_path
        document.file_size = file_size
        document.file_hash = file_hash
        document.version += 1
        document.updated_at = datetime.now()
        document.extracted_text = content # 更新缓存的文本内容
        
        await self.db.flush()
        return document

    async def update_document(
        self,
        document_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list] = None,
    ) -> Optional[Document]:
        """更新文档信息"""
        document = await self.get_document(document_id)
        if not document:
            return None
        
        if name:
            document.name = name
        if description is not None:
            document.description = description
        if tags is not None:
            document.tags = tags
        
        document.updated_at = datetime.now()
        await self.db.flush()
        
        return document
    
    async def analyze_document(self, document_id: str) -> dict:
        """AI分析文档"""
        from src.agents.workforce import get_workforce
        from src.services.document_parser import parse_contract_document
        
        document = await self.get_document(document_id)
        if not document:
            raise ValueError("文档不存在")
        
        workforce = get_workforce()
        
        # 构建分析提示
        analysis_prompt = f"""
请分析以下文档：

文档名称：{document.name}
文档类型：{document.doc_type.value}
文件大小：{document.file_size} 字节
描述：{document.description or '无'}

请提供：
1. 文档摘要（100字以内）
2. 关键要点（3-5个）
3. 涉及的法律实体（公司、人员等）
4. 重要日期和金额
5. 潜在法律风险

以JSON格式返回结果。
"""
        
        try:
            result = await workforce.process_task(
                task_description=analysis_prompt,
                task_type="document_analysis",
                context={
                    "document_id": document_id,
                    "doc_type": document.doc_type.value,
                }
            )
            
            final_result = result.get("final_result", {})
            
            # 解析结果
            if isinstance(final_result, str):
                import json
                import re
                json_match = re.search(r'\{[\s\S]*\}', final_result)
                if json_match:
                    try:
                        final_result = json.loads(json_match.group())
                    except:
                        final_result = {"summary": final_result[:200]}
            
            # 保存摘要到文档
            summary = final_result.get("summary", "")
            if summary:
                document.ai_summary = summary[:500]
                await self.db.flush()
            
            return {
                "document_id": document_id,
                "name": document.name,
                "summary": final_result.get("summary", ""),
                "key_points": final_result.get("key_points", []),
                "entities": final_result.get("entities", []),
                "dates": final_result.get("dates", []),
                "amounts": final_result.get("amounts", []),
                "risks": final_result.get("risks", []),
            }
            
        except Exception as e:
            logger.error(f"文档分析失败: {e}")
            return {
                "document_id": document_id,
                "summary": f"分析失败: {str(e)}",
                "key_points": [],
                "entities": [],
            }
    
    async def get_versions(self, document_id: str) -> List[DocumentVersion]:
        """获取文档版本历史"""
        result = await self.db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version.desc())
        )
        return list(result.scalars().all())
