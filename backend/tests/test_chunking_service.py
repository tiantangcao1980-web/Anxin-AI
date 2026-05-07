from src.services.chunking_service import (
    ChunkingService,
    ChunkingStrategy,
    chunk_text,
)


def test_chunk_text_fixed_size_applies_metadata_and_overrides():
    service = ChunkingService()

    chunks = service.chunk_text(
        "第一句内容足够长。第二句内容也足够长。第三句用于测试。",
        strategy=ChunkingStrategy.FIXED_SIZE,
        metadata={"doc_id": "doc-1"},
        chunk_size=14,
        chunk_overlap=2,
        min_chunk_size=4,
    )

    assert len(chunks) >= 2
    assert chunks[0].metadata["doc_id"] == "doc-1"
    assert chunks[0].metadata["strategy"] == "fixed_size"
    assert chunks[0].start_char == 0
    assert chunks[0].end_char <= len("第一句内容足够长。第二句内容也足够长。第三句用于测试。")


def test_chunk_document_adds_document_position_metadata():
    service = ChunkingService()

    chunks = service.chunk_document(
        "第一段合同背景说明。\n\n第二段权利义务说明。\n\n第三段违约责任说明。",
        title="服务合同",
        doc_id="contract-1",
        doc_type="contract",
        max_chunk_size=20,
    )

    assert chunks
    assert chunks[0].metadata["doc_id"] == "contract-1"
    assert chunks[0].metadata["doc_title"] == "服务合同"
    assert chunks[0].metadata["doc_type"] == "contract"
    assert chunks[0].metadata["position"] == "start"
    assert chunks[-1].metadata["position"] == "end"


def test_chunk_text_convenience_function_returns_dicts():
    chunks = chunk_text("第一句。第二句。", chunk_size=5, chunk_overlap=0, strategy="fixed_size")

    assert chunks
    assert set(chunks[0]) >= {"content", "index", "start_char", "end_char", "metadata"}
