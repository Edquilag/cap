# Frontend (React + Vite)

## Run locally

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Default URL:
- `http://localhost:5173`

## Build

```powershell
npm run build
```

## Environment

- `VITE_API_BASE_URL`
  - Example: `http://localhost:8000/api/v1`

## Key UI behavior

- Guided navigation: Region -> Province -> City/Municipality -> Barangay -> Zonal values
- Zonal workspace:
  - street-priority search
  - precision badges
  - dataset version switch/compare
  - summary cards and class mix chips
  - CSV/XLSX export
  - modal details with source lineage
