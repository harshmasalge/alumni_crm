# IITGN Alumni & Donor CRM — Modular Implementation Plan

## Decision on the initial system design

**Accepted, with targeted changes.** The proposed open-source modular monolith is the right technical shape for this project: React/TypeScript, FastAPI, PostgreSQL, Redis-backed jobs, object storage, and provider adapters. It meets the scale without prematurely creating a microservice estate.

The following decisions are retained:

- `constituent_id` (UUID) is the internal relational key; Roll No. and Donor ID are immutable business identifiers, not foreign keys.
- One backend owns all business rules. The internal CRM and alumni portal are distinct frontend experiences over the same API contracts.
- External providers are replaceable adapters. Mock implementations let the product progress before IITGN provides SMTP, WhatsApp, payment, ERP, or SSO access.
- Long-running work (imports, document generation, campaigns, reporting) runs as jobs, never inside a normal web request.
- Every meaningful data change is auditable and every user-facing feature is permission checked server-side.

The following changes are required:

1. **Frontend-visible progress is a release requirement.** We will not spend weeks on an invisible backend foundation. The first release is a polished, navigable CRM preview with one real vertical slice behind it.
2. **Build vertical slices, not technical layers.** A slice includes a screen, API, database migration, validation, permission check, tests, and audit event. A completed slice can remain usable even if later work is delayed.
3. **Do not represent unavailable integrations as working.** Each external-service feature shows a clear `Under development`, `Sandbox`, `Connected`, or `Unavailable` state. Mock delivery is visibly labelled and never presented as a real WhatsApp/payment transaction.
4. **Do not make a single Master Admin a production single point of failure.** Use a bootstrap admin only for initial setup; production needs two named break-glass administrators, controlled recovery, and logged role changes.
5. **"IITGN Wi-Fi only" is a production gateway policy, not an application assumption.** Local/demo development stays accessible to the delivery team. IITGN IT must supply trusted network ranges before the production allowlist is enabled.
6. **Aadhaar and other highly sensitive fields are not built as ordinary profile inputs.** They remain disabled pending an approved purpose, retention policy, and authorised access model.

## Delivery principle

Every milestone ends with a demo that a non-technical stakeholder can use. No milestone depends on an unimplemented future module to be valuable.

```text
Experience shell → People & profiles → Donations → Migration & reporting
        → Engagement → Portal → Communications → External integrations
```

At every point the CRM should show three types of state:

| State | Meaning in the product |
| --- | --- |
| Live | Persisted data and operational workflow are complete for this release. |
| Preview | UI and representative seed data exist; the feature is intentionally not yet operational. |
| Under development | A planned module with a concise description and no false implication that it works. |

## Product presentation standards

The CRM should feel like institutional software, not an AI-generated dashboard.

- Use a restrained IITGN-inspired visual system: warm off-white page background, charcoal/navy text, one deep saffron/ochre accent, quiet neutral borders, and purposeful status colours.
- Use a real type scale, compact data tables, generous whitespace, readable forms, and accessible focus/empty/error states.
- Avoid decorative gradients, glowing cards, excessive rounded pills, purple/black palettes, emoji UI, fake metrics, and generic stock illustrations.
- Place a small environment label in the header: `Demo data`, `Sandbox`, or `Production`.
- Use realistic but clearly labelled seed records in development; never place personal or donor data in demo environments.

## Architecture boundaries that prevent rework

```text
CRM web app / Alumni portal
             │
             ▼
FastAPI modular monolith
  ├── identity & access
  ├── constituents
  ├── fundraising
  ├── engagement
  ├── communications
  ├── reporting & imports
  └── integrations (interfaces/adapters)
             │
             ▼
PostgreSQL | object storage | Redis/job worker
```

Within each module, separate API routes, application services, repositories, schemas, and migrations. Modules may reference another module only through its public service/API contract; no module reads another module’s private tables directly.

All unfinished integrations are behind feature flags and adapters:

```text
PaymentProvider: MockPaymentProvider now → Razorpay/CCAvenue later
MessageProvider: InApp/Mock now → SMTP/WhatsApp/SMS later
IdentityProvider: local demo now → Google Workspace OIDC later
```

## Delivery roadmap and checkpoints

### M0 — Project foundation and product preview

**Goal:** show a credible working CRM from the beginning while establishing safe engineering foundations.

**Build**

- Application shell: sidebar, top bar, routing, environment label, loading/empty/error states, responsive layout, and design tokens.
- Publicly demonstrable pages: executive dashboard, people list, profile shell, donations list, events list, reports catalogue, and integrations/status centre.
- Seeded, explicitly labelled demo data and a mock API contract. No invented claims of live donation/payment or external messaging.
- Backend health endpoint, PostgreSQL connection, migration tooling, Docker local environment, linting, formatting, and CI checks.
- Initial authentication boundary: development login only; no production identity claim.
- A feature registry powering `Live`, `Preview`, and `Under development` markers.

