# IITGN Alumni & Donor CRM

An open-source, modular CRM for IIT Gandhinagar's Alumni Relations Office and Institute Advancement Office. It will replace fragmented spreadsheets with an auditable people registry, donation ledger, engagement workspace, reporting, and an alumni portal.

## Start here

Read these files in order:

1. [MASTER_GOAL_AND_SYSTEM_DESIGN.md](MASTER_GOAL_AND_SYSTEM_DESIGN.md) — enduring product intent, architecture, constraints, and non-negotiable decisions.
2. [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) — current checkpoint, what works, what is under development, and the next smallest useful task.
3. [docs/checkpoints/M0.md](docs/checkpoints/M0.md) — acceptance criteria for the active release.
4. [AGENTS.md](AGENTS.md) — working agreement for people and coding agents.

## Repository map

```text
apps/
  crm-web/              Internal CRM frontend (React + TypeScript)
  alumni-portal/        Alumni self-service frontend (later release)
  api/                  FastAPI modular monolith
packages/
  ui/                   Shared design tokens and UI primitives (later)
  contracts/            Shared API/domain contracts (later)
docs/
  architecture/         System boundaries and technical decisions
  checkpoints/          Release acceptance criteria and demo scripts
  decisions/            ADRs: short, irreversible or costly decisions
  runbooks/             Operational and developer procedures
  legacy/               Notes about replaced prototypes/source material
infra/                  Local and production deployment assets
scripts/                Repeatable development and verification tasks
```

## Current state

M0, “Project foundation and product preview”, is in progress. The first deliverable is a professional CRM shell with clearly labelled demo, preview, and under-development states; it is not presented as a live production service.

## Legacy prototypes

`crm html code.txt` and `CRM Codes.txt` are retained as source references only. They are not part of the production runtime. See [docs/legacy/prototype-assessment.md](docs/legacy/prototype-assessment.md).
