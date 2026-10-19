# Changelog - CosmiCenter

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

## [2.4.0] - 2026-10-19

### 🔒 Audit de sécurité et de fiabilité (correctifs)

#### Sécurité
- **CSRF** réellement appliqué : jeton de session vérifié sur tous les POST/PUT/DELETE (`utils/security.py`, `static/js/csrf.js`). La déconnexion passe en POST.
- **XSS** : messagerie interne (échappement de tout contenu serveur), attributs `onclick` / `onsubmit` (valeurs passées en JSON échappé), e-mails (description du ticket, commentaires, suggestions échappés).
- **Débogueur Werkzeug** désactivé automatiquement dès que `FLASK_HOST` n'est pas une adresse locale (partage réseau sans exposer l'exécution de code).
- **Verrouillage de compte** : 7 tentatives (`MAX_LOGIN_ATTEMPTS`), verrouillage **temporaire** de 30 min (`LOCKOUT_DURATION_MINUTES`), levée automatique ou par un administrateur ; message d'erreur identique pour comptes inconnus/existants.
- Redirection `?next=` limitée aux chemins locaux (open redirect corrigé) ; e-mails de connexion insensibles à la casse.
- Sessions : `session_version` — le changement de mot de passe, « Déconnecter les autres sessions » (désormais réel) et la désactivation d'un compte invalident les sessions existantes. Les comptes désactivés ne peuvent plus utiliser une session ouverte.
- Fichiers uploadés : accès réservé aux utilisateurs connectés, extensions contrôlées (images pour photos/logos), noms aléatoires, 10 Mo/fichier, en-têtes `nosniff` + CSP sandbox.
- Mots de passe AnyDesk/TeamViewer chiffrés en base et masqués aux autres utilisateurs.
- Contrôles d'accès : commenter / changer le statut / fermer / cocher une tâche exigent l'accès au ticket ; rapports et exports CSV soumis aux permissions `rapports_*` ; plan d'action (`.modifier`) ; paramètres système (`admin_parametres.modifier`, mots de passe jamais renvoyés au navigateur, clés autorisées en liste blanche) ; création/modification de rôles et d'utilisateurs limitée au niveau de l'acteur (plus d'escalade) ; un utilisateur sans droit ne peut plus changer son entreprise.
- Suppression de la route `/admin/api/migrate_db` (sans authentification) et de la route `test_davmail` (module inexistant).
- `seed_db.py` : confirmation explicite avant de vider la base ; mots de passe de démonstration aléatoires (`SEED_PASSWORD`). `init-db` : mot de passe admin aléatoire (`ADMIN_PASSWORD`). Identifiants de base retirés de `start.bat`, `check_db.py`, `.env.example`.
- En-têtes `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` ; `SECRET_KEY` obligatoire hors développement.

