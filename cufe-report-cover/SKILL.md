---
name: cufe-report-cover
description: Generate Central University of Finance and Economics (CUFE, 中央财经大学) report cover PDFs/PNGs and prepend cover pages to PDFs or DOCX files for course papers and lab reports. Use when a user needs a CUFE 课程论文封面 or 实验报告封面, needs a one-page cover PDF/PNG, wants to prepend a cover to an existing report PDF/DOCX, or asks to avoid LaTeX/DOCX template editing while preserving the original cover layout.
---

# CUFE Report Cover

## Overview

Generate a one-page CUFE cover from structured fields. Do not edit the original cover templates through DOCX, Word, WPS, Google Docs, or office conversion workflows; these often reflow Chinese fonts, lines, and spacing. Generate a fresh cover PDF/PNG with the bundled scripts, then replace/prepend the report's existing cover page if needed.

## Template Choice

- Use `--type course-paper` for 课程论文封面. This uses page 1 of `assets/course_paper_cover_page1.pdf` as the fixed background and overlays field values.
- Use `--type lab-report` for 实验报告封面. This uses only page 1 of `assets/lab_report_cover_page1.pdf` as the fixed background and overlays field values. Ignore page 2 of the source lab template unless the user explicitly asks for it.

If the user provides an existing report that already has an old or broken cover, create the new one-page cover with `generate_cover.py`, then rebuild the PDF so the new cover replaces the old first page. Prefer PDF page operations with `pypdf`; do not round-trip through DOCX or office editors.

## Quick Start

Create a data file:

```yaml
project_name: "地方政府债利率实验"
course: "金融统计学"
experiment_type: "综合实验"
experiment_date: "2026年6月6日"
teacher: "任课教师姓名"
class_name: "专业班级"
student_id: "学号"
student_name: "姓名"
```

Generate a lab-report cover:

```bash
python3 /path/to/cufe-report-cover/scripts/generate_cover.py \
  --type lab-report \
  --data cover.yaml \
  --output cover.pdf
```

Generate a course-paper cover:

```yaml
term: "2025-2026 第一学期"
course: "数学与统计建模案例"
course_id: "4012012"
teacher: "任课教师姓名"
class_name: "专业班级"
student_id: "学号"
student_name: "姓名"
score: ""
grader: ""
```

```bash
python3 /path/to/cufe-report-cover/scripts/generate_cover.py \
  --type course-paper \
  --data cover.yaml \
  --output cover.pdf
```

Fields can also be passed or overridden inline:

```bash
python3 /path/to/cufe-report-cover/scripts/generate_cover.py \
  --type lab-report \
  --field project_name="地方政府债利率实验" \
  --field course="金融统计学" \
  --field student_name="姓名" \
  --output cover.pdf
```

## Merge With Report

To prepend the generated cover to a body PDF:

```bash
python3 /path/to/cufe-report-cover/scripts/merge_cover.py \
  --cover cover.pdf \
  --body report_body.pdf \
  --output report_with_cover.pdf
```

If the input PDF already includes an old cover, drop the old first page while merging:

```bash
python3 /path/to/cufe-report-cover/scripts/merge_cover.py \
  --cover cover.pdf \
  --body report_with_old_cover.pdf \
  --drop-body-first-page \
  --output report_with_new_cover.pdf
```

Keep all operations at PDF level. Do not convert the template or report through DOCX/Word/WPS/Google Docs to edit it.

## DOCX Cover Insertion

For a DOCX deliverable, do not rebuild the cover as Word text, shapes, or tables. Render the CUFE cover to a full-page PNG and insert that image as page 1:

```bash
python3 /path/to/cufe-report-cover/scripts/prepend_docx_cover.py \
  --type course-paper \
  --data cover.yaml \
  --input-docx report_body.docx \
  --output-docx report_with_cover.docx \
  --preview-png cover_preview.png
```

`prepend_docx_cover.py`:

- renders the original PDF template background with `pdftoppm`
- overlays field values onto the PNG with Pillow
- defaults `--font-index 2`, which is the Simplified Chinese face in `NotoSansCJK-Regular.ttc`
- inserts the PNG as a full A4 first page
- sets the cover section margins to `0`
- restores body margins to top/bottom `2.5cm`, left/right `2.3cm` unless overridden

Use `--field-offset-y -12` or `--field-offset-x <px>` when all fields need a small global adjustment on the rendered PNG.

## Font Preservation

Template content is preserved as the original PDF background, so the school logo, headings, labels, lines, and existing template typography are not redrawn. Field values in generated PDFs are overlaid by ReportLab with `STSong-Light` by default for reliable PDF merging. Field values in rendered PNG/DOCX covers are overlaid by Pillow with a real CJK font; for `.ttc` collections, pass `--font-index`, defaulting to `2` for `Noto Sans CJK SC`.

## Dependencies

Install only lightweight Python packages as needed:

```bash
cd /path/to/cufe-report-cover
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Use JSON input instead of YAML if `pyyaml` is unavailable. The scripts use paths relative to the skill folder, so they can be copied to another machine as long as `assets/`, `scripts/`, and `requirements.txt` stay together.

## Assets

- `assets/course_paper_cover_page1.pdf`: fixed first-page course-paper cover background.
- `assets/lab_report_cover_page1.pdf`: fixed first-page lab-report cover background. Use page 1 only.
