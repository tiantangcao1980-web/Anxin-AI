import subprocess
import sys
from pathlib import Path


def test_citation_link_audit_smoke_generates_zero_broken_report(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    output = tmp_path / "citation-link-health-report.md"

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "audit_citation_links.py"),
            "--sources",
            str(repo_root / "eval" / "citation_sources_smoke.json"),
            "--documents",
            str(repo_root / "eval" / "citation_documents_smoke.json"),
            "--out",
            str(output),
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )

    report = output.read_text(encoding="utf-8")

    assert "broken_rate=0.00%" in result.stdout
    assert "missing_targets=0" in result.stdout
    assert "missing_anchors=0" in result.stdout
    assert "Broken sources: 0" in report
    assert "| 1 | OK |" in report


def test_citation_link_audit_fails_on_missing_chunk(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    sources = tmp_path / "sources.json"
    documents = tmp_path / "documents.json"
    output = tmp_path / "citation-link-health-report.md"
    sources.write_text(
        '{"sources":[{"title":"坏引用","doc_id":"doc-1","chunk_id":"missing","anchor_text":"合同成立"}]}',
        encoding="utf-8",
    )
    documents.write_text(
        '{"documents":[{"id":"doc-1","content":"合同成立","chunks":[{"id":"chunk-1","content":"合同成立"}]}]}',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "audit_citation_links.py"),
            "--sources",
            str(sources),
            "--documents",
            str(documents),
            "--out",
            str(output),
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "missing_targets=1" in result.stdout
    assert "BROKEN" in output.read_text(encoding="utf-8")
