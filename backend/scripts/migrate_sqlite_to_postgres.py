from __future__ import annotations

import argparse
import csv
import io
from pathlib import Path
import sqlite3
import sys

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import models  # noqa: F401
from app.config import get_settings
from app.database import Base, engine
from app.services.postgres_optimization import apply_postgres_optimizations


COLUMNS = [
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
    "source_file",
    "source_sheet",
    "source_row",
    "dataset_version",
    "created_at",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate zonal values from SQLite to PostgreSQL.")
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=ROOT / "zonalhub.db",
        help="Path to source SQLite database.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10000,
        help="Rows per batch during COPY.",
    )
    return parser.parse_args()


def to_psycopg_dsn(sqlalchemy_url: str) -> str:
    if sqlalchemy_url.startswith("postgresql+psycopg://"):
        return "postgresql://" + sqlalchemy_url.split("postgresql+psycopg://", 1)[1]
    if sqlalchemy_url.startswith("postgresql://"):
        return sqlalchemy_url
    raise ValueError("DATABASE_URL must be PostgreSQL for this migration script.")


def main() -> int:
    args = parse_args()
    sqlite_path = args.sqlite_path
    if not sqlite_path.exists():
        print(f"SQLite source not found: {sqlite_path}")
        return 1

    settings = get_settings()
    dsn = to_psycopg_dsn(settings.database_url)

    # Recreate table so Postgres schema matches current SQLAlchemy model types.
    Base.metadata.drop_all(bind=engine, tables=[models.ZonalValue.__table__])
    Base.metadata.create_all(bind=engine, tables=[models.ZonalValue.__table__])

    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    sqlite_cur.execute(f"SELECT {', '.join(COLUMNS)} FROM zonal_values ORDER BY id")

    total_rows = sqlite_conn.execute("SELECT COUNT(*) FROM zonal_values").fetchone()[0]
    print(f"Source rows: {total_rows}")

    copied_rows = 0
    with psycopg.connect(dsn) as pg_conn:
        with pg_conn.cursor() as pg_cur:
            while True:
                rows = sqlite_cur.fetchmany(args.batch_size)
                if not rows:
                    break

                buffer = io.StringIO()
                writer = csv.writer(buffer, lineterminator="\n")
                for row in rows:
                    writer.writerow([row[column] for column in COLUMNS])
                buffer.seek(0)

                copy_sql = f"COPY zonal_values ({', '.join(COLUMNS)}) FROM STDIN WITH (FORMAT CSV)"
                with pg_cur.copy(copy_sql) as copy:
                    copy.write(buffer.getvalue())
                pg_conn.commit()

                copied_rows += len(rows)
                print(f"Copied {copied_rows}/{total_rows}")

            pg_cur.execute(
                """
                SELECT setval(
                  pg_get_serial_sequence('zonal_values', 'id'),
                  COALESCE((SELECT MAX(id) FROM zonal_values), 1),
                  true
                )
                """
            )
            pg_conn.commit()

            apply_postgres_optimizations(engine)

            pg_cur.execute("SELECT COUNT(*) FROM zonal_values")
            target_count = pg_cur.fetchone()[0]
            print(f"Target rows: {target_count}")

    sqlite_conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
