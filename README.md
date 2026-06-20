# dbt + pg_duckdb

[![CI](https://github.com/TiagoAdriaNunes/dbt_pg_duckdb/actions/workflows/ci.yml/badge.svg)](https://github.com/TiagoAdriaNunes/dbt_pg_duckdb/actions/workflows/ci.yml)
[![dbt docs](https://github.com/TiagoAdriaNunes/dbt_pg_duckdb/actions/workflows/dbt-docs.yml/badge.svg)](https://tiagoadrianunes.github.io/dbt_pg_duckdb/)

Dockerized PostgreSQL with the [pg_duckdb](https://github.com/duckdb/pg_duckdb) extension and a [dbt](https://github.com/dbt-labs/dbt-core) project for analytics transformations on TPC-H benchmark data.

## Live docs

**[tiagoadrianunes.github.io/dbt_pg_duckdb](https://tiagoadrianunes.github.io/dbt_pg_duckdb/)**

Auto-generated on every push to `main`. Includes:

- **Lineage DAG** — end-to-end graph from raw sources through staging and marts to downstream exposures (dashboards, reports, notebooks)
- **Model contracts** — enforced column names and data types on all mart models; dbt fails the run if the SQL output doesn't match the declared schema
- **Test results** — `unique`, `not_null`, and `accepted_values` tests on every key column, visible per model
- **Exposures** — downstream consumers declared in YAML so the lineage shows where data lands after the marts

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

`make all` starts the database, loads TPC-H benchmark data (sf=1, ~6M lineitems), runs all dbt models, tests, and linters. No `.env` file required.

## Commands

```bash
make all                # full pipeline: up + deps + tpch-init + run + test + lint
make up                 # start DB and wait until healthy
make down               # stop containers and remove volumes
make dbt-run            # run all models
make dbt-test           # run schema tests
make dbt-snapshot       # run SCD2 snapshots
make dbt-docs-serve     # generate and serve docs at http://localhost:8080
make simulate-new-data  # insert new lineitems + update customers (triggers incremental + snapshot)
make duckdb-cli         # open DuckDB shell with Postgres attached
make benchmark          # run TPC-H Q1/Q3/Q5 under Postgres vs DuckDB engine
make lint               # ruff check + format check
make lint-sql           # sqlfluff lint on all SQL models and macros
make pre-commit-install # install git hooks (run once after cloning)
```

## dbt features

### Contracts
All mart models declare explicit column names and data types in YAML. dbt enforces these at run time — if the SQL produces a different schema, the run fails before any data is written.

### Tests
Every key column has at least one test:
- `unique` + `not_null` on primary keys
- `not_null` on critical foreign keys and measures
- `accepted_values` on status/flag columns

Tests run via `make dbt-test` and as the last step of CI.

### Incremental models
`tpch_daily_revenue` only processes new `ship_date` values on each run. On first run it builds the full table; on subsequent runs it appends only dates not yet present. Demo:

```bash
make dbt-run              # full build
make simulate-new-data    # insert rows with ship_date=today
make dbt-run              # incremental: only today's date processed
```

### Snapshots (SCD Type 2)
`snap_tpch_customers` tracks historical changes to customer records. Each time a customer's `market_segment`, `account_balance`, `address`, or `phone` changes, dbt closes the old row (`dbt_valid_to`) and inserts a new active one. Demo:

```bash
make dbt-snapshot         # initial capture: 150k customers
make simulate-new-data    # updates 100 customers BUILDING → MACHINERY
make dbt-snapshot         # 100 expired rows + 100 new active rows

# query history:
psql -c "SELECT * FROM snapshots.snap_tpch_customers WHERE dbt_valid_to IS NOT NULL LIMIT 5"
```

### Exposures
Downstream consumers are declared in YAML so the lineage DAG extends beyond the marts:
- `revenue_dashboard` — consumes `tpch_revenue_by_segment` + `tpch_daily_revenue`
- `supplier_performance_report` — consumes `tpch_supplier_performance` + `tpch_q5_local_supplier_volume`
- `tpch_benchmark_notebook` — consumes Q1, Q3, Q5 models

### DuckDB execution
All dbt runs use `SET duckdb.force_execution = true` via an `on-run-start` hook, routing every query through DuckDB's vectorized columnar engine instead of the Postgres planner.

## Models

```
staging/                      (views)
  stg_customers               — TPC-H customers
  stg_orders                  — TPC-H orders
  stg_lineitems               — TPC-H lineitems
  stg_suppliers               — TPC-H suppliers
  stg_nations                 — TPC-H nations
  stg_regions                 — TPC-H regions

marts/                        (tables, enforced contracts)
  tpch_revenue_by_segment     — revenue by market segment
  tpch_supplier_performance   — supplier revenue and discount stats by nation
  tpch_daily_revenue          — incremental daily revenue rollup (keyed on ship_date)
  tpch_q1_pricing_summary     — TPC-H Q1: aggregate scan over all lineitems
  tpch_q3_shipping_priority   — TPC-H Q3: top 10 unshipped orders by revenue
  tpch_q5_local_supplier_volume — TPC-H Q5: supplier revenue by nation in ASIA

snapshots/
  snap_tpch_customers         — SCD2 history of customer segment and balance changes
```

## Environments

| Target | Schema | Usage |
|--------|--------|-------|
| `dev` (default) | `dev` | local development |
| `prod` | `public` | set `DBT_TARGET=prod` |
