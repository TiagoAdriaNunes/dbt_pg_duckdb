CREATE EXTENSION IF NOT EXISTS pg_duckdb;
ALTER ROLE postgres SET duckdb.force_execution = true;
