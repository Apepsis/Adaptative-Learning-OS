# Adaptive Learning OS

A personal **Learning Operating System**: a unified platform for ingesting study
material (PDFs, slides, photos of notes, web pages, YouTube videos), turning it
into a searchable, cited knowledge base, structuring it into a concept
curriculum, and — in later phases — practicing against it, tracking mastery,
and adaptively planning study time.

This repository follows the architecture defined in
[`docs/architecture/blueprint.md`](docs/architecture/blueprint.md): a modular
monolith backend, a Next.js frontend, Postgres/pgvector as the single source
of domain truth, and object storage as the source of truth for original
files.

> **Current status:** Phase 0 (repository foundation) + Phase 1 (Source
> Library: upload, storage, status tracking). See
> [`docs/architecture/roadmap.md`](docs/architecture/roadmap.md) for what
> comes next (parsing/RAG, curriculum builder, practice, planner, tutor).

## Why a static site *and* a full backend in the same repo?

GitHub Pages only serves static files — it cannot run the FastAPI backend,
PostgreSQL, Redis, or Celery workers this project needs. So this repo ships
two things:

1. **The real application** (`apps/web`, `apps/api`, `docker-compose.yml`) —
   run it locally with Docker, or deploy it to a host that supports servers
   (Render, Railway, Fly.io, a VPS, etc.).
2. **A static landing page** (`site/`) describing the project, deployed to
   GitHub Pages via [`.github/workflows/pages.yml`](.github/workflows/pages.yml).
   It's documentation/marketing, not the app itself.

## Quickstart (local, Docker)

```bash
cp .env.example .env
make dev
```

This starts Postgres (with pgvector), Redis, MinIO, the FastAPI API, the
Celery worker, and the Next.js web app.

- Web: http://localhost:3000
- API: http://localhost:8000 (docs at `/docs`)
- API health: http://localhost:8000/health/ready
- MinIO console: http://localhost:9001

Apply database migrations (first run, and after any schema change):

```bash
make migrate
```

Run the test suites:

```bash
make test
```

See [`docs/runbooks/windows-local.md`](docs/runbooks/windows-local.md) for
Windows/Docker Desktop specific notes.

## Repository layout

```
apps/web/     Next.js frontend (TypeScript, Tailwind, TanStack Query)
apps/api/     FastAPI backend (modular monolith) + Celery workers
infra/        Dockerfiles and deployment infrastructure
docs/         Architecture, ADRs, runbooks
site/         Static landing page published to GitHub Pages
```

## Architecture rules

The codebase follows the module boundaries and architectural constraints
documented under `docs/architecture`. Routers do not access the database
directly, LLM providers are called through `app/ai/providers`, original files
are kept out of Postgres, every schema change ships an Alembic migration, and
retrieved source content is always treated as untrusted data rather than
instructions.

## License

MIT. See [`LICENSE`](LICENSE).
