from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import String, and_, case, cast, exists, func, literal, or_, select
from sqlalchemy.orm import Session, aliased

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


def _normalize_token(value: str | None) -> str:
    return (value or "").strip()


def _normalized_text(column):
    return func.lower(func.trim(func.coalesce(column, "")))


def _like_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _is_catch_all_street(column):
    return _normalized_text(column).like("%all other street%")


def _street_priority_components(street_query: str):
    normalized_street_query = _normalize_token(street_query).lower()
    if not normalized_street_query:
        return None, None, None

    street_column = _normalized_text(ZonalValue.street_subdivision)
    pattern = _like_pattern(normalized_street_query)
    exact_match_condition = street_column == normalized_street_query
    contains_condition = street_column.like(pattern, escape="\\")
    catch_all_condition = _is_catch_all_street(ZonalValue.street_subdivision)
    named_match_condition = and_(contains_condition, ~catch_all_condition)

    peer_row = aliased(ZonalValue)
    peer_street_column = _normalized_text(peer_row.street_subdivision)
    peer_contains_condition = peer_street_column.like(pattern, escape="\\")
    peer_catch_all_condition = _is_catch_all_street(peer_row.street_subdivision)
    same_scope_condition = and_(
        func.coalesce(peer_row.province, "") == func.coalesce(ZonalValue.province, ""),
        func.coalesce(peer_row.city_municipality, "") == func.coalesce(ZonalValue.city_municipality, ""),
        func.coalesce(peer_row.barangay, "") == func.coalesce(ZonalValue.barangay, ""),
        func.coalesce(peer_row.property_class, "") == func.coalesce(ZonalValue.property_class, ""),
        func.coalesce(peer_row.dataset_version, "") == func.coalesce(ZonalValue.dataset_version, ""),
    )
    named_peer_exists = exists(
        select(1).select_from(peer_row).where(and_(same_scope_condition, peer_contains_condition, ~peer_catch_all_condition))
    )

    catch_all_fallback_condition = and_(catch_all_condition, ~named_peer_exists)
    inclusion_condition = or_(exact_match_condition, named_match_condition, catch_all_fallback_condition)
    rank_expression = case(
        (exact_match_condition, 0),
        (named_match_condition, 1),
        (catch_all_fallback_condition, 2),
        else_=3,
    )

    return inclusion_condition, rank_expression, exact_match_condition


def _apply_conditions(
    db: Session,
    stmt,
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
    street: str | None = None,
):
    conditions = []
    street_rank = None
    exact_match_condition = None

    if search:
        normalized_search = _normalize_token(search)
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
        conditions.append(ZonalValue.region.ilike(f"%{_normalize_token(region)}%"))
    if province:
        conditions.append(ZonalValue.province.ilike(f"%{_normalize_token(province)}%"))
    if city:
        conditions.append(ZonalValue.city_municipality.ilike(f"%{_normalize_token(city)}%"))
    if barangay:
        conditions.append(ZonalValue.barangay.ilike(f"%{_normalize_token(barangay)}%"))
    if property_class:
        conditions.append(ZonalValue.property_class.ilike(f"%{_normalize_token(property_class)}%"))
    if property_type:
        conditions.append(ZonalValue.property_type.ilike(f"%{_normalize_token(property_type)}%"))
    if dataset_version:
        conditions.append(ZonalValue.dataset_version == _normalize_token(dataset_version))
    if min_value is not None:
        conditions.append(ZonalValue.zonal_value >= min_value)
    if max_value is not None:
        conditions.append(ZonalValue.zonal_value <= max_value)

    if street:
        street_inclusion_condition, street_rank, exact_match_condition = _street_priority_components(street)
        if street_inclusion_condition is not None:
            conditions.append(street_inclusion_condition)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    return stmt, street_rank, exact_match_condition


def _ordered_stmt(stmt, street_rank=None):
    ordering = []
    if street_rank is not None:
        ordering.append(street_rank.asc())
    ordering.extend(
        [
            ZonalValue.region.asc().nulls_last(),
            ZonalValue.province.asc().nulls_last(),
            ZonalValue.city_municipality.asc().nulls_last(),
            ZonalValue.barangay.asc().nulls_last(),
            ZonalValue.property_class.asc().nulls_last(),
            ZonalValue.street_subdivision.asc().nulls_last(),
            ZonalValue.id.asc(),
        ]
    )
    return stmt.order_by(*ordering)


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
    street: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[Sequence[ZonalValue], int]:
    stmt = select(ZonalValue)
    stmt, street_rank, _ = _apply_conditions(
        db,
        stmt,
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
        street=street,
    )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    stmt = _ordered_stmt(stmt, street_rank=street_rank).offset((page - 1) * page_size).limit(page_size)
    rows = db.execute(stmt).scalars().all()
    return rows, total


