

select
    lineitems.ship_date,
    count(*) as line_count,
    count(distinct lineitems.order_key) as order_count,
    round(sum(lineitems.quantity), 2)::numeric as total_quantity,
    round(sum(lineitems.extended_price * (1 - lineitems.discount)), 2)::numeric as revenue,
    round(
        sum(lineitems.extended_price * (1 - lineitems.discount) * (1 + lineitems.tax)), 2
    )::numeric as revenue_after_tax,
    avg(lineitems.discount) as avg_discount
from "analytics"."dev"."stg_lineitems" as lineitems


    where lineitems.ship_date > (select max(t.ship_date) from "analytics"."dev"."tpch_daily_revenue" as t)


group by lineitems.ship_date
order by lineitems.ship_date