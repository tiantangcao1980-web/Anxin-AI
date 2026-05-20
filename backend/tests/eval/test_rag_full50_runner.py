import json
import subprocess
import sys
from pathlib import Path


def _write_minimal_inputs(tmp_path: Path, *, smoke: bool) -> tuple[Path, Path]:
    golden = tmp_path / "commercial-golden.jsonl"
    corpus = tmp_path / "business-corpus.jsonl"
    golden.write_text(
        json.dumps(
            {
                "id": "Q-0001",
                "category": "contract",
                "query": "合同只有一方签字但另一方已经履行主要义务，合同是否成立？",
                "relevant_chunk_ids": ["civil_code_490_0"],
                "expected_law_refs": ["民法典:第490条"],
                "smoke": smoke,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    corpus.write_text(
        json.dumps(
            {
                "doc_id": "civil_code_490",
                "chunk_id": "civil_code_490_0",
                "content": "当事人采用合同书形式订立合同的，自当事人均签名、盖章或者按指印时合同成立。",
                "metadata": {"law_ref": "民法典:第490条"},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return golden, corpus


def _run_full50(
    repo_root: Path, golden: Path, corpus: Path, *extra: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / "eval" / "rag_live_qdrant_full50.py"),
            "--golden",
            str(golden),
            "--corpus",
            str(corpus),
            "--preflight-only",
            "--min-questions",
            "1",
            *extra,
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def _run_full50_builtin(
    repo_root: Path,
    golden: Path,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / "eval" / "rag_live_qdrant_full50.py"),
            "--golden",
            str(golden),
            "--built-in-legal-corpus",
            "--preflight-only",
            *extra,
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def _run_full50_live_attempt(
    repo_root: Path,
    golden: Path,
    corpus: Path,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / "eval" / "rag_live_qdrant_full50.py"),
            "--golden",
            str(golden),
            "--corpus",
            str(corpus),
            "--min-questions",
            "1",
            *extra,
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def test_full50_runner_rejects_smoke_marked_golden_by_default(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    golden, corpus = _write_minimal_inputs(tmp_path, smoke=True)

    result = _run_full50(repo_root, golden, corpus)

    assert result.returncode == 1
    assert "Golden set is marked as smoke/non-commercial" in result.stderr


def test_full50_runner_writes_failure_artifact_for_smoke_golden(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    golden, corpus = _write_minimal_inputs(tmp_path, smoke=True)
    failure_out = tmp_path / "rag-full50-failure.json"

    result = _run_full50(repo_root, golden, corpus, "--failure-out", str(failure_out))

    assert result.returncode == 1
    assert "Wrote RAG full50 failure artifact" in result.stderr
    report = json.loads(failure_out.read_text(encoding="utf-8"))
    assert report["mode"] == "rag_full50_preflight_failure"
    assert report["status"] == "failed"
    assert report["golden"]["smoke_question_count"] == 1
    assert report["golden"]["smoke_question_sample"] == ["Q-0001"]
    assert report["readiness"]["commercial_full50_ready"] is False
    assert "golden_contains_smoke_questions:1" in report["readiness"]["blockers"]
    assert report["next_steps"]


def test_full50_runner_allows_smoke_golden_only_for_dry_runs(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    golden, corpus = _write_minimal_inputs(tmp_path, smoke=True)

    result = _run_full50(repo_root, golden, corpus, "--allow-smoke-golden")

    assert result.returncode == 0
    assert "RAG full50 corpus preflight passed" in result.stdout


def test_full50_runner_accepts_non_smoke_golden(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    golden, corpus = _write_minimal_inputs(tmp_path, smoke=False)
    out = tmp_path / "rag-full50-preflight.json"

    result = _run_full50(repo_root, golden, corpus, "--out", str(out))

    assert result.returncode == 0
    assert "RAG full50 corpus preflight passed" in result.stdout
    assert "Wrote RAG full50 preflight artifact" in result.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["mode"] == "rag_full50_preflight"
    assert report["status"] == "passed"
    assert report["golden"]["question_count"] == 1
    assert report["commercial_provenance"]["artifact_kind"] == "preflight"
    assert report["commercial_provenance"]["non_commercial_override_count"] == 0
    assert report["corpus"]["required_chunk_count"] == 1
    assert report["checks"]["full_golden_chunk_coverage"] is True
    assert report["readiness"]["commercial_full50_ready"] is True
    assert report["readiness"]["all_questions"]["coverage_ratio"] == 1.0
    assert report["readiness"]["blockers"] == []


def test_full50_runner_writes_failure_artifact_for_missing_chunks(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    golden, corpus = _write_minimal_inputs(tmp_path, smoke=False)
    corpus.write_text(
        json.dumps(
            {
                "doc_id": "other_doc",
                "chunk_id": "other_doc_0",
                "content": "unrelated commercial corpus chunk",
                "metadata": {"law_ref": "民法典:第999条"},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    failure_out = tmp_path / "rag-full50-missing-chunk.json"

    result = _run_full50(repo_root, golden, corpus, "--failure-out", str(failure_out))

    assert result.returncode == 1
    assert "Corpus is missing 1 golden relevant chunks" in result.stderr
    report = json.loads(failure_out.read_text(encoding="utf-8"))
    assert report["diagnostics"]["missing_chunk_count"] == 1
    assert report["diagnostics"]["missing_chunk_sample"] == ["civil_code_490_0"]
    assert report["readiness"]["all_questions"]["missing_chunk_count"] == 1
    assert "corpus_missing_required_chunks:1" in report["readiness"]["blockers"]


def test_full50_runner_rejects_dry_run_overrides_for_live_mode(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    golden, corpus = _write_minimal_inputs(tmp_path, smoke=False)

    result = _run_full50_live_attempt(repo_root, golden, corpus, "--allow-missing-law-refs")

    assert result.returncode == 1
    assert "may only be used with --preflight-only" in result.stderr


def test_full50_runner_reports_repo_builtin_readiness_gap(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    failure_out = tmp_path / "rag-full50-repo-gap.json"

    result = _run_full50(
        repo_root,
        repo_root / "eval" / "rag_golden_set.jsonl",
        repo_root / "eval" / "citation_documents_smoke.json",
        "--allow-fixture-corpus",
        "--failure-out",
        str(failure_out),
    )

    assert result.returncode == 1
    assert "Golden set is marked as smoke/non-commercial" in result.stderr

    report = json.loads(failure_out.read_text(encoding="utf-8"))
    readiness = report["readiness"]
    assert readiness["uses_repo_local_corpus"] is True
    assert readiness["repo_relative_corpus_path"] == "eval/citation_documents_smoke.json"
    assert readiness["repo_relative_golden_path"] == "eval/rag_golden_set.jsonl"
    assert readiness["available_chunk_count"] == 3
    assert readiness["smoke_question_count"] == 10
    assert readiness["all_questions"]["required_chunk_count"] == 60
    assert readiness["all_questions"]["missing_chunk_count"] == 57
    assert readiness["all_questions"]["coverage_ratio"] == 0.05
    assert readiness["non_smoke_questions"]["question_count"] == 40
    assert readiness["non_smoke_questions"]["required_chunk_count"] == 47
    assert readiness["non_smoke_questions"]["available_required_chunk_count"] == 0
    assert readiness["non_smoke_questions"]["missing_chunk_count"] == 47
    assert readiness["commercial_full50_ready"] is False
    assert "golden_contains_smoke_questions:10" in readiness["blockers"]
    assert "corpus_missing_required_chunks:57" in readiness["blockers"]
    assert "corpus_missing_non_smoke_required_chunks:47" in readiness["blockers"]
    assert report["next_steps"]
    assert "non-smoke commercial export" in report["next_steps"][0]


def test_full50_runner_reports_internal_legal_corpus_gap(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    failure_out = tmp_path / "rag-full50-builtin-gap.json"

    result = _run_full50_builtin(
        repo_root,
        repo_root / "eval" / "rag_golden_set.jsonl",
        "--allow-smoke-golden",
        "--failure-out",
        str(failure_out),
    )

    assert result.returncode == 1
    assert "Corpus is missing 30 golden relevant chunks" in result.stderr

    report = json.loads(failure_out.read_text(encoding="utf-8"))
    readiness = report["readiness"]
    assert report["corpus"]["path"] == "builtin://legal_corpus_loader"
    assert readiness["uses_repo_local_corpus"] is True
    assert readiness["repo_relative_corpus_path"] == "backend/src/services/legal_corpus_loader.py"
    assert readiness["available_chunk_count"] == 42
    assert readiness["smoke_question_count"] == 10
    assert readiness["all_questions"]["required_chunk_count"] == 60
    assert readiness["all_questions"]["available_required_chunk_count"] == 30
    assert readiness["all_questions"]["missing_chunk_count"] == 30
    assert readiness["all_questions"]["coverage_ratio"] == 0.5
    assert readiness["non_smoke_questions"]["question_count"] == 40
    assert readiness["non_smoke_questions"]["required_chunk_count"] == 47
    assert readiness["non_smoke_questions"]["available_required_chunk_count"] == 20
    assert readiness["non_smoke_questions"]["missing_chunk_count"] == 27
    assert readiness["commercial_full50_ready"] is False
    assert "corpus_missing_required_chunks:30" in readiness["blockers"]
    assert "corpus_missing_non_smoke_required_chunks:27" in readiness["blockers"]
    assert any(
        "legal_corpus_loader.py::get_all_legal_corpus()" in step for step in report["next_steps"]
    )
