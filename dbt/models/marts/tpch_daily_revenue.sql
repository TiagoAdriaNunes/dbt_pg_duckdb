{{
    config(
        materialized='incremental',
        unique_key='ship_date',
        incremental_strategy='delete+insert',
        on_schema_change='fail'
    )
}}

select
    l.ship_date,
    count(*)                                         as line_count,
    count(distinct l.order_key)                      as order_count,
    sum(l.quantity)                                  as total_quantity,
    sum(l.extended_price * (1 - l.discount))         as revenue,
    sum(l.extended_price * (1 - l.discount) * (1 + l.tax)) as revenue_after_tax,
    avg(l.discount)                                  as avg_discount
from {{ ref('stg_tpch_lineitems') }} l

{% if is_incremental() %}
    -- only process ship dates not yet in the table
    where l.ship_date > (select max(ship_date) from {{ this }})
{% endif %}

group by l.ship_date
order by l.ship_date
