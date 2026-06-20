select
    lineitems.return_flag,
    lineitems.line_status,
    sum(lineitems.quantity) as sum_qty,
    sum(lineitems.extended_price) as sum_base_price,
    sum(lineitems.extended_price * (1 - lineitems.discount)) as sum_disc_price,
    sum(lineitems.extended_price * (1 - lineitems.discount) * (1 + lineitems.tax)) as sum_charge,
    avg(lineitems.quantity) as avg_qty,
    avg(lineitems.extended_price) as avg_price,
    avg(lineitems.discount) as avg_disc,
    count(*) as count_order
from {{ ref('stg_lineitems') }} as lineitems
where lineitems.ship_date <= date '1998-09-02'
group by lineitems.return_flag, lineitems.line_status
order by lineitems.return_flag, lineitems.line_status