**Stakeholder demo:** navigate a professional CRM, open a representative alumni 360° profile, filter the people list, and see a clearly sequenced roadmap in the status centre.

**Checkpoint / exit criteria**

- Frontend deploys reproducibly and works at desktop and tablet widths.
- A new developer can run the stack from documented instructions.
- The dashboard and profile use stable API contracts, even if the first dataset is seeded.
- No real personal data, credentials, or external-provider keys are required.

**If delayed:** the product still provides a trustworthy interactive preview and the design system/API contracts remain reusable.

### M1 — Secure people registry and 360° profile

**Goal:** deliver the first operational slice: staff can manage a real alumni/donor registry.

**Build**

- Constituent, person, organisation, alumni-profile, donor-profile, contacts, addresses, affiliations, consent/preferences, and document metadata migrations.
- Alumni and donor list with pagination, sorting, structured filters, and fast search by name, Roll No., email, organisation, and donor ID.
- 360° profile: overview, contact, academic summary, current affiliation, donation summary, activity timeline, and completion score.
- Create/edit profile with server validation; current affiliation changes close the prior affiliation and preserve history.
- Exact Roll Number and partial-name search. Selecting a result opens the complete 360° profile, with restricted fields masked or omitted according to the viewer's permissions.
- Post-IITGN education and career timeline. Every job switch and later qualification is recorded as a dated history record, never overwritten.
- A calculated profile-freshness field: `days_since_profile_update`. It changes only after a substantive approved profile update, not after viewing, exporting, or background processing.
- Homepage action card for `Profiles not updated in more than one year`; its count is derived from the registry and links to the pre-filtered people list.
- Organisation search that returns all present and former associations (for example, a Google search) and labels every result `Current` or `Past`.
- Exact duplicate prevention on Roll No., donor ID, and verified email.
- Initial roles and permissions: bootstrap admin, CRM manager, database manager, donation manager, event manager, report viewer.
- Audit events for create/update/archive and a staff-visible profile activity timeline.

**Stakeholder demo:** add an alumnus, update their employer, see the former affiliation become history, and search/filter the registry immediately.

**Checkpoint / exit criteria**

- This slice is backed by persistent PostgreSQL data, not mock state.
- All profile edits enforce permissions and create audit entries.
- Data export is restricted to authorised roles and initially supports CSV only.
- The profile-freshness home-card count and its filtered-list drill-down reconcile against the same authoritative query.
- Organisation search is based on affiliation history, not only the current employer field.

**Deferred but visible:** photo/document upload, advanced academic records, fuzzy merge, and portal updates are shown as under development rather than dead navigation links.

### M2 — Donation ledger and fundraising workspace

**Goal:** make IITGN’s donation operations demonstrable without waiting for a payment gateway.

**Build**

- Funds, campaigns, gifts/donations, allocations, pledges, payment references, receipt records, donor tiers, purpose tags, and FCRA classification.
- Automatic Indian financial-year assignment, donor statements, financial-year totals, top-donor views, and pledge follow-up queue.
- Manual donation recording with approval states: draft → reviewed → posted → reversed/refunded. Posted transactions are immutable; adjustments are separate records.
- 80G receipt template and sandbox PDF generation with a prominent `Sample / not valid for tax use` watermark until finance approves the template and numbering process.
- Donation acknowledgements delivered to the in-app outbox/mock provider only.

**Stakeholder demo:** record a donation, see it classified by financial year and fund, generate a sample receipt, and view the updated donor profile and funding dashboard.

**Checkpoint / exit criteria**

- No payment-gateway dependency exists for the ledger to work.
- Receipt identifiers, approval events, and reversals are auditable.
- Finance-facing screens restrict sensitive data and mask PAN by default.

### M3 — Migration workbench and operational reporting

**Goal:** replace spreadsheet-only work with a controlled, reviewable import process and useful management reporting.

**Build**

- Import batch, staging row, column mapping, validation issue, duplicate candidate, approval, reconciliation, and rollback metadata.
- CSV/XLSX upload to staging; mapping templates; validation for email, phone, dates, country, programme, and identifiers.
- Review queue for invalid and duplicate rows; downloadable error file; row-count reconciliation.
- Dashboard data comes from reporting views, not hard-coded cards: people counts, profile completeness, donation totals, donor count, recent activity, upcoming events placeholder.
- Standard reports: alumni by programme/YOG/discipline, incomplete profiles, geography, affiliation/sector distribution, FY donation summary, donor statement.
- Role-scoped CSV and PDF exports. Power BI remains an under-development adapter.

**Stakeholder demo:** upload a sample spreadsheet, inspect validation errors and duplicates, approve valid rows, and see the dashboard/report totals update from the imported data.

**Checkpoint / exit criteria**

- Import is staged and reversible; there is no direct spreadsheet-to-production insert path.
- Reports reconcile against operational data on an agreed sample dataset.
- The import workflow can become a stand-alone valuable delivery if later modules are paused.

### M4 — Events, engagement, and work queues

**Goal:** make the CRM useful for relationship management beyond maintaining records.

**Build**

- Events, event types, invitations, RSVP, registrations, attendance, accompanying guests, engagement records, and communication logs.
- Event workspace with attendee list and check-in/attendance actions.
- Chapters and chapter membership; campus-visit request queue.
- Configurable engagement-score rules with transparent explanation, not a black-box score.
- Staff work queues: birthdays today, upcoming work anniversaries, lost-contact follow-up, pledge reminders, and pending profile-review requests.

**Stakeholder demo:** create an event, invite a selected segment in sandbox mode, register/check in attendees, and see engagement history and score change on a profile.

**Checkpoint / exit criteria**

- Events and attendance work with no email/WhatsApp provider.
- Every automated recommendation is visible as a reviewable task before real messages are enabled.

### M5 — Alumni portal: controlled self-service

**Goal:** give alumni a real but deliberately limited self-service experience.

**Build**

- Separate portal frontend and restricted `/me` API surface.
- Development identity mapping; Google/LinkedIn/OIDC only after IITGN confirms credentials and allowed identity flows.
- View/update own approved profile fields, address, contact details, affiliation, photo, and communication preferences.
- Change-request workflow for fields that require staff approval; no portal API accepts arbitrary constituent IDs.
- Event browse/RSVP and donation intent/sandbox checkout.
- Privacy controls for future directory fields.

**Stakeholder demo:** sign in as a seeded alumnus, request an employment update, observe it enter the CRM approval queue, approve it as staff, and see it reflected in the portal.

**Checkpoint / exit criteria**

- Object-level authorisation tests prove that one portal user cannot access another’s record.
- Portal changes are traced to both person and session/user identity.
- Directory, mentoring, jobs, and startup showcase remain clearly marked as later releases.

### M6 — Communications and automations

**Goal:** create compliant messaging workflows before connecting paid channels.

**Build**

- Templates, campaigns, recipient selection, delivery records, communication preferences, global DNC enforcement, and in-app/mock delivery outbox.
- Central eligibility service checks status, consent, channel preference, verified contact, and DNC before every send.
- Scheduled jobs for birthday reminders, work anniversaries, weekly digest, monthly summary, affiliation change notifications, and lost-contact task creation.
- Campaign preview, recipient count, approval, test send, and delivery/audit history.

**Stakeholder demo:** prepare a birthday campaign, preview eligible recipients, demonstrate excluded DNC records, run it through sandbox delivery, and inspect its audit trail.

**Checkpoint / exit criteria**

- Compliance rules are built and tested before SMTP/WhatsApp/SMS is connected.
- A provider outage cannot delete or duplicate communication jobs.

### M7 — Production integrations and hardening

**Goal:** connect IITGN-controlled systems only after the core workflows are accepted.

**Build, subject to IITGN/vendor access**

- Google Workspace/OIDC, approved network allowlist, MFA policy, and production session controls.
- SMTP/Exchange, WhatsApp Business API, SMS gateway, Razorpay/CCAvenue, donation portal webhooks, and ERP adapters.
- Object-storage malware scanning/retention controls, backup/restore rehearsal, monitoring, alerts, VAPT remediation, and disaster-recovery runbook.
- Metabase/Power BI integration through read-only reporting views.

**Stakeholder demo:** an integration status dashboard shows each provider’s environment, health, last synchronisation, and any failure without exposing secrets.

**Checkpoint / exit criteria**

- Each provider is released independently behind a feature flag and has an operational rollback path.
- Production claims (data residency, RPO/RTO, uptime, certification) are documented only after infrastructure and IITGN acceptance prove them.

## Not scheduled until the core is accepted

- Natural-language/AI search: first deliver structured search and saved filters. If added later, it may only produce validated, allow-listed filters; it may not generate unrestricted database queries.
- Automated LinkedIn updates: use staff verification unless approved API rights and terms make automation feasible.
- Job board, startup showcase, predictive donor propensity, and engagement-churn scoring.

## Cross-cutting definition of done

A feature is not complete when its page looks complete. It is complete only when it has:

1. a user-visible workflow and clear status;
2. database migration and validation rules;
3. server-side authorisation and audit behaviour;
4. API contract and error states;
5. automated tests for its business rule and access boundary;
6. realistic seeded demo data or a safe test workflow;
7. a demo script and a known rollback/feature-flag path where applicable.

## Suggested immediate sequence

Start M0 and M1 as overlapping vertical work:

1. Establish the polished CRM shell and feature-status centre.
2. Implement persistent constituents, profiles, and affiliation history behind the already-visible people/profile screens.
3. Add role enforcement and audit events before enabling create/edit actions broadly.
4. Seed representative, fictitious IITGN-like records so stakeholder demos show a coherent product from the first week.
5. Demonstrate M1, collect feedback on profile layout and terminology, then begin the donation slice.

This sequence makes progress visible immediately, keeps the project credible to non-technical stakeholders, and ensures each completed module is independently useful rather than disposable scaffolding.
