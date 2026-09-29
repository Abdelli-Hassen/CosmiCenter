@echo off
chcp 65001 >nul
title CosmittoHUB

set DATABASE_URL=postgresql+psycopg://CosHub:testtest@localhost:5432/CosHub
set FLASK_PORT=8080
set PYTHONIOENCODING=utf-8

echo.
echo  CosmittoHUB - Lancement...
echo  http://127.0.0.1:8080
echo.

call venv\Scripts\activate.bat
python app.py

pause
