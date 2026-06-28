SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command

.PHONY: help setup install-backend install-frontend backend backend-window frontend-windows frontend-chrome frontend-web app-windows app-web analyze backend-test test check format

help:
	@Write-Host "Available commands:"
	@Write-Host "  make setup            Install backend and frontend dependencies"
	@Write-Host "  make install-backend  Create .venv and install backend requirements"
	@Write-Host "  make install-frontend Run flutter pub get"
	@Write-Host "  make backend          Start FastAPI backend on http://127.0.0.1:8000"
	@Write-Host "  make backend-window   Start backend in a new PowerShell window"
	@Write-Host "  make frontend-windows Start Flutter app on Windows desktop"
	@Write-Host "  make frontend-chrome  Start Flutter app in Chrome"
	@Write-Host "  make frontend-web     Start Flutter web server on http://127.0.0.1:5403"
	@Write-Host "  make app-windows      Start backend window, then Flutter Windows app"
	@Write-Host "  make app-web          Start backend window, then Flutter web server"
	@Write-Host "  make analyze          Run Flutter analyzer"
	@Write-Host "  make backend-test     Run backend pytest suite"
	@Write-Host "  make test             Run Flutter tests"
	@Write-Host "  make check            Run backend tests, Flutter analyzer and Flutter tests"
	@Write-Host "  make format           Format Flutter Dart files"

setup:
	.\scripts\dev.ps1 setup

install-backend:
	.\scripts\dev.ps1 install-backend

install-frontend:
	.\scripts\dev.ps1 install-frontend

backend:
	.\scripts\dev.ps1 backend

backend-window:
	.\scripts\dev.ps1 backend-window

frontend-windows:
	.\scripts\dev.ps1 frontend-windows

frontend-chrome:
	.\scripts\dev.ps1 frontend-chrome

frontend-web:
	.\scripts\dev.ps1 frontend-web

app-windows:
	.\scripts\dev.ps1 app-windows

app-web:
	.\scripts\dev.ps1 app-web

analyze:
	.\scripts\dev.ps1 analyze

backend-test:
	.\scripts\dev.ps1 backend-test

test:
	.\scripts\dev.ps1 test

check:
	.\scripts\dev.ps1 check

format:
	.\scripts\dev.ps1 format
