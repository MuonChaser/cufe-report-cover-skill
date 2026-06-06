#!/usr/bin/env python3
"""Prepend a generated cover PDF to a report PDF."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))

try:
    from pypdf import PdfReader, PdfWriter
except ImportError as exc:
    raise SystemExit("Missing dependency: pypdf. Install with `python3 -m pip install pypdf`.") from exc


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
