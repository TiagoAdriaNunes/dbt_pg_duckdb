select
    o_orderkey::bigint       as order_key,
    o_custkey::bigint        as customer_key,
    o_orderstatus::text      as status,
    o_totalprice::double precision as total_price,
    o_orderdate::date        as order_date,
    o_orderpriority::text    as priority,
    o_clerk::text            as clerk,
    o_shippriority::bigint   as ship_priority
from "analytics"."raw"."orders"