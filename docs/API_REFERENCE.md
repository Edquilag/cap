# API Reference

Base URL (default local):
- `http://localhost:8000`

API prefix (default):
- `/api/v1`

Interactive docs:
- `http://localhost:8000/docs`

## 1. Health Endpoint

### `GET /health`

Purpose:
- Basic service liveness check.

Response:
```json
{
  "status": "ok"
}
```

## 2. List/Search Zonal Values

### `GET /api/v1/zonal-values`

Returns paginated records with optional global search and structured filters.

### Query Parameters

- `search` (string, optional)  
  Global search across location/property fields and numeric value text.

- `region` (string, optional)
- `province` (string, optional)
- `city` (string, optional)
- `barangay` (string, optional)
- `property_class` (string, optional)
- `property_type` (string, optional)
- `dataset_version` (string, optional)
- `min_value` (decimal, optional)
- `max_value` (decimal, optional)

- `page` (int, default `1`, min `1`)
- `page_size` (int, default from config, max from config)

### Example Request

```http
GET /api/v1/zonal-values?search=Quezon&province=Quezon&page=1&page_size=25
```

### Example Response Shape

```json
{
  "items": [
    {
      "id": 123,
      "rdo_code": "RDO No. 39",
      "region": "REGION IV-A",
      "province": "QUEZON",
      "city_municipality": "LUCENA CITY",
      "barangay": "Barangay 1",
      "street_subdivision": "Sample Street",
      "property_class": "R-1",
      "property_type": "Land",
      "zonal_value": "12000.00",
      "unit": "PHP per sq.m.",
      "effectivity_date": null,
      "remarks": "Vicinity: ...",
      "source_file": "....xls",
      "source_sheet": "Sheet1",
      "source_row": 42,
      "dataset_version": "BIR-ZONAL-2026-02-15",
      "created_at": "2026-02-15T12:34:56.000000+00:00"
    }
  ],
  "total": 90305,
  "page": 1,
  "page_size": 25
}
```

## 3. Filter Options

### `GET /api/v1/zonal-values/filters`

Returns distinct values (capped) for frontend filter dropdowns.

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

Notes:
- Each option list is currently limited to 500 values in backend logic.
- For extremely large distributions, this cap should be reviewed and may require dedicated lookup endpoints with pagination.

## 4. Record Details

### `GET /api/v1/zonal-values/{zonal_value_id}`

Returns one record by primary key.

Behavior:
- `404` if ID does not exist.

## 5. Location Cascade Helper

### `GET /api/v1/zonal-values/location-children`

Provides dependent location options for the new UI flow.

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
- Always returns city list for the given province.
- Returns barangay list only when `city` is provided.

## 6. Query Semantics

Search behavior:
- PostgreSQL:
  - Uses full-text search (`to_tsvector` + `websearch_to_tsquery`) over a combined search document.
  - Includes trigram-backed `ILIKE` fallback on the same combined document.
- SQLite:
  - Uses column-wise `ILIKE` OR matching.

Structured filters:
- Most text filters use case-insensitive contains matching (`ILIKE '%value%'`).
- `dataset_version` uses exact matching.
- `min_value`/`max_value` apply numeric comparisons.

Ordering:
- Results are sorted by:
  - `region`
  - `province`
  - `city_municipality`
  - `barangay`
  - `street_subdivision`
  - (then implicit row order by ID as tie-break behavior in index strategy)

## 7. Error Handling

Typical error responses:
- `422` for invalid query parameter types/ranges (FastAPI validation)
- `404` for missing record on detail endpoint
- `500` for unhandled server-side failures

Recommendation:
- Add structured error envelopes with correlation IDs for production incident tracing.
