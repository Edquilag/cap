# Operations Runbook

## 1. Environments

Recommended environment model:
- `dev`: local developer machines
- `staging`: pre-production validation
- `prod`: production workload

Each environment should have:
- separate database
- separate credentials
- separate dataset-version process

## 2. Prerequisites

- Python 3.12+ (or project-compatible runtime)
- Node.js 20+ for frontend
- PostgreSQL 14+ recommended for production
- Windows PowerShell commands shown below (adapt for Linux/macOS as needed)

## 3. Backend Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:
- `GET http://localhost:8000/health`

## 4. Frontend Setup

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Local app URL:
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

Post-migration validation:
- compare source/target row counts
- query sample records from API

## 6. Deployment Workflow (Recommended)

1. Deploy backend API.
2. Run DB schema initialization/startup.
3. Apply migration/import for target dataset version.
4. Verify health endpoint and smoke-test key API routes.
5. Deploy frontend with correct `VITE_API_BASE_URL`.
6. Validate end-to-end search/filter behavior.

## 7. Backups and Recovery

Recommended baseline:
- daily logical backup (`pg_dump`)
- periodic physical backups/snapshots
- backup retention policy by environment criticality

Recovery drill checklist:
- restore backup to isolated environment
- verify row counts and selected critical queries
- document RTO/RPO achieved

## 8. Monitoring

Minimum production telemetry:
- API request count/latency/error-rate
- DB CPU, memory, connections, disk, slow queries
- ingestion job success/failure metrics

Recommended tools:
- reverse proxy metrics + logs
- PostgreSQL performance views (`pg_stat_activity`, `pg_stat_statements`)
- centralized log aggregation

## 9. Troubleshooting Guide

### Symptom: API starts but search is slow

Checks:
- confirm PostgreSQL is used (`DATABASE_URL`)
- confirm optimization indexes exist (`pg_indexes`)
- run `ANALYZE zonal_values`

### Symptom: Migration fails with column length errors

Cause:
- model/schema mismatch against real source text lengths.

Resolution:
- update model types to support observed max lengths
- recreate table and rerun migration

### Symptom: Empty filter dropdown options

Checks:
- verify data ingestion inserted rows
- confirm `GET /api/v1/zonal-values/filters` returns data
- inspect DB for null-heavy columns

## 10. Change Management

Recommended release discipline:
- version dataset imports explicitly (`dataset_version`)
- track schema changes with migration notes
- keep deployment checklist in pull request template
- require smoke test evidence before production rollout