#### Corrigé
- Corruption de caractères (`A` → `é`) dans le code : export Excel du plan d'action, enregistrement des paramètres `.env`, upload de photo de profil, dossiers d'upload, messages d'accès.
- API : permissions (comparaison rôle/chaînes), attribut inexistant `assigne_id`, statuts, route de lecture des notifications (identifiants UUID).
- Statuts : « Ouvert » regroupe `nouveau` + `ouvert` (compteurs à 0 sur le tableau de bord, l'admin et l'API) ; le menu « Ouvert » du détail ticket n'était pas accepté par le serveur.
- Visibilité des tickets : un utilisateur sans département ne voit plus les tickets sans département ; liste, détail et actions utilisent les mêmes règles (collaborateurs et départements en collaboration inclus).
- Numéros de ticket : séquence PostgreSQL atomique (plus de doublons en cas de créations simultanées).
- Création de ticket : validations (titre, description, priorité, type, département), échec des notifications sans annuler un ticket déjà créé, pièces jointes refusées individuellement avec message.
- Délais de première réponse et de résolution (SLA) désormais calculés.
- E-mail → ticket : numéro de ticket reconnu, valeurs par défaut valides, expéditeur contrôlé, désactivé par défaut (`IMAP_ENABLE_POLLING`).
- Pages 400 / 403 / 413 ajoutées ; redirections vers des routes inexistantes corrigées ; `flask create-admin` fonctionnel.
- Départements : statistiques du détail alignées sur la liste (par département du ticket), requêtes regroupées.
- PDV, entreprises, base de connaissance, suggestions, rôles, catégories : validations et gestion des doublons (au lieu d'erreurs 500).
- Libellés : « InterComm » / « CosmittoHUB » / « CosmittoDesk » / contact `support@example.com` remplacés par « CosmiCenter » / `SUPPORT_EMAIL`.

#### Exploitation
- Journal applicatif avec rotation (5 Mo × 5), lecture des logs par la fin du fichier.
- Dernière activité écrite au plus une fois par minute et par utilisateur.
- Colonnes ajoutées automatiquement au démarrage (`utils/schema.py`).

## [2.3.0] - 2026-10-14

### 🚀 Nouveautés majeures & Refontes Opérationnelles

#### Ajouté
- 🤝 **Collaboration Multi-Départements & Multi-Agents sur les Tickets**
  - Mode d'assignation « Collaboration (multiples) » dans la création et modification de tickets.
  - Sélection interactive par tags/puces des départements impliqués avec pré-sélection automatique du département principal.
  - Filtrage dynamique et ciblé des collaborateurs affichés selon les départements participants.
  - Affichage clair de la collaboration dans la barre latérale du ticket (liste des départements associés et des membres collaborateurs).
  - Badge `+N collab` dans la colonne Département de la liste des tickets.
  - Inclusion automatique des utilisateurs de tous les départements collaborateurs dans la liste déroulante d'assignation directe.
  - Sauvegarde explicite avec boutons Enregistrer / Annuler lors des réassignations sur le détail du ticket.
- 🏪 **Module Points de Vente (PDV)**
  - Gestion dédiée des Points de Vente du réseau Cosmitto avec indicateurs spécifiques, adresses, gérants et contacts.
  - Affichage différencié dans l'annuaire : thème ambré chaleureux et icône magasin distincte pour identifier immédiatement les membres en PDV par rapport aux départements du siège.
- 🏢 **Gestion des Entreprises (Cosmitto Coffee, etc.)**
  - Entité `Entreprise` permettant le rattachement multi-sociétés des utilisateurs avec code couleur personnalisé et badges dédiés.
- 🖼️ **Visualiseur d'images Lightbox & Prévisualisations in-tab**
  - Prévisualisation directe sous forme de miniatures pour les pièces jointes d'images dans les tickets et commentaires.
  - Visualisation agrandie dans la même page via une modale plein écran sombre avec backdrop blur, zoom interactif et raccourci touche Échap.
- 💬 **Recherche améliorée dans la Messagerie**
  - Filtrage en temps réel des conversations et recherche dynamique des collègues dans la fenêtre de nouveau message.
- ↕️ **Tri des Colonnes & Ergonomie**
  - Tri par clic sur les en-têtes de colonnes (Nom, E-mail, Rôle, Département) dans l'annuaire des utilisateurs.
  - Survol interactif de ligne avec surbrillance de marque et indicateur latéral.

#### Modifié & Nettoyé
- 🗑️ **Suppression intégrale du Matricule**
  - Suppression complète du champ matricule de l'ensemble des formulaires, tableaux, filtres de recherche et routes (profils, annuaire, administration, création d'utilisateurs).
