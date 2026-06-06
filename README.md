# CUFE Report Cover Skill

Generate one-page Central University of Finance and Economics (CUFE, 中央财经大学) report cover PDFs without LaTeX, Word, WPS, DOCX conversion, or office-template editing.

This repository packages a Codex skill for two cover types:

- `course-paper`: 课程论文封面
- `lab-report`: 实验报告封面

Both templates are preserved as PDF backgrounds. The scripts only overlay field values onto the original first-page template, so the school logo, headings, labels, lines, and template typography are not redrawn or reflowed.

## Why This Exists

Editing these covers through DOCX, Word, WPS, or Google Docs can easily change Chinese fonts, spacing, line positions, and PDF layout. This skill keeps the original PDF cover page intact and performs PDF-level overlay/merge operations instead.

The lab report template uses only the first page. If a source lab-report template has additional pages, they are intentionally ignored unless you explicitly handle them yourself.

## Install As A Codex Skill

Clone this repository, then copy or symlink the skill folder into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R cufe-report-cover ~/.codex/skills/
```

After that, another Codex agent can invoke the skill as `$cufe-report-cover`.

## WSL Install With SSH

On WSL, first make sure your SSH key is added to GitHub, then clone the public repository with SSH:

```bash
mkdir -p ~/src ~/.codex/skills
cd ~/src
git clone git@github.com:MuonChaser/cufe-report-cover-skill.git
ln -sfn ~/src/cufe-report-cover-skill/cufe-report-cover ~/.codex/skills/cufe-report-cover
```

Install the lightweight Python dependencies:

```bash
cd ~/src/cufe-report-cover-skill/cufe-report-cover
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Quick smoke test:

```bash
python3 scripts/generate_cover.py \
  --type lab-report \
  --data ../examples/lab-report.yaml \
  --output ../output/lab-cover.pdf
```

## Python Setup

The scripts are intentionally lightweight. Create a virtual environment inside the skill folder:

```bash
cd cufe-report-cover
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Python 3.9+ is recommended. The scripts use `reportlab`, `pypdf`, and `pyyaml`.

## Generate A Lab Report Cover

Create a YAML file like `examples/lab-report.yaml`:

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

Run:

```bash
cd cufe-report-cover
. .venv/bin/activate
python3 scripts/generate_cover.py \
  --type lab-report \
  --data ../examples/lab-report.yaml \
  --output ../output/lab-cover.pdf
```

## Generate A Course Paper Cover

Create a YAML file like `examples/course-paper.yaml`:

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

Run:

```bash
cd cufe-report-cover
. .venv/bin/activate
python3 scripts/generate_cover.py \
  --type course-paper \
  --data ../examples/course-paper.yaml \
  --output ../output/course-cover.pdf
```

## Replace An Existing Cover

If your report PDF already has an old first-page cover, generate a new cover and drop the original first page while merging:

```bash
cd cufe-report-cover
. .venv/bin/activate
python3 scripts/merge_cover.py \
  --cover ../output/lab-cover.pdf \
  --body ../path/to/report-with-old-cover.pdf \
  --drop-body-first-page \
  --output ../output/report-with-new-cover.pdf
```

If the body PDF has no cover, omit `--drop-body-first-page`.

## Inline Fields

You can skip YAML and pass fields directly:

```bash
python3 cufe-report-cover/scripts/generate_cover.py \
  --type lab-report \
  --field project_name="地方政府债利率实验" \
  --field course="金融统计学" \
  --field student_name="姓名" \
  --output output/lab-cover.pdf
```

## Font Notes

Template content is preserved as the original PDF background. Field values are overlaid with ReportLab's `STSong-Light` by default for reliable cross-platform PDF merging.

To force a specific field-value font:

```bash
CUFE_COVER_FONT=/path/to/font.ttf python3 scripts/generate_cover.py ...
```

Always render and inspect the resulting PDF after changing fonts. Some local TTF/TTC fonts do not survive PDF overlay merging consistently across devices.

## Repository Layout

```text
cufe-report-cover-skill/
├── README.md
├── examples/
│   ├── course-paper.yaml
│   └── lab-report.yaml
└── cufe-report-cover/
    ├── SKILL.md
    ├── requirements.txt
    ├── agents/
    │   └── openai.yaml
    ├── assets/
    │   ├── course_paper_cover_page1.pdf
    │   └── lab_report_cover_page1.pdf
    └── scripts/
        ├── generate_cover.py
        └── merge_cover.py
```

## Important Rule For Agents

Do not edit the original cover templates through DOCX, Word, WPS, Google Docs, or office conversion workflows. Generate a fresh one-page cover PDF with this skill, then replace or prepend it at the PDF level.
