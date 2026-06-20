select
    r_regionkey::bigint as region_key,
    r_name::text        as name
from "analytics"."raw"."region"