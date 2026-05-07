#!/usr/bin/env python3
"""Audit exported RAG sources for clickable citation targets."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def load_sources(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    sources = data.get("sources", data) if isinstance(data, dict) else data
    if not isinstance(sources, list):
        raise ValueError("Citation source input must be a list or {'sources': [...]}")
    return [source for source in sources if isinstance(source, dict)]


def load_documents(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    documents = data.get("documents", data) if isinstance(data, dict) else data
    if not isinstance(documents, list):
        raise ValueError("Document input must be a list or {'documents': [...]}")
    return {
        str(document.get("id")): document
        for document in documents
        if isinstance(document, dict) and document.get("id")
    }


def has_click_target(source: dict[str, Any]) -> bool:
    source_url = str(source.get("source_url") or "").strip()
    doc_id = str(source.get("doc_id") or "").strip()
    chunk_id = str(source.get("chunk_id") or source.get("id") or "").strip()
    return bool(source_url or (doc_id and chunk_id))


def _chunk_exists(document: dict[str, Any], chunk_id: str) -> bool:
    chunks = document.get("chunks")
    if not isinstance(chunks, list):
        return True
    return any(str(chunk.get("id") or "") == chunk_id for chunk in chunks if isinstance(chunk, dict))


def _anchor_exists(source: dict[str, Any], document: dict[str, Any] | None) -> bool | None:
    anchor = str(source.get("anchor_text") or "").strip()
    if not anchor or document is None:
        return None
    content = str(document.get("content") or "")
    if anchor in content:
        return True
    chunks = document.get("chunks")
    if isinstance(chunks, list):
        return any(anchor in str(chunk.get("content") or "") for chunk in chunks if isinstance(chunk, dict))
    return False


def audit_sources(
    sources: list[dict[str, Any]],
    documents: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    document_map = documents or {}
    validate_documents = bool(document_map)
    rows = []
    broken = 0
    missing_targets = 0
    missing_anchors = 0
    for index, source in enumerate(sources, start=1):
        clickable = has_click_target(source)
        doc_id = str(source.get("doc_id") or "").strip()
        chunk_id = str(source.get("chunk_id") or source.get("id") or "").strip()
        document = document_map.get(doc_id)
        document_ok = True
        chunk_ok = True
        anchor_ok = _anchor_exists(source, document)

        if validate_documents and doc_id:
            document_ok = document is not None
            chunk_ok = bool(document and _chunk_exists(document, chunk_id))
        if anchor_ok is False:
            missing_anchors += 1
        if not document_ok or not chunk_ok:
            missing_targets += 1

        ok = clickable and document_ok and chunk_ok and anchor_ok is not False
        if not ok:
            broken += 1
        rows.append(
            {
                "index": index,
                "title": source.get("title") or source.get("source") or f"source-{index}",
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "source_url": source.get("source_url") or "",
                "clickable": clickable,
                "document_ok": document_ok,
                "chunk_ok": chunk_ok,
                "anchor_ok": anchor_ok,
                "ok": ok,
            }
        )
    total = len(rows)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total": total,
        "clickable": total - broken,
        "broken": broken,
        "broken_rate": broken / total if total else 0.0,
        "missing_targets": missing_targets,
        "missing_anchors": missing_anchors,
        "validate_documents": validate_documents,
        "rows": rows,
    }


def render_markdown(report: dict[str, Any], source_path: Path) -> str:
    lines = [
        "# Citation Link Health Report",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Source export: `{source_path}`",
        (
            "- Mode: offline source-shape audit"
            + (" + exported document/chunk existence audit." if report["validate_documents"] else ".")
        ),
        f"- Total sources: {report['total']}",
        f"- Clickable sources: {report['clickable']}",
        f"- Broken sources: {report['broken']}",
        f"- Broken rate: {report['broken_rate']:.2%}",
        f"- Missing document/chunk targets: {report['missing_targets']}",
        f"- Missing anchors: {report['missing_anchors']}",
        "",
        "| # | Status | Title | doc_id | chunk_id | target | anchor |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in report["rows"]:
        status = "OK" if row["ok"] else "BROKEN"
        if row["anchor_ok"] is None:
            anchor = "n/a"
        else:
            anchor = "OK" if row["anchor_ok"] else "MISSING"
        lines.append(
            "| {index} | {status} | {title} | `{doc_id}` | `{chunk_id}` | `{target}` | {anchor} |".format(
                index=row["index"],
                status=status,
                title=str(row["title"]).replace("|", "\\|"),
                doc_id=row["doc_id"],
                chunk_id=row["chunk_id"],
                target=row["source_url"] or "doc+chunk",
                anchor=anchor,
            )
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True, help="Exported RAG sources JSON")
    parser.add_argument("--documents", type=Path, help="Optional exported documents/chunks JSON")
    parser.add_argument("--out", type=Path, required=True, help="Markdown report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = audit_sources(load_sources(args.sources), load_documents(args.documents))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_markdown(report, args.sources), encoding="utf-8")
    print(
        "Citation links "
        f"total={report['total']} clickable={report['clickable']} "
        f"broken_rate={report['broken_rate']:.2%} "
        f"missing_targets={report['missing_targets']} missing_anchors={report['missing_anchors']}"
    )
    return 0 if report["broken"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
