
  create view "analytics"."dev"."stg_tpch_customers__dbt_tmp"
    
    
      
  as (
    select
    c_custkey::bigint as customer_key,
    c_name::text as name,
    c_address::text as address,
    c_nationkey::bigint as nation_key,
    c_phone::text as phone,
    c_acctbal::double precision as account_balance,
    c_mktsegment::text as market_segment
from "analytics"."raw"."customer"
  );