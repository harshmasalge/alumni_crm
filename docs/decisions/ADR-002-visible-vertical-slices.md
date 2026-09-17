# ADR-002: Deliver visible vertical slices from the first checkpoint

**Status:** Accepted  
**Date:** 2026-09-17

## Context

Non-technical stakeholders need regular evidence of progress. A backend-first plan delays useful feedback and makes a project appear stalled.

## Decision

Every checkpoint delivers a professional frontend workflow backed by the appropriate layer of real implementation. When a dependency is unavailable, the UI must show a clearly labelled preview or under-development state rather than a false simulation.

## Consequences

The frontend shell and design system begin in M0. Later delivery follows vertical slices with API, data, security, test, documentation, and demo criteria.
