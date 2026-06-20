

select
    l.ship_date,
    count(*)                                         as line_count,
    count(distinct l.order_key)                      as order_count,
    sum(l.quantity)                                  as total_quantity,
    sum(l.extended_price * (1 - l.discount))         as revenue,
    sum(l.extended_price * (1 - l.discount) * (1 + l.tax)) as revenue_after_tax,
    avg(l.discount)                                  as avg_discount
from "analytics"."dev"."stg_tpch_lineitems" l


    -- only process ship dates not yet in the table
    where l.ship_date > (select max(ship_date) from "analytics"."dev"."tpch_daily_revenue")


group by l.ship_date
order by l.ship_date