# CosmittoHUB — Plateforme de gestion opérationnelle

![CosmittoHUB Logo](static/images/logo-cosmitto.png)

**CosmittoHUB** est le système de gestion de tickets et d'incidents interne de **Cosmitto Coffee**, réseau multi-points de vente (multi-POS) de cafés. Il centralise le suivi des incidents, demandes, maintenances et besoins opérationnels de l'ensemble des points de vente.

---

## Aperçu

| Connexion | Tableau de bord |
|-----------|----------------|
| ![Connexion](static/images/guide/01-connexion.png) | ![Tableau de bord](static/images/guide/02-tableau-bord.png) |

| Nouveau ticket | Liste des tickets |
|---------------|-----------------|
| ![Nouveau ticket](static/images/guide/04-nouveau-ticket.png) | ![Liste tickets](static/images/guide/03-liste-tickets.png) |

| Administration | Rapports |
|---------------|---------|
| ![Admin](static/images/guide/05-admin-tableau-bord.png) | ![Rapports](static/images/guide/11-rapports.png) |

---

## Contexte métier

Cosmitto Coffee opère plusieurs points de vente (POS). CosmittoHUB permet à chaque site de remonter des incidents ou demandes vers les équipes centrales (Support IT, Maintenance, Stock, Qualité, RH, Finances, SI), avec suivi, priorisation et résolution traçable.

---

## Fonctionnalités

### Tickets
- 5 types : incident, demande, besoin, plainte, tâche
- Numérotation automatique (ex. `TK-2026-0042`)
- Catégories regroupées par département avec attribution automatique
- Priorité calculée automatiquement via matrice Impact × Urgence
- Sous-tâches, pièces jointes, commentaires (publics ou internes)
- Historique d'audit complet de chaque modification
- Évaluation de satisfaction (1–5 étoiles)
- Suivi SLA : temps de première réponse et de résolution

### Utilisateurs
- Profils complets : nom, poste, matricule, département, photo
- Vue liste avec avatars colorés par département
- Filtres : recherche, rôle, département, statut
- Activation / désactivation / réactivation
- Statistiques par utilisateur (tickets créés, assignés, résolus)

### Départements
- Création avec code unique, couleur, icône, responsable
- SLA configurables par département (réponse : défaut 4h, résolution : défaut 48h)
- Horaires de travail personnalisés
- Statistiques : membres, tickets par statut, catégories

### Rôles et permissions
| Rôle | Niveau | Périmètre |
|------|--------|-----------|
| Super Administrateur | 100 | Accès total |
| Administrateur | 90 | Utilisateurs, départements, tickets, rapports |
| Manager | 70 | Son département, assignation, rapports |
| Agent | 50 | Tickets assignés, commentaires |
| Utilisateur | 10 | Ses propres tickets |

20+ permissions granulaires (tickets, admin, rapports, base de connaissances) sont désormais appliquées dynamiquement sur toutes les interfaces et les routes au lieu de vérifications statiques, garantissant un contrôle précis des actions (Création, Modification, Suppression, Désactivation).

### Rapports
- Tableau de bord analytique : métriques SLA, satisfaction, évolution quotidienne
- Performance par agent : tickets résolus, temps moyen, taux de résolution
- Satisfaction client : distribution des notes, commentaires par département
- Export CSV avec filtres de dates

### Administration
- Gestion des utilisateurs avec filtres avancés et stat chips (total / actifs / inactifs)
- Gestion des rôles et permissions par cases à cocher hiérarchisées (interface en accordéon avec logique de désactivation en cascade)
- Création, modification, désactivation et suppression des rôles personnalisés
- Gestion des catégories de tickets (type, priorité par défaut, délai SLA, couleur)
- Logs système et paramètres (en cours)

### Paramètres du compte
- Modification du profil : nom, téléphone, préférences (thème clair/sombre/auto, langue)
- Changement de mot de passe sécurisé
- Centre de notifications (marquer lu, tout marquer lu)

### API REST
8 endpoints JSON pour intégrations : stats globales, stats par jour/département/priorité, changement de statut, assignation, recherche d'utilisateurs, health check.

---

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

# 5. Données de démonstration (optionnel)
python scripts/seed_incidents.py

# 6. Lancer
python app.py
```

Accès : `http://127.0.0.1:5000`  

### Comptes de test par défaut
- **Super Administrateur** : `admin@example.com` / `testtest`
- **Chef département** : `stock8@example.com` / `testtest`
- **Agent Support** : `ressourceshumaines1@example.com` / `testtest`
- **Utilisateur Standard** : `utilisateurstandard1@example.com` / `testtest`

> ⚠️ Changer les mots de passe à la première connexion en production.

---

## Base de données

SQLite par défaut (développement). PostgreSQL recommandé en production :

```env
DATABASE_URL=postgresql://user:testtest@localhost:5432/cosmitto_hub
```

---

## Structure

```
CosmittoHUB/
├── app.py              # Point d'entrée Flask
├── config.py           # Configuration par environnement
├── models.py           # 14 modèles SQLAlchemy
├── routes/             # 9 blueprints — 58 routes HTTP
│   ├── auth.py
│   ├── tickets.py
│   ├── admin.py
│   ├── utilisateurs.py
│   ├── departements.py
│   ├── rapports.py
│   ├── parametres.py
│   ├── api.py
│   └── base_connaissance.py
├── templates/          # 30 templates Jinja2
├── static/             # CSS, JS, images, guide
└── scripts/            # init_db.py, seed_incidents.py
```

---

## Documentation

| Document | Contenu |
|----------|---------|
| `FONCTIONNALITES.md` | Référence complète de toutes les fonctionnalités et routes |
| `GUIDE_UTILISATEUR.md` | Guide utilisateur illustré en français (14 captures d'écran) |

---

## Licence

Pour moi — © 2026
