"""在临时 PostgreSQL 数据库上执行 Alembic 全量迁移 smoke。

用途：
- 验证全新数据库能否从 <base> 迁移到 head
- 避免只在已存在表的开发库上验证迁移链
"""

from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.config import settings


def build_db_url(database_name: str) -> str:
    parsed = urlparse(settings.DATABASE_URL)
    return urlunparse(parsed._replace(path=f"/{database_name}"))


def maintenance_db_url() -> str:
    parsed = urlparse(settings.DATABASE_URL)
    maintenance_db = "postgres"
    return urlunparse(parsed._replace(path=f"/{maintenance_db}"))


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def print_result(title: str, result: subprocess.CompletedProcess[str]) -> None:
    print(f"\n== {title} ==")
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())


def main(keep_db: bool) -> int:
    if not settings.DATABASE_URL.startswith("postgresql://"):
        print("仅支持 PostgreSQL DATABASE_URL。")
        return 2

    tmp_db = f"legal_agent_migration_smoke_{secrets.token_hex(4)}"
    db_url = build_db_url(tmp_db)
    admin_url = maintenance_db_url()

    print(f"临时数据库: {tmp_db}")

    create_result = run([
        "psql",
        admin_url,
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        f'CREATE DATABASE "{tmp_db}"',
    ])
    print_result("CREATE DATABASE", create_result)
    if create_result.returncode != 0:
        return create_result.returncode

    env = os.environ.copy()
    env["DATABASE_URL"] = db_url

    upgrade_result = run(["./.venv/bin/alembic", "upgrade", "head"], env=env)
    print_result("ALEMBIC UPGRADE", upgrade_result)

    current_result = run(["./.venv/bin/alembic", "current"], env=env)
    print_result("ALEMBIC CURRENT", current_result)

    exit_code = 0 if upgrade_result.returncode == 0 and current_result.returncode == 0 else 1

    if keep_db:
        print(f"\n保留临时数据库: {tmp_db}")
        print(f"DATABASE_URL={db_url}")
        return exit_code

    drop_result = run([
        "psql",
        admin_url,
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        f'DROP DATABASE IF EXISTS "{tmp_db}" WITH (FORCE)',
    ])
    print_result("DROP DATABASE", drop_result)
    if drop_result.returncode != 0 and exit_code == 0:
        exit_code = drop_result.returncode

    return exit_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="在临时数据库上执行 Alembic 全量迁移 smoke")
    parser.add_argument("--keep-db", action="store_true", help="保留临时数据库，便于排查")
    args = parser.parse_args()
    raise SystemExit(main(keep_db=args.keep_db))
