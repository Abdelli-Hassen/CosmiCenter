# Cosmicenter — Fonctionnalités

Plateforme de gestion des opérations interne de **Cosmitto Coffee** (réseau multi-POS).

---

## Table des matières

1. [Authentification](#1-authentification)
2. [Tableau de bord](#2-tableau-de-bord)
3. [Tickets](#3-tickets)
4. [Annuaire des utilisateurs](#4-annuaire-des-utilisateurs)
5. [Départements](#5-départements)
6. [Points de Vente (PDV)](#6-points-de-vente-pdv)
7. [Entreprises](#7-entreprises-multi-sociétés)
8. [Administration](#8-administration)
9. [Rapports](#9-rapports)
10. [Paramètres du compte](#10-paramètres-du-compte)
11. [API REST](#11-api-rest)
12. [Modèles de données](#12-modèles-de-données)
13. [Rôles et permissions](#13-rôles-et-permissions)
14. [Architecture technique](#14-architecture-technique)

---

## 1. Authentification

| Route | Fonctionnalité |
|-------|---------------|
| `GET/POST /auth/connexion` | Connexion e-mail + mot de passe ; option "Se souvenir de moi" ; vérification du statut actif du compte |
| `GET /auth/deconnexion` | Déconnexion et invalidation de la session |
| `GET/POST /auth/mot-de-passe-oublie` | Demande de réinitialisation de mot de passe (envoi d'e-mail) |
| `GET /auth/profil` | Affichage du profil de l'utilisateur connecté |

**Sécurité**
- Hashage des mots de passe avec Werkzeug (scrypt)
- Verrouillage temporaire du compte après 7 tentatives échouées (30 minutes, configurable)
- Protection CSRF sur tous les formulaires POST
- Sessions sécurisées Flask-Login

---

## 2. Tableau de bord

Route : `GET /tickets/tableau-bord`

**Métriques affichées**
- Compteurs : tickets ouverts, en cours, résolus, en attente
- Activité récente : derniers tickets créés ou modifiés
- Répartition par priorité et par département
- Filtrage automatique selon le rôle : admins et managers voient tout, agents et utilisateurs voient uniquement leurs tickets

---

## 3. Tickets

### 3.1 Liste des tickets

Route : `GET /tickets/liste`

- Pagination (20 par page)
- Filtres : statut, priorité, département
- Tri par date de création décroissante
- Accès filtré par rôle (voir section Rôles)

### 3.2 Créer un ticket

Route : `GET/POST /tickets/nouveau`

**Types de tickets**
| Type | Description |
|------|-------------|
| Incident | Panne, dysfonctionnement |
| Demande | Demande de service ou d'information |
| Besoin | Besoin opérationnel (fournitures, équipements) |
| Plainte | Réclamation client ou interne |
| Tâche | Tâche planifiée ou projet |

**Champs disponibles**
- Titre, description
- Type, département puis catégorie : la liste des catégories s'affiche sous le département et ne montre que celles du département choisi
- Le type de ticket (Incident, Demande, etc.) reste choisi manuellement par l'utilisateur ; choisir une catégorie ne change ni la priorité (toujours choisie à la main) ni l'échéance (SLA du département).
- Tout ce qui touche à la technologie (SI, informatique, caisse, TPE, WiFi, messagerie) est rattaché au département IT
- Priorité (basse / moyenne / haute / urgente / critique) — pré-remplie par la catégorie, modifiable
- Impact et urgence → calcul automatique de priorité via matrice Impact × Urgence
- Champs spécifiques par type : article demandé, quantité, unité, nature du besoin, personne concernée, date et lieu d'incident
- Numéro unique généré automatiquement (ex. `TK-2026-0042`)
- **Modes d'assignation & Routage** :
  - *À tout le département* : assignation globale à l'équipe du département.
  - *À une personne spécifique* : assignation directe à un agent filtré selon le département sélectionné.
  - *Collaboration (multiples)* : implication de plusieurs départements avec sélection interactive par tags. Pré-sélectionne automatiquement le département principal et filtre la liste des collaborateurs éligibles uniquement parmi les membres des départements participants.

### 3.3 Détail d'un ticket

Route : `GET /tickets/<id>`

- Affichage complet : description, historique, commentaires, pièces jointes, sous-tâches
- Contrôle d'accès : créateur, agent assigné, ou admin/manager
- Section **Collaboration** : visualisation des départements associés et des membres collaborateurs
- Assignation d'un agent avec bouton explicite "Enregistrer" / "Annuler"
- Visualiseur de médias : prévisualisation en cartes miniatures des images jointes et agrandissement dans la même page via une modale Lightbox avec fond flouté
- Ajout de commentaires (publics ou internes) avec pièces jointes multiples
- Fermeture du ticket via bouton d'action directe

### 3.4 Modifier un ticket

Route : `GET/POST /tickets/<id>/modifier`

- Modification du titre, description, priorité, statut, type, département et catégorie (filtrée par département)
- Mode d'assignation (département, spécifique, ou collaboration multiple avec sélection interactive)
- Assignation (réservée aux admins/managers)
- Enregistrement automatique dans l'historique : titre, type, priorité, statut, description, département, catégorie et assignation
- Bouton de retour rapide vers le détail du ticket

### 3.5 Commenter un ticket

Route : `POST /tickets/<id>/commenter`

- Commentaire public ou interne (note visible uniquement par les agents)
- Type : commentaire, solution, note

### 3.6 Fermer un ticket

Route : `POST /tickets/<id>/fermer`

- Passage au statut `fermé`
- Enregistrement de la date de fermeture
- Permission : créateur, assigné, ou admin

### 3.7 Suivi SLA

- Temps de première réponse (`date_premiere_reponse`)
- Temps de résolution (`date_resolution`)
- Indicateur de respect du SLA (`sla_respecte`)
- Temps calculés en minutes pour les rapports

### 3.8 Évaluation de satisfaction

- Note de 1 à 5 étoiles
- Commentaire libre associé

### 3.9 Historique des modifications

Chaque modification d'un ticket crée une entrée d'audit :
- Champ modifié, ancienne valeur, nouvelle valeur
- Utilisateur et horodatage

---

## 4. Annuaire des utilisateurs

Route : `GET /utilisateurs/`

- Liste de tous les utilisateurs (pagination 50 par page)
- Filtres : recherche instantanée (nom, prénom, e-mail), rôle, département, point de vente (PDV), statut actif/inactif
- Tri dynamique par clic sur les colonnes (Nom, E-mail, Rôle, Département)
- Vue en liste avec surbrillance au survol, avatars colorés, nom, poste, e-mail, rôle, département / PDV (avec distinction visuelle ambrée pour les équipes en point de vente), statut
- Rattachement d'entreprise avec badge coloré

### 4.1 Profil utilisateur

Route : `GET /utilisateurs/<id>`

- Informations complètes : nom, poste, département / PDV, entreprise, e-mail, téléphone
- Statistiques : tickets créés, tickets en cours assignés, tickets résolus, commentaires
- 10 derniers tickets récents

### 4.2 Créer un utilisateur

Route : `GET/POST /utilisateurs/nouveau`

Champs : nom, prénom, e-mail, mot de passe, rôle, département, point de vente, entreprise, téléphone, poste

### 4.3 Modifier un utilisateur

Route : `GET/POST /utilisateurs/<id>/modifier`

- Auto-modification limitée (pas de changement de rôle)
- Admin : modification complète
- Changement de mot de passe optionnel
- Validation de l'unicité de l'e-mail

### 4.4 Activer / Désactiver

Route : `POST /utilisateurs/<id>/toggle-actif`

Blocage de la désactivation sur son propre compte.

### 4.5 Supprimer

Route : `POST /utilisateurs/<id>/supprimer`

Bloqué si l'utilisateur a des tickets associés (désactivation recommandée).

---

## 5. Départements

### 5.1 Liste des départements

Route : `GET /departements/`

- Pagination (20 par page)
- Filtres : recherche, statut actif/inactif
- Non-admins : voient uniquement leur département
- Statistiques par département : membres, tickets actifs/total, catégories

### 5.2 Détail d'un département

Route : `GET /departements/<id>`

- Membres, responsable, contact (e-mail, téléphone, localisation)
- SLA configurés (temps de réponse, temps de résolution)
- Statistiques tickets par statut
- 10 tickets récents

### 5.3 Créer / Modifier un département

Routes : `GET/POST /departements/nouveau` · `GET/POST /departements/<id>/modifier`

**Champs**
| Champ | Description |
|-------|-------------|
| Nom | Nom unique du département |
| Code | Code court unique (ex. `IT`, `RH`) |
| Description | Description libre |
| E-mail / Téléphone | Contact du département |
| Localisation | Adresse ou site |
| Couleur | Couleur d'identification (hex) |
| Icône | Icône SVG ou emoji |
| Responsable | Utilisateur responsable |
| SLA réponse | Délai de première réponse (heures, défaut : 4h) |
| SLA résolution | Délai de résolution (heures, défaut : 24h) |
| Horaires de travail | JSON (jours, heures) |

### 5.4 Activer / Désactiver / Archiver / Supprimer

- Toggle actif : `POST /departements/<id>/toggle-actif`
- Archiver : Permission `departements.archiver`
- Suppression : bloquée si des membres ou catégories sont rattachés

---

## 6. Points de Vente (PDV)

Route : `GET /pdv/`

Le module Points de Vente centralise la gestion du réseau de cafés Cosmitto :
- Liste avec recherche, filtres par catégorie (Urbain, Mall, Drive, etc.) et statut opérationnel.
- Détail d'un PDV (`GET /pdv/<id>`) :
  - Métriques clés (Effectif, tickets ouverts, taux de résolution).
  - Équipe rattachée au point de vente.
  - Historique et tableau des tickets d'incidents / demandes liés au PDV.
  - Coordonnées, localisation géographique et gérant.
- Thème visuel distinctif : dans l'annuaire et les tickets, les équipes en PDV sont mises en valeur avec une palette ambrée et une icône boutique pour les distinguer immédiatement des départements du siège.

---

## 7. Entreprises (Multi-Sociétés)

Route : `GET /companies/`

Permet la structuration des filiales et entités juridiques du groupe (Cosmitto Coffee, etc.) :
- Liste et détail des entreprises (`GET /companies/<id>`).
- Code couleur d'entreprise personnalisé.
- Rattachement automatique des utilisateurs et affichage de badges stylisés sur les profils et l'annuaire.

---

## 8. Administration

Accès réservé aux utilisateurs avec `role.niveau >= 70`.

### 6.1 Tableau de bord admin

Route : `GET /admin/tableau-bord`

- Statistiques globales : utilisateurs actifs, départements, tickets ouverts/total/du mois
- Tickets regroupés par statut et priorité

### 6.2 Gestion des utilisateurs (admin)

Route : `GET /admin/utilisateurs`

- Vue liste avec stat chips (total, actifs, inactifs)
- Filtres : recherche (nom, prénom, e-mail, poste), rôle (dynamique), département, statut
- Actions par ligne : modifier, désactiver, réactiver

**Créer** : `GET/POST /admin/utilisateurs/nouveau`
**Modifier** : `GET/POST /admin/utilisateurs/<id>/modifier`
**Désactiver** : `POST /admin/utilisateurs/<id>/desactiver` — empêche la self-désactivation
**Réactiver** : `POST /admin/utilisateurs/<id>/reactiver` — remet à zéro le verrou et les tentatives de connexion

### 6.3 Rôles et permissions

Route : `GET /admin/roles`

- Liste des rôles avec niveau hiérarchique et couleur
- Permissions organisées par catégorie dans une interface en accordéon.
- Rôles système (non modifiables) vs rôles personnalisés
- Les actions enfants sont grisées et désactivées si la page parente est décochée.

**Créer un rôle** : `POST /admin/roles/creer` — nom, niveau, couleur, description
**Modifier un rôle** : `POST /admin/roles/<id>/modifier`
**Modifier les permissions** : `POST /admin/roles/<id>/permissions` — cases à cocher hiérarchisées.

### 6.4 Catégories de tickets

Route : `GET /admin/categories`

Affichage en tableau : nom + couleur, description, type, département, nombre de tickets, statut.

**Créer** : `POST /admin/categories/creer`

| Champ | Valeurs |
|-------|---------|
| Nom | Texte libre |
| Description | Optionnel |
| Type | incident / demande / besoin / plainte / tâche |
| Département | Sélection (obligatoire) |
| Priorité par défaut | basse / moyenne / haute / urgente / critique |
| Délai de résolution | Jours (défaut : 7) |
| Couleur | Sélecteur de couleur |

**Toggle actif/inactif** : `POST /admin/categories/<id>/toggle`

### 6.5 Paramètres système

Route : `GET /admin/parametres` — (en cours d'implémentation)

### 6.6 Logs système

Route : `GET /admin/logs` — (en cours d'implémentation)

---

## 7. Rapports

Accès réservé aux rôles avec la permission `rapports.voir`.

### 7.1 Tableau de bord rapports

Route : `GET /rapports/`

**Filtres de période** : 7 jours / 30 jours / 90 jours / 1 an

**Métriques globales**
- Total tickets, ouverts, résolus, fermés
- Utilisateurs et départements actifs
- Temps moyen de première réponse (minutes)
- Temps moyen de résolution (minutes)
- Note de satisfaction moyenne
- Taux de respect des SLA (%)

**Distributions**
- Par statut (nouveau, en cours, en attente, résolu, fermé, annulé)
- Par priorité (basse → critique)
- Par type (incident, demande, besoin, plainte, tâche)
- Par département

**Évolution quotidienne** : courbe des tickets créés jour par jour

**Top 10 agents** : classés par tickets résolus sur la période

### 7.2 Performance des agents

Route : `GET /rapports/performance-agents`

Par agent : tickets totaux, résolus, en cours, temps moyen de résolution, taux de résolution (%), satisfaction moyenne.

### 7.3 Satisfaction client

Route : `GET /rapports/satisfaction-client`

- Filtres de période
- Distribution des notes 1–5 étoiles
- Satisfaction moyenne globale
- Satisfaction par département
- Liste des derniers commentaires positifs et négatifs

### 7.4 Export CSV

Route : `GET /rapports/export/csv`

Export de tous les tickets avec filtres de dates.

**Colonnes exportées** : numéro, titre, type, priorité, statut, créateur, assigné, département, catégorie, date création, date résolution, satisfaction.

### 7.5 API stats (JSON)

Route : `GET /rapports/api/stats`

Paramètre `type` :
- `evolution` → données pour graphique journalier
- `statuts` → distribution par statut

---

## 8. Paramètres du compte

### 8.1 Profil

Route : `GET /parametres/profil`

Statistiques personnelles : tickets créés, assignés actifs, résolus.

### 8.2 Modifier le profil

Route : `GET/POST /parametres/profil/modifier`

- Nom, prénom, téléphone
- Préférences d'affichage : thème (clair/sombre/auto), langue
- Notifications : e-mail, push

### 8.3 Sécurité — changer le mot de passe

Route : `GET/POST /parametres/securite`

- Validation de l'ancien mot de passe
- Minimum 8 caractères
- Confirmation requise

### 8.4 Notifications

Route : `GET /parametres/notifications`

- Liste paginée (20 par page), non-lues en premier
- Marquer une notification comme lue : `POST /parametres/notifications/<id>/marquer-lue`
- Tout marquer comme lu : `POST /parametres/notifications/marquer-toutes-lues`

**Types de notifications**
- Ticket créé, assigné, commenté, statut changé
- Échéance approchante
- SLA dépassé
- Mention dans un commentaire
- Notification système

---

## 9. API REST

Toutes les routes API requièrent `@login_required`.

| Route | Méthode | Description |
|-------|---------|-------------|
| `/api/stats/globales` | GET | Stats globales JSON : tickets, utilisateurs, départements |
| `/api/stats/tickets-par-jour` | GET | Tickets créés par jour (30 derniers jours) |
| `/api/stats/tickets-par-departement` | GET | Tickets groupés par département |
| `/api/stats/tickets-par-priorite` | GET | Tickets groupés par priorité |
| `/api/tickets/<id>/statut` | PUT | Changer le statut d'un ticket |
| `/api/tickets/<id>/assigner` | PUT | Assigner ou désassigner un ticket |
| `/api/recherche/utilisateurs` | GET | Recherche d'utilisateurs (min. 2 chars, max 10 résultats) |
| `/api/health` | GET | Vérification de l'état du serveur |

---

## 10. Modèles de données

| Modèle | Rôle principal |
|--------|---------------|
| `Utilisateur` | Comptes utilisateurs avec rôles, département, préférences |
| `Role` | Rôles hiérarchiques avec niveau et permissions associées |
| `Permission` | Permissions granulaires par code (ex. `tickets.modifier`) |
| `Departement` | Unités organisationnelles avec SLA et responsable |
| `CategorieTicket` | Catégories de tickets par type et département |
| `Ticket` | Tickets avec statut, priorité, SLA, satisfaction, historique |
| `Tache` | Sous-tâches rattachées à un ticket |
| `Commentaire` | Commentaires publics et notes internes sur les tickets |
| `PieceJointe` | Fichiers joints à un ticket |
| `HistoriqueTicket` | Journal d'audit de chaque modification de ticket |
| `Notification` | Notifications utilisateur (lue/non lue) |
| `Statistique` | Données agrégées pour les rapports |
| `ModeleReponse` | Modèles de réponses pré-rédigés pour les agents |
| `BaseConnaissance` | Articles FAQ et base de connaissances |
| `ArticleVue` | Lectures d'un article par personne (nombre de lectures, dernière lecture) ; affichées au survol de l'œil pour les gestionnaires |

---

## 11. Rôles et permissions

### Rôles préconfigurés

| Rôle | Niveau | Accès |
|------|--------|-------|
| Super Administrateur | 100 | Accès complet, y compris configuration système |
| Administrateur | 90 | Gestion utilisateurs, départements, tickets, rapports |
| Manager | 70 | Supervision de son département, assignation, rapports |
| Agent | 50 | Traitement des tickets assignés, commentaires |
| Utilisateur | 10 | Création et suivi de ses propres tickets |

**Architecture des permissions (Séparation Pages / Actions)**

Le système de permissions est divisé en deux catégories :
1. **Pages (`.voir`)** : Détermine l'accès au menu et la visibilité d'une vue (ex. `tickets_tous.voir`, `admin_roles.voir`).
2. **Actions** : Détermine les opérations spécifiques possibles sur une page (ex. `tickets.creer`, `tickets.modifier`).

*14 Pages disponibles :* `dashboard.voir`, `tickets_tous.voir`, `tickets_mes.voir`, `tickets_nouveau.voir`, `messagerie.voir`, `departements.voir`, `utilisateurs.voir`, `rapports_globaux.voir`, `rapports_performance.voir`, `base_connaissance.voir`, `admin_dashboard.voir`, `admin_roles.voir`, `admin_plan_action.voir`, `admin_acces.voir`.

*Actions associées :* `tickets.creer`, `tickets.modifier`, `tickets.supprimer`, `departements.creer`, `departements.modifier`, `departements.archiver`, `utilisateurs.creer`, `utilisateurs.modifier`, `utilisateurs.supprimer`.

*Note: La désactivation d'une page (ex. `tickets_tous.voir`) désactive automatiquement et en cascade (UI grisée) les actions enfants (ex. `tickets.modifier`) pour ce rôle.*
---

## 12. Architecture technique

### Stack

| Composant | Technologie |
|-----------|-------------|
| Backend | Python 3.11, Flask 3.0 |
| ORM | Flask-SQLAlchemy |
| Migrations | Flask-Migrate (Alembic) |
| Auth | Flask-Login |
| Templates | Jinja2 |
| Base de données | SQLite (dev), PostgreSQL (prod) |
| Frontend | HTML/CSS/JS vanilla (pas de framework JS) |
| Typographie | IBM Plex Sans, IBM Plex Mono, Staatliches |

### Structure du projet

```
Cosmicenter/
├── app.py                  # Point d'entrée Flask, factory
├── config.py               # Configuration par environnement
├── models.py               # 14 modèles SQLAlchemy
├── routes/
│   ├── auth.py             # Authentification (4 routes)
│   ├── tickets.py          # Tickets (7 routes)
│   ├── admin.py            # Administration (15 routes)
│   ├── utilisateurs.py     # Annuaire utilisateurs (6 routes)
│   ├── departements.py     # Départements (6 routes)
│   ├── rapports.py         # Rapports et export (5 routes)
│   ├── parametres.py       # Paramètres compte (6 routes)
│   └── api.py              # API REST (8 routes)
├── templates/              # 30 templates Jinja2
├── static/
│   ├── css/                # Feuilles de style
│   ├── js/app.js           # Logique UI (ripples, dropdowns, tabs, sidebar)
│   └── images/             # Logos, screenshots, guide
├── scripts/
│   ├── init_db.py          # Initialisation de la base de données
│   └── seed_incidents.py   # Données de test
└── instance/               # Fichier SQLite (dev)
```

### Chiffres clés

| Métrique | Valeur |
|----------|--------|
| Routes HTTP | 57 endpoints |
| Modèles de données | 14 |
| Templates Jinja2 | 30 |
| Rôles préconfigurés | 5 |
| Permissions | 20+ |
| Types de tickets | 5 |
| Priorités | 5 niveaux |
| Statuts de ticket | 6 |

---

*Cosmicenter — Pour moi © 2026 — Documentation*

## Affichage mobile (2.7.0)
Toutes les pages s'adaptent aux téléphones et tablettes : menu latéral en tiroir (bouton « ☰ » en haut à gauche), barre du haut allégée, tableaux défilants, grilles sur 1–2 colonnes, formulaires en une colonne. Messagerie : liste des conversations puis conversation plein écran avec bouton retour.
