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
echo  Debogueur + auto-reload actifs UNIQUEMENT si FLASK_HOST=127.0.0.1 (fichier .env).
echo  Si le serveur est expose au reseau (0.0.0.0), le debogueur est desactive automatiquement.
echo.

call scripts\ensure_venv.bat
if errorlevel 1 (
    pause
    exit /b 1
)

"venv\Scripts\python.exe" app.py

pause