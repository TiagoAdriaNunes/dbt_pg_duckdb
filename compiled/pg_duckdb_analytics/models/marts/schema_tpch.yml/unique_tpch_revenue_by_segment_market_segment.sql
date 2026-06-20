
    
    

select
    market_segment as unique_field,
    count(*) as n_records

from "analytics"."dev"."tpch_revenue_by_segment"
where market_segment is not null
group by market_segment
having count(*) > 1


