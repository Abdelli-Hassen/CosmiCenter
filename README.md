# CosmiCenter — Plateforme de gestion opérationnelle

![CosmiCenter Logo](static/images/logo-cosmitto.png)

**CosmiCenter** est la plateforme interne de tickets et d'incidents de **Cosmitto Coffee**, réseau multi-points de vente (PDV) de cafés. Elle centralise les incidents, demandes, besoins, plaintes et tâches des points de vente vers les équipes centrales (Support IT, Maintenance, Stock, Qualité, RH, Finances, SI), avec priorisation, suivi des délais (SLA) et historique complet. L'interface est en français et s'utilise aussi bien sur ordinateur que sur téléphone ou tablette.

**Version actuelle : 2.7.4** (voir [CHANGELOG.md](CHANGELOG.md)).

## Sommaire

1. [Technologies](#technologies)
2. [Démarrage rapide](#démarrage-rapide)
3. [Base de données](#base-de-données)
4. [Configuration (`.env`)](#configuration-env) et [clé secrète](#clé-secrète-secret_key)
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
| Langage | **Python 3.11** (version utilisée pour le développement) |
| Serveur web | **Flask 3.0**, Flask-Login 0.6, Flask-SQLAlchemy 3.1 (SQLAlchemy 2.1, psycopg 3) |
| Base de données | **PostgreSQL 14+** (obligatoire) — schéma complété au démarrage par `utils/schema.py` |
| Interface | Jinja2 + **JavaScript vanilla** + CSS maison (thème clair/sombre, adapté aux téléphones et tablettes) |
| Production | **Waitress** 3 (`serve.py`), derrière Nginx en déploiement Ubuntu |
| Divers | Chiffrement Fernet (`cryptography`), Pillow (images), openpyxl (export Excel), SMTP pour les e-mails |

> `requirements.txt` contient aussi des paquets hérités qui ne sont **pas utilisés** par le code (`o365`, `msal`, `psycopg2-binary`, `alembic`). Flask-Migrate est branché dans `app.py`, mais il n'y a pas de dossier `migrations/` : les migrations ne sont pas utilisées, les colonnes ajoutées après coup passent par `utils/schema.py`.

---

## Démarrage rapide

**Prérequis :** Python 3.11 et un serveur PostgreSQL 14+ en marche.

### Windows

| Fichier | Rôle |
|---|---|
| `start.bat` | **Premier lancement guidé** : crée le `venv` s'il manque, installe les dépendances, crée `.env` à partir de `.env.example` s'il n'existe pas, teste la connexion à la base (`scripts/check_db.py`), puis démarre l'application en mode développement. |
| `run_dev.bat` | Développement : `python app.py`, **toujours** en local (`127.0.0.1`), débogueur et rechargement automatique actifs, quel que soit le `.env`. |
| `run_prod.bat` | Production ou partage réseau : serveur Waitress (`serve.py`), sans débogueur. Affiche, à chaque démarrage, les adresses à ouvrir depuis un téléphone sur le même réseau. |
| `Activate_venv.bat` | Ouvre une console avec l'environnement Python déjà activé. |

Tous ces fichiers démarrent depuis leur propre dossier et recréent automatiquement le `venv` s'il vient d'un autre emplacement (`scripts/ensure_venv.bat`). Dans la console du serveur : **R** = redémarrage complet (recharge le code Python et le `.env`), **Ctrl+C** = arrêt.

### Linux / macOS, ou à la main

```bash
# 1. Environnement virtuel
python -m venv venv
source venv/bin/activate        # Linux / Mac
venv\Scripts\activate           # Windows

# 2. Dépendances
pip install -r requirements.txt

# 3. Configuration
cp .env.example .env            # puis renseigner SECRET_KEY (voir « Clé secrète ») et DATABASE_URL

# 4. Base de données (voir la section suivante)
psql -U postgres -f cosmicenter.example.sql

# 5. Lancer
python app.py                   # développement (http://127.0.0.1:8080, débogueur actif)
python serve.py                 # Waitress : partage réseau / production
```

`start.sh` fait la même chose que `start.bat` sous Linux et macOS, à une différence près : s'il doit créer `.env`, il s'arrête pour que vous le remplissiez (`DATABASE_URL`, `SECRET_KEY`), puis il faut le relancer.

### Premières informations utiles

- **Adresse :** `http://127.0.0.1:8080` (port défini par `FLASK_PORT`).
- **Compte par défaut** (créé par le script SQL d'exemple) : `admin@example.com` / `testtest` — **à changer immédiatement**.
- **Partager sur le réseau (téléphone, autre poste) :** mettre `FLASK_HOST=0.0.0.0` dans `.env`, lancer `run_prod.bat`, ouvrir `http://<ip-du-poste>:8080` (autoriser le port 8080 dans le pare-feu). Dès que l'hôte n'est pas une adresse locale, le **débogueur Werkzeug est coupé automatiquement**.
- **Projet portable :** aucun chemin absolu dans le code ; le dossier peut être copié sur un autre PC ou un disque externe. Copier aussi `.env` (non versionné), la base PostgreSQL, `static/uploads/` et `instance/chat_files/`.
- **Commandes CLI** (`python -m flask --app app …`) :
  - `create-admin` : crée un compte administrateur (`admin@example.com`) s'il n'existe pas. Mot de passe = variable `ADMIN_PASSWORD`, sinon une valeur aléatoire affichée une seule fois.
  - `init-db` : commande **historique** (voir « Option B » plus bas) ; elle ne crée **pas** les 6 rôles ni les 62 permissions actuels. Préférer le script SQL d'exemple.
  - `reset-db` : ⚠ efface **toutes** les tables puis exécute `init-db` (confirmation demandée).

---

## Base de données

PostgreSQL 14 ou plus. Deux façons de créer la base :

### Option A — Script SQL d'exemple (structure, rôles et données fictives) — recommandé

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

⚠ **Changer ce mot de passe dès la première connexion** (*Paramètres du compte → Sécurité*), puis supprimer ou remplacer les données d'exemple. Les 12 autres utilisateurs d'exemple sont **inactifs** (aucune connexion possible) : activez-les ou supprimez-les.

Puis dans `.env` : `DATABASE_URL=postgresql+psycopg://cosmicenter:testtest@localhost:5432/cosmicenter`.

> **À savoir**
> - **`cosmicenter.sql` (avec les données)** est un fichier **local, ignoré par git** (`.gitignore`) : copie de la vraie base (utilisateurs, entreprises, départements, points de vente, catégories de tickets, base de connaissances, rôle personnalisé « HR »…) **sans** tickets, commentaires, pièces jointes ni messages. Il contient des e-mails et des hachages de mots de passe : ne jamais le publier. Les seuls fichiers qui portent des secrets sont donc **`.env`** et **`cosmicenter.sql`**, tous deux hors de git.
> - Les **photos et pièces jointes** ne sont pas dans la base : `static/uploads/` (ignoré par git) et `instance/chat_files/` se copient à part.
> - Aucune Row Level Security PostgreSQL : le contrôle d'accès est fait par l'application (tables `permissions`, `roles`, `roles_permissions`, méthode `Utilisateur.has_permission`, `utils/permissions.py`).
> - Le script est généré à partir de `models.py` : il faut le régénérer après une modification de modèle ou de permission.
> - Contrôle effectué : le script s'exécute sans erreur dans un schéma jetable (annulé ensuite) et crée les 26 tables. La section 0 (création du rôle et de la base, commandes `psql`) n'a pas été exécutée.
> - Les vraies données de l'organisation (départements, points de vente, catégories, base de connaissances…) ne sont **pas** dans l'exemple : elles restent dans `cosmicenter.sql` (copie locale).

### Option B — Laisser l'application faire

Au démarrage, `db.create_all()` crée les tables manquantes, puis `utils/schema.py` rejoue des instructions **idempotentes** : colonnes ajoutées après coup (`ALTER TABLE … IF NOT EXISTS`), séquence des tickets, élargissement des colonnes chiffrées, et création des permissions manquantes (avec rattrapage des droits des rôles existants).

La commande `init-db` est **historique** : elle crée les tables, une vingtaine de permissions de base, **5 anciens rôles** (Super Administrateur, Administrateur, Manager, Agent, Utilisateur — pas ceux du tableau « Rôles et permissions » ci-dessous), le compte administrateur et 4 départements d'exemple (Support IT, Ressources Humaines, Finances, Achats). Les rôles et permissions actuels ne s'obtiennent complètement qu'avec le script SQL de l'option A (ou depuis une base déjà configurée).

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

Copier `.env.example` en `.env` (jamais commité ; `start.bat` le fait automatiquement). Variables :

| Variable | Rôle |
|---|---|
| `SECRET_KEY` | **Obligatoire**, aléatoire et longue (voir [Clé secrète](#clé-secrète-secret_key)). Ne pas la changer sans migrer les champs chiffrés (sauf si `FIELD_ENCRYPTION_KEY` est définie) |
| `FIELD_ENCRYPTION_KEY` | Facultative : clé propre au chiffrement des mots de passe AnyDesk / TeamViewer (sinon dérivée de `SECRET_KEY`) |
| `DATABASE_URL` | Connexion PostgreSQL (`postgresql+psycopg://utilisateur:mot_de_passe@hôte:5432/base`) |
| `FLASK_HOST` / `FLASK_PORT` | `127.0.0.1` (local) ou `0.0.0.0` (réseau) ; port 8080 par défaut |
| `FLASK_ENV` / `FLASK_DEBUG` / `FLASK_APP` | `development` en local ; le débogueur n'est utilisé qu'en local (voir plus haut) |
| `BEHIND_PROXY` | `true` derrière Nginx (ProxyFix) ; `FLASK_HOST` reste alors `127.0.0.1` |
| `PUBLIC_BASE_URL` | URL publique utilisée dans les liens des e-mails |
| `SESSION_COOKIE_SECURE` | `true` uniquement derrière HTTPS |
| `MAX_LOGIN_ATTEMPTS`, `LOCKOUT_DURATION_MINUTES` | Verrouillage de compte (7 essais / 30 min) |
| `UPLOAD_FOLDER` | Relatif et sous `static/` (`static/uploads`) |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USE_SSL`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`, `MAIL_TIMEOUT` | E-mails sortants (SMTP) ; bouton « Envoyer un e-mail de test » dans Administration → Paramètres |
| `SUPPORT_EMAIL` | Adresse de contact affichée dans l'application |
| `ADMIN_PASSWORD` | Facultative : mot de passe initial du compte créé par `create-admin` |
| `TIMEZONE`, `LANGUAGE` | `Africa/Tunis`, `fr` |

### Clé secrète (`SECRET_KEY`)

**À quoi elle sert** (depuis la version 2.5, commit « Harden security ») :
1. **Sessions de connexion** : Flask signe avec elle le cookie qui garde l'utilisateur connecté.
2. **Protection des formulaires** : le jeton anti-falsification (CSRF) est conservé dans cette session signée.
3. **Mots de passe AnyDesk / TeamViewer** : `utils/crypto.py` en tire la clé de chiffrement de ces champs (sauf si `FIELD_ENCRYPTION_KEY` est définie).

Sans clé définie, l'application refuse de démarrer en production (« SECRET_KEY n'est pas défini »).

**D'où elle vient** : de personne, on la génère soi-même (aléatoire, 64 caractères hexadécimaux). Chaque ordinateur ou serveur a la sienne ; `deploy/install.sh` en génère une automatiquement sur un serveur Ubuntu.

**Créer ou remplacer la clé (Windows, depuis le dossier du projet)** :
```powershell
# 1. Générer une clé (copier la ligne affichée)
.\venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```
```bash
# Linux / macOS
python3 -c "import secrets; print(secrets.token_hex(32))"      # ou : openssl rand -hex 32
```
2. Dans `.env`, remplacer la valeur de la ligne `SECRET_KEY=` (sans espace ni guillemets), puis enregistrer.
3. Redémarrer l'application (**R** dans la console du serveur, ou relancer `python app.py` / `run_prod.bat`).
4. Se reconnecter : tout le monde est déconnecté une fois, c'est normal.

**Règles**
- Ne jamais la committer, ni la partager (`.env` est ignoré par git).
- Ne pas la changer à la légère une fois des mots de passe AnyDesk / TeamViewer enregistrés : ils deviendraient illisibles. Pour la changer quand même, mettre d'abord l'**ancienne** clé dans `FIELD_ENCRYPTION_KEY=` ; ils restent alors lisibles.
- Une seule clé par environnement, conservée pendant toute la vie de la base.

---

## Fonctionnalités

### Connexion et compte
- Connexion par e-mail et mot de passe ; la page « mot de passe oublié » explique que la réinitialisation est faite par un administrateur.
- **Paramètres du compte** : profil (nom, téléphone, photo avec suppression, thème, notifications par e-mail), **sécurité** (changement de mot de passe, sessions actives avec navigateur, système, adresse IP et heure, « Déconnecter les autres sessions »), centre de **notifications**.

### Tickets
- 5 types (incident, demande, besoin, plainte, tâche), 5 priorités (critique, urgente, haute, moyenne, basse), statuts nouveau → en cours → en attente → résolu → fermé (ou annulé), avec réouverture possible. La **priorité se choisit à la main**.
- Pages : tableau de bord, liste de **tous les tickets**, **mes tickets**, nouveau ticket, fiche et modification.
- Routage : un département, un ou plusieurs agents, ou **collaboration multi-départements et multi-agents**.
- Catégories regroupées par département ; gestion complète (créer, modifier, activer/désactiver, archiver, supprimer) avec la permission `admin.categories`, aussi accessible par un bouton sur la page Nouveau ticket.
- Sous-tâches (checklist), commentaires, **pièces jointes jusqu'à 30 Mo** (150 Mo par envoi) avec miniatures et visionneuse intégrée (même composant sur la fiche et la modification).
- Modification = même page que « Nouveau ticket », pré-remplie ; historique d'audit de chaque changement.
- Liste avec recherche (numéro `#12`, titre, description), filtres, **actions groupées** (statut, assignation) et colonne « Assigné à » (Tous + département, ou noms des agents). **Les tickets jamais ouverts sont mis en évidence** (pastille rouge, fond teinté, gras).
- SLA par département (réponse 4 h, résolution 24 h par défaut) : l'échéance d'un ticket vient du SLA de son département ; suivi du retard, de la première réponse et de « SLA respecté / dépassé ».
- Évaluation de satisfaction (1–5 étoiles et commentaire) par le créateur une fois le ticket résolu ou fermé.
- Numéros séquentiels atomiques (`#42`) ; les tickets se créent uniquement depuis la plateforme (pas de création par e-mail).

### Utilisateurs, départements, entreprises, points de vente
- **Utilisateurs** : annuaire avec tri et filtres (rôle, département, point de vente, statut), profil complet (poste, département / PDV, entreprise, photo), activation / désactivation, statistiques par personne.
- **Accès à distance** (Administration) : ID AnyDesk et TeamViewer par collaborateur, avec boutons « Connecter » et « Copier » pour chaque outil (mots de passe chiffrés).
- **Départements** : code, couleur, icône, responsable, SLA, horaires, membres.
- **Entreprises** (filiales) avec code couleur, archivage et rattachement de collaborateurs.
- **Points de vente** : KPI, effectifs, équipements, **thème couleur propre**, catégories et palette modifiables depuis *Points de vente → Catégories & thèmes*.

### Communication
- **Messagerie** privée entre utilisateurs avec fichiers joints (25 Mo, tout type), badge de messages non lus ; les fichiers sont stockés hors de `static/`.
- **Notifications** (centre de notifications, sons « ticket envoyé / reçu », badges dans la barre latérale, interrogation toutes les 2,5 s).
- **Boîte à idées** : proposer une idée, une amélioration ou un bug ; statut (lue, acceptée, refusée, en cours, terminée) ; alerte e-mail aux personnes dont le rôle peut voir toutes les idées.
- **Base de connaissances** : catégories, articles, nombre de lecteurs distincts et, pour ceux qui peuvent créer des articles, la liste des lecteurs.

### Rapports et pilotage
- **Rapport global** : 10 indicateurs comparés à la période précédente, courbes, répartitions, carte de chaleur jour × heure, performance par département, catégories et PDV les plus actifs, tickets en retard, satisfaction. Filtres : période, département, PDV, type, priorité, agent. Export **CSV** filtré (séparateur `;`) et impression / PDF.
- **Performance des agents** : podium, classement (résolus, en cours, en retard, délai moyen, SLA, satisfaction, situation) et fiche détaillée par agent comparée à l'équipe. Mêmes chiffres que le rapport global (`services/reporting.py`).
- **Plan d'action** : suivi des tâches sous forme de calendrier, avec **export Excel**.

### Administration
- Tableau de bord d'administration (état réel de la base, de l'e-mail et du dossier d'envoi), gestion des **utilisateurs**, **rôles et permissions**, **catégories de tickets**, **paramètres système** (SMTP, test d'e-mail), **logs** (erreurs par jour), **accès à distance** et **plan d'action**.

### Confort d'utilisation
- Thème clair / sombre synchronisé, interface responsive (menu en tiroir, tableaux et tickets en cartes sur téléphone), info-bulles « i » au survol, fenêtres de confirmation intégrées, animations (désactivées si le système demande de réduire les animations).
- Raccourcis clavier : **Ctrl/Cmd+K** palette de commandes, **Ctrl/Cmd+N** nouveau ticket, **Ctrl/Cmd+Maj+L** changer de thème, **?** aide ; dans la liste des tickets : **J / K** (naviguer), **X** (sélectionner), **Entrée** (ouvrir), **S** (statut), **A** (assigner).
- Accessibilité : lignes cliquables utilisables au clavier, boutons-icônes nommés.

### API JSON
12 endpoints sous `/api` : statistiques (globales, par jour, par département, par priorité), changement de statut, assignation, recherche d'utilisateurs, notifications (interrogation, marquage lu), santé (`/api/health`). Voir `FONCTIONNALITES.md`.

Au total : **13 modules (blueprints)** et **131 routes**.

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
- Les actions sont vérifiées **côté serveur** et masquées dans l'interface quand le rôle n'a pas la case. Des rôles personnalisés peuvent être créés, modifiés, désactivés et supprimés ; la création et la modification de rôles et d'utilisateurs est limitée au niveau de l'acteur (pas d'escalade de droits).
- Une permission ajoutée dans une nouvelle version reçoit, à sa création, les droits d'origine des rôles qui pouvaient déjà faire l'action : aucune perte d'accès.
- Visibilité des tickets : selon le département, la collaboration et le rôle (`utils/permissions.py`) ; la liste, la fiche et les actions appliquent les mêmes règles.

---

## Sécurité

- **CSRF** sur toutes les requêtes POST/PUT/DELETE (jeton injecté par `static/js/csrf.js`) ; la déconnexion se fait en POST.
- **En-têtes** : `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy`, `Strict-Transport-Security` quand `SESSION_COOKIE_SECURE=true` ; les fichiers envoyés sont servis avec une CSP « sandbox ».
- **Verrouillage de compte** après 7 échecs pendant 30 minutes (message d'erreur identique pour comptes connus et inconnus) ; levée possible par un administrateur.
- **Sessions** : option « Se souvenir de moi » à la connexion ; une session est invalidée au changement de mot de passe, par « Déconnecter les autres sessions » ou à la désactivation du compte ; redirection `?next=` limitée aux chemins locaux.
- **Fichiers** : réservés aux utilisateurs connectés, extensions contrôlées, noms aléatoires. Limites : **30 Mo** par pièce jointe de ticket, **25 Mo** par fichier de messagerie, **5 Mo** pour les photos et logos. Seules les images s'affichent dans le navigateur, les autres types sont téléchargés. Les fichiers de la messagerie sont stockés hors de `static/` (`instance/chat_files/`) et servis par une route réservée à l'expéditeur et au destinataire.
- **Mots de passe distants** AnyDesk / TeamViewer chiffrés (Fernet), visibles uniquement par l'intéressé et les détenteurs de `admin_acces.voir`.
- **Secrets** : `.env` et `cosmicenter.sql` ne sont jamais dans git (voir `.gitignore`).
- **Journaux** : rotation automatique (5 Mo × 5) dans `logs/`.

---

## Structure du projet

```
CosmiCenter/
├── app.py                  # Factory Flask, commandes CLI (init-db, create-admin, reset-db)
├── config.py               # Configuration par environnement, APP_VERSION
├── models.py               # Modèles SQLAlchemy (26 tables)
├── serve.py                # Serveur de production (Waitress)
├── start.bat / start.sh    # Premier lancement guidé (Windows / Linux, macOS)
├── run_dev.bat             # Développement (local, débogueur)
├── run_prod.bat            # Production / partage réseau (Waitress)
├── Activate_venv.bat       # Console avec le venv activé
├── requirements.txt        # Dépendances Python
├── .env.example            # Modèle de configuration (copier en .env)
├── cosmicenter.example.sql # Exemple de base : structure, rôles et données fictives
├── routes/                 # 13 blueprints, 131 routes
│   ├── auth, tickets, utilisateurs, departements, companies, pdv
│   ├── rapports, parametres, admin, api
│   └── chat, suggestions, base_connaissance
├── services/
│   ├── reporting.py        # Moteur des rapports (global et agents)
│   ├── referentiels.py     # Catégories et thèmes PDV (JSON en base, cache)
│   └── email_service.py    # E-mails sortants
├── utils/                  # security (CSRF, en-têtes), permissions, uploads, crypto, schema, console_keys
├── templates/              # 64 gabarits Jinja2 (un dossier par module + emails, errors)
├── static/                 # css (8 fichiers), js (13), images, sons, uploads
├── scripts/                # init_db.py, check_db.py, ensure_venv.bat, create_db.sql,
│                           # seed_incidents.py, migrate_profile_pics.py
├── deploy/                 # install.sh (installateur Ubuntu), backup.sh (sauvegardes)
├── tests/                  # Suites d'intégration autonomes
└── *.md                    # README, CHANGELOG, guides (voir Documentation)
```

Dossiers créés à l'exécution et ignorés par git : `venv/`, `logs/`, `instance/` (dont `chat_files/`), `static/uploads/`.

---

## Tests

Suites autonomes dans `tests/` (pas de framework), exécutées avec l'application réelle sur la base du `.env` :

```bash
venv\Scripts\python.exe tests\permissions_test.py     # Windows
venv/bin/python tests/permissions_test.py             # Linux / macOS
```

Suites : `nav_test`, `chat_test`, `kb_views_test`, `pdv_ref_test`, `cat_test`, `report_test`, `agents_test`, `permissions_test`, `prod_test`, `proxy_test` et **`portability_test`** (aucun chemin absolu dans le projet). Outils : `dbq.py` (requêtes SQL en lecture seule) et `seed_sample_tickets.py seed|clean` (tickets d'exemple pour contrôler les rapports). Détails dans [tests/README.md](tests/README.md).

> Les tests créent des données temporaires (comptes `zz.*@example.invalid`) puis les suppriment, mais **ne doivent jamais être lancés sur une base de production**.

---

## Déploiement

Sur un serveur **Ubuntu 22.04 / 24.04**, `sudo bash deploy/install.sh` fait tout en une commande :
- installe Python, PostgreSQL, Nginx et Certbot ;
- crée la base et le `.env` (mot de passe de base et clé secrète générés, ou clé existante réutilisée avec `OLD_SECRET_KEY`) ;
- restaure éventuellement votre base et vos fichiers ;
- crée le service systemd, configure Nginx (envois jusqu'à 150 Mo), le pare-feu (SSH, 80, 443) et le HTTPS Let's Encrypt ;
- programme des **sauvegardes quotidiennes** (`deploy/backup.sh` : base et fichiers envoyés, 14 jours conservés).

Relançable sans danger : les exécutions suivantes mettent simplement à jour le code et les dépendances, sans toucher à la base, au `.env` ni aux fichiers envoyés. Pas à pas : **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** (en anglais). Derrière Nginx : `BEHIND_PROXY=true` et `FLASK_HOST=127.0.0.1`.

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
