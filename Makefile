.PHONY: check lint format-check typecheck format check-environment

# Run checks sequentially, including when the caller passes -j.
check: check-environment
	$(MAKE) lint
	$(MAKE) format-check
	$(MAKE) typecheck

check-environment:
	@test -f pyproject.toml -a -f uv.lock || { echo "검증 준비 필요: Python 버전과 개발 의존성을 설정하고 pyproject.toml 및 uv.lock을 생성하세요." >&2; exit 1; }

lint: check-environment
	uv run --locked ruff check .

format-check: check-environment
	uv run --locked ruff format --check .

typecheck: check-environment
	uv run --locked pyrefly check --min-severity warn

format: check-environment
	uv run --locked ruff format .

.PHONY: up down logs ps compose-check smoke check-container

up:
	docker compose up --build --detach --wait --wait-timeout 120

down:
	docker compose down

logs:
	docker compose logs --follow

ps:
	docker compose ps

compose-check:
	docker compose config --quiet

smoke:
	docker compose exec -T api uv run --locked python scripts/smoke.py

check-container:
	docker compose run --build --rm --no-deps api make check

.PHONY: migrate migration-check test test-unit test-container

migrate:
	uv run --locked alembic upgrade head

migration-check:
	uv run --locked alembic check

test-unit:
	uv run --locked pytest tests/unit

test:
	@test "$$POSTGRES_DB" = "mdm_test" || { echo "POSTGRES_DB must be mdm_test" >&2; exit 1; }
	$(MAKE) migrate
	$(MAKE) migration-check
	uv run --locked pytest tests

test-container:
	docker compose --profile test run --build --rm test

.PHONY: test-stop
test-stop:
	docker compose --profile test stop postgres-test
