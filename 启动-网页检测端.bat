@echo off
rem ============================================================
rem  Start Web DETECT page (single object tracking)
rem  Chinese-name launcher; English alias = Start-Detect-Page.bat
rem  Author: [Your Name]  Student ID: [Your ID]  2026-07
rem  Double-click: auto start vision service(9000) + web backend(8080)
rem  if not running, then open http://localhost:8080/track.html
rem ============================================================
setlocal
set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if /i "%~1"=="test" (
  "%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start_all.ps1" -Open "http://localhost:8080/track.html" -Quiet
) else (
  "%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start_all.ps1" -Open "http://localhost:8080/track.html"
)
endlocal
