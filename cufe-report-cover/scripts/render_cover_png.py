#!/usr/bin/env python3
"""Render a CUFE cover template to PNG and paint field values with a CJK font."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"
ASSETS = ROOT / "assets"
COURSE_COVER_PAGE1 = ASSETS / "course_paper_cover_page1.pdf"
LAB_COVER_PAGE1 = ASSETS / "lab_report_cover_page1.pdf"

A4_WIDTH_PT = 595.2756
A4_HEIGHT_PT = 841.8898

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

COURSE_FIELDS = [
    ("term", 330.9, 537.1, 226.2, 15),
    ("course", 330.9, 503.4, 226.2, 15),
    ("course_id", 330.9, 471.5, 226.2, 15),
    ("teacher", 330.9, 435.4, 226.2, 15),
    ("class_name", 330.9, 401.7, 226.2, 15),
    ("student_id", 330.9, 370.5, 226.2, 15),
    ("student_name", 330.9, 335.0, 226.2, 15),
    ("score", 330.9, 269.4, 226.2, 15),
    ("grader", 330.9, 235.7, 226.2, 15),
]

LAB_FIELDS = [
    ("project_name", 331, 418, 185, 14),
    ("course", 331, 386, 185, 14),
    ("experiment_type", 331, 354, 185, 14),
    ("experiment_date", 331, 323, 185, 14),
    ("teacher", 331, 291, 185, 14),
    ("class_name", 331, 228, 185, 14),
    ("student_id", 331, 196, 185, 14),
    ("student_name", 331, 165, 185, 14),
]


def enable_vendor_if_compatible() -> bool:
    if os.environ.get("CUFE_COVER_NO_VENDOR"):
        return False
    if not VENDOR.exists() or str(VENDOR) in sys.path:
        return VENDOR.exists()
    if not os.environ.get("CUFE_COVER_FORCE_VENDOR"):
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


def import_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
        return Image, ImageDraw, ImageFont
    except Exception as first_exc:
        if enable_vendor_if_compatible():
            try:
                from PIL import Image, ImageDraw, ImageFont
                return Image, ImageDraw, ImageFont
            except Exception as vendor_exc:
                raise dependency_error("pillow", vendor_exc) from vendor_exc
        raise dependency_error("pillow", first_exc) from first_exc


Image, ImageDraw, ImageFont = import_pillow()


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


def find_font(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit).expanduser()
        if not path.exists():
            raise SystemExit(f"Font does not exist: {path}")
        return path

    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansSC-Regular.ttf",
        "/System/Library/Fonts/Supplemental/NotoSansKaithi-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "C:/Windows/Fonts/simkai.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return path
    raise SystemExit("No CJK font found. Pass --font-path, preferably a Simplified Chinese font.")


def render_template(pdf_path: Path, output_png: Path, dpi: int) -> None:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise SystemExit("Missing dependency: pdftoppm. Install poppler-utils or pass an existing PNG to prepend_docx_cover.py.")
    with tempfile.TemporaryDirectory() as tmp:
        prefix = Path(tmp) / "cover"
        cmd = [pdftoppm, "-f", "1", "-l", "1", "-png", "-singlefile", "-r", str(dpi), str(pdf_path), str(prefix)]
        subprocess.run(cmd, check=True)
        rendered = prefix.with_suffix(".png")
        output_png.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(rendered, output_png)


def pt_to_px_x(x_pt: float, dpi: int, offset_px: float) -> float:
    return x_pt / 72.0 * dpi + offset_px


def pt_to_px_y(y_pt: float, dpi: int, offset_px: float) -> float:
    return (A4_HEIGHT_PT - y_pt) / 72.0 * dpi + offset_px


def fit_font(font_path: Path, font_index: int, text: str, max_width_px: float, base_pt: float, dpi: int):
    size_px = max(1, round(base_pt * dpi / 72.0))
    min_px = max(1, round(8 * dpi / 72.0))
    while size_px >= min_px:
        font = ImageFont.truetype(str(font_path), size=size_px, index=font_index)
        bbox = font.getbbox(text)
        if bbox[2] - bbox[0] <= max_width_px:
            return font
        size_px -= 1
    return ImageFont.truetype(str(font_path), size=min_px, index=font_index)


def paint_fields(
    png_path: Path,
    data: dict[str, str],
    cover_type: str,
    font_path: Path,
    font_index: int,
    dpi: int,
    field_offset_x: float,
    field_offset_y: float,
) -> None:
    img = Image.open(png_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    fields = COURSE_FIELDS if cover_type == "course-paper" else LAB_FIELDS
    for key, center_x_pt, baseline_y_pt, max_width_pt, base_pt in fields:
        text = data.get(key, "")
        if not text:
            continue
        font = fit_font(font_path, font_index, text, max_width_pt / 72.0 * dpi, base_pt, dpi)
        x = pt_to_px_x(center_x_pt, dpi, field_offset_x)
        y = pt_to_px_y(baseline_y_pt, dpi, field_offset_y)
        draw.text((x, y), text, font=font, fill=(0, 0, 0), anchor="ms")
    img.save(png_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a CUFE cover template to PNG and paint field values.")
    parser.add_argument("--type", required=True, choices=["course-paper", "lab-report"], help="Cover template to use.")
    parser.add_argument("--data", help="YAML or JSON file containing cover fields.")
    parser.add_argument("--field", action="append", default=[], help="Override/add one field as key=value. Can be repeated.")
    parser.add_argument("--output", required=True, help="Output PNG path.")
    parser.add_argument("--dpi", type=int, default=220, help="Render DPI for the output PNG.")
    parser.add_argument("--font-path", help="CJK font path for field values.")
    parser.add_argument("--font-index", type=int, default=2, help="Font face index for TTC collections; Noto Sans CJK SC is usually 2.")
    parser.add_argument("--field-offset-x", type=float, default=0, help="Global field x-offset in output pixels.")
    parser.add_argument("--field-offset-y", type=float, default=0, help="Global field y-offset in output pixels.")
    args = parser.parse_args()

    output = Path(args.output)
    template = COURSE_COVER_PAGE1 if args.type == "course-paper" else LAB_COVER_PAGE1
    data = load_data(args.data, args.field)
    font_path = find_font(args.font_path)

    render_template(template, output, args.dpi)
    paint_fields(output, data, args.type, font_path, args.font_index, args.dpi, args.field_offset_x, args.field_offset_y)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
