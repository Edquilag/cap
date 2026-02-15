# Performance and Search Optimization

## 1. Performance Profile

Dataset scale in current environment:
- ~1.83 million rows in `zonal_values`

Performance goals:
- maintain acceptable search latency for interactive UI
- preserve stable pagination ordering
- keep filtering responsive under mixed query patterns

## 2. PostgreSQL Optimization Layer

Module:
- `backend/app/services/postgres_optimization.py`

Applied at:
- API startup (`backend/app/main.py`)
- SQLite to PostgreSQL migration completion (`backend/scripts/migrate_sqlite_to_postgres.py`)

The optimization layer is idempotent (`CREATE ... IF NOT EXISTS`).

## 3. Index Strategy

### Baseline B-tree indexes

Created from SQLAlchemy model `index=True` declarations, including:
- location fields
- classification fields
- `dataset_version`
- `zonal_value`
- source lineage fields

### Additional query-planning indexes

- `ix_zonal_values_query_order`  
  `(region, province, city_municipality, barangay, street_subdivision, id)`  
  Optimizes ordered pagination path.

- `ix_zonal_values_dataset_value`  
  `(dataset_version, zonal_value)`  
  Supports version+value filtered workloads.

### Trigram and full-text indexes

Required extension:
- `pg_trgm`

Implementation note:
- If `pg_trgm` cannot be created due DB privilege restrictions, the API still runs with baseline and full-text indexes; only trigram indexes are skipped.

Search indexes:
- `ix_zonal_values_rdo_code_trgm`
- `ix_zonal_values_region_trgm`
- `ix_zonal_values_province_trgm`
- `ix_zonal_values_city_municipality_trgm`
- `ix_zonal_values_barangay_trgm`
- `ix_zonal_values_street_subdivision_trgm`
- `ix_zonal_values_property_class_trgm`
- `ix_zonal_values_property_type_trgm`
- `ix_zonal_values_search_blob_trgm` (combined document expression)
- `ix_zonal_values_search_vector` (`to_tsvector('simple', ...)`)

## 4. Search Query Behavior

For PostgreSQL global `search`:
- Full-text match:
  - `to_tsvector('simple', search_blob) @@ websearch_to_tsquery('simple', :q)`
- Trigram fallback:
  - `search_blob ILIKE '%:q%'`

This dual strategy covers:
- token-based search
- substring-style search
- mixed short/long user input

SQLite fallback path:
- column-by-column `ILIKE` OR matching (no Postgres-specific operators)

## 5. Why This Works

- GIN full-text index handles lexical token search efficiently.
- GIN trigram index improves `%...%` substring matching.
- Dedicated order index reduces sort overhead on paginated listing.

## 6. Verification Commands

List indexes:
```sql
SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'zonal_values'
ORDER BY indexname;
```

Inspect query plans:
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*)
FROM zonal_values
WHERE to_tsvector('simple', ...) @@ websearch_to_tsquery('simple', 'quezon')
   OR (...) ILIKE '%quezon%';
```

## 7. Tuning Checklist

- Run `ANALYZE zonal_values;` after large imports.
- Run `VACUUM (ANALYZE)` during maintenance windows when needed.
- Tune `work_mem` and `shared_buffers` according to server capacity.
- Monitor slow query logs and `pg_stat_statements`.
- Reindex if index bloat becomes significant.

## 8. Known Tradeoffs

- More indexes improve reads but increase write/import overhead.
- Combined search expression indexes consume additional disk space.
- High-frequency updates are not currently the primary workload, so read optimization is prioritized.
