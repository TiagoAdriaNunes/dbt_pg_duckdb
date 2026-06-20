
  
    

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
    l.order_key,
    sum(l.extended_price * (1 - l.discount)) as revenue,
    o.order_date,
    o.ship_priority
from "analytics"."dev"."stg_tpch_customers" as c
inner join "analytics"."dev"."stg_tpch_orders" as o on c.customer_key = o.customer_key
inner join "analytics"."dev"."stg_tpch_lineitems" as l on o.order_key = l.order_key
where
    c.market_segment = 'BUILDING'
    and o.order_date < date '1995-03-15'
    and l.ship_date > date '1995-03-15'
group by l.order_key, o.order_date, o.ship_priority
order by revenue desc, o.order_date asc
limit 10
    ) as model_subq
  );
  