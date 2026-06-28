param(
    [Parameter(Position = 0)]
    [ValidateSet(
        "setup",
        "install-backend",
        "install-frontend",
        "backend",
        "backend-window",
        "frontend-windows",
        "frontend-chrome",
        "frontend-web",
        "app-windows",
        "app-web",
        "analyze",
        "backend-test",
        "test",
        "check",
        "format",
        "help"
    )]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$VenvDir = Join-Path $Root ".venv"
$VenvActivate = Join-Path $Root ".venv\Scripts\Activate.ps1"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$FlutterRoot = "C:\flutter"
$DartExe = Join-Path $FlutterRoot "bin\cache\dart-sdk\bin\dart.exe"
$FlutterBat = Join-Path $FlutterRoot "bin\flutter.bat"
$FlutterTool = Join-Path $FlutterRoot "packages\flutter_tools\bin\flutter_tools.dart"

function Show-Help {
    Write-Host ""
    Write-Host "ECU AI App dev commands"
    Write-Host ""
    Write-Host "  .\scripts\dev.ps1 setup             Install backend and frontend dependencies"
    Write-Host "  .\scripts\dev.ps1 install-backend   Create .venv and install backend requirements"
    Write-Host "  .\scripts\dev.ps1 install-frontend  Run flutter pub get"
    Write-Host "  .\scripts\dev.ps1 backend           Start FastAPI backend"
    Write-Host "  .\scripts\dev.ps1 backend-window    Start backend in a new PowerShell window"
    Write-Host "  .\scripts\dev.ps1 frontend-windows  Start Flutter Windows app"
    Write-Host "  .\scripts\dev.ps1 frontend-chrome   Start Flutter in Chrome"
    Write-Host "  .\scripts\dev.ps1 frontend-web      Start Flutter web server"
    Write-Host "  .\scripts\dev.ps1 app-windows       Start backend window, then Flutter Windows app"
    Write-Host "  .\scripts\dev.ps1 app-web           Start backend window, then Flutter web server"
    Write-Host "  .\scripts\dev.ps1 analyze           Run Flutter analyzer"
    Write-Host "  .\scripts\dev.ps1 backend-test      Run backend pytest suite"
    Write-Host "  .\scripts\dev.ps1 test              Run Flutter tests"
    Write-Host "  .\scripts\dev.ps1 check             Run backend tests, Flutter analyzer and Flutter tests"
    Write-Host "  .\scripts\dev.ps1 format            Format Dart files"
    Write-Host ""
}

function Invoke-Python {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)

    if (Test-Path $VenvPython) {
        & $VenvPython @Args
    }
    elseif (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 @Args
    }
    else {
        & python @Args
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE."
    }
}

function Enter-Backend {
    Set-Location $BackendDir

    if (Test-Path $VenvActivate) {
        . $VenvActivate
    }
    else {
        Write-Warning "Virtual environment not found at $VenvActivate. Using current Python environment."
    }
}

function Enter-Frontend {
    Set-Location $FrontendDir
}

function Install-Backend {
    Set-Location $Root

    if (-not (Test-Path $VenvPython)) {
        Write-Host "Creating Python virtual environment in .venv..."
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3 -m venv $VenvDir
        }
        else {
            & python -m venv $VenvDir
        }
    }

    Write-Host "Installing backend dependencies..."
    & $VenvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "pip upgrade failed with exit code $LASTEXITCODE."
    }
    & $VenvPython -m pip install -r (Join-Path $BackendDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Backend dependency install failed with exit code $LASTEXITCODE."
    }
}

function Install-Frontend {
    Enter-Frontend
    Invoke-Flutter pub get
}

function Invoke-Dart {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)

    if (Test-Path $DartExe) {
        & $DartExe @Args
    }
    else {
        & dart @Args
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Dart command failed with exit code $LASTEXITCODE."
    }
}

function Invoke-Flutter {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)

    if (Test-Path $FlutterBat) {
        & $FlutterBat @Args
    }
    elseif ((Test-Path $DartExe) -and (Test-Path $FlutterTool)) {
        & $DartExe $FlutterTool @Args
    }
    else {
        & flutter @Args
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Flutter command failed with exit code $LASTEXITCODE."
    }
}

function Start-BackendWindow {
    $command = "Set-Location '$Root'; .\scripts\dev.ps1 backend"
    Start-Process powershell.exe -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-NoExit",
        "-Command",
        $command
    )
    Start-Sleep -Seconds 2
}

switch ($Command) {
    "setup" {
        Install-Backend
        Install-Frontend
    }
    "install-backend" {
        Install-Backend
    }
    "install-frontend" {
        Install-Frontend
    }
    "backend" {
        Enter-Backend
        Invoke-Python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    }
    "backend-window" {
        Start-BackendWindow
    }
    "frontend-windows" {
        Enter-Frontend
        Invoke-Flutter run -d windows
    }
    "frontend-chrome" {
        Enter-Frontend
        Invoke-Flutter run -d chrome
    }
    "frontend-web" {
        Enter-Frontend
        Invoke-Flutter run -d web-server --web-hostname 127.0.0.1 --web-port 5403
    }
    "app-windows" {
        Start-BackendWindow
        Enter-Frontend
        Invoke-Flutter run -d windows
    }
    "app-web" {
        Start-BackendWindow
        Enter-Frontend
        Invoke-Flutter run -d web-server --web-hostname 127.0.0.1 --web-port 5403
    }
    "analyze" {
        Enter-Frontend
        Invoke-Dart analyze
    }
    "backend-test" {
        Enter-Backend
        Invoke-Python -m pytest tests
    }
    "test" {
        Enter-Frontend
        Invoke-Flutter test
    }
    "check" {
        Enter-Backend
        Invoke-Python -m pytest tests
        Enter-Frontend
        Invoke-Dart analyze
        Invoke-Flutter test
    }
    "format" {
        Enter-Frontend
        Invoke-Dart format lib test
    }
    default {
        Show-Help
    }
}
