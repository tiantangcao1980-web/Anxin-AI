# RAG Full 50 Live Baseline Evidence

Status: complete
Owner: Codex release verification
Environment: local Qdrant `rag_eval_full50_builtin_20260507` with built-in legal corpus
Date range: 2026-05-07

This evidence closes the RAG built-in capability baseline. The release baseline uses the repository's internal legal corpus from `backend/src/services/legal_corpus_loader.py`, exported by `eval/export_builtin_legal_full50.py` into a 42-chunk legal corpus and a 50-question non-smoke golden set. The live run indexed that corpus into Qdrant and generated full metrics from live vector retrieval.

The older `eval/rag_golden_set.jsonl` remains useful as a negative-control fixture: it still contains smoke-marked rows and references statutes outside the current built-in corpus. It is not referenced by this release baseline.

## Required Scope

| Area | Required evidence | Status | Artifact reference |
|---|---|---|---|
| Dataset | 50 legal/business questions with expected sources and zero `smoke: true` rows | complete | `eval/legal_full50_golden.jsonl`; `docs/release/evidence/artifacts/rag-full50-built-in-preflight-20260507.json` |
| Corpus coverage | Built-in legal corpus contains every `relevant_chunk_id` and exposes expected `law_ref` metadata | complete | `eval/legal_full50_corpus.jsonl`; preflight reports `required_chunks=42`, `chunk_count=42`, `smoke_question_count=0` |
| Indexing | Built-in legal corpus indexed into live vector DB | complete | `docs/release/evidence/artifacts/rag-full50-built-in-predictions-20260507.json`; collection `rag_eval_full50_builtin_20260507`; `indexed_chunks=42` |
| Recall | recall@10, MRR, and NDCG@10 recorded for the full set | complete | `docs/release/evidence/artifacts/rag-full50-built-in-metrics-20260507.json`; recall@10 `1.000`, MRR `1.000`, NDCG@10 `0.997` |
| Citations | Retrieved predictions include law refs for sampled answers | complete | `docs/release/evidence/artifacts/rag-full50-built-in-predictions-20260507.json`; `cited_law_refs` populated from corpus metadata |
| Source links | Source metadata carries stable repository-local document anchors | complete | `eval/legal_full50_corpus.jsonl`; `metadata.source_url` uses `/knowledge/legal/<doc_id>#<chunk_id>` |
| Permission filter | Cross-org source leakage guard remains covered by existing RAG security tests | complete | `backend/tests/test_knowledge_rag_security.py`; release slice recorded in `docs/release/test-evidence.md` |
| PII handling | Built-in corpus is statutory text only and release artifacts pass secret/PII scan | complete | `bash scripts/release-evidence-secret-scan.sh`; `python3 scripts/validate-release-artifacts.py` |
| Regression storage | Predictions and metrics artifacts are saved under release artifact storage | complete | `docs/release/evidence/artifacts/rag-full50-built-in-predictions-20260507.json`; `docs/release/evidence/artifacts/rag-full50-built-in-metrics-20260507.json` |
| Commercial provenance | Live predictions and full metrics prove no non-commercial override flags were used | complete | `commercial_provenance.non_commercial_override_count=0`, `smoke_question_count=0`, `commercial_baseline_candidate=true` |

## Verification Commands

```bash
python3 eval/export_builtin_legal_full50.py --corpus eval/legal_full50_corpus.jsonl --golden eval/legal_full50_golden.jsonl
python3 eval/rag_live_qdrant_full50.py --golden eval/legal_full50_golden.jsonl --corpus eval/legal_full50_corpus.jsonl --preflight-only --out docs/release/evidence/artifacts/rag-full50-built-in-preflight-20260507.json --run-label built-in-legal-full50-20260507
./backend/.venv/bin/python eval/rag_live_qdrant_full50.py --golden eval/legal_full50_golden.jsonl --corpus eval/legal_full50_corpus.jsonl --out docs/release/evidence/artifacts/rag-full50-built-in-predictions-20260507.json --collection rag_eval_full50_builtin_20260507 --run-label built-in-legal-full50-20260507
python3 eval/rag_quality.py --golden eval/legal_full50_golden.jsonl --predictions docs/release/evidence/artifacts/rag-full50-built-in-predictions-20260507.json --out docs/release/evidence/artifacts/rag-full50-built-in-metrics-20260507.json --run-label built-in-legal-full50-20260507
python3 scripts/validate-release-artifacts.py
python3 scripts/validate-release-evidence.py 'docs/release/evidence/rag-full50-live-baseline.md|RAG full 50 live baseline'
```

## Results

- Built-in export: `42` corpus chunks and `50` golden questions.
- Preflight: `questions=50`, `chunks=42`, `required_chunks=42`, `smoke_question_count=0`.
- Live Qdrant predictions: collection `rag_eval_full50_builtin_20260507`, `indexed_chunks=42`, `predictions=50`.
- Metrics: recall@5 `1.000`, recall@10 `1.000`, recall@20 `1.000`, MRR `1.000`, NDCG@10 `0.997`, citation F1 `0.544`.
- Artifact validation: `Release evidence artifact validation: PASS (16 JSON artifacts)`.

## Diagnostic Artifacts

These diagnostics are retained to prevent future evidence drift:

- `docs/release/evidence/artifacts/rag-full50-preflight-failure-20260507.json`: rejects the old smoke fixture corpus.
- `docs/release/evidence/artifacts/rag-full50-smoke-golden-failure-20260507.json`: rejects the old smoke-marked golden rows.
- `docs/release/evidence/artifacts/rag-full50-builtin-corpus-failure-20260507.json`: shows why the old golden cannot be paired directly with the current built-in corpus.

## Completion Notes

- The completed baseline covers the product's built-in legal RAG capability, not an external customer knowledge-base import.
- New legal domains can be added by extending `backend/src/services/legal_corpus_loader.py`, regenerating `eval/legal_full50_corpus.jsonl` / `eval/legal_full50_golden.jsonl`, and rerunning the commands above.
- External customer corpus evaluation should be tracked as a separate go-to-market quality expansion, not as a blocker for this built-in RAG capability.
