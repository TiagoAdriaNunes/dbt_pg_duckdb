-- Mart: aggregate completed order totals per customer.
select
    customer_id,
    count(*) as order_count,
    sum(amount)::numeric(10, 2) as total_amount,
    min(created_at) as first_order_date,
    max(created_at) as last_order_date
from {{ ref('stg_orders') }}
where status = 'completed'
group by customer_id
