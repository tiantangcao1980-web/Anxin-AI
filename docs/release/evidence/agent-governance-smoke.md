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
| Route-token broker | code-level complete for hash-only lease storage, scope checks, expiration, consumer mismatch, revocation next-call failure, and audit events across MCP, CLI, Chat Agent LLM, RAG direct LLM, and browser/crawler fetch entry points | `backend/tests/test_agent_governance_service.py`, `backend/tests/test_mcp_route_governance.py`, `backend/tests/test_cli_route.py`, `backend/tests/test_llm_route_governance.py`, `backend/tests/test_crawler_compliance.py` |
| High-risk approvals | code-level complete for service/API creation, scope, authorized decisions, revocation, expiration, validate, audit timeline, audit export, payload redaction, workspace-control fail-closed, and approved-workspace artifact list/create/export with recursive redaction | `backend/src/services/agent_approval_service.py`, `backend/src/api/routes/agent_approvals.py`, `backend/tests/test_agent_approval_service.py`, `backend/tests/test_agent_approval_api.py`, `frontend/src/lib/api.ts`, `frontend/src/pages/AgentApprovalWorkspace.tsx`, `frontend/e2e/helpers/session.ts`, `frontend/e2e/agent-approval-workspace.spec.ts` |
| Skill governance | code-level complete for proposal, required eval, authorized approval, gray release, rollback, enabled-version persistence, org isolation, API scope, API audit export, append-only audit events, migration upgrade/downgrade, no raw secret/token columns, and a minimal frontend governance panel for create/eval/approve/gray/audit flows | `backend/tests/test_skill_evolution_service.py`, `backend/tests/test_skill_service.py`, `backend/tests/test_skill_governance_models.py`, `backend/tests/test_skill_governance_service.py`, `backend/tests/test_skill_governance_api.py`, `frontend/src/lib/api.ts`, `frontend/src/pages/AgentApprovalWorkspace.tsx`, `frontend/e2e/agent-approval-workspace.spec.ts` |
| Mobile remote-control safety gate | code-level complete for persisted pairing requests, desktop confirmation, DB-backed route-token issuance, safe-probe-only command queue, desktop host claim, running/completed/failed status callback, cancellation, recursively redacted payload/audit events, fail-closed local/top-secret/missing-token/high-risk states, backend enqueue rejection for non-safe-probe command types with audited `unsupported_command_type` / `remote_control_command_type_not_supported`, desktop Tauri IPC host confirm/claim/status payload validation, an explicit safe-probe host cycle that completes only `ping/status_probe` while failing unsupported commands, a bounded safe-probe host poll command with interval/cycle/limit caps, and a mobile `/desktop-control` action that can only enqueue `desktop.status_probe` after confirmed-pairing status plus short-lived route-token issuance; mobile can now refresh queued command status, cancel queued/claimed safe probes, and show a redacted remote-control audit timeline without rendering command payloads or metadata; still no always-on desktop daemon, high-risk executor, cross-device run, signed runtime, or device evidence | `backend/src/services/remote_control_service.py`, `backend/src/api/routes/sync.py`, `backend/src/models/sync.py`, `backend/alembic/versions/042_add_remote_control_queue.py`, `backend/alembic/versions/043_add_remote_control_execution_state.py`, `backend/tests/test_remote_control_fail_closed.py`, `desktop/src/services/remote_control_host.rs`, `desktop/src/commands/remote_control.rs`, `mobile/app/desktop-control.tsx`, `mobile/src/services/api.test.ts`, `mobile/src/features/desktop-control/model.test.ts` |
| Real approved connector rehearsal | pending | TBD |
| LLM/browser/desktop-control route-token integration | code-level partial for REST/SSE/WebSocket Chat Agent LLM runtime, RAG direct LLM calls, and browser/crawler fetch: Agent sync/stream model calls and RAG generation/query expansion/entity extraction/stream generation now fail closed in staging/production unless an org-scoped DB-backed route token with `llm:chat` scope is supplied, `/chat/route-token` can issue a user-bound token, REST Knowledge RAG, synchronous Chat RAG, and WebSocket RAG pass route context into `RAGService`, and `crawler_service.fetch()` requires `browser:fetch` before robots/http access. Due-diligence execution/credit/wenshu lookups no longer keep direct Playwright fallbacks; they use the compliant crawl service path or return no external evidence. Route revocation denies the next Agent LLM/RAG/crawler call and writes governance audit events. Full browser automation beyond the crawler fetch path, desktop-control high-risk execution, real connector rehearsal, and cross-process runtime evidence remain pending. | `backend/src/services/llm_route_governance.py`, `backend/src/agents/base.py`, `backend/src/services/rag_service.py`, `backend/src/services/knowledge_service.py`, `backend/src/services/chat_service.py`, `backend/src/api/routes/chat.py`, `backend/src/api/routes/knowledge.py`, `backend/src/api/routes/chat_handlers/rag_handler.py`, `backend/tests/test_llm_route_governance.py`, `backend/src/services/crawler_service.py`, `backend/src/services/crawl4ai_service.py`, `backend/src/services/due_diligence_service.py`, `backend/src/core/config.py`, `backend/tests/test_crawler_compliance.py`, `backend/tests/test_due_diligence_intent.py`, `scripts/commercial-readiness-gate.sh` |
| Human-in-the-loop observe/pause/takeover/terminate runtime | pending | TBD |
| Artifact-first workspace and export flow | code-level partial complete for approved-workspace summary artifact recording, list view, JSON export, API redaction, service redaction, and frontend workspace artifact panel; still missing runtime-generated long-task artifacts, artifact editing, desktop/local sync rehearsal, cross-device recovery, and commercial runtime evidence | `backend/src/services/agent_approval_service.py`, `backend/src/api/routes/agent_approvals.py`, `backend/tests/test_agent_approval_service.py`, `backend/tests/test_agent_approval_api.py`, `frontend/src/lib/api.ts`, `frontend/src/pages/AgentApprovalWorkspace.tsx`, `frontend/e2e/helpers/session.ts`, `frontend/e2e/agent-approval-workspace.spec.ts` |
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
# 7 API tests and 8 service tests cover approved-workspace artifact list/create/export redaction.
cd backend && ./.venv/bin/pytest -q tests/test_mcp_route_governance.py
cd backend && ./.venv/bin/pytest -q tests/test_cli_route.py
cd backend && ./.venv/bin/pytest -q tests/test_llm_route_governance.py
# 11 passed on 2026-05-08, including RAG direct LLM route-token denial/allow/revoke regressions.
cd backend && ./.venv/bin/pytest -q tests/test_crawler_compliance.py
cd backend && ./.venv/bin/pytest -q tests/test_due_diligence_intent.py tests/test_chat_due_diligence_routing.py
# 21 passed on 2026-05-08, including no-direct-Playwright due-diligence Wenshu lookup coverage.
cd backend && ./.venv/bin/pytest -q tests/test_skill_evolution_service.py tests/test_skill_service.py tests/test_skill_governance_models.py tests/test_skill_governance_service.py tests/test_skill_governance_api.py
cd backend && ./.venv/bin/pytest -q tests/test_remote_control_fail_closed.py
# 9 passed on 2026-05-08, including backend safe-probe-only enqueue rejection for unsupported command types.
cd frontend && npx playwright test e2e/agent-approval-workspace.spec.ts --project=chromium --project=mobile
```

## Completion Rule

Only change this file to `Status: complete` after the pending rows above have real redacted artifacts and the commercial readiness gate passes on a clean committed worktree. GitNexus may be rerun at final release for commit-scoped indexing, but it must not be used as a substitute for this runtime evidence.
