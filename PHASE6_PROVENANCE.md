# Phase 6 — Source Provenance & Traceable Academic Decisions

## Goal
Academic decisions must be traceable to verified backend evidence rather than being attributed to the language model.

## Evidence model
- `KG-COURSE-CATALOG` — Neo4j course catalog facts.
- `KG-PREREQUISITES` — Neo4j prerequisite relationships.
- `MYSQL-STUDENT-RECORD` — MySQL student profile and completion status.
- `LLM-SYNTHESIS` — Ollama/Qwen natural-language synthesis only; non-authoritative.

Every Copilot chat response now returns a `provenance` object with evidence IDs, course codes used, and student scope. What-If and recommendation responses also return provenance.

## Governance rule
Neo4j/MySQL are authoritative for university-specific academic facts. The LLM may explain verified context but cannot create policy, prerequisite, eligibility, credit, or student-record facts.
