#!/usr/bin/env bash
# GitNexus indexing helper for this repository.
#
# Default mode refreshes the structure graph only. Embeddings are opt-in because
# they are slow and the stable GitNexus/LadybugDB vector-index path is fragile on
# this machine; use the rc/direct binary path after the preflight passes.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/gitnexus-index.sh [options]

Options:
  --structure-only        Rebuild structure graph only (default).
  --embeddings            Rebuild structure graph and generate embeddings.
  --clean-first           Run "gitnexus clean --force" before indexing.
  --skip-embedding-preflight
                          Skip the tiny embedding/vector-index smoke test.
  --skip-context-checks   Skip post-index symbol smoke checks.
  -h, --help              Show this help.

Embedding mode requires an OpenAI-compatible endpoint:
  GITNEXUS_BIN                Optional absolute path to a GitNexus binary.
                              Takes precedence over GITNEXUS_NPX_SPEC and avoids npx/npm wrapper issues.
  GITNEXUS_NPX_SPEC           Optional npx package spec. Default: gitnexus@latest
                              Use gitnexus@rc for the 1.6.4 release-candidate
                              vector-index/exact-scan fallback path.
  GITNEXUS_EMBEDDING_URL      Base URL ending at /v1, for example http://127.0.0.1:8080/v1
  GITNEXUS_EMBEDDING_MODEL    Model name accepted by the endpoint
  GITNEXUS_EMBEDDING_DIMS     Positive integer matching the endpoint vector size
  GITNEXUS_EMBEDDING_API_KEY  Optional; GitNexus uses "unused" if omitted
  GITNEXUS_REPO_NAME          Optional repository label. Default: current directory basename.

If GITNEXUS_* variables are unset, the script falls back to EMBEDDING_BASE_URL,
EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, and EMBEDDING_API_KEY from .env or
backend/.env.

Examples:
  bash scripts/gitnexus-index.sh
  GITNEXUS_BIN=/path/to/gitnexus \
  bash scripts/gitnexus-index.sh --embeddings
  GITNEXUS_NPX_SPEC=gitnexus@rc \
  GITNEXUS_EMBEDDING_URL=http://127.0.0.1:8080/v1 \
  GITNEXUS_EMBEDDING_MODEL=snowflake-arctic-embed-xs \
  GITNEXUS_EMBEDDING_DIMS=384 \
  bash scripts/gitnexus-index.sh --embeddings
EOF
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

info() {
  echo ">>> $*"
}

count_lines() {
  awk 'NF { n++ } END { print n + 0 }'
}

RUN_EMBEDDINGS=0
CLEAN_FIRST=0
CONTEXT_CHECKS=1
EMBEDDING_PREFLIGHT=1
BACKUP_PATH=""
INDEX_STATS_VALIDATED=0

restore_backup_on_failure() {
  local rc=$?
  if [ "$rc" -ne 0 ] && [ "$RUN_EMBEDDINGS" -eq 1 ] && [ "$INDEX_STATS_VALIDATED" -eq 0 ] && [ -n "$BACKUP_PATH" ] && [ -d "$BACKUP_PATH" ]; then
    local failed_path
    failed_path=".gitnexus.failed-$(date +%Y%m%d-%H%M%S)"
    if [ -d .gitnexus ]; then
      echo ">>> Embedding run failed; moving partial .gitnexus to ${failed_path}" >&2
      mv .gitnexus "$failed_path" 2>/dev/null || true
    fi
    echo ">>> Restoring previous GitNexus index from ${BACKUP_PATH}" >&2
    cp -R "$BACKUP_PATH" .gitnexus
  fi
  exit "$rc"
}

trap restore_backup_on_failure EXIT

for arg in "$@"; do
  case "$arg" in
    --structure-only)
      RUN_EMBEDDINGS=0
      ;;
    --embeddings)
      RUN_EMBEDDINGS=1
      ;;
    --clean-first)
      CLEAN_FIRST=1
      ;;
    --skip-embedding-preflight)
      EMBEDDING_PREFLIGHT=0
      ;;
    --skip-context-checks)
      CONTEXT_CHECKS=0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      die "unknown option: $arg"
      ;;
  esac
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

[ -d .git ] || die "run this script from inside the Git repository"
[ -f .gitnexusignore ] || die ".gitnexusignore is required before indexing"

REPO_NAME="${GITNEXUS_REPO_NAME:-$(basename "$PROJECT_ROOT")}"
GITNEXUS_NPX_SPEC="${GITNEXUS_NPX_SPEC:-gitnexus@latest}"

if [ -n "${GITNEXUS_BIN:-}" ]; then
  [ -x "$GITNEXUS_BIN" ] || die "GITNEXUS_BIN is not executable: $GITNEXUS_BIN"
  GITNEXUS_COMMAND_LABEL="$GITNEXUS_BIN"
else
  command -v npx >/dev/null 2>&1 || die "npx is required when GITNEXUS_BIN is not set"
  GITNEXUS_COMMAND_LABEL="npx -y ${GITNEXUS_NPX_SPEC}"
fi

