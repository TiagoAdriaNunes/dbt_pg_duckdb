
  create view "analytics"."dev"."stg_tpch_suppliers__dbt_tmp"
    
    
      
  as (
    select
    s_suppkey::bigint            as supplier_key,
    s_name::text                 as name,
    s_address::text              as address,
    s_nationkey::bigint          as nation_key,
    s_phone::text                as phone,
    s_acctbal::double precision  as account_balance
from "analytics"."raw"."supplier"
  );