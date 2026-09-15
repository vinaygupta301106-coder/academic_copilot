# Phase 7 — Baseline & Evaluation

## Purpose
This phase evaluates whether Academic Pathway Copilot improves the academic-pathway workflow compared with a manual baseline.

This is an evaluation plan and evidence framework. No performance numbers are fabricated; measured timings and outcomes must be recorded from the user's actual demonstration/testing environment.

## Baseline: manual academic-pathway process
A student/adviser manually:
1. Finds the course in the curriculum/catalog.
2. Checks prerequisite rules.
3. Checks the student's completed courses.
4. Determines eligibility.
5. Explores consequences of taking/skipping a course.
6. Chooses a possible next course.
7. Sends an exception/approval request to an adviser when needed.
8. Records or retrieves the final decision and its history.

## Proposed workflow
Academic Copilot combines:
- MySQL student records and enrollment/completion state.
- Neo4j curriculum and prerequisite relationships.
- Deterministic eligibility and pathway rules.
- What-If simulation without modifying the real record.
- Recommendation dashboard with transparent reasons.
- AI explanation using verified context.
- Advisor approval workflow and audit trail.
- Source provenance for traceable academic facts.

## Evaluation scenarios

| ID | Scenario | Manual baseline | Copilot capability | Evidence to capture |
|---|---|---|---|---|
| E1 | Check eligibility for a course | Student/adviser checks prerequisites and record manually | Deterministic eligibility result | Result + provenance |
| E2 | Identify missing prerequisites | Manually compare completed courses with prerequisites | Shows missing prerequisites | Course/prerequisite evidence |
| E3 | Simulate taking a course | Manually reason about downstream effects | What-If simulation | Baseline vs simulated pathway |
| E4 | Simulate skipping a prerequisite/course | Manually reason about blocked courses | What-If simulation | Newly locked/blocked courses |
| E5 | Choose a next course | Adviser/student manually compares eligible options | Ranked recommendation dashboard | Recommendation reasons |
| E6 | Request exception/approval | Email/manual adviser process | Structured approval request | Request + decision + audit entry |
| E7 | Explain an academic decision | Adviser explains from records | Copilot explains verified context | Answer + source IDs |
| E8 | Review previous decisions | Search manual records | Audit trail | Audit screen |

## Evaluation dimensions

### Correctness
Does the system reach the same eligibility/pathway conclusion that follows from the configured curriculum and student record?

### Traceability
Can the user identify the MySQL/Neo4j evidence behind an academic claim?

### Efficiency
Can the same scenario be completed with fewer manual lookup/reasoning steps?

### Safety and governance
Does the system prevent unauthorized access, unsupported claims, prompt injection, and AI-only approval of governed decisions?

### Reproducibility
Does the same student state and curriculum state produce the same deterministic eligibility/What-If/recommendation result?

### Human control
Are approval/exception decisions kept with Advisor/Coordinator roles rather than the LLM?

## Measurement sheet
Record actual results during the final demonstration instead of inventing values.

| Scenario | Manual steps/time | Copilot steps/time | Correct? | Evidence shown? | Notes |
|---|---|---|---|---|---|
| E1 | TBD | TBD | TBD | TBD | |
| E2 | TBD | TBD | TBD | TBD | |
| E3 | TBD | TBD | TBD | TBD | |
| E4 | TBD | TBD | TBD | TBD | |
| E5 | TBD | TBD | TBD | TBD | |
| E6 | TBD | TBD | TBD | TBD | |
| E7 | TBD | TBD | TBD | TBD | |
| E8 | TBD | TBD | TBD | TBD | |

## Expected evaluation claim
The capstone should claim improvement only where the collected evidence supports it. A safe conclusion is that Academic Copilot centralizes prerequisite checking, pathway simulation, recommendations, governed approval, provenance, and auditability in one workflow. Quantitative time/accuracy improvements should be reported only after measurement.


### Finalized Enrollment Governance Behavior
The final evaluation build uses an approval-first enrollment workflow. The existing `Enroll` action creates an advisor/coordinator approval request; no student enrollment is persisted until an authorized Advisor or Coordinator approves the request. Approved requests create an `enrolled` record and an audit event. Staff can remove enrolled or completed records from Student Academic Overview with a required reason, and those changes are audited.
