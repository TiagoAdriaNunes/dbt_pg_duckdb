# dbt + pg_duckdb

[![CI](https://github.com/TiagoAdriaNunes/dbt_pg_duckdb/actions/workflows/ci.yml/badge.svg)](https://github.com/TiagoAdriaNunes/dbt_pg_duckdb/actions/workflows/ci.yml)
[![dbt docs](https://github.com/TiagoAdriaNunes/dbt_pg_duckdb/actions/workflows/dbt-docs.yml/badge.svg)](https://tiagoadrianunes.github.io/dbt_pg_duckdb/)

Dockerized PostgreSQL with the [pg_duckdb](https://github.com/duckdb/pg_duckdb) extension and a dbt project for analytics transformations on TPC-H benchmark data.

**[Data lineage, model contracts, and test results →](https://tiagoadrianunes.github.io/dbt_pg_duckdb/)**

## Stack

| Layer | Tool |
|-------|------|
| Database | `pgduckdb/pgduckdb:18-v1.1.1` — Postgres 18 + DuckDB columnar engine |
| Transformations | [`dbt-postgres`](https://github.com/dbt-labs/dbt-core) |
| Python env | `uv` |
| Python lint | `ruff` |
| SQL lint | `sqlfluff` + dbt templater |
| Git hooks | `pre-commit` |

## Quickstart

```bash
git clone https://github.com/TiagoAdriaNunes/dbt_pg_duckdb.git
cd dbt_pg_duckdb
uv sync
make pre-commit-install  # install git hooks (once)
make all
```

`make all` starts the database, loads TPC-H benchmark data (sf=0.1, ~600k lineitems), runs all dbt models, tests, and linters.

No `.env` file required — everything defaults to zero-config local credentials.

## Commands

```bash
make all                # full pipeline: up + deps + tpch-init + seed + run + test + lint
make up                 # start DB and wait until healthy
make down               # stop containers and remove volumes
make dbt-run            # run all models
make dbt-test           # run schema tests
make dbt-docs-serve     # generate and serve docs at http://localhost:8080
make simulate-new-data  # insert new lineitem rows with ship_date=today (triggers incremental model)
make duckdb-cli         # open DuckDB shell with Postgres attached
make lint               # ruff check + format check
make lint-sql           # sqlfluff lint on all SQL models and macros
make pre-commit-install # install git hooks (run once after cloning)
```

## Models

```
staging/
  stg_orders            — seed-based orders (view)
  stg_tpch_customers    — TPC-H customers (view)
  stg_tpch_orders       — TPC-H orders (view)
  stg_tpch_lineitems    — TPC-H lineitems (view)
  stg_tpch_suppliers    — TPC-H suppliers (view)
  stg_tpch_nations      — TPC-H nations (view)
  stg_tpch_regions      — TPC-H regions (view)
  stg_tpch_parts        — TPC-H parts (view)

marts/
  orders_summary           — order totals by status (table)
  tpch_revenue_by_segment  — revenue by market segment (table)
  tpch_supplier_performance — supplier revenue and discount stats (table)
  tpch_daily_revenue           — incremental daily revenue rollup (table, keyed on ship_date)
  tpch_q1_pricing_summary      — TPC-H Q1: pricing summary by return flag and line status
  tpch_q3_shipping_priority    — TPC-H Q3: top 10 unshipped orders by revenue (BUILDING segment)
  tpch_q5_local_supplier_volume — TPC-H Q5: supplier revenue by nation in ASIA region
```

All mart models have enforced dbt contracts. The `tpch_daily_revenue` model is incremental — `make simulate-new-data` inserts rows with today's date, then `make dbt-run` picks them up via DuckDB's columnar engine.

## Incremental demo

```bash
make dbt-run              # first run: full build
make simulate-new-data    # insert 1000 new lineitems with ship_date=today
make dbt-run              # incremental: only processes today's date
```

## Environments

| Target | Schema | Usage |
|--------|--------|-------|
| `dev` (default) | `dev` | local development |
| `prod` | `public` | set `DBT_TARGET=prod` |
