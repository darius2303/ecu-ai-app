# ECU Calibration Analyzer Frontend

Flutter desktop frontend for the ECU Calibration Analyzer.

The UI is focused on the final tuner workflow:

- load calibration files
- run analysis
- review the global verdict
- inspect priority recommendations
- focus related maps
- inspect 3D map previews
- export a PDF report

Developer dataset/export tools are hidden by default in the app code.

## Requirements

- Flutter SDK
- Windows desktop support enabled
- Backend API running at `http://127.0.0.1:8000`

From the repository root, the easiest setup is:

```powershell
make install-frontend
make frontend-windows
```

## Run

From `frontend`:

```powershell
flutter pub get
flutter run -d windows
```

## Checks

```powershell
dart analyze
flutter test
```

From the repository root:

```powershell
make analyze
make test
```

## Important Files

```text
lib/main.dart                  Main app UI and interaction flow
lib/services/api_service.dart  Backend API client
test/widget_test.dart          Basic widget smoke tests
```

## UI Flow

1. Select the original calibration file.
2. Optionally select the tuned/current file.
3. Optionally select a map pack/definitions file (`.kp`, `.csv`, `.json`).
4. Enter basic vehicle context when available.
5. Run analysis.
6. Review:
   - global verdict
   - tuner report summary
   - compact recommendation cards
   - AI-assisted checks
   - focused map browser
   - related map/recommendation links
7. Export PDF report.

## Notes

The frontend does not perform calibration logic by itself. Binary parsing, map extraction, recommendations, AI-assisted review, and PDF generation are handled by the backend.
