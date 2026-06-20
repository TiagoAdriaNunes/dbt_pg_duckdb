"""
Initialize TPC-H benchmark data into pg_duckdb.
Generates synthetic supply-chain data at the requested scale factor.
Idempotent: skips generation if tables already exist in the raw schema.
"""

import os

import duckdb

PG_HOST = os.environ.get("POSTGRES_HOST", "localhost")
PG_PORT = os.environ.get("POSTGRES_PORT", "5432")
PG_USER = os.environ.get("POSTGRES_USER", "postgres")
PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "duckdb")
PG_DB = os.environ.get("POSTGRES_DB", "analytics")
SCALE_FACTOR = float(os.environ.get("TPCH_SCALE_FACTOR", "1"))  # sf=0.1 ≈ 100 MB, sf=1 ≈ 1 GB
STAGING_DB = "/tmp/tpch_staging.duckdb"

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
            print(f"TPC-H already present ({count:,} customers). Skipping.")
            return True
    except Exception:
        pass
    return False


def generate_staging() -> None:
    size_hint = f"~{SCALE_FACTOR} GB" if SCALE_FACTOR >= 1 else f"~{int(SCALE_FACTOR * 1000)} MB"
    print(f"Generating TPC-H data (scale_factor={SCALE_FACTOR}, {size_hint})...")
    staging = duckdb.connect(STAGING_DB)
    staging.execute("SET temp_directory='/tmp'")
    staging.execute("INSTALL tpch; LOAD tpch")
    staging.execute(f"CALL dbgen(sf={SCALE_FACTOR})")
    staging.close()


def load_into_postgres(conn: duckdb.DuckDBPyConnection) -> None:
    print("Loading TPC-H tables into Postgres (raw schema)...")
    conn.execute(f"ATTACH '{STAGING_DB}' AS staging (READ_ONLY)")
    conn.execute("CREATE SCHEMA IF NOT EXISTS pg.raw")
    for table in TABLES:
        conn.execute(f"CREATE OR REPLACE TABLE pg.raw.{table} AS SELECT * FROM staging.{table}")

    counts = conn.execute(
        " UNION ALL ".join(
            f"SELECT '{t}' AS table_name, count(*) AS row_count FROM pg.raw.{t}" for t in TABLES
        )
        + " ORDER BY table_name"
    ).fetchall()

    print("Tables created in pg_duckdb (raw schema):")
    for table, count in counts:
        print(f"  {table:<12} {count:>10,} rows")


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
