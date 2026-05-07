import json
import subprocess
import sys
from pathlib import Path


def test_rag_quality_smoke_generates_recall_mrr_ndcg(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    output = tmp_path / "rag_baseline.json"

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "eval" / "rag_quality.py"),
            "--golden",
            str(repo_root / "eval" / "rag_golden_set.jsonl"),
            "--predictions",
            str(repo_root / "eval" / "rag_predictions_smoke.json"),
            "--out",
            str(output),
            "--smoke",
            "--run-label",
            "pytest-smoke",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))

    assert "recall@10=" in result.stdout
    assert report["mode"] == "smoke"
    assert report["status"] == "offline_predictions_only"
    assert report["summary"]["question_count"] == 10
    assert report["summary"]["recall@5"] >= 0.8
    assert report["summary"]["recall@10"] >= report["summary"]["recall@5"]
    assert report["summary"]["mrr"] > 0
    assert report["summary"]["ndcg@10"] > 0


def test_rag_quality_marks_live_prediction_exports(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    predictions = tmp_path / "live_predictions.json"
    output = tmp_path / "rag_live_baseline.json"
    predictions.write_text(
        json.dumps(
            {
                "mode": "live_qdrant_smoke",
                "predictions": [
                    {
                        "question_id": "Q-0001",
                        "retrieved_chunk_ids": ["civil_code_490_0"],
                        "cited_law_refs": ["民法典:第490条"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(repo_root / "eval" / "rag_quality.py"),
            "--golden",
            str(repo_root / "eval" / "rag_golden_set.jsonl"),
            "--predictions",
            str(predictions),
            "--out",
            str(output),
            "--smoke",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))

    assert report["status"] == "live_predictions_export"


def test_rag_quality_rejects_smoke_golden_for_full_metrics(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    predictions = tmp_path / "live_predictions.json"
    output = tmp_path / "rag_live_baseline.json"
    predictions.write_text(
        json.dumps(
            {
                "mode": "live_qdrant_full50",
                "commercial_provenance": {
                    "non_commercial_overrides": {},
                    "non_commercial_override_count": 0,
                    "smoke_question_count": 0,
                },
                "predictions": [
                    {
                        "question_id": "Q-0001",
                        "retrieved_chunk_ids": ["civil_code_490_0"],
                        "cited_law_refs": ["民法典:第490条"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "eval" / "rag_quality.py"),
            "--golden",
            str(repo_root / "eval" / "rag_golden_set.jsonl"),
            "--predictions",
            str(predictions),
            "--out",
            str(output),
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "cannot use smoke-marked golden rows" in result.stderr
    assert not output.exists()


def test_rag_quality_requires_provenance_for_full_live_metrics(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    golden = tmp_path / "commercial-golden.jsonl"
    predictions = tmp_path / "live_predictions.json"
    output = tmp_path / "rag_live_baseline.json"
    golden.write_text(
        json.dumps(
            {
                "id": "Q-COMM-1",
                "category": "contract",
                "query": "商业合同问题",
                "relevant_chunk_ids": ["commercial_chunk_1"],
                "expected_law_refs": ["民法典:第490条"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    predictions.write_text(
        json.dumps(
            {
                "mode": "live_qdrant_full50",
                "predictions": [
                    {
                        "question_id": "Q-COMM-1",
                        "retrieved_chunk_ids": ["commercial_chunk_1"],
                        "cited_law_refs": ["民法典:第490条"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "eval" / "rag_quality.py"),
            "--golden",
            str(golden),
            "--predictions",
            str(predictions),
            "--out",
            str(output),
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "requires predictions commercial_provenance" in result.stderr
    assert not output.exists()
