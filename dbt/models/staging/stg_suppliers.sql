select
    s_suppkey::bigint as supplier_key,
    s_name::text as name,
    s_address::text as address,
    s_nationkey::bigint as nation_key,
    s_phone::text as phone,
    s_acctbal::numeric(15, 2) as account_balance
from {{ source('tpch', 'supplier') }}
