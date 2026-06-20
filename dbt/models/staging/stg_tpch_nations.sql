select
    n_nationkey::bigint as nation_key,
    n_name::text        as name,
    n_regionkey::bigint as region_key
from {{ source('tpch', 'nation') }}
