@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Falta preparar Python. Consulte docs\INSTALACION_WINDOWS.md
  pause
  exit /b 1
)
call npm.cmd run desktop
if errorlevel 1 pause
