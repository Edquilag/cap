from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


logger = logging.getLogger(__name__)


SEARCH_BLOB_SQL = """
(
  coalesce(rdo_code, '') || ' ' ||
  coalesce(region, '') || ' ' ||
  coalesce(province, '') || ' ' ||
  coalesce(city_municipality, '') || ' ' ||
  coalesce(barangay, '') || ' ' ||
  coalesce(street_subdivision, '') || ' ' ||
  coalesce(property_class, '') || ' ' ||
  coalesce(property_type, '') || ' ' ||
  coalesce(dataset_version, '') || ' ' ||
  coalesce(zonal_value::text, '')
)
"""


BASE_INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS ix_zonal_values_query_order ON zonal_values (region, province, city_municipality, barangay, street_subdivision, id)",
    "CREATE INDEX IF NOT EXISTS ix_zonal_values_dataset_value ON zonal_values (dataset_version, zonal_value)",
    "CREATE INDEX IF NOT EXISTS ix_zonal_values_scope_class_version ON zonal_values (province, city_municipality, barangay, property_class, dataset_version)",
    "CREATE INDEX IF NOT EXISTS ix_zonal_values_street_subdivision_lower ON zonal_values ((lower(street_subdivision)))",
    f"CREATE INDEX IF NOT EXISTS ix_zonal_values_search_vector ON zonal_values USING GIN (to_tsvector('simple', {SEARCH_BLOB_SQL}))",
]

TRIGRAM_INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS ix_zonal_values_rdo_code_trgm ON zonal_values USING GIN (rdo_code gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS ix_zonal_values_region_trgm ON zonal_values USING GIN (region gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS ix_zonal_values_province_trgm ON zonal_values USING GIN (province gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS ix_zonal_values_city_municipality_trgm ON zonal_values USING GIN (city_municipality gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS ix_zonal_values_barangay_trgm ON zonal_values USING GIN (barangay gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS ix_zonal_values_street_subdivision_trgm ON zonal_values USING GIN (street_subdivision gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS ix_zonal_values_property_class_trgm ON zonal_values USING GIN (property_class gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS ix_zonal_values_property_type_trgm ON zonal_values USING GIN (property_type gin_trgm_ops)",
    f"CREATE INDEX IF NOT EXISTS ix_zonal_values_search_blob_trgm ON zonal_values USING GIN (({SEARCH_BLOB_SQL}) gin_trgm_ops)",
]


def is_postgres_engine(engine: Engine) -> bool:
    return engine.dialect.name == "postgresql"


def apply_postgres_optimizations(engine: Engine) -> None:
    if not is_postgres_engine(engine):
        return

    with engine.begin() as connection:
        for statement in BASE_INDEX_STATEMENTS:
            connection.execute(text(statement))

    trgm_available = False
    with engine.begin() as connection:
        trgm_available = (
            connection.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")).scalar_one_or_none() == 1
        )

    if not trgm_available:
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            trgm_available = True
        except SQLAlchemyError as error:
            logger.warning("pg_trgm extension unavailable; trigram indexes skipped: %s", error)
            return

    with engine.begin() as connection:
        for statement in TRIGRAM_INDEX_STATEMENTS:
            connection.execute(text(statement))
