
    
    

select
    nation_key as unique_field,
    count(*) as n_records

from "analytics"."dev"."stg_tpch_nations"
where nation_key is not null
group by nation_key
having count(*) > 1


