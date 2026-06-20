
  
    

  create  table "analytics"."dev"."tpch_supplier_performance__dbt_tmp"
  
  
    
  
  (
    supplier_key bigint,
    supplier_name text,
    nation_name text,
    region_name text,
    revenue double precision,
    order_count bigint,
    avg_discount numeric(18,4)
    
    )
 ;
    insert into "analytics"."dev"."tpch_supplier_performance__dbt_tmp" (
      supplier_key, supplier_name, nation_name, region_name, revenue, order_count, avg_discount
    )
  
  (
    
    select supplier_key, supplier_name, nation_name, region_name, revenue, order_count, avg_discount
    from (
        select
    s.supplier_key,
    s.name                                        as supplier_name,
    n.name                                        as nation_name,
    r.name                                        as region_name,
    sum(l.extended_price * (1 - l.discount))      as revenue,
    count(distinct l.order_key)                   as order_count,
    round(avg(l.discount)::numeric, 4)            as avg_discount
from "analytics"."dev"."stg_tpch_lineitems" l
join "analytics"."dev"."stg_tpch_suppliers" s on l.supplier_key = s.supplier_key
join "analytics"."dev"."stg_tpch_nations" n on s.nation_key = n.nation_key
join "analytics"."dev"."stg_tpch_regions" r on n.region_key = r.region_key
group by s.supplier_key, s.name, n.name, r.name
order by revenue desc
    ) as model_subq
  );
  