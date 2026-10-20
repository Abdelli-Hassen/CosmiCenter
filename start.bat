@echo off
chcp 65001 >nul
REM Toujours travailler depuis le dossier du projet, quel que soit l'endroit d'ou le script est lance
cd /d "%~dp0"
echo.
echo ========================================================
echo      COSMICENTER - DEMARRAGE RAPIDE
echo ========================================================
echo.

echo [1/4] Environnement Python...
call scripts\ensure_venv.bat
if errorlevel 1 (
    pause
    exit /b 1
)

echo [2/4] Dependances...
"venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet

REM Creer le fichier .env s'il n'existe pas
if not exist ".env" (
    echo [3/4] Creation du fichier .env...
    copy .env.example .env >nul
    echo ATTENTION: Modifiez le fichier .env ^(DATABASE_URL, SECRET_KEY...^) avant de continuer
    pause
) else (
    echo [3/4] Fichier .env present
)

REM Creer les dossiers necessaires
if not exist "instance" mkdir instance
if not exist "logs" mkdir logs
if not exist "static\uploads" mkdir static\uploads

echo [4/4] Verification de la connexion a la base de donnees (DATABASE_URL du fichier .env)...
"venv\Scripts\python.exe" scripts\check_db.py
if errorlevel 1 (
    echo.
    echo [ERREUR] Connexion a la base impossible : verifiez DATABASE_URL dans .env
    pause
    exit /b 1
)

echo.
echo Si la base est vide, initialisez-la avec :  venv\Scripts\python.exe -m flask --app app init-db
echo (le mot de passe administrateur initial est affiche une seule fois, ou defini via ADMIN_PASSWORD)
echo.
echo L'application demarre sur http://127.0.0.1:8080  (voir FLASK_HOST / FLASK_PORT dans .env)
echo Pour un partage sur le reseau, utilisez run_prod.bat (serveur Waitress, sans debogueur).
echo Appuyez sur Ctrl+C pour arreter l'application
echo.

"venv\Scripts\python.exe" app.py
pause