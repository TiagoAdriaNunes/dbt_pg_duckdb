
    
    

select
    nation_name as unique_field,
    count(*) as n_records

from "analytics"."dev"."tpch_q5_local_supplier_volume"
where nation_name is not null
group by nation_name
having count(*) > 1


