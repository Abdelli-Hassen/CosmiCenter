@echo off
chcp 65001 >nul
echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║     COSMITTODESK 2.0 - DÉMARRAGE RAPIDE                ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM Vérifier si Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installé ou n'est pas dans le PATH
    echo Téléchargez Python depuis https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] Vérification de Python...
python --version

REM Créer l'environnement virtuel s'il n'existe pas
if not exist "venv" (
    echo [2/5] Création de l'environnement virtuel...
    python -m venv venv
) else (
    echo [2/5] Environnement virtuel déjà existant
)

REM Activer l'environnement virtuel
echo [3/5] Activation de l'environnement virtuel...
call venv\Scripts\activate.bat

REM Installer les dépendances
echo [4/5] Installation des dépendances...
pip install -r requirements.txt --quiet

REM Créer le fichier .env s'il n'existe pas
if not exist ".env" (
    echo [5/5] Création du fichier .env...
    copy .env.example .env
    echo ⚠ ATTENTION: Modifiez le fichier .env avec vos paramètres
)

REM Créer les dossiers nécessaires
if not exist "instance" mkdir instance
if not exist "logs" mkdir logs
if not exist "static\uploads" mkdir static\uploads

echo.
echo ═══════════════════════════════════════════════════════
echo.

REM Vérifier si la base de données PostgreSQL est initialisée
python -c "import psycopg, sys; conn=psycopg.connect('postgresql+psycopg://Cosmicenter:testtest@localhost:5432/Cosmicenter'.replace('postgresql+psycopg','postgresql')); cur=conn.cursor(); cur.execute(\"SELECT COUNT(*) FROM pg_tables WHERE schemaname='public'\"); n=cur.fetchone()[0]; conn.close(); sys.exit(0 if n>0 else 1)" >nul 2>&1
if errorlevel 1 (
    echo La base de données PostgreSQL n'est pas encore initialisée.
    echo.
    set /p init="Voulez-vous initialiser la base de données? (O/N): "
    if /i "%init%"=="O" (
        echo.
        echo Initialisation de la base de données...
        set DATABASE_URL=postgresql+psycopg://Cosmicenter:testtest@localhost:5432/Cosmicenter
        python scripts\init_db.py
        echo.
    )
)

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║           LANCEMENT DE L'APPLICATION                  ║
echo ╚════════════════════════════════════════════════════════╝
echo.
echo L'application va démarrer sur http://127.0.0.1:8080
echo.
echo Connexion par défaut:
echo   Email: admin@example.com
echo   Mot de passe: testtest
echo.
echo Appuyez sur Ctrl+C pour arrêter l'application
echo.
echo ═══════════════════════════════════════════════════════
echo.

REM Lancer l'application
set DATABASE_URL=postgresql+psycopg://Cosmicenter:testtest@localhost:5432/Cosmicenter
python app.py

pause
