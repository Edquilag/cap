# Operations Runbook

## 1. Environment Model

Recommended environments:
- `dev`
- `staging`
- `prod`

Each environment should have:
- separate database
- separate credentials
- controlled dataset-version workflow

## 2. Prerequisites

- Python 3.12+
- Node.js 20+
- npm 10+
- PostgreSQL 14+ recommended for production

## 3. Backend Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health:
- `GET http://localhost:8000/health`

API docs:
- `http://localhost:8000/docs`

## 4. Frontend Setup

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

App URL:
- `http://localhost:5173`

## 5. Data Operations

### A. Fetch official BIR files

```powershell
cd backend
.venv\Scripts\activate
python scripts\fetch_bir_zonal_files.py
```

Outputs:
- `data/raw/bir_zonal/downloads`
- `data/raw/bir_zonal/extracted`
- `data/raw/bir_zonal/manifest.json`

### B. Ingest workbook folder

```powershell
python scripts\ingest_from_folder.py --folder ..\data\raw\bir_zonal\extracted --dataset-version BIR-ZONAL-2026-02-15
```

### C. Migrate SQLite to PostgreSQL

```powershell
python scripts\migrate_sqlite_to_postgres.py --batch-size 20000
```

## 6. Runtime Smoke Checklist

Verify these routes after deployment:
- `GET /health`
- `GET /api/v1/zonal-values/filters`
- `GET /api/v1/zonal-values/location-children?province=<...>`
- `GET /api/v1/zonal-values?province=<...>&city=<...>&barangay=<...>&page=1&page_size=25`
- `GET /api/v1/zonal-values/summary?province=<...>&city=<...>&barangay=<...>`
- `GET /api/v1/zonal-values/export?province=<...>&city=<...>&barangay=<...>&format=csv`

## 7. Export Operations

Export behavior:
- synchronous response
- capped by `export_max_rows` (default `50000`)
- truncation metadata via response headers when matched rows exceed cap

Operational guidance:
- monitor response size and duration
- track frequent high-volume export callers
- lower `export_max_rows` if infrastructure is constrained

## 8. Deployment Workflow

1. Deploy backend.
2. Ensure startup index optimization runs successfully.
3. Ingest/promote target dataset version.
4. Smoke-test key endpoints.
5. Deploy frontend with correct `VITE_API_BASE_URL`.
6. Validate location flow + zonal workspace + export.

## 9. Backups and Recovery

Recommended baseline:
- daily `pg_dump`
- periodic snapshot backups
- environment-specific retention policy

Recovery drill:
1. restore into isolated environment
2. validate row counts and sample API calls
3. document achieved RTO/RPO

## 10. Troubleshooting

### Symptom: street query returns unexpected rows

Checks:
- confirm `street` parameter is being passed
- verify row is `ALL OTHER STREETS` fallback candidate
- verify location/class/dataset scope in request

### Symptom: export is truncated

Cause:
- results exceed `export_max_rows`.

Resolution:
- narrow filters or increase cap carefully in `backend/app/config.py`

### Symptom: summary endpoint is slow

Checks:
- verify PostgreSQL usage
- verify indexes from `docs/PERFORMANCE.md`
- run `ANALYZE zonal_values`

## 11. Change Management

- version dataset imports explicitly (`dataset_version`)
- document schema/API changes in release notes
- require smoke-test evidence in pull requests
