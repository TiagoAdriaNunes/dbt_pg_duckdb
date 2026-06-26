.PHONY: up down clean logs dbt-deps dbt-run dbt-test dbt-snapshot lint lint-sql help all duckdb-cli tpch-init simulate-new-data dbt-docs-generate dbt-docs-serve pre-commit-install benchmark

all: up dbt-deps tpch-init dbt-run dbt-test lint lint-sql

up:
	@docker info > /dev/null 2>&1 || (echo "Docker daemon is not running. Start Docker Desktop and retry."; exit 1)
	docker compose up db -d --wait

help:
	@echo "make all         run everything (up + deps + tpch-init + seed + run + test + lint)"
	@echo "make up          start DB and wait until healthy"
	@echo "make down        stop containers and remove volumes"
	@echo "make dbt-deps    install dbt packages"
	@echo "make dbt-run     run all models"
	@echo "make dbt-test     run schema tests"
	@echo "make dbt-snapshot run SCD2 snapshots"
	@echo "make lint        ruff check + format check"
	@echo "make lint-sql    sqlfluff lint on all dbt SQL models and macros"
	@echo "make duckdb-cli  open DuckDB shell with pg attached as 'pg'"
	@echo "make tpch-init          load TPC-H benchmark data into raw schema (idempotent)"
	@echo "make simulate-new-data  insert 1000 new lineitem rows with ship_date=today"
	@echo "make benchmark          run TPC-H Q1/Q3/Q5 under Postgres vs DuckDB engine"
	@echo "make dbt-docs-generate  generate docs catalog (no server)"
	@echo "make dbt-docs-serve     generate docs and open at http://localhost:8080"

down:
	docker compose down -v

clean:
	docker compose down -v --rmi all

logs:
	docker compose logs db -f

dbt-deps:
	cd dbt && uv run dbt deps --profiles-dir .

dbt-run:
	cd dbt && uv run dbt run --profiles-dir .

dbt-test:
	cd dbt && uv run dbt test --profiles-dir .

dbt-snapshot:
	cd dbt && uv run dbt snapshot --profiles-dir .

lint:
	uv run ruff check .
	uv run ruff format --check .

lint-sql:
	uv run sqlfluff lint dbt/models dbt/macros

pre-commit-install:
	uv run pre-commit install

duckdb-cli:
	./scripts/duckdb_cli.sh

tpch-init:
	uv run python scripts/init_tpch.py

simulate-new-data:
	uv run python scripts/simulate_new_data.py

benchmark:
	uv run python scripts/benchmark.py

dbt-docs-generate:
	cd dbt && uv run dbt docs generate --profiles-dir .

dbt-docs-serve: dbt-docs-generate
	cd dbt && uv run dbt docs serve --profiles-dir . --port 8080