- 🎨 **Harmonisation UI / UX des boutons et en-têtes**
  - Correction du contraste et de la visibilité du bouton « Fermer » du ticket (suppression du conflit d'héritage `.btn-danger` blanc sur fond clair).
  - Simplification de l'en-tête de modification de ticket : suppression des liens de fil d'Ariane superflus et suppression des boutons de sauvegarde dupliqués en haut.
  - Avatars utilisateurs modernisés avec dégradés dynamiques aux couleurs du département et initiales contrastées en fallback.

---

## [2.2.0] - 2026-10-03

### 🚀 Nouveautés & Améliorations UI

#### Ajouté
- 📚 **Base de Connaissance (Fondations)**
  - Création de la route `/base_connaissance` et du template de base.
  - Ajout du lien dans la barre de navigation sous "Opérations".
  - Intégration de la permission `base_connaissance.voir`.
- 🔐 **Nouvelles Permissions**
  - Ajout de la permission `departements.archiver` pour archiver les départements au lieu de les supprimer.
- ✨ **Améliorations de l'Interface Utilisateur (UI/UX)**
  - **Filtres Avancés (Accès à Distance)** : Remplacement du menu déroulant textuel par un élégant système de filtres à icônes (Tous, Avec Identifiant, Sans Identifiant).
  - **Gestion des Rôles** : Refonte de l'interface des permissions. Utilisation d'un accordéon (chevron) pour masquer/afficher les actions enfants d'une page.
  - **Logique UI Intelligente** : Désactivation et grisage automatique des actions enfants (ex: Modifier) si la page parente est décochée.
  - **Navigation Fluide** : Ajout d'un script d'auto-scroll qui centre automatiquement l'élément actif dans la barre de navigation latérale au chargement de la page.
  - **Nettoyage** : Suppression du bouton "Nouvelle Permission" pour simplifier l'interface.
- 🗂️ **Catégories de tickets**
  - Liste déroulante de catégorie sous le département (création et modification), filtrée selon le département choisi.
  - La catégorie pré-remplit la **priorité** et l'**échéance** (délai de résolution) — le type de ticket reste choisi manuellement par l'utilisateur. Affichage de la catégorie et de l'échéance sur le détail du ticket.
  - Script `scripts/seed_incidents.py` : charge tous les incidents et demandes des tableaux fournis ; SI, informatique, caisse, TPE et WiFi sont rattachés au département IT (le département « SI » n'existe pas).
- 🧾 **Historique d'audit enrichi** : la modification d'un ticket enregistre aussi description, département, catégorie et assignation.

#### Corrigé
- Le département d'un ticket n'était pas affiché (liste, détail) ni pré-sélectionné à la modification ; ajout de l'alias `Ticket.departement`.
- Le filtre par département ignorait les tickets sans catégorie ; le rapport « tickets par département » aussi.

---

## [2.1.0] - 2026-10-01

#### Ajouté
- ✨ **Nouveau Design System Premium**
  - Ajout d'interactions de survol (lift-off, ombres dynamiques)
  - Intégration de badges de statut et de priorité repensés
  - Création d'un référentiel `DESIGN_SYSTEM.md` pour l'interface
- 🏆 **Gamification des Performances**
  - Tableau "Le Podium (Top 3)" sur la page des performances
  - Classement général (#) visible dans le tableau global
  - Badges de classement dorés sur les profils d'agents
- 📈 **Profils d'Agents Détaillés**
  - Nouvelle page dédiée pour le tableau de bord individuel des agents
  - Cartes KPI spécifiques à l'agent (Résolus, Taux de résolution, Temps moyen, CSAT)
  - Historique complet des tickets traités par l'agent
- 🔍 **Recherche et Tri Côté Client**
  - Barre de recherche instantanée (par nom/département ou par titre de ticket)
  - Tri dynamique en cliquant sur les en-têtes de colonnes des tableaux
  - Animations de chargement et de filtrage (`slide-up`, `fade-in-up`)

---

## [2.0.0] - 2026-02-09

#### Ajouté
- ✨ **Système de rôles et permissions granulaire**
  - 5 rôles pré-configurés (Super Admin, Admin, Manager, Agent, Utilisateur)
  - Permissions personnalisables par rôle
  - Gestion fine des accès aux fonctionnalités

- 👥 **Gestion avancée des utilisateurs**
  - Profils utilisateurs complets avec photo
  - Matricule et informations détaillées
  - Paramètres de notification personnalisés
  - Gestion des préférences (thème, langue)

- 🏢 **Gestion complète des départements**
  - Création et organisation de départements
  - Catégories de tickets par département
  - SLA configurables
  - Horaires de travail personnalisés
  - Responsables de département
  - Statistiques par département

- 📊 **Rapports et statistiques avancés**
  - Tableau de bord avec métriques en temps réel
  - Rapports de performance des agents
  - Statistiques de satisfaction client
  - Analyse des temps de résolution
  - Suivi du respect des SLA
  - Export en CSV
  - Graphiques et visualisations

- 🔔 **Système de notifications**
  - Notifications en temps réel
  - Centre de notifications
  - Alertes par email (optionnel)
  - Paramètres personnalisables

- 📚 **Base de connaissances**
  - Articles FAQ
  - Solutions pré-enregistrées
  - Modèles de réponses
  - Recherche intégrée
  - Gestion collaborative

- 🎯 **Améliorations des tickets**
  - Sous-tâches et checklist
  - Calcul automatique de priorité (impact × urgence)
  - Tags personnalisables
  - Évaluation de satisfaction
  - Données personnalisées par type de ticket
  - Historique détaillé des modifications

- 🎨 **Interface utilisateur modernisée**
  - Design professionnel et distinctif
  - Thème clair/sombre
  - Responsive (mobile, tablette, desktop)
  - Animations fluides et micro-interactions
  - Typographie unique (Staatliches + IBM Plex Sans)
  - Couleurs inspirées de l'identité Cosmitto
  - Effet de grain et textures subtiles

- 🔧 **Améliorations techniques**
  - Architecture modulaire avec blueprints
  - Configuration par environnement
  - Migrations de base de données (Flask-Migrate)
  - Logging amélioré
  - Gestion d'erreurs robuste
  - API REST pour intégrations futures
  - Support multi-bases de données (SQLite, PostgreSQL, MySQL)

- 📝 **Documentation**
  - README complet et détaillé
  - Guide d'installation pas à pas
  - Documentation des configurations
  - Exemples de personnalisation
  - Scripts de démarrage automatisés

#### Modifié
- 🔄 Refonte complète du modèle de données
- 🔄 Amélioration de l'architecture du code
- 🔄 Optimisation des performances
- 🔄 Sécurité renforcée

#### Sécurité
- 🔒 Hashage sécurisé des mots de passe
- 🔒 Protection CSRF
- 🔒 Validation des entrées utilisateur
- 🔒 Gestion des sessions sécurisée
- 🔒 Prévention des injections SQL

---

## [1.0.0] - 2024-XX-XX

### Version Initiale
- Gestion basique des tickets
- Authentification utilisateur
- Rôles simples (admin, utilisateur, département)
- Départements et catégories
- Interface basique

---

**Format**: Ce changelog suit le format [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/)
