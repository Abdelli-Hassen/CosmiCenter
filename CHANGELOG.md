# Changelog - CosmittoDesk

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

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
