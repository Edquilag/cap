from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

import pandas as pd
from sqlalchemy.orm import Session

from app.models import ZonalValue

CANONICAL_COLUMNS = [
    "rdo_code",
    "region",
    "province",
    "city_municipality",
    "barangay",
    "street_subdivision",
    "property_class",
    "property_type",
    "zonal_value",
    "unit",
    "effectivity_date",
    "remarks",
]

COLUMN_ALIASES: dict[str, str] = {
    "rdo": "rdo_code",
    "rdo_code": "rdo_code",
    "revenue_district_office": "rdo_code",
    "region": "region",
    "province": "province",
    "city": "city_municipality",
    "municipality": "city_municipality",
    "city_municipality": "city_municipality",
    "city_or_municipality": "city_municipality",
    "barangay": "barangay",
    "brgy": "barangay",
    "street": "street_subdivision",
    "subdivision": "street_subdivision",
    "street_subdivision": "street_subdivision",
    "street_subdivision_name": "street_subdivision",
    "property_class": "property_class",
    "classification": "property_class",
    "class": "property_class",
    "property_type": "property_type",
    "type": "property_type",
    "zonal_value": "zonal_value",
    "zonal_value_per_sq_m": "zonal_value",
    "value": "zonal_value",
    "value_per_sq_m": "zonal_value",
    "unit": "unit",
    "uom": "unit",
    "effectivity_date": "effectivity_date",
    "effectivity": "effectivity_date",
    "remarks": "remarks",
    "note": "remarks",
    "zone_barangay": "barangay",
    "street_name_subdivision_condominium": "street_subdivision",
    "zv_sq_m": "zonal_value",
}

PROPERTY_CLASS_PATTERN = re.compile(r"^\*{0,2}[A-Z]{1,4}[0-9A-Z]{0,4}$")


def _normalize_column_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return re.sub(r"_+", "_", cleaned).strip("_")


def _detect_header_row(df: pd.DataFrame, max_scan_rows: int = 30) -> int:
    max_score = 0
    best_row = 0
    scan_rows = min(max_scan_rows, len(df))
    for i in range(scan_rows):
        cells = [str(v) for v in df.iloc[i].tolist() if pd.notna(v)]
        normalized = {_normalize_column_name(cell) for cell in cells}
        aliases_hit = sum(1 for col in normalized if col in COLUMN_ALIASES)
        if aliases_hit > max_score:
            max_score = aliases_hit
            best_row = i
    return best_row


