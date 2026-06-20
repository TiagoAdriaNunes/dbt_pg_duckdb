
  
    

  create  table "analytics"."dev"."tpch_q3_shipping_priority__dbt_tmp"
  
  
    
  
  (
    order_key bigint,
    revenue double precision,
    order_date date,
    ship_priority bigint
    
    )
 ;
    insert into "analytics"."dev"."tpch_q3_shipping_priority__dbt_tmp" (
      order_key, revenue, order_date, ship_priority
    )
  
  (
    
    select order_key, revenue, order_date, ship_priority
    from (
        select
    lineitems.order_key,
    sum(lineitems.extended_price * (1 - lineitems.discount)) as revenue,
    orders.order_date,
    orders.ship_priority
from "analytics"."dev"."stg_customers" as customers
inner join "analytics"."dev"."stg_orders" as orders on customers.customer_key = orders.customer_key
inner join "analytics"."dev"."stg_lineitems" as lineitems on orders.order_key = lineitems.order_key
where
    customers.market_segment = 'BUILDING'
    and orders.order_date < date '1995-03-15'
    and lineitems.ship_date > date '1995-03-15'
group by lineitems.order_key, orders.order_date, orders.ship_priority
order by revenue desc, orders.order_date asc
limit 10
    ) as model_subq
  );
  