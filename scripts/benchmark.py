"""
Benchmark TPC-H Q1, Q3, Q5 comparing pg_duckdb's two execution engines.
Both run inside the same Postgres instance against the same raw.* tables.
  PG executor  : duckdb.force_execution = false  (uses indexes, PG planner)
  DuckDB engine: duckdb.force_execution = true   (vectorized, ignores PG indexes)
"""

import os
import time

import psycopg

PG_HOST = os.environ.get("POSTGRES_HOST", "localhost")
PG_PORT = os.environ.get("POSTGRES_PORT", "5432")
PG_USER = os.environ.get("POSTGRES_USER", "postgres")
PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "duckdb")
PG_DB = os.environ.get("POSTGRES_DB", "analytics")
RUNS = int(os.environ.get("BENCHMARK_RUNS", "3"))

QUERIES = {
    "Q1 pricing summary": """
        SELECT
            l_returnflag,
            l_linestatus,
            sum(l_quantity),
            sum(l_extendedprice),
            sum(l_extendedprice * (1 - l_discount)),
            sum(l_extendedprice * (1 - l_discount) * (1 + l_tax)),
            avg(l_quantity),
            avg(l_extendedprice),
            avg(l_discount),
            count(*)
        FROM raw.lineitem
        WHERE l_shipdate <= date '1998-09-02'
        GROUP BY l_returnflag, l_linestatus
        ORDER BY l_returnflag, l_linestatus
    """,
    "Q3 shipping priority": """
        SELECT
            l.l_orderkey,
            sum(l.l_extendedprice * (1 - l.l_discount)) AS revenue,
            o.o_orderdate,
            o.o_shippriority
        FROM raw.customer AS c
        INNER JOIN raw.orders AS o ON c.c_custkey = o.o_custkey
        INNER JOIN raw.lineitem AS l ON o.o_orderkey = l.l_orderkey
        WHERE
            c.c_mktsegment = 'BUILDING'
            AND o.o_orderdate < date '1995-03-15'
            AND l.l_shipdate > date '1995-03-15'
        GROUP BY l.l_orderkey, o.o_orderdate, o.o_shippriority
        ORDER BY revenue DESC, o.o_orderdate ASC
        LIMIT 10
    """,
    "Q5 local supplier volume": """
        SELECT
            n.n_name,
            sum(l.l_extendedprice * (1 - l.l_discount)) AS revenue
        FROM raw.customer AS c
        INNER JOIN raw.orders AS o ON c.c_custkey = o.o_custkey
        INNER JOIN raw.lineitem AS l ON o.o_orderkey = l.l_orderkey
        INNER JOIN raw.supplier AS s ON l.l_suppkey = s.s_suppkey
        INNER JOIN raw.nation AS n ON s.s_nationkey = n.n_nationkey
        INNER JOIN raw.region AS r ON n.n_regionkey = r.r_regionkey
        WHERE
            r.r_name = 'ASIA'
            AND o.o_orderdate >= date '1994-01-01'
            AND o.o_orderdate < date '1995-01-01'
        GROUP BY n.n_name
        ORDER BY revenue DESC
    """,
}


def bench(cur, sql: str, use_duckdb: bool) -> float:
    cur.execute(f"SET duckdb.force_execution = {'true' if use_duckdb else 'false'}")
    times = []
    for _ in range(RUNS):
        t0 = time.perf_counter()
        cur.execute(sql)
        cur.fetchall()
        times.append(time.perf_counter() - t0)
    return min(times)


def main() -> None:
    conn = psycopg.connect(
        host=PG_HOST,
        port=int(PG_PORT),
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT count(*) FROM raw.lineitem")
    lineitem_count = cur.fetchone()[0]
    print(f"\nTPC-H benchmark  —  best of {RUNS} runs  —  {lineitem_count:,} lineitems\n")
    print(f"{'Query':<28} {'PG executor':>12} {'DuckDB engine':>14} {'DuckDB speedup':>15}")
    print("-" * 72)

    for name, sql in QUERIES.items():
        t_pg = bench(cur, sql, use_duckdb=False)
        t_dk = bench(cur, sql, use_duckdb=True)
        speedup = t_pg / t_dk
        winner = "DuckDB" if speedup > 1 else "PG    "
        print(f"{name:<28} {t_pg:>11.3f}s {t_dk:>13.3f}s {speedup:>13.1f}x  [{winner}]")

    print()
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
