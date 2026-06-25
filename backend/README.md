# ECU Calibration Analyzer Backend

FastAPI backend for calibration file parsing, map extraction, recommendations, AI-assisted review, and PDF report generation.

## Requirements

- Python 3.12 recommended
- Dependencies from `requirements.txt`

Install from `backend`:

```powershell
python -m pip install -r requirements.txt
```

## Run API

From `backend`:

```powershell
uvicorn app.main:app --reload
```

Default local URL:

```text
http://127.0.0.1:8000
```

## Run Tests

From `backend`:

```powershell
python -m pytest tests
```

The backend test suite covers ECU file decoding, CSV/JSON map definition parsing, map extraction and comparison, central calibration analysis behavior, verdict generation, recommendation logic, ML fallback behavior, negative API validation, the main calibration analysis endpoint, and PDF report generation.

## Main Endpoints

```text
POST /api/calibration/analyze
POST /api/calibration/report
```

Development-only dataset endpoints:

```text
POST /api/calibration/ml-dataset
POST /api/calibration/labeling-template
```

## Input Files

The main analysis accepts:

- original ECU/calibration file
- optional tuned/current ECU/calibration file
- optional map definitions file (`.kp`, `.csv`, `.json`)

Binary-like calibration files are read as raw binary unless they match supported text formats such as Intel HEX or Motorola S-record.

## Output

Analysis returns:

- file and binary diff summary
- extracted maps
- changed-map findings
- global verdict
- rule-based recommendations
- AI-assisted evidence when model artifacts are available
- map-level previews and 3D surface data
- report payload used by the PDF generator

The report endpoint writes a temporary PDF to:

```text
backend/generated/calibration_tuner_report.pdf
```

`backend/generated/` is ignored by git.

## Important Services

```text
app/services/file_formats.py          ECU file decoding
app/services/map_definitions.py       Map-pack and definition parsing
app/services/calibration_maps.py      Map extraction and diffing
app/services/calibration_recommender.py
app/services/calibration_analyzer.py  Main analysis orchestration
app/services/calibration_ml.py        Runtime AI-assisted review integration
app/services/report_generator.py      PDF generation
```

## ML and Dataset Workflow

See:

```text
backend/ml/README.md
backend/scripts/README.md
```

Generated datasets, labeling CSV files, predictions, and PDF outputs should stay under `backend/generated/` and should not be committed by default.

## Safety

The backend provides decision-support recommendations only. It does not generate flash-ready calibration files. All suggested changes require tuner review and real-world validation.
