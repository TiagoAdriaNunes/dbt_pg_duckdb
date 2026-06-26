select
    suppliers.supplier_key,
    suppliers.name as supplier_name,
    nations.name as nation_name,
    regions.name as region_name,
    sum(lineitems.extended_price * (1 - lineitems.discount)) as revenue,
    count(distinct lineitems.order_key) as order_count,
    round(avg(lineitems.discount)::numeric, 4) as avg_discount
from {{ ref('stg_lineitems') }} as lineitems
inner join
    {{ ref('stg_suppliers') }} as suppliers
    on lineitems.supplier_key = suppliers.supplier_key
inner join
    {{ ref('stg_nations') }} as nations
    on suppliers.nation_key = nations.nation_key
inner join
    {{ ref('stg_regions') }} as regions
    on nations.region_key = regions.region_key
where lineitems.ship_date >= date '1996-01-01'
group by suppliers.supplier_key, suppliers.name, nations.name, regions.name
order by revenue desc
