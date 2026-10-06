@echo off
chcp 65001 >nul
title Cosmicenter

set DATABASE_URL=postgresql+psycopg://Cosmicenter:testtest@localhost:5432/Cosmicenter
set FLASK_PORT=8080
set PYTHONIOENCODING=utf-8
set FLASK_ENV=development
set FLASK_DEBUG=1

echo.
echo  =========================================
echo   Cosmicenter - Mode DEVELOPPEMENT (Debug)
echo  =========================================
echo  Serveur de dev (auto-reload) sur : http://127.0.0.1:8080
echo.

call venv\Scripts\activate.bat
python app.py

pause
