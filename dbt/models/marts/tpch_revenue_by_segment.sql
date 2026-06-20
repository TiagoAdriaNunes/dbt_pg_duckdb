select
    c.market_segment,
    sum(l.extended_price * (1 - l.discount)) as revenue,
    count(distinct o.order_key) as order_count,
    count(distinct o.customer_key) as customer_count
from {{ ref('stg_tpch_lineitems') }} as l
inner join {{ ref('stg_tpch_orders') }} as o on l.order_key = o.order_key
inner join
    {{ ref('stg_tpch_customers') }} as c
    on o.customer_key = c.customer_key
group by c.market_segment
order by revenue desc
