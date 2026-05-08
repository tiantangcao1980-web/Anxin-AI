#!/usr/bin/env bash
# Commercial readiness gate.
#
# This is intentionally stricter than "tests passed": it checks whether the
# release evidence needed for a commercial handoff exists. The current project
# is expected to fail this gate until external sandbox, runtime, device, and
# quality-baseline evidence is supplied.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/commercial-readiness-gate.sh [options]

Options:
  --quick              Check evidence files and local GitNexus metadata (default).
  --with-local-tests   Also run local code-level smoke commands.
  -h, --help           Show this help.

Expected result:
  Exit 0 only when the repo has all release evidence required by
  docs/release/completion-audit.md and docs/release/commercial-delivery-readiness.md.
EOF
}

RUN_LOCAL_TESTS=0

for arg in "$@"; do
  case "$arg" in
    --quick)
      RUN_LOCAL_TESTS=0
      ;;
    --with-local-tests)
      RUN_LOCAL_TESTS=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      echo "ERROR: unknown option: $arg" >&2
      exit 2
      ;;
  esac
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

failures=()
warnings=()

add_failure() {
  failures+=("$*")
}

add_warning() {
  warnings+=("$*")
}

require_file() {
  local path="$1"
  if [ ! -s "$path" ]; then
    add_failure "missing or empty required artifact: $path"
  fi
}

require_command() {
  local label="$1"
  shift
  echo ">>> $label"
  if ! "$@"; then
    add_failure "command failed: $label"
  fi
}

read_meta_field() {
  local expr="$1"
  node -e "const fs=require('fs'); const m=JSON.parse(fs.readFileSync('.gitnexus/meta.json','utf8')); const v=${expr}; console.log(v ?? '')"
}

coerce_nonnegative_int() {
  local value="$1"
  case "$value" in
    ''|*[!0-9]*)
      printf '0'
      ;;
    *)
      printf '%s' "$value"
      ;;
  esac
}

count_lines() {
  awk 'NF { n++ } END { print n + 0 }'
}

