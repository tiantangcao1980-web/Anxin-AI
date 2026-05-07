#!/usr/bin/env python3
"""Generate live Qdrant smoke predictions for the RAG golden set.

This is a plumbing baseline, not a production quality claim: it writes a small
fixed legal corpus into a temporary Qdrant collection with the configured
embedding provider, queries that live collection, and emits the same prediction
schema consumed by ``eval/rag_quality.py``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rag_quality import load_golden

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

SMOKE_CORPUS: dict[str, dict[str, str]] = {
    "civil_code_490_0": {
        "doc_id": "civil_code_490",
        "title": "《民法典》第490条 合同成立时间",
        "source": "民法典",
        "law_ref": "民法典:第490条",
        "content": "当事人采用书面形式订立合同的，自当事人均签名、盖章或者按指印时合同成立。一方已经履行主要义务，对方接受时，该合同成立。",
    },
    "civil_code_496_0": {
        "doc_id": "civil_code_496",
        "title": "《民法典》第496条 格式条款提示说明义务",
        "source": "民法典",
        "law_ref": "民法典:第496条",
        "content": "采用格式条款订立合同的，提供格式条款的一方应当遵循公平原则确定权利义务，并采取合理方式提示免除或者减轻其责任等与对方有重大利害关系的条款。",
    },
    "civil_code_497_0": {
        "doc_id": "civil_code_497",
        "title": "《民法典》第497条 格式条款无效情形",
        "source": "民法典",
        "law_ref": "民法典:第497条",
        "content": "格式条款具有不合理地免除或者减轻其责任、加重对方责任、限制对方主要权利等情形的，该格式条款无效。",
    },
    "civil_code_585_0": {
        "doc_id": "civil_code_585",
        "title": "《民法典》第585条 违约金调整",
        "source": "民法典",
        "law_ref": "民法典:第585条",
        "content": "约定的违约金低于造成的损失的，人民法院或者仲裁机构可以根据请求予以增加；约定的违约金过分高于造成的损失的，可以根据请求予以适当减少。",
    },
    "civil_code_590_0": {
        "doc_id": "civil_code_590",
        "title": "《民法典》第590条 不可抗力",
        "source": "民法典",
        "law_ref": "民法典:第590条",
        "content": "当事人一方因不可抗力不能履行合同的，根据不可抗力的影响，部分或者全部免除责任，但法律另有规定的除外；迟延履行后发生不可抗力的，不免除其违约责任。",
    },
    "labor_contract_law_10_0": {
        "doc_id": "labor_contract_law_10",
        "title": "《劳动合同法》第10条 书面劳动合同",
        "source": "劳动合同法",
        "law_ref": "劳动合同法:第10条",
        "content": "建立劳动关系，应当订立书面劳动合同。已建立劳动关系未同时订立书面劳动合同的，应当自用工之日起一个月内订立。",
    },
    "labor_contract_law_82_0": {
        "doc_id": "labor_contract_law_82",
        "title": "《劳动合同法》第82条 二倍工资",
        "source": "劳动合同法",
        "law_ref": "劳动合同法:第82条",
        "content": "用人单位自用工之日起超过一个月不满一年未与劳动者订立书面劳动合同的，应当向劳动者每月支付二倍的工资。",
    },
    "labor_contract_law_19_0": {
        "doc_id": "labor_contract_law_19",
        "title": "《劳动合同法》第19条 试用期",
        "source": "劳动合同法",
        "law_ref": "劳动合同法:第19条",
        "content": "同一用人单位与同一劳动者只能约定一次试用期。试用期包含在劳动合同期限内。",
    },
    "labor_contract_law_37_0": {
        "doc_id": "labor_contract_law_37",
        "title": "《劳动合同法》第37条 劳动者解除合同",
        "source": "劳动合同法",
        "law_ref": "劳动合同法:第37条",
        "content": "劳动者提前三十日以书面形式通知用人单位，可以解除劳动合同；在试用期内提前三日通知用人单位，可以解除劳动合同。",
    },
    "labor_contract_law_23_0": {
        "doc_id": "labor_contract_law_23",
        "title": "《劳动合同法》第23条 竞业限制违约金",
        "source": "劳动合同法",
        "law_ref": "劳动合同法:第23条",
        "content": "对负有保密义务的劳动者，用人单位可以约定竞业限制条款，并约定劳动者违反竞业限制约定的，应当按照约定向用人单位支付违约金。",
    },
    "labor_contract_law_24_0": {
        "doc_id": "labor_contract_law_24",
        "title": "《劳动合同法》第24条 竞业限制范围期限",
        "source": "劳动合同法",
        "law_ref": "劳动合同法:第24条",
        "content": "竞业限制的人员限于高级管理人员、高级技术人员和其他负有保密义务的人员；竞业限制期限不得超过二年。",
    },
    "civil_procedure_law_34_0": {
        "doc_id": "civil_procedure_law_34",
        "title": "《民事诉讼法》第34条 协议管辖",
        "source": "民事诉讼法",
        "law_ref": "民事诉讼法:第34条",
        "content": "合同或者其他财产权益纠纷的当事人可以书面协议选择与争议有实际联系地点的人民法院管辖，但不得违反级别管辖和专属管辖的规定。",
    },
    "civil_procedure_law_35_0": {
        "doc_id": "civil_procedure_law_35",
        "title": "《民事诉讼法》第35条 共同管辖",
        "source": "民事诉讼法",
        "law_ref": "民事诉讼法:第35条",
        "content": "两个以上人民法院都有管辖权的诉讼，原告可以向其中一个人民法院起诉；原告向两个以上有管辖权的人民法院起诉的，由最先立案的人民法院管辖。",
    },
    "pipl_13_0": {
        "doc_id": "pipl_13",
        "title": "《个人信息保护法》第13条 合法性基础",
        "source": "个人信息保护法",
        "law_ref": "个人信息保护法:第13条",
        "content": "符合取得个人的同意、为订立履行合同所必需、履行法定职责或者法定义务所必需等情形之一的，个人信息处理者方可处理个人信息。",
    },
    "pipl_14_0": {
        "doc_id": "pipl_14",
        "title": "《个人信息保护法》第14条 同意",
        "source": "个人信息保护法",
        "law_ref": "个人信息保护法:第14条",
        "content": "基于个人同意处理个人信息的，该同意应当由个人在充分知情的前提下自愿、明确作出。法律规定应当取得单独同意或者书面同意的，从其规定。",
    },
}


def _build_chunks() -> dict[str, list[dict[str, Any]]]:
    chunks_by_doc: dict[str, list[dict[str, Any]]] = {}
    for chunk_id, row in SMOKE_CORPUS.items():
        chunks_by_doc.setdefault(row["doc_id"], []).append(
            {
                "chunk_id": chunk_id,
                "title": row["title"],
                "content": row["content"],
                "source": row["source"],
                "metadata": {
                    "law_ref": row["law_ref"],
                    "source_url": f"/knowledge/documents/{row['doc_id']}#{chunk_id}",
                },
            }
        )
    return chunks_by_doc


async def generate_predictions(args: argparse.Namespace) -> dict[str, Any]:
    from src.core.config import settings
    from src.services.vector_store import vector_store

    if not vector_store.is_available:
        raise RuntimeError("Vector store is not available; check Qdrant and embedding config")

    collection = args.collection
    await vector_store.create_collection(collection, recreate=True)
    indexed = 0
    for doc_id, chunks in _build_chunks().items():
        indexed += await vector_store.add_chunks(collection, doc_id, chunks)

    if indexed == 0:
        raise RuntimeError("No chunks indexed into Qdrant")

    questions = load_golden(args.golden, smoke_only=True)
    predictions = []
    for question in questions:
        results = await vector_store.search(
            collection_name=collection,
            query=question.query,
            top_k=args.top_k,
            score_threshold=0.0,
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
                "scores": [result.get("score") for result in results],
            }
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "run_label": args.run_label,
        "mode": "live_qdrant_smoke",
        "collection": collection,
        "qdrant_url": settings.QDRANT_URL,
        "embedding": vector_store.embedding_info,
        "indexed_chunks": indexed,
        "notes": [
            "Live Qdrant and configured embeddings were used.",
            "Corpus is a fixed smoke corpus for plumbing validation, not the full production legal knowledge base.",
        ],
        "predictions": predictions,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, default=REPO_ROOT / "eval" / "rag_golden_set.jsonl")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "eval" / "rag_live_predictions_smoke.json")
    parser.add_argument("--collection", default="rag_eval_smoke_live")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--citation-top-k", type=int, default=3)
    parser.add_argument("--run-label", default="rag-live-qdrant-smoke-2026-05-06")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = asyncio.run(generate_predictions(args))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "RAG live Qdrant smoke "
        f"collection={report['collection']} indexed_chunks={report['indexed_chunks']} "
        f"predictions={len(report['predictions'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
