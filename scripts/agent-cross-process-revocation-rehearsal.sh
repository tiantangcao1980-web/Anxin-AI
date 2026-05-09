#!/usr/bin/env bash
# Local cross-process revocation rehearsal for enterprise Agent governance.
#
# This proves route-token revocation propagates through the database across
# independent issuer, worker, and admin service sessions. It is not signed
# packaged runtime or live provider evidence.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/agent-cross-process-revocation-rehearsal.sh [--out path]

Options:
  --out path   Write a structured JSON artifact.
  -h, --help   Show this help.
EOF
}

OUT_PATH=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --out)
      OUT_PATH="${2:-}"
      if [ -z "$OUT_PATH" ]; then
        usage
        echo "ERROR: --out requires a path" >&2
        exit 2
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      echo "ERROR: unknown option: $1" >&2
      exit 2
      ;;
  esac
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo ">>> cross-process route-token revocation rehearsal tests"
bash -lc "cd '$PROJECT_ROOT/backend' && ./.venv/bin/pytest -q tests/test_agent_governance_service.py -k cross_process"

if [ -n "$OUT_PATH" ]; then
  python3 - "$OUT_PATH" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

out_path = Path(sys.argv[1])
report = {
    "generated_at": datetime.now(UTC).isoformat(),
    "mode": "agent_cross_process_revocation_rehearsal",
    "status": "passed",
    "release_evidence_complete": False,
    "runtime_evidence_complete": False,
    "database_mode": "sqlite_file_local_rehearsal",
    "checks": {
        "independent_issuer_worker_admin_sessions": "passed",
        "worker_session_cache_refresh": "passed",
        "admin_revokes_active_route_and_lease": "passed",
        "next_worker_call_fail_closed": "passed",
        "audit_trail": "passed",
        "raw_token_hash_only": "passed",
    },
    "scope": {
        "route_key": "approved-materials",
        "route_scope": "mcp:call",
        "consumer": "legal-advisor-worker",
        "evidence_level": "local_cross_process_rehearsal",
    },
    "pending_external_evidence": [
        "signed_packaged_runtime_outbound_evidence",
        "commercial_cross_process_revocation_runtime_evidence",
        "real_approved_connector_provider_runtime",
        "production_database_observability_logs",
    ],
    "completion_note": (
        "Supporting local cross-process route-token revocation rehearsal only; "
        "release evidence remains pending until signed packaged runtime, real "
        "approved connector provider execution, production observability logs, "
        "and commercial multi-process revocation evidence are attached."
    ),
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote cross-process revocation rehearsal artifact: {out_path}")
PY
fi

echo
echo "cross-process revocation local rehearsal complete."
