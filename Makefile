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
	uv run --locked pyrefly check

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
