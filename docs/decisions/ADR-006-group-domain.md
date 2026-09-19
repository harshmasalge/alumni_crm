# ADR-006 — Groups Domain Foundation (M1.1 Phase B1)

**Status:** Accepted 2026-09-19
**Scope:** B1 backend domain only. B2/B3 UI and Phase C export reuse these
contracts unchanged.

## Context

Phase B needs governed group membership on top of the Phase A filter
language, with per-actor four-eyes separation and no silent automation.
Corrections D–I (idempotency, two stages, self-approval, versioning,
explanations, concurrency) constrain the domain shape.

## Decisions

1. **Current-state membership + uniqueness.** `group_memberships` holds one
   row per member with `UNIQUE(group_id, constituent_id)`. Adds are
   insert-or-skip (race-safe via `ON CONFLICT DO NOTHING` on the apply
   path); removals delete the row. History lives in `audit_events`, not in
   the membership table. Explicit-ID and filtered-population adds share this
   primitive and return `{added, already_members, invalid}` so the future UI
   can explain 262-adds-from-342-matches.
2. **Append-only rule versions.** Statuses `PENDING/ACTIVE/SUPERSEDED/
   REJECTED`; partial unique indexes enforce at most one ACTIVE and one
   PENDING version per group (the approve endpoint flushes the supersede
   before activating, otherwise PostgreSQL rejects the transient double-
   ACTIVE). Trees are stored as JSON snapshots and never mutated.
3. **Two approvals, two endpoints, no collapse.** Rule approval activates
   the version and *auto-runs evaluation*, which only creates PENDING
   proposals. Membership approval applies rows. A separate `evaluate`
   endpoint re-runs the ACTIVE version on demand (data changed); pending
   versions are never evaluated — their impact previews via the existing
   `POST /constituents/search`.
4. **Per-stage four-eyes, no bypass.** Rule: approver ≠ proposer.
   Membership: approver ≠ evaluator (the actor who produced the proposals).
   Requiring both checks at membership time deadlocks two-reviewer teams,
   so the evaluator check binds there; rule-stage separation is enforced at
   rule approval. No superuser/self bypass exists in B1.
5. **Optimistic concurrency by version binding.** Proposals store
   `rule_version_id`; approval applies only while that version is still the
   group's ACTIVE version, else the proposal reports `stale` (never applies
   under the wrong rule). No locking infrastructure.
6. **Stored reason snapshots.** Each proposal carries `reason_summary` +
   per-leaf `reason_detail` JSON (field/operator/expected/actual/matched)
   computed at evaluation; reviewers never reconstruct reasons from mutable
   data.
7. **Re-evaluate, don't trust.** Filtered-population operations
   (`preview`, `materialize`) compile and run the filter at execution time;
   preview never mutates. "Select all on page" is an explicit-ID list —
   there is no page-population type.
8. **Attention is derived.** `needs_review`, pending counts, and active
   version are computed from child rows; `groups.status` stores only
   `ACTIVE/DEACTIVATED`. No hard group delete (deactivation is the
   lifecycle).

## Consequences

- B2 builds list/Manual UI directly on these endpoints; B3 builds
  rule/proposal UI on versions/proposals/evaluate.
- Evaluation cost is per-leaf EXISTS queries per candidate; acceptable
  on-demand at current scale, worker-compatible later (reason schema and
  `evaluated_by` already support it).
- Export (Phase C) can consume `{ids} | {filter} | {group}` populations
  through the same server-side evaluation.
