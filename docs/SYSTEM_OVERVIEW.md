# System Overview

## 1. Purpose

ZonalHub is a B2B real-estate data platform that converts fragmented BIR zonal-value spreadsheets into a searchable application.

Primary objective:
- Let users find zonal values quickly by location and property attributes without manually navigating workbook files and sheet structures.

Core value delivered:
- Faster due diligence
- Unified data structure across many workbook layouts
- Source traceability (`source_file`, `source_sheet`, `source_row`) for audit confidence

## 2. Current Scope

The current implementation provides:
- FastAPI backend for read APIs
- PostgreSQL or SQLite persistence (PostgreSQL recommended for production)
- Data ingestion scripts for local workbook folders
- BIR page fetch script that downloads official zonal attachments
- React frontend with filtering, search, pagination, and detail panel

Out-of-scope (current version):
- Authentication and role-based access control
- Multi-tenant data isolation
- Export jobs and async workflows
- Geospatial map overlays

## 3. High-Level Architecture

```text
                    +-----------------------------+
                    |  BIR Zonal Values Web Page |
                    +--------------+--------------+
                                   |
                                   v
                    +-----------------------------+
                    | fetch_bir_zonal_files.py    |
                    | - scrape template codes      |
                    | - query BIR CMS API          |
                    | - download attachments       |
                    | - extract workbooks          |
                    +--------------+--------------+
                                   |
                                   v
                    +-----------------------------+
                    | ingest_from_folder.py        |
                    | + app/services/ingestion.py  |
                    | - parse workbook rows        |
                    | - normalize fields           |
                    | - load zonal_values table    |
                    +--------------+--------------+
                                   |
                                   v
 +----------------------+   +----------------------+   +----------------------+
 | React Frontend       |-->| FastAPI API Layer    |-->| PostgreSQL / SQLite  |
 | - filters            |   | - routers            |   | - zonal_values table |
 | - table              |   | - CRUD query builder |   | - search indexes     |
 | - detail view        |   | - pagination         |   |                      |
 +----------------------+   +----------------------+   +----------------------+
```

## 4. Backend Components

- `backend/app/main.py`  
  App bootstrap, CORS setup, health route, router registration, startup DB/table/index initialization.

- `backend/app/config.py`  
  Environment-driven settings (`DATABASE_URL`, page-size limits, CORS origins).

- `backend/app/models.py`  
  SQLAlchemy model for `zonal_values`.

- `backend/app/crud.py`  
  Query logic for filtered search, record retrieval, and filter option extraction.

- `backend/app/routers/zonal_values.py`  
  API contract for list/details/filter endpoints.

- `backend/app/services/ingestion.py`  
  Workbook normalization and row-level extraction logic.

- `backend/app/services/postgres_optimization.py`  
  Idempotent PostgreSQL index and extension creation for search performance.

## 5. Frontend Components

- `frontend/src/App.tsx`
  - Search/filter form
  - Paginated table
  - Selected-record details panel
  - API integration and client-side state management

- `frontend/src/App.css`, `frontend/src/index.css`
  - UI styling and layout behavior

## 6. Data Model

Primary table: `zonal_values`

Core field groups:
- Location hierarchy: `region`, `province`, `city_municipality`, `barangay`, `street_subdivision`
- Classification: `property_class`, `property_type`
- Pricing: `zonal_value`, `unit`
- Versioning/traceability: `dataset_version`, `source_file`, `source_sheet`, `source_row`
- Context: `rdo_code`, `effectivity_date`, `remarks`

Design notes:
- Some fields are modeled as `Text` because BIR spreadsheets contain long, non-standard strings.
- Data lineage fields support source validation and audit workflows.

## 7. End-to-End Request Flow

1. User submits filters/search in frontend.
2. Frontend builds query string and calls `GET /api/v1/zonal-values`.
3. Backend composes SQLAlchemy conditions in `crud.get_zonal_values`.
4. Backend runs:
   - count query for total matches
   - paginated ordered query for current page
5. API returns `items`, `total`, `page`, and `page_size`.
6. Frontend renders table rows; selected row shows full detail + lineage.

## 8. Design Principles Used

- Traceability first: every row stores source file/sheet/row metadata.
- Lenient ingestion: parser handles inconsistent workbook formats with alias mapping and heuristics.
- Query ergonomics: both global search and structured filters.
- Production path: PostgreSQL optimization layer for large datasets.

