
  
    

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
    suppliers.supplier_key,
    suppliers.name as supplier_name,
    nations.name as nation_name,
    regions.name as region_name,
    sum(lineitems.extended_price * (1 - lineitems.discount)) as revenue,
    count(distinct lineitems.order_key) as order_count,
    round(avg(lineitems.discount)::numeric, 4) as avg_discount
from "analytics"."dev"."stg_lineitems" as lineitems
inner join
    "analytics"."dev"."stg_suppliers" as suppliers
    on lineitems.supplier_key = suppliers.supplier_key
inner join
    "analytics"."dev"."stg_nations" as nations
    on suppliers.nation_key = nations.nation_key
inner join
    "analytics"."dev"."stg_regions" as regions
    on nations.region_key = regions.region_key
group by suppliers.supplier_key, suppliers.name, nations.name, regions.name
order by revenue desc
    ) as model_subq
  );
  