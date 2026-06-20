# pg_duckdb + dbt + uv Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Dockerized PostgreSQL environment with the pg_duckdb extension and a dbt project using the postgres adapter, managed by uv and linted with ruff.

**Architecture:** The `pgduckdb/pgduckdb:18-v1.1.1` official image bundles Postgres 18 + pg_duckdb. A docker-compose file brings up the DB and a separate dbt runner container. Python deps (dbt-postgres, ruff) are managed by uv via `pyproject.toml`; the dbt runner image installs from the lockfile.

**Tech Stack:** pgduckdb/pgduckdb:18-v1.1.1, dbt-postgres ≥1.9, uv ≥0.5, ruff ≥0.9, Python ≥3.12

## Global Constraints

- pg_duckdb image tag: `pgduckdb/pgduckdb:18-v1.1.1`
- dbt adapter: `dbt-postgres` (pg_duckdb is a Postgres extension — no separate dbt-duckdb adapter needed)
- Python version: 3.12
- uv for all Python dependency management — no pip/poetry/conda
- ruff for lint + format — no flake8/black/isort
- No secrets committed — use `.env` file (gitignored) based on `.env.example`

---

## File Map

| File | Responsibility |
|------|---------------|
| `Dockerfile` | dbt runner image: Python 3.12 + uv + deps from lockfile |
| `docker-compose.yml` | `db` (pgduckdb) + `dbt` (runner) services |
| `scripts/init.sql` | `CREATE EXTENSION pg_duckdb;` on DB init |
| `.env.example` | Template for `POSTGRES_PASSWORD`, `DBT_TARGET` |
| `pyproject.toml` | uv project: dbt-postgres, ruff deps + tool config |
| `uv.lock` | Generated lockfile (committed) |
| `.python-version` | `3.12` |
| `dbt/dbt_project.yml` | dbt project metadata and path config |
| `dbt/profiles.yml` | dbt connection profile reading from env vars |
| `dbt/packages.yml` | dbt package dependencies (dbt-utils) |
| `dbt/seeds/raw_orders.csv` | Sample seed data |
| `dbt/models/staging/stg_orders.sql` | Staging model using pg_duckdb `duckdb.query()` |
| `dbt/models/staging/schema.yml` | Column docs + not_null/unique tests |
| `dbt/models/marts/orders_summary.sql` | Mart aggregation model |
| `dbt/models/marts/schema.yml` | Mart docs + tests |
| `dbt/macros/duckdb_scan.sql` | Macro wrapping `duckdb.query()` for reuse |
| `Makefile` | `make up`, `make dbt-run`, `make dbt-test`, `make lint` |
| `CLAUDE.md` | Project conventions for AI assistants |

---

## Task 1: Docker infrastructure

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `scripts/init.sql`
- Create: `.env.example`
- Create: `.dockerignore`

**Interfaces:**
- Produces: `db` service at `localhost:5432`, database `analytics`, user `postgres`

- [ ] **Step 1: Write `scripts/init.sql`**

```sql
CREATE EXTENSION IF NOT EXISTS pg_duckdb;
```

- [ ] **Step 2: Write `.env.example`**

```bash
POSTGRES_PASSWORD=secret
POSTGRES_DB=analytics
POSTGRES_USER=postgres
DBT_TARGET=dev
```

- [ ] **Step 3: Write `docker-compose.yml`**

```yaml
services:
  db:
    image: pgduckdb/pgduckdb:18-v1.1.1
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB:-analytics}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-analytics}"]
      interval: 5s
      timeout: 5s
      retries: 10

  dbt:
    build: .
    environment:
      POSTGRES_HOST: db
      POSTGRES_PORT: 5432
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB:-analytics}
      DBT_TARGET: ${DBT_TARGET:-dev}
    volumes:
      - ./dbt:/app/dbt
    depends_on:
      db:
        condition: service_healthy
    working_dir: /app/dbt
    # ponytail: no command — run dbt interactively via `docker compose run dbt dbt run`

volumes:
  pgdata:
```

- [ ] **Step 4: Write `Dockerfile`**

```dockerfile
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY dbt/ ./dbt/
```

- [ ] **Step 5: Write `.dockerignore`**

```
.git
.env
__pycache__
*.pyc
.venv
dbt/target
dbt/dbt_packages
dbt/logs
```

