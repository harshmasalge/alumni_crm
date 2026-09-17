# Working Agreement for Contributors and Coding Agents

## Orientation

Before changing code, read `MASTER_GOAL_AND_SYSTEM_DESIGN.md`, then `IMPLEMENTATION_STATUS.md`, then the active checkpoint in `docs/checkpoints/`.

Treat `initial system design.md` and the RFP PDF as source references. Do not copy their diagrams or prose into code comments. `crm html code.txt` and `CRM Codes.txt` are legacy prototypes, not production code.

## Change discipline

- Work on the active checkpoint unless explicitly asked to reprioritise.
- Prefer a small vertical slice over a broad partial layer.
- Do not introduce an external paid integration to unblock local development; add an interface and clearly labelled mock/sandbox implementation instead.
- Do not use real alumni, donor, financial, or credential data in development/demo fixtures.
- Do not silently change a domain/security decision. Add an ADR under `docs/decisions/` when the decision is costly to reverse.
- Update `IMPLEMENTATION_STATUS.md` and the relevant checkpoint document when a checkpoint changes state.
- Add/adjust tests with behaviour changes. Do not claim a feature is complete without running its relevant verification.

## UX rules

- Institutional, calm, and accessible—not decorative, neon, generic-AI, or dashboard cluttered.
- Use the established design tokens; do not add arbitrary colours, gradients, or UI libraries for a single screen.
- Every unavailable area must say why it is unavailable and what it depends on. Never render a blank dead-end page.

## Security rules

- Enforce permissions in the API, never only in the browser.
- Never log secrets or unmasked sensitive fields.
- Do not implement Aadhaar handling without an explicit approved requirement.
- Treat financial posting, receipt issuance, exports, merge, and role changes as audit-worthy operations.

## Documentation rule

Documentation is part of the deliverable. At the end of a completed checkpoint, update: its checkpoint file, `IMPLEMENTATION_STATUS.md`, relevant runbook/ADR, and the README if the developer start path changed.
