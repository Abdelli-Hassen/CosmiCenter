@echo off
title Cosmicenter - PRODUCTION

REM =========================================
REM Cosmicenter Production Launcher
REM =========================================

echo.
echo ========================================
echo   Cosmicenter - PREPARATION DU SERVEUR
echo ========================================
echo.

REM Verifier si le dossier venv existe
if not exist venv\Scripts\activate.bat (
    echo [ERREUR] L environnement virtuel n est pas installe.
    echo Veuillez executer setup.bat d abord.
    pause
    exit /b 1
)

REM Charger l'environnement virtuel
echo [INFO] Activation de l environnement virtuel...
call venv\Scripts\activate.bat

REM Variables d'environnement pour la production
set FLASK_ENV=production
set FLASK_PORT=8080
set FLASK_HOST=127.0.0.1
set PYTHONIOENCODING=utf-8

REM Lancer l'application via Waitress
echo [INFO] Demarrage du serveur WSGI...
python serve.py

pause
