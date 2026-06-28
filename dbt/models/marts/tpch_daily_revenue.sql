{{
    config(
        materialized='incremental',
        unique_key='ship_date',
        incremental_strategy='delete+insert',
        on_schema_change='fail'
    )
}}

select
    lineitems.ship_date,
    count(*) as line_count,
    count(distinct lineitems.order_key) as order_count,
    round(sum(lineitems.quantity), 2)::numeric as total_quantity,
    round(sum(lineitems.extended_price * (1 - lineitems.discount)), 2)::numeric as revenue,
    round(
        sum(lineitems.extended_price * (1 - lineitems.discount) * (1 + lineitems.tax)), 2
    )::numeric as revenue_after_tax,
    avg(lineitems.discount)::numeric as avg_discount
from {{ ref('stg_lineitems') }} as lineitems

{% if is_incremental() %}
    where lineitems.ship_date > (select max(t.ship_date) from {{ this }} as t)
{% endif %}

group by lineitems.ship_date
order by lineitems.ship_date
