from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shutil
from urllib.error import HTTPError
from urllib.parse import quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen
import zipfile


ZONAL_PAGE_URL = "https://www.bir.gov.ph/zonal-values"
CMS_BASE_URL = "https://bir-cms-ws.bir.gov.ph"
REQUEST_HEADERS = {
    "client-website-id": "2",
    "origin": "https://www.bir.gov.ph",
    "referer": ZONAL_PAGE_URL,
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    ),
    "accept": "application/json, text/plain, */*",
}
ALLOWED_WORKBOOK_EXTENSIONS = {".xlsx", ".xlsm", ".xls"}


@dataclass
class AttachmentRecord:
    template_code: str
    dataset_id: int | None
    dataset_name: str | None
    rdo: str | None
    province: str | None
    content_key: str
    url: str
    source_value: str


def _request_text(url: str, headers: dict[str, str], timeout_seconds: int = 60) -> str:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8", errors="ignore")


def _request_json(url: str, headers: dict[str, str], timeout_seconds: int = 60) -> dict:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8", errors="ignore"))


def _extract_template_codes(page_html: str) -> list[str]:
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', page_html, flags=re.S)
    decoded = "\n".join(chunks).encode("utf-8").decode("unicode_escape")
    codes = sorted(set(re.findall(r'"code":"(\d+)"', decoded)), key=lambda value: int(value))
    return codes


def _extract_attachment_records(template_code: str, rows: list[dict]) -> list[AttachmentRecord]:
    records: list[AttachmentRecord] = []
    for row in rows:
        content = row.get("content") or {}
        if not isinstance(content, dict):
            continue

        for content_key, raw_value in content.items():
            values: list[str] = []
            if isinstance(raw_value, str):
                values = [raw_value]
            elif isinstance(raw_value, list):
                values = [entry for entry in raw_value if isinstance(entry, str)]

            for value in values:
                if "http" not in value.lower():
                    continue
                url = value.split("|", 1)[0].strip()
                if not url.startswith("http"):
                    continue
                records.append(
                    AttachmentRecord(
                        template_code=template_code,
                        dataset_id=row.get("id"),
                        dataset_name=row.get("name"),
                        rdo=content.get("RDO"),
                        province=content.get("Province"),
                        content_key=str(content_key),
                        url=url,
                        source_value=value,
                    )
                )
    return records


def _safe_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    basename = unquote(Path(parsed.path).name) or "file"
    sanitized = re.sub(r"[^A-Za-z0-9._ -]+", "_", basename).strip(" ._")
    if not sanitized:
        sanitized = "file"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return f"{digest}_{sanitized}"


def _download_binary_file(url: str, destination: Path) -> None:
    parsed = urlparse(url)
    quoted_path = quote(parsed.path, safe="/._-()[]")
    safe_url = f"{parsed.scheme}://{parsed.netloc}{quoted_path}"
    if parsed.query:
        safe_url = f"{safe_url}?{parsed.query}"
    request = Request(safe_url, headers=REQUEST_HEADERS)
    with urlopen(request, timeout=180) as response:
        destination.write_bytes(response.read())


def _extract_workbooks(downloaded_file: Path, extracted_dir: Path) -> list[Path]:
    extracted_files: list[Path] = []
    suffix = downloaded_file.suffix.lower()

    if suffix in ALLOWED_WORKBOOK_EXTENSIONS:
        target = extracted_dir / downloaded_file.name
        if not target.exists():
            shutil.copy2(downloaded_file, target)
        extracted_files.append(target)
        return extracted_files

    if suffix != ".zip":
        return extracted_files

    try:
        with zipfile.ZipFile(downloaded_file) as zip_file:
            for member in zip_file.infolist():
                if member.is_dir():
                    continue
                member_name = Path(member.filename).name
                member_suffix = Path(member_name).suffix.lower()
                if member_suffix not in ALLOWED_WORKBOOK_EXTENSIONS:
                    continue

                safe_name = re.sub(r"[^A-Za-z0-9._ -]+", "_", member_name).strip(" ._") or "workbook.xls"
                target = extracted_dir / f"{downloaded_file.stem}__{safe_name}"
                if target.exists():
                    extracted_files.append(target)
                    continue

                with zip_file.open(member) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                extracted_files.append(target)
    except zipfile.BadZipFile:
        return []

    return extracted_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and extract official BIR zonal value workbooks.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "data" / "raw" / "bir_zonal",
        help="Output root directory for downloads and extracted workbooks.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    downloads_dir = output_dir / "downloads"
    extracted_dir = output_dir / "extracted"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    extracted_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching zonal page: {ZONAL_PAGE_URL}")
    page_html = _request_text(ZONAL_PAGE_URL, headers=REQUEST_HEADERS)
    template_codes = _extract_template_codes(page_html)
    print(f"Found template codes: {len(template_codes)}")

    all_records: list[AttachmentRecord] = []
    missing_templates: list[tuple[str, int]] = []

    for code in template_codes:
        query = urlencode({"per_page": "3000"})
        endpoint = f"{CMS_BASE_URL}/api/pub/templates/{code}/datasets?{query}"
        try:
            payload = _request_json(endpoint, headers=REQUEST_HEADERS)
        except HTTPError as error:
            missing_templates.append((code, error.code))
            continue

        dataset_rows = payload.get("data") or []
        records = _extract_attachment_records(code, dataset_rows)
        all_records.extend(records)
        print(f"Template {code}: rows={len(dataset_rows)} attachments={len(records)}")

    unique_by_url: dict[str, AttachmentRecord] = {}
    for record in all_records:
        unique_by_url.setdefault(record.url, record)

    manifest_items: list[dict] = []
    print(f"Unique attachment URLs: {len(unique_by_url)}")

    for index, (url, record) in enumerate(sorted(unique_by_url.items()), start=1):
        filename = _safe_filename_from_url(url)
        downloaded_file = downloads_dir / filename

        if not downloaded_file.exists():
            try:
                _download_binary_file(url, downloaded_file)
            except Exception as error:  # noqa: BLE001
                print(f"[{index}] FAILED download: {url} ({error})")
                continue

        extracted_files = _extract_workbooks(downloaded_file, extracted_dir)
        print(
            f"[{index}] {downloaded_file.name} -> extracted workbooks: {len(extracted_files)} "
            f"(template {record.template_code})"
        )
        manifest_items.append(
            {
                "template_code": record.template_code,
                "dataset_id": record.dataset_id,
                "dataset_name": record.dataset_name,
                "rdo": record.rdo,
                "province": record.province,
                "content_key": record.content_key,
                "url": url,
                "source_value": record.source_value,
                "downloaded_file": str(downloaded_file),
                "extracted_files": [str(path) for path in extracted_files],
            }
        )

    manifest = {
        "zonal_page_url": ZONAL_PAGE_URL,
        "template_codes": template_codes,
        "missing_templates": [{"template_code": code, "http_status": status} for code, status in missing_templates],
        "attachment_count": len(manifest_items),
        "output_dir": str(output_dir),
        "downloads_dir": str(downloads_dir),
        "extracted_dir": str(extracted_dir),
        "items": manifest_items,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    workbook_files = sorted(
        [
            *extracted_dir.glob("*.xlsx"),
            *extracted_dir.glob("*.xlsm"),
            *extracted_dir.glob("*.xls"),
        ]
    )
    print(f"Done. Downloaded attachments: {len(manifest_items)}")
    print(f"Extracted workbook files: {len(workbook_files)}")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
