-- Staging model: cast and clean raw_orders seed data.
-- Uses standard SQL; pg_duckdb accelerates the scan automatically.
select
    order_id::bigint,
    customer_id::bigint,
    amount::numeric(10, 2),
    status,
    created_at::date
from {{ ref('raw_orders') }}
where status != 'cancelled'
