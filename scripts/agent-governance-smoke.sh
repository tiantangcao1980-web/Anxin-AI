#!/usr/bin/env bash
# Code-level enterprise agent governance smoke checks.
#
# This proves the local governance baseline is runnable: capability policy,
# route-token gates, approvals, SkillGovernance, memory governance, remote-control
# safety, desktop host safe-probe handling, and the minimal frontend governance
# workspace. It is not final commercial runtime evidence.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/agent-governance-smoke.sh [--out path]

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

run_step() {
  local label="$1"
  shift
  echo ">>> ${label}"
  "$@"
}

run_step "agent governance docs scan" bash -lc "cd '$PROJECT_ROOT' && test -s docs/release/evidence/agent-governance-smoke.md && rg -n 'AgentManager|CapabilityRoute|Human-in-the-loop|SkillEvolutionProposal|企业智能体治理' docs/openspec docs/audit/_tasks docs/references >/dev/null"

run_step "agent capability policy tests" bash -lc "cd '$PROJECT_ROOT/backend' && ./.venv/bin/pytest -q tests/test_harness.py -k 'PolicyEngine or AgentMcpToolPolicy'"

run_step "backend governance regression tests" bash -lc "cd '$PROJECT_ROOT/backend' && ./.venv/bin/pytest -q \
  tests/test_agent_governance_policy.py \
  tests/test_capability_policy_engine.py \
  tests/test_capability_routes.py \
  tests/test_agent_governance_models.py \
  tests/test_agent_governance_service.py \
  tests/test_agent_approval_service.py \
  tests/test_agent_approval_api.py \
  tests/test_memory_governance.py \
  tests/test_mcp_route_governance.py \
  tests/test_cli_route.py \
  tests/test_llm_route_governance.py \
  tests/test_crawler_compliance.py \
  tests/test_remote_control_fail_closed.py \
  tests/test_skill_evolution_service.py \
  tests/test_skill_service.py \
  tests/test_skill_governance_models.py \
  tests/test_skill_governance_service.py \
  tests/test_skill_governance_api.py"

run_step "approval authorization guard tests" bash -lc "cd '$PROJECT_ROOT/backend' && ./.venv/bin/pytest -q tests/test_business_authorization_guards.py -k 'approval or template'"

run_step "MCP connection config policy tests" bash -lc "cd '$PROJECT_ROOT/backend' && ./.venv/bin/pytest -q tests/test_config_commercial_guards.py -k mcp"

run_step "desktop remote-control host tests" bash -lc "cd '$PROJECT_ROOT/desktop' && cargo test remote_control"

run_step "frontend agent governance workspace e2e" bash -lc "cd '$PROJECT_ROOT/frontend' && npx playwright test e2e/agent-approval-workspace.spec.ts --project=chromium --project=mobile"

if [ -n "$OUT_PATH" ]; then
  python3 - "$OUT_PATH" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

out_path = Path(sys.argv[1])
checks = {
    "governance_docs_scan": "passed",
    "agent_capability_policy": "passed",
    "backend_governance_regressions": "passed",
    "approval_authorization_guard": "passed",
    "mcp_connection_config_policy": "passed",
    "desktop_remote_control_host": "passed",
    "frontend_agent_workspace_e2e": "passed",
}
report = {
    "generated_at": datetime.now(UTC).isoformat(),
    "mode": "agent_governance_code_smoke",
    "status": "passed",
    "release_evidence_complete": False,
    "runtime_evidence_complete": False,
    "checks": checks,
    "scope": {
        "enterprise_agent_governance": "code_level",
        "backend": "policy/routes/approvals/skills/memory/remote-control",
        "desktop": "remote-control safe-probe host tests",
        "frontend": "agent governance workspace e2e",
    },
    "pending_runtime_evidence": [
        "approved_connector_rehearsal",
        "real_cross_process_revocation",
        "long_task_artifact_workflow",
        "pause_takeover_terminate_runtime",
        "signed_packaged_runtime_outbound_evidence",
        "cross_device_recovery",
    ],
    "completion_note": (
        "Code-level enterprise agent governance evidence only. Keep "
        "agent-governance-smoke.md Status: pending until approved connector, "
        "cross-process revocation, real runtime controls, signed packaged runtime, "
        "and cross-device recovery evidence are attached."
    ),
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote agent governance smoke artifact: {out_path}")
PY
fi

echo
echo "agent governance code-level smoke complete."
