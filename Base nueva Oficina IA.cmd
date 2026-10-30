@echo off
cd /d "%~dp0"
echo Esto aparta la base actual (no la borra) y la proxima apertura empieza de cero.
echo Cierre Oficina IA antes de continuar.
pause
if exist "Oficina IA.exe" if not exist ".venv\Scripts\python.exe" (
  "Oficina IA.exe" --base-nueva
  exit /b
)
".venv\Scripts\python.exe" scripts\base_nueva.py
pause
