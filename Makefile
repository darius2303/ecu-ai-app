SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command

.PHONY: help backend frontend-windows frontend-chrome frontend-web analyze test format

help:
	@Write-Host "Available commands:"
	@Write-Host "  make backend          Start FastAPI backend on http://127.0.0.1:8000"
	@Write-Host "  make frontend-windows Start Flutter app on Windows desktop"
	@Write-Host "  make frontend-chrome  Start Flutter app in Chrome"
	@Write-Host "  make frontend-web     Start Flutter web server on http://127.0.0.1:5403"
	@Write-Host "  make analyze          Run Flutter analyzer"
	@Write-Host "  make test             Run Flutter tests"
	@Write-Host "  make format           Format Flutter Dart files"

backend:
	.\scripts\dev.ps1 backend

frontend-windows:
	.\scripts\dev.ps1 frontend-windows

frontend-chrome:
	.\scripts\dev.ps1 frontend-chrome

frontend-web:
	.\scripts\dev.ps1 frontend-web

analyze:
	.\scripts\dev.ps1 analyze

test:
	.\scripts\dev.ps1 test

format:
	.\scripts\dev.ps1 format
