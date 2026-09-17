# IITGN Alumni & Donor CRM — Implementation Status

**Last updated:** 2026-09-18  
**Active checkpoint:** M1 — Persistent alumni/donor registry, 360° profile, affiliations, permissions, audit  
**Overall status:** M0 complete; M1 in progress

## What works today

- Product requirements, architecture, and staged delivery approach have been reviewed and documented.
- The repository now has a professional monorepo layout and agent entry points.
- The internal CRM frontend workspace contains the first professional, data-oriented preview shell (M0 complete).
- The CRM frontend passes `npm run check:crm` (TypeScript type check plus production Vite build).
- The RFP field catalogue is represented by the baseline [data dictionary](docs/data/DATA_DICTIONARY.md), including M1 fields and deferred entities.
- FastAPI modular monolith scaffolded with M1 domain models (constituents, people, alumni_profiles, education_records, affiliations, organisations, contact_methods, addresses, communication_preferences, files, audit_events, users, roles, permissions).
- Alembic initial migration created for M1 schema.
- API routes implemented: constituent search (name/roll_no), 360° profile, stale profiles count/list, organisation search across current/past affiliations.
- Docker Compose for local PostgreSQL, Redis, API, and CRM-web.

## Under development

- PostgreSQL database and migration execution (requires `docker-compose up`).
- CRM frontend People module wired to real API (replacing preview).
- Server-side RBAC, field-level permissions, and audit middleware.

M1's fixed functional scope is documented in [docs/checkpoints/M1.md](docs/checkpoints/M1.md): full profile lookup by Roll No./name, preserved education and job history, profile-freshness tracking with a >365-day dashboard drill-down, and current/past organisation search. M1 schema work must follow the [data dictionary](docs/data/DATA_DICTIONARY.md).

## Not started by design

- IITGN SSO/network allowlist, WhatsApp/SMS/email, payment gateway, ERP, Power BI, and LinkedIn integrations.
- Any use of real alumni/donor data or production credentials.
- Alumni portal, communications, AI search, job board, and predictive analytics.

## Active acceptance criteria

See [docs/checkpoints/M1.md](docs/checkpoints/M1.md). M1 is complete when PostgreSQL migrations exist, exact Roll Number and partial-name search work through API and UI, 360° profile opens from search results, education/job history are append/preserve workflows, freshness calculation and >365-day dashboard count work, clicking stale-profile count opens filtered list, organisation search finds current/past affiliations with status labels, permissions and audit tests cover profile changes and restricted fields.

## Next smallest useful task

Run `npm run docker:up` to start PostgreSQL and Redis, then `npm run db:migrate` to apply the M1 schema. Verify API at `http://localhost:8000/docs`. Then wire CRM frontend People module to `/api/v1/constituents` endpoints.

## Change log

| Date | Change |
| --- | --- |
| 2026-09-17 | Created curated monorepo scaffold, agent entry points, M0 frontend shell, and documentation structure. |
| 2026-09-17 | Installed frontend dependencies and verified `npm run check:crm`; local browser visual QA remains pending. |
| 2026-09-17 | Added an RFP-traceable field-level data dictionary and M1 field-freeze decisions. |
| 2026-09-18 | Completed M0: CRM shell launches locally (`npm run dev:crm`), responsive at desktop/tablet/mobile, `Live`/`Preview`/`Under development` labels visible, fictional demo data labelled, lint/type checks pass. |
| 2026-09-18 | Scaffolded M1 FastAPI/PostgreSQL people-registry: domain models, Alembic migration, API routes (search, 360° profile, stale profiles, organisation search), Docker Compose. |
