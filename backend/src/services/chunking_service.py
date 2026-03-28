"""
文档分块服务

实现智能文本分块，支持多种分块策略：
- 按段落分块
- 按句子分块
- 按固定长度分块（带重叠）
- 递归分块（智能分割）

针对法律文档特别优化：
- 保留条款结构
- 识别法律条文编号
- 保持上下文完整性
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from enum import Enum

from loguru import logger


class ChunkingStrategy(str, Enum):
    """分块策略"""
    FIXED_SIZE = "fixed_size"           # 固定长度
    PARAGRAPH = "paragraph"             # 按段落
    SENTENCE = "sentence"               # 按句子
    RECURSIVE = "recursive"             # 递归分块
    LEGAL_ARTICLE = "legal_article"     # 法律条款（特殊处理）


@dataclass
class TextChunk:
    """文本块"""
    content: str                        # 块内容
    index: int                          # 块索引
    start_char: int                     # 起始字符位置
    end_char: int                       # 结束字符位置
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def char_count(self) -> int:
        return len(self.content)
    
    @property
    def word_count(self) -> int:
        # 简单的中英文混合词数统计
        # 中文按字符计数，英文按空格分词
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', self.content))
        english_words = len(re.findall(r'[a-zA-Z]+', self.content))
        return chinese_chars + english_words
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "index": self.index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "char_count": self.char_count,
            "word_count": self.word_count,
            "metadata": self.metadata,
        }


@dataclass
class ChunkingConfig:
    """分块配置"""
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    chunk_size: int = 500               # 目标块大小（字符数）
    chunk_overlap: int = 50             # 块间重叠（字符数）
    min_chunk_size: int = 100           # 最小块大小
    max_chunk_size: int = 1000          # 最大块大小
    
    # 分隔符配置（按优先级排序）
    separators: List[str] = field(default_factory=lambda: [
        "\n\n\n",       # 多个空行
        "\n\n",         # 段落
        "\n",           # 换行
        "。",           # 中文句号
        "；",           # 中文分号
        "！",           # 中文感叹号
        "？",           # 中文问号
        ".",            # 英文句号
        ";",            # 英文分号
        "!",            # 英文感叹号
        "?",            # 英文问号
        "，",           # 中文逗号
        ",",            # 英文逗号
        " ",            # 空格
    ])
    
    # 法律文档特殊分隔符
    legal_separators: List[str] = field(default_factory=lambda: [
        r"第[一二三四五六七八九十百千]+条",     # 中文条款编号
        r"第\d+条",                             # 数字条款编号
        r"\d+\.",                               # 数字编号
        r"\([一二三四五六七八九十]+\)",          # 中文括号编号
        r"\(\d+\)",                             # 数字括号编号
    ])
    
    # 是否保留元数据
    keep_separator: bool = True
    add_start_index: bool = True


class ChunkingService:
    """文档分块服务"""
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()
    
    def chunk_text(
        self,
        text: str,
        strategy: Optional[ChunkingStrategy] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[TextChunk]:
        """
        对文本进行分块
        
        Args:
            text: 要分块的文本
            strategy: 分块策略（可选，使用配置中的默认值）
            metadata: 附加到每个块的元数据
            **kwargs: 覆盖配置的参数
            
        Returns:
            分块结果列表
        """
        if not text or not text.strip():
            return []
        
        strategy = strategy or self.config.strategy
        base_metadata = metadata or {}
        
        # 更新配置
        config = self._merge_config(kwargs)
        
        # 选择分块方法
        if strategy == ChunkingStrategy.FIXED_SIZE:
            chunks = self._chunk_by_fixed_size(text, config)
        elif strategy == ChunkingStrategy.PARAGRAPH:
            chunks = self._chunk_by_paragraph(text, config)
        elif strategy == ChunkingStrategy.SENTENCE:
            chunks = self._chunk_by_sentence(text, config)
        elif strategy == ChunkingStrategy.LEGAL_ARTICLE:
            chunks = self._chunk_by_legal_article(text, config)
        else:  # RECURSIVE
            chunks = self._chunk_recursive(text, config)
        
        # 添加元数据
        for chunk in chunks:
            chunk.metadata.update(base_metadata)
            chunk.metadata["strategy"] = strategy.value
        
        logger.debug(f"文本分块完成: {len(chunks)} 块, 策略: {strategy.value}")
        return chunks
    
    def _merge_config(self, kwargs: Dict) -> ChunkingConfig:
        """合并配置参数"""
        config_dict = {
            "strategy": self.config.strategy,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "min_chunk_size": self.config.min_chunk_size,
            "max_chunk_size": self.config.max_chunk_size,
            "separators": self.config.separators,
            "keep_separator": self.config.keep_separator,
            "add_start_index": self.config.add_start_index,
        }
        config_dict.update(kwargs)
        return ChunkingConfig(**{k: v for k, v in config_dict.items() 
                                 if k in ChunkingConfig.__dataclass_fields__})
    
    def _chunk_by_fixed_size(
        self,
        text: str,
        config: ChunkingConfig,
    ) -> List[TextChunk]:
        """按固定长度分块"""
        chunks = []
        start = 0
        index = 0
        
        while start < len(text):
            end = min(start + config.chunk_size, len(text))
            
            # 尝试在句子边界处断开
            if end < len(text):
                for sep in ["。", ".", "！", "？", "!", "?", "\n"]:
                    sep_pos = text.rfind(sep, start, end)
                    if sep_pos > start + config.min_chunk_size:
                        end = sep_pos + 1
                        break
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(TextChunk(
                    content=chunk_text,
                    index=index,
                    start_char=start,
                    end_char=end,
                ))
                index += 1
            
            # 计算下一个起始位置（考虑重叠）
            start = end - config.chunk_overlap if end < len(text) else end
            if start <= chunks[-1].start_char if chunks else 0:
                start = end  # 防止无限循环
        
        return chunks
    
    def _chunk_by_paragraph(
        self,
        text: str,
        config: ChunkingConfig,
    ) -> List[TextChunk]:
        """按段落分块"""
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current_chunk = ""
        current_start = 0
        index = 0
        char_pos = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                char_pos += 2  # 空行
                continue
            
            # 如果当前块加上新段落超过最大长度，先保存当前块
            if current_chunk and len(current_chunk) + len(para) + 2 > config.max_chunk_size:
                chunks.append(TextChunk(
                    content=current_chunk,
                    index=index,
                    start_char=current_start,
                    end_char=char_pos,
                ))
                index += 1
                current_chunk = ""
                current_start = char_pos
            
            # 如果单个段落超过最大长度，进行子分块
            if len(para) > config.max_chunk_size:
                if current_chunk:
                    chunks.append(TextChunk(
                        content=current_chunk,
                        index=index,
                        start_char=current_start,
                        end_char=char_pos,
                    ))
                    index += 1
                    current_chunk = ""
                
                # 递归分块长段落
                sub_chunks = self._chunk_by_fixed_size(para, config)
                for sub_chunk in sub_chunks:
                    sub_chunk.index = index
                    sub_chunk.start_char += char_pos
                    sub_chunk.end_char += char_pos
                    chunks.append(sub_chunk)
                    index += 1
                
                current_start = char_pos + len(para) + 2
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                    current_start = char_pos
            
            char_pos += len(para) + 2
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(TextChunk(
                content=current_chunk,
                index=index,
                start_char=current_start,
                end_char=char_pos,
            ))
        
        return chunks
    
    def _chunk_by_sentence(
        self,
        text: str,
        config: ChunkingConfig,
    ) -> List[TextChunk]:
        """按句子分块"""
        # 中英文句子分割
        sentence_pattern = r'([^。！？.!?\n]+[。！？.!?]?)'
        sentences = re.findall(sentence_pattern, text)
        
        chunks = []
        current_chunk = ""
        current_start = 0
        index = 0
        char_pos = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_chunk) + len(sentence) > config.chunk_size:
                if current_chunk:
                    chunks.append(TextChunk(
                        content=current_chunk,
                        index=index,
                        start_char=current_start,
                        end_char=char_pos,
                    ))
                    index += 1
                current_chunk = sentence
                current_start = char_pos
            else:
                current_chunk += sentence
            
            char_pos += len(sentence)
        
        if current_chunk:
            chunks.append(TextChunk(
                content=current_chunk,
                index=index,
                start_char=current_start,
                end_char=char_pos,
            ))
        
        return chunks
    
    def _chunk_by_legal_article(
        self,
        text: str,
        config: ChunkingConfig,
    ) -> List[TextChunk]:
        """
        按法律条款分块
        
        专门针对法律文档优化：
        - 识别条款编号（第X条）
        - 保持条款完整性
        - 处理款、项结构
        """
        # 构建条款分割正则
        article_pattern = r'(第[一二三四五六七八九十百千\d]+条[^\n]*)'
        
        # 分割条款
        parts = re.split(article_pattern, text)
        
        chunks = []
        current_chunk = ""
        current_start = 0
        current_article = ""
        index = 0
        char_pos = 0
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # 检查是否是条款标题
            is_article_header = bool(re.match(r'^第[一二三四五六七八九十百千\d]+条', part))
            
            if is_article_header:
                # 保存之前的块
                if current_chunk:
                    chunks.append(TextChunk(
                        content=current_chunk,
                        index=index,
                        start_char=current_start,
                        end_char=char_pos,
                        metadata={"article": current_article},
                    ))
                    index += 1
                
                current_chunk = part
                current_article = part.split()[0] if part.split() else part[:10]
                current_start = char_pos
            else:
                # 条款内容
                if current_chunk:
                    combined = current_chunk + "\n" + part
                    if len(combined) <= config.max_chunk_size:
                        current_chunk = combined
                    else:
                        # 内容太长，需要分块
                        chunks.append(TextChunk(
                            content=current_chunk,
                            index=index,
                            start_char=current_start,
                            end_char=char_pos,
                            metadata={"article": current_article},
                        ))
                        index += 1
                        
                        # 对长内容进行子分块
                        if len(part) > config.max_chunk_size:
                            sub_chunks = self._chunk_by_fixed_size(part, config)
                            for sub_chunk in sub_chunks:
                                sub_chunk.index = index
                                sub_chunk.metadata["article"] = current_article
                                sub_chunk.metadata["is_continuation"] = True
                                chunks.append(sub_chunk)
                                index += 1
                            current_chunk = ""
                        else:
                            current_chunk = part
                            current_start = char_pos
                else:
                    current_chunk = part
                    current_start = char_pos
            
            char_pos += len(part) + 1
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(TextChunk(
                content=current_chunk,
                index=index,
                start_char=current_start,
                end_char=char_pos,
                metadata={"article": current_article},
            ))
        
        return chunks
    
    def _chunk_recursive(
        self,
        text: str,
        config: ChunkingConfig,
        separators: Optional[List[str]] = None,
    ) -> List[TextChunk]:
        """
        递归分块
        
        使用多级分隔符递归分割文本，确保块大小适中。
        优先使用更大的分隔符（段落 > 句子 > 逗号 > 空格）
        """
        separators = separators or config.separators
        
        # 如果文本足够短，直接返回
        if len(text) <= config.chunk_size:
            return [TextChunk(
                content=text.strip(),
                index=0,
                start_char=0,
                end_char=len(text),
            )] if text.strip() else []
        
        # 尝试使用当前分隔符分割
        for i, separator in enumerate(separators):
            if separator in text:
                splits = self._split_text(text, separator, config.keep_separator)
                
                if len(splits) > 1:
                    chunks = []
                    current_chunk = ""
                    current_start = 0
                    char_pos = 0
                    
                    for split in splits:
                        if not split.strip():
                            char_pos += len(split)
                            continue
                        
                        # 如果合并后仍在限制内
                        if len(current_chunk) + len(split) <= config.chunk_size:
                            if current_chunk:
                                current_chunk += split
                            else:
                                current_chunk = split
                                current_start = char_pos
                        else:
                            # 保存当前块
                            if current_chunk:
                                chunks.extend(self._finalize_chunk(
                                    current_chunk, current_start, config, separators[i+1:]
                                ))
                            
                            # 如果单个分割仍然太大，递归处理
                            if len(split) > config.chunk_size:
                                sub_chunks = self._chunk_recursive(
                                    split, config, separators[i+1:]
                                )
                                for sub_chunk in sub_chunks:
                                    sub_chunk.start_char += char_pos
                                    sub_chunk.end_char += char_pos
                                chunks.extend(sub_chunks)
                                current_chunk = ""
                            else:
                                current_chunk = split
                                current_start = char_pos
                        
                        char_pos += len(split)
                    
                    # 处理最后一个块
                    if current_chunk:
                        chunks.extend(self._finalize_chunk(
                            current_chunk, current_start, config, separators[i+1:]
                        ))
                    
                    # 重新编号
                    for idx, chunk in enumerate(chunks):
                        chunk.index = idx
                    
                    return chunks
        
        # 没有找到合适的分隔符，强制按长度分割
        return self._chunk_by_fixed_size(text, config)
    
    def _split_text(
        self,
        text: str,
        separator: str,
        keep_separator: bool,
    ) -> List[str]:
        """分割文本"""
        if keep_separator:
            # 保留分隔符
            parts = re.split(f'({re.escape(separator)})', text)
            # 将分隔符附加到前一个部分
            result = []
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    if i + 1 < len(parts):
                        result.append(part + parts[i + 1])
                    else:
                        result.append(part)
            return result
        else:
            return text.split(separator)
    
    def _finalize_chunk(
        self,
        text: str,
        start_pos: int,
        config: ChunkingConfig,
        remaining_separators: List[str],
    ) -> List[TextChunk]:
        """处理最终的块"""
        text = text.strip()
        if not text:
            return []
        
        if len(text) <= config.chunk_size:
            return [TextChunk(
                content=text,
                index=0,
                start_char=start_pos,
                end_char=start_pos + len(text),
            )]
        
        # 如果还有分隔符可用，继续递归
        if remaining_separators:
            return self._chunk_recursive(text, config, remaining_separators)
        
        # 否则强制分割
        return self._chunk_by_fixed_size(text, config)
    
    def chunk_document(
        self,
        content: str,
        title: str = "",
        doc_id: str = "",
        doc_type: str = "general",
        **kwargs
    ) -> List[TextChunk]:
        """
        对文档进行分块（高级接口）
        
        Args:
            content: 文档内容
            title: 文档标题
            doc_id: 文档ID
            doc_type: 文档类型（general, law, contract, case）
            
        Returns:
            分块结果
        """
        # 根据文档类型选择策略
        if doc_type in ["law", "regulation"]:
            strategy = ChunkingStrategy.LEGAL_ARTICLE
        elif doc_type == "contract":
            strategy = ChunkingStrategy.PARAGRAPH
        else:
            strategy = ChunkingStrategy.RECURSIVE
        
        # 准备元数据
        metadata = {
            "doc_id": doc_id,
            "doc_title": title,
            "doc_type": doc_type,
        }
        
        # 执行分块
        chunks = self.chunk_text(
            text=content,
            strategy=strategy,
            metadata=metadata,
            **kwargs
        )
        
        # 添加额外的上下文信息
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk.metadata["total_chunks"] = total_chunks
            chunk.metadata["chunk_index"] = chunk.index
            # 添加位置信息
            if chunk.index == 0:
                chunk.metadata["position"] = "start"
            elif chunk.index == total_chunks - 1:
                chunk.metadata["position"] = "end"
            else:
                chunk.metadata["position"] = "middle"
        
        return chunks


# 创建默认实例
chunking_service = ChunkingService()


# 便捷函数
def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    strategy: str = "recursive",
) -> List[Dict[str, Any]]:
    """
    快速分块文本
    
    Args:
        text: 要分块的文本
        chunk_size: 块大小
        chunk_overlap: 重叠大小
        strategy: 分块策略
        
    Returns:
        分块结果（字典列表）
    """
    config = ChunkingConfig(
        strategy=ChunkingStrategy(strategy),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    service = ChunkingService(config)
    chunks = service.chunk_text(text)
    return [chunk.to_dict() for chunk in chunks]


def chunk_legal_document(
    content: str,
    title: str = "",
    doc_id: str = "",
) -> List[Dict[str, Any]]:
    """
    分块法律文档
    
    专门针对法律文档优化的分块方法
    """
    service = ChunkingService(ChunkingConfig(
        strategy=ChunkingStrategy.LEGAL_ARTICLE,
        chunk_size=800,
        chunk_overlap=100,
    ))
    chunks = service.chunk_document(
        content=content,
        title=title,
        doc_id=doc_id,
        doc_type="law",
    )
    return [chunk.to_dict() for chunk in chunks]
