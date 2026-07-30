"""
Query engines for benchmark.py.
  PG (native) : duckdb.force_execution = false (PG planner, heap storage)
  PG (duckdb) : duckdb.force_execution = true  (vectorized, but scans PG heap tuples)
  ClickHouse  : separate server, same raw.* tables loaded by scripts/init_tpch.py
  DuckDB native: scripts/init_tpch.py's staging file, queried directly - no PG at all
  Parquet     : same data as Parquet files, read_parquet() views under raw.*
  Lance       : same data as Lance datasets (LanceDB's columnar format)
  Vortex      : same data as Vortex files (Spiral's columnar format)
  DuckLake    : same data in a DuckLake catalog (Parquet + transactional metadata)

PG and ClickHouse are separate server processes reached over a network
connection — cheap to keep open for the whole benchmark. The other five are
embedded DuckDB connections living in this process's own memory; DUCKDB_ENGINES
holds a connect function per engine rather than a live connection so
bench_duckdb_engine() can open, query, and close them one at a time. Opening
all five at once (2GB memory_limit each = 10GB) is what OOM-killed Postgres
the first time this ran on a 6.4GB box.
"""

import os
import tempfile
import time

import clickhouse_connect
import duckdb
import psycopg

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

NATIVE_DB = os.environ.get(
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

DUCKDB_MEMORY_LIMIT = os.environ.get("DUCKDB_MEMORY_LIMIT", "2GB")
DUCKDB_THREADS = os.environ.get("DUCKDB_THREADS", "2")

TABLES = ["customer", "orders", "lineitem", "supplier", "nation", "region", "part", "partsupp"]


def _cap(conn: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyConnection:
    conn.execute(f"SET memory_limit='{DUCKDB_MEMORY_LIMIT}'")
    conn.execute(f"SET threads={DUCKDB_THREADS}")
    return conn


def run_pg_native(cur, sql: str) -> None:
    cur.execute("SET duckdb.force_execution = false")
    cur.execute(sql)
    cur.fetchall()


def run_pg_duckdb(cur, sql: str) -> None:
    cur.execute("SET duckdb.force_execution = true")
    cur.execute(sql)
    cur.fetchall()


def run_clickhouse(client, sql: str) -> None:
    client.query(sql)


def run_duckdb(conn: duckdb.DuckDBPyConnection, sql: str) -> None:
    conn.execute(sql).fetchall()


def _connect_parquet() -> duckdb.DuckDBPyConnection:
    conn = _cap(duckdb.connect())
    conn.execute("CREATE SCHEMA raw")
    for table in TABLES:
        path = os.path.join(PARQUET_DIR, f"{table}.parquet")
        conn.execute(f"CREATE VIEW raw.{table} AS SELECT * FROM read_parquet('{path}')")
    return conn


def _connect_lance() -> duckdb.DuckDBPyConnection:
    conn = _cap(duckdb.connect())
    conn.execute("INSTALL lance; LOAD lance")
    conn.execute("CREATE SCHEMA raw")
    for table in TABLES:
        path = os.path.join(LANCE_DIR, f"{table}.lance")
        conn.execute(f"CREATE VIEW raw.{table} AS SELECT * FROM '{path}'")
    return conn


def _connect_vortex() -> duckdb.DuckDBPyConnection:
    conn = _cap(duckdb.connect())
    conn.execute("INSTALL vortex; LOAD vortex")
    conn.execute("CREATE SCHEMA raw")
    for table in TABLES:
        path = os.path.join(VORTEX_DIR, f"{table}.vortex")
        conn.execute(f"CREATE VIEW raw.{table} AS SELECT * FROM read_vortex('{path}')")
    return conn


def _connect_ducklake() -> duckdb.DuckDBPyConnection:
    conn = _cap(duckdb.connect())
    conn.execute("INSTALL ducklake; LOAD ducklake")
    # READ_ONLY: plain ATTACH takes an exclusive lock, so a second concurrent
    # benchmark.py run (or a leftover one) fails instead of just reading alongside it.
    conn.execute(
        f"ATTACH 'ducklake:{DUCKLAKE_METADATA}' AS lake (DATA_PATH '{DUCKLAKE_DATA}', READ_ONLY)"
    )
    conn.execute("USE lake")
    return conn


def connect_pg() -> psycopg.Connection:
    conn = psycopg.connect(
        host=PG_HOST, port=int(PG_PORT), dbname=PG_DB, user=PG_USER, password=PG_PASSWORD
    )
    conn.autocommit = True
    return conn


def connect_ch():
    return clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT, username=CH_USER, password=CH_PASSWORD, database=CH_DB
    )


def _connect_native() -> duckdb.DuckDBPyConnection:
    return _cap(duckdb.connect(NATIVE_DB, read_only=True))


DUCKDB_ENGINES = [
    ("DuckDB native", _connect_native),
    ("Parquet", _connect_parquet),
    ("Lance", _connect_lance),
    ("Vortex", _connect_vortex),
    ("DuckLake", _connect_ducklake),
]


def timed(run_fn, handle, sql: str, runs: int) -> float:
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        run_fn(handle, sql)
        times.append(time.perf_counter() - t0)
    return min(times)


def bench_duckdb_engine(connect_fn, queries: dict, runs: int) -> list:
    """Opens one DuckDB connection, times every query on it, closes it, returns the times."""
    conn = connect_fn()
    try:
        return [timed(run_duckdb, conn, sql, runs) for sql in queries.values()]
    finally:
        conn.close()
