from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import Base, SessionLocal, engine
from app.services.ingestion import ingest_folder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest zonal-value Excel files from a folder.")
    parser.add_argument(
        "--folder",
        required=True,
        type=Path,
        help="Path to folder containing .xlsx/.xls/.xlsm files.",
    )
    parser.add_argument(
        "--dataset-version",
        required=True,
        type=str,
        help="Version label, e.g. RMC-2026-01.",
    )
    parser.add_argument("--default-region", type=str, default=None, help="Default region fallback.")
    parser.add_argument("--default-province", type=str, default=None, help="Default province fallback.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.folder.exists() or not args.folder.is_dir():
        print(f"Folder not found: {args.folder}")
        return 1

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        workbook_count, inserted_count, skipped_count = ingest_folder(
            session,
            folder_path=args.folder,
            dataset_version=args.dataset_version,
            default_region=args.default_region,
            default_province=args.default_province,
        )
    print(
        f"Ingestion finished. Workbooks: {workbook_count}, inserted rows: {inserted_count}, skipped rows: {skipped_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

