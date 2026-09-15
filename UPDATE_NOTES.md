# Academic Copilot — Phase 3 refinement

## Changes in this build
- Fixed Recommendation Dashboard action overflow by using a responsive 2-column action grid.
- Removed the unused top notification button.
- Moved the AI Academic Advisor from the permanent right column into a floating/minimizable panel.
- Added an `Ask AI Advisor` launcher near the footer for Student view.
- Copilot Chat navigation now opens the floating advisor panel.
- Added role-aware Student vs Advisor/Coordinator screen separation.
- Advisor/Coordinator views hide student-only dashboard, recommendation, course intelligence and Copilot content.
- Advisor/Coordinator views retain Advisor Approval & Audit Trail and add a Student Academic Overview selector.
- Added student academic snapshot: semester, credits, completed courses, eligible courses, locked courses.
- Added working Advisor Review modal with Approve / Reject / Request Changes actions.
- Advisor request lists load automatically on startup and refresh silently every 8 seconds for staff demo roles.
- Added explicit role-switch reload so switching Student/Advisor/Coordinator immediately rebuilds the correct view.
- Kept Student approval history visible, including request status and reviewer information.
- Fixed the student creation backend to match the simplified form: track is always AI & Data Science and no subjects are accepted.

## Preserved
- Neo4j curriculum and prerequisite logic
- MySQL student/enrollment persistence
- What-If Simulation
- Recommendation Dashboard
- Ollama + Qwen 0.5B
- 15-question daily AI limit
- Student approval workflow and audit log

Keep the user's existing `backend/.env`; it is intentionally not included in the ZIP.


## Phase 4 — Security, Governance & Traceability
- Added backend AI safety inspection for prompt injection, secrets/credentials, and input length.
- Added security headers and request IDs.
- Added Copilot source/provenance metadata and UI rendering.
- Added demo RBAC header consistency checks for advisor workflow.
- Added automated security tests under backend/tests/.
- Added PHASE4_SECURITY_GOVERNANCE.md.
