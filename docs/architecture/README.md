# Architecture Documentation

This directory holds durable explanations of how the running system is organised. Keep product intent in the root master-goal file and irreversible decisions in `docs/decisions/`.

Current system boundary: the React CRM is a client of the FastAPI modular monolith. PostgreSQL is authoritative; files and background jobs are separate concerns. Each domain module owns its service and persistence boundary.
