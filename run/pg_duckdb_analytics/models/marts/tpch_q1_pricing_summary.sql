
  
    

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
    l.return_flag,
    l.line_status,
    sum(l.quantity) as sum_qty,
    sum(l.extended_price) as sum_base_price,
    sum(l.extended_price * (1 - l.discount)) as sum_disc_price,
    sum(l.extended_price * (1 - l.discount) * (1 + l.tax)) as sum_charge,
    avg(l.quantity) as avg_qty,
    avg(l.extended_price) as avg_price,
    avg(l.discount) as avg_disc,
    count(*) as count_order
from "analytics"."dev"."stg_tpch_lineitems" as l
where l.ship_date <= date '1998-09-02'
group by l.return_flag, l.line_status
order by l.return_flag, l.line_status
    ) as model_subq
  );
  