@echo off
rem MIA installer for Windows: double-click this file.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
echo.
pause
