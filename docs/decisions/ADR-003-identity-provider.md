# ADR-003: Google-only sign-in in production; password sign-in is dev-only

**Status:** Accepted  
**Date:** 2026-09-18

## Context

The CRM must never store staff passwords in production. All production
sign-ins are Sign in with Google; the backend only checks whether the
verified Google email already has an authorized user row (email allowlist —
no auto-provisioning). The Google OAuth client ID requires IITGN admin
action and is not yet available, while development needs a working sign-in
today with zero external dependencies.

## Decision

- Introduce an identity-provider seam (`app/core/identity.py`):
  `PasswordIdentityProvider` for dev/staging, `GoogleIdentityProvider`
  for production, selected by `IDENTITY_PROVIDER`. Both mint the same
  short-lived session token, so RBAC, field-level permissions, and audit
  are provider-agnostic and unchanged by the swap.
- The password provider refuses to run when `environment == "production"`.
- The Google provider verifies the ID token signature, audience
  (`GOOGLE_CLIENT_ID`), and expiry, requires a verified email, and
  authorizes strictly by existing, active user row. `/auth/google`
  returns 503 until the client ID is configured.
- Seeded password accounts exist for local development only and must
  never be created in production.

## Consequences

- Production deployment is blocked on IITGN supplying the OAuth client ID;
  no code changes are needed beyond setting `IDENTITY_PROVIDER=google`
  and `GOOGLE_CLIENT_ID`.
- A future frontend change replaces the dev sign-in form with the Google
  button; no API, permission, or audit changes are required.
- `google-auth` and `requests` join the API dependencies for token
  verification; `passlib`/`bcrypt` remain dev-only transitive needs of the
  password provider and seed scripts.
