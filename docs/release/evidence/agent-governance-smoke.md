# Agent Governance Smoke Evidence

Status: pending
Owner: TBD
Environment: local code-level governance smoke complete; full commercial runtime evidence pending
Date range: 2026-05-08

This evidence file tracks the enterprise-agent governance lane. It is intentionally `Status: pending` because code-level policy, approval, route-token, and SkillGovernance regressions are not the same as a full commercial runtime rehearsal.

## Required Scope

| Scope | Current result | Artifact reference |
|---|---|---|
| Capability policy | code-level complete for harness tool filtering plus service-level unified capability decisions covering subscription, role, permission, risk level, privacy mode, device trust, channel policy, high-risk approval context, audit events, unknown-tool/unknown-route fail-closed, MCP runtime re-checks, a minimal frontend capability policy panel for role-filtered available/requestable/hidden tool visibility, a minimal org CapabilityRoute policy API/panel for admin list/update and enable/disable, policy redaction, disable-time lease revocation, and five business permission regressions: employee browser-fill rejection, department-admin report Agent allow, boss desktop-control approval, super-admin MCP route revocation, and external-provider material-package boundary | `backend/src/services/capability_policy_engine.py`, `backend/src/services/agent_governance_service.py`, `backend/src/api/routes/agent_approvals.py`, `backend/tests/test_capability_policy_engine.py`, `backend/tests/test_agent_governance_policy.py`, `backend/tests/test_capability_routes.py`, `backend/tests/test_agent_governance_service.py`, `backend/tests/test_agent_approval_api.py`, `frontend/src/hooks/usePermission.ts`, `frontend/src/lib/api.ts`, `frontend/src/pages/AgentApprovalWorkspace.tsx`, `frontend/e2e/helpers/auth.ts`, `frontend/e2e/helpers/session.ts`, `frontend/e2e/agent-approval-workspace.spec.ts` |
| Route-token broker | code-level complete for hash-only lease storage, scope checks, expiration, consumer mismatch, revocation next-call failure, and audit events | `backend/tests/test_agent_governance_service.py`, `backend/tests/test_mcp_route_governance.py`, `backend/tests/test_cli_route.py` |
| High-risk approvals | code-level complete for service/API creation, scope, authorized decisions, revocation, expiration, validate, audit timeline, audit export, payload redaction, and workspace-control fail-closed | `backend/tests/test_agent_approval_service.py`, `backend/tests/test_agent_approval_api.py`, `frontend/e2e/agent-approval-workspace.spec.ts` |
| Skill governance | code-level complete for proposal, required eval, authorized approval, gray release, rollback, enabled-version persistence, org isolation, API scope, API audit export, append-only audit events, migration upgrade/downgrade, no raw secret/token columns, and a minimal frontend governance panel for create/eval/approve/gray/audit flows | `backend/tests/test_skill_evolution_service.py`, `backend/tests/test_skill_service.py`, `backend/tests/test_skill_governance_models.py`, `backend/tests/test_skill_governance_service.py`, `backend/tests/test_skill_governance_api.py`, `frontend/src/lib/api.ts`, `frontend/src/pages/AgentApprovalWorkspace.tsx`, `frontend/e2e/agent-approval-workspace.spec.ts` |
| Mobile remote-control safety gate | code-level complete for persisted pairing requests, desktop confirmation, DB-backed route-token issuance, command queue, desktop host claim, running/completed/failed status callback, cancellation, recursively redacted payload/audit events, fail-closed local/top-secret/missing-token/high-risk states, desktop Tauri IPC host confirm/claim/status payload validation, an explicit safe-probe host cycle that completes only `ping/status_probe` while failing unsupported commands, a bounded safe-probe host poll command with interval/cycle/limit caps, and a mobile `/desktop-control` action that can only enqueue `desktop.status_probe` after confirmed-pairing status plus short-lived route-token issuance; mobile can now refresh queued command status, cancel queued/claimed safe probes, and show a redacted remote-control audit timeline without rendering command payloads or metadata; still no always-on desktop daemon, high-risk executor, cross-device run, signed runtime, or device evidence | `backend/src/services/remote_control_service.py`, `backend/src/api/routes/sync.py`, `backend/src/models/sync.py`, `backend/alembic/versions/042_add_remote_control_queue.py`, `backend/alembic/versions/043_add_remote_control_execution_state.py`, `backend/tests/test_remote_control_fail_closed.py`, `desktop/src/services/remote_control_host.rs`, `desktop/src/commands/remote_control.rs`, `mobile/app/desktop-control.tsx`, `mobile/src/services/api.test.ts`, `mobile/src/features/desktop-control/model.test.ts` |
| Real approved connector rehearsal | pending | TBD |
| LLM/browser/desktop-control route-token integration | pending | TBD |
| Human-in-the-loop observe/pause/takeover/terminate runtime | pending | TBD |
| Artifact-first workspace and export flow | pending | TBD |
| Full capability center UI beyond the current role-filtered visibility panel, org route enable/disable panel, Agent approval panel, and Skill governance panel, plus full policy editor, subscription purchase linkage, and department request flow | pending | TBD |
| Memory governance and cross-process revocation evidence | pending | TBD |

## Local Verification

```bash
cd backend && ./.venv/bin/pytest -q tests/test_agent_governance_policy.py
cd backend && ./.venv/bin/pytest -q tests/test_capability_policy_engine.py
# 11 passed on 2026-05-08
cd backend && ./.venv/bin/pytest -q tests/test_capability_routes.py
cd backend && ./.venv/bin/pytest -q tests/test_agent_governance_models.py
cd backend && ./.venv/bin/pytest -q tests/test_agent_governance_service.py
cd backend && ./.venv/bin/pytest -q tests/test_agent_approval_api.py
cd backend && ./.venv/bin/pytest -q tests/test_agent_approval_service.py
cd backend && ./.venv/bin/pytest -q tests/test_mcp_route_governance.py
cd backend && ./.venv/bin/pytest -q tests/test_cli_route.py
cd backend && ./.venv/bin/pytest -q tests/test_skill_evolution_service.py tests/test_skill_service.py tests/test_skill_governance_models.py tests/test_skill_governance_service.py tests/test_skill_governance_api.py
cd backend && ./.venv/bin/pytest -q tests/test_remote_control_fail_closed.py
cd frontend && npx playwright test e2e/agent-approval-workspace.spec.ts --project=chromium --project=mobile
```

## Completion Rule

Only change this file to `Status: complete` after the pending rows above have real redacted artifacts and the commercial readiness gate passes on a clean committed worktree. GitNexus may be rerun at final release for commit-scoped indexing, but it must not be used as a substitute for this runtime evidence.
