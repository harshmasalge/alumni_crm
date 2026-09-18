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
- Git repository initialized with `.gitignore` for Node, Python, IDE, Docker, OS artifacts.
- Python virtual environment setup via `npm run install:api` (creates `.venv` in apps/api).
- API dependencies pinned in `apps/api/requirements.txt` (generated from `pyproject.toml`).
- Development automation: `Makefile` (Unix) and `scripts/dev.ps1` (Windows PowerShell).
- **CRM frontend People module wired to real API**: search by name/roll_no, paginated results, 360° profile with all tabs (identity, alumni profile, contact methods, addresses, education history, career history, audit trail).

## Under development

- PostgreSQL database and migration execution (requires `docker-compose up`).
- Server-side RBAC, field-level permissions, and audit middleware.

M1's fixed functional scope is documented in [docs/checkpoints/M1.md](docs/checkpoints/M1.md): full profile lookup by Roll No./name, preserved education and job history, profile-freshness tracking with a >365-day dashboard drill-down, and current/past organisation search. M1 schema work must follow the [data dictionary](docs/data/DATA_DICTIONARY.md).

## Not started by design

- IITGN SSO/network allowlist, WhatsApp/SMS/email, payment gateway, ERP, Power BI, and LinkedIn integrations.
- Any use of real alumni/donor data or production credentials.
- Alumni portal, communications, AI search, job board, and predictive analytics.

## Active acceptance criteria

See [docs/checkpoints/M1.md](docs/checkpoints/M1.md). M1 is complete when PostgreSQL migrations exist, exact Roll Number and partial-name search work through API and UI, 360° profile opens from search results, education/job history are append/preserve workflows, freshness calculation and >365-day dashboard count work, clicking stale-profile count opens filtered list, organisation search finds current/past affiliations with status labels, permissions and audit tests cover profile changes and restricted fields.

## Next smallest useful task

Run `npm run docker:up` to start PostgreSQL and Redis, then `npm run db:migrate` to apply the M1 schema. Verify API at `http://localhost:8000/docs` and CRM at `http://localhost:5173`. Test People search → 360° profile flow end-to-end.

## Change log

| Date | Change |
| --- | --- |
| 2026-09-17 | Created curated monorepo scaffold, agent entry points, M0 frontend shell, and documentation structure. |
| 2026-09-17 | Installed frontend dependencies and verified `npm run check:crm`; local browser visual QA remains pending. |
| 2026-09-17 | Added an RFP-traceable field-level data dictionary and M1 field-freeze decisions. |
| 2026-09-18 | Completed M0: CRM shell launches locally (`npm run dev:crm`), responsive at desktop/tablet/mobile, `Live`/`Preview`/`Under development` labels visible, fictional demo data labelled, lint/type checks pass. |
| 2026-09-18 | Scaffolded M1 FastAPI/PostgreSQL people-registry: domain models, Alembic migration, API routes (search, 360° profile, stale profiles, organisation search), Docker Compose. |
| 2026-09-18 | Added git `.gitignore`, Python virtual environment setup, `requirements.txt`, `Makefile`, and `scripts/dev.ps1` for cross-platform dev automation. |
| 2026-09-18 | Wired CRM frontend People module to real API: search (name/roll_no), paginated results, 360° profile with all tabs; TypeScript/build passes. |

---

## Phase 2 — Full CRM Frontend Visualization (Session 2, `feat/frontend-visualization`)

**Status:** Complete — `npm run check:crm` passes (tsc + Vite build, 24 modules). All fixtures fictional.

### Modules visualized (all Preview / Under development; never Live)

- **Fundraising (Preview, M2 scope)** — dashboard KPIs, donations ledger with donation-detail panel, pledges with progress bars, funds table, campaigns with goal bars, 80G workflow states, analytics.
- **Imports (Preview, M3 scope)** — workspace with mock drop zone, column-mapping table, validation results, duplicate-candidate review with keep/merge preview notices, import history.
- **Reports (Preview, M3 scope)** — KPI dashboard, standard-report catalogue (constituent/donation/engagement/compliance) with category filter, export controls with guardrails.
- **Engagement (Under development, M4 scope)** — dashboard, event list + event detail (registration/attendance/participants/performance), chapters table with health + ownership, staff queues with queue filter, engagement timeline.
- **Communications (Under development, M6 scope)** — dashboard, campaign pipeline with channel filter, audience segments with eligible/DNC-excluded counts, templates, mock delivery history. DNC-blocked sends shown explicitly.
- **Integrations (Under development, M7 scope)** — dashboard counts, provider registry (Sandbox/Connected/Unavailable/Under development), mock configuration detail, mock logs.
- **Administration (Under development, M1/M7 scope)** — users & roles (fictional people), module/field permission matrix, audit-log excerpt, system config (lookups, guardrails).

### Routes/pages added

- New files under `apps/crm-web/src/preview/` (no M1 changes): `demoData.ts`, `ui.tsx`, `Fundraising.tsx`, `ImportsReports.tsx`, `Engagement.tsx`, `Communications.tsx`, `IntegrationsAdmin.tsx`.
- Navigation extended additively: existing 7 items preserved verbatim; `Imports` (Preview) and `Administration` (Under development) appended. Existing M1 modules now render full previews instead of the generic placeholder.
- `App.tsx` diff limited to: preview imports, `export` on `StatusBadge`, two nav items, render branching. `Overview`, `People`, `ProfileDetail`, `ModulePreview`, `Metric` untouched. No changes to `src/api.ts`, `src/styles.css`, `package.json`, or `apps/api/**`.

### Status model and demo-data approach

- Live = M0 shell + M1 People/API only. Everything new is labelled Preview or Under development with per-screen banners naming the backend capability required (M2/M3/M4/M6/M7).
- Preview actions (record/post/export/register/check-in/send/merge) open explanatory notices; nothing executes, no fake endpoints, no real money/messages/receipts.
- All demo records fictional and internally consistent (donors, funds, campaigns, events, chapters, tasks, batches); `DEMO DATA` sidebar label retained.

### Validation performed

- `npm run check:crm` passes (tsc --noEmit + vite build).
- Verified `Overview`, `People`, `ProfileDetail`, `ModulePreview`, `Metric` still present and unmodified in `App.tsx`; M1 API contracts untouched.
- Layouts reuse existing tokens/classes (`panel`, `metric-grid`, `two-column`, `table-wrap`, `note`) so the 920px/680px responsive rules apply.

### Known future work

- Bind each preview to its real backend per checkpoint (M2 ledger → M7 adapters); replace fixtures tab by tab.
- Add pagination, loading/error states, and server-driven filters when real endpoints land.
- Alumni portal (M5) intentionally not visualized — separate frontend with limited `/me` API.
