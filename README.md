# ECU Calibration Analyzer

ECU Calibration Analyzer este o aplicatie desktop pentru analiza fisierelor de calibrare ECU, a definitiilor de harti, a modificarilor de calibrare si a rapoartelor generate pentru revizuire tehnica.

Proiectul combina un backend FastAPI cu o interfata Flutter. Backend-ul prelucreaza fisierele incarcate, extrage si compara harti de calibrare, genereaza recomandari explicabile, adauga dovezi ML cu rol consultativ si produce rapoarte PDF. Interfata Flutter ofera fluxul de lucru pentru incarcarea fisierelor, rularea analizei, inspectarea recomandarilor, vizualizarea suprafetelor 3D si exportul raportului.

Aplicatia este destinata analizei si asistarii deciziei. Nu genereaza fisiere ECU pregatite pentru flash si nu inlocuieste validarile reale pe dyno, loguri, teste pe vehicul, verificari hardware sau evaluari de siguranta.

## Functionalitati principale

- Incarcarea fisierului original de calibrare ECU.
- Incarcarea optionala a unui fisier modificat/curent pentru comparatie.
- Incarcarea optionala a definitiilor de harti in format `.kp`, `.csv` sau `.json`.
- Decodarea formatelor uzuale de fisiere de calibrare, inclusiv fisiere binare si formate text suportate.
- Extragerea hartilor definite si compararea valorilor originale cu cele modificate.
- Evidentierea modificarilor importante si a zonelor cu risc.
- Generarea de recomandari bazate pe reguli pentru cuplu, combustibil, aer/lambda, boost, avans, presiune in rampa si limitatoare.
- Adaugarea predictiilor ML cu rol consultativ atunci cand artefactele modelului sunt disponibile.
- Legarea recomandarilor de hartile relevante din interfata.
- Afisarea suprafetelor 3D pentru inspectarea hartilor.
- Exportul unui raport PDF cu verdict, tabele de sinteza, dovezi vizuale, recomandari, harti modificate si note de validare.
- Rularea backend-ului, frontend-ului, backend-ului Docker si a verificarilor de calitate printr-un singur script PowerShell.

## Structura proiectului