extract_cypher_count() {
  node -e "
let s = '';
process.stdin.on('data', (chunk) => { s += chunk; });
process.stdin.on('end', () => {
  const jsonMatch = s.match(/\"cnt\"\\s*:\\s*(\\d+)/);
  const markdownMatch = s.match(/\\|\\s*(\\d+)\\s*\\|/g)?.pop()?.match(/\\d+/);
  process.stdout.write(jsonMatch?.[1] ?? markdownMatch?.[0] ?? '');
});
"
}

echo ">>> Checking release artifacts"

required_artifacts=(
  ".gitnexusignore"
  ".env.example"
  "scripts/gitnexus-index.sh"
  "scripts/static-quality-baseline.sh"
  "scripts/mypy-baseline-check.sh"
  "scripts/sandbox-evidence-runner.py"
  "scripts/mobile-device-smoke.sh"
  "scripts/desktop-installed-profile-smoke.sh"
  "scripts/desktop-release-package.sh"
  "scripts/desktop-release-preflight.sh"
  "scripts/desktop-network-surface-gate.sh"
  "scripts/desktop-sqlite-security-gate.sh"
  "scripts/release-evidence-secret-scan.sh"
  "scripts/release-worktree-inventory.py"
  "scripts/validate-release-evidence.py"
  "scripts/validate-commercial-delivery-checklist.cjs"
  "scripts/validate-commercial-delivery-lanes.cjs"
  "scripts/validate-release-artifacts.py"
  "eval/rag_live_qdrant_full50.py"
  "docs/audit/00-platform/06-gitnexus-knowledge-graph.md"
  "docs/audit/SUMMARY.md"
  "docs/openspec/01-commercial-delivery-spec.md"
  "docs/openspec/02-commercial-delivery-test-spec.md"
  "docs/release/completion-audit.md"
  "docs/release/commercial-delivery-checklist.json"
  "docs/release/commercial-delivery-lanes.json"
  "docs/release/commercial-delivery-readiness.md"
  "docs/release/evidence-collection-runbook.md"
  "docs/release/external-inputs-checklist.md"
  "docs/release/test-evidence.md"
  "docs/release/rollback-runbook.md"
  "docs/release/security-and-privacy-checklist.md"
)

for artifact in "${required_artifacts[@]}"; do
  require_file "$artifact"
done

if ! node scripts/validate-commercial-delivery-checklist.cjs; then
  add_failure "commercial delivery checklist JSON is invalid or references missing evidence files"
fi

if ! node scripts/validate-commercial-delivery-lanes.cjs; then
  add_failure "commercial delivery lanes JSON is invalid or references missing evidence files"
fi

echo ">>> Checking evidence configuration templates"
sandbox_required_env=(
  "PAYMENT_NOTIFY_BASE_URL"
  "WECHAT_PAY_APP_ID"
  "WECHAT_PAY_MCH_ID"
  "WECHAT_PAY_MERCHANT_SERIAL_NO"
  "WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH"
  "WECHAT_PAY_MERCHANT_PRIVATE_KEY"
  "WECHAT_PAY_PLATFORM_SERIAL"
  "WECHAT_PAY_PLATFORM_PUBLIC_KEY_PATH"
  "WECHAT_PAY_PLATFORM_PUBLIC_KEY"
  "WECHAT_PAY_API_V3_KEY"
  "WECHAT_PAY_OFFICIAL_WEBHOOK_ENABLED"
  "ALIPAY_APP_ID"
  "ALIPAY_PRIVATE_KEY_PATH"
  "ALIPAY_PRIVATE_KEY"
  "ALIPAY_PUBLIC_KEY_PATH"
  "ALIPAY_PUBLIC_KEY"
  "ALIPAY_GATEWAY_URL"
  "ALIPAY_OFFICIAL_WEBHOOK_ENABLED"
  "ESIGN_BAO_APP_ID"
  "ESIGN_BAO_APP_SECRET"
  "ESIGN_BAO_API_URL"
  "ESIGN_OFFICIAL_WEBHOOK_ENABLED"
  "FADADA_APP_ID"
  "FADADA_APP_SECRET"
  "FADADA_API_URL"
)

capability_governance_env=(
  "MCP_STANDALONE_ENABLED"
  "MCP_STDIO_ENABLED"
  "MCP_STDIO_ALLOWED_COMMANDS"
  "MCP_STDIO_ALLOWED_COMMAND_LINES"
  "MCP_STDIO_ALLOWED_ENV_KEYS"
  "MCP_SSE_ALLOWED_HOSTS"
  "MCP_SSE_ALLOWED_SCHEMES"
  "MCP_TOOL_ROUTE_TOKEN_REQUIRED"
  "CLI_ROUTE_TOKEN_REQUIRED"
)

for template in ".env.example" "backend/.env.example"; do
  for env_name in "${sandbox_required_env[@]}"; do
    if ! rg -q "^${env_name}=" "$template"; then
      add_failure "sandbox evidence config template is missing ${env_name}: ${template}"
    fi
  done
  for env_name in "${capability_governance_env[@]}"; do
    if ! rg -q "^${env_name}=" "$template"; then
      add_failure "capability governance config template is missing ${env_name}: ${template}"
    fi
  done
done

echo ">>> Checking GitNexus metadata"
tracked_changes="$(git status --short --untracked-files=no | count_lines)"
untracked_changes="$(git ls-files --others --exclude-standard | count_lines)"
if [ "$tracked_changes" -gt 0 ] || [ "$untracked_changes" -gt 0 ]; then
  add_failure "working tree is not clean: tracked_changes=${tracked_changes}, untracked_files=${untracked_changes}; GitNexus metadata is commit-scoped, so release artifacts must be committed and GitNexus must be rerun before Go"
  if inventory_output="$(python3 scripts/release-worktree-inventory.py --json 2>&1)"; then
    inventory_counts="$(printf '%s\n' "$inventory_output" | node -e "let s=''; process.stdin.on('data', c => s += c); process.stdin.on('end', () => { const p = JSON.parse(s); const c = p.category_counts ?? {}; process.stdout.write([c.local_secret ?? 0, c.generated_or_runtime ?? 0, c.unknown ?? 0].join(' ')); });")"
    read -r local_secret_count generated_count unknown_count <<< "$inventory_counts"
    [ "$local_secret_count" -eq 0 ] || add_failure "dirty worktree contains ${local_secret_count} local secret paths; remove them from release staging"
    [ "$generated_count" -eq 0 ] || add_warning "dirty worktree contains ${generated_count} generated/runtime paths; verify before staging"
    [ "$unknown_count" -eq 0 ] || add_warning "dirty worktree contains ${unknown_count} unknown paths; run python3 scripts/release-worktree-inventory.py before staging"
  else
    add_warning "dirty worktree inventory failed: $inventory_output"
  fi
fi

if [ ! -s .gitnexus/meta.json ]; then
  add_failure "missing .gitnexus/meta.json; run bash scripts/gitnexus-index.sh first"
else
  files="$(read_meta_field 'm.stats?.files')"
  nodes="$(read_meta_field 'm.stats?.nodes')"
  edges="$(read_meta_field 'm.stats?.edges')"
  flows="$(read_meta_field 'm.stats?.processes')"
  embeddings="$(read_meta_field 'm.stats?.embeddings')"

  echo "    files=${files:-0}, nodes=${nodes:-0}, edges=${edges:-0}, flows=${flows:-0}, embeddings=${embeddings:-0}"

  [ "${files:-0}" -gt 0 ] || add_failure "GitNexus indexed zero files"
  [ "${nodes:-0}" -gt 0 ] || add_failure "GitNexus indexed zero nodes"
  [ "${edges:-0}" -gt 0 ] || add_failure "GitNexus indexed zero edges"
  [ "${flows:-0}" -gt 0 ] || add_failure "GitNexus indexed zero flows"
  [ "${embeddings:-0}" -gt 0 ] || add_failure "GitNexus embeddings are still zero; rerun scripts/gitnexus-index.sh --embeddings after fixing the selected GitNexus/LadybugDB vector-index path"

  if [ -n "${GITNEXUS_BIN:-}" ]; then
    if [ ! -x "$GITNEXUS_BIN" ]; then
      add_failure "GITNEXUS_BIN is not executable: $GITNEXUS_BIN"
    else
      repo_name="${GITNEXUS_REPO_NAME:-$(basename "$PROJECT_ROOT")}"
      if output="$("$GITNEXUS_BIN" cypher -r "$repo_name" "MATCH (e:CodeEmbedding) RETURN count(e) AS cnt" 2>&1)"; then
        cypher_embeddings="$(printf '%s\n' "$output" | extract_cypher_count)"
        cypher_embeddings="$(coerce_nonnegative_int "$cypher_embeddings")"
        [ "$cypher_embeddings" -gt 0 ] || add_failure "GitNexus cypher integrity check returned zero embeddings"
        if [ "${embeddings:-0}" -gt 0 ] && [ "$cypher_embeddings" -ne "${embeddings:-0}" ]; then
          add_failure "GitNexus meta embeddings (${embeddings:-0}) do not match cypher count (${cypher_embeddings})"
        fi
      else
        add_failure "GitNexus cypher integrity check failed; .gitnexus may be unreadable"
      fi
    fi
  else
    add_warning "GitNexus store integrity was not checked; set GITNEXUS_BIN=/path/to/gitnexus to verify cypher readability"
  fi
fi

echo ">>> Checking release readiness declarations"
if rg -q "Not ready for commercial launch|当前结论：目标尚未完成|当前目标不能标记完成|商业发布仍阻断" docs/release docs/audit/SUMMARY.md; then
  add_failure "release documents still declare the project not commercially ready"
fi

echo ">>> Checking external release evidence"
release_evidence=(
  "docs/release/evidence/payment-sandbox.md|payment sandbox"
  "docs/release/evidence/esign-sandbox.md|e-sign sandbox"
  "docs/release/evidence/desktop-runtime-smoke.md|desktop runtime smoke"
  "docs/release/evidence/rag-full50-live-baseline.md|RAG full 50 live baseline"
  "docs/release/evidence/mobile-device-smoke.md|mobile and mini-program device smoke"
  "docs/release/evidence/static-quality-baseline.md|static quality baseline"
)

for item in "${release_evidence[@]}"; do
  if ! evidence_validation_output="$(python3 scripts/validate-release-evidence.py "$item" 2>&1)"; then
    while IFS= read -r line; do
      [ -z "$line" ] && continue
      case "$line" in
        WARN:\ *)
          add_warning "${line#WARN: }"
          ;;
        FAIL:\ *)
          add_failure "${line#FAIL: }"
          ;;
        *)
          add_warning "$line"
          ;;
      esac
    done <<< "$evidence_validation_output"
  fi
