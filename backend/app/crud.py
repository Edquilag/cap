from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import String, and_, cast, func, literal, or_, select
from sqlalchemy.orm import Session

from app.models import ZonalValue


def _is_postgres_session(db: Session) -> bool:
    bind = db.get_bind()
    return bind.dialect.name == "postgresql"


def _search_blob():
    separator = literal(" ")
    return (
        func.coalesce(ZonalValue.rdo_code, "")
        + separator
        + func.coalesce(ZonalValue.region, "")
        + separator
        + func.coalesce(ZonalValue.province, "")
        + separator
        + func.coalesce(ZonalValue.city_municipality, "")
        + separator
        + func.coalesce(ZonalValue.barangay, "")
        + separator
        + func.coalesce(ZonalValue.street_subdivision, "")
        + separator
        + func.coalesce(ZonalValue.property_class, "")
        + separator
        + func.coalesce(ZonalValue.property_type, "")
        + separator
        + func.coalesce(ZonalValue.dataset_version, "")
        + separator
        + func.coalesce(cast(ZonalValue.zonal_value, String), "")
    )


def get_zonal_values(
    db: Session,
    *,
    search: str | None = None,
    region: str | None = None,
    province: str | None = None,
    city: str | None = None,
    barangay: str | None = None,
    property_class: str | None = None,
    property_type: str | None = None,
    dataset_version: str | None = None,
    min_value: Decimal | None = None,
    max_value: Decimal | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[Sequence[ZonalValue], int]:
    stmt = select(ZonalValue)
    conditions = []

    if search:
        normalized_search = search.strip()
        if normalized_search:
            pattern = f"%{normalized_search}%"
            if _is_postgres_session(db):
                search_blob = _search_blob()
                text_match = func.to_tsvector("simple", search_blob).op("@@")(
                    func.websearch_to_tsquery("simple", normalized_search)
                )
                conditions.append(or_(text_match, search_blob.ilike(pattern)))
            else:
                searchable_cols = [
                    ZonalValue.rdo_code,
                    ZonalValue.region,
                    ZonalValue.province,
                    ZonalValue.city_municipality,
                    ZonalValue.barangay,
                    ZonalValue.street_subdivision,
                    ZonalValue.property_class,
                    ZonalValue.property_type,
                    ZonalValue.dataset_version,
                    cast(ZonalValue.zonal_value, String),
                ]
                conditions.append(or_(*[col.ilike(pattern) for col in searchable_cols]))

    if region:
        conditions.append(ZonalValue.region.ilike(f"%{region.strip()}%"))
    if province:
        conditions.append(ZonalValue.province.ilike(f"%{province.strip()}%"))
    if city:
        conditions.append(ZonalValue.city_municipality.ilike(f"%{city.strip()}%"))
    if barangay:
        conditions.append(ZonalValue.barangay.ilike(f"%{barangay.strip()}%"))
    if property_class:
        conditions.append(ZonalValue.property_class.ilike(f"%{property_class.strip()}%"))
    if property_type:
        conditions.append(ZonalValue.property_type.ilike(f"%{property_type.strip()}%"))
    if dataset_version:
        conditions.append(ZonalValue.dataset_version == dataset_version.strip())
    if min_value is not None:
        conditions.append(ZonalValue.zonal_value >= min_value)
    if max_value is not None:
        conditions.append(ZonalValue.zonal_value <= max_value)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    stmt = (
        stmt.order_by(
            ZonalValue.region.asc().nulls_last(),
            ZonalValue.province.asc().nulls_last(),
            ZonalValue.city_municipality.asc().nulls_last(),
            ZonalValue.barangay.asc().nulls_last(),
            ZonalValue.street_subdivision.asc().nulls_last(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = db.execute(stmt).scalars().all()
    return rows, total


def get_zonal_value_by_id(db: Session, zonal_value_id: int) -> ZonalValue | None:
    stmt = select(ZonalValue).where(ZonalValue.id == zonal_value_id)
    return db.execute(stmt).scalar_one_or_none()


def get_filter_options(db: Session) -> dict[str, list[str]]:
    def distinct_values(column) -> list[str]:
        stmt = select(func.distinct(column)).where(column.is_not(None)).order_by(column.asc()).limit(500)
        return [value for value in db.execute(stmt).scalars().all() if value]

    return {
        "regions": distinct_values(ZonalValue.region),
        "provinces": distinct_values(ZonalValue.province),
        "cities": distinct_values(ZonalValue.city_municipality),
        "barangays": distinct_values(ZonalValue.barangay),
        "property_classes": distinct_values(ZonalValue.property_class),
        "property_types": distinct_values(ZonalValue.property_type),
        "dataset_versions": distinct_values(ZonalValue.dataset_version),
    }


def get_location_children(
    db: Session,
    *,
    province: str,
    city: str | None = None,
    limit: int = 1000,
) -> dict[str, list[str]]:
    province_filter = province.strip()
    if not province_filter:
        return {"cities": [], "barangays": []}

    city_stmt = (
        select(func.distinct(ZonalValue.city_municipality))
        .where(ZonalValue.province.ilike(f"%{province_filter}%"))
        .where(ZonalValue.city_municipality.is_not(None))
        .order_by(ZonalValue.city_municipality.asc())
        .limit(limit)
    )
    cities = [value for value in db.execute(city_stmt).scalars().all() if value]

    barangays: list[str] = []
    if city and city.strip():
        city_filter = city.strip()
        barangay_stmt = (
            select(func.distinct(ZonalValue.barangay))
            .where(ZonalValue.province.ilike(f"%{province_filter}%"))
            .where(ZonalValue.city_municipality.ilike(f"%{city_filter}%"))
            .where(ZonalValue.barangay.is_not(None))
            .order_by(ZonalValue.barangay.asc())
            .limit(limit)
        )
        barangays = [value for value in db.execute(barangay_stmt).scalars().all() if value]

    return {"cities": cities, "barangays": barangays}
