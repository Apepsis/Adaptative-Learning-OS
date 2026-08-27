# Running locally on Windows

This project is developed and run via Docker Desktop on Windows. Notes
specific to that setup:

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with
  the WSL2 backend enabled (default on modern installs).
- Git.
- `make` is optional. The `Makefile` targets are thin wrappers around
  `docker compose` commands — if you don't have `make` (it isn't built
  into Windows), either install it via `choco install make` / a WSL
  shell, or just run the underlying `docker compose ...` command shown in
  each target directly from PowerShell or Git Bash.

## Line endings

`.gitattributes` normalizes everything to LF in the repository
(`* text=auto eol=lf`), regardless of your local `core.autocrlf` setting.
This matters because the Dockerfiles and `Makefile` run inside Linux
containers, where a CRLF shebang line or CRLF-indented Makefile recipe can
fail in confusing ways. You don't need to configure anything locally —
Git checks the file out as CRLF on your Windows working copy if your
`core.autocrlf` is `true`, but always stores/transmits LF.

## Ports

`docker-compose.yml` binds Postgres (5432), Redis (6379), and MinIO
(9000/9001) to `127.0.0.1` only, not `0.0.0.0` — they won't be reachable
from other devices on your network, which is intentional for a local dev
database holding personal study material.

If another local service already uses one of these ports (a common
conflict: a separately-installed Postgres on 5432), stop that service or
change the host-side port mapping in `docker-compose.yml`.

## File watching / hot reload

The `api` and `web` services bind-mount `apps/api` and `apps/web` into the
containers so edits on the host are picked up without a rebuild
(`uvicorn --reload` for the API, `next dev` for the web app). On Windows,
file-change notifications through a bind mount can occasionally be slower
or miss events depending on the Docker Desktop file-sharing backend; if
hot reload stops working, restart the affected service:

```bash
docker compose restart api
docker compose restart web
```

## First run

```bash
cp .env.example .env
docker compose up --build
```

**The first `--build` is slow and large as of Phase 2** — the `api` image
now installs `sentence-transformers` (which pulls in PyTorch) for local
BGE-M3 embeddings. Expect several minutes and a few GB just for that
layer. Subsequent builds are cached and fast unless `apps/api/pyproject.toml`
changes. Separately, the **first time a PDF is actually ingested**, the
worker downloads the BGE-M3 model itself (~2GB) from Hugging Face — that
happens once, needs internet access, and is cached under the container's
home directory afterward (add a named volume for it if you want the
download to survive a `docker compose down`).

In a second terminal, once Postgres is healthy:

```bash
docker compose run --rm api alembic upgrade head
```

Then open http://localhost:3000. The home page shows an "API ready" /
"API unreachable" indicator — if it says unreachable, check
`docker compose logs api` first.

## Running tests without `make`

```bash
docker compose run --rm api pytest              # fast, no ML model, no fixtures beyond Postgres/MinIO
docker compose run --rm api pytest -m slow       # real PDF + real BGE-M3 embedding; slow, needs internet on first run
docker compose run --rm web pnpm test -- --run
```
