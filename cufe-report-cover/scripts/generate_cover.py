#!/usr/bin/env python3
"""Generate CUFE course-paper or lab-report cover PDFs without LaTeX or DOCX."""

from __future__ import annotations

import argparse
import json
import os
import sys
from io import BytesIO
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


def import_reportlab():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas
        return A4, pdfmetrics, UnicodeCIDFont, TTFont, canvas
    except Exception as first_exc:
        if enable_vendor_if_compatible(allow_binary_mismatch=True):
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.cidfonts import UnicodeCIDFont
                from reportlab.pdfbase.ttfonts import TTFont
                from reportlab.pdfgen import canvas
                return A4, pdfmetrics, UnicodeCIDFont, TTFont, canvas
            except Exception as vendor_exc:
                raise dependency_error("reportlab", vendor_exc) from vendor_exc
        raise dependency_error("reportlab", first_exc) from first_exc


A4, pdfmetrics, UnicodeCIDFont, TTFont, canvas = import_reportlab()

ASSETS = ROOT / "assets"
COURSE_COVER_PAGE1 = ASSETS / "course_paper_cover_page1.pdf"
LAB_COVER_PAGE1 = ASSETS / "lab_report_cover_page1.pdf"

ALIASES = {
    "term": ["term", "学年学期", "semester", "school_term"],
    "course": ["course", "课程名称", "course_name"],
    "course_id": ["course_id", "课程代码", "course_code"],
    "teacher": ["teacher", "任课教师", "advisor", "instructor"],
    "class_name": ["class_name", "班级", "class"],
    "student_id": ["student_id", "学号", "id"],
    "student_name": ["student_name", "姓名", "name"],
    "score": ["score", "总分"],
    "grader": ["grader", "评分人"],
    "project_name": ["project_name", "项目名称", "title", "实验名称"],
    "experiment_type": ["experiment_type", "实验类型", "type"],
    "experiment_date": ["experiment_date", "实验日期", "date"],
}


def load_data(path: str | None, field_overrides: list[str]) -> dict[str, str]:
    raw: dict[str, object] = {}
    if path:
        data_path = Path(path)
        text = data_path.read_text(encoding="utf-8")
        if data_path.suffix.lower() == ".json":
            raw = json.loads(text)
        else:
            try:
                import yaml
            except ImportError as exc:
                if enable_vendor_if_compatible():
                    try:
                        import yaml
                    except Exception as vendor_exc:
                        raise dependency_error("pyyaml", vendor_exc) from vendor_exc
                else:
                    raise dependency_error("pyyaml", exc) from exc
            loaded = yaml.safe_load(text)
            raw = loaded or {}

    for item in field_overrides:
        if "=" not in item:
            raise SystemExit(f"Invalid --field value {item!r}; use key=value.")
        key, value = item.split("=", 1)
        raw[key.strip()] = value.strip()

    normalized: dict[str, str] = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            if alias in raw and raw[alias] is not None:
                normalized[canonical] = str(raw[alias])
                break
    return normalized


def register_font() -> str:
    custom_font = os.environ.get("CUFE_COVER_FONT")
    if custom_font:
        try:
            font_name = "CUFEFieldFont"
            pdfmetrics.registerFont(TTFont(font_name, custom_font))
            return font_name
        except Exception as exc:
            raise SystemExit(f"Could not load CUFE_COVER_FONT={custom_font!r}: {exc}") from exc

    font_name = "STSong-Light"
    pdfmetrics.registerFont(UnicodeCIDFont(font_name))
    return font_name


def fit_text(c: canvas.Canvas, text: str, font: str, max_width: float, base_size: float, min_size: float = 8) -> float:
    size = base_size
    while size > min_size and c.stringWidth(text, font, size) > max_width:
        size -= 0.5
    return size


def draw_centered_text(
    c: canvas.Canvas,
    text: str,
    font: str,
    center_x: float,
    baseline_y: float,
    max_width: float,
    base_size: float = 16,
) -> None:
    size = fit_text(c, text, font, max_width, base_size)
    c.setFillColorRGB(0, 0, 0)
    c.setFont(font, size)
    c.drawCentredString(center_x, baseline_y, text)


def merge_overlay(base_pdf: Path, overlay_pdf_bytes: bytes, output: Path) -> None:
    try:
        from pypdf import PdfReader, PdfWriter
    except Exception as exc:
        if enable_vendor_if_compatible():
            try:
                from pypdf import PdfReader, PdfWriter
            except Exception as vendor_exc:
                raise dependency_error("pypdf", vendor_exc) from vendor_exc
        else:
            raise dependency_error("pypdf", exc) from exc

    base_reader = PdfReader(str(base_pdf))
    overlay_reader = PdfReader(BytesIO(overlay_pdf_bytes))
    page = base_reader.pages[0]
    page.merge_page(overlay_reader.pages[0])
    writer = PdfWriter()
    writer.add_page(page)
    with output.open("wb") as f:
        writer.write(f)


def draw_course_overlay(data: dict[str, str]) -> bytes:
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    font = register_font()

    labels = [
        ("term", 531.1),
        ("course", 497.4),
        ("course_id", 465.5),
        ("teacher", 429.4),
        ("class_name", 395.7),
        ("student_id", 364.5),
        ("student_name", 329.0),
        ("score", 263.4),
        ("grader", 229.7),
    ]

    line_x1 = 217.8
    line_x2 = 444.0
    value_center = (line_x1 + line_x2) / 2

    for key, line_y in labels:
        c.setFillColorRGB(1, 1, 1)
        c.rect(line_x1 - 2, line_y + 1, line_x2 - line_x1 + 4, 26, stroke=0, fill=1)
        draw_centered_text(c, data.get(key, ""), font, value_center, line_y + 6, line_x2 - line_x1 - 8, base_size=15)

    c.showPage()
    c.save()
    return packet.getvalue()


def draw_course_paper_cover(data: dict[str, str], output: Path) -> None:
    merge_overlay(COURSE_COVER_PAGE1, draw_course_overlay(data), output)


def draw_lab_overlay(data: dict[str, str]) -> bytes:
    packet = BytesIO()
    width, height = A4
    c = canvas.Canvas(packet, pagesize=A4)
    font = register_font()

    # Coordinates are calibrated against assets/lab_report_cover_page1.pdf.
    fields = [
        ("project_name", 331, 418, 185),
        ("course", 331, 386, 185),
        ("experiment_type", 331, 354, 185),
        ("experiment_date", 331, 323, 185),
        ("teacher", 331, 291, 185),
        ("class_name", 331, 228, 185),
        ("student_id", 331, 196, 185),
        ("student_name", 331, 165, 185),
    ]
    for key, center_x, baseline_y, max_width in fields:
        draw_centered_text(c, data.get(key, ""), font, center_x, baseline_y, max_width, base_size=14)

    c.showPage()
    c.save()
    return packet.getvalue()


def draw_lab_report_cover(data: dict[str, str], output: Path) -> None:
    merge_overlay(LAB_COVER_PAGE1, draw_lab_overlay(data), output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a CUFE report cover PDF.")
    parser.add_argument("--type", required=True, choices=["course-paper", "lab-report"], help="Cover template to use.")
    parser.add_argument("--data", help="YAML or JSON file containing cover fields.")
    parser.add_argument("--field", action="append", default=[], help="Override/add one field as key=value. Can be repeated.")
    parser.add_argument("--output", required=True, help="Output PDF path.")
    args = parser.parse_args()

    data = load_data(args.data, args.field)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if args.type == "course-paper":
        draw_course_paper_cover(data, output)
    else:
        draw_lab_report_cover(data, output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
