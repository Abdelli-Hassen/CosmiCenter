# CosmittoHUB — Plateforme de gestion opérationnelle

![CosmittoHUB Logo](static/images/logo-cosmitto.png)

**CosmittoHUB** est le système de gestion de tickets et d'incidents interne de **Cosmitto Coffee**, réseau multi-points de vente (multi-POS) de cafés. Il centralise le suivi des incidents, demandes, maintenances et besoins opérationnels de l'ensemble des points de vente.

---

## Contexte métier

Cosmitto Coffee opère plusieurs points de vente (POS). CosmittoHUB permet à chaque site de remonter des incidents ou demandes vers les équipes centrales (Support IT, Maintenance, Stock, Qualité, RH, Finances), avec suivi, priorisation et résolution traçable.

## Fonctionnalités

- **Tickets** — incidents, demandes, besoins, plaintes, tâches
- **25 catégories d'incidents** pré-configurées pour la restauration (pannes équipements, ruptures stock, hygiène, SI, RH…)
- **Départements** — Support IT, Maintenance, Stock, Qualité, RH, Finances, SI
- **Rôles & permissions** granulaires (Super Admin, Admin, Manager, Agent, Utilisateur)
- **Tableau de bord** avec métriques en temps réel
- **Rapports** — délais de résolution, SLA, performance par département
- **Interface française**, thème clair/sombre

## Installation

```bash
# 1. Environnement virtuel
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate          # Windows

# 2. Dépendances
pip install -r requirements.txt

# 3. Configuration
cp .env.example .env
# Modifier .env : SECRET_KEY, DATABASE_URL

# 4. Base de données
python scripts/init_db.py

# 5. Catégories d'incidents (optionnel)
python scripts/seed_incidents.py

# 6. Lancer
python app.py
```

Accès : http://127.0.0.1:5000  
Compte par défaut : `admin@example.com` / `testtest`

> ⚠️ Changer le mot de passe admin à la première connexion.

## Base de données

SQLite par défaut (développement). PostgreSQL recommandé en production :

```env
DATABASE_URL=postgresql://user:testtest@localhost:5432/cosmitto_hub
```

## Structure

```
CosmittoHUB/
├── app.py              # Point d'entrée Flask
├── config.py           # Configuration
├── models.py           # Modèles SQLAlchemy
├── routes/             # Blueprints (auth, tickets, admin, …)
├── templates/          # Templates Jinja2
├── static/             # CSS, JS, images
└── scripts/            # init_db.py, seed_incidents.py
```

## Licence

Pour moi — © 2026
