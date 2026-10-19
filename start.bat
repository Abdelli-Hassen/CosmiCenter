@echo off
chcp 65001 >nul
echo.
echo ========================================================
echo      COSMICENTER - DEMARRAGE RAPIDE
echo ========================================================
echo.

REM Verifier si Python est installe
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH
    echo Telechargez Python depuis https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] Verification de Python...
python --version

REM Creer l'environnement virtuel s'il n'existe pas
if not exist "venv" (
    echo [2/5] Creation de l'environnement virtuel...
    python -m venv venv
) else (
    echo [2/5] Environnement virtuel deja existant
)

REM Activer l'environnement virtuel
echo [3/5] Activation de l'environnement virtuel...
call venv\Scripts\activate.bat

REM Installer les dependances
echo [4/5] Installation des dependances...
pip install -r requirements.txt --quiet

REM Creer le fichier .env s'il n'existe pas
if not exist ".env" (
    echo [5/5] Creation du fichier .env...
    copy .env.example .env
    echo ATTENTION: Modifiez le fichier .env (DATABASE_URL, SECRET_KEY...) avant de continuer
    pause
)

REM Creer les dossiers necessaires
if not exist "instance" mkdir instance
if not exist "logs" mkdir logs
if not exist "static\uploads" mkdir static\uploads

echo.
echo Verification de la connexion a la base de donnees (DATABASE_URL du fichier .env)...
python scripts\check_db.py
if errorlevel 1 (
    echo.
    echo [ERREUR] Connexion a la base impossible : verifiez DATABASE_URL dans .env
    pause
    exit /b 1
)

echo.
echo Si la base est vide, initialisez-la avec :  python -m flask --app app init-db
echo (le mot de passe administrateur initial est affiche une seule fois, ou defini via ADMIN_PASSWORD)
echo.
echo L'application demarre sur http://127.0.0.1:8080  (voir FLASK_HOST / FLASK_PORT dans .env)
echo Pour un partage sur le reseau, utilisez run_prod.bat (serveur Waitress, sans debogueur).
echo Appuyez sur Ctrl+C pour arreter l'application
echo.

python app.py
pause
