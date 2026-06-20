#!/usr/bin/env bash
set -e

duckdb \
  -cmd "ATTACH 'host=${POSTGRES_HOST:-localhost} port=${POSTGRES_PORT:-5432} dbname=${POSTGRES_DB:-analytics} user=${POSTGRES_USER:-postgres} password=${POSTGRES_PASSWORD:-duckdb}' AS pg (TYPE POSTGRES);" \
  -cmd "USE pg;"
