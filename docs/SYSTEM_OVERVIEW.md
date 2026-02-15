# System Overview

## 1. Purpose

ZonalHub is a B2B real-estate data platform that transforms fragmented BIR zonal spreadsheets into an auditable and searchable web application.

Primary value:
- faster valuation lookup
- lower operational friction versus raw spreadsheet browsing
- source traceability for compliance and due diligence

## 2. Functional Scope

Current implementation provides:
- FastAPI backend with paginated query API
- Data ingestion scripts for workbook folders and BIR download sources
- Location cascade navigation (Region -> Province -> City/Municipality -> Barangay)
- Zonal workspace features:
  - street-priority matching with catch-all fallback policy
  - dataset (DO/year) switching and summary comparison
  - decision metrics (total, min, median, max, class mix)
  - source transparency modal
  - CSV/XLSX export with row cap safety control

Out-of-scope (current version):
- authentication and RBAC
- tenant isolation
- geospatial map overlays
- background async export jobs

## 3. High-Level Architecture

```text
                    +-----------------------------+
                    |  BIR Zonal Values Web Page |
                    +--------------+--------------+
                                   |
                                   v
                    +-----------------------------+
                    | fetch_bir_zonal_files.py    |
                    | - discover attachments       |
                    | - download workbooks         |
                    | - extract files              |
                    +--------------+--------------+
                                   |
                                   v
                    +-----------------------------+
                    | ingest_from_folder.py        |
                    | + app/services/ingestion.py  |
                    | - normalize row fields       |
                    | - load zonal_values table    |
                    +--------------+--------------+
                                   |
                                   v
 +----------------------+   +----------------------+   +----------------------+
 | React Frontend       |-->| FastAPI API Layer    |-->| PostgreSQL / SQLite  |
 | - location flow      |   | - routers            |   | - zonal_values table |
 | - summary + table    |   | - CRUD query logic   |   | - search indexes     |
 | - export + modal     |   | - export streaming   |   |                      |
 +----------------------+   +----------------------+   +----------------------+
```

## 4. Backend Modules

- `backend/app/main.py`
  - app initialization, CORS, DB/table startup
  - PostgreSQL optimization hook

- `backend/app/routers/zonal_values.py`
  - list/search endpoint
  - summary endpoint
  - export endpoint
  - location helper and record detail endpoints

- `backend/app/crud.py`
  - filter condition builder
  - street-priority ranking + catch-all fallback logic
  - aggregate summary queries (including median)
  - export query path

- `backend/app/services/postgres_optimization.py`
  - idempotent index creation for search and scope ranking

- `backend/app/services/ingestion.py`
  - workbook parsing and normalization into canonical schema

## 5. Frontend Modules

- `frontend/src/App.tsx`
  - page-mode routing via query params
  - region/province/city/barangay navigation
  - zonal workspace controls, summary, table, modal, export actions

- `frontend/src/App.css`, `frontend/src/index.css`
  - responsive layout and design system styling

- `frontend/src/data/phRegionProvinces.ts`
  - static region -> province mapping used in initial location navigation

## 6. Data Model

Primary table: `zonal_values`

Field groups:
- location hierarchy: `region`, `province`, `city_municipality`, `barangay`, `street_subdivision`
- classification: `property_class`, `property_type`
- valuation: `zonal_value`, `unit`
- traceability: `dataset_version`, `source_file`, `source_sheet`, `source_row`
- context: `rdo_code`, `effectivity_date`, `remarks`

## 7. End-to-End Request Flow

1. User selects location path to a target barangay.
2. Frontend calls `GET /api/v1/zonal-values` with location + optional `street` and `dataset_version`.
3. Backend applies:
   - global search/structured filters
   - street-priority ranking
   - fallback policy for `ALL OTHER STREETS`
4. Frontend fetches `GET /api/v1/zonal-values/summary` for decision metrics.
5. User inspects record modal with source provenance fields.
6. User can export the filtered result set via `GET /api/v1/zonal-values/export`.

## 8. Design Principles

- Traceability-first: lineage fields are first-class in API and UI.
- Preserve official ambiguity: catch-all rows are not auto-guessed into specific streets.
- Decision-ready UX: summary metrics and precision indicators are shown before deep record inspection.
- Performance-aware querying: indexes and query structure optimize read-heavy enterprise workflows.
