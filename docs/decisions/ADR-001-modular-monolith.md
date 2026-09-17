# ADR-001: Use a modular monolith

**Status:** Accepted  
**Date:** 2026-09-17

## Context

The CRM must support several domains and future integrations, but early usage is approximately 20–50 concurrent internal users and an alumni population that can grow to 200,000 records.

## Decision

Build a FastAPI modular monolith with explicit domain boundaries. Use PostgreSQL as the primary database, Redis for background work/cache, and object storage for documents. Split into independently deployed services only when an evidenced operational bottleneck requires it.

## Consequences

The system is simpler to develop, test, deploy, and explain while retaining a clear route to future extraction. Modules must not bypass each other’s public services or query private tables directly.
