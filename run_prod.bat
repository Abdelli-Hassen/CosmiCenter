@echo off
title CosmiCenter - PRODUCTION / PARTAGE RESEAU

REM =========================================
REM CosmiCenter - serveur Waitress (sans debogueur)
REM Pour partager sur le reseau local : FLASK_HOST=0.0.0.0 dans .env
REM =========================================

echo.
echo ========================================
echo   CosmiCenter - PREPARATION DU SERVEUR
echo ========================================
echo.

REM Verifier si le dossier venv existe
if not exist venv\Scripts\activate.bat (
    echo [ERREUR] L environnement virtuel n est pas installe.
    echo Veuillez executer start.bat d abord.
    pause
    exit /b 1
)

REM Charger l'environnement virtuel
echo [INFO] Activation de l environnement virtuel...
call venv\Scripts\activate.bat

set FLASK_ENV=production
set PYTHONIOENCODING=utf-8

REM Lancer l'application via Waitress (hote et port : FLASK_HOST / FLASK_PORT du fichier .env)
echo [INFO] Demarrage du serveur WSGI...
python serve.py

pause
