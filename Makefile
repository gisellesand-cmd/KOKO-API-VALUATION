.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help dev dev-down dev-clean build test test-local lint format typecheck \
	migrate migrate-new migrate-down seed shell psql redis-cli \
	logs logs-prod logs-scrapers \
	deploy deploy-api deploy-scrapers ssh secrets-list backup clean

help: ## Show this help
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\nTargets:\n"} /^[a-zA-Z_-]+:.*## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

dev: ## Start local stack (api + postgres + redis + scrapers) and tail api logs
	docker compose up -d
	docker compose logs -f api

dev-down: ## Stop local stack
	docker compose down

dev-clean: ## Stop local stack and remove volumes (destructive)
	docker compose down -v

build: ## Build docker images
	docker compose build

test: ## Run tests inside docker
	docker compose run --rm api pytest -v

test-local: ## Run tests against local venv (needs running postgres/redis)
	pytest -v

lint: ## Run ruff check + format check
	ruff check . && ruff format --check .

format: ## Auto-format and fix lint issues
	ruff format . && ruff check --fix .

typecheck: ## Run mypy on api, scrapers, db
	mypy api scrapers db

migrate: ## Apply pending Alembic migrations
	docker compose run --rm api alembic upgrade head

migrate-new: ## Create new Alembic revision (requires MSG="...")
ifndef MSG
	$(error MSG is required. Usage: make migrate-new MSG="add new column")
endif
	docker compose run --rm api alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Revert last Alembic revision
	docker compose run --rm api alembic downgrade -1

seed: ## Load reference data (catalogs, initial FX)
	docker compose run --rm api bash infra/seed.sh

shell: ## Open a bash shell inside the api container
	docker compose exec api bash

psql: ## Open psql against local postgres
	docker compose exec postgres psql -U koko -d koko_mls

redis-cli: ## Open redis-cli against local redis
	docker compose exec redis redis-cli

logs: ## Tail local api logs
	docker compose logs -f api

logs-prod: ## Tail Fly logs for the API app
	flyctl logs --app koko-valuation-api

logs-scrapers: ## Tail Fly logs for the scrapers app
	flyctl logs --app koko-valuation-scrapers

deploy: ## Deploy API + scrapers to Fly
	flyctl deploy --remote-only --config fly.toml --app koko-valuation-api && \
	flyctl deploy --remote-only --config fly-scrapers.toml --app koko-valuation-scrapers

deploy-api: ## Deploy only the API app to Fly
	flyctl deploy --remote-only --config fly.toml --app koko-valuation-api

deploy-scrapers: ## Deploy only the scrapers app to Fly
	flyctl deploy --remote-only --config fly-scrapers.toml --app koko-valuation-scrapers

ssh: ## SSH into the API Fly machine
	flyctl ssh console --app koko-valuation-api

secrets-list: ## List Fly secrets for the API app
	flyctl secrets list --app koko-valuation-api

backup: ## Run an ad-hoc Postgres backup to S3
	bash infra/backup.sh

clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + ; \
	find . -type d -name .pytest_cache -exec rm -rf {} + ; \
	rm -rf .mypy_cache .ruff_cache htmlcov .coverage dist build *.egg-info
