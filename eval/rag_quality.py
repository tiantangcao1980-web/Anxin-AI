#!/usr/bin/env python3
"""Offline RAG quality metrics for fixed golden sets.

The script intentionally works from exported predictions instead of calling a
live vector database. That makes the smoke gate deterministic in CI; live
retrieval runs can write the same prediction schema and reuse the metrics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RECALL_CUTOFFS = (5, 10, 20)
NDCG_CUTOFF = 10


@dataclass(frozen=True)
class GoldenQuestion:
    id: str
    category: str
    query: str
    relevant_ids: tuple[str, ...]
    expected_law_refs: tuple[str, ...]
    smoke: bool = False


@dataclass(frozen=True)
class Prediction:
    question_id: str
    retrieved_ids: tuple[str, ...]
    cited_law_refs: tuple[str, ...]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number} is not valid JSON") from exc
    return rows


def load_golden(path: Path, smoke_only: bool = False) -> list[GoldenQuestion]:
    questions: list[GoldenQuestion] = []
    for row in load_jsonl(path):
        relevant = row.get("relevant_chunk_ids") or row.get("relevant_doc_ids") or []
        if not relevant:
            raise ValueError(f"Golden question {row.get('id')} has no relevant ids")
        question = GoldenQuestion(
            id=str(row["id"]),
            category=str(row.get("category", "uncategorized")),
            query=str(row["query"]),
            relevant_ids=tuple(str(item) for item in relevant),
            expected_law_refs=tuple(str(item) for item in row.get("expected_law_refs", [])),
            smoke=bool(row.get("smoke", False)),
        )
        if not smoke_only or question.smoke:
            questions.append(question)
    if not questions:
        raise ValueError("No golden questions selected")
    return questions


def load_predictions(path: Path) -> dict[str, Prediction]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("predictions", data) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError("Predictions must be a list or {'predictions': [...]}")

    predictions: dict[str, Prediction] = {}
    for row in rows:
        retrieved = row.get("retrieved_chunk_ids") or row.get("retrieved_doc_ids") or []
        question_id = str(row["question_id"])
        predictions[question_id] = Prediction(
            question_id=question_id,
            retrieved_ids=tuple(str(item) for item in retrieved),
            cited_law_refs=tuple(str(item) for item in row.get("cited_law_refs", [])),
        )
    return predictions


def recall_at_k(relevant: set[str], retrieved: tuple[str, ...], k: int) -> float:
    if not relevant:
        return 0.0
    return len(relevant.intersection(retrieved[:k])) / len(relevant)


def reciprocal_rank(relevant: set[str], retrieved: tuple[str, ...]) -> float:
    for index, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / index
    return 0.0


def ndcg_at_k(relevant: set[str], retrieved: tuple[str, ...], k: int = NDCG_CUTOFF) -> float:
    if not relevant:
        return 0.0

    def gain(rank: int) -> float:
        item = retrieved[rank - 1]
        relevance = 1.0 if item in relevant else 0.0
        return relevance / math.log2(rank + 1)

    dcg = sum(gain(rank) for rank in range(1, min(k, len(retrieved)) + 1))
    ideal_hits = min(len(relevant), k)
    ideal_dcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / ideal_dcg if ideal_dcg else 0.0


def f1_score(expected: set[str], actual: set[str]) -> float:
    if not expected and not actual:
        return 1.0
    if not expected or not actual:
        return 0.0
    true_positive = len(expected.intersection(actual))
    if true_positive == 0:
        return 0.0
    precision = true_positive / len(actual)
    recall = true_positive / len(expected)
    return 2 * precision * recall / (precision + recall)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def evaluate(
    questions: list[GoldenQuestion],
    predictions: dict[str, Prediction],
) -> dict[str, Any]:
    per_question: list[dict[str, Any]] = []
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for question in questions:
        prediction = predictions.get(question.id, Prediction(question.id, tuple(), tuple()))
        relevant = set(question.relevant_ids)
        expected_law_refs = set(question.expected_law_refs)
        cited_law_refs = set(prediction.cited_law_refs)
        row = {
            "id": question.id,
            "category": question.category,
            "query": question.query,
            "retrieved_count": len(prediction.retrieved_ids),
            "mrr": reciprocal_rank(relevant, prediction.retrieved_ids),
            "ndcg@10": ndcg_at_k(relevant, prediction.retrieved_ids, NDCG_CUTOFF),
            "citation_f1": f1_score(expected_law_refs, cited_law_refs),
        }
        for cutoff in RECALL_CUTOFFS:
            row[f"recall@{cutoff}"] = recall_at_k(relevant, prediction.retrieved_ids, cutoff)
        per_question.append(row)
        by_category[question.category].append(row)

    def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
        summary = {
            "question_count": len(rows),
            "mrr": _mean([row["mrr"] for row in rows]),
            "ndcg@10": _mean([row["ndcg@10"] for row in rows]),
            "citation_f1": _mean([row["citation_f1"] for row in rows]),
        }
        for cutoff in RECALL_CUTOFFS:
            key = f"recall@{cutoff}"
            summary[key] = _mean([row[key] for row in rows])
        return summary

    return {
        "summary": summarize(per_question),
        "by_category": {
            category: summarize(rows)
            for category, rows in sorted(by_category.items(), key=lambda item: item[0])
        },
        "per_question": per_question,
    }


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _truthy_override_values(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    return [str(key) for key, enabled in value.items() if bool(enabled)]


def _as_nonnegative_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)


def validate_full_commercial_inputs(
    *,
    questions: list[GoldenQuestion],
    prediction_source: Any,
    prediction_mode: str,
    smoke_only: bool,
) -> None:
    if smoke_only:
        return

    smoke_questions = [question.id for question in questions if question.smoke]
    if smoke_questions:
        sample = ", ".join(smoke_questions[:12])
        raise ValueError(
            "Full RAG quality baseline cannot use smoke-marked golden rows "
            f"({len(smoke_questions)} questions, sample: {sample}). "
            "Pass --smoke for non-commercial smoke metrics or use a commercial full50 golden set."
        )

    provenance = (
        prediction_source.get("commercial_provenance")
        if isinstance(prediction_source, dict)
        else None
    )
    is_live_export = str(prediction_mode).startswith("live_")
    if is_live_export and not isinstance(provenance, dict):
        raise ValueError(
            "Full live RAG quality baseline requires predictions commercial_provenance; "
            "regenerate predictions with eval/rag_live_qdrant_full50.py."
        )
    if not isinstance(provenance, dict):
        return

    overrides = _truthy_override_values(provenance.get("non_commercial_overrides"))
    override_count = _as_nonnegative_int(provenance.get("non_commercial_override_count"))
    smoke_question_count = _as_nonnegative_int(provenance.get("smoke_question_count"))
    if overrides or override_count:
        details = ", ".join(sorted(set(overrides))) or f"count={override_count}"
        raise ValueError(
            "Full RAG quality baseline cannot use predictions generated with "
            f"non-commercial overrides: {details}"
        )
    if smoke_question_count:
        raise ValueError(
            "Full RAG quality baseline cannot use predictions whose provenance "
            f"reports smoke_question_count={smoke_question_count}"
        )


def build_report(
    golden_path: Path,
    predictions_path: Path,
    smoke_only: bool,
    run_label: str,
) -> dict[str, Any]:
    questions = load_golden(golden_path, smoke_only=smoke_only)
    predictions = load_predictions(predictions_path)
    prediction_source = json.loads(predictions_path.read_text(encoding="utf-8"))
    prediction_mode = (
        prediction_source.get("mode", "offline_predictions")
        if isinstance(prediction_source, dict)
        else "offline_predictions"
    )
    is_live_export = str(prediction_mode).startswith("live_")
    commercial_provenance = (
        prediction_source.get("commercial_provenance")
        if isinstance(prediction_source, dict)
        else None
    )
    validate_full_commercial_inputs(
        questions=questions,
        prediction_source=prediction_source,
        prediction_mode=str(prediction_mode),
        smoke_only=smoke_only,
    )
    metrics = evaluate(questions, predictions)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "run_label": run_label,
        "mode": "smoke" if smoke_only else "full",
        "status": "live_predictions_export" if is_live_export else "offline_predictions_only",
        "notes": [
            (
                "Metrics are computed from predictions exported by a live vector-store run."
                if is_live_export
                else "Metrics are computed from exported predictions; no live vector store was queried."
            ),
            (
                "Use the same prediction schema for live Qdrant/RAG runs before tuning "
                "top-k or reranker thresholds."
            ),
        ],
        "inputs": {
            "golden_path": str(golden_path),
            "golden_sha256": file_sha256(golden_path),
            "predictions_path": str(predictions_path),
            "predictions_sha256": file_sha256(predictions_path),
        },
        **({"commercial_provenance": commercial_provenance} if isinstance(commercial_provenance, dict) else {}),
        **metrics,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, required=True, help="JSONL golden question set")
    parser.add_argument("--predictions", type=Path, required=True, help="JSON predictions file")
    parser.add_argument("--out", type=Path, required=True, help="Output baseline JSON")
    parser.add_argument("--smoke", action="store_true", help="Evaluate only rows with smoke=true")
    parser.add_argument(
        "--run-label", default="rag-quality-baseline", help="Human readable run label"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build_report(
            golden_path=args.golden,
            predictions_path=args.predictions,
            smoke_only=args.smoke,
            run_label=args.run_label,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = report["summary"]
    print(
        "RAG quality "
        f"{report['mode']} questions={summary['question_count']} "
        f"recall@10={summary['recall@10']:.3f} "
        f"mrr={summary['mrr']:.3f} "
        f"ndcg@10={summary['ndcg@10']:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
