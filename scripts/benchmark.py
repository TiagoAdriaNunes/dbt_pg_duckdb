"""
Benchmark TPC-H Q1, Q3, Q5 across every engine set up by scripts/init_tpch.py.
Engine details: scripts/bench/engines.py. Queries: scripts/bench/queries.py.

The 5 DuckDB-backed engines connect one at a time (see engines.DUCKDB_ENGINES)
instead of all upfront, to keep peak memory down on small boxes.
"""

import os

from bench import engines
from bench.queries import QUERIES

RUNS = int(os.environ.get("BENCHMARK_RUNS", "3"))


def main() -> None:
    pg_conn = engines.connect_pg()
    pg_cur = pg_conn.cursor()
    ch_client = engines.connect_ch()

    pg_cur.execute("SET duckdb.force_execution = false")
    pg_cur.execute("SELECT count(*) FROM raw.lineitem")
    lineitem_count = pg_cur.fetchone()[0]
    print(f"\nTPC-H benchmark  —  best of {RUNS} runs  —  {lineitem_count:,} lineitems\n")

    query_names = list(QUERIES)
    query_sqls = list(QUERIES.values())

    times = {
        "PG (native)": [
            engines.timed(engines.run_pg_native, pg_cur, sql, RUNS) for sql in query_sqls
        ],
        "PG (duckdb)": [
            engines.timed(engines.run_pg_duckdb, pg_cur, sql, RUNS) for sql in query_sqls
        ],
        "ClickHouse": [
            engines.timed(engines.run_clickhouse, ch_client, sql, RUNS) for sql in query_sqls
        ],
    }
    pg_conn.close()
    ch_client.close()

    for label, connect_fn in engines.DUCKDB_ENGINES:
        times[label] = engines.bench_duckdb_engine(connect_fn, QUERIES, RUNS)

    labels = list(times)
    label_width = max(len(label) for label in labels) + 2
    col_width = max(max(len(n) for n in query_names), label_width) + 2

    header = f"{'Engine':<{label_width}}" + "".join(f"{n:>{col_width}}" for n in query_names)
    print(header)
    print("-" * (label_width + col_width * len(query_names)))

    for label in labels:
        row = "".join(f"{t:>{col_width - 1}.3f}s" for t in times[label])
        print(f"{label:<{label_width}}{row}")

    print("-" * (label_width + col_width * len(query_names)))
    fastest = "".join(
        f"{min(times, key=lambda lbl: times[lbl][i]):>{col_width}}" for i in range(len(query_names))
    )
    print(f"{'Fastest':<{label_width}}{fastest}")

    print()


if __name__ == "__main__":
    main()
