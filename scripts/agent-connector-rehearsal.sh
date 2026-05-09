#!/usr/bin/env bash
# Local approved connector runtime rehearsal for enterprise Agent governance.
#
# This proves the governed MCP connector execution path with mock provider data:
# route-token issuance, connector-bound tool call, revocation, fail-closed retry,
# and redacted evidence artifact shape. It is not live provider evidence.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/agent-connector-rehearsal.sh [--out path]

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

echo ">>> approved connector local rehearsal tests"
bash -lc "cd '$PROJECT_ROOT/backend' && ./.venv/bin/pytest -q tests/test_agent_connector_runtime_rehearsal.py"

if [ -n "$OUT_PATH" ]; then
  python3 - "$OUT_PATH" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

out_path = Path(sys.argv[1])
report = {
    "generated_at": datetime.now(UTC).isoformat(),
    "mode": "agent_connector_local_rehearsal",
    "status": "passed",
    "release_evidence_complete": False,
    "runtime_evidence_complete": False,
    "provider_mode": "local_mock_mcp",
    "checks": {
        "route_token_issued": "passed",
        "connector_bound_tool_call": "passed",
        "route_revocation": "passed",
        "revoked_token_fail_closed": "passed",
        "audit_trail": "passed",
        "raw_secret_redaction": "passed",
    },
    "scope": {
        "connector": "approved-materials",
        "route_scope": "mcp:call",
        "consumer": "legal_advisor",
        "evidence_level": "local_mock_runtime_rehearsal",
    },
    "pending_external_evidence": [
        "real_provider_credentials",
        "provider_dashboard_logs",
        "signed_packaged_runtime_outbound_evidence",
        "commercial_cross_process_revocation_runtime_evidence",
    ],
    "completion_note": (
        "Supporting local mock runtime rehearsal only; release evidence remains "
        "pending until a real approved connector runs with provider credentials, "
        "redacted dashboard/log artifacts, signed packaged runtime evidence, and "
        "commercial multi-process revocation proof."
    ),
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote approved connector rehearsal artifact: {out_path}")
PY
fi

echo
echo "approved connector local rehearsal complete."
