# IITGN Alumni & Donor CRM — Implementation Status

**Last updated:** 2026-09-20  
**Active checkpoint:** M1.1 — complete (Phases A–D verified)  
**Overall status:** M0 complete; M1 complete (accepted by owner, pending stakeholder review). M1.1 complete — segmentation, governed Groups, permission-aware Excel export, final validation (single-head migrations, suite 51 passed with the known-unrelated profile-photo test deselected, `npm run check:crm` green, 19/19 DB checks). M2 on hold until stakeholder review concludes.

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
- **M1 security complete (Session 1)**: JWT login (`/auth/login`, `/auth/me`), server-side RBAC on all constituent endpoints, field-level restrictions (optional fields withheld, required PII masked as `[restricted]`), audit middleware attributing the actor from the Bearer token without consuming request bodies.
- **M1 append workflows (Session 1)**: `POST /constituents/{id}/education` and `POST /constituents/{id}/affiliations` append dated records, close prior current jobs, refresh `last_substantive_profile_update_at`; `days_since_profile_update` computed on read via `app/services/freshness.py`.
- **M1 UI complete (Session 1)**: staff sign-in panel, stale-profile drill-down (Overview count → filtered People list), stale pagination, organisation search tab with Current/Past labels, freshness display, inline append forms.
- **M1 automated tests (Session 1)**: 26 pytest tests green — security, field permissions, audit helpers, freshness boundaries, identity seam (ADR-003), route registration, live-DB integration (auth incl. Google allowlist, search, profile, stale, org search, append, 403 enforcement) with seed-data restoration.
- **Hash-based routing (Session 1)**: `#/people`, `#/people?stale=1`, `#/people/<id>` deep links; browser back/forward works between list and 360° profile; no new dependencies.

## Under development

- **M1.1 Phase A complete (2026-09-19):** People segmentation on main — generic server-side filter tree (16 fields, nested AND/OR), `POST /constituents/search` intersecting M1 criteria, staff-managed `taxonomies` (44 industries + 5 company types seeded from real data; function/seniority staff-populated), org master-data API, 360°/People UI extensions, audit coverage, 11 new tests green. Detail: [docs/checkpoints/M1.1.md](docs/checkpoints/M1.1.md), [ADR-005](docs/decisions/ADR-005-segmentation-taxonomy.md). **Phases B (Groups), C (Export), D (final validation) await explicit go-ahead.**
- M2 backend (donation ledger, pledges, funds, 80G) remains **on hold pending stakeholder review of M1**. M3 deferred per owner decision (full Excel seeding covers real-data testing of People).
- **Administration page complete (M1 completion, explicitly not M7):** migration `7f3a9c2e41b8` (`users.hashed_password` nullable per ADR-003); admin-gated APIs (`/admin/users` CRUD + role assignment, `/admin/roles` + permission matrix, `/admin/permissions` catalog, `/admin/audit-events` with filters); explicit audit rows for every admin write; last-active-superuser guard; live Administration UI (Users / Roles & permissions / Audit log tabs) replacing the preview; 27 pytest green. System-config lookups stay preview; SSO/network allowlist stay M7.

M1's fixed functional scope is documented in [docs/checkpoints/M1.md](docs/checkpoints/M1.md): full profile lookup by Roll No./name, preserved education and job history, profile-freshness tracking with a >365-day dashboard drill-down, and current/past organisation search. M1 schema work must follow the [data dictionary](docs/data/DATA_DICTIONARY.md).

## Not started by design

- IITGN SSO/network allowlist, WhatsApp/SMS/email, payment gateway, ERP, Power BI, and LinkedIn integrations.
- Any use of real alumni/donor data or production credentials.
- Alumni portal, communications, AI search, job board, and predictive analytics.

## Active acceptance criteria

See [docs/checkpoints/M1.md](docs/checkpoints/M1.md). M1 is complete when PostgreSQL migrations exist, exact Roll Number and partial-name search work through API and UI, 360° profile opens from search results, education/job history are append/preserve workflows, freshness calculation and >365-day dashboard count work, clicking stale-profile count opens filtered list, organisation search finds current/past affiliations with status labels, permissions and audit tests cover profile changes and restricted fields.