gitnexus_cli() {
  if [ -n "${GITNEXUS_BIN:-}" ]; then
    "$GITNEXUS_BIN" "$@"
  else
    npx -y "$GITNEXUS_NPX_SPEC" "$@"
  fi
}

validate_embedding_env() {
  [ -n "${GITNEXUS_EMBEDDING_URL:-}" ] || die "GITNEXUS_EMBEDDING_URL is required for --embeddings"
  [ -n "${GITNEXUS_EMBEDDING_MODEL:-}" ] || die "GITNEXUS_EMBEDDING_MODEL is required for --embeddings"
  [ -n "${GITNEXUS_EMBEDDING_DIMS:-}" ] || die "GITNEXUS_EMBEDDING_DIMS is required for --embeddings"

  case "$GITNEXUS_EMBEDDING_DIMS" in
    ''|*[!0-9]*)
      die "GITNEXUS_EMBEDDING_DIMS must be a positive integer"
      ;;
  esac

  [ "$GITNEXUS_EMBEDDING_DIMS" -gt 0 ] || die "GITNEXUS_EMBEDDING_DIMS must be greater than 0"

  if [[ "$GITNEXUS_EMBEDDING_URL" == */embeddings ]]; then
    die "GITNEXUS_EMBEDDING_URL must be the base /v1 URL, not the /embeddings path"
  fi
}

