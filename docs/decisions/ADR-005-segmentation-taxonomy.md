# ADR-005 — People Segmentation Model and Staff-Managed Taxonomies (M1.1 Phase A)

**Status:** Accepted 2026-09-19
**Scope:** M1.1 Phase A only. Groups (Phase B) and export (Phase C) reuse this
filter representation but are not decided here.

## Context

M1.1 requires advanced People filtering across company, role, and personal
dimensions. The Excel source (4,101 rows, profiled 2026-09-19) carries rich
free-text employment data (1,206 distinct organisations, 658 designations, 47
raw sectors, 387 cities, 38 countries) but **no** structured function,
seniority, company-type, or HQ columns. The M1 schema stores employment as
time-bound affiliation history and education as dated records.

## Decisions

1. **No flattened columns.** Current/past company and job titles resolve
   through the existing affiliation history (`is_current` split); school
   resolves through `education_records`; tenures derive from `start_date` at
   query time and are never persisted. Small additive columns only where no
   representation exists: `people.last_name` (Excel has the column; M1 seed
   ignored it), `affiliations.function` / `seniority_level`, and
   `organisations.company_type` / `hq_city` / `hq_state` / `hq_country`.
2. **Generic filter tree, server-side.** `FilterGroup {op, conditions}` with
   `FilterCondition {field, operator, value/values}`; validated and compiled
   to correlated EXISTS subqueries (`app/services/segmentation.py`). A person
   with N affiliations still matches once. The frontend builds the tree only.
   Depth ≤ 3, ≤ 50 leaves; invalid definitions are 422, the Phase B reserved
   `groups` field is a clear 400 (never silently ignored).
3. **POST `/constituents/search`.** GET search keeps exact M1 semantics; the
   POST body accepts the filter tree plus the M1 criteria (`q`, `roll_no`,
   `organisation_q`, `stale_threshold_days`), combined as a server-side
   intersection. The field/operator registry is served via
   `GET /constituents/search/fields` so UI and backend cannot drift.
4. **One advisory taxonomy table.** `taxonomies(category, value,
   normalised_value, is_active)` serves every controlled list. Values are
   advisory, never FK-enforced, so vocabulary edits cannot invalidate
   constituent rows. Referenced values cannot be hard-deleted (409 with usage
   count); soft-deactivation is always allowed. Seeded from real data:
   `industry` ← 44 de-duplicated sectors observed in the Excel;
   `company_type` ← the established `AffiliationType` vocabulary.
   `function` / `seniority_level` start **empty** — inventing them from
   generic CRM conventions was explicitly rejected; staff populate them.
5. **No new permissions in Phase A.** Taxonomy/org-master reads use
   `constituents.read`, writes use `constituents.write` (existing named
   dependencies). Group/export permissions are a Phase B/C decision.
6. **Known approximations (documented, not hidden).**
   - `years_in_current_position` equals company tenure until a
     position-history model lands; both derive from current-affiliation
     `start_date`. Tenure cutoffs use 365.25 days/year.
   - `company_hq` matches affiliation city/state/country **or** resolved-org
     HQ fields; resolved-org matching against raw affiliation text is M3
     import-workbench scope — until then the affiliation fallback carries
     real-data recall.
   - Existing rows keep NULL `last_name`/`function`/`seniority_level` (no
     heuristic backfill); `is_empty`/`is_not_empty` operators query absence.

## Consequences

- Phase B reuses the filter tree for rule-based group rules and persists it
  (saved-search shape already compatible); governance/approval is new work.
- Phase C reuses the population query for export; field-level export
  allow-lists are new work.
- Organisation master-data write surface is API-only in Phase A
  (`PATCH /organisations/{id}`); a staff UI for it is deferred and recorded
  in the M1.1 checkpoint as a known limitation.