```text
.
|-- backend/
|   |-- app/
|   |   |-- api/                  Rutele FastAPI
|   |   |-- core/                 Configurarea backend-ului
|   |   |-- models/               Scheme pentru cereri si raspunsuri
|   |   `-- services/             Parsare, analiza, recomandari, ML, rapoarte
|   |-- ml/                       Scripturi de antrenare si predictie
|   |-- scripts/                  Scripturi pentru pregatirea dataseturilor
|   |-- tests/                    Teste backend, API, E2E si regresie vizuala
|   `-- generated/                Fisiere generate local, ignorate de git
|-- frontend/
|   |-- lib/                      Aplicatia Flutter
|   `-- test/                     Teste Flutter
|-- scripts/
|   `-- dev.ps1                  Script principal pentru comenzi de dezvoltare
|-- Makefile                     Scurtaturi optionale peste scripts/dev.ps1
`-- README.md
```

## Cerinte

Mediu local recomandat:

- Windows cu PowerShell.
- Python 3.12 recomandat. Imaginea Docker foloseste in prezent Python 3.11 slim.
- Flutter SDK cu suport pentru Windows desktop activat.
- Docker Desktop, optional, doar pentru rularea backend-ului in container.
- GNU Make, optional. Toate comenzile din Makefile au echivalent in PowerShell.

Scriptul de dezvoltare cauta mai intai Flutter in `C:\flutter`. Daca Flutter este instalat in alta locatie, asigura-te ca `flutter` si `dart` sunt disponibile in `PATH`.

## Pornire rapida

Din radacina proiectului, cea mai simpla varianta pe Windows este:

```powershell
.\scripts\dev.ps1 setup
.\scripts\dev.ps1 app-windows
```

Comanda `setup` creeaza mediul virtual Python local in `.venv`, instaleaza dependintele backend-ului din `backend/requirements.txt` si ruleaza `flutter pub get`.

Comanda `app-windows` porneste backend-ul FastAPI intr-o fereastra separata PowerShell, apoi lanseaza aplicatia Flutter pentru Windows.

Daca GNU Make este instalat, acelasi flux poate fi rulat cu:

```powershell
make setup
make app-windows
```

Backend-ul este disponibil la:

```text
http://127.0.0.1:8000
```

## Rulare manuala

### Backend

Din radacina proiectului:

```powershell
.\scripts\dev.ps1 backend
```

Echivalent manual:

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Daca mediul virtual nu a fost creat inca:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

### Frontend

Din radacina proiectului:

```powershell
.\scripts\dev.ps1 frontend-windows
```

Echivalent manual:

```powershell
cd frontend
flutter pub get
flutter run -d windows
```

Versiunea web poate fi pornita pentru testare in browser:

```powershell
.\scripts\dev.ps1 app-web
```

Aceasta comanda porneste backend-ul si ruleaza Flutter ca web server la:

```text
http://127.0.0.1:5403
```

## Backend cu Docker

Docker este optional si ruleaza doar API-ul backend.

```powershell
.\scripts\dev.ps1 docker-build
.\scripts\dev.ps1 docker-run
```

Echivalent cu Makefile:

```powershell
make docker-build
make docker-run
```

Containerul expune backend-ul la:

```text
http://127.0.0.1:8000
```

Interfata Flutter trebuie pornita separat dupa ce containerul este activ.

## Fluxul aplicatiei

1. Se pornesc backend-ul si frontend-ul.
2. Se selecteaza fisierul original de calibrare ECU.
3. Optional, se selecteaza fisierul modificat/curent.
4. Optional, se selecteaza un map pack sau un fisier cu definitii de harti.
5. Se adauga contextul vehiculului, atunci cand este disponibil:
   - cilindreea motorului
   - puterea stock
   - tipul de combustibil
   - turbo/non-turbo
6. Se ruleaza analiza calibrarii.
7. Se verifica verdictul global, hartile modificate, recomandarile, verificarile ML consultative si suprafetele 3D.
8. Se exporta raportul PDF atunci cand analiza este pregatita pentru documentare.

## API backend

Endpoint-uri principale:

```text
POST /api/calibration/analyze
POST /api/calibration/report
```

Endpoint-uri pentru dataseturi de dezvoltare:

```text
POST /api/calibration/ml-dataset
POST /api/calibration/labeling-template
```

Endpoint-urile de dezvoltare exporta dataseturi intermediare si sabloane folosite pentru revizuirea ML. Acestea nu sunt necesare pentru utilizarea normala a aplicatiei.

## Fisiere de intrare

Analiza accepta:

- fisierul original de calibrare, obligatoriu
- fisierul modificat/curent, optional
- fisierul cu definitii de harti, optional

Formate suportate pentru definitii de harti:

- `.kp`
- `.csv`
- `.json`

Fisierele de calibrare de tip binar sunt tratate ca date brute, cu exceptia cazurilor in care corespund unui format text ECU suportat. Backend-ul normalizeaza continutul fisierelor astfel incat restul fluxului de analiza sa lucreze cu o reprezentare unitara.

## Fisiere generate

Fisierele generate local sunt scrise in:

```text
backend/generated/
```

Exemple:

- raport PDF generat
- pachete de dovezi vizuale pentru testele E2E
- dataseturi ML exportate
- sabloane pentru etichetare
- artefacte temporare ale analizei

Directorul `backend/generated/` este ignorat de git. Aceste fisiere sunt destinate inspectiei locale, dezvoltarii, capturilor pentru documentatie sau experimentelor de reantrenare.

## Note despre AI si dataset

Componenta ML are rol de opinie secundara consultativa. Aceasta nu aproba si nu respinge singura o calibrare si nu inlocuieste motorul determinist de recomandari bazate pe reguli.

Artefactele modelului folosite la rulare sunt stocate in:

```text
backend/ml/artifacts/calibration_labels/
```

Fisiere asteptate:

```text
calibration_label_model.joblib
calibration_risk_model.joblib
training_metrics.json
```

Aceste artefacte fac parte din aplicatia rulabila, astfel incat o clona noua a proiectului poate folosi analiza asistata ML dupa instalarea dependentelor.

Dataseturile de antrenare si dataseturile augmentate sunt fisiere generate local. Fisiere ca acestea nu trebuie incluse in git decat daca exista un motiv explicit pentru publicarea unui esantion sanitizat:

```text
backend/generated/training_dataset.csv
backend/generated/training_dataset_augmented.csv
backend/generated/training_dataset_augmented_large.csv
backend/generated/labeled_datasets/
```

Documentatie utila pentru ML si dataseturi:

- `backend/ml/README.md`
- `backend/scripts/README.md`

## Verificari de calitate

Pentru rularea intregului set local de verificari:

```powershell
.\scripts\dev.ps1 check
```

Aceasta comanda ruleaza:

- suita de teste backend cu pytest
- analiza statica Flutter
- testele Flutter

Comenzi individuale:

```powershell
.\scripts\dev.ps1 backend-test
.\scripts\dev.ps1 analyze
.\scripts\dev.ps1 test
```

Echivalent cu Makefile:

```powershell
make check
make backend-test
make analyze
make test
```

Testele backend acopera decodarea fisierelor, parsarea definitiilor de harti, extragerea si compararea hartilor, logica de recomandare, comportamentul ML fallback, validarea API, generarea PDF, regresia vizuala, suprafetele 3D si fluxurile E2E de analiza.

## Formatare

Codul Flutter poate fi formatat cu:

```powershell
.\scripts\dev.ps1 format
```

Echivalent cu Makefile:

```powershell
make format
```

## Servicii backend importante

```text
backend/app/services/file_formats.py             Decodarea si normalizarea fisierelor ECU
backend/app/services/map_definitions.py          Parsarea definitiilor de harti
backend/app/services/map_utils.py                Functii comune pentru harti
backend/app/services/calibration_maps.py         Extragerea si compararea hartilor
backend/app/services/calibration_recommender.py  Recomandari bazate pe reguli
backend/app/services/calibration_ml.py           Integrarea dovezilor ML la rulare
backend/app/services/calibration_analyzer.py     Orchestrarea analizei principale
backend/app/services/report_generator.py         Generarea raportului PDF
backend/app/services/visualization.py            Elemente vizuale pentru harti si raport
```

## Probleme frecvente

Daca frontend-ul nu se poate conecta la API, verifica daca backend-ul ruleaza la `http://127.0.0.1:8000`.

Daca comenzile Flutter nu sunt gasite, instaleaza Flutter si plaseaza-l in `C:\flutter` sau adauga-l in `PATH`.

Daca comenzile Docker esueaza, instaleaza/porneste Docker Desktop sau ruleaza backend-ul local cu:

```powershell
.\scripts\dev.ps1 backend
```

Daca artefactele ML lipsesc, analiza determinista poate rula in continuare, dar dovezile ML nu vor fi disponibile pana cand artefactele sunt restaurate sau modelele sunt reantrenate.

Daca dataseturile, rapoartele sau fisierele E2E generate apar in working tree, pastreaza-le sub `backend/generated/`, astfel incat sa ramana ignorate de git.

## Limite de siguranta

Aplicatia ofera suport structurat pentru analiza si raportarea calibrarilor. Toate recomandarile trebuie revizuite de o persoana calificata si validate prin loguri reale, comportament AFR/lambda, EGT, knock/noise, control boost, temperaturi, limite ale transmisiei si configuratia mecanica specifica.

Proiectul nu scrie fisiere ECU modificate, nu flasheaza ECU-uri si nu garanteaza ca o modificare sugerata este sigura pentru un anumit vehicul.
