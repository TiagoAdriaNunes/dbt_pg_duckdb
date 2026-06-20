select
    l.order_key,
    sum(l.extended_price * (1 - l.discount)) as revenue,
    o.order_date,
    o.ship_priority
from {{ ref('stg_tpch_customers') }} as c
inner join {{ ref('stg_tpch_orders') }} as o on c.customer_key = o.customer_key
inner join {{ ref('stg_tpch_lineitems') }} as l on o.order_key = l.order_key
where
    c.market_segment = 'BUILDING'
    and o.order_date < date '1995-03-15'
    and l.ship_date > date '1995-03-15'
group by l.order_key, o.order_date, o.ship_priority
order by revenue desc, o.order_date asc
limit 10
