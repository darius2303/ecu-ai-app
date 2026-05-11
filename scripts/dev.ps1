param(
    [Parameter(Position = 0)]
    [ValidateSet(
        "backend",
        "frontend-windows",
        "frontend-chrome",
        "frontend-web",
        "analyze",
        "test",
        "format",
        "help"
    )]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$VenvActivate = Join-Path $Root ".venv\Scripts\Activate.ps1"
$FlutterRoot = "C:\flutter"
$DartExe = Join-Path $FlutterRoot "bin\cache\dart-sdk\bin\dart.exe"
$FlutterTool = Join-Path $FlutterRoot "packages\flutter_tools\bin\flutter_tools.dart"

function Show-Help {
    Write-Host ""
    Write-Host "ECU AI App dev commands"
    Write-Host ""
    Write-Host "  .\scripts\dev.ps1 backend           Start FastAPI backend"
    Write-Host "  .\scripts\dev.ps1 frontend-windows  Start Flutter Windows app"
    Write-Host "  .\scripts\dev.ps1 frontend-chrome   Start Flutter in Chrome"
    Write-Host "  .\scripts\dev.ps1 frontend-web      Start Flutter web server"
    Write-Host "  .\scripts\dev.ps1 analyze           Run Flutter analyzer"
    Write-Host "  .\scripts\dev.ps1 test              Run Flutter tests"
    Write-Host "  .\scripts\dev.ps1 format            Format Dart files"
    Write-Host ""
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

function Invoke-Dart {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)

    if (Test-Path $DartExe) {
        & $DartExe @Args
    }
    else {
        & dart @Args
    }
}

function Invoke-Flutter {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)

    if ((Test-Path $DartExe) -and (Test-Path $FlutterTool)) {
        & $DartExe $FlutterTool --no-version-check @Args
    }
    else {
        & flutter --no-version-check @Args
    }
}

switch ($Command) {
    "backend" {
        Enter-Backend
        uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
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
    "analyze" {
        Enter-Frontend
        Invoke-Flutter analyze
    }
    "test" {
        Enter-Frontend
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