backup_existing_index() {
  if [ -d .gitnexus ]; then
    local ts backup
    ts="$(date +%Y%m%d-%H%M%S)"
    backup=".gitnexus.backup-${ts}"
    info "Backing up existing .gitnexus to ${backup}"
    cp -R .gitnexus "$backup"
    BACKUP_PATH="$backup"
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

verify_embedding_store() {
  local output count

  [ "$RUN_EMBEDDINGS" -eq 1 ] || return 0

  info "Verifying GitNexus embedding store"
  if ! output="$(gitnexus_cli cypher -r "$REPO_NAME" "MATCH (e:CodeEmbedding) RETURN count(e) AS cnt" 2>&1)"; then
    printf '%s\n' "$output" >&2
    die "GitNexus embedding store verification failed"
  fi

  count="$(printf '%s\n' "$output" | extract_cypher_count)"
  count="$(coerce_nonnegative_int "$count")"
  [ "$count" -gt 0 ] || die "GitNexus embedding store verification returned zero embeddings"
  info "GitNexus embedding store count=${count}"
}

report_worktree_drift() {
  local tracked_changes untracked_changes

  tracked_changes="$(git status --short --untracked-files=no | count_lines)"
  untracked_changes="$(git ls-files --others --exclude-standard | count_lines)"

  if [ "$tracked_changes" -gt 0 ] || [ "$untracked_changes" -gt 0 ]; then
    info "Worktree drift: tracked_changes=${tracked_changes}, untracked_files=${untracked_changes}"
    info "GitNexus status is commit-scoped; use detect-changes plus direct source inspection for dirty worktree analysis, and rebuild embeddings after release artifacts are committed."
  fi
}

read_env_value() {
  local env_file="$1"
  local key="$2"
  local line value

  [ -f "$env_file" ] || return 0
  line="$(grep -E "^${key}=" "$env_file" | tail -n 1 || true)"
  [ -n "$line" ] || return 0

  value="${line#*=}"
  value="${value%$'\r'}"
  value="${value%\"}"
  value="${value#\"}"
  value="${value%\'}"
  value="${value#\'}"
  printf '%s' "$value"
}

apply_embedding_env_fallbacks() {
  local env_file value
  for env_file in .env backend/.env; do
    [ -f "$env_file" ] || continue

    if [ -z "${GITNEXUS_EMBEDDING_URL:-}" ]; then
      value="$(read_env_value "$env_file" EMBEDDING_BASE_URL)"
      [ -n "$value" ] && export GITNEXUS_EMBEDDING_URL="$value"
    fi

    if [ -z "${GITNEXUS_EMBEDDING_MODEL:-}" ]; then
      value="$(read_env_value "$env_file" EMBEDDING_MODEL)"
      [ -n "$value" ] && export GITNEXUS_EMBEDDING_MODEL="$value"
    fi

    if [ -z "${GITNEXUS_EMBEDDING_DIMS:-}" ]; then
      value="$(read_env_value "$env_file" EMBEDDING_DIMENSIONS)"
      [ -n "$value" ] && export GITNEXUS_EMBEDDING_DIMS="$value"
    fi

    if [ -z "${GITNEXUS_EMBEDDING_API_KEY:-}" ]; then
      value="$(read_env_value "$env_file" EMBEDDING_API_KEY)"
      [ -n "$value" ] && export GITNEXUS_EMBEDDING_API_KEY="$value"
    fi
  done
}

run_embedding_preflight() {
  local tmp_dir preflight_name rc

  tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/gitnexus-embedding-preflight.XXXXXX")"
  preflight_name="${REPO_NAME}-embedding-preflight-$(date +%s)"

  cleanup_embedding_preflight() {
    gitnexus_cli remove --force "$preflight_name" >/dev/null 2>&1 || true
    rm -rf "$tmp_dir"
  }

  info "Running GitNexus embedding preflight with ${GITNEXUS_COMMAND_LABEL} (${preflight_name})"
  set +e
  (
    cd "$tmp_dir"
    git init -q
    printf 'export function gitnexusEmbeddingPreflight(name) { return `hello ${name}`; }\n' > index.js
    printf 'node_modules/\n.gitnexus*\n' > .gitnexusignore
    git add . >/dev/null
    git -c user.email=gitnexus-preflight@example.invalid \
      -c user.name=gitnexus-preflight \
      commit -q -m init >/dev/null
    gitnexus_cli analyze \
      --force \
      --embeddings \
      --skip-agents-md \
      --name "$preflight_name" \
      .
  )
  rc=$?
  set -e
  cleanup_embedding_preflight

  if [ "$rc" -ne 0 ]; then
    die "GitNexus embedding preflight failed with exit code ${rc}; refusing to run embeddings against the main repository. The selected GitNexus command could not complete CodeEmbedding write plus CREATE_VECTOR_INDEX in a tiny repository. Keep the previous index, try GITNEXUS_NPX_SPEC=gitnexus@rc if using the stable package, or pass --skip-embedding-preflight only for controlled diagnostics."
  fi
}

if [ "$RUN_EMBEDDINGS" -eq 1 ]; then
  apply_embedding_env_fallbacks
  validate_embedding_env
  if [ "$EMBEDDING_PREFLIGHT" -eq 1 ]; then
    run_embedding_preflight
  fi
  backup_existing_index
else
  info "Structure-only mode. Embeddings are intentionally skipped."
fi

report_worktree_drift

if [ "$CLEAN_FIRST" -eq 1 ]; then
  info "Cleaning current GitNexus index"
  gitnexus_cli clean --force
fi

EXISTING_EMBEDDINGS=0
if [ -s .gitnexus/meta.json ]; then
  EXISTING_EMBEDDINGS="$(read_meta_field 'm.stats?.embeddings' 2>/dev/null || printf '0')"
  EXISTING_EMBEDDINGS="$(coerce_nonnegative_int "$EXISTING_EMBEDDINGS")"
fi

ANALYZE_ARGS=(analyze --skip-agents-md --name "$REPO_NAME")
if [ "$RUN_EMBEDDINGS" -eq 1 ]; then
  ANALYZE_ARGS+=(--force --embeddings)
elif [ "$EXISTING_EMBEDDINGS" -gt 0 ]; then
  info "Existing embeddings detected (${EXISTING_EMBEDDINGS}); preserving them by skipping --force in structure-only mode. Use --embeddings for a full refresh."
else
  ANALYZE_ARGS+=(--force)
fi
ANALYZE_ARGS+=(.)

info "Running: ${GITNEXUS_COMMAND_LABEL} ${ANALYZE_ARGS[*]}"
gitnexus_cli "${ANALYZE_ARGS[@]}"

[ -f .gitnexus/meta.json ] || die ".gitnexus/meta.json was not created"

FILES="$(read_meta_field 'm.stats?.files')"
NODES="$(read_meta_field 'm.stats?.nodes')"
EDGES="$(read_meta_field 'm.stats?.edges')"
FLOWS="$(read_meta_field 'm.stats?.processes')"
EMBEDDINGS="$(read_meta_field 'm.stats?.embeddings')"

info "GitNexus stats: files=${FILES}, nodes=${NODES}, edges=${EDGES}, flows=${FLOWS}, embeddings=${EMBEDDINGS}"

[ "${FILES:-0}" -gt 0 ] || die "GitNexus indexed zero files"
[ "${NODES:-0}" -gt 0 ] || die "GitNexus indexed zero nodes"
[ "${EDGES:-0}" -gt 0 ] || die "GitNexus indexed zero edges"

if [ "$RUN_EMBEDDINGS" -eq 1 ] && [ "${EMBEDDINGS:-0}" -le 0 ]; then
  die "--embeddings completed but meta.json still reports zero embeddings"
fi

verify_embedding_store
INDEX_STATS_VALIDATED=1

info "GitNexus status"
gitnexus_cli status || info "GitNexus status command failed after meta.json validation; keeping the generated index"

if [ "$CONTEXT_CHECKS" -eq 1 ]; then
  info "Context smoke: runLocalSyncWithDependencies"
  gitnexus_cli context -r "$REPO_NAME" runLocalSyncWithDependencies >/dev/null
  info "Context smoke: getDesktopSQLiteSecurityStatus"
  gitnexus_cli context -r "$REPO_NAME" getDesktopSQLiteSecurityStatus >/dev/null
  info "Context smoke: sqlite_migrations"
  gitnexus_cli context -r "$REPO_NAME" sqlite_migrations >/dev/null
  if [ "${EMBEDDINGS:-0}" -gt 0 ]; then
    info "Query smoke: desktop sqlite security status"
    gitnexus_cli query "desktop sqlite security status" --limit 1 --repo "$REPO_NAME" >/dev/null
  fi
fi

info "Detecting affected symbols for current worktree"
gitnexus_cli detect-changes --repo "$REPO_NAME" || true

info "GitNexus indexing check complete"
