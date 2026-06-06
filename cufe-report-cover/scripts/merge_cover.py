#!/usr/bin/env python3
"""Prepend a generated cover PDF to a report PDF."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"


def enable_vendor_if_compatible(allow_binary_mismatch: bool = False) -> bool:
    if os.environ.get("CUFE_COVER_NO_VENDOR"):
        return False
    if not VENDOR.exists() or str(VENDOR) in sys.path:
        return VENDOR.exists()
    if not allow_binary_mismatch and not os.environ.get("CUFE_COVER_FORCE_VENDOR"):
        cache_tag = sys.implementation.cache_tag
        binary_modules = list(VENDOR.rglob("*.so")) + list(VENDOR.rglob("*.pyd"))
        incompatible = [
            path.name
            for path in binary_modules
            if "cpython-" in path.name and cache_tag not in path.name
        ]
        if incompatible:
            return False
    sys.path.insert(0, str(VENDOR))
    return True


def dependency_error(package: str, exc: BaseException) -> SystemExit:
    return SystemExit(
        f"Missing dependency: {package}. Install with `python3 -m pip install -r requirements.txt`, "
        f"use a matching Python for cufe-report-cover/vendor, or set CUFE_COVER_NO_VENDOR=1 "
        f"to ignore vendored packages. Current Python ABI is {sys.implementation.cache_tag}. "
        f"Original error: {exc}"
    )


def import_pypdf():
    try:
        from pypdf import PdfReader, PdfWriter
        return PdfReader, PdfWriter
    except Exception as first_exc:
        if enable_vendor_if_compatible(allow_binary_mismatch=True):
            try:
                from pypdf import PdfReader, PdfWriter
                return PdfReader, PdfWriter
            except Exception as vendor_exc:
                raise dependency_error("pypdf", vendor_exc) from vendor_exc
        raise dependency_error("pypdf", first_exc) from first_exc


PdfReader, PdfWriter = import_pypdf()


def append_pages(writer: PdfWriter, path: Path, skip_first: bool = False) -> None:
    reader = PdfReader(str(path))
    start = 1 if skip_first else 0
    for page in reader.pages[start:]:
        writer.add_page(page)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepend a cover PDF to a body PDF.")
    parser.add_argument("--cover", required=True, help="Generated one-page cover PDF.")
    parser.add_argument("--body", required=True, help="Existing report body PDF.")
    parser.add_argument("--output", required=True, help="Merged output PDF.")
    parser.add_argument(
        "--drop-body-first-page",
        action="store_true",
        help="Drop page 1 from the body PDF before prepending the new cover.",
    )
    args = parser.parse_args()

    writer = PdfWriter()
    append_pages(writer, Path(args.cover))
    append_pages(writer, Path(args.body), skip_first=args.drop_body_first_page)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as f:
        writer.write(f)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
