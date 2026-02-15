# API Reference

Base URL (default local):
- `http://localhost:8000`

API prefix:
- `/api/v1`

Interactive docs:
- `http://localhost:8000/docs`

## 1. Health Endpoint

### `GET /health`

Purpose:
- Service liveness check.

Response:
```json
{
  "status": "ok"
}
```

## 2. List/Search Zonal Values

### `GET /api/v1/zonal-values`

Returns paginated records with global search, structured filters, and street-priority logic.

### Query Parameters

- `search` (string, optional)
- `region` (string, optional)
- `province` (string, optional)
- `city` (string, optional)
- `barangay` (string, optional)
- `property_class` (string, optional)
- `property_type` (string, optional)
- `dataset_version` (string, optional, exact match)
- `street` (string, optional)
- `min_value` (decimal, optional)
- `max_value` (decimal, optional)
- `page` (int, default `1`, min `1`)
- `page_size` (int, default from config, max from config)

### Street-priority behavior

When `street` is provided:
1. Exact street/subdivision match rows rank highest.
2. Named street rows containing the query rank next.
3. `ALL OTHER STREETS` rows appear only as fallback when no named row matches in the same:
   - province
   - city/municipality
   - barangay
   - property class
   - dataset version

### Response shape

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 25
}
```

## 3. Decision Summary

### `GET /api/v1/zonal-values/summary`

Returns summary metrics for the same filter set used by listing.

Query parameters:
- same as list endpoint except pagination

Response shape:
```json
{
  "total_records": 0,
  "min_value": null,
  "max_value": null,
  "median_value": null,
  "catch_all_records": 0,
  "exact_street_records": 0,
  "class_mix": [
    {
      "property_class": "R-1",
      "count": 123
    }
  ]
}
```

Notes:
- `median_value` uses `percentile_cont` on PostgreSQL and deterministic ordered median logic on SQLite.
- `class_mix` is capped to the top 8 classes by count.

## 4. Export Endpoint

### `GET /api/v1/zonal-values/export`

Exports filtered records in `csv` or `xlsx`.

Query parameters:
- `format` (`csv` or `xlsx`, default `csv`)
- same filters as list endpoint (except pagination)

Output fields include source transparency metadata:
- `source_file`
- `source_sheet`
- `source_row`
- `dataset_version`
- plus all location/classification/value fields

Truncation controls:
- Export row count is capped by `export_max_rows` (default `50000`).
- If capped, response includes:
  - `X-Export-Truncated: true`
  - `X-Export-Row-Limit`
  - `X-Export-Total-Matches`

## 5. Filter Options

### `GET /api/v1/zonal-values/filters`

Returns distinct values for dropdown/filter population.

Response shape:
```json
{
  "regions": [],
  "provinces": [],
  "cities": [],
  "barangays": [],
  "property_classes": [],
  "property_types": [],
  "dataset_versions": []
}
```

## 6. Location Cascade Helper

### `GET /api/v1/zonal-values/location-children`

Query parameters:
- `province` (required)
- `city` (optional)
- `limit` (optional, default `1000`, max `5000`)

Response shape:
```json
{
  "cities": [],
  "barangays": []
}
```

Behavior:
- always returns cities for `province`
- returns barangays only when `city` is provided

## 7. Record Details

### `GET /api/v1/zonal-values/{zonal_value_id}`

Returns one record by ID.

Behavior:
- `404` when record does not exist

## 8. Error Handling

Typical responses:
- `422` invalid query parameter types/ranges
- `404` missing record on detail endpoint
- `500` unhandled server-side exception

Production recommendation:
- use structured error envelope + correlation ID middleware.
