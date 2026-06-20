"""
Insert a batch of new lineitem rows with ship_date = today into raw.lineitem.
Offsets order keys to avoid collisions with existing TPC-H data.
Run before `make dbt-run` to trigger the incremental model.
"""

import os
from datetime import date

import duckdb

PG_HOST = os.environ.get("POSTGRES_HOST", "localhost")
PG_PORT = os.environ.get("POSTGRES_PORT", "5432")
PG_USER = os.environ.get("POSTGRES_USER", "postgres")
PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "duckdb")
PG_DB = os.environ.get("POSTGRES_DB", "analytics")
BATCH_SIZE = int(os.environ.get("SIMULATE_BATCH_SIZE", "1000"))

PG_CONN = f"host={PG_HOST} port={PG_PORT} dbname={PG_DB} user={PG_USER} password={PG_PASSWORD}"


def main() -> None:
    conn = duckdb.connect()
    conn.execute("INSTALL postgres; LOAD postgres")
    conn.execute(f"ATTACH '{PG_CONN}' AS pg (TYPE POSTGRES)")

    max_order_key = conn.execute("SELECT max(l_orderkey) FROM pg.raw.lineitem").fetchone()[0]
    today = date.today().isoformat()

    conn.execute(f"""
        INSERT INTO pg.raw.lineitem
        SELECT
            l_orderkey + {max_order_key}  AS l_orderkey,
            l_partkey,
            l_suppkey,
            l_linenumber,
            l_quantity,
            l_extendedprice,
            l_discount,
            l_tax,
            l_returnflag,
            l_linestatus,
            '{today}'::date               AS l_shipdate,
            l_commitdate,
            l_receiptdate,
            l_shipinstruct,
            l_shipmode,
            l_comment
        FROM pg.raw.lineitem
        LIMIT {BATCH_SIZE}
    """)

    count = conn.execute(
        f"SELECT count(*) FROM pg.raw.lineitem WHERE l_shipdate = '{today}'"
    ).fetchone()[0]
    print(f"Inserted {count:,} new lineitem rows with ship_date={today}")
    conn.execute("""
        UPDATE pg.raw.customer
        SET c_mktsegment = 'MACHINERY'
        WHERE c_custkey IN (
            SELECT c_custkey FROM pg.raw.customer
            WHERE c_mktsegment = 'BUILDING'
            LIMIT 100
        )
    """)
    print("Updated 100 customers: BUILDING -> MACHINERY (triggers snapshot SCD2 rows)")
    conn.close()


if __name__ == "__main__":
    main()
