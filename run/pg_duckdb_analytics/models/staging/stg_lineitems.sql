
  create view "analytics"."dev"."stg_lineitems__dbt_tmp"
    
    
      
  as (
    select
    l_orderkey::bigint as order_key,
    l_partkey::bigint as part_key,
    l_suppkey::bigint as supplier_key,
    l_linenumber::bigint as line_number,
    l_quantity::numeric(12, 2) as quantity,
    l_extendedprice::numeric(15, 2) as extended_price,
    l_discount::numeric(4, 2) as discount,
    l_tax::numeric(4, 2) as tax,
    l_returnflag::text as return_flag,
    l_linestatus::text as line_status,
    l_shipdate::date as ship_date,
    l_commitdate::date as commit_date,
    l_receiptdate::date as receipt_date,
    l_shipinstruct::text as ship_instruct,
    l_shipmode::text as ship_mode
from "analytics"."raw"."lineitem"
  );