- [ ] **Step 6: Verify DB starts**

```bash
cp .env.example .env
# edit .env: set POSTGRES_PASSWORD=secret
docker compose up db -d
docker compose exec db psql -U postgres -d analytics -c "\dx"
```

Expected: extension row for `pg_duckdb` in the output.

- [ ] **Step 7: Commit**

```bash
git add Dockerfile docker-compose.yml scripts/ .env.example .dockerignore
git commit -m "feat: add docker infrastructure with pgduckdb and dbt runner"
```

---

## Task 2: Python environment (uv + ruff)

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Generated: `uv.lock`

**Interfaces:**
- Produces: `uv run dbt`, `uv run ruff check .` available in the venv

- [ ] **Step 1: Write `.python-version`**

```
3.12
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "dbt-pg-duckdb"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "dbt-postgres>=1.9",
    "dbt-utils>=1.3",
]

[tool.uv]
dev-dependencies = [
    "ruff>=0.9",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
```

- [ ] **Step 3: Generate lockfile**

```bash
uv sync
```

Expected: `.venv/` created, `uv.lock` written.

- [ ] **Step 4: Verify ruff works**

```bash
uv run ruff check .
```

Expected: no output (nothing to lint yet) or exit 0.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock .python-version
git commit -m "feat: add uv python environment with dbt-postgres and ruff"
```

---

## Task 3: dbt project scaffold

**Files:**
- Create: `dbt/dbt_project.yml`
- Create: `dbt/profiles.yml`
- Create: `dbt/packages.yml`

**Interfaces:**
- Consumes: `POSTGRES_*` env vars from docker-compose / `.env`
- Produces: `dbt debug` passes, dbt project named `pg_duckdb_analytics`

- [ ] **Step 1: Write `dbt/profiles.yml`**

```yaml
pg_duckdb_analytics:
  target: "{{ env_var('DBT_TARGET', 'dev') }}"
  outputs:
    dev:
      type: postgres
      host: "{{ env_var('POSTGRES_HOST', 'localhost') }}"
      port: "{{ env_var('POSTGRES_PORT', '5432') | int }}"
      user: "{{ env_var('POSTGRES_USER', 'postgres') }}"
      password: "{{ env_var('POSTGRES_PASSWORD') }}"
      dbname: "{{ env_var('POSTGRES_DB', 'analytics') }}"
      schema: public
      threads: 4
```

- [ ] **Step 2: Write `dbt/dbt_project.yml`**

```yaml
name: pg_duckdb_analytics
version: "1.0.0"
profile: pg_duckdb_analytics

model-paths: ["models"]
seed-paths: ["seeds"]
test-paths: ["tests"]
macro-paths: ["macros"]
target-path: "target"
clean-targets: ["target", "dbt_packages"]

models:
  pg_duckdb_analytics:
    staging:
      +materialized: view
    marts:
      +materialized: table
```

- [ ] **Step 3: Write `dbt/packages.yml`**

```yaml
packages:
  - package: dbt-labs/dbt_utils
    version: ">=1.3.0"
