{% macro duckdb_scan(query) %}
    {# Macro that wraps duckdb.query() so models don't depend on the raw function name #}
    select * from duckdb.query($$ {{ query }} $$)
{% endmacro %}
