select
    c.market_segment,
    sum(l.extended_price * (1 - l.discount)) as revenue,
    count(distinct o.order_key)              as order_count,
    count(distinct o.customer_key)           as customer_count
from "analytics"."dev"."stg_tpch_lineitems" l
join "analytics"."dev"."stg_tpch_orders" o on l.order_key = o.order_key
join "analytics"."dev"."stg_tpch_customers" c on o.customer_key = c.customer_key
group by c.market_segment
order by revenue desc