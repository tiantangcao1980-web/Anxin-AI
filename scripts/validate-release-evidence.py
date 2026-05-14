#!/usr/bin/env python3
"""Validate release evidence status and required-scope closure.

The commercial gate treats evidence files as release blockers. This helper
prevents a weak handoff where a file is marked ``Status: complete`` while its
required-scope table still contains unresolved rows such as ``pending`` or
``TBD``.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


FIELD_RE = re.compile(r"^\s*(?P<key>[A-Za-z][A-Za-z ]*)\s*:\s*(?P<value>.*?)\s*$")
TABLE_SEPARATOR_RE = re.compile(r"^\|[|:\-\s]+\|$")
ARTIFACT_PATH_RE = re.compile(r"docs/release/evidence/artifacts/[A-Za-z0-9._/@+=:-]+")
REQUIRED_COMPLETE_FIELDS = ("Owner", "Environment", "Date range")
UNRESOLVED_FIELD_VALUES = {"", "tbd", "pending", "unknown", "n/a"}
UNRESOLVED_PATTERNS = (
    re.compile(r"\|\s*pending\s*\|", re.IGNORECASE),
    re.compile(r"\|\s*tbd\s*\|", re.IGNORECASE),
    re.compile(r"evidence pending", re.IGNORECASE),
    re.compile(r"verification pending", re.IGNORECASE),
    re.compile(r"packaged[^|]*pending", re.IGNORECASE),
    re.compile(r"device[^|]*pending", re.IGNORECASE),
    re.compile(r"final notes pending", re.IGNORECASE),
    re.compile(r"release_ready=false", re.IGNORECASE),
    re.compile(r"not run", re.IGNORECASE),
    re.compile(r"not yet", re.IGNORECASE),
    re.compile(r"仍未"),
    re.compile(r"缺"),
    re.compile(r"\|\s*(pass|complete|code-level pass|code-level complete)\s*\|\s*\|$", re.IGNORECASE),
)
PROSE_CONFLICT_PATTERNS = (
    re.compile(r"remains\s+`?status:\s*pending`?", re.IGNORECASE),
    re.compile(r"commercial baseline remains pending", re.IGNORECASE),
    re.compile(r"仍为\s*pending", re.IGNORECASE),
    re.compile(r"仍未完成"),
    re.compile(r"不能标记"),
    re.compile(r"cannot mark", re.IGNORECASE),
    re.compile(r"not commercially ready", re.IGNORECASE),
)


@dataclass(frozen=True)
class EvidenceItem:
    path: Path
    label: str


@dataclass(frozen=True)
class ValidationResult:
    failures: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.failures


def parse_evidence_item(raw: str) -> EvidenceItem:
    path_text, separator, label = raw.partition("|")
    path = Path(path_text)
    return EvidenceItem(path=path, label=label if separator else path_text)


def read_field(text: str, field_name: str) -> str | None:
    for line in text.splitlines():
        match = FIELD_RE.match(line)
        if match and match.group("key").strip().lower() == field_name.lower():
            return match.group("value").strip()
    return None


def read_status(text: str) -> str | None:
    value = read_field(text, "Status")
    return value.lower() if value is not None else None


def unresolved_complete_metadata(text: str) -> list[str]:
    missing: list[str] = []
    for field_name in REQUIRED_COMPLETE_FIELDS:
        value = read_field(text, field_name)
        if value is None or value.strip().lower() in UNRESOLVED_FIELD_VALUES:
            missing.append(f"{field_name}: {value or 'missing'}")
    return missing


def iter_required_scope_rows(text: str) -> list[str]:
    rows: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if TABLE_SEPARATOR_RE.match(stripped):
            continue
        rows.append(stripped)
    return rows


def unresolved_required_scope_rows(text: str, *, limit: int = 20) -> list[str]:
    unresolved: list[str] = []
    for row in iter_required_scope_rows(text):
        if any(pattern.search(row) for pattern in UNRESOLVED_PATTERNS):
            unresolved.append(row)
            if len(unresolved) >= limit:
                break
    return unresolved


def unresolved_complete_prose_lines(text: str, *, limit: int = 20) -> list[str]:
    unresolved: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("|"):
            continue
        if any(pattern.search(stripped) for pattern in PROSE_CONFLICT_PATTERNS):
            unresolved.append(stripped)
            if len(unresolved) >= limit:
                break
    return unresolved


def missing_artifact_references(text: str, *, limit: int = 20) -> list[str]:
    missing: list[str] = []
    for match in ARTIFACT_PATH_RE.finditer(text):
        artifact_path = Path(match.group(0).rstrip(".,;:)]}"))
        if not artifact_path.is_file() or artifact_path.stat().st_size == 0:
            missing.append(str(artifact_path))
            if len(missing) >= limit:
                break
    return missing


def validate_item(item: EvidenceItem) -> ValidationResult:
    if not item.path.is_file() or item.path.stat().st_size == 0:
        return ValidationResult(
            failures=(f"missing release evidence: {item.path}",),
            warnings=(),
        )

    text = item.path.read_text(encoding="utf-8")
    status_value = read_status(text)
    # Phase F (2026-05-14): "deferred" status 表示**有意识降级到商业化阶段**,
    # 不阻断当前 PMF 验证. 必须在 evidence 文件中显式声明 Deferred-Reason +
    # Deferred-Until 才视为有效降级 (防止滥用).
    if status_value == "deferred":
        deferred_reason = re.search(r"^Deferred-Reason:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
        deferred_until = re.search(r"^Deferred-Until:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
        if not deferred_reason or not deferred_until:
            return ValidationResult(
                failures=(
                    f"release evidence is marked deferred but missing "
                    f"Deferred-Reason / Deferred-Until ({item.label}): {item.path}",
                ),
                warnings=(),
            )
        # Deferred 视为合法 — 当前 gate 跳过, 仅 warning 提示
        return ValidationResult(
            failures=(),
            warnings=(
                f"release evidence deferred ({item.label}): "
                f"{deferred_reason.group(1).strip()[:80]} (until: {deferred_until.group(1).strip()[:30]})",
            ),
        )
    if status_value != "complete":
        return ValidationResult(
            failures=(
                "release evidence is not complete "
                f"({item.label}): {item.path} has Status: {status_value or 'missing'}",
            ),
            warnings=(),
        )

    unresolved_metadata = unresolved_complete_metadata(text)
    if unresolved_metadata:
        return ValidationResult(
            failures=(
                "release evidence is marked complete but has unresolved metadata "
                f"({item.label}): {item.path}",
            ),
            warnings=tuple(f"{item.path}: {metadata}" for metadata in unresolved_metadata),
        )

    unresolved_prose = unresolved_complete_prose_lines(text)
    if unresolved_prose:
        return ValidationResult(
            failures=(
                "release evidence is marked complete but still has conflicting "
                f"pending/not-ready prose ({item.label}): {item.path}",
            ),
            warnings=tuple(f"{item.path}: {line}" for line in unresolved_prose),
        )

    unresolved_rows = unresolved_required_scope_rows(text)
    if unresolved_rows:
        return ValidationResult(
            failures=(
                "release evidence is marked complete but still has unresolved "
                f"required-scope rows ({item.label}): {item.path}",
            ),
            warnings=tuple(f"{item.path}: {row}" for row in unresolved_rows),
        )

    missing_artifacts = missing_artifact_references(text)
    if missing_artifacts:
        return ValidationResult(
            failures=(
                "release evidence is marked complete but references missing "
                f"artifact files ({item.label}): {item.path}",
            ),
            warnings=tuple(
                f"{item.path}: missing artifact {artifact}" for artifact in missing_artifacts
            ),
        )

    return ValidationResult(failures=(), warnings=())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "evidence",
        nargs="+",
        help="Evidence path, optionally suffixed as path|label",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable validation summary",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    failures: list[str] = []
    warnings: list[str] = []
    for raw in args.evidence:
        result = validate_item(parse_evidence_item(raw))
        failures.extend(result.failures)
        warnings.extend(result.warnings)

    if args.json:
        print(
            json.dumps(
                {
                    "ok": not failures,
                    "failures": failures,
                    "warnings": warnings,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if failures else 0

    for warning in warnings:
        print(f"WARN: {warning}")
    for failure in failures:
        print(f"FAIL: {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
