# Phase 4 — Signed Session Authorization

This phase replaces trust in client-supplied role headers with a server-issued, HMAC-signed demo session token.

## Security boundary
- FastAPI issues a short-lived bearer token from `/api/v1/auth/demo-session`.
- Protected endpoints require `Authorization: Bearer <token>`.
- The server verifies token integrity, expiry, role, and student scope.
- Existing `X-Demo-Role` / `X-Demo-Student-Id` values must match the signed session when present.
- This is stronger than a UI-only role selector, but it is still a demonstration authentication model, not production identity management.

## Human approval boundary
Students may create approval requests; only Advisor/Coordinator sessions may make decisions.

## Production gap
For deployment, replace demo-session issuance with institutional SSO/OIDC or another real identity provider and keep authorization checks server-side.
