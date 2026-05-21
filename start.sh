#!/bin/bash

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║     COSMITTODESK 2.0 - DÉMARRAGE RAPIDE              ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Vérifier si Python est installé
if ! command -v python3 &> /dev/null; then
    echo "[ERREUR] Python 3 n'est pas installé"
    echo "Installez Python 3: sudo apt install python3 python3-pip"
    exit 1
fi

echo "[1/5] Vérification de Python..."
python3 --version

# Créer l'environnement virtuel s'il n'existe pas
if [ ! -d "venv" ]; then
    echo "[2/5] Création de l'environnement virtuel..."
    python3 -m venv venv
else
    echo "[2/5] Environnement virtuel déjà existant"
fi

# Activer l'environnement virtuel
echo "[3/5] Activation de l'environnement virtuel..."
source venv/bin/activate

# Installer les dépendances
echo "[4/5] Installation des dépendances..."
pip install -r requirements.txt --quiet

# Créer le fichier .env s'il n'existe pas
if [ ! -f ".env" ]; then
    echo "[5/5] Création du fichier .env..."
    cp .env.example .env
    echo "⚠ ATTENTION: Modifiez le fichier .env avec vos paramètres"
fi

# Créer les dossiers nécessaires
mkdir -p instance logs static/uploads

echo ""
echo "═══════════════════════════════════════════════════════"
echo ""

# Vérifier si la base de données existe
if [ ! -f "instance/cosmitto.db" ]; then
    echo "La base de données n'existe pas encore."
    echo ""
    read -p "Voulez-vous initialiser la base de données? (o/n): " init
    if [ "$init" = "o" ] || [ "$init" = "O" ]; then
        echo ""
        echo "Initialisation de la base de données..."
        python3 scripts/init_db.py
        echo ""
    fi
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║           LANCEMENT DE L'APPLICATION                  ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "L'application va démarrer sur http://127.0.0.1:5000"
echo ""
echo "Connexion par défaut:"
echo "  Email: admin@example.com"
echo "  Mot de passe: testtest"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter l'application"
echo ""
echo "═══════════════════════════════════════════════════════"
echo ""

# Lancer l'application
python3 app.py
