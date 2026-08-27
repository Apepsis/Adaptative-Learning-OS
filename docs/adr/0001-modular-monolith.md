# ADR 0001: Modular monolith, not microservices

## Context

The blueprint (section 3.1) targets a personal/small-team learning
platform that must run on a single Windows laptop via Docker Compose, with
a credible path to a small VPS and eventually a managed cloud deployment.
It has many logical domains (identity, sources, curriculum, practice,
mastery, planner, tutor...) that could each become a service.

## Decision

Build a single FastAPI application (`apps/api`) organized as a modular
monolith: each domain is a Python package under `app/modules/<name>/` with
its own `router.py`, `schemas.py`, `service.py`, `repository.py`,
`models.py`, and (where relevant) `policies.py`. All modules share one
PostgreSQL database and one deployable process (plus Celery workers for
async jobs). Cross-module calls go through service functions, never
through HTTP or direct ORM access into another module's tables.

## Alternatives considered

- **Microservices per domain.** Rejected for the MVP: massively higher
  operational cost (service discovery, distributed transactions, N
  deployables) for a single-user/small-team product with no scaling
  pressure yet.
- **Single flat FastAPI app with no module boundaries.** Rejected: would
  make a future extraction (if a module ever needs to scale
  independently) far more expensive, and encourages exactly the
  router-touches-database-directly pattern `CLAUDE.md` forbids.

## Consequences

- Module boundaries are enforced by convention and code review
  (`architect` review focus in `docs/architecture/blueprint.md` section
  45.4), not by network isolation. Discipline matters more than in a
  microservices setup.
- Adding a new module later is cheap: copy the file layout, register its
  router in `app/main.py`, add its models to `app/db/migrations/env.py`'s
  model imports.
- Splitting a module into its own service later is possible without a
  domain rewrite, because the module already owns its own repository and
  service layer — only the transport (in-process call -> HTTP/queue call)
  changes.

## Rollback

If a specific module (most likely `ingestion` or `tutor`, given their
CPU/GPU and latency profiles) needs independent scaling before the rest
of the system does, extract only that module into its own deployable,
keeping the shared Postgres database initially and moving to a
module-owned database only if/when that becomes a bottleneck. This ADR
does not need to be reversed for that — it would be superseded by a new
ADR documenting the specific extraction.
