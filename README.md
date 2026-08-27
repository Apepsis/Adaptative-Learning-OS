# Adaptive Learning OS

A personal **Learning Operating System**: upload study material (PDFs,
slides, photos of notes), get a searchable, cited knowledge base, a concept
curriculum extracted from it, lessons/flashcards/a study guide generated
from that, grounded chat over your sources, and practice questions with
timing, hints, and error feedback — all from the same domain model.

This repository follows the architecture defined in
[`docs/architecture/blueprint.md`](docs/architecture/blueprint.md): a modular
monolith backend, a Next.js frontend, Postgres/pgvector as the single source
of domain truth, and object storage as the source of truth for original
files.

> **Current status: MVP complete** (blueprint section 43 — Phases 0-6).
> Upload → parse/search → concept graph → lessons/flashcards/study guide →
> grounded chat with citations → practice, end to end. See
> [`docs/architecture/roadmap.md`](docs/architecture/roadmap.md) for what
> was built in each phase and what's next (mastery modeling, FSRS, the
> adaptive planner, olympiad-depth verification, integrations, hardening —
> a distinct second stage, not started).

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
.claude/      Claude Code agents, commands, and project rules
```

## Architecture rules

The non-negotiable rules for this codebase live in [`CLAUDE.md`](CLAUDE.md).
In short: routers never touch the database directly, LLM providers are only
called through `app/ai/providers`, original files never go into Postgres,
every schema change ships an Alembic migration, and retrieved source content
is always treated as untrusted data, never as instructions.

## License

MIT. See [`LICENSE`](LICENSE).
