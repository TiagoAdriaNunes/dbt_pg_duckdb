{% snapshot snap_tpch_customers %}

{{
    config(
        target_schema='snapshots',
        unique_key='customer_key',
        strategy='check',
        check_cols=['market_segment', 'account_balance', 'address', 'phone'],
        invalidate_hard_deletes=True,
    )
}}

    select * from {{ ref('stg_tpch_customers') }}

{% endsnapshot %}
