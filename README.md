# ECU Calibration Analyzer

Desktop-oriented calibration review tool for ECU binary files and WinOLS/map-pack definitions.

The app is intended as tuner decision support: it compares an original calibration with an optional tuned/current file, extracts defined maps, highlights changed areas, gives structured tuning recommendations, shows 3D map previews, and exports a PDF report. It does not produce flash-ready files and does not replace real log, dyno, safety, or hardware validation.

## Current Workflow

1. Start the backend API.
2. Start the Flutter frontend.
3. Load:
   - original ECU/calibration binary
   - optional tuned/current binary
   - optional WinOLS/map-pack definition file (`.kp`, `.csv`, `.json`)
4. Run calibration analysis.
5. Review:
   - global verdict
   - priority recommendations
   - AI-assisted review notes
   - focused map browser and 3D map previews
   - PDF report export

## Main Features

- Binary diff summary between original and tuned/current files.
- Map extraction from real calibration files using map definitions.
- WinOLS `.kp` parser support.
- Rule-based recommendation engine for torque, fuel, air/lambda, boost, timing, rail pressure, and limiters.
- AI-assisted second-opinion layer trained from reviewed map-level labels.
- Focus flow between recommendations and related maps.
- Flutter-rendered 3D surface previews.
- PDF report with executive summary, verdict, priority recommendations, visual map highlights, top changed maps, and validation checklist.

## Repository Layout

```text
backend/
  app/
    api/                  FastAPI routes
    models/               Request schemas
    services/             Calibration parsing, analysis, recommendations, ML integration, PDF generation
  ml/                     Training and prediction scripts for the calibration label baseline
  scripts/                Dataset preparation scripts
  generated/              Local generated datasets/reports; ignored by git

frontend/
  lib/                    Flutter app
  test/                   Flutter widget tests
```

## Backend

From `backend`:

```powershell
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The frontend expects the API at:

```text
http://127.0.0.1:8000
```

Important endpoints:

- `POST /api/calibration/analyze`
- `POST /api/calibration/report`
- `POST /api/calibration/ml-dataset` development-only
- `POST /api/calibration/labeling-template` development-only

## Frontend

From `frontend`:

```powershell
flutter pub get
flutter run -d windows
```

Useful checks:

```powershell
dart analyze
flutter test
```

## AI/ML Notes

The runtime model is a small baseline used as advisory evidence only. Rule-based recommendations remain the primary decision layer.

Training data is built from reviewed CSV files in:

```text
backend/generated/labeled_datasets/
```

Generated datasets and reports under `backend/generated/` are intentionally ignored by git. Do not commit local training datasets such as `training_dataset.csv`.

See:

- `backend/ml/README.md`
- `backend/scripts/README.md`

## Safety Scope

Recommendations are decision-support guidance. Before applying any calibration changes, validate with real logs and hardware-specific constraints, including AFR/lambda, EGT, knock/noise, temperatures, drivetrain limits, and mechanical/thermal protections.