done

echo ">>> Checking known high-risk code-level gates"
if ! evidence_secret_output="$(bash scripts/release-evidence-secret-scan.sh 2>&1)"; then
  add_failure "release evidence artifacts contain possible secrets or raw PII"
  while IFS= read -r line; do
    [ -n "$line" ] && add_warning "$line"
  done <<< "$evidence_secret_output"
fi

if artifact_validation_output="$(python3 scripts/validate-release-artifacts.py 2>&1)"; then
  while IFS= read -r line; do
    case "$line" in
      WARN:\ *)
        add_warning "${line#WARN: }"
        ;;
    esac
  done <<< "$artifact_validation_output"
else
  add_failure "release evidence artifacts are malformed or insufficiently redacted"
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    case "$line" in
      WARN:\ *)
        add_warning "${line#WARN: }"
        ;;
      FAIL:\ *)
        add_failure "${line#FAIL: }"
        ;;
      *)
        add_warning "$line"
        ;;
    esac
  done <<< "$artifact_validation_output"
fi

if ! desktop_security_output="$(bash scripts/desktop-sqlite-security-gate.sh 2>&1)"; then
  add_failure "desktop SQLite encryption/keyring gate is still release-blocking"
  while IFS= read -r line; do
    [ -n "$line" ] && add_warning "$line"
  done <<< "$desktop_security_output"
