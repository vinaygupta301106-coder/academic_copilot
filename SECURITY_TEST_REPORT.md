# Phase 5 — Security Test Report

## System

Policy-Aware Academic Pathway Copilot with Knowledge Graph and What-If Simulation

## Test date

Fill in during final execution.

## Automated test command

```bat
py -m pytest -q
```

## Results

| Test category | Result | Evidence |
|---|---|---|
| Prompt injection | PASS / FAIL | pytest + UI screenshot |
| Sensitive-data protection | PASS / FAIL | pytest + UI screenshot |
| Input length validation | PASS / FAIL | pytest |
| Signed-session integrity | PASS / FAIL | pytest |
| Session expiry | PASS / FAIL | pytest |
| Role tampering | PASS / FAIL | pytest |
| Student scope isolation | PASS / FAIL | pytest + API response |
| Role permission matrix | PASS / FAIL | pytest + UI screenshot |
| Human approval boundary | PASS / FAIL | advisor workflow + audit trail |
| Academic truth/provenance boundary | PASS / FAIL | Copilot source indicator |

## Acceptance criteria

A category is considered passing only when the expected security control is enforced server-side and the result can be reproduced.

Do not mark a manual test as PASS until it has been executed against the running application.

## Known limitation

The prototype uses signed demo sessions rather than production authentication. This is documented as a capstone prototype limitation and should not be described as production identity/security.
