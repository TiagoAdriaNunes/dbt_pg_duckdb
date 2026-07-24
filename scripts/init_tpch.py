"""
Initialize TPC-H benchmark data into pg_duckdb.
Generates synthetic supply-chain data at the requested scale factor.
Idempotent: skips generation if tables already exist in the raw schema.
"""

import logging
import os
import tempfile
import time

import clickhouse_connect
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

CH_HOST = os.environ.get("CLICKHOUSE_HOST", "localhost")
CH_PORT = int(os.environ.get("CLICKHOUSE_PORT", "8123"))
CH_USER = os.environ.get("CLICKHOUSE_USER", "default")
CH_PASSWORD = os.environ.get("CLICKHOUSE_PASSWORD", "duckdb")
CH_DB = os.environ.get("CLICKHOUSE_DB", "analytics")

SCALE_FACTOR = float(os.environ.get("TPCH_SCALE_FACTOR", "1"))  # sf=0.1 ≈ 100 MB, sf=1 ≈ 1 GB
CH_BATCH_SIZE = int(os.environ.get("CH_INSERT_BATCH_SIZE", "100000"))
# DuckDB defaults to ~80% of *total* system RAM, ignoring whatever else is already
# running (IDE, Docker containers, ...). Cap it explicitly to avoid over-committing.
DUCKDB_MEMORY_LIMIT = os.environ.get("DUCKDB_MEMORY_LIMIT", "2GB")
DUCKDB_THREADS = os.environ.get("DUCKDB_THREADS", "2")
STAGING_DB = os.path.join(tempfile.gettempdir(), "tpch_staging.duckdb")

PG_CONN = f"host={PG_HOST} port={PG_PORT} dbname={PG_DB} user={PG_USER} password={PG_PASSWORD}"

TABLES = ["customer", "orders", "lineitem", "supplier", "nation", "region", "part", "partsupp"]

# duckdb dbgen only emits these types; DECIMAL(p,s) is valid ClickHouse syntax as-is.
DUCKDB_TO_CLICKHOUSE_TYPES = {
    "BIGINT": "Int64",
    "INTEGER": "Int32",
    "DOUBLE": "Float64",
    "VARCHAR": "String",
    "DATE": "Date",
}


def _clickhouse_type(duckdb_type: str) -> str:
    return DUCKDB_TO_CLICKHOUSE_TYPES.get(duckdb_type, duckdb_type)


def get_ch_client():
    return clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT, username=CH_USER, password=CH_PASSWORD, database=CH_DB
    )


def _cap_resources(conn: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyConnection:
    conn.execute(f"SET memory_limit='{DUCKDB_MEMORY_LIMIT}'")
    conn.execute(f"SET threads={DUCKDB_THREADS}")
    return conn


def get_conn() -> duckdb.DuckDBPyConnection:
    conn = _cap_resources(duckdb.connect())
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
            if count > 0:
                log.info("TPC-H already present (%s customers). Skipping.", f"{count:,}")
                return True
            log.info("raw.customer exists but is empty (crash likely truncated it). Reloading.")
    except Exception:
        pass
    return False


def ch_already_loaded(client) -> bool:
    # Check the last table loaded (partsupp) so a run interrupted mid-way is retried, not skipped.
    exists = client.query(
        "SELECT count(*) FROM system.tables WHERE database = 'raw' AND name = 'partsupp'"
    ).result_rows[0][0]
    if exists:
        count = client.query("SELECT count(*) FROM raw.customer").result_rows[0][0]
        log.info("TPC-H already present in ClickHouse (%s customers). Skipping.", f"{count:,}")
        return True
    return False


def generate_staging() -> None:
    size_hint = f"~{SCALE_FACTOR} GB" if SCALE_FACTOR >= 1 else f"~{int(SCALE_FACTOR * 1000)} MB"
    log.info("Starting TPC-H dbgen (scale_factor=%s, %s)", SCALE_FACTOR, size_hint)
    t0 = time.time()
    # dbgen() appends rather than replacing — a leftover file from a killed/crashed
    # run would silently double every table instead of erroring.
    if os.path.exists(STAGING_DB):
        os.remove(STAGING_DB)
    staging = _cap_resources(duckdb.connect(STAGING_DB))
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


def load_into_clickhouse(client) -> None:
    log.info("Loading TPC-H tables into ClickHouse (raw database)...")
    conn = _cap_resources(duckdb.connect())
    conn.execute(f"ATTACH '{STAGING_DB}' AS staging (READ_ONLY)")
    client.command("CREATE DATABASE IF NOT EXISTS raw")

    total_t0 = time.time()
    for table in TABLES:
        t0 = time.time()
        log.info("Loading %s...", table)
        columns = conn.execute(f"DESCRIBE staging.{table}").fetchall()
        col_names = [name for name, *_ in columns]
        cols_ddl = ", ".join(f"{name} {_clickhouse_type(dtype)}" for name, dtype, *_ in columns)
        client.command(f"DROP TABLE IF EXISTS raw.{table}")
        client.command(
            f"CREATE TABLE raw.{table} ({cols_ddl}) ENGINE = MergeTree ORDER BY {col_names[0]}"
        )

        # Stream in bounded batches — fetchall() on lineitem-sized tables exhausts RAM.
        cur = conn.execute(f"SELECT * FROM staging.{table}")
        row_count = 0
        while chunk := cur.fetchmany(CH_BATCH_SIZE):
            client.insert(f"raw.{table}", chunk, column_names=col_names)
            row_count += len(chunk)
        log.info("  %s done in %.1fs (%s rows)", table, time.time() - t0, f"{row_count:,}")
    log.info("All tables loaded into ClickHouse in %.1fs", time.time() - total_t0)
    conn.close()


def main() -> None:
    pg_conn = get_conn()
    pg_done = already_loaded(pg_conn)
    pg_conn.close()

    ch_client = get_ch_client()
    ch_done = ch_already_loaded(ch_client)

    if pg_done and ch_done:
        return

    try:
        generate_staging()

        if not pg_done:
            pg_conn = get_conn()
            load_into_postgres(pg_conn)
            pg_conn.close()

        if not ch_done:
            load_into_clickhouse(ch_client)
    finally:
        if os.path.exists(STAGING_DB):
            os.remove(STAGING_DB)


if __name__ == "__main__":
    main()
