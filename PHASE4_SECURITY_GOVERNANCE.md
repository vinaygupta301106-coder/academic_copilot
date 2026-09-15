# Phase 4 — Security, Governance & Traceability

Implemented foundational controls without changing the tested Phase 1–3 academic workflow.

## Controls
- AI input length limit (1200 characters).
- Prompt-injection detection for common instruction-override attempts.
- Secret/credential detection to reduce sensitive-data leakage into the local LLM.
- Security response headers and request IDs in FastAPI.
- AI responses expose source/provenance metadata: Neo4j, MySQL, and Ollama synthesis.
- Advisor workflow now checks a matching `X-Demo-Role` header against the role in the request. This is a **demo RBAC control**, not real authentication.
- Automated security unit tests are included.

## Governance boundary
Neo4j and MySQL remain authoritative for academic facts. Ollama is only a synthesis layer. Advisor approval remains a human-controlled action.

## Next Phase 4 work
- stronger permission-aware authentication/authorization
- source-level citation rendering for individual course facts
- prompt-injection, leakage, unsupported-claim and approval-boundary test suite
- audit coverage for security events
- baseline/manual-process evaluation and robustness evidence

## Part 2 — Permission-aware access

The Phase 4 Part 2 hardening adds server-side role and student-scope enforcement for the demo workflow. The UI role switcher is no longer the only boundary.

### Permission matrix

| Capability | Student | Advisor | Coordinator |
|---|---:|---:|---:|
| View own academic record | Yes | Yes | Yes |
| View student academic records | No (own only) | Yes | Yes |
| Use AI Copilot | Yes (own scope) | No | No |
| Run What-If | Yes (own scope) | No | No |
| View own recommendations | Yes | No | No |
| Request advisor approval | Yes | No | No |
| Review approval requests | No | Yes | Yes |
| View audit trail | Own only | Yes | Yes |
| Workflow summary | No | Yes | Yes |

### Server-side controls

- `X-Demo-Role` is validated against an explicit allow-list.
- `X-Demo-Student-Id` scopes Student requests to the selected student record.
- Student requests cannot read another student's academic data.
- Students cannot approve/reject their own requests.
- Advisors/Coordinators cannot use the student Copilot, What-If, or recommendation endpoints.
- The advisor workflow summary is staff-only.
- Audit access is role-aware and student-scoped for Students.

> Limitation: this remains a capstone **demo authentication model**, not production identity authentication. The next hardening step should replace demo headers with a real authenticated session/token and server-side identity.
