
  
    

  create  table "analytics"."dev"."tpch_q1_pricing_summary__dbt_tmp"
  
  
    
  
  (
    return_flag text,
    line_status text,
    sum_qty double precision,
    sum_base_price double precision,
    sum_disc_price double precision,
    sum_charge double precision,
    avg_qty double precision,
    avg_price double precision,
    avg_disc double precision,
    count_order bigint
    
    )
 ;
    insert into "analytics"."dev"."tpch_q1_pricing_summary__dbt_tmp" (
      return_flag, line_status, sum_qty, sum_base_price, sum_disc_price, sum_charge, avg_qty, avg_price, avg_disc, count_order
    )
  
  (
    
    select return_flag, line_status, sum_qty, sum_base_price, sum_disc_price, sum_charge, avg_qty, avg_price, avg_disc, count_order
    from (
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
from "analytics"."dev"."stg_lineitems" as lineitems
where lineitems.ship_date <= date '1998-09-02'
group by lineitems.return_flag, lineitems.line_status
order by lineitems.return_flag, lineitems.line_status
    ) as model_subq
  );
  