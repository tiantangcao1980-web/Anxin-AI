# Agent Governance Smoke Evidence

Status: pending
Owner: TBD
Environment: local code-level governance smoke complete; full commercial runtime evidence pending
Date range: 2026-05-08

This evidence file tracks the enterprise-agent governance lane. It is intentionally `Status: pending` because code-level policy, approval, route-token, and SkillGovernance regressions are not the same as a full commercial runtime rehearsal.

## Required Scope

| Scope | Current result | Artifact reference |
|---|---|---|
| Capability policy | code-level complete for subscription, permission, privacy, device, channel, high-risk approval context, unknown-tool fail-closed, MCP runtime re-checks, and a minimal frontend capability policy panel for available/blocked tool visibility | `backend/tests/test_agent_governance_policy.py`, `backend/tests/test_capability_routes.py`, `frontend/src/lib/api.ts`, `frontend/src/pages/AgentApprovalWorkspace.tsx`, `frontend/e2e/agent-approval-workspace.spec.ts` |
| Route-token broker | code-level complete for hash-only lease storage, scope checks, expiration, consumer mismatch, revocation next-call failure, and audit events | `backend/tests/test_agent_governance_service.py`, `backend/tests/test_mcp_route_governance.py`, `backend/tests/test_cli_route.py` |
| High-risk approvals | code-level complete for service/API creation, scope, authorized decisions, revocation, expiration, validate, audit timeline, audit export, payload redaction, and workspace-control fail-closed | `backend/tests/test_agent_approval_service.py`, `backend/tests/test_agent_approval_api.py`, `frontend/e2e/agent-approval-workspace.spec.ts` |
| Skill governance | code-level complete for proposal, required eval, authorized approval, gray release, rollback, enabled-version persistence, org isolation, API scope, API audit export, append-only audit events, migration upgrade/downgrade, no raw secret/token columns, and a minimal frontend governance panel for create/eval/approve/gray/audit flows | `backend/tests/test_skill_evolution_service.py`, `backend/tests/test_skill_service.py`, `backend/tests/test_skill_governance_models.py`, `backend/tests/test_skill_governance_service.py`, `backend/tests/test_skill_governance_api.py`, `frontend/src/lib/api.ts`, `frontend/src/pages/AgentApprovalWorkspace.tsx`, `frontend/e2e/agent-approval-workspace.spec.ts` |
| Mobile remote-control safety gate | code-level complete for persisted pairing requests, desktop confirmation, DB-backed route-token issuance, command queue, desktop host claim, running/completed/failed status callback, cancellation, recursively redacted payload/audit events, fail-closed local/top-secret/missing-token/high-risk states, desktop Tauri IPC host confirm/claim/status payload validation, and an explicit safe-probe host cycle that completes only `ping/status_probe` while failing unsupported commands; still no always-on desktop poller, high-risk executor, cross-device run, signed runtime, or device evidence | `backend/src/services/remote_control_service.py`, `backend/src/api/routes/sync.py`, `backend/src/models/sync.py`, `backend/alembic/versions/042_add_remote_control_queue.py`, `backend/alembic/versions/043_add_remote_control_execution_state.py`, `backend/tests/test_remote_control_fail_closed.py`, `desktop/src/services/remote_control_host.rs`, `desktop/src/commands/remote_control.rs`, `mobile/src/app/desktop-control.tsx` |
| Real approved connector rehearsal | pending | TBD |
| LLM/browser/desktop-control route-token integration | pending | TBD |
| Human-in-the-loop observe/pause/takeover/terminate runtime | pending | TBD |
| Artifact-first workspace and export flow | pending | TBD |
| Full capability center UI beyond the current visibility panel, Agent approval panel, and Skill governance panel, plus organization policy CRUD | pending | TBD |
| Memory governance and cross-process revocation evidence | pending | TBD |

## Local Verification

```bash
cd backend && ./.venv/bin/pytest -q tests/test_agent_governance_policy.py
cd backend && ./.venv/bin/pytest -q tests/test_capability_routes.py
cd backend && ./.venv/bin/pytest -q tests/test_agent_governance_models.py
cd backend && ./.venv/bin/pytest -q tests/test_agent_governance_service.py
cd backend && ./.venv/bin/pytest -q tests/test_agent_approval_service.py
cd backend && ./.venv/bin/pytest -q tests/test_agent_approval_api.py
cd backend && ./.venv/bin/pytest -q tests/test_mcp_route_governance.py
cd backend && ./.venv/bin/pytest -q tests/test_cli_route.py
cd backend && ./.venv/bin/pytest -q tests/test_skill_evolution_service.py tests/test_skill_service.py tests/test_skill_governance_models.py tests/test_skill_governance_service.py tests/test_skill_governance_api.py
cd backend && ./.venv/bin/pytest -q tests/test_remote_control_fail_closed.py
cd frontend && npx playwright test e2e/agent-approval-workspace.spec.ts --project=chromium --project=mobile
```

## Completion Rule

Only change this file to `Status: complete` after the pending rows above have real redacted artifacts and the commercial readiness gate passes on a clean committed worktree. GitNexus may be rerun at final release for commit-scoped indexing, but it must not be used as a substitute for this runtime evidence.
