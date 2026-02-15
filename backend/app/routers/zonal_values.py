from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
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


@router.get("/{zonal_value_id}", response_model=schemas.ZonalValueRead)
def get_zonal_value(zonal_value_id: int, db: Session = Depends(get_db)) -> schemas.ZonalValueRead:
    row = crud.get_zonal_value_by_id(db, zonal_value_id=zonal_value_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Zonal value not found")
    return schemas.ZonalValueRead.model_validate(row)
