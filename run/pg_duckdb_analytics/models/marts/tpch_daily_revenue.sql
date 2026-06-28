
      
  
    

  create  table "analytics"."dev"."tpch_daily_revenue"
  
  
    
  
  (
    ship_date date,
    line_count bigint,
    order_count bigint,
    total_quantity numeric(38,2),
    revenue numeric(38,2),
    revenue_after_tax numeric(38,2),
    avg_discount double precision
    
    )
 ;
    insert into "analytics"."dev"."tpch_daily_revenue" (
      ship_date, line_count, order_count, total_quantity, revenue, revenue_after_tax, avg_discount
    )
  
  (
    
    select ship_date, line_count, order_count, total_quantity, revenue, revenue_after_tax, avg_discount
    from (
        

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



group by lineitems.ship_date
order by lineitems.ship_date
    ) as model_subq
  );
  
  