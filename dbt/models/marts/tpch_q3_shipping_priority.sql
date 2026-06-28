select
    lineitems.order_key,
    round(sum(lineitems.extended_price * (1 - lineitems.discount)), 2) as revenue,
    orders.order_date,
    orders.ship_priority
from {{ ref('stg_customers') }} as customers
inner join {{ ref('stg_orders') }} as orders on customers.customer_key = orders.customer_key
inner join {{ ref('stg_lineitems') }} as lineitems on orders.order_key = lineitems.order_key
where
    customers.market_segment = 'BUILDING'
    and orders.order_date < date '1995-03-15'
    and lineitems.ship_date > date '1995-03-15'
group by lineitems.order_key, orders.order_date, orders.ship_priority
order by revenue desc, orders.order_date asc
limit 10
