select
    lineitems.return_flag,
    lineitems.line_status,
    round(sum(lineitems.quantity), 2) as sum_qty,
    round(sum(lineitems.extended_price), 2) as sum_base_price,
    round(sum(lineitems.extended_price * (1 - lineitems.discount)), 2) as sum_disc_price,
    round(sum(lineitems.extended_price * (1 - lineitems.discount) * (1 + lineitems.tax)), 2) as sum_charge,
    avg(lineitems.quantity) as avg_qty,
    avg(lineitems.extended_price) as avg_price,
    avg(lineitems.discount) as avg_disc,
    count(*) as count_order
from "analytics"."dev"."stg_lineitems" as lineitems
where lineitems.ship_date <= date '1998-09-02'
group by lineitems.return_flag, lineitems.line_status
order by lineitems.return_flag, lineitems.line_status