@echo off
title CosmiCenter - PRODUCTION / PARTAGE RESEAU
cd /d "%~dp0"

REM =========================================
REM CosmiCenter - serveur Waitress (sans debogueur)
REM Pour partager sur le reseau local : FLASK_HOST=0.0.0.0 dans .env
REM =========================================

echo.
echo ========================================
echo   CosmiCenter - PREPARATION DU SERVEUR
echo ========================================
echo.

REM Cree ou recree l'environnement Python si besoin (premiere utilisation, dossier deplace...)
call scripts\ensure_venv.bat
if errorlevel 1 (
    pause
    exit /b 1
)

set FLASK_ENV=production
set PYTHONIOENCODING=utf-8

REM Lancer l'application via Waitress (hote et port : FLASK_HOST / FLASK_PORT du fichier .env)
:run
echo [INFO] Demarrage du serveur WSGI...
"venv\Scripts\python.exe" serve.py
REM Code 3 = touche R pressee dans la console : on relance le serveur
if errorlevel 3 if not errorlevel 4 goto run

pause