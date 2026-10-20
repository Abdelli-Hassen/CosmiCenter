@echo off
cd /d "%~dp0"
echo ====================================================
echo  Activation de l'environnement virtuel (CosmiCenter)
echo ====================================================
echo.
call scripts\ensure_venv.bat
if errorlevel 1 (
    pause
    exit /b 1
)
echo Environnement active ! Vous pouvez maintenant taper vos commandes (ex: python seed_db.py)
echo.
cmd /k "venv\Scripts\activate.bat"