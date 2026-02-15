# ZonalHub

ZonalHub is a searchable web app for B2B real estate teams to browse BIR zonal values without opening Excel files.

## What is built in this first version

- FastAPI backend with normalized `zonal_values` table
- Excel ingestion pipeline (`.xlsx`, `.xls`, `.xlsm`)
- Filtered, paginated search API
- PostgreSQL search optimization layer (full-text + trigram indexes)
- React frontend with:
  - searchable region dropdown
  - province cards per selected region
  - province page with city list and barangay cards
  - zonal-value page per selected barangay with paginated records and detail panel

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

Place BIR files in a folder, for example:

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

This command pulls BIR zonal datasets from the official `https://www.bir.gov.ph/zonal-values` page, downloads linked files, and extracts workbook files into `data/raw/bir_zonal/extracted`.

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

## Documentation

Full project documentation is in `docs/README.md`, including:
- system architecture and logic
- API reference
- ingestion and data lineage behavior
- performance optimization details
- security model and hardening checklist
- operations and deployment runbook

Quick Codex/bootstrap guide:
- `CODEX_SETUP_GUIDE.txt`

## PostgreSQL connection (optional now, recommended for production)

No password is required to start development with SQLite.

When you want to use your PostgreSQL database, update `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg://YOUR_USER:YOUR_PASSWORD@YOUR_HOST:5432/YOUR_DB
```

Then restart the backend and re-run ingestion.

If you already have data in SQLite (`backend/zonalhub.db`) and want to move it to PostgreSQL:

```powershell
cd backend
.venv_local\Scripts\activate
python scripts\migrate_sqlite_to_postgres.py --batch-size 20000
```

## Next build steps

- Add auth + roles (admin, analyst, partner)
- Add saved searches and export jobs
- Add dataset version management and diff reports
- Add map view with geocoding and polygon overlays
