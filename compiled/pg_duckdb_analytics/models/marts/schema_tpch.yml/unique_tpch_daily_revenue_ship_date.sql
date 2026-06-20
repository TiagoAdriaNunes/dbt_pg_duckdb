
    
    

select
    ship_date as unique_field,
    count(*) as n_records

from "analytics"."dev"."tpch_daily_revenue"
where ship_date is not null
group by ship_date
having count(*) > 1


