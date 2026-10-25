@echo off
chcp 65001 >nul
title CosmiCenter
cd /d "%~dp0"

set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
set FLASK_ENV=development
set FLASK_DEBUG=1

echo.
echo  =========================================
echo   CosmiCenter - Mode DEVELOPPEMENT
echo  =========================================
echo  Local uniquement : http://127.0.0.1:8080 (le .env n'est pas pris en compte pour l'hote).
echo  Debogueur + auto-reload actifs. Pour partager sur le reseau : run_prod.bat
echo.

call scripts\ensure_venv.bat
if errorlevel 1 (
    pause
    exit /b 1
)

"venv\Scripts\python.exe" app.py

pause