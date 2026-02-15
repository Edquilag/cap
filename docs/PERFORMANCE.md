# Performance and Query Optimization

## 1. Performance Goals

Primary goals for this system:
- responsive interactive search for large zonal datasets
- stable pagination order for deterministic UX
- efficient street-priority filtering and comparison summaries
- safe export behavior for large result sets

## 2. Optimization Layer

Module:
- `backend/app/services/postgres_optimization.py`

Applied at:
- API startup (`backend/app/main.py`)
- post-migration path (`backend/scripts/migrate_sqlite_to_postgres.py`)

All statements are idempotent (`CREATE ... IF NOT EXISTS`).

## 3. Index Strategy

### Baseline (from SQLAlchemy model)

Indexes exist on frequently filtered columns:
- location fields
- classification fields
- `dataset_version`
- `zonal_value`
- source lineage fields

### Additional explicit indexes

- `ix_zonal_values_query_order`
  - `(region, province, city_municipality, barangay, street_subdivision, id)`
  - helps ordered pagination path

- `ix_zonal_values_dataset_value`
  - `(dataset_version, zonal_value)`
  - helps dataset-version + numeric range workloads

- `ix_zonal_values_scope_class_version`
  - `(province, city_municipality, barangay, property_class, dataset_version)`
  - supports street fallback scope checks

- `ix_zonal_values_street_subdivision_lower`
  - expression index on `lower(street_subdivision)`
  - supports normalized street matching

### Full-text and trigram indexes

- `ix_zonal_values_search_vector` (GIN)
- trigram GIN indexes on key text columns and combined search blob
- requires `pg_trgm` extension (created when allowed)

## 4. Street-Priority Query Cost Controls

Street matching introduces scoped fallback checks (`EXISTS` correlation) to enforce:
- exact/contains named street rows first
- `ALL OTHER STREETS` fallback only when no named match exists in scope

Performance impact mitigation:
- scope composite index (`ix_zonal_values_scope_class_version`)
- normalized street expression index
- strong location filters (province/city/barangay) in UI workflow

## 5. Summary Endpoint Performance

`GET /summary` computes:
- count, min, max
- median
- catch-all count
- top property-class mix

Median implementation:
- PostgreSQL: `percentile_cont(0.5)` in SQL
- SQLite: ordered midpoint retrieval strategy

For production-scale workloads, PostgreSQL is strongly recommended.

## 6. Export Performance and Safety

`GET /export` is synchronous and optimized for operational safety:
- hard export cap via `export_max_rows` (default `50000`)
- truncation headers expose actual match count vs exported rows
- avoids unbounded memory pressure from very large exports

## 7. Validation and Monitoring

### Useful checks

List indexes:
```sql
SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'zonal_values'
ORDER BY indexname;
```

Inspect a street-filter plan:
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM zonal_values
WHERE province ILIKE '%AGUSAN%'
  AND city_municipality ILIKE '%BUTUAN%'
  AND barangay ILIKE '%DOONGAN%';
```

### Operational recommendations

- run `ANALYZE zonal_values` after large ingestion
- monitor slow query logs and `pg_stat_statements`
- tune `work_mem` and `shared_buffers` to server capacity
- schedule vacuum/analyze during maintenance windows

## 8. Tradeoffs

- More indexes increase read speed but add ingestion/write overhead.
- Full-text + trigram strategy increases disk footprint.
- Synchronous export keeps architecture simple but requires row caps for protection.
