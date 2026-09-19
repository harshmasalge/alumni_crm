# IITGN Alumni & Donor CRM — Data Dictionary

**Status:** Baseline for M1 schema design  
**Source:** IITGN Alumni/Donor CRM RFP Sections 6–7 and approved operational requirements  
**Rule:** This is the field-level implementation baseline. New persisted fields require an RFP reference, business-owner decision, or ADR.

## Conventions

All entity keys are UUIDs; Roll Number and Donor ID are unique business identifiers, never foreign keys. Dates are ISO dates, timestamps are UTC, and monetary values are fixed-precision decimals. `M1` means required for the first real registry release; `Later` means accepted but intentionally deferred. Restricted fields never appear in ordinary list/search/export responses.

## Constituent and person identity

### `constituents`

| Field | Type | Delivery | Rule |
| --- | --- | --- | --- |
| `id` | UUID | M1 | Internal, immutable primary key. |
| `kind` | enum | M1 | `PERSON` or `ORGANISATION`. |
| `status` | enum | M1 | `ACTIVE`, `DECEASED`, `LOST_CONTACT`, `OPTED_OUT`, `ARCHIVED`; RFP F-003. |
| `member_types` | relationship | M1 | Alumni, donor, student, faculty, staff, friend; roles are not mutually exclusive. |
| `display_name` / `normalised_display_name` | text | M1 | Display plus case/accent-insensitive name search. |
| `notes` | text | M1 | Internal-only; RFP F-032. |
| `profile_completeness_percent` | small integer | M1 | Calculated 0–100; RFP F-030. |
| `last_substantive_profile_update_at` | timestamp | M1 | Calculated freshness basis; see definition below. |

### `people`

| Field | Type | Delivery | RFP / sensitivity |
| --- | --- | --- | --- |
| `constituent_id` | UUID FK | M1 | One-to-one person identity. |
| `first_name`, `full_name` | text | M1 | RFP F-002. |
| `gender` | enum, nullable | M1 | RFP F-005; restricted in broad exports. |
| `date_of_birth` | date, nullable | M1 | RFP F-006; restricted; birthday automation uses month/day only. |
| `blood_group` | enum, nullable | Later | RFP F-007; restricted health information. |
| `spouse_name` | text, nullable | Later | RFP F-029; restricted. |
| `profile_photo_file_id` | UUID, nullable | Later | RFP F-031; object-storage reference only. |

### `organisations`

| Field | Type | Delivery | Rule |
| --- | --- | --- | --- |
| `constituent_id` | UUID FK | M1 | One-to-one organisation identity. |
| `legal_name`, `normalised_name` | text | M1 | Employer/CSR donor; normalized field supports Google-style search. |
| `sector` | lookup | M1 | Controlled sector taxonomy. |
| `website_url` | URL, nullable | Later | For employers/startups. |

## Alumni, donor, contact, and consent

### `alumni_profiles`

| Field | Type | Delivery | RFP / validation |
| --- | --- | --- | --- |
| `constituent_id` | UUID FK | M1 | Alumni person. |
| `roll_no` | text | M1 | F-001; normalized unique identifier; controlled correction only. |
| `iitgn_email` | email, nullable | M1 | F-017; normalized unique where present. |
| `programme_id`, `discipline_id` | UUID FK | M1 | F-008/F-009; lookup values from IITGN. |
| `year_of_graduation` | small integer | M1 | F-010; four-digit graduation year. |
| `final_cpi` | decimal(4,2), nullable | M1 | F-012; 0–10; restricted academic value. |
| `course_codes` | relation | Later | F-011; never a delimited string. |
| `jee_air`, `gate_air`, `jam_air`, `csir_net_rank` | integer, nullable | Later | F-013; restricted. |
| `thesis_title`, `thesis_defence_date` | text/date, nullable | Later | F-014/F-016. |
| `thesis_supervisor_id`, `thesis_co_supervisor_id` | UUID FK, nullable | Later | F-015. |
| association-membership fields | relationship | Later | F-027; model separately from profile. |

### `donor_profiles`

| Field | Type | Delivery | Rule |
| --- | --- | --- | --- |
| `constituent_id` | UUID FK | M1 | Person or organisation donor. |
| `donor_id` | text | M1 | Unique business identifier. |
| `pan_encrypted`, `pan_last_four` | encrypted text/text | M2 | F-025; finance-only, masked by default. |
| `aadhaar_encrypted` | encrypted text | Not scheduled | F-026; disabled until purpose/access/retention approved. |
| batch gift pledge fields | pledge relation | M2 | F-028; belongs in pledges, not profile columns. |

