.PHONY: up down dbt-deps dbt-seed dbt-run dbt-test lint

up:
	docker compose up db -d

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