## Next smallest useful task

1. Stakeholder review of M1 incl. Administration and related-entity profile sections (demo script: sign in as admin → Administration → users/roles/audit; sign in as staff → People search → 360° profile with academic/career/restricted sections → stale drill-down → append flows).
2. For real-data testing of People, seed the full Excel into dev (`scripts/seed_alumni.py` currently caps at 100 rows) — no M3 work needed for that.

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
| 2026-09-18 | Session 1 M1 completion: JWT/RBAC + field-level masking + audit attribution; append-only education/affiliation endpoints with freshness refresh; `days_since_profile_update` computed on read; sign-in UI, stale drill-down, org-search tab; 20 pytest tests green; `npm run check:crm` passes. |
| 2026-09-18 | ADR-003 identity seam: `PasswordIdentityProvider` (dev-only, refuses production) + `GoogleIdentityProvider` (email allowlist, 503 until `GOOGLE_CLIENT_ID` set); shared session minting; `POST /auth/google`; 26 pytest tests green. |
| 2026-09-18 | M1 accepted by owner (all 9 acceptance criteria verified); hash routing for list/profile deep links + browser back/forward. M2 on hold pending stakeholder review. |
| 2026-09-18 | Started Administration page as M1 completion (owner-approved, explicitly not M7): email-allowlist user management, role/permission APIs, audit viewer, live UI. M3 deferred. |
| 2026-09-18 | Completed Administration page: nullable-password migration, 7 admin endpoints (admin-gated, audited, last-superuser guard), live UI with Users/Roles/Audit tabs, 27 pytest green, `npm run check:crm` green. |
| 2026-09-18 | Administration fixes: shared `AuthPanel` so the page asks for sign-in in place; stale-backend hint on Not Found errors (API server must be restarted to pick up new routes). |
| 2026-09-18 | Login wall: auth state lifted to the App shell — unauthenticated visitors see only the sign-in screen; per-page sign-in duplicates removed from People/Administration; user chip + sign-out in topbar; 401s return to login centrally. |
| 2026-09-18 | Owner-confirmed 360° field catalogue + donation-history spec in data dictionary; ADR-004 (staff-only CRM, no online donations, fundraising = entry + analysis); M2/M5 scope notes in master design; M1 known gaps recorded for review (member_types association, programme/discipline lookups, course codes). |
| 2026-09-18 | Related entities T2–T25 slice complete: 14 child tables + migration, 360° read path with SSAC/family gating (`ssac.read_restricted`, `people.read_family`), seed fixtures, 14 profile panels, 28 pytest green, `npm run check:crm` green. T3 stays M2, T22/T24 stay M4/M6. |
| 2026-09-18 | Staff widened to full read/write except user/role admin (migration `b81f5d3a90c2`); full profile write coverage — PATCH constituent/person/alumni/comms, POST contacts/addresses, generic POST factory for all 14 T-tables (SSAC/family permission-gated, Roll Number immutable); edit/add UI across all profile panels; 29 pytest green. |
| 2026-09-18 | Write controls gated on `constituents.write` in the UI (unauthorized notice on click, form never opens); initials avatar top-right of 360° profile as photo placeholder (file serving pending). |
| 2026-09-18 | Multi-photo support: `profile_photos` table + migration, local object-storage backend, upload/serve/set-primary/delete endpoints (raster-only, 5 MB cap), 112px slideshow with dots/counter, Back button removed (browser history covers navigation). |
| 2026-09-19 | M1.1 Phase A complete: migration `f3a91c4d55e2` (last_name, function/seniority, company_type/HQ, `taxonomies` + 49 seeded values), filter DSL + EXISTS engine, `POST /constituents/search` + taxonomy/org-master APIs, audit events, Advanced Filters + Master Data UI, 360° function/seniority/last-name coverage, 11 segmentation tests green (full suite 40 passed, photo test deselected as unrelated), `npm run check:crm` green. |
| 2026-09-19 | Phase A UI refinement (still Phase A, no Groups/Export): People page is a workspace — segmented People/Organisation tabs, results + collapsible right filter sidebar (COMPANY/ROLE/PERSONAL accordions, active counts, chips, clear-all), action toolbar reserving the Groups/Export mount point, Master Data moved to Administration → Master data (staff `constituents.write` accessible, no new permission system). Backend untouched; suite re-run 40 passed, `npm run check:crm` green (27 modules). |
| 2026-09-19 | M1.1 B1 complete (backend only, no UI): migration `b1a91c4d77e2` (groups, memberships, rule versions, proposals + 7 `groups.*` permissions with admin/staff/viewer grants), 20 group APIs (idempotent membership, preview/materialize, two-stage rule→proposal approvals, self-approval 403s, stale-version 409s, per-leaf reason snapshots), 6 B1 tests green, full suite 46 passed (photo test deselected as unrelated). |
| 2026-09-19 | M1.1 B2 complete (frontend only, no backend changes): Groups nav module (list filters/search, Manual create, Manual detail with Members/Activity/picker/deactivate, read-only rule-based surfacing), People selection (explicit IDs + select-all-matching snapshot) with Add-to-group dialog (live preview confirm, idempotent results). `npm run check:crm` green; backend suite 46 passed. Flagged: B1 preview/materialize need M1 search fields for combined filtered handoffs (fix proposed, awaiting approval). |
| 2026-09-19 | Approved B1/B2 integration fix applied: preview/materialize accept M1 criteria via existing helper (backwards compatible); dialog carries the full People query; parity test proves combined populations match People search before transfer. Suite 47 passed, `npm run check:crm` green. |
| 2026-09-20 | M1.1 B4 (Groups validation) complete: single-head migration chain, B1 tables/enums/indexes present, permission matrix verified (admin/staff 7 groups perms, viewer read-only, finance none), 21 audit actions present, suite 47 passed, `npm run check:crm` green, B3 422 fix owner-verified. Phase B done; Export stays Phase C. |
| 2026-09-20 | M1.1 Phase C complete: `constituents.export` permission (migration `c1a91c4d88e2`, admin/staff only), sync XLSX export with server-side population re-evaluation (IDs/filter+M1/group) and field allow-listing (drop/mask, fail-closed), shared Export dialog on People + Groups, `EXPORT_PEOPLE` metadata audit, 4 export tests green, suite 51 passed, `npm run check:crm` green (29 modules). |
| 2026-09-20 | Export registry made dynamic per review: columns derive from the 360° response models (singletons flat, lists as counts + joined columns), so future profile fields export automatically under existing permission checks; Aadhaar/ciphertext/files/photos/audit excluded by rule. Suite 51 passed, `npm run check:crm` green, no frontend changes needed. |
| 2026-09-20 | M1.1 Phase D complete: final validation — single-head migration chain, suite 51 passed, `npm run check:crm` green, 19/19 DB checks (schema, permission matrix, export holders, taxonomy, audit actions), docs synchronized, requirement-by-requirement audit recorded in M1.1.md. M1.1 closed; no new milestone started. |
| 2026-09-20 | M1.1 B3 complete (frontend only, no backend changes): Rule tab (approved/pending cards, reused filter builder, approve/reject with confirms, re-evaluate, version history), Proposals tab (review with per-leaf evidence, bulk approve/reject with stale/already reporting), pending-review banner + tab badge. `npm run check:crm` green; backend suite 47 passed. |

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
- `App.tsx` at Session 2 commit: preview imports, `export` on `StatusBadge`, two nav items, render branching. `Overview`, `People`, `ProfileDetail`, `ModulePreview`, `Metric` untouched at that commit. No changes to `src/api.ts`, `src/styles.css`, `package.json`, or `apps/api/**` at that commit.
- Session 1 follow-ups on the same branch (uncommitted at Session 2 commit time, still additive to previews): token-aware `src/api.ts`, staff sign-in panel, stale drill-down, org-search tab, append forms, and hash routing (`#/people`, `#/people?stale=1`, `#/people/<id>`). Preview components under `src/preview/` remain unmodified.

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
