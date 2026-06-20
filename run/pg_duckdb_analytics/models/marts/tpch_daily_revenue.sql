
      
  
    

  create  table "analytics"."dev"."tpch_daily_revenue"
  
  
    
  
  (
    ship_date date,
    line_count bigint,
    order_count bigint,
    total_quantity double precision,
    revenue double precision,
    revenue_after_tax double precision,
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
    l.ship_date,
    count(*) as line_count,
    count(distinct l.order_key) as order_count,
    sum(l.quantity) as total_quantity,
    sum(l.extended_price * (1 - l.discount)) as revenue,
    sum(l.extended_price * (1 - l.discount) * (1 + l.tax)) as revenue_after_tax,
    avg(l.discount) as avg_discount
from "analytics"."dev"."stg_tpch_lineitems" as l



group by l.ship_date
order by l.ship_date
    ) as model_subq
  );
  
  