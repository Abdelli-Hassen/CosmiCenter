#!/usr/bin/env bash
# CosmiCenter - démarrage rapide (Linux / macOS).
# Fonctionne depuis n'importe quel dossier et après un déplacement du projet (autre machine, disque externe...).
set -e
cd "$(dirname "$0")"
ROOT="$PWD"

echo ""
echo "=========================================="
echo "   COSMICENTER - DÉMARRAGE RAPIDE"
echo "=========================================="
echo ""

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERREUR] Python 3 n'est pas installé : sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

# Un venv mémorise son emplacement : on le recrée s'il manque ou si le dossier a été déplacé
echo "[1/4] Environnement Python..."
if [ ! -x venv/bin/python ] || ! venv/bin/python -c "import sys" >/dev/null 2>&1 || ! grep -Fq "$ROOT/venv" venv/bin/activate 2>/dev/null; then
    echo "      (création de l'environnement : première utilisation ou dossier déplacé)"
    rm -rf venv
    python3 -m venv venv
fi

echo "[2/4] Dépendances..."
venv/bin/python -m pip install -r requirements.txt --quiet

if [ ! -f ".env" ]; then
    echo "[3/4] Création du fichier .env..."
    cp .env.example .env
    echo "ATTENTION : renseignez DATABASE_URL et SECRET_KEY dans .env, puis relancez ce script."
    exit 0
else
    echo "[3/4] Fichier .env présent"
fi

mkdir -p instance logs static/uploads

echo "[4/4] Vérification de la base de données (DATABASE_URL du fichier .env)..."
if ! venv/bin/python scripts/check_db.py; then
    echo "[ERREUR] Connexion à la base impossible : vérifiez DATABASE_URL dans .env"
    exit 1
fi

echo ""
echo "Si la base est vide : venv/bin/python -m flask --app app init-db"
echo "(le mot de passe administrateur initial est affiché une seule fois, ou défini via ADMIN_PASSWORD)"
echo "L'application démarre sur http://127.0.0.1:8080 (FLASK_HOST / FLASK_PORT dans .env). Ctrl+C pour arrêter."
echo "Pour un serveur en ligne : voir DEPLOYMENT_GUIDE.md"
echo ""

exec venv/bin/python app.py