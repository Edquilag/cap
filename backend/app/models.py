from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ZonalValue(Base):
    __tablename__ = "zonal_values"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Some source sheets contain long free-text in these fields.
    rdo_code: Mapped[str | None] = mapped_column(Text, index=True)
    region: Mapped[str | None] = mapped_column(String(100), index=True)
    province: Mapped[str | None] = mapped_column(String(100), index=True)
    city_municipality: Mapped[str | None] = mapped_column(String(150), index=True)
    barangay: Mapped[str | None] = mapped_column(Text, index=True)
    street_subdivision: Mapped[str | None] = mapped_column(Text, index=True)
    property_class: Mapped[str | None] = mapped_column(String(100), index=True)
    property_type: Mapped[str | None] = mapped_column(String(100), index=True)
    zonal_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), index=True)
    unit: Mapped[str | None] = mapped_column(String(50))
    effectivity_date: Mapped[date | None] = mapped_column(Date, index=True)
    remarks: Mapped[str | None] = mapped_column(Text)
    source_file: Mapped[str] = mapped_column(String(255), index=True)
    source_sheet: Mapped[str] = mapped_column(String(255), index=True)
    source_row: Mapped[int | None]
    dataset_version: Mapped[str] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
