@echo off
rem ============================================================
rem  Start-Detect-Page.bat  (same as: ???-????????.bat)
rem  Double-click: auto start services and open the Web Detect
rem  page http://localhost:8080/track.html in your browser.
rem ============================================================
setlocal
set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if /i "%~1"=="test" (
  "%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start_all.ps1" -Open "http://localhost:8080/track.html" -Quiet
) else (
  "%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start_all.ps1" -Open "http://localhost:8080/track.html"
)
endlocal