```

- [ ] **Step 4: Create empty dirs dbt expects**

```bash
mkdir -p dbt/models/staging dbt/models/marts dbt/tests dbt/macros dbt/seeds dbt/logs
touch dbt/tests/.gitkeep dbt/logs/.gitkeep
```

- [ ] **Step 5: Add `.gitignore` entries for dbt artifacts**

```bash
cat >> .gitignore << 'EOF'
.env
.venv/
dbt/target/
dbt/dbt_packages/
dbt/logs/
EOF
```

- [ ] **Step 6: Install dbt packages and debug**

```bash
cd dbt && uv run dbt deps
DBT_TARGET=dev POSTGRES_PASSWORD=secret uv run dbt debug --profiles-dir .
```

Expected: `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add dbt/ .gitignore
git commit -m "feat: scaffold dbt project with postgres profile and dbt-utils"
```

---

## Task 4: dbt seed, models, and tests

**Files:**
- Create: `dbt/seeds/raw_orders.csv`
- Create: `dbt/models/staging/stg_orders.sql`
- Create: `dbt/models/staging/schema.yml`
- Create: `dbt/models/marts/orders_summary.sql`
- Create: `dbt/models/marts/schema.yml`
- Create: `dbt/macros/duckdb_scan.sql`

**Interfaces:**
- Consumes: `db` service running with `pg_duckdb` extension
- Produces: `stg_orders` view, `orders_summary` table, passing `dbt test`

- [ ] **Step 1: Write `dbt/seeds/raw_orders.csv`**

```csv
order_id,customer_id,amount,status,created_at
1,101,99.99,completed,2024-01-01
2,102,149.50,pending,2024-01-02
3,101,25.00,completed,2024-01-03
4,103,299.00,cancelled,2024-01-04
5,102,75.00,completed,2024-01-05
```

- [ ] **Step 2: Write `dbt/macros/duckdb_scan.sql`**

```sql
{% macro duckdb_scan(query) %}
    {# ponytail: wraps duckdb.query() so models don't depend on the raw function name #}
    select * from duckdb.query($$ {{ query }} $$)
{% endmacro %}
```

- [ ] **Step 3: Write `dbt/models/staging/stg_orders.sql`**

```sql
-- Staging model: cast and clean raw_orders seed data.
-- Uses standard SQL; pg_duckdb accelerates the scan automatically.
select
    order_id::bigint,
    customer_id::bigint,
    amount::numeric(10, 2),
    status,
    created_at::date
from {{ ref('raw_orders') }}
where status != 'cancelled'
```

- [ ] **Step 4: Write `dbt/models/staging/schema.yml`**

```yaml
version: 2

models:
  - name: stg_orders
    description: "Cleaned and filtered orders from raw seed data"
    columns:
      - name: order_id
        description: "Primary key"
        tests:
          - unique
          - not_null
      - name: customer_id
        tests:
          - not_null
      - name: amount
        tests:
          - not_null
      - name: status
        tests:
          - not_null
          - accepted_values:
              values: ["completed", "pending"]
```

- [ ] **Step 5: Write `dbt/models/marts/orders_summary.sql`**

```sql
-- Mart: aggregate completed order totals per customer.
select
    customer_id,
    count(*) as order_count,
    sum(amount) as total_amount,
    min(created_at) as first_order_date,
    max(created_at) as last_order_date
from {{ ref('stg_orders') }}
where status = 'completed'
group by customer_id
```

- [ ] **Step 6: Write `dbt/models/marts/schema.yml`**

```yaml
version: 2

models:
  - name: orders_summary
    description: "Per-customer completed order aggregates"
    columns:
      - name: customer_id
        tests:
          - unique
          - not_null
      - name: order_count
        tests:
          - not_null
      - name: total_amount
        tests:
          - not_null
```

- [ ] **Step 7: Run seed + models + tests**

```bash
cd dbt
uv run dbt seed --profiles-dir .
uv run dbt run --profiles-dir .
uv run dbt test --profiles-dir .
```

Expected: all green, `orders_summary` table created with 2 customer rows (101, 102).

- [ ] **Step 8: Commit**

```bash
git add dbt/seeds/ dbt/models/ dbt/macros/
git commit -m "feat: add seed data, staging/mart models, and schema tests"
```

---

## Task 5: Makefile + ruff CI check

**Files:**
- Create: `Makefile`

**Interfaces:**
- Produces: `make up`, `make dbt-run`, `make dbt-test`, `make lint`, `make down`

- [ ] **Step 1: Write `Makefile`**

```makefile
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
```

- [ ] **Step 2: Run full flow end-to-end**

```bash
make up
sleep 5          # wait for healthcheck
make dbt-deps
make dbt-seed
make dbt-run
make dbt-test
make lint
```

Expected: all targets exit 0.

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "feat: add Makefile for common dev tasks"
```

---

## Self-Review

**Spec coverage:**
- [x] Docker image with pg_duckdb — Task 1 (official pgduckdb image + extension init)
- [x] dbt transformations and tests — Tasks 3, 4
- [x] uv for package management — Task 2
- [x] ruff for linting — Task 2, Task 5
- [x] CLAUDE.md — written separately alongside this plan

**Placeholder scan:** None found — all code blocks are complete.

**Type consistency:** `ref('raw_orders')` in Task 4 Step 3 refers to the seed named `raw_orders` (CSV filename without extension) — matches `dbt/seeds/raw_orders.csv`.
