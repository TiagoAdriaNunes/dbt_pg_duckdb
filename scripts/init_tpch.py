"""
Initialize TPC-H benchmark data into pg_duckdb.
Generates synthetic supply-chain data at the requested scale factor.
Idempotent: skips generation if tables already exist in the raw schema.
"""

import logging
import os
import tempfile
import time

import duckdb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

PG_HOST = os.environ.get("POSTGRES_HOST", "localhost")
PG_PORT = os.environ.get("POSTGRES_PORT", "5432")
PG_USER = os.environ.get("POSTGRES_USER", "postgres")
PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "duckdb")
PG_DB = os.environ.get("POSTGRES_DB", "analytics")
SCALE_FACTOR = float(os.environ.get("TPCH_SCALE_FACTOR", "1"))  # sf=0.1 ≈ 100 MB, sf=1 ≈ 1 GB
STAGING_DB = os.path.join(tempfile.gettempdir(), "tpch_staging.duckdb")

PG_CONN = f"host={PG_HOST} port={PG_PORT} dbname={PG_DB} user={PG_USER} password={PG_PASSWORD}"

TABLES = ["customer", "orders", "lineitem", "supplier", "nation", "region", "part", "partsupp"]


def get_conn() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect()
    conn.execute("INSTALL postgres; LOAD postgres")
    conn.execute(f"ATTACH '{PG_CONN}' AS pg (TYPE POSTGRES)")
    return conn


def already_loaded(conn: duckdb.DuckDBPyConnection) -> bool:
    try:
        row = conn.execute(
            "SELECT count(*) FROM pg.information_schema.tables "
            "WHERE table_schema = 'raw' AND table_name = 'customer'"
        ).fetchone()
        if row and row[0] > 0:
            count = conn.execute("SELECT count(*) FROM pg.raw.customer").fetchone()[0]
            log.info("TPC-H already present (%s customers). Skipping.", f"{count:,}")
            return True
    except Exception:
        pass
    return False


def generate_staging() -> None:
    size_hint = f"~{SCALE_FACTOR} GB" if SCALE_FACTOR >= 1 else f"~{int(SCALE_FACTOR * 1000)} MB"
    log.info("Starting TPC-H dbgen (scale_factor=%s, %s)", SCALE_FACTOR, size_hint)
    t0 = time.time()
    staging = duckdb.connect(STAGING_DB)
    staging.execute(f"SET temp_directory='{tempfile.gettempdir()}'")
    staging.execute("INSTALL tpch; LOAD tpch")
    staging.execute(f"CALL dbgen(sf={SCALE_FACTOR})")
    staging.close()
    log.info("Data generation done in %.1fs", time.time() - t0)


def load_into_postgres(conn: duckdb.DuckDBPyConnection) -> None:
    log.info("Loading TPC-H tables into Postgres (raw schema)...")
    conn.execute(f"ATTACH '{STAGING_DB}' AS staging (READ_ONLY)")
    conn.execute("CREATE SCHEMA IF NOT EXISTS pg.raw")
    conn.execute("CALL postgres_execute('pg', 'SET synchronous_commit = off')")
    total_t0 = time.time()
    for table in TABLES:
        t0 = time.time()
        log.info("Loading %s...", table)
        # UNLOGGED skips WAL entirely — safe for regeneratable benchmark data
        conn.execute(
            f"CREATE OR REPLACE TABLE pg.raw.{table} AS SELECT * FROM staging.{table} WHERE false"
        )
        conn.execute(f"CALL postgres_execute('pg', 'ALTER TABLE raw.{table} SET UNLOGGED')")
        conn.execute("CALL pg_clear_cache()")
        conn.execute(f"INSERT INTO pg.raw.{table} SELECT * FROM staging.{table}")
        log.info("  %s done in %.1fs", table, time.time() - t0)
    log.info("All tables loaded in %.1fs", time.time() - total_t0)

    counts = conn.execute(
        " UNION ALL ".join(
            f"SELECT '{t}' AS table_name, count(*) AS row_count FROM pg.raw.{t}" for t in TABLES
        )
        + " ORDER BY table_name"
    ).fetchall()

    log.info("Row counts:")
    for table, count in counts:
        log.info("  %-12s %10s rows", table, f"{count:,}")


def main() -> None:
    conn = get_conn()
    try:
        if already_loaded(conn):
            return
        conn.close()

        generate_staging()

        conn = get_conn()
        load_into_postgres(conn)
    finally:
        conn.close()
        if os.path.exists(STAGING_DB):
            os.remove(STAGING_DB)


if __name__ == "__main__":
    main()