def _sqlite_median_from_subquery(db: Session, filtered_subquery) -> Decimal | None:
    non_null_count_stmt = select(func.count()).select_from(filtered_subquery).where(filtered_subquery.c.zonal_value.is_not(None))
    non_null_count = db.execute(non_null_count_stmt).scalar_one()
    if non_null_count == 0:
        return None

    if non_null_count % 2 == 1:
        middle_offset = non_null_count // 2
        median_stmt = (
            select(filtered_subquery.c.zonal_value)
            .where(filtered_subquery.c.zonal_value.is_not(None))
            .order_by(filtered_subquery.c.zonal_value.asc())
            .offset(middle_offset)
            .limit(1)
        )
        return db.execute(median_stmt).scalar_one_or_none()

    upper_offset = non_null_count // 2
    lower_offset = upper_offset - 1
    pair_stmt = (
        select(filtered_subquery.c.zonal_value)
        .where(filtered_subquery.c.zonal_value.is_not(None))
        .order_by(filtered_subquery.c.zonal_value.asc())
        .offset(lower_offset)
        .limit(2)
    )
    pair = db.execute(pair_stmt).scalars().all()
    if len(pair) != 2:
        return pair[0] if pair else None
    return (pair[0] + pair[1]) / Decimal("2")


def get_zonal_summary(
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
    street: str | None = None,
) -> dict[str, object]:
    stmt = select(ZonalValue)
    stmt, _, exact_match_condition = _apply_conditions(
        db,
        stmt,
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
        street=street,
    )

    filtered_subquery = stmt.subquery()
    aggregate_stmt = select(
        func.count(filtered_subquery.c.id),
        func.min(filtered_subquery.c.zonal_value),
        func.max(filtered_subquery.c.zonal_value),
    )
    total_records, min_value_result, max_value_result = db.execute(aggregate_stmt).one()

    if _is_postgres_session(db):
        median_stmt = select(func.percentile_cont(0.5).within_group(filtered_subquery.c.zonal_value)).where(
            filtered_subquery.c.zonal_value.is_not(None)
        )
        median_value = db.execute(median_stmt).scalar_one_or_none()
    else:
        median_value = _sqlite_median_from_subquery(db, filtered_subquery)

    catch_all_count_stmt = select(func.count(filtered_subquery.c.id)).where(
        _is_catch_all_street(filtered_subquery.c.street_subdivision)
    )
    catch_all_records = db.execute(catch_all_count_stmt).scalar_one()

    exact_street_records = 0
    if exact_match_condition is not None:
        exact_stmt = select(func.count(ZonalValue.id)).select_from(ZonalValue)
        exact_stmt, _, _ = _apply_conditions(
            db,
            exact_stmt,
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
            street=street,
        )
        exact_stmt = exact_stmt.where(exact_match_condition)
        exact_street_records = db.execute(exact_stmt).scalar_one()

    property_class_label = func.coalesce(filtered_subquery.c.property_class, literal("Unspecified")).label("property_class")
    class_mix_stmt = (
        select(property_class_label, func.count(filtered_subquery.c.id).label("count"))
        .group_by(property_class_label)
        .order_by(func.count(filtered_subquery.c.id).desc(), property_class_label.asc())
        .limit(8)
    )
    class_mix_rows = db.execute(class_mix_stmt).all()
    class_mix = [{"property_class": row.property_class, "count": row.count} for row in class_mix_rows]

    return {
        "total_records": total_records,
        "min_value": min_value_result,
        "max_value": max_value_result,
        "median_value": median_value,
        "catch_all_records": catch_all_records,
        "exact_street_records": exact_street_records,
        "class_mix": class_mix,
    }


def get_zonal_values_for_export(
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
    street: str | None = None,
    limit: int = 50000,
) -> tuple[Sequence[ZonalValue], int]:
    stmt = select(ZonalValue)
    stmt, street_rank, _ = _apply_conditions(
        db,
        stmt,
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
        street=street,
    )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    rows_stmt = _ordered_stmt(stmt, street_rank=street_rank).limit(limit)
    rows = db.execute(rows_stmt).scalars().all()
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
