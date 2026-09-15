# Phase 7 Update Notes

## Added
- `PHASE7_BASELINE_EVALUATION.md` — baseline/manual process, proposed workflow, evaluation dimensions, scenarios, and measurement sheet.
- `EVALUATION_TEST_CASES.md` — end-to-end demonstration and acceptance test cases.

## Governance note
No benchmark numbers are invented. Timing, correctness, and outcome measurements are marked TBD until they are observed in the user's actual environment.

## Scope
Phase 7 focuses on evaluation evidence rather than adding new product features. Existing What-If, recommendation, advisor workflow, audit, RBAC, security, provenance, and CI/CD capabilities remain unchanged.


## Enrollment Governance Update
- Existing Student `Enroll` buttons are approval-gated; they create a pending advisor request instead of directly writing an enrollment record.
- Advisor/Coordinator approval revalidates prerequisites and creates an `enrolled` course record only after approval.
- Student audit now distinguishes `completed` from `enrolled`. Enrolled courses do not count as completed prerequisites.
- Advisor/Coordinator Student Academic Overview now exposes enrolled records with Remove and completed records with Adjust/remove controls.
- Academic record changes require a reason and are written to the audit trail.
- Added enrollment-governance regression tests.
