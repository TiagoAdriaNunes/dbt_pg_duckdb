"""
Initialize TPC-H benchmark data into pg_duckdb, ClickHouse, a plain DuckDB file,
Parquet files, and a DuckLake catalog.
Generates synthetic supply-chain data at the requested scale factor.
Idempotent: skips generation if tables already exist in the raw schema.
"""

import logging
import os
import shutil
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

SCALE_FACTOR = float(os.environ.get("TPCH_SCALE_FACTOR", "3"))  # sf=0.1 ≈ 100 MB, sf=1 ≈ 1 GB
CH_BATCH_SIZE = int(os.environ.get("CH_INSERT_BATCH_SIZE", "100000"))
# DuckDB defaults to ~80% of *total* system RAM, ignoring whatever else is already
# running (IDE, Docker containers, ...). Cap it explicitly to avoid over-committing.
DUCKDB_MEMORY_LIMIT = os.environ.get("DUCKDB_MEMORY_LIMIT", "2GB")
DUCKDB_THREADS = os.environ.get("DUCKDB_THREADS", "2")
# Kept around after load (not deleted) so benchmark.py can query it directly as a
# fourth, native-DuckDB-storage engine — no Postgres heap scan, no network hop.
STAGING_DB = os.environ.get(
    "TPCH_DUCKDB_PATH", os.path.join(tempfile.gettempdir(), "tpch_staging.duckdb")
)
PARQUET_DIR = os.environ.get(
    "TPCH_PARQUET_DIR", os.path.join(tempfile.gettempdir(), "tpch_parquet")
)
LANCE_DIR = os.environ.get("TPCH_LANCE_DIR", os.path.join(tempfile.gettempdir(), "tpch_lance"))
VORTEX_DIR = os.environ.get("TPCH_VORTEX_DIR", os.path.join(tempfile.gettempdir(), "tpch_vortex"))
DUCKLAKE_DIR = os.environ.get(
    "TPCH_DUCKLAKE_DIR", os.path.join(tempfile.gettempdir(), "tpch_ducklake")
)
DUCKLAKE_METADATA = os.path.join(DUCKLAKE_DIR, "metadata.ducklake")
DUCKLAKE_DATA = os.path.join(DUCKLAKE_DIR, "data")

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
    # Views under raw.* so the same benchmark SQL (raw.lineitem, ...) runs unmodified
    # against this file as a fourth "native DuckDB" engine, alongside PG/DuckDB-engine/ClickHouse.
    staging.execute("CREATE SCHEMA IF NOT EXISTS raw")
    for table in TABLES:
        staging.execute(f"CREATE OR REPLACE VIEW raw.{table} AS SELECT * FROM main.{table}")
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


def export_parquet() -> None:
    log.info("Exporting raw.* to Parquet files at %s...", PARQUET_DIR)
    os.makedirs(PARQUET_DIR, exist_ok=True)
    conn = _cap_resources(duckdb.connect(STAGING_DB, read_only=True))
    t0 = time.time()
    for table in TABLES:
        path = os.path.join(PARQUET_DIR, f"{table}.parquet")
        conn.execute(f"COPY raw.{table} TO '{path}' (FORMAT parquet, COMPRESSION zstd)")
    conn.close()
    log.info("Parquet export done in %.1fs", time.time() - t0)


def export_lance() -> None:
    log.info("Exporting raw.* to Lance datasets at %s...", LANCE_DIR)
    os.makedirs(LANCE_DIR, exist_ok=True)
    conn = _cap_resources(duckdb.connect(STAGING_DB, read_only=True))
    conn.execute("INSTALL lance; LOAD lance")
    t0 = time.time()
    for table in TABLES:
        path = os.path.join(LANCE_DIR, f"{table}.lance")
        conn.execute(f"COPY raw.{table} TO '{path}' (FORMAT lance, MODE 'overwrite')")
    conn.close()
    log.info("Lance export done in %.1fs", time.time() - t0)


def export_vortex() -> None:
    log.info("Exporting raw.* to Vortex files at %s...", VORTEX_DIR)
    os.makedirs(VORTEX_DIR, exist_ok=True)
    conn = _cap_resources(duckdb.connect(STAGING_DB, read_only=True))
    conn.execute("INSTALL vortex; LOAD vortex")
    t0 = time.time()
    for table in TABLES:
        path = os.path.join(VORTEX_DIR, f"{table}.vortex")
        conn.execute(f"COPY raw.{table} TO '{path}' (FORMAT vortex)")
    conn.close()
    log.info("Vortex export done in %.1fs", time.time() - t0)


def load_ducklake() -> None:
    log.info("Loading TPC-H tables into a DuckLake catalog at %s...", DUCKLAKE_DIR)
    if os.path.exists(DUCKLAKE_DIR):
        shutil.rmtree(DUCKLAKE_DIR)
    os.makedirs(DUCKLAKE_DATA, exist_ok=True)
    conn = _cap_resources(duckdb.connect())
    conn.execute("INSTALL ducklake")
    conn.execute(f"ATTACH '{STAGING_DB}' AS staging (READ_ONLY)")
    conn.execute(f"ATTACH 'ducklake:{DUCKLAKE_METADATA}' AS lake (DATA_PATH '{DUCKLAKE_DATA}')")
    conn.execute("CREATE SCHEMA lake.raw")
    t0 = time.time()
    for table in TABLES:
        conn.execute(f"CREATE TABLE lake.raw.{table} AS SELECT * FROM staging.{table}")
    conn.close()
    log.info("DuckLake load done in %.1fs", time.time() - t0)


def main() -> None:
    pg_conn = get_conn()
    pg_done = already_loaded(pg_conn)
    pg_conn.close()

    ch_client = get_ch_client()
    ch_done = ch_already_loaded(ch_client)
    native_done = os.path.exists(STAGING_DB)
    parquet_done = os.path.exists(os.path.join(PARQUET_DIR, f"{TABLES[-1]}.parquet"))
    lance_done = os.path.exists(os.path.join(LANCE_DIR, f"{TABLES[-1]}.lance"))
    vortex_done = os.path.exists(os.path.join(VORTEX_DIR, f"{TABLES[-1]}.vortex"))
    ducklake_done = os.path.exists(DUCKLAKE_METADATA)

    if (
        pg_done
        and ch_done
        and native_done
        and parquet_done
        and lance_done
        and vortex_done
        and ducklake_done
    ):
        return

    generate_staging()

    if not pg_done:
        pg_conn = get_conn()
        load_into_postgres(pg_conn)
        pg_conn.close()

    if not ch_done:
        load_into_clickhouse(ch_client)

    if not parquet_done:
        export_parquet()

    if not lance_done:
        export_lance()

    if not vortex_done:
        export_vortex()

    if not ducklake_done:
        load_ducklake()

    log.info("Native DuckDB file kept at %s for benchmark.py", STAGING_DB)


if __name__ == "__main__":
    main()
