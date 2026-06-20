
  
    

  create  table "analytics"."dev"."tpch_q5_local_supplier_volume__dbt_tmp"
  
  
    
  
  (
    nation_name text,
    revenue double precision
    
    )
 ;
    insert into "analytics"."dev"."tpch_q5_local_supplier_volume__dbt_tmp" (
      nation_name, revenue
    )
  
  (
    
    select nation_name, revenue
    from (
        select
    n.name as nation_name,
    sum(l.extended_price * (1 - l.discount)) as revenue
from "analytics"."dev"."stg_tpch_customers" as c
inner join "analytics"."dev"."stg_tpch_orders" as o on c.customer_key = o.customer_key
inner join "analytics"."dev"."stg_tpch_lineitems" as l on o.order_key = l.order_key
inner join
    "analytics"."dev"."stg_tpch_suppliers" as s
    on l.supplier_key = s.supplier_key
inner join "analytics"."dev"."stg_tpch_nations" as n on s.nation_key = n.nation_key
inner join "analytics"."dev"."stg_tpch_regions" as r on n.region_key = r.region_key
where
    r.name = 'ASIA'
    and o.order_date >= date '1994-01-01'
    and o.order_date < date '1995-01-01'
group by n.name
order by revenue desc
    ) as model_subq
  );
  