
  create view "analytics"."dev"."stg_tpch_nations__dbt_tmp"
    
    
      
  as (
    select
    n_nationkey::bigint as nation_key,
    n_name::text        as name,
    n_regionkey::bigint as region_key
from "analytics"."raw"."nation"
  );