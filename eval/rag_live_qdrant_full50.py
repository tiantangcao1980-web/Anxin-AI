#!/usr/bin/env python3
"""Generate live Qdrant predictions for the full RAG commercial baseline.

Unlike ``rag_live_qdrant_smoke.py``, this script never embeds an in-code sample
corpus. A caller must provide a realistic corpus export whose chunk IDs cover
the full golden set before live predictions can be generated.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rag_quality import GoldenQuestion, file_sha256, load_golden, load_jsonl

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

DEFAULT_MIN_QUESTIONS = 50
DEFAULT_PREDICTIONS_OUT = REPO_ROOT / "eval" / "rag_live_predictions_full50.json"
SMOKE_MARKERS = ("smoke", "fixture", "sample", "demo", "mock")
BUILTIN_CORPUS_URI = "builtin://legal_corpus_loader"
BUILTIN_CORPUS_SOURCE = REPO_ROOT / "backend" / "src" / "services" / "legal_corpus_loader.py"
BUILTIN_LAW_SLUGS = {
    "中华人民共和国民法典": "civil_code",
    "中华人民共和国劳动合同法": "labor_contract_law",
    "中华人民共和国个人信息保护法": "pipl",
    "中华人民共和国数据安全法": "data_security_law",
    "中华人民共和国网络安全法": "cybersecurity_law",
    "中华人民共和国公司法": "company_law",
    "中华人民共和国广告法": "advertising_law",
    "中华人民共和国消费者权益保护法": "consumer_rights_law",
    "中华人民共和国电子商务法": "ecommerce_law",
    "中华人民共和国民事诉讼法": "civil_procedure_law",
    "民事诉讼证据规定": "civil_procedure_evidence_rules",
}
BUILTIN_LAW_REFS = {
    "中华人民共和国民法典": "民法典",
    "中华人民共和国劳动合同法": "劳动合同法",
    "中华人民共和国个人信息保护法": "个人信息保护法",
    "中华人民共和国数据安全法": "数据安全法",
    "中华人民共和国网络安全法": "网络安全法",
    "中华人民共和国公司法": "公司法",
    "中华人民共和国广告法": "广告法",
    "中华人民共和国消费者权益保护法": "消费者权益保护法",
    "中华人民共和国电子商务法": "电子商务法",
    "中华人民共和国民事诉讼法": "民事诉讼法",
    "民事诉讼证据规定": "民事诉讼证据规定",
}


@dataclass(frozen=True)
class CorpusChunk:
    doc_id: str
    chunk_id: str
    title: str
    content: str
    source: str
    metadata: dict[str, Any]


def _as_text(value: Any, *, field_name: str) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must not be empty")
    return text


def _as_metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("metadata must be a JSON object when present")
    return dict(value)


def _derive_doc_id(chunk_id: str) -> str:
    parts = chunk_id.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return chunk_id


def _load_raw_corpus(path: Path) -> Any:
    if not path.exists():
        raise ValueError(f"Corpus file does not exist: {path}")
    if path.suffix.lower() == ".jsonl":
        return load_jsonl(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_chunk_rows(raw: Any) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
    rows: list[tuple[dict[str, Any], dict[str, Any] | None]] = []

    def visit(item: Any, inherited_doc: dict[str, Any] | None = None) -> None:
        if not isinstance(item, dict):
            raise ValueError("Corpus rows must be JSON objects")

        nested_chunks = item.get("chunks")
        if nested_chunks is not None:
            if not isinstance(nested_chunks, list):
                raise ValueError("document.chunks must be a list")
            for chunk in nested_chunks:
                visit(chunk, inherited_doc=item)
            return

        rows.append((item, inherited_doc))

    if isinstance(raw, dict):
        if isinstance(raw.get("chunks"), list):
            for chunk in raw["chunks"]:
                visit(chunk)
        elif isinstance(raw.get("documents"), list):
            for document in raw["documents"]:
                visit(document)
        else:
            visit(raw)
    elif isinstance(raw, list):
        for item in raw:
            visit(item)
    else:
        raise ValueError("Corpus must be a JSON object, JSON array, or JSONL rows")

    return rows


def _extract_article_digits(article_number: str) -> str:
    digits = "".join(character for character in article_number if character.isdigit())
    if not digits:
        raise ValueError(f"Article number must contain digits: {article_number}")
    return digits


def _builtin_doc_id(article: Any) -> str:
    slug = BUILTIN_LAW_SLUGS.get(article.law_name)
    if not slug:
        raise ValueError(f"Unsupported built-in law name for eval corpus export: {article.law_name}")
    return f"{slug}_{_extract_article_digits(article.article_number)}"


def _builtin_law_ref(article: Any) -> str:
    law_ref_name = BUILTIN_LAW_REFS.get(article.law_name, article.law_name)
    return f"{law_ref_name}:{article.article_number}"


def load_builtin_legal_corpus() -> tuple[Any, list[CorpusChunk]]:
    from src.services.legal_corpus_loader import get_all_legal_corpus

    documents: list[dict[str, Any]] = []
    chunks: list[CorpusChunk] = []
    for article in get_all_legal_corpus():
        doc_id = _builtin_doc_id(article)
        chunk_id = f"{doc_id}_0"
        title = f"《{article.law_name}》{article.article_number} {article.title}".strip()
        source_url = f"/knowledge/builtin/legal-corpus/{doc_id}#{chunk_id}"
        metadata = {
            "law_name": article.law_name,
            "law_type": article.law_type,
            "law_ref": _builtin_law_ref(article),
            "article_number": article.article_number,
            "chapter": article.chapter,
            "effective_date": article.effective_date,
            "issuing_authority": article.issuing_authority,
            "tags": list(article.tags),
            "source_url": source_url,
        }
        documents.append(
            {
                "id": doc_id,
                "title": title,
                "source": article.law_name,
                "metadata": metadata,
                "chunks": [{"id": chunk_id, "content": article.content, "metadata": metadata}],
            }
        )
        chunks.append(
            CorpusChunk(
                doc_id=doc_id,
                chunk_id=chunk_id,
                title=title,
                content=article.content,
                source=article.law_name,
                metadata=metadata,
            )
        )

    raw = {
        "corpus_kind": "builtin_legal_corpus",
        "source": str(BUILTIN_CORPUS_SOURCE.relative_to(REPO_ROOT)),
        "builder": "src.services.legal_corpus_loader.get_all_legal_corpus",
        "documents": documents,
    }
    return raw, chunks


def _coerce_chunk(row: dict[str, Any], inherited_doc: dict[str, Any] | None) -> CorpusChunk:
    inherited_doc = inherited_doc or {}
    inherited_metadata = _as_metadata(inherited_doc.get("metadata"))
    metadata = {**inherited_metadata, **_as_metadata(row.get("metadata"))}

    for key in ("law_ref", "source_url", "organization_id", "tenant_id", "acl"):
        if row.get(key) is not None:
            metadata[key] = row[key]
        elif inherited_doc.get(key) is not None:
            metadata[key] = inherited_doc[key]

    chunk_id = _as_text(row.get("chunk_id") or row.get("id"), field_name="chunk_id")
    doc_id = _as_text(
        row.get("doc_id")
        or row.get("document_id")
        or inherited_doc.get("doc_id")
        or inherited_doc.get("document_id")
        or inherited_doc.get("id")
        or _derive_doc_id(chunk_id),
        field_name="doc_id",
    )
    content = _as_text(
        row.get("content") or row.get("text") or row.get("body"),
        field_name=f"content for {chunk_id}",
    )
    title = str(row.get("title") or inherited_doc.get("title") or "").strip()
    source = str(row.get("source") or inherited_doc.get("source") or "").strip()

    return CorpusChunk(
        doc_id=doc_id,
        chunk_id=chunk_id,
        title=title,
        content=content,
        source=source,
        metadata=metadata,
    )


def load_corpus(path: Path) -> tuple[Any, list[CorpusChunk]]:
    raw = _load_raw_corpus(path)
    chunks = [_coerce_chunk(row, document) for row, document in _iter_chunk_rows(raw)]
    if not chunks:
        raise ValueError("Corpus contains no chunks")

    seen: set[str] = set()
    duplicates: set[str] = set()
    for chunk in chunks:
        if chunk.chunk_id in seen:
            duplicates.add(chunk.chunk_id)
        seen.add(chunk.chunk_id)
    if duplicates:
        sample = ", ".join(sorted(duplicates)[:10])
        raise ValueError(f"Corpus contains duplicate chunk_id values: {sample}")

    return raw, chunks


def load_selected_corpus(args: argparse.Namespace) -> tuple[Any, list[CorpusChunk]]:
    if args.built_in_legal_corpus:
        return load_builtin_legal_corpus()
    if args.corpus is None:
        raise ValueError("Either --corpus or --built-in-legal-corpus is required")
    return load_corpus(args.corpus)


def corpus_identifier(args: argparse.Namespace) -> str:
    if args.built_in_legal_corpus:
        return BUILTIN_CORPUS_URI
    assert args.corpus is not None
    return str(args.corpus)


def corpus_repo_relative_path(args: argparse.Namespace) -> str | None:
    if args.built_in_legal_corpus:
        return str(BUILTIN_CORPUS_SOURCE.relative_to(REPO_ROOT))
    assert args.corpus is not None
    return _relative_to_repo(args.corpus)


def corpus_sha256(args: argparse.Namespace, raw: Any | None = None) -> str:
    if args.built_in_legal_corpus:
        normalized = json.dumps(raw or {}, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(normalized).hexdigest()
    assert args.corpus is not None
    return file_sha256(args.corpus)


def _raw_corpus_text(raw: Any, corpus_path: Path) -> str:
    if isinstance(raw, dict):
        marker_fields = {
            key: raw.get(key)
            for key in (
                "mode",
                "run_label",
                "name",
                "description",
                "notes",
                "corpus_kind",
                "dataset_type",
            )
            if key in raw
        }
        return json.dumps(marker_fields, ensure_ascii=False).lower()
    return corpus_path.name.lower()


def validate_not_fixture_corpus(raw: Any, corpus_path: Path, allow_fixture: bool) -> None:
    if allow_fixture:
        return

    haystack = f"{corpus_path.name.lower()}\n{_raw_corpus_text(raw, corpus_path)}"
    matched = [marker for marker in SMOKE_MARKERS if marker in haystack]
    if matched:
        raise ValueError(
            "Corpus looks like a fixture/smoke/demo export "
            f"(matched: {', '.join(matched)}). Use --allow-fixture-corpus only "
            "for non-commercial dry runs."
        )


def validate_not_smoke_golden(
    questions: list[GoldenQuestion],
    *,
    golden_path: Path,
    allow_smoke_golden: bool,
) -> None:
    if allow_smoke_golden:
        return

    smoke_questions = [question.id for question in questions if question.smoke]
    if smoke_questions:
        sample = ", ".join(smoke_questions[:12])
        raise ValueError(
            "Golden set is marked as smoke/non-commercial "
            f"({len(smoke_questions)} questions, sample: {sample}). "
            f"Use a commercial full50 golden export instead of {golden_path}, "
            "or pass --allow-smoke-golden only for non-commercial dry runs."
        )


def _required_chunk_ids(questions: list[GoldenQuestion]) -> set[str]:
    return {chunk_id for question in questions for chunk_id in question.relevant_ids}


def _relative_to_repo(path: Path) -> str | None:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return None


def _coverage_snapshot(
    *,
    questions: list[GoldenQuestion],
    available_chunk_ids: set[str],
) -> dict[str, Any]:
    required_chunk_ids = _required_chunk_ids(questions)
    missing_chunk_ids = sorted(required_chunk_ids.difference(available_chunk_ids))
    required_count = len(required_chunk_ids)
    available_required_count = required_count - len(missing_chunk_ids)
    coverage_ratio = (available_required_count / required_count) if required_count else 0.0
    return {
        "question_count": len(questions),
        "required_chunk_count": required_count,
        "available_required_chunk_count": available_required_count,
        "missing_chunk_count": len(missing_chunk_ids),
        "missing_chunk_sample": missing_chunk_ids[:200],
        "coverage_ratio": round(coverage_ratio, 4),
    }


def build_readiness_summary(
    *,
    args: argparse.Namespace,
    chunks: list[CorpusChunk] | None,
    questions: list[GoldenQuestion] | None,
) -> dict[str, Any]:
    available_chunk_ids = {chunk.chunk_id for chunk in chunks or []}
    smoke_question_count = sum(1 for question in questions or [] if question.smoke)
    non_smoke_questions = [question for question in questions or [] if not question.smoke]
    all_questions_snapshot = _coverage_snapshot(
        questions=questions or [],
        available_chunk_ids=available_chunk_ids,
    )
    non_smoke_snapshot = _coverage_snapshot(
        questions=non_smoke_questions,
        available_chunk_ids=available_chunk_ids,
    )
    repo_relative_corpus = corpus_repo_relative_path(args)
    repo_relative_golden = _relative_to_repo(args.golden)

    blockers: list[str] = []
    if questions is None:
        blockers.append("golden_not_loaded")
    else:
        if len(questions) < args.min_questions:
            blockers.append(
                f"golden_below_min_questions:{len(questions)}<{args.min_questions}"
            )
        if smoke_question_count:
            blockers.append(f"golden_contains_smoke_questions:{smoke_question_count}")
        if all_questions_snapshot["missing_chunk_count"]:
            blockers.append(
                "corpus_missing_required_chunks:"
                f"{all_questions_snapshot['missing_chunk_count']}"
            )
        if non_smoke_snapshot["missing_chunk_count"]:
            blockers.append(
                "corpus_missing_non_smoke_required_chunks:"
                f"{non_smoke_snapshot['missing_chunk_count']}"
            )

    return {
        "uses_repo_local_corpus": repo_relative_corpus is not None,
        "repo_relative_corpus_path": repo_relative_corpus,
        "repo_relative_golden_path": repo_relative_golden,
        "available_chunk_count": len(available_chunk_ids),
        "smoke_question_count": smoke_question_count,
        "all_questions": all_questions_snapshot,
        "non_smoke_questions": non_smoke_snapshot,
        "commercial_full50_ready": (
            questions is not None
            and len(questions) >= args.min_questions
            and smoke_question_count == 0
            and all_questions_snapshot["missing_chunk_count"] == 0
        ),
        "blockers": blockers,
    }


def build_next_steps(
    *,
    args: argparse.Namespace,
    readiness: dict[str, Any],
) -> list[str]:
    steps: list[str] = []
    smoke_question_count = int(readiness.get("smoke_question_count", 0))
    all_questions = readiness.get("all_questions", {})
    non_smoke_questions = readiness.get("non_smoke_questions", {})
    available_chunk_count = int(readiness.get("available_chunk_count", 0))

    if smoke_question_count:
        steps.append(
            "Replace or split the current golden file with a non-smoke commercial export: "
            f"the repo golden currently has {smoke_question_count} smoke rows and cannot "
            "serve as full50 release evidence."
        )
    if all_questions.get("missing_chunk_count"):
        steps.append(
            "Generate a built-in legal corpus export that covers every required chunk_id "
            f"from the golden set: current input exposes {available_chunk_count} chunks and "
            f"is missing {all_questions['missing_chunk_count']} of "
            f"{all_questions['required_chunk_count']} required chunks."
        )
    if non_smoke_questions.get("missing_chunk_count"):
        steps.append(
            "If you want a local non-smoke preflight before live Qdrant work, start with the "
            f"{non_smoke_questions['question_count']} non-smoke questions already in repo and "
            f"add the {non_smoke_questions['missing_chunk_count']} missing chunks with "
            "`doc_id`, `chunk_id`, `content`, and `metadata.law_ref`/`source_url`."
        )
    if args.built_in_legal_corpus and all_questions.get("missing_chunk_count"):
        steps.append(
            "Extend `backend/src/services/legal_corpus_loader.py::get_all_legal_corpus()` "
            "to add the missing compliance/litigation statutes required by full50 "
            "(currently missing PIPL, Data Security Law, Cybersecurity Law, Company Law, "
            "Advertising Law, Consumer Rights Protection Law, E-commerce Law, Civil "
            "Procedure Law, and Civil Procedure Evidence Rules coverage)."
        )
    if not steps:
        steps.append(
            "Rerun the full50 preflight against the commercial golden/corpus pair and then "
            "generate live predictions plus full metrics."
        )
    return steps


def validate_full50_scope(
    *,
    questions: list[GoldenQuestion],
    chunks: list[CorpusChunk],
    min_questions: int,
    allow_missing_law_refs: bool,
) -> None:
    if len(questions) < min_questions:
        raise ValueError(f"Golden set selected {len(questions)} questions; need at least {min_questions}")

    chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    missing_chunks = sorted(_required_chunk_ids(questions).difference(chunks_by_id))
    if missing_chunks:
        sample = ", ".join(missing_chunks[:20])
        raise ValueError(
            f"Corpus is missing {len(missing_chunks)} golden relevant chunks: {sample}"
        )

    if allow_missing_law_refs:
        return

    law_ref_gaps: list[str] = []
    for question in questions:
        expected = set(question.expected_law_refs)
        if not expected:
            continue
        available = {
            str(chunks_by_id[chunk_id].metadata.get("law_ref"))
            for chunk_id in question.relevant_ids
            if chunks_by_id[chunk_id].metadata.get("law_ref")
        }
        if not expected.issubset(available):
            missing = ", ".join(sorted(expected.difference(available)))
            law_ref_gaps.append(f"{question.id}: {missing}")

    if law_ref_gaps:
        sample = "; ".join(law_ref_gaps[:12])
        raise ValueError(
            "Corpus relevant chunks do not expose expected law_ref metadata: " + sample
        )


def _non_commercial_overrides(args: argparse.Namespace) -> dict[str, bool]:
    return {
        "allow_fixture_corpus": bool(args.allow_fixture_corpus),
        "allow_smoke_golden": bool(args.allow_smoke_golden),
        "allow_missing_law_refs": bool(args.allow_missing_law_refs),
    }


def _non_commercial_override_count(args: argparse.Namespace) -> int:
    return sum(1 for enabled in _non_commercial_overrides(args).values() if enabled)


def validate_live_mode_has_no_dry_run_overrides(args: argparse.Namespace) -> None:
    if args.preflight_only or _non_commercial_override_count(args) == 0:
        return
    enabled = [
        name.replace("_", "-")
        for name, enabled in _non_commercial_overrides(args).items()
        if enabled
    ]
    flags = ", ".join(f"--{name}" for name in enabled)
    raise ValueError(
        f"{flags} may only be used with --preflight-only. "
        "Live commercial predictions must use a non-fixture corpus, "
        "non-smoke golden set, and complete law_ref coverage."
    )


def build_commercial_provenance(
    *,
    args: argparse.Namespace,
    questions: list[GoldenQuestion],
    artifact_kind: str,
) -> dict[str, Any]:
    smoke_question_count = sum(1 for question in questions if question.smoke)
    override_count = _non_commercial_override_count(args)
    return {
        "artifact_kind": artifact_kind,
        "commercial_baseline_candidate": artifact_kind == "live_predictions"
        and override_count == 0
        and smoke_question_count == 0,
        "non_commercial_overrides": _non_commercial_overrides(args),
        "non_commercial_override_count": override_count,
        "smoke_question_count": smoke_question_count,
        "law_ref_coverage_required": not args.allow_missing_law_refs,
        "fixture_corpus_rejected": not args.allow_fixture_corpus,
        "smoke_golden_rejected": not args.allow_smoke_golden,
    }


def group_chunks_by_doc(chunks: list[CorpusChunk]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, chunk in enumerate(chunks):
        grouped[chunk.doc_id].append(
            {
                "chunk_id": chunk.chunk_id,
                "chunk_index": index,
                "title": chunk.title,
                "content": chunk.content,
                "source": chunk.source,
                "metadata": chunk.metadata,
            }
        )
    return dict(grouped)


async def generate_predictions(
    args: argparse.Namespace,
    raw_corpus: Any,
    chunks: list[CorpusChunk],
    questions: list[GoldenQuestion],
) -> dict[str, Any]:
    from src.core.config import settings
    from src.services.vector_store import vector_store

    if not vector_store.is_available:
        raise RuntimeError("Vector store is not available; check Qdrant and embedding config")

    if not args.skip_index:
        if args.recreate and not args.collection.startswith("rag_eval_"):
            raise ValueError(
                "Refusing to recreate a non-evaluation collection. Use a name starting "
                "with 'rag_eval_' or pass --no-recreate."
            )

        await vector_store.create_collection(args.collection, recreate=args.recreate)
        indexed = 0
        for doc_id, doc_chunks in group_chunks_by_doc(chunks).items():
            indexed += await vector_store.add_chunks(args.collection, doc_id, doc_chunks)
        if indexed != len(chunks):
            raise RuntimeError(f"Indexed {indexed} chunks, expected {len(chunks)}")
    else:
        indexed = None

    predictions = []
    for question in questions:
        results = await vector_store.search(
            collection_name=args.collection,
            query=question.query,
            top_k=args.top_k,
            score_threshold=args.score_threshold,
        )
        predictions.append(
            {
                "question_id": question.id,
                "retrieved_chunk_ids": [
                    str(result.get("metadata", {}).get("chunk_id") or result.get("id"))
                    for result in results
                ],
                "cited_law_refs": [
                    str(result.get("metadata", {}).get("law_ref"))
                    for result in results[: args.citation_top_k]
                    if result.get("metadata", {}).get("law_ref")
                ],
                "source_urls": [
                    str(result.get("metadata", {}).get("source_url"))
                    for result in results[: args.citation_top_k]
                    if result.get("metadata", {}).get("source_url")
                ],
                "scores": [result.get("score") for result in results],
            }
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "run_label": args.run_label,
        "mode": "live_qdrant_full50",
        "collection": args.collection,
        "qdrant_url": settings.QDRANT_URL,
        "embedding": vector_store.embedding_info,
        "indexed_chunks": indexed,
        "corpus": {
            "path": corpus_identifier(args),
            "sha256": corpus_sha256(args, raw_corpus),
            "chunk_count": len(chunks),
        },
        "golden": {
            "path": str(args.golden),
            "sha256": file_sha256(args.golden),
            "question_count": len(questions),
            "min_questions": args.min_questions,
            "smoke_question_count": sum(1 for question in questions if question.smoke),
        },
        "commercial_provenance": build_commercial_provenance(
            args=args,
            questions=questions,
            artifact_kind="live_predictions",
        ),
        "notes": [
            "Live Qdrant and configured embeddings were used.",
            "The corpus was provided by an external export and passed full golden-set coverage checks.",
        ],
        "predictions": predictions,
    }


def build_preflight_report(
    *,
    args: argparse.Namespace,
    raw_corpus: Any,
    chunks: list[CorpusChunk],
    questions: list[GoldenQuestion],
) -> dict[str, Any]:
    readiness = build_readiness_summary(args=args, chunks=chunks, questions=questions)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "run_label": args.run_label,
        "mode": "rag_full50_preflight",
        "status": "passed",
        "corpus": {
            "path": corpus_identifier(args),
            "sha256": corpus_sha256(args, raw_corpus),
            "chunk_count": len(chunks),
            "required_chunk_count": len(_required_chunk_ids(questions)),
        },
        "golden": {
            "path": str(args.golden),
            "sha256": file_sha256(args.golden),
            "question_count": len(questions),
            "min_questions": args.min_questions,
            "smoke_question_count": sum(1 for question in questions if question.smoke),
        },
        "checks": {
            "fixture_corpus_rejected": not args.allow_fixture_corpus,
            "smoke_golden_rejected": not args.allow_smoke_golden,
            "law_ref_coverage_required": not args.allow_missing_law_refs,
            "full_golden_chunk_coverage": True,
        },
        "commercial_provenance": build_commercial_provenance(
            args=args,
            questions=questions,
            artifact_kind="preflight",
        ),
        "readiness": readiness,
        "notes": [
            "No Qdrant or embedding provider calls were made in preflight-only mode.",
            "This artifact proves corpus/golden shape and coverage only; it is not a live recall baseline.",
        ],
    }


def _safe_sha256(path: Path) -> str | None:
    return file_sha256(path) if path.exists() else None


def _law_ref_gap_sample(
    *,
    chunks_by_id: dict[str, CorpusChunk],
    questions: list[GoldenQuestion],
    limit: int = 20,
) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    for question in questions:
        expected = set(question.expected_law_refs)
        if not expected:
            continue
        available = {
            str(chunks_by_id[chunk_id].metadata.get("law_ref"))
            for chunk_id in question.relevant_ids
            if chunk_id in chunks_by_id and chunks_by_id[chunk_id].metadata.get("law_ref")
        }
        missing = sorted(expected.difference(available))
        if missing:
            gaps.append({"question_id": question.id, "missing_law_refs": ", ".join(missing)})
            if len(gaps) >= limit:
                break
    return gaps


def write_failure_report(
    *,
    args: argparse.Namespace,
    error: Exception,
    raw_corpus: Any | None,
    chunks: list[CorpusChunk] | None,
    questions: list[GoldenQuestion] | None,
) -> None:
    if args.failure_out is None:
        return

    available_chunk_ids = {chunk.chunk_id for chunk in chunks or []}
    required_chunk_ids = _required_chunk_ids(questions or [])
    missing_chunk_ids = sorted(required_chunk_ids.difference(available_chunk_ids))
    chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks or []}
    smoke_question_ids = [question.id for question in questions or [] if question.smoke]
    readiness = build_readiness_summary(args=args, chunks=chunks, questions=questions)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "run_label": args.run_label,
        "mode": "rag_full50_preflight_failure",
        "status": "failed",
        "error": {
            "type": type(error).__name__,
            "message": str(error),
        },
        "corpus": {
            "path": corpus_identifier(args),
            "sha256": corpus_sha256(args, raw_corpus) if raw_corpus is not None else _safe_sha256(args.corpus) if args.corpus is not None else None,
            "chunk_count": len(chunks or []),
            "available_chunk_count": len(available_chunk_ids),
        },
        "golden": {
            "path": str(args.golden),
            "sha256": _safe_sha256(args.golden),
            "question_count": len(questions or []),
            "min_questions": args.min_questions,
            "smoke_question_count": len(smoke_question_ids),
            "smoke_question_sample": smoke_question_ids[:50],
        },
        "diagnostics": {
            "required_chunk_count": len(required_chunk_ids),
            "missing_chunk_count": len(missing_chunk_ids),
            "missing_chunk_sample": missing_chunk_ids[:200],
            "law_ref_gap_sample": _law_ref_gap_sample(
                chunks_by_id=chunks_by_id,
                questions=questions or [],
            ),
        },
        "commercial_provenance": (
            build_commercial_provenance(args=args, questions=questions, artifact_kind="preflight_failure")
            if questions is not None
            else {
                "artifact_kind": "preflight_failure",
                "commercial_baseline_candidate": False,
                "non_commercial_overrides": _non_commercial_overrides(args),
                "non_commercial_override_count": _non_commercial_override_count(args),
                "smoke_question_count": 0,
            }
        ),
        "readiness": readiness,
        "next_steps": build_next_steps(args=args, readiness=readiness),
        "completion_note": (
            "Failure diagnostics only. Keep release evidence Status: pending until "
            "commercial golden/corpus coverage and live Qdrant metrics pass."
        ),
    }
    args.failure_out.parent.mkdir(parents=True, exist_ok=True)
    args.failure_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote RAG full50 failure artifact: {args.failure_out}", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, default=REPO_ROOT / "eval" / "rag_golden_set.jsonl")
    parser.add_argument("--corpus", type=Path, help="Business corpus JSON/JSONL export")
    parser.add_argument(
        "--built-in-legal-corpus",
        action="store_true",
        help="Use backend/src/services/legal_corpus_loader.py as the built-in corpus source",
    )
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--failure-out",
        type=Path,
        help="Write a redacted JSON diagnostic artifact when preflight validation fails",
    )
    parser.add_argument("--collection", default="rag_eval_full50_live")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--citation-top-k", type=int, default=3)
    parser.add_argument("--score-threshold", type=float, default=0.0)
    parser.add_argument("--min-questions", type=int, default=DEFAULT_MIN_QUESTIONS)
    parser.add_argument("--run-label", default="rag-live-qdrant-full50")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate corpus/golden coverage without connecting to Qdrant",
    )
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Query an existing collection while still validating the supplied corpus export",
    )
    parser.add_argument(
        "--no-recreate",
        dest="recreate",
        action="store_false",
        help="Upsert into the collection instead of recreating it first",
    )
    parser.add_argument(
        "--allow-fixture-corpus",
        action="store_true",
        help="Allow smoke/demo/sample corpus paths or metadata for non-commercial dry runs",
    )
    parser.add_argument(
        "--allow-smoke-golden",
        action="store_true",
        help="Allow golden rows marked smoke=true for non-commercial dry runs",
    )
    parser.add_argument(
        "--allow-missing-law-refs",
        action="store_true",
        help="Do not require relevant chunks to expose every expected law_ref",
    )
    parser.set_defaults(recreate=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_live_mode_has_no_dry_run_overrides(args)
    if args.built_in_legal_corpus and args.corpus is not None:
        raise ValueError("Use either --corpus or --built-in-legal-corpus, not both")
    if not args.built_in_legal_corpus and args.corpus is None:
        raise ValueError("Either --corpus or --built-in-legal-corpus is required")
    raw_corpus: Any | None = None
    chunks: list[CorpusChunk] | None = None
    questions: list[GoldenQuestion] | None = None
    try:
        raw_corpus, chunks = load_selected_corpus(args)
        validate_not_fixture_corpus(
            raw_corpus,
            BUILTIN_CORPUS_SOURCE if args.built_in_legal_corpus else args.corpus,
            args.allow_fixture_corpus,
        )
        questions = load_golden(args.golden, smoke_only=False)
        validate_not_smoke_golden(
            questions,
            golden_path=args.golden,
            allow_smoke_golden=args.allow_smoke_golden,
        )
        validate_full50_scope(
            questions=questions,
            chunks=chunks,
            min_questions=args.min_questions,
            allow_missing_law_refs=args.allow_missing_law_refs,
        )
    except (RuntimeError, ValueError) as exc:
        write_failure_report(
            args=args,
            error=exc,
            raw_corpus=raw_corpus,
            chunks=chunks,
            questions=questions,
        )
        raise
    assert chunks is not None
    assert questions is not None
    assert raw_corpus is not None

    if args.preflight_only:
        report = build_preflight_report(
            args=args,
            raw_corpus=raw_corpus,
            chunks=chunks,
            questions=questions,
        )
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote RAG full50 preflight artifact: {args.out}")
        print(
            "RAG full50 corpus preflight passed "
            f"questions={len(questions)} chunks={len(chunks)} "
            f"required_chunks={len(_required_chunk_ids(questions))}"
        )
        return 0

    report = asyncio.run(generate_predictions(args, raw_corpus, chunks, questions))
    out_path = args.out or DEFAULT_PREDICTIONS_OUT
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "RAG live Qdrant full50 "
        f"collection={report['collection']} indexed_chunks={report['indexed_chunks']} "
        f"predictions={len(report['predictions'])}"
    )
    return 0


def cli() -> int:
    try:
        return main()
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())
