select
    s.supplier_key,
    s.name as supplier_name,
    n.name as nation_name,
    r.name as region_name,
    sum(l.extended_price * (1 - l.discount)) as revenue,
    count(distinct l.order_key) as order_count,
    round(avg(l.discount)::numeric, 4) as avg_discount
from {{ ref('stg_tpch_lineitems') }} as l
inner join
    {{ ref('stg_tpch_suppliers') }} as s
    on l.supplier_key = s.supplier_key
inner join {{ ref('stg_tpch_nations') }} as n on s.nation_key = n.nation_key
inner join {{ ref('stg_tpch_regions') }} as r on n.region_key = r.region_key
group by s.supplier_key, s.name, n.name, r.name
order by revenue desc
