.PHONY: up down dbt-deps dbt-seed dbt-run dbt-test lint help all duckdb-cli tpch-init simulate-new-data dbt-docs-generate dbt-docs-serve

all: up dbt-deps tpch-init dbt-seed dbt-run dbt-test lint

up:
	docker compose up db -d --wait

help:
	@echo "make all         run everything (up + deps + tpch-init + seed + run + test + lint)"
	@echo "make up          start DB and wait until healthy"
	@echo "make down        stop containers and remove volumes"
	@echo "make dbt-deps    install dbt packages"
	@echo "make dbt-seed    load seed CSV files"
	@echo "make dbt-run     run all models"
	@echo "make dbt-test    run schema tests"
	@echo "make lint        ruff check + format check"
	@echo "make duckdb-cli  open DuckDB shell with pg attached as 'pg'"
	@echo "make tpch-init          load TPC-H benchmark data into raw schema (idempotent)"
	@echo "make simulate-new-data  insert 1000 new lineitem rows with ship_date=today"
	@echo "make dbt-docs-generate  generate docs catalog (no server)"
	@echo "make dbt-docs-serve     generate docs and open at http://localhost:8080"

down:
	docker compose down -v

dbt-deps:
	cd dbt && uv run dbt deps --profiles-dir .

dbt-seed:
	cd dbt && uv run dbt seed --profiles-dir .

dbt-run:
	cd dbt && uv run dbt run --profiles-dir .

dbt-test:
	cd dbt && uv run dbt test --profiles-dir .

lint:
	uv run ruff check .
	uv run ruff format --check .

duckdb-cli:
	./scripts/duckdb_cli.sh

tpch-init:
	uv run python scripts/init_tpch.py

simulate-new-data:
	uv run python scripts/simulate_new_data.py

dbt-docs-generate:
	cd dbt && uv run dbt docs generate --profiles-dir .

dbt-docs-serve: dbt-docs-generate
	cd dbt && uv run dbt docs serve --profiles-dir . --port 8080
