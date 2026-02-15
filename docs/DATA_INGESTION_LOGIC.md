# Data Ingestion Logic

## 1. Ingestion Goals

The ingestion pipeline converts heterogeneous BIR workbook formats into one canonical table:
- normalize inconsistent headers
- preserve source lineage
- skip invalid/non-data rows
- support repeated imports under dataset version labels

## 2. Input Sources

Two supported entry points:

1. Manual folder ingestion:
- Script: `backend/scripts/ingest_from_folder.py`
- Input: `.xlsx`, `.xlsm`, `.xls`

2. Official BIR fetch + extraction:
- Script: `backend/scripts/fetch_bir_zonal_files.py`
- Flow:
  - Fetch `https://www.bir.gov.ph/zonal-values`
  - Parse template codes from Next.js page payload
  - Query BIR CMS dataset APIs
  - Download attachments
  - Extract workbook files from zips
  - Write a JSON manifest with provenance

## 3. Canonical Schema Mapping

Canonical fields expected by ingestion logic:
- `rdo_code`
- `region`
- `province`
- `city_municipality`
- `barangay`
- `street_subdivision`
- `property_class`
- `property_type`
- `zonal_value`
- `unit`
- `effectivity_date`
- `remarks`

Column aliases are normalized through:
- punctuation/space cleanup
- lowercasing
- alias dictionary matching (example: `brgy -> barangay`, `class -> property_class`)

## 4. BIR-Specific Heuristic Parser

When dataset version starts with `BIR-ZONAL`, the parser uses a BIR-specific extraction path.

Key logic:
- Detect context rows (`RDO`, `Province`, `City/Municipality`, `Zone/Barangay`).
- Track dynamic column positions for:
  - classification
  - zonal value
  - vicinity text
- Validate probable property class using regex and disallowed fragments.
- Skip rows that look like headers/notes instead of data.
- Reject zero/invalid zonal values.
- Build remarks from vicinity when available.
- Set `property_type = "Land"` and `unit = "PHP per sq.m."` in this parsing mode.

## 5. Generic Workbook Parser (Fallback)

For non-BIR mode or sheets not matching BIR extraction:
- detect best header row using alias-hit scoring
- normalize headers
- map known aliases to canonical columns
- iterate rows and coerce:
  - decimals
  - dates
  - text
- skip rows that have no usable zonal value and no location context

## 6. Data Quality Rules

Applied quality controls:
- Decimal sanitizer strips currency symbols and separators.
- Date parser uses `pandas.to_datetime(..., errors='coerce')`.
- Empty strings normalize to `NULL`.
- Invalid rows are counted as skipped.

Current limitations:
- No deduplication by semantic keys.
- No strict validation by reference datasets (province/city master lists).
- No anomaly scoring for outlier values.

## 7. Lineage and Auditability

Every stored row includes:
- `source_file`
- `source_sheet`
- `source_row`
- `dataset_version`

This enables:
- row-level trace-back to raw source
- reproducible audits
- dataset version comparisons

## 8. Migration from SQLite to PostgreSQL

Script:
- `backend/scripts/migrate_sqlite_to_postgres.py`

Behavior:
- drops and recreates target table to match current model
- streams rows in batches with PostgreSQL `COPY`
- resets sequence after load
- applies PostgreSQL optimization indexes
- reports source and target counts

## 9. Operational Commands

Fetch official files:
```powershell
cd backend
.venv\Scripts\activate
python scripts\fetch_bir_zonal_files.py
```

Ingest extracted files:
```powershell
python scripts\ingest_from_folder.py --folder ..\data\raw\bir_zonal\extracted --dataset-version BIR-ZONAL-2026-02-15
```

Migrate local SQLite data to PostgreSQL:
```powershell
python scripts\migrate_sqlite_to_postgres.py --batch-size 20000
```

