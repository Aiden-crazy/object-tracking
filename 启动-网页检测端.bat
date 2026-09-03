@echo off
rem ============================================================
rem  Start Web Detect Page (Track) - double click to launch
rem  Author: [Name]  Student ID: [ID]  2026-07
rem  Starts MySQL check + vision service(9000) + web backend(8080)
rem  if not running, then opens browser at /track.html
rem ============================================================
setlocal
set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if /i "%~1"=="test" (
  "%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start_all.ps1" -Open "http://localhost:8080/track.html" -Quiet
) else (
  "%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start_all.ps1" -Open "http://localhost:8080/track.html"
)
endlocal