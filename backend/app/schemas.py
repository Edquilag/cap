from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ZonalValueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rdo_code: str | None
    region: str | None
    province: str | None
    city_municipality: str | None
    barangay: str | None
    street_subdivision: str | None
    property_class: str | None
    property_type: str | None
    zonal_value: Decimal | None
    unit: str | None
    effectivity_date: date | None
    remarks: str | None
    source_file: str
    source_sheet: str
    source_row: int | None
    dataset_version: str
    created_at: datetime


class PaginatedZonalValues(BaseModel):
    items: list[ZonalValueRead]
    total: int
    page: int
    page_size: int


class FilterOptions(BaseModel):
    regions: list[str] = Field(default_factory=list)
    provinces: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    barangays: list[str] = Field(default_factory=list)
    property_classes: list[str] = Field(default_factory=list)
    property_types: list[str] = Field(default_factory=list)
    dataset_versions: list[str] = Field(default_factory=list)


class LocationChildren(BaseModel):
    cities: list[str] = Field(default_factory=list)
    barangays: list[str] = Field(default_factory=list)
