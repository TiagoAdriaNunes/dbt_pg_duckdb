
  
    

  create  table "analytics"."dev"."tpch_revenue_by_segment__dbt_tmp"
  
  
    
  
  (
    market_segment text,
    revenue double precision,
    order_count bigint,
    customer_count bigint
    
    )
 ;
    insert into "analytics"."dev"."tpch_revenue_by_segment__dbt_tmp" (
      market_segment, revenue, order_count, customer_count
    )
  
  (
    
    select market_segment, revenue, order_count, customer_count
    from (
        select
    customers.market_segment,
    sum(lineitems.extended_price * (1 - lineitems.discount)) as revenue,
    count(distinct orders.order_key) as order_count,
    count(distinct orders.customer_key) as customer_count
from "analytics"."dev"."stg_lineitems" as lineitems
inner join "analytics"."dev"."stg_orders" as orders on lineitems.order_key = orders.order_key
inner join
    "analytics"."dev"."stg_customers" as customers
    on orders.customer_key = customers.customer_key
where orders.order_date >= date '1996-01-01'
group by customers.market_segment
order by revenue desc
    ) as model_subq
  );
  