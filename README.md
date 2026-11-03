# CosmiCenter — Plateforme de gestion opérationnelle

![CosmiCenter Logo](static/images/logo-cosmitto.png)

**CosmiCenter** est la plateforme interne de tickets et d'incidents de **Cosmitto Coffee**, réseau multi-points de vente (PDV) de cafés. Elle centralise les incidents, demandes, besoins, plaintes et tâches des points de vente vers les équipes centrales (Support IT, Maintenance, Stock, Qualité, RH, Finances, SI), avec priorisation, suivi des délais (SLA) et historique complet.

**Version actuelle : 2.7.2** (voir [CHANGELOG.md](CHANGELOG.md)).

## Sommaire

1. [Technologies](#technologies)
2. [Démarrage rapide](#démarrage-rapide)
3. [Base de données](#base-de-données)
4. [Configuration (`.env`)](#configuration-env)
5. [Fonctionnalités](#fonctionnalités)
6. [Rôles et permissions](#rôles-et-permissions)
7. [Sécurité](#sécurité)
8. [Structure du projet](#structure-du-projet)
9. [Tests](#tests)
10. [Déploiement](#déploiement)
11. [Documentation](#documentation)

---

## Technologies

| Couche | Choix |
|---|---|
| Serveur | Python, **Flask 3**, Flask-Login, Flask-SQLAlchemy (SQLAlchemy 2.1, psycopg 3) |
| Base de données | **PostgreSQL** (obligatoire) — pas d'Alembic : schéma complété au démarrage par `utils/schema.py` |
| Interface | Jinja2 + **JavaScript vanilla** + CSS maison (thème clair/sombre, adapté aux téléphones et tablettes) |
| Production | **Waitress** (`serve.py`), derrière Nginx en déploiement Ubuntu |
| Divers | Chiffrement Fernet (`cryptography`), Pillow (images), openpyxl (exports Excel), SMTP pour les e-mails |

---

## Démarrage rapide

Sous **Windows**, le plus simple est de lancer `start.bat` (ou `run_dev.bat` / `run_prod.bat`) : il crée le `venv` s'il manque, installe les dépendances et démarre l'application. Manuellement :

```bash
# 1. Environnement virtuel
python -m venv venv
source venv/bin/activate        # Linux / Mac
venv\Scripts\activate           # Windows

# 2. Dépendances
pip install -r requirements.txt

# 3. Configuration
cp .env.example .env            # puis renseigner SECRET_KEY et DATABASE_URL

# 4. Base de données (voir la section suivante)
psql -U postgres -f cosmicenter.example.sql

# 5. Lancer
python app.py                   # développement (http://127.0.0.1:8080, débogueur actif)
python serve.py                 # Waitress : partage réseau / production
```

- Compte par défaut (script SQL d'exemple) : `admin@example.com` / `testtest` — **à changer immédiatement**. Sans le script d'exemple, `create-admin` crée ce compte avec `ADMIN_PASSWORD` ou un mot de passe aléatoire affiché une seule fois.
- Dans la console du serveur (Windows) : **R** = redémarrage complet, **Ctrl+C** = arrêt.
- Pour tester sur un téléphone ou un autre poste : `FLASK_HOST=0.0.0.0` dans `.env`, lancer `run_prod.bat`, ouvrir `http://<ip-du-poste>:8080` (autoriser le port 8080 dans le pare-feu). Dès que l'hôte n'est pas local, le **débogueur Werkzeug est coupé automatiquement**.
- **Projet portable** : aucun chemin absolu dans le code ; le dossier peut être copié sur un autre PC ou disque externe (les `.bat` recréent le `venv`). Copier aussi `.env` (non versionné), la base PostgreSQL, `static/uploads/` et `instance/chat_files/`.
- Commandes CLI : `init-db` (tables + permissions + rôles + admin), `create-admin`, `reset-db` (⚠ efface tout, confirmation demandée).
- `seed_db.py` charge des données de démonstration mais **vide toutes les tables** (il faut taper `EFFACER`). Ne jamais le lancer sur une vraie base.

---

## Base de données

PostgreSQL 14 ou plus. Deux façons de créer la base :

### Option A — Script SQL d'exemple (structure, rôles et données fictives)

Le fichier **[`cosmicenter.example.sql`](cosmicenter.example.sql)** joue le même rôle que `.env.example` : il est versionné, ne contient **aucune donnée réelle** (tout est fictif, adresses `@example.com`) et sert de modèle.

| Section | Contenu |
|---|---|
| 0 | Rôle PostgreSQL `cosmicenter` et base `cosmicenter` |
| 1 | Les **26 tables**, clés étrangères, contraintes d'unicité et index |
| 2 | La séquence `ticket_numero_seq` (numéros de ticket atomiques) |
| 3 | Les « policies » de l'application : **62 permissions**, les **6 rôles standard** (Super Administrateur, Directrice Réseau, Responsable Département, Agent, Responsable Point de Vente, Personnel Point de Vente) et leurs **159 droits**, plus les réglages par défaut (catégories et thèmes des PDV) |
| 3b | Des **données d'exemple** fictives, pour voir toutes les pages remplies : 1 entreprise, 7 départements, 4 points de vente (dont 4 équipements), 17 catégories de tickets, **13 utilisateurs** (au moins 1 par rôle), **12 tickets** couvrant tous les statuts (nouveau, en cours, en attente, résolu, fermé, annulé), tous les types et toutes les priorités, avec 6 sous-tâches, 9 commentaires, historique, évaluations de satisfaction et une collaboration multi-agents ; 3 notifications, 3 messages, 3 idées (bug, amélioration, fonctionnalité), 3 tâches du plan d'action, 3 modèles de réponse, 4 catégories et 5 articles de base de connaissances |
| 4 | Les droits PostgreSQL du rôle applicatif |

```bash
# 1. Mot de passe d'exemple : testtest (à changer en production), puis créer la structure
psql -U postgres -f cosmicenter.example.sql

# 2. Se connecter avec le compte par défaut (ci-dessous), puis changer son mot de passe
```

**Compte Super Administrateur par défaut** (créé par le script d'exemple) :

| E-mail | Mot de passe |
|---|---|
| `admin@example.com` | `testtest` |

⚠ **Changer ce mot de passe dès la première connexion** (*Paramètres du compte*), puis supprimer ou remplacer les données d'exemple. Les 12 autres utilisateurs d'exemple sont **inactifs** (aucune connexion possible) : activez-les ou supprimez-les.

Puis dans `.env` : `DATABASE_URL=postgresql+psycopg://cosmicenter:<mot_de_passe>@localhost:5432/cosmicenter`.

> **À savoir**
> - **`cosmicenter.sql` (avec les données)** est un fichier **local, ignoré par git** (`.gitignore`) : copie de la vraie base (utilisateurs, entreprises, départements, points de vente, catégories de tickets, base de connaissances, rôle personnalisé « HR »…) **sans** tickets, commentaires, pièces jointes ni messages. Il contient des e-mails et des hachages de mots de passe : ne jamais le publier. Les seuls fichiers qui portent des secrets sont donc **`.env`** et **`cosmicenter.sql`**, tous deux hors de git.
> - Les **photos et pièces jointes** ne sont pas dans la base : `static/uploads/` (ignoré par git) et `instance/chat_files/` se copient à part.
> - Aucune Row Level Security PostgreSQL : le contrôle d'accès est fait par l'application (tables `permissions`, `roles`, `roles_permissions`, méthode `Utilisateur.has_permission`, `utils/permissions.py`).
> - Les deux fichiers sont générés à partir de `models.py` ; il faut les régénérer après une modification de modèle.
> - Contrôle effectué : les deux fichiers s'exécutent sans erreur dans un schéma jetable (annulé ensuite) et créent les 26 tables. La section 0 (création du rôle et de la base, commandes `psql`) n'a pas été exécutée.
> - Les vraies données de l'organisation (départements, points de vente, catégories, base de connaissances…) ne sont **pas** dans l'exemple : elles restent dans `cosmicenter.sql` (copie locale).

### Option B — Laisser l'application faire

Au démarrage, `db.create_all()` crée les tables manquantes, puis `utils/schema.py` rejoue des instructions **idempotentes** : colonnes ajoutées après coup (`ALTER TABLE … IF NOT EXISTS`), séquence des tickets, élargissement des colonnes chiffrées, et création des permissions manquantes (avec rattrapage des droits des rôles existants). `python -m flask --app app init-db` crée en plus les rôles de base et l'administrateur.

> Règle de développement : toute nouvelle colonne = le modèle **et** une ligne dans `STATEMENTS` de `utils/schema.py` ; toute nouvelle permission = une entrée dans `DEFAULT_PERMISSIONS` du même fichier.

### Les tables

| Domaine | Tables |
|---|---|
| Accès | `utilisateurs`, `roles`, `permissions`, `roles_permissions` |
| Organisation | `departements`, `points_de_vente`, `equipements`, `entreprises` |
| Tickets | `tickets`, `categories_tickets`, `taches` (sous-tâches), `commentaires`, `pieces_jointes`, `historique_tickets`, `ticket_collaborateurs`, `ticket_departements_collab`, `modeles_reponses` |
| Communication | `messages` (messagerie), `notifications`, `suggestions` (boîte à idées) |
| Connaissance | `categories_connaissance`, `articles_connaissance`, `articles_connaissance_vues` |
| Pilotage | `statistiques`, `plan_action_tasks`, `configurations_systeme` (réglages clé/valeur en JSON) |

Points d'attention :
- Les identifiants sont des UUID (texte, 36 caractères) ; les numéros de ticket viennent de la séquence `ticket_numero_seq`.
- Les durées sont stockées en **minutes** et affichées en h/j.
- Les mots de passe AnyDesk / TeamViewer sont **chiffrés** avant d'entrer en base.
- La **base de connaissances** utilise `categories_connaissance`, `articles_connaissance` et `articles_connaissance_vues`. Une ancienne table `base_connaissance` (vide, sans modèle ni code) peut subsister dans pgAdmin : elle est inutile et peut être supprimée.
- Les index des clés étrangères figurent dans le modèle mais manquent dans une base créée avant leur ajout (`create_all` n'ajoute pas d'index sur une table existante) ; le script SQL les crée tous.

---

## Configuration (`.env`)

Copier `.env.example` en `.env` (jamais commité). Variables principales :

| Variable | Rôle |
|---|---|
| `SECRET_KEY` | **Obligatoire**, aléatoire et longue. Ne pas la changer sans migrer les champs chiffrés (sauf si `FIELD_ENCRYPTION_KEY` est définie) |
| `DATABASE_URL` | Connexion PostgreSQL |
| `FLASK_HOST` / `FLASK_PORT` | `127.0.0.1` (local) ou `0.0.0.0` (réseau) ; port 8080 par défaut |
| `BEHIND_PROXY` | `true` derrière Nginx (ProxyFix) ; `FLASK_HOST` reste alors `127.0.0.1` |
| `PUBLIC_BASE_URL` | URL publique utilisée dans les liens des e-mails |
| `SESSION_COOKIE_SECURE` | `true` uniquement derrière HTTPS |
| `MAX_LOGIN_ATTEMPTS`, `LOCKOUT_DURATION_MINUTES` | Verrouillage de compte (7 essais / 30 min) |
| `UPLOAD_FOLDER` | Relatif et sous `static/` (`static/uploads`) |
| `MAIL_*`, `SUPPORT_EMAIL` | E-mails sortants (SMTP) ; bouton « Envoyer un e-mail de test » dans Administration → Paramètres |
| `TIMEZONE`, `LANGUAGE` | `Africa/Tunis`, `fr` |

---

## Fonctionnalités

### Tickets
- 5 types (incident, demande, besoin, plainte, tâche), 5 priorités (critique, urgente, haute, moyenne, basse), statuts nouveau → en cours → en attente → résolu → fermé (ou annulé). La **priorité se choisit à la main**.
- Routage : un département, un ou plusieurs agents, ou **collaboration multi-départements et multi-agents**.
- Catégories regroupées par département ; gestion complète (créer, modifier, activer/désactiver, archiver, supprimer) avec la permission `admin.categories`.
- Sous-tâches (checklist), commentaires, **pièces jointes jusqu'à 30 Mo** avec miniatures et visionneuse intégrée (même composant sur la fiche et la modification).
- Modification = même page que « Nouveau ticket », pré-remplie ; historique d'audit de chaque changement.
- Liste avec recherche, filtres, actions groupées et colonne « Assigné à » (Tous + département, ou noms des agents). **Les tickets jamais ouverts sont mis en évidence** (pastille rouge, fond teinté, gras).
- SLA par département (réponse 4 h, résolution 24 h par défaut) : l'échéance d'un ticket vient du SLA de son département ; suivi du retard et de la première réponse.
- Évaluation de satisfaction (1–5 étoiles) par le créateur une fois le ticket résolu.
- Numéros séquentiels atomiques (`#42`) ; les tickets se créent uniquement depuis la plateforme.

### Utilisateurs, départements, entreprises, points de vente
- Profils complets (poste, département / PDV, entreprise, photo), tri et filtres, activation/désactivation, statistiques par personne.
- **Accès à distance** : ID AnyDesk et TeamViewer par collaborateur, avec bouton « Connecter » et « Copier » pour chaque outil (mots de passe chiffrés).
- Départements : code, couleur, icône, responsable, SLA, horaires, membres.
- Entreprises (filiales) avec code couleur.
- Points de vente : KPI, effectifs, équipements, **thème couleur propre**, catégories et palette modifiables depuis *Points de vente → Catégories & thèmes*.

### Communication
- **Messagerie** privée entre utilisateurs avec fichiers joints (25 Mo), badge de messages non lus.
- **Notifications** (centre de notifications, sons « ticket envoyé / reçu », badges dans la barre latérale).
- **Boîte à idées** : proposer une idée ou un bug, statut (lue, acceptée, refusée, en cours, terminée), alerte e-mail aux responsables.
- **Base de connaissances** : catégories, articles, compteur de lectures et liste des lecteurs.

### Rapports et pilotage
- **Rapport global** : 10 indicateurs comparés à la période précédente, courbes, répartitions, carte de chaleur jour × heure, performance par département, catégories et PDV les plus actifs, tickets en retard, satisfaction. Filtres : période, département, PDV, type, priorité, agent. Export **CSV** filtré et impression / PDF.
- **Performance des agents** : classement lisible (résolus, en cours, en retard, délai moyen, SLA, satisfaction) et fiche détaillée par agent, utilisables sur téléphone.
- **Plan d'action** : suivi des tâches avec export Excel.

### Administration
- Utilisateurs, **rôles et permissions** (page par page, cases hiérarchisées, éditeur plein écran sur téléphone), catégories de tickets, paramètres système et test d'e-mail, journaux, accès à distance.

### Confort d'utilisation
- Thème clair / sombre synchronisé, palette de commandes et raccourcis clavier, info-bulles « i » au survol, fenêtres de confirmation intégrées, interface responsive (menu en tiroir sur téléphone).

### API JSON
12 endpoints sous `/api` : statistiques (globales, par jour, par département, par priorité), changement de statut, assignation, recherche d'utilisateurs, notifications (interrogation, marquage lu), santé (`/api/health`). Voir `FONCTIONNALITES.md`.

---

## Rôles et permissions

Le niveau d'un rôle sert de repère hiérarchique ; **le niveau 100 a toutes les permissions implicitement**, les autres rôles ne peuvent faire que ce qui est coché dans *Administration → Rôles*.

| Rôle | Niveau |
|---|---|
| Super Administrateur | 100 |
| Directrice Réseau | 85 |
| Responsable Département | 60 |
| Agent Support (« Agent ») | 50 |
| Responsable Point de Vente | 30 |
| Personnel Point de Vente | 10 |

- **62 permissions** en 4 catégories : Espace de travail, Opérations, Intelligence, Administration. Chaque page a toutes ses cases (voir, créer, modifier, supprimer, exporter…), rangées sous la case « voir » de la page.
- Les actions sont vérifiées **côté serveur** et masquées dans l'interface quand le rôle n'a pas la case. Des rôles personnalisés peuvent être créés, modifiés, désactivés et supprimés.
- Une permission ajoutée dans une nouvelle version reçoit, à sa création, les droits d'origine des rôles qui pouvaient déjà faire l'action : aucune perte d'accès.

---

## Sécurité

- **CSRF** sur toutes les requêtes POST/PUT/DELETE (jeton injecté par `static/js/csrf.js`) ; en-têtes de sécurité (CSP, `nosniff`).
- **Verrouillage de compte** après 7 échecs pendant 30 minutes ; levée possible par un administrateur.
- **Sessions** invalidées au changement de mot de passe ou à la désactivation du compte.
- **Fichiers** : réservés aux utilisateurs connectés, types autorisés uniquement, 30 Mo par fichier ; les fichiers de la messagerie sont stockés hors de `static/` (`instance/chat_files/`) et servis par une route autorisée.
- **Mots de passe distants** AnyDesk / TeamViewer chiffrés (Fernet), visibles uniquement par l'intéressé et les détenteurs de `admin_acces.voir`.
- **Journaux** avec rotation (5 Mo × 5) dans `logs/`.

---

## Structure du projet

```
CosmiCenter/
├── app.py                  # Factory Flask, commandes CLI (init-db, create-admin, reset-db)
├── config.py               # Configuration par environnement, APP_VERSION
├── models.py               # Modèles SQLAlchemy (26 tables)
├── serve.py                # Serveur de production (Waitress)
├── seed_db.py              # Données de démonstration (⚠ vide les tables)
├── cosmicenter.example.sql # Exemple de base : structure, rôles et données fictives (cosmicenter.sql = copie locale ignorée)
├── routes/                 # 13 blueprints, ~130 routes
│   ├── auth, tickets, utilisateurs, departements, companies, pdv
│   ├── rapports, parametres, admin, api
│   └── chat, suggestions, base_connaissance
├── services/
│   ├── reporting.py        # Moteur des rapports (global et agents)
│   ├── referentiels.py     # Catégories et thèmes PDV (JSON en base, cache)
│   └── email_service.py    # E-mails sortants
├── utils/                  # security (CSRF, en-têtes), permissions, uploads, crypto, schema
├── templates/              # ~64 gabarits Jinja2 (un dossier par module + emails, errors)
├── static/                 # css, js, images, uploads
├── scripts/                # init_db.py, ensure_venv.bat, create_db.sql, outils de base
├── deploy/                 # install.sh (Ubuntu), backup.sh
├── tests/                  # Suites d'intégration autonomes
└── *.md                    # README, CHANGELOG, guides (voir Documentation)
```

---

## Tests

Suites autonomes dans `tests/` (pas de framework), exécutées avec l'application réelle sur la base du `.env` :

```bash
venv\Scripts\python.exe tests\permissions_test.py     # Windows
venv/bin/python tests/permissions_test.py             # Linux / macOS
```

Principales suites : `nav_test`, `chat_test`, `kb_views_test`, `pdv_ref_test`, `cat_test`, `report_test`, `agents_test`, `permissions_test`, `prod_test`, `proxy_test` et **`portability_test`** (aucun chemin absolu dans le projet). Détails dans [tests/README.md](tests/README.md).

> Les tests créent des données temporaires puis les suppriment, mais **ne doivent jamais être lancés sur une base de production**.

---

## Déploiement

Sur un serveur **Ubuntu 22.04 / 24.04** : `sudo bash deploy/install.sh` installe Python, PostgreSQL, Nginx, HTTPS, le service systemd, le pare-feu et les sauvegardes quotidiennes. Pas à pas : **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**. Derrière Nginx : `BEHIND_PROXY=true` et `FLASK_HOST=127.0.0.1`.

> Les scripts `deploy/*.sh` n'ont pas encore été validés sur un vrai serveur Ubuntu.

---

## Documentation

| Document | Contenu |
|----------|---------|
| [CHANGELOG.md](CHANGELOG.md) | Historique des versions |
| [FONCTIONNALITES.md](FONCTIONNALITES.md) | Référence des fonctionnalités et des routes |
| [GUIDE_UTILISATEUR.md](GUIDE_UTILISATEUR.md) | Guide utilisateur illustré en français |
| [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) | Charte graphique et composants |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Mise en ligne sur Ubuntu |
| [tests/README.md](tests/README.md) | Suites de tests |
| [cosmicenter.example.sql](cosmicenter.example.sql) | Création de la base (structure, rôles, compte par défaut et données fictives) |

---

## Licence

Pour moi — © 2026
