.PHONY: dev down build migrate makemigration test test-api test-api-slow test-web lint lint-api lint-web typecheck typecheck-api typecheck-web e2e logs shell-api shell-web

dev:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

migrate:
	docker compose run --rm api alembic upgrade head

makemigration:
	docker compose run --rm api alembic revision --autogenerate -m "$(m)"

test: test-api test-web

test-api:
	docker compose run --rm api pytest

# Runs tests marked "slow": real PDF parsing + real BGE-M3 embedding
# inference. First run downloads the ~2GB model from Hugging Face.
test-api-slow:
	docker compose run --rm api pytest -m slow

test-web:
	docker compose run --rm web pnpm test -- --run

lint: lint-api lint-web

lint-api:
	docker compose run --rm api ruff check .

lint-web:
	docker compose run --rm web pnpm lint

typecheck: typecheck-api typecheck-web

typecheck-api:
	docker compose run --rm api mypy app

typecheck-web:
	docker compose run --rm web pnpm typecheck

e2e:
	docker compose run --rm web pnpm e2e

logs:
	docker compose logs -f

shell-api:
	docker compose exec api bash

shell-web:
	docker compose exec web sh
