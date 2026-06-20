select
    nations.name as nation_name,
    sum(lineitems.extended_price * (1 - lineitems.discount)) as revenue
from "analytics"."dev"."stg_customers" as customers
inner join "analytics"."dev"."stg_orders" as orders on customers.customer_key = orders.customer_key
inner join "analytics"."dev"."stg_lineitems" as lineitems on orders.order_key = lineitems.order_key
inner join
    "analytics"."dev"."stg_suppliers" as suppliers
    on lineitems.supplier_key = suppliers.supplier_key
inner join "analytics"."dev"."stg_nations" as nations on suppliers.nation_key = nations.nation_key
inner join "analytics"."dev"."stg_regions" as regions on nations.region_key = regions.region_key
where
    regions.name = 'ASIA'
    and orders.order_date >= date '1994-01-01'
    and orders.order_date < date '1995-01-01'
group by nations.name
order by revenue desc