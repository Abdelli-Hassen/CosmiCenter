@echo off
REM ============================================================
REM  Prepare l'environnement Python du projet (dossier "venv").
REM  Appele par start.bat, run_dev.bat, run_prod.bat, Activate_venv.bat.
REM
REM  Un venv memorise l'emplacement ou il a ete cree : si le dossier du
REM  projet a ete deplace ou copie (autre PC, disque externe...), il ne
REM  fonctionne plus. Ce script le detecte et le recree automatiquement.
REM ============================================================
setlocal EnableExtensions
cd /d "%~dp0.."
set "ROOT=%CD%"

if not exist "venv\Scripts\python.exe" goto rebuild
"venv\Scripts\python.exe" -c "import sys" >nul 2>&1
if errorlevel 1 goto rebuild
findstr /i /l /c:"VIRTUAL_ENV=%ROOT%\venv" "venv\Scripts\activate.bat" >nul 2>&1
if errorlevel 1 goto rebuild
exit /b 0

:rebuild
echo.
echo [INFO] Preparation de l'environnement Python (premiere utilisation ou dossier deplace)...
set "PY="
python --version >nul 2>&1 && set "PY=python"
if not defined PY py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY goto nopython
if exist "venv" rmdir /s /q "venv"
%PY% -m venv venv
if errorlevel 1 goto fail
"venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo [INFO] Environnement Python pret.
exit /b 0

:nopython
echo.
echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH.
echo Telechargez Python 3.10 ou plus recent : https://www.python.org/downloads/
echo (cochez "Add python.exe to PATH" pendant l'installation)
exit /b 1

:fail
echo.
echo [ERREUR] Impossible de creer l'environnement Python ou d'installer les dependances.
echo Verifiez votre connexion Internet puis relancez.
exit /b 1