def _map_columns(raw_columns: Iterable[str]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for column in raw_columns:
        normalized = _normalize_column_name(str(column))
        mapped[column] = COLUMN_ALIASES.get(normalized, normalized)
    return mapped


def _safe_decimal(value: object) -> Decimal | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (date, datetime)):
        return None
    text = str(value).strip()
    if not text:
        return None
    if re.search(r"\d+[/-]\d+[/-]\d+", text):
        return None
    cleaned = re.sub(r"[^\d\.-]", "", text)
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _safe_date(value: object) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _coerce_text(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _extract_labeled_value(cells: list[str], label: str) -> str | None:
    first = cells[0] if cells else ""
    label_upper = label.upper()
    if first.upper().startswith(label_upper):
        if ":" in first:
            _, right_side = first.split(":", 1)
            candidate = right_side.strip()
            if candidate:
                return candidate
        if len(cells) > 2 and cells[1] == ":":
            return cells[2] or None
        if len(cells) > 1:
            return cells[1] or None
    return None


def _is_valid_property_class(value: str) -> bool:
    normalized = value.strip().upper()
    if not normalized:
        return False
    disallowed_fragments = {
        "EFFECTIVITY",
        "CLASSIFICATION",
        "CLASSI",
        "FICATION",
        "REVISION",
        "D.O.",
        "DO NO",
        "ZV/",
        "FROM",
        "TO",
    }
    if any(fragment in normalized for fragment in disallowed_fragments):
        return False
    if len(normalized) > 12:
        return False
    return PROPERTY_CLASS_PATTERN.match(normalized) is not None


def _derive_rdo_from_filename(workbook_path: Path) -> str | None:
    match = re.search(r"(RDO\\s*No\\.?\\s*\\d+[A-Z]?(?:\\s*-\\s*[^_]+)?)", workbook_path.stem, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def _ingest_bir_zonal_sheet(
    session: Session,
    raw_df: pd.DataFrame,
    *,
    workbook_path: Path,
    sheet_name: str,
    dataset_version: str,
    default_region: str | None = None,
    default_province: str | None = None,
) -> tuple[int, int]:
    inserted = 0
    skipped = 0

    rdo_code: str | None = _derive_rdo_from_filename(workbook_path)
    province: str | None = default_province
    city_municipality: str | None = None
    barangay: str | None = None
    street_subdivision: str | None = None
    classification_col = 4
    zonal_value_col = 5
    vicinity_col = 3

    for idx, row in raw_df.iterrows():
        cells = [_coerce_text(value) or "" for value in row.tolist()]
        if not any(cells):
            skipped += 1
            continue

        upper_cells = [cell.upper() for cell in cells]
        for column_index, upper_cell in enumerate(upper_cells):
            if "CLASSIFICATION" in upper_cell:
                classification_col = column_index
            if "CLASSI" in upper_cell or upper_cell == "FICATION":
                classification_col = column_index
            if "VICINITY" in upper_cell:
                vicinity_col = column_index
            if "ZV/" in upper_cell or ("ZV" in upper_cell and "SQ" in upper_cell):
                zonal_value_col = column_index

        first_cell = cells[0].upper() if cells else ""
        if first_cell.startswith("RDO NO"):
            rdo_code = " ".join(part for part in [cells[0], cells[1] if len(cells) > 1 else ""] if part).strip()
            skipped += 1
            continue
        if "REVENUE DISTRICT OFFICE" in first_cell and "NO." in first_cell:
            rdo_code = cells[0]
            skipped += 1
            continue

        province_candidate = _extract_labeled_value(cells, "Province")
        if province_candidate:
            province = province_candidate
            skipped += 1
            continue

        city_candidate = _extract_labeled_value(cells, "City/Municipality")
        if not city_candidate:
            city_candidate = _extract_labeled_value(cells, "Municipality")
        if city_candidate:
            city_municipality = city_candidate
            skipped += 1
            continue

        barangay_candidate = _extract_labeled_value(cells, "Zone/Barangay")
        if not barangay_candidate:
            barangay_candidate = _extract_labeled_value(cells, "Barangay")
        if barangay_candidate:
            upper_barangay = barangay_candidate.upper()
            if upper_barangay.startswith("BARANGAY:"):
                barangay_candidate = barangay_candidate.split(":", 1)[1].strip()
            barangay = barangay_candidate
            street_subdivision = None
            skipped += 1
            continue

        if ("STREET NAME" in first_cell and "SUBDIVISION" in first_cell) or first_cell.startswith("STREET/SUBDIVISION"):
            street_subdivision = None
            skipped += 1
            continue

        property_class = cells[classification_col] if len(cells) > classification_col else None
        zonal_value = _safe_decimal(cells[zonal_value_col] if len(cells) > zonal_value_col else None)
        if zonal_value is None or not property_class:
            skipped += 1
            continue

        if not city_municipality and not barangay:
            skipped += 1
            continue

        if not _is_valid_property_class(property_class):
            skipped += 1
            continue

        if zonal_value <= 0:
            skipped += 1
            continue

        row_street = cells[0] if cells else None
        if row_street:
            street_subdivision = row_street
        vicinity = cells[vicinity_col] if len(cells) > vicinity_col else None
        remarks = f"Vicinity: {vicinity}" if vicinity else None

        entity = ZonalValue(
            rdo_code=rdo_code,
            region=default_region,
            province=province,
            city_municipality=city_municipality,
            barangay=barangay,
            street_subdivision=street_subdivision,
            property_class=property_class,
            property_type="Land",
            zonal_value=zonal_value,
            unit="PHP per sq.m.",
            effectivity_date=None,
            remarks=remarks,
            source_file=workbook_path.name,
            source_sheet=str(sheet_name),
            source_row=int(idx) + 1,
            dataset_version=dataset_version,
        )
        session.add(entity)
        inserted += 1

    return inserted, skipped


def _normalize_sheet(df: pd.DataFrame) -> pd.DataFrame:
    stripped = df.dropna(how="all").dropna(axis=1, how="all")
    if stripped.empty:
        return pd.DataFrame()
    header_row = _detect_header_row(stripped)
    sheet = stripped.iloc[header_row + 1 :].copy()
    sheet.columns = stripped.iloc[header_row].fillna("").astype(str).tolist()
    sheet = sheet.rename(columns=_map_columns(sheet.columns))
    sheet = sheet.loc[:, ~sheet.columns.duplicated()]
    return sheet


def _read_workbook_sheets(workbook_path: Path) -> dict[str, pd.DataFrame]:
    suffix = workbook_path.suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(workbook_path, sheet_name=None, dtype=object, engine="openpyxl")
    if suffix == ".xls":
        return pd.read_excel(workbook_path, sheet_name=None, dtype=object, engine="xlrd")
    raise ValueError(f"Unsupported workbook extension: {workbook_path.suffix}")


def ingest_workbook(
    session: Session,
    workbook_path: Path,
    *,
    dataset_version: str,
    default_region: str | None = None,
    default_province: str | None = None,
) -> tuple[int, int]:
    sheets = _read_workbook_sheets(workbook_path)
    inserted = 0
    skipped = 0
    bir_dataset_mode = dataset_version.upper().startswith("BIR-ZONAL")

    for sheet_name, raw_df in sheets.items():
        bir_inserted, bir_skipped = _ingest_bir_zonal_sheet(
            session,
            raw_df,
            workbook_path=workbook_path,
            sheet_name=str(sheet_name),
            dataset_version=dataset_version,
            default_region=default_region,
            default_province=default_province,
        )
        if bir_inserted > 0 or bir_dataset_mode:
            inserted += bir_inserted
            if bir_inserted > 0:
                skipped += bir_skipped
            else:
                skipped += len(raw_df)
            continue

        sheet = _normalize_sheet(raw_df)
        if sheet.empty:
            continue

        for idx, row in sheet.iterrows():
            payload = {column: row[column] for column in sheet.columns if column in CANONICAL_COLUMNS}
            zonal_value = _safe_decimal(payload.get("zonal_value"))
            location_fields = [
                _coerce_text(payload.get("region")),
                _coerce_text(payload.get("province")),
                _coerce_text(payload.get("city_municipality")),
                _coerce_text(payload.get("barangay")),
                _coerce_text(payload.get("street_subdivision")),
            ]
            if zonal_value is None and not any(location_fields):
                skipped += 1
                continue

            entity = ZonalValue(
                rdo_code=_coerce_text(payload.get("rdo_code")),
                region=_coerce_text(payload.get("region")) or default_region,
                province=_coerce_text(payload.get("province")) or default_province,
                city_municipality=_coerce_text(payload.get("city_municipality")),
                barangay=_coerce_text(payload.get("barangay")),
                street_subdivision=_coerce_text(payload.get("street_subdivision")),
                property_class=_coerce_text(payload.get("property_class")),
                property_type=_coerce_text(payload.get("property_type")),
                zonal_value=zonal_value,
                unit=_coerce_text(payload.get("unit")) or "PHP per sq.m.",
                effectivity_date=_safe_date(payload.get("effectivity_date")),
                remarks=_coerce_text(payload.get("remarks")),
                source_file=workbook_path.name,
                source_sheet=str(sheet_name),
                source_row=int(idx) + 1,
                dataset_version=dataset_version,
            )
            session.add(entity)
            inserted += 1

    session.commit()
    return inserted, skipped


def ingest_folder(
    session: Session,
    folder_path: Path,
    *,
    dataset_version: str,
    default_region: str | None = None,
    default_province: str | None = None,
) -> tuple[int, int, int]:
    files = sorted(
        [*folder_path.glob("*.xlsx"), *folder_path.glob("*.xlsm"), *folder_path.glob("*.xls")],
        key=lambda p: p.name.lower(),
    )
    workbook_count = 0
    inserted_count = 0
    skipped_count = 0

    for workbook in files:
        inserted, skipped = ingest_workbook(
            session,
            workbook,
            dataset_version=dataset_version,
            default_region=default_region,
            default_province=default_province,
        )
        workbook_count += 1
        inserted_count += inserted
        skipped_count += skipped

    return workbook_count, inserted_count, skipped_count
