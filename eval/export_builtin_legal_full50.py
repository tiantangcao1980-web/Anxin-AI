#!/usr/bin/env python3
"""Export the built-in legal corpus and a full50 golden set for RAG release checks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from src.services.legal_corpus_loader import LegalArticle, get_all_legal_corpus  # noqa: E402

DEFAULT_CORPUS_OUT = REPO_ROOT / "eval" / "legal_full50_corpus.jsonl"
DEFAULT_GOLDEN_OUT = REPO_ROOT / "eval" / "legal_full50_golden.jsonl"


@dataclass(frozen=True)
class ArticleChunk:
    article: LegalArticle
    doc_id: str
    chunk_id: str
    short_law_name: str
    law_ref: str


def _article_digits(article_number: str) -> str:
    match = re.search(r"\d+", article_number)
    if not match:
        raise ValueError(f"Cannot derive article number from {article_number!r}")
    return match.group(0)


def _law_identity(article: LegalArticle) -> tuple[str, str]:
    if "劳动合同法" in article.law_name:
        return "labor_contract_law", "劳动合同法"
    if "民法典" in article.law_name:
        return "civil_code", "民法典"
    normalized = re.sub(r"[^a-z0-9]+", "_", article.law_name.lower()).strip("_")
    return normalized or "legal_doc", article.law_name


def _chunk_for_article(article: LegalArticle) -> ArticleChunk:
    prefix, short_law_name = _law_identity(article)
    article_no = _article_digits(article.article_number)
    doc_id = f"{prefix}_{article_no}"
    chunk_id = f"{doc_id}_0"
    return ArticleChunk(
        article=article,
        doc_id=doc_id,
        chunk_id=chunk_id,
        short_law_name=short_law_name,
        law_ref=f"{short_law_name}:{article.article_number}",
    )


def build_corpus_rows(chunks: list[ArticleChunk]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chunk in chunks:
        article = chunk.article
        rows.append(
            {
                "doc_id": chunk.doc_id,
                "chunk_id": chunk.chunk_id,
                "title": f"《{article.law_name}》{article.article_number} {article.title}",
                "source": article.law_name,
                "content": (
                    f"《{article.law_name}》{article.article_number}（{article.title}）\n"
                    f"{article.content}"
                ),
                "metadata": {
                    "law_ref": chunk.law_ref,
                    "source_url": f"/knowledge/legal/{chunk.doc_id}#{chunk.chunk_id}",
                    "law_name": article.law_name,
                    "article_number": article.article_number,
                    "chapter": article.chapter,
                    "effective_date": article.effective_date,
                    "issuing_authority": article.issuing_authority,
                    "tags": article.tags,
                    "corpus_source": "builtin_legal_corpus",
                },
            }
        )
    return rows


def _single_question(chunk: ArticleChunk, index: int) -> dict[str, Any]:
    article = chunk.article
    category = "labor" if chunk.short_law_name == "劳动合同法" else "contract"
    return {
        "id": f"BLT-{index:04d}",
        "category": category,
        "query": (
            f"客户咨询“{article.title}”相关问题时，"
            f"{chunk.short_law_name}{article.article_number}的核心规则是什么？"
        ),
        "relevant_doc_ids": [chunk.doc_id],
        "relevant_chunk_ids": [chunk.chunk_id],
        "expected_law_refs": [chunk.law_ref],
        "difficulty": "easy" if index % 3 else "medium",
        "smoke": False,
    }


def _paired_question(
    chunks_by_doc: dict[str, ArticleChunk],
    *,
    qid: int,
    category: str,
    query: str,
    doc_ids: list[str],
    difficulty: str = "medium",
) -> dict[str, Any]:
    chunks = [chunks_by_doc[doc_id] for doc_id in doc_ids]
    return {
        "id": f"BLT-{qid:04d}",
        "category": category,
        "query": query,
        "relevant_doc_ids": [chunk.doc_id for chunk in chunks],
        "relevant_chunk_ids": [chunk.chunk_id for chunk in chunks],
        "expected_law_refs": [chunk.law_ref for chunk in chunks],
        "difficulty": difficulty,
        "smoke": False,
    }


def build_golden_rows(chunks: list[ArticleChunk]) -> list[dict[str, Any]]:
    rows = [_single_question(chunk, index) for index, chunk in enumerate(chunks, start=1)]
    chunks_by_doc = {chunk.doc_id: chunk for chunk in chunks}
    paired_specs = [
        {
            "category": "contract",
            "query": "格式条款未提示免责内容且条款本身加重客户责任时，应分别依据哪些规则判断？",
            "doc_ids": ["civil_code_496", "civil_code_497"],
        },
        {
            "category": "contract",
            "query": "格式条款发生两种解释且与非格式条款冲突时，应如何处理？",
            "doc_ids": ["civil_code_496", "civil_code_498"],
        },
        {
            "category": "contract",
            "query": "合同签署前一方已履行主要义务且对方接受时，合同成立和生效如何衔接？",
            "doc_ids": ["civil_code_490", "civil_code_502"],
        },
        {
            "category": "contract",
            "query": "企业想解除长期合作合同，约定解除和法定解除分别需要看哪些法律依据？",
            "doc_ids": ["civil_code_562", "civil_code_563"],
        },
        {
            "category": "contract",
            "query": "供应商违约导致损失并约定违约金时，责任承担、赔偿范围和违约金调整如何判断？",
            "doc_ids": ["civil_code_577", "civil_code_584", "civil_code_585"],
            "difficulty": "hard",
        },
        {
            "category": "labor",
            "query": "入职后长期未签书面劳动合同，公司需要同时关注哪些书面合同和双倍工资规则？",
            "doc_ids": ["labor_contract_law_10", "labor_contract_law_82"],
        },
        {
            "category": "labor",
            "query": "员工负有保密义务并违反竞业限制时，竞业限制条款和适用人员范围如何判断？",
            "doc_ids": ["labor_contract_law_23", "labor_contract_law_24"],
        },
        {
            "category": "labor",
            "query": "解除或终止劳动合同时，经济补偿适用情形和计算标准应如何结合审查？",
            "doc_ids": ["labor_contract_law_46", "labor_contract_law_47"],
        },
    ]
    for offset, spec in enumerate(paired_specs, start=len(rows) + 1):
        rows.append(_paired_question(chunks_by_doc, qid=offset, **spec))
    if len(rows) != 50:
        raise ValueError(f"Expected 50 built-in legal golden questions, got {len(rows)}")
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_OUT)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN_OUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    chunks = [_chunk_for_article(article) for article in get_all_legal_corpus()]
    if len(chunks) < 40:
        raise RuntimeError(f"Built-in legal corpus is unexpectedly small: {len(chunks)} articles")
    corpus_rows = build_corpus_rows(chunks)
    golden_rows = build_golden_rows(chunks)
    if any(row.get("smoke") for row in golden_rows):
        raise RuntimeError("Built-in legal full50 golden must not contain smoke rows")
    _write_jsonl(args.corpus, corpus_rows)
    _write_jsonl(args.golden, golden_rows)
    print(
        "Exported built-in legal full50 "
        f"corpus_chunks={len(corpus_rows)} golden_questions={len(golden_rows)} "
        f"corpus={args.corpus} golden={args.golden}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