fi

if ! desktop_network_output="$(bash scripts/desktop-network-surface-gate.sh 2>&1)"; then
  add_failure "desktop network surface gate is still release-blocking"
  while IFS= read -r line; do
    [ -n "$line" ] && add_warning "$line"
  done <<< "$desktop_network_output"
fi

if rg -q '当前 `ruff` / `mypy` 全仓历史问题未清零|ruff/mypy 全仓清零仍未完成|全仓 `ruff` / `mypy` 尚未清零' \
  docs/release docs/openspec docs/audit; then
  add_failure "ruff/mypy full-repo quality baseline is not closed"
fi

if [ "$RUN_LOCAL_TESTS" -eq 1 ]; then
  echo ">>> Running local code-level smoke commands"
  require_command "git diff --check" git diff --check
  require_command "frontend lint" bash -lc "cd frontend && npm run lint"
  require_command "frontend tests" bash -lc "cd frontend && npm test"
  require_command "frontend build" bash -lc "cd frontend && npm run build"
  require_command "frontend workstation settings e2e" \
    bash -lc "cd frontend && npx playwright test e2e/settings-workstation.spec.ts --project=chromium --project=mobile"
  require_command "desktop cargo check" bash -lc "cd desktop && cargo check"
  require_command "desktop cargo test" bash -lc "cd desktop && cargo test"
  require_command "desktop network surface gate" bash scripts/desktop-network-surface-gate.sh
  require_command "desktop installed-profile SQLCipher/keyring smoke" \
    bash scripts/desktop-installed-profile-smoke.sh --out /tmp/anxin-desktop-installed-profile-gate.json
  require_command "backend mypy zero-baseline gate" bash scripts/mypy-baseline-check.sh
  require_command "agent capability policy tests" \
    bash -lc "cd backend && ./.venv/bin/pytest -q tests/test_harness.py -k 'PolicyEngine or AgentMcpToolPolicy'"
  require_command "agent governance policy tests" \
    bash -lc "cd backend && ./.venv/bin/pytest -q tests/test_agent_governance_policy.py"
  require_command "capability route token tests" \
    bash -lc "cd backend && ./.venv/bin/pytest -q tests/test_capability_routes.py"
  require_command "agent governance model tests" \
    bash -lc "cd backend && ./.venv/bin/pytest -q tests/test_agent_governance_models.py"
  require_command "agent governance service tests" \
    bash -lc "cd backend && ./.venv/bin/pytest -q tests/test_agent_governance_service.py"
  require_command "agent approval service tests" \
    bash -lc "cd backend && ./.venv/bin/pytest -q tests/test_agent_approval_service.py"
  require_command "MCP route governance tests" \
    bash -lc "cd backend && ./.venv/bin/pytest -q tests/test_mcp_route_governance.py"
  require_command "CLI route governance tests" \
    bash -lc "cd backend && ./.venv/bin/pytest -q tests/test_cli_route.py"
  require_command "skill evolution gate tests" \
    bash -lc "cd backend && ./.venv/bin/pytest -q tests/test_skill_evolution_service.py tests/test_skill_service.py"
  require_command "approval authorization guard tests" \
    bash -lc "cd backend && ./.venv/bin/pytest -q tests/test_business_authorization_guards.py -k 'approval or template'"
  require_command "MCP connection config policy tests" \
    bash -lc "cd backend && ./.venv/bin/pytest -q tests/test_config_commercial_guards.py -k mcp"
  require_command "RAG full50 runner tests" \
    bash -lc "backend/.venv/bin/pytest -q backend/tests/eval/test_rag_full50_runner.py"
  require_command "RAG quality metrics tests" \
    bash -lc "backend/.venv/bin/pytest -q backend/tests/eval/test_rag_quality_smoke.py"
  require_command "sandbox evidence runner tests" \
    bash -lc "backend/.venv/bin/pytest -q backend/tests/test_sandbox_evidence_runner.py"
  require_command "payment/e-sign provider and webhook tests" \
    bash -lc "cd backend && ./.venv/bin/pytest -q tests/test_payment_provider_clients.py tests/test_esign_provider_clients.py tests/test_official_webhook_security.py tests/test_webhook_business_events.py tests/test_refund_idempotency.py tests/test_external_surface_guards.py tests/test_commercial_action_audit.py"
  require_command "release evidence secret scan tests" \
    bash -lc "backend/.venv/bin/pytest -q backend/tests/test_release_evidence_secret_scan.py"
  require_command "release evidence artifact validation tests" \
    bash -lc "backend/.venv/bin/pytest -q backend/tests/test_release_artifact_validation.py"
  require_command "commercial readiness gate tests" \
    bash -lc "backend/.venv/bin/pytest -q backend/tests/test_commercial_readiness_gate.py"
  require_command "release worktree inventory tests" \
    bash -lc "backend/.venv/bin/pytest -q backend/tests/test_release_worktree_inventory.py"
  require_command "release evidence validation tests" \
    bash -lc "backend/.venv/bin/pytest -q backend/tests/test_release_evidence_validation.py"
  require_command "commercial delivery checklist tests" \
    bash -lc "backend/.venv/bin/pytest -q backend/tests/test_commercial_delivery_checklist.py"
  require_command "commercial delivery lanes tests" \
    bash -lc "backend/.venv/bin/pytest -q backend/tests/test_commercial_delivery_lanes.py"
  require_command "release evidence validation lint" \
    bash -lc "backend/.venv/bin/ruff check backend/tests/test_commercial_delivery_checklist.py backend/tests/test_commercial_delivery_lanes.py backend/tests/test_commercial_readiness_gate.py scripts/release-worktree-inventory.py backend/tests/test_release_worktree_inventory.py scripts/validate-release-artifacts.py backend/tests/test_release_artifact_validation.py scripts/validate-release-evidence.py backend/tests/test_release_evidence_validation.py"
  require_command "sandbox evidence preflight" \
    bash -lc "python3 scripts/sandbox-evidence-runner.py --scope all --out /tmp/anxin-sandbox-gate-preflight.json >/dev/null"
  require_command "mobile and mini-program local smoke" \
    bash scripts/mobile-device-smoke.sh \
      --out /tmp/anxin-mobile-mini-code-smoke-gate.json \
      --manual-template-out /tmp/anxin-mobile-device-manual-template-gate.json
else
  add_warning "local tests were not run; use --with-local-tests for code-level smoke commands"
fi

echo
if [ "${#warnings[@]}" -gt 0 ]; then
  echo "Warnings:"
  for warning in "${warnings[@]}"; do
    echo "  - $warning"
  done
  echo
fi

if [ "${#failures[@]}" -gt 0 ]; then
  echo "Commercial readiness gate: FAIL"
  for failure in "${failures[@]}"; do
    echo "  - $failure"
  done
  exit 1
fi

echo "Commercial readiness gate: PASS"
