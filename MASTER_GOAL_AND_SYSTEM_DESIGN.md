# IITGN Alumni & Donor CRM — Master Goal and System Design

## Product goal

Deliver an open-source, institution-owned CRM that gives IITGN one trusted, secure record of alumni and donors; supports fundraising, engagement, reporting, and self-service; and can grow from approximately 6,000 records to 200,000 without replacing the core architecture.

The RFP is the source of functional intent. [initial system design.md](initial%20system%20design.md) is the detailed original architecture reference. This file is deliberately concise: it is the fastest reliable entry point for a new contributor or coding agent. The field-level implementation baseline is [docs/data/DATA_DICTIONARY.md](docs/data/DATA_DICTIONARY.md).

## Current delivery rule

Build **vertical, demonstrable slices**. Every completed checkpoint must leave behind a usable screen and durable backend capability. Never postpone all visible work until after the backend is “finished”.

## Target architecture

```text
Internal CRM / Alumni Portal
             │
             ▼
FastAPI modular monolith
  identity | constituents | fundraising | engagement
  communications | reporting/imports | integrations
             │
             ▼
PostgreSQL | Redis jobs | Object storage
```

- Internal CRM: React + TypeScript + Vite.
- Alumni portal: separate frontend with a limited `/me` API; later release.
- API: FastAPI, SQLAlchemy, Alembic, Pydantic.
- Data: PostgreSQL is the source of truth; object storage is for files; Redis supports jobs/cache.
- Deployment: Docker locally; production cloud and provider choices require IITGN approval.
- Reporting: product reporting views first; Metabase/Power BI adapters later.

## Domain model rules

- `constituent_id` UUID is the stable relational key.
- Roll Number and Donor ID are unique business identifiers, never cross-table foreign keys.
- A constituent may be an alumnus, individual donor, organisation donor, or more than one of these.
- Current and previous affiliations use one time-bound affiliation history model; records are never physically moved between tables.
- Every alumnus has a searchable 360° profile. A search by exact Roll Number or name opens the entire profile, subject only to the viewer's field permissions.
- Post-IITGN education and career history are time-bound records. The model must preserve every known qualification and job switch rather than overwriting prior employers or education.
- Each profile exposes a calculated `days_since_profile_update` based on the last substantive, approved profile-data change. System-only reads, exports, and background jobs do not reset it.
- Organisation search is history-aware. Searching an organisation such as Google returns every associated alumnus and clearly labels each affiliation as `Current` or `Past`.
- Posted financial transactions are immutable. Use adjustment/reversal records rather than destructive edits.
- Files are stored outside PostgreSQL with metadata, authorisation, and audit links.

## Security rules

- Server-side authorisation is mandatory; frontend hiding is never a security control.
- RBAC, module permissions, field-level restrictions, and object-level portal permissions are required.
- Every sensitive change is audited with actor, time, IP/request identifier, previous state, and new state.
- PAN is masked by default. Aadhaar and similarly high-risk fields remain disabled until IITGN approves purpose, access, and retention policies.
- “IITGN Wi-Fi only” is a production gateway/network policy after IITGN supplies approved network ranges. It must not block safe local development.
- A bootstrap administrator is not the production recovery model; production requires at least two controlled break-glass administrators.

## Integration rule

External systems are adapter interfaces, not product dependencies:

```text
Mock provider now → IITGN-approved provider later
```

This applies to identity, email, WhatsApp, SMS, payment, ERP, donation portal, and analytics. The UI must accurately label `Sandbox`, `Connected`, `Unavailable`, or `Under development`; no mock result may appear to be real.

## Release order

| Checkpoint | Durable outcome |
| --- | --- |
| M0 | Professional CRM preview shell, local stack, feature states, seeded demo data |
| M1 | Persistent alumni/donor registry, 360° profile, affiliations, permissions, audit |
| M2 | Donation ledger, pledges, funds, sample 80G workflow |
| M3 | Staged import/migration workbench and standard reporting |
| M4 | Events, attendance, chapters, engagement and staff queues |
| M5 | Restricted alumni self-service portal |
| M6 | Compliant campaigns and automation with mock/in-app delivery |
| M7 | IITGN-controlled integrations and production hardening |

Nice-to-have work (job board, startup showcase, predictive analytics) cannot delay M0–M7.

## Explicit operational behaviours

1. **Person lookup:** staff can search by Roll Number or name and reach the complete alumni profile from the result. Name search supports partial matching; Roll Number uses exact matching as the primary path.
2. **History, not replacement:** after IITGN graduation, new qualifications and employer changes create dated history records. The current job is the active affiliation; past jobs remain queryable.
3. **Profile freshness:** the home screen displays the count of alumni whose profiles have had no substantive update for more than 365 days. Selecting that count opens the corresponding filtered people list.
4. **Organisation relationship search:** an organisation search includes both present and former associations, with a visible status and dates where available. A person associated with Google twice still appears once in a roll-up result, with the profile showing the complete timeline.

## Definition of done

A feature is complete only when it has a visible workflow, database/API implementation, validation, server-side authorisation, audit behaviour, automated tests, safe demo data, documentation, and a demo/rollback path where applicable.
