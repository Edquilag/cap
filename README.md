# ZonalHub

ZonalHub is a B2B real-estate web platform that converts BIR zonal-value spreadsheets into a fast, searchable, and auditable system.

## What this build includes

- FastAPI backend with normalized `zonal_values` table
- Excel ingestion pipeline (`.xlsx`, `.xls`, `.xlsm`)
- PostgreSQL optimization layer (full-text + trigram + scope indexes)
- React frontend with guided location navigation:
  - Region -> Province -> City/Municipality -> Barangay -> Zonal values
- Enterprise-facing zonal workspace:
  - Street-priority matching (`Exact` first, `ALL OTHER STREETS` fallback)
  - Precision badges (`Exact`, `Catch-all`, `Special case`)
  - Policy banner for catch-all behavior
  - DO/Year dataset switcher + optional comparison summary
  - Decision summary cards (total, min, median, max, class mix)
  - Export buttons (CSV/XLSX) including source lineage fields
  - Modal details with source transparency and "Why this appears" logic

## Tech stack

- Backend: Python, FastAPI, SQLAlchemy
- Data: SQLite by default, PostgreSQL-ready via `DATABASE_URL`
- Frontend: React + TypeScript + Vite

## Project structure

```text
backend/
  app/
  scripts/
frontend/
data/
docs/
```

## 1) Backend setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs:
- `http://localhost:8000/docs`

## 2) Ingest Excel files

Place BIR files in:

```text
data/raw/
```

Run ingestion:

```powershell
cd backend
.venv\Scripts\activate
python scripts\ingest_from_folder.py --folder ..\data\raw --dataset-version RMC-2026-01
```

### Pull official BIR zonal files automatically

```powershell
cd backend
.venv\Scripts\activate
python scripts\fetch_bir_zonal_files.py
```

Then ingest extracted workbooks:

```powershell
python scripts\ingest_from_folder.py --folder ..\data\raw\bir_zonal\extracted --dataset-version BIR-ZONAL-2026-02-15
```

## 3) Frontend setup

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open:
- `http://localhost:5173`

## 4) Key API endpoints

- `GET /api/v1/zonal-values`
  - Supports pagination + location filters + dataset version + `street` priority matching
- `GET /api/v1/zonal-values/summary`
  - Returns decision metrics and class mix for current filters
- `GET /api/v1/zonal-values/export`
  - Exports filtered records in `csv` or `xlsx`
- `GET /api/v1/zonal-values/filters`
- `GET /api/v1/zonal-values/location-children`
- `GET /api/v1/zonal-values/{id}`

## Documentation

Full project documentation is in `docs/README.md`, including:
- architecture and request flow
- full API contract
- street-priority matching and fallback logic
- ingestion/data lineage model
- performance and index strategy
- security controls and hardening checklist
- operations/deployment runbook

Quick Codex/bootstrap guide:
- `CODEX_SETUP_GUIDE.txt`

## PostgreSQL connection (recommended for production)

Update `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg://YOUR_USER:YOUR_PASSWORD@YOUR_HOST:5432/YOUR_DB
```

Then restart backend and re-run ingestion.

If you already have data in SQLite (`backend/zonalhub.db`) and want to migrate to PostgreSQL:

```powershell
cd backend
.venv_local\Scripts\activate
python scripts\migrate_sqlite_to_postgres.py --batch-size 20000
```

## Notes

- `ALL OTHER STREETS` is treated as official catch-all source data, not inferred street mapping.
- Export endpoint enforces a safety row cap (`export_max_rows`, default `50000`) and returns truncation headers when applicable.
