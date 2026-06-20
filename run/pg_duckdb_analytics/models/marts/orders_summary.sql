
  
    

  create  table "analytics"."dev"."orders_summary__dbt_tmp"
  
  
    
  
  (
    customer_id bigint,
    order_count bigint,
    total_amount numeric(10,2),
    first_order_date date,
    last_order_date date
    
    )
 ;
    insert into "analytics"."dev"."orders_summary__dbt_tmp" (
      customer_id, order_count, total_amount, first_order_date, last_order_date
    )
  
  (
    
    select customer_id, order_count, total_amount, first_order_date, last_order_date
    from (
        -- Mart: aggregate completed order totals per customer.
select
    customer_id,
    count(*) as order_count,
    sum(amount)::numeric(10,2) as total_amount,
    min(created_at) as first_order_date,
    max(created_at) as last_order_date
from "analytics"."dev"."stg_orders"
where status = 'completed'
group by customer_id
    ) as model_subq
  );
  