### `contact_methods`, `addresses`, `communication_preferences`

| Entity | M1 fields | RFP / rule |
| --- | --- | --- |
| `contact_methods` | constituent, type, value, normalized value, primary, verified, WhatsApp linked, active | F-017–F-022: IITGN/personal/work email, two phones, LinkedIn, Instagram. Preserve replaced contacts as history. |
| `addresses` | constituent, type, lines, city, state, country, postal code, active | F-023/F-024: current/permanent. Current country/city is filterable. |
| `communication_preferences` | email/WhatsApp/SMS opt-in, global DNC, consent source, consent time | COM-011/012 and PRT-008. DNC overrides all providers. |
| `family_members` | name, relationship, contact data | T25; Later and restricted third-party information. |

## Education and post-IITGN learning history

### `education_records`

This M1 entity retains every known qualification, including education completed after IITGN graduation.

| Field | Type | Rule |
| --- | --- | --- |
| `id`, `constituent_id` | UUID | Primary key and alumni owner. |
| `education_stage` | enum | `PRE_IITGN`, `IITGN`, `POST_IITGN`. |
| `qualification`, `institution_name`, `board_or_university` | text | RFP T2. |
| `field_of_study` | text, nullable | Programme/discipline where known. |
| `start_year`, `completion_year` | small integer, nullable | Validate ordering. |
| `grade_or_cgpa`, `remarks` | text, nullable | Preserve original academic scale; do not force conversion. |
| `is_verified` | boolean | Claimed history is distinct from confirmed history. |

### Academic entities deferred after M1

| Entity | RFP | Key fields |
| --- | --- | --- |
| `hostel_history` | T4 | hostel, room, academic year, semester. |
| `academic_courses` | T5/T8/T10 | programme level, course, credits, year, semester, instructor, grade. |
| `semester_performance` | T6/T9/T11 | programme level, year, semester, SPI/CPI. |
| `gps_assignments` | T7 | year, semester, coordinator. |
| `awards_recognition` | T12 | type, date, agency, detail. |
| `scholarships_financial_aid` | T13 | type, name, year, amount, remarks. |
| `internships`, `placements` | T14/T15 | organisation, location, dates, funding/CTC as applicable. |
| `positions_of_responsibility`, `publications`, `overseas_exposure` | T18/T21/T23 | Domain fields as specified in the RFP. |
| `ssac_records` | T17 | Restricted; separate policy/approval required. |

## Career and organisation associations

### `affiliations`

One table represents all current and past employment. A new current job closes the previous current record; no history is overwritten or moved between tables.

| Field | Type | Delivery | Rule |
| --- | --- | --- | --- |
| `id`, `constituent_id` | UUID | M1 | Affiliation and alumnus owner. |
| `organisation_id` | UUID FK, nullable | M1 | Normalised employer record where resolved. |
| `organisation_name_raw` | text, nullable | M1 | Preserve imported/unmatched employer text. |
| `affiliation_type` | enum | M1 | `PRIVATE`, `GOVERNMENT`, `ACADEMIC`, `STARTUP`, `OTHER`; T19. |
| `sector`, `designation` | lookup/text | M1 | Search/filter fields. |
| `city`, `state`, `country` | text/lookup | M1 | T19. |
| `start_date`, `end_date` | date, nullable | M1 | End cannot precede start. |
| `is_current` | boolean | M1 | One current employment affiliation unless approved exception. |
| `date_precision` | enum | M1 | `DAY`, `MONTH`, `YEAR`, `UNKNOWN`; never invent dates from imports. |
| `source`, `verified_at` | enum/timestamp | M1 | Staff, portal, import, verified source. |

**Organisation-search rule:** searching “Google” joins all affiliation history to normalised organisations and returns each alumnus once with a computed label: `Current`, `Past`, or `Current and past`. The 360° profile displays the entire matching timeline and dates.

## Fundraising (M2)

Staff-operated only per ADR-004: no alumni self-donation flow, no online
collection. Staff enter donations received through outside channels and
use the module for receipts/80G, pledge tracking, and giving analysis.

| Entity | Required fields / rules |
| --- | --- |
| `funds`, `campaigns` | name, purpose, active dates/status, finance owner. |
| `pledges` | donor, fund/campaign, amount, expected fulfilment date, status/reminders. Batch gift pledges surface per-profile with amount and fulfilment status. |
| `donations` | donor, received date, automatic Indian FY, amount/currency, purpose, payment mode/reference, FCRA status, lifecycle state, remarks. Staff-entered; no donor-facing capture. |
| `donation_allocations` | donation-to-fund amounts reconcile exactly to donation total. |
| `payment_transactions` | Deferred: online collection is out of scope (ADR-004). Reconciliation-only use would need a new decision. Never raw card credentials. |
| `receipts`, `tax_certificates` | immutable numbers/status/document reference; 80G needs approved finance process. PAN (masked, finance-only) supports receipt issuance. |
| `association_memberships` | member (constituent), Yes/No status, membership amount, membership date; RFP F-027. Modelled separately from the profile; surfaced in the 360° profile. |

### Donation history in the 360° profile (M2 data, profile display)

- Full donation history table (received date, amount, fund/purpose, receipt status).
- Computed totals: lifetime giving and giving in the past 1 year (rolling 365 days), calculated on read like `days_since_profile_update` — never persisted counters.
- Pledge line (batch gift pledge amount + fulfilment status) and association-membership line where present.

## Engagement, communications, portal, files, governance

| Entity | RFP / key fields | Delivery |
| --- | --- | --- |
| `events`, `event_registrations`, `event_attendance`, `engagements` | Event code/type, RSVP, guests, check-in, interaction type/date/notes | M4 |
| `chapters`, `chapter_memberships`, mentorship entities | city/country, leads/members; mentor expertise, matches/sessions | M4/Later |
| `communication_logs`, templates, campaign recipients | channel, outcome, staff, consent eligibility, delivery status | M4/M6 |
| `portal_accounts` | constituent, identity-provider subject, status, last login; no external credentials | M5 |
| `files` | entity owner, storage key, original name, MIME type, size, scan/classification | M1 foundation |
| `users`, `roles`, `permissions`, `user_roles` | Server-enforced RBAC; never UI-only role checks | M1 |
| `audit_events` | actor, IP/request metadata, entity, action, before/after, timestamp; append-only | M1 |
| migration/quality entities | import batch, staging row, validation, duplicate candidate, merge event | M3 |

## 360° profile field catalogue (owner-confirmed 2026-09-18)

Every alumnus profile must present these fields, each subject to the
viewer's field permissions. Storage and delivery follow the sections above.

| Profile field | Storage | Delivery / notes |
| --- | --- | --- |
| Roll No (unique, immutable) | `alumni_profiles.roll_no`, normalized unique | M1, live |
| Full Name + First Name | `people.full_name`, `people.first_name` | M1, live |
| Status | `constituents.status` (`ACTIVE`, `DECEASED`, `LOST_CONTACT`, `OPTED_OUT`, `ARCHIVED`) | M1, live |
| Member Type | `member_types` relationship (alumni, donor, student, faculty, staff, friend; non-exclusive) | M1 spec; **gap: association not yet implemented (enum only)** — flagged for stakeholder review |
| Gender | `people.gender`, restricted in broad exports | M1, live (field-permission gated) |
| Date of Birth | `people.date_of_birth`, restricted; birthday workflows use month/day only | M1, live (field-permission gated) |
| Blood Group | `people.blood_group`, restricted health information | M1, live (field-permission gated) |
| Programme | `alumni_profiles.programme_id` → lookup | M1 spec; **gap: lookup values + display names pending** (field-freeze item 1) |
| Discipline | `alumni_profiles.discipline_id` → lookup | M1 spec; **gap: lookup values + display names pending** (field-freeze item 1) |
| Year of Graduation | `alumni_profiles.year_of_graduation`, 4-digit, key filter | M1, live |
| Course Codes | relation, never a delimited string (RFP T5/T8/T10) | Deferred academic entity; **gap: not yet modelled** — flagged for review |
| CPI (CGPA, 10-point) | `alumni_profiles.final_cpi`, restricted academic value | M1, live (field-permission gated) |
| JEE / GATE / JAM / CSIR ranks | nullable integer ranks, restricted | M1, live (field-permission gated) |
| Thesis Title / Supervisor(s) / Defence Date | nullable thesis fields | M1, live |
| IITGN / Personal / Work Email | `contact_methods` (history preserved) | M1, live |
| Phone 1 & Phone 2 | `contact_methods` with country code + WhatsApp-linked flag | M1, live |
| LinkedIn / Instagram URL | `contact_methods` link types | M1, live |
| Permanent Address; Current Address + City/State/Country | `addresses` (`PERMANENT` / `CURRENT`), history preserved | M1, live |
| PAN | `donor_profiles.pan_last_four` (masked) + encrypted full value, finance-only | M2 with ledger (80G receipts) |
| Aadhaar | Disabled until purpose/access/retention approved | Not scheduled |
| Alumni Association Membership | `association_memberships` (status, amount, date) | M2 model; surfaced in profile |
| Batch Gift Pledge | `pledges` (amount + fulfilment status) | M2; surfaced in profile |
| Spouse Name | `people.spouse_name`, restricted third-party-adjacent data | M1 stored; exposure policy per field-freeze item 5 |
| Profile Score (%) | `constituents.profile_completeness_percent`, calculated 0–100 | M1, live; weights per field-freeze item 2 |
| Photo | object-storage reference only, never in PostgreSQL | Deferred; support multiple images when modelled |
| Notes | `constituents.notes`, internal-only | M1, live (internal permission) |
| Donation history + totals | M2 ledger (see above) | M2; lifetime + past-1-year computed on read |

## Related entity tables T2–T25 (owner-confirmed 2026-09-18)

Every table below is a child record of the alumni profile, linked by
`constituent_id` UUID (never by Roll Number). History is append-only:
new rows never overwrite or move prior rows.

| Code | Entity / table | Key fields & purpose | Delivery |
| --- | --- | --- | --- |
| T2 | `education_records` | Qualification, years, school/college, board/university, CGPA, remarks (SSC/HSC/graduation + post-IITGN) | M1, live |
| T3 | Donations ledger | FY (Apr–Mar), date, amount INR/USD, purpose, payment mode, receipt no., 80G status, remarks | M2 (on hold); profile totals spec above |
| T4 | `hostel_history` | Hostel name, room number, academic year, semester | M1 extension (this slice) |
| T5/T8/T10 | `academic_courses` | Course code, name, credits, year, semester, instructor, grade; `programme_level` UG/PG/PHD distinguishes the three | M1 extension (this slice) |
| T6/T9/T11 | `semester_performance` | Semester-wise SPI and CPI per programme level | M1 extension (this slice) |
| T7 | `gps_assignments` | Year, semester, GPS coordinator | M1 extension (this slice) |
| T12 | `awards_recognition` | Type (Dean's List/Medal/Award/Recognition), date, agency, details, academic year/semester | M1 extension (this slice) |
| T13 | `scholarships_financial_aid` | Type, name, year, amount, remarks | M1 extension (this slice) |
| T14 | `internships` | Domestic/international, online/offline, duration, organisation, year, funding source + amount | M1 extension (this slice) |
| T15 | `placements` | Domestic/international, company, sector, city/state/country, CTC, date of joining | M1 extension (this slice) |
| T16 | `startups` | Startup name, type, incubator, founders, year, team size, sector, location, website | M1 extension (this slice) |
| T17 | `ssac_records` | Incident details, sanction-letter date, PDF attachment reference | Restricted: separate policy/approval required; `ssac.read_restricted` (admin role only). Never in list/search/export responses |
| T18 | `positions_of_responsibility` | Position title, domain (Council/Club/Event), academic year | M1 extension (this slice) |
| T19/T20 | `affiliations` | Current + auto-archived previous employment with month-year precision | M1, live |
| T21 | `publications` | Title, DOI, date, PDF attachment reference | M1 extension (this slice) |
| T22 | Meetups & engagements | Type (Homecoming/Campus Visit/Chapter Meet/Webinar/Other), year, date, accompanying persons, remarks | M4 (engagement workspace) |
| T23 | `overseas_exposure` | Organisation, year, duration from-to, funding details + amount | M1 extension (this slice) |
| T24 | Communication logs | Date, channel, staff, purpose, status, remarks | M6 (consent-aware campaigns) |
| T25 | `family_members` | Name, relationship, contact, email (third-party PII) | Restricted via `people.read_family`; never in list/search/export responses |

File attachments (T17/T21 PDFs, photos) are object-storage references only,
never byte columns in PostgreSQL. This slice delivers model + migration +
360° read path + UI for the M1-extension rows; per-record write endpoints
beyond education/affiliations are follow-up work.

## Profile freshness definition

The home-screen stale-profile count is an authoritative backend query:

```text
active alumni
AND last_substantive_profile_update_at < current_date - 365 days
AND status is not DECEASED or ARCHIVED
```

A substantive update is an approved profile, contact, address, education, or affiliation change. Reads, exports, login, audit creation, and background jobs never reset freshness. The dashboard card and its click-through people list use exactly the same filter specification.

## M1 field freeze decisions

Before the first Alembic migration, confirm:

1. IITGN programme and discipline lookup values.
2. Profile-completeness field weights.
3. Which edits require approval before resetting profile freshness.
4. Whether a person may have multiple concurrent affiliations and under which circumstances.
5. Access/data-owner policy for final CPI, date of birth, personal contacts, and legacy academic records.

No external provider credential blocks M1 schema work.

## M1.1 Phase A — segmentation extensions (2026-09-19, ADR-005)

Additive; M1 semantics unchanged. Tenures are derived at query time, never stored.

| Table | New field | Rule |
| --- | --- | --- |
| `people` | `last_name` (text, nullable) | Excel column the M1 seed ignored; new seeds populate it. |
| `affiliations` | `function` (text, nullable) | Structured role family; staff vocabulary, advisory. |
| `affiliations` | `seniority_level` (text, nullable) | Structured seniority; staff vocabulary, advisory. |
| `organisations` | `company_type` (text, nullable) | Master data; seeded vocabulary mirrors `AffiliationType`. |
| `organisations` | `hq_city`, `hq_state`, `hq_country` (text, nullable) | HQ master data; affiliation locations carry recall meanwhile. |

### `taxonomies` (new)

Staff-managed categorical values: `category` + `value` + `normalised_value`
(unique together) + `is_active` (soft-deactivation over deletion).
Categories: `industry` (44 values seeded from observed sectors),
`company_type` (5), `function` / `seniority_level` (empty by design — no
structured source; staff populate). Values are advisory, never FK-enforced.

### Filter fields → storage

Current/past company and job titles → affiliation history (`is_current`
split, raw or resolved names). Company type → `affiliation_type` or org
`company_type`. HQ → affiliation city/state/country or org HQ fields.
Function/seniority → affiliation columns. Geography → current affiliation or
current address city/state/country. Industry → affiliation `sector`. Names →
`people`. Experience/tenures → derived from `start_date`. School →
`education_records.institution_name`. `groups` is reserved for Phase B.

## M1.1 Phase B1 — groups domain (2026-09-19, ADR-006, backend only)

| Table | Key design |
| --- | --- |
| `groups` | name (unique), description, type `MANUAL/RULE_BASED`, status `ACTIVE/DEACTIVATED`, created_by. No hard delete. |
| `group_memberships` | Current-state rows; `UNIQUE(group_id, constituent_id)`; removal deletes the row (audited). |
| `group_rule_versions` | Append-only `filter_tree` JSON snapshots; `PENDING/ACTIVE/SUPERSEDED/REJECTED`; at most one ACTIVE and one PENDING per group (partial unique indexes). |
| `group_membership_proposals` | Version-bound deltas (`ADD/REMOVE`) with stored reason summary + per-leaf reason detail, `evaluated_by`/`reviewed_by`, `applied_at`; `PENDING/APPROVED/REJECTED`. |

Populations are explicit-ID lists or re-evaluated filter definitions (never
stale browser counts). Attention states (pending rule/proposals) are derived,
not stored. New `groups.*` permissions: read/create/update/manage_members/
manage_rules/approve/deactivate.

## M1.1 Phase C — export (2026-09-20, ADR-007, no schema change)

Exports are stateless (no tables). The exportable column registry in
`app/services/exports.py` derives from the 360° profile response models:
singleton sections flatten all scalar fields (legacy curated keys keep
stable labels), list sections contribute counts plus joined per-field
columns. Aadhaar, ciphertext blobs, files/photos/audit, and technical
identifiers are excluded by rule; everything else exports subject to the
caller's field permissions (SSAC/family additionally whole-section
gated). Populations: validated ID lists, re-evaluated M1 + filter
definitions, or server-side group membership. New `constituents.export`
permission (admin + staff).
