@echo off
rem MIA comes back by itself after Windows restarts: double-click this file.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pc_stay_up.ps1" %*
echo.
pause
