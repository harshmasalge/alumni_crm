# ADR-007 — Permission-Aware Export (M1.1 Phase C)

**Status:** Accepted 2026-09-20
**Scope:** Phase C implementation. Phase D (final validation) may revisit.

## Context

People and Groups need Excel export of server-side populations without
becoming a restricted-data bypass. Current scale is thousands of rows;
async job infrastructure would be premature.

## Decisions

1. **Sync-first XLSX.** `POST /exports/people` generates the workbook
   in-request (openpyxl, already pinned). The contract (population +
   columns → file) is worker-compatible: a future async evolution keeps
   the same request shape behind request → job → download. A 5000-row
   single-request cap keeps sync generation bounded; larger needs narrow
   via filters.
2. **Populations re-evaluated, never supplied.** Explicit IDs are
   validated (ghosts dropped, reported in audit); filters + M1 criteria
   re-run through the same intersection as People search; group members
   read server-side (requires `groups.read` in addition to the export
   permission). No row data is ever accepted from the client.
3. **Columns intersected, fail-closed — and dynamic.** The registry
   derives from the `Profile360Response` models at import: singleton
   sections flatten every scalar field, list sections contribute a count
   plus `|`-joined per-field columns, all routed through the unchanged
   `FieldPermissionChecker` (drop/mask identical to profile reads).
   A field added to the 360° profile is automatically exportable under
   the same permission checks — no export code change needed. Unknown
   columns are 422. Whole-section gates mirror the profile route
   (`ssac.read_restricted`, `people.read_family`); Aadhaar, ciphertext
   blobs, files/photos/audit, and technical identifiers are excluded
   from the registry by rule, never merely gated.
   Sensitive-by-design data (notes, PAN, SSAC, family) is excluded from
   the exportable registry entirely, not merely gated.
4. **Dedicated permission.** `constituents.export` (admin + staff only;
   viewer/finance excluded — bulk PII extraction outranks single reads).
   Follows the existing seed + migration-grant convention.
5. **Audit metadata only.** `EXPORT_PEOPLE` rows carry population
   summary, requested/allowed/dropped columns, row/invalid counts —
   never exported values or IDs.
6. **No new tables.** Exports are stateless; no migration beyond the
   permission row.

## Consequences

- People and Group detail share one export dialog and one endpoint.
- Phase D verifies the full M1.1 surface; a future milestone may add
  async jobs, scheduled exports, or finance-module exports without
  changing these contracts.
