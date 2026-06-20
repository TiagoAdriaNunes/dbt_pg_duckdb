select
    l_orderkey::bigint as order_key,
    l_partkey::bigint as part_key,
    l_suppkey::bigint as supplier_key,
    l_linenumber::bigint as line_number,
    l_quantity::double precision as quantity,
    l_extendedprice::double precision as extended_price,
    l_discount::double precision as discount,
    l_tax::double precision as tax,
    l_returnflag::text as return_flag,
    l_linestatus::text as line_status,
    l_shipdate::date as ship_date,
    l_commitdate::date as commit_date,
    l_receiptdate::date as receipt_date,
    l_shipinstruct::text as ship_instruct,
    l_shipmode::text as ship_mode
from "analytics"."raw"."lineitem"