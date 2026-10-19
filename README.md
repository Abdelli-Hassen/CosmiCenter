# CosmiCenter — Plateforme de gestion opérationnelle

![CosmiCenter Logo](static/images/logo-cosmitto.png)

**CosmiCenter** est le système de gestion de tickets et d'incidents interne de **Cosmitto Coffee**, réseau multi-points de vente (multi-POS) de cafés. Il centralise le suivi des incidents, demandes, maintenances et besoins opérationnels de l'ensemble des points de vente.

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

Cosmitto Coffee opère plusieurs points de vente (POS). CosmiCenter permet à chaque site de remonter des incidents ou demandes vers les équipes centrales (Support IT, Maintenance, Stock, Qualité, RH, Finances, SI), avec suivi, priorisation et résolution traçable.

---

## Fonctionnalités

### Tickets
- 5 types : incident, demande, besoin, plainte, tâche
- Numérotation séquentielle atomique (ex. `#42`, séquence PostgreSQL)
- Routage flexible : Département, Agent spécifique, ou **Collaboration multi-départements & multi-agents**
- Catégories regroupées par département avec attribution automatique
- Priorité calculée automatiquement via matrice Impact × Urgence
- Sous-tâches, pièces jointes avec prévisualisation miniatures et visualiseur Lightbox in-tab
- Historique d'audit complet de chaque modification
- Évaluation de satisfaction (1–5 étoiles)
- Suivi SLA : temps de première réponse et de résolution

### Utilisateurs
- Profils complets : nom, poste, département / point de vente, entreprise, photo
- Vue liste avec avatars dynamiques colorés et surbrillance au survol
- Tri interactif par clic de colonne (nom, e-mail, rôle, département)
- Filtres : recherche instantanée, rôle, département, point de vente, statut
- Activation / désactivation / réactivation
- Statistiques par utilisateur (tickets créés, assignés, résolus)

### Points de Vente (PDV)
- Gestion des cafés du réseau Cosmitto avec KPI opérationnels et effectifs
- Distinction visuelle ambrée avec icône dédiée pour les équipes terrain en PDV

### Entreprises
- Gestion multi-sociétés (filiales) avec code couleur d'entité et badges visuels

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
# Modifier .env : SECRET_KEY (obligatoire, aléatoire), DATABASE_URL (PostgreSQL)

# 4. Base de données (première installation)
python -m flask --app app init-db
#   -> crée le compte admin@example.com ; son mot de passe initial est affiché UNE seule fois
#      (ou défini par la variable ADMIN_PASSWORD)

# 5. Lancer
python app.py            # développement
python serve.py          # serveur Waitress (partage réseau / production)
```

Accès : `http://127.0.0.1:8080` (port défini par `FLASK_PORT`).

> Le script `seed_db.py` **vide toutes les tables** avant d'insérer des données de démonstration : il demande une
> confirmation explicite (taper `EFFACER`) et utilise le mot de passe `SEED_PASSWORD` (ou une valeur aléatoire affichée en fin d'exécution).

### Partager la plateforme sur le réseau (tests par d'autres personnes)

1. Dans `.env` : `FLASK_HOST=0.0.0.0` (et éventuellement `PUBLIC_BASE_URL=http://<ip-du-poste>:8080` pour les liens des emails).
2. Lancer `run_prod.bat` (Waitress) ou `python app.py`.
3. Les autres utilisateurs ouvrent `http://<ip-du-poste>:8080`.

Dès que `FLASK_HOST` n'est pas une adresse locale, le **débogueur Werkzeug est désactivé automatiquement** (il permet d'exécuter du code à distance).
Autoriser le port 8080 dans le pare-feu Windows si nécessaire. Cookies `Secure` : uniquement derrière HTTPS (`SESSION_COOKIE_SECURE=true`).

---

## Sécurité

- **CSRF** : jeton de session vérifié sur toutes les requêtes POST/PUT/DELETE (formulaires et `fetch`), injecté automatiquement par `static/js/csrf.js`.
- **Verrouillage de compte** : 7 échecs de connexion (`MAX_LOGIN_ATTEMPTS`) verrouillent le compte 30 minutes (`LOCKOUT_DURATION_MINUTES`) ; un administrateur peut le lever immédiatement (Réactiver).
- **Sessions** : changer son mot de passe ou « Déconnecter les autres sessions » invalide toutes les autres sessions ; désactiver un compte coupe ses sessions.
- **Fichiers uploadés** : réservés aux utilisateurs connectés, 10 Mo par fichier, types autorisés uniquement, servis avec `nosniff` et une CSP « sandbox ».
- **Mots de passe AnyDesk / TeamViewer** : chiffrés en base (Fernet, clé `FIELD_ENCRYPTION_KEY` ou dérivée de `SECRET_KEY` — ne pas changer `SECRET_KEY` sans migrer ces champs) et visibles uniquement par l'intéressé et les détenteurs de `admin_acces.voir`.
- **Journaux** : rotation automatique (5 Mo x 5).

---

## Base de données

PostgreSQL obligatoire :

```env
DATABASE_URL=postgresql://utilisateur:testtest@localhost:5432/nom_base
```

Les colonnes ajoutées après la première installation (verrouillage temporaire, version de session, séquence des numéros de ticket)
sont créées automatiquement au démarrage (`utils/schema.py`, instructions idempotentes).

---

## Structure

```
CosmiCenter/
├── app.py              # Point d'entrée Flask
├── config.py           # Configuration par environnement
├── models.py           # Modèles SQLAlchemy
├── utils/              # Sécurité (CSRF, en-têtes), uploads, chiffrement, permissions, schéma
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
