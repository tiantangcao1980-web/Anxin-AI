#!/usr/bin/env python3
"""Inventory dirty worktree entries before commercial release handoff."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


DELIVERY_PREFIXES = (
    ".env.example",
    ".gitignore",
    ".gitnexusignore",
    "backend/.env.example",
    "backend/alembic/",
    "backend/pyproject.toml",
    "backend/src/",
    "backend/tests/",
    "desktop/Cargo.toml",
    "desktop/Entitlements.plist",
    "desktop/capabilities/",
    "desktop/gen/",
    "desktop/migrations/",
    "desktop/src/",
    "desktop/tauri.conf.json",
    "docker-compose.dev.yml",
    "docker-compose.yml",
    "docs/architecture/",
    "docs/DEPLOYMENT_DESKTOP.md",
    "docs/audit/",
    "docs/design/",
    "docs/desktop/",
    "docs/mobile/",
    "docs/openspec/",
    "docs/release/",
    "docs/wiki/",
    "eval/",
    "frontend/e2e/",
    "frontend/package-lock.json",
    "frontend/package.json",
    "frontend/src/",
    "frontend/vite.config.ts",
    "mini-program/",
    "mobile/",
    "scripts/",
)
GENERATED_PREFIXES = (
    ".gitnexus/",
    ".gitnexus.",
    ".mypy_cache/",
    ".omx/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".super-skill/",
    ".superpowers/",
    "backend/.mypy_cache/",
    "backend/.pytest_cache/",
    "backend/.ruff_cache/",
    "desktop/target/",
    "frontend/dist/",
    "frontend/node_modules/",
)
LOCAL_SECRET_PATHS = {
    ".env",
    ".env.local",
    "backend/.env",
    "backend/.env.local",
    "frontend/.env",
    "frontend/.env.local",
    "frontend/.env.tauri",
    "livekit.yaml",
}


@dataclass(frozen=True)
class StatusEntry:
    status: str
    path: str
    tracked: bool


def run_git_status(repo_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def normalize_status_path(raw_path: str) -> str:
    path = raw_path.strip()
    if " -> " in path:
        path = path.rsplit(" -> ", 1)[1]
    return path


def parse_status_line(line: str) -> StatusEntry:
    status = line[:2]
    path = normalize_status_path(line[3:] if len(line) > 3 else "")
    return StatusEntry(status=status, path=path, tracked=status != "??")


def has_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def classify(path: str) -> str:
    if path in LOCAL_SECRET_PATHS:
        return "local_secret"
    if has_prefix(path, GENERATED_PREFIXES):
        return "generated_or_runtime"
    if has_prefix(path, DELIVERY_PREFIXES):
        return "release_delivery"
    return "unknown"


def build_inventory(entries: list[StatusEntry]) -> dict:
    categories: dict[str, list[str]] = {
        "release_delivery": [],
        "generated_or_runtime": [],
        "local_secret": [],
        "unknown": [],
    }
    for entry in entries:
        categories[classify(entry.path)].append(entry.path)

    return {
        "tracked_changes": sum(1 for entry in entries if entry.tracked),
        "untracked_files": sum(1 for entry in entries if not entry.tracked),
        "categories": {key: sorted(value) for key, value in categories.items()},
        "category_counts": {key: len(value) for key, value in categories.items()},
    }


def load_status_lines(args: argparse.Namespace) -> list[str]:
    if args.status_file:
        return [
            line
            for line in Path(args.status_file).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    return run_git_status(Path(args.repo_root))


def print_human(inventory: dict) -> None:
    print(
        "Release worktree inventory: "
        f"tracked_changes={inventory['tracked_changes']} "
        f"untracked_files={inventory['untracked_files']}"
    )
    for category, paths in inventory["categories"].items():
        print(f"\n[{category}] {len(paths)}")
        for path in paths[:50]:
            print(f"  - {path}")
        if len(paths) > 50:
            print(f"  ... {len(paths) - 50} more")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root for git status")
    parser.add_argument("--status-file", help="Read git-status short lines from a fixture file")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument(
        "--fail-on-unknown",
        action="store_true",
        help="Exit 1 when any dirty path falls outside known release categories",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    entries = [parse_status_line(line) for line in load_status_lines(args)]
    inventory = build_inventory(entries)
    if args.json:
        print(json.dumps(inventory, ensure_ascii=False, indent=2))
    else:
        print_human(inventory)
    return 1 if args.fail_on_unknown and inventory["categories"]["unknown"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
