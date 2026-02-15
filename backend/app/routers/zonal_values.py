import csv
from datetime import datetime
from decimal import Decimal
from io import BytesIO, StringIO
from typing import Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import crud, schemas
from app.config import get_settings
from app.database import get_db

router = APIRouter(prefix="/zonal-values", tags=["zonal-values"])
settings = get_settings()


@router.get("", response_model=schemas.PaginatedZonalValues)
def list_zonal_values(
    search: str | None = Query(default=None, description="Search across location and property fields."),
    region: str | None = None,
    province: str | None = None,
    city: str | None = None,
    barangay: str | None = None,
    property_class: str | None = None,
    property_type: str | None = None,
    dataset_version: str | None = None,
    street: str | None = Query(default=None, description="Street/subdivision input for priority matching."),
    min_value: Decimal | None = None,
    max_value: Decimal | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.default_page_size, ge=1, le=settings.max_page_size),
    db: Session = Depends(get_db),
) -> schemas.PaginatedZonalValues:
    rows, total = crud.get_zonal_values(
        db,
        search=search,
        region=region,
        province=province,
        city=city,
        barangay=barangay,
        property_class=property_class,
        property_type=property_type,
        dataset_version=dataset_version,
        street=street,
        min_value=min_value,
        max_value=max_value,
        page=page,
        page_size=page_size,
    )
    return schemas.PaginatedZonalValues(items=rows, total=total, page=page, page_size=page_size)


@router.get("/filters", response_model=schemas.FilterOptions)
def list_filters(db: Session = Depends(get_db)) -> schemas.FilterOptions:
    return schemas.FilterOptions(**crud.get_filter_options(db))


@router.get("/location-children", response_model=schemas.LocationChildren)
def list_location_children(
    province: str = Query(..., description="Province name."),
    city: str | None = Query(default=None, description="City/municipality name."),
    limit: int = Query(default=1000, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> schemas.LocationChildren:
    payload = crud.get_location_children(db, province=province, city=city, limit=limit)
    return schemas.LocationChildren(**payload)


@router.get("/summary", response_model=schemas.ZonalSummary)
def get_zonal_summary(
    search: str | None = Query(default=None, description="Search across location and property fields."),
    region: str | None = None,
    province: str | None = None,
    city: str | None = None,
    barangay: str | None = None,
    property_class: str | None = None,
    property_type: str | None = None,
    dataset_version: str | None = None,
    street: str | None = Query(default=None, description="Street/subdivision input for priority matching."),
    min_value: Decimal | None = None,
    max_value: Decimal | None = None,
    db: Session = Depends(get_db),
) -> schemas.ZonalSummary:
    payload = crud.get_zonal_summary(
        db,
        search=search,
        region=region,
        province=province,
        city=city,
        barangay=barangay,
        property_class=property_class,
        property_type=property_type,
        dataset_version=dataset_version,
        street=street,
        min_value=min_value,
        max_value=max_value,
    )
    return schemas.ZonalSummary(**payload)


@router.get("/export")
def export_zonal_values(
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    search: str | None = Query(default=None, description="Search across location and property fields."),
    region: str | None = None,
    province: str | None = None,
    city: str | None = None,
    barangay: str | None = None,
    property_class: str | None = None,
    property_type: str | None = None,
    dataset_version: str | None = None,
    street: str | None = Query(default=None, description="Street/subdivision input for priority matching."),
    min_value: Decimal | None = None,
    max_value: Decimal | None = None,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    rows, total = crud.get_zonal_values_for_export(
        db,
        search=search,
        region=region,
        province=province,
        city=city,
        barangay=barangay,
        property_class=property_class,
        property_type=property_type,
        dataset_version=dataset_version,
        street=street,
        min_value=min_value,
        max_value=max_value,
        limit=settings.export_max_rows,
    )

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base_filename = f"zonal_values_export_{timestamp}"
    field_names = [
        "id",
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
        "dataset_version",
        "source_file",
        "source_sheet",
        "source_row",
        "created_at",
    ]

    records = [
        {
            "id": row.id,
            "rdo_code": row.rdo_code,
            "region": row.region,
            "province": row.province,
            "city_municipality": row.city_municipality,
            "barangay": row.barangay,
            "street_subdivision": row.street_subdivision,
            "property_class": row.property_class,
            "property_type": row.property_type,
            "zonal_value": str(row.zonal_value) if row.zonal_value is not None else None,
            "unit": row.unit,
            "effectivity_date": row.effectivity_date.isoformat() if row.effectivity_date else None,
            "remarks": row.remarks,
            "dataset_version": row.dataset_version,
            "source_file": row.source_file,
            "source_sheet": row.source_sheet,
            "source_row": row.source_row,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]

    truncated = total > settings.export_max_rows
    headers = {}
    if truncated:
        headers["X-Export-Truncated"] = "true"
        headers["X-Export-Row-Limit"] = str(settings.export_max_rows)
        headers["X-Export-Total-Matches"] = str(total)

    if format == "csv":
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(records)
        csv_bytes = output.getvalue().encode("utf-8-sig")
        filename = f"{base_filename}.csv"
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return StreamingResponse(iter([csv_bytes]), media_type="text/csv; charset=utf-8", headers=headers)

    dataframe = pd.DataFrame.from_records(records, columns=field_names)
    output_xlsx = BytesIO()
    with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="zonal_values")
    output_xlsx.seek(0)
    filename = f"{base_filename}.xlsx"
    headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return StreamingResponse(
        output_xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/{zonal_value_id}", response_model=schemas.ZonalValueRead)
def get_zonal_value(zonal_value_id: int, db: Session = Depends(get_db)) -> schemas.ZonalValueRead:
    row = crud.get_zonal_value_by_id(db, zonal_value_id=zonal_value_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Zonal value not found")
    return schemas.ZonalValueRead.model_validate(row)
