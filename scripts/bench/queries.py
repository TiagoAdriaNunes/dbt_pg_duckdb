"""TPC-H queries shared by every engine in benchmark.py — same SQL, same raw.* names."""

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
