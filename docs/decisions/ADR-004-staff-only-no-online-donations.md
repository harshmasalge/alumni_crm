# ADR-004: Staff-only internal CRM; no alumni self-donation flow

**Status:** Accepted  
**Date:** 2026-09-18

## Context

The CRM serves IITGN's Alumni Relations and Advancement staff. Alumni will
not donate through this system, so there is no online collection flow to
build, secure, or comply-operate (no checkout, no donor-facing payment
pages, no donor login for giving).

## Decision

1. The CRM is entirely internal for staff. Every page sits behind staff
   sign-in (Google in production per ADR-003); there is no anonymous or
   alumni-facing surface in this system.
2. Fundraising is staff data entry plus analysis only: staff record
   donations received through outside channels, issue/manage receipts and
   80G certificates, track pledges and funds, and analyze giving (including
   per-profile lifetime and past-1-year totals).
3. No payment-gateway online-collection integration is in scope. If a
   gateway is ever needed purely for reconciling offline receipts, that is
   a new decision, not covered here.

## Consequences

- M2 scope narrows to ledger, pledges, funds, receipts/80G, and
  giving analysis — all staff-operated. Online-payment entities
  (`payment_transactions` for live collection) stay deferred.
- The 360° profile carries a donation-history section (totals + pledge
  and association-membership lines) sourced from M2 data.
- M5 (alumni self-service portal) as currently defined needs explicit
  re-scoping before any work begins; it is not approved by this ADR.
