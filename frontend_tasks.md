# Plan d'action pour la mise à jour du Front-End (InterComm)

Voici la liste des tâches à accomplir pour intégrer toutes les fonctionnalités requises par le manuel de l'utilisateur. Cochez les cases au fur et à mesure de votre progression.

## Étape 1 : Amélioration de l'Authentification et Profil
- [x] **Connexion (`connexion.html`)** : Vérifier et adapter les textes selon le manuel (ex. indication que seul l'admin peut créer un compte, contact `support@example.com` pour le mot de passe oublié).
- [x] **Mon compte (`profil.html`)** : Ajouter les champs pour modifier le nom, téléphone, photo de profil.
- [x] **Mon compte (`profil.html`)** : Ajouter le formulaire de changement de mot de passe (mot de passe actuel + nouveau mot de passe x2).

## Étape 2 : Page d'accueil (Tableau de bord)
- [x] **Accueil (`tableau_bord.html`)** : Intégrer un fil d'actualités "Quoi de neuf ?" (nouveautés de l'application et actualités IT/Cybersécurité).

## Étape 3 : Création et Liste de Tickets
- [x] **Nouveau Ticket (`nouveau.html`)** : Ajouter le menu déroulant « Processus IT » (qui conditionne automatiquement Type/Catégorie).
- [x] **Nouveau Ticket (`nouveau.html`)** : Ajouter le champ de téléchargement de pièces jointes.
- [x] **Tous les tickets (`liste.html`)** : Ajouter des filtres avancés (société, statut, type, catégorie, priorité).
- [x] **Tous les tickets (`liste.html`)** : Ajouter une case à cocher « Archivés » pour afficher les tickets masqués.

## Étape 4 : Gestion de Ticket (Côté Agent)
- [x] **Fiche Ticket (`detail.html`)** : Ajouter le bloc "Gestion du ticket" avec menus déroulants pour Statut et Assigné à.
- [x] **Fiche Ticket (`detail.html`)** : Ajouter les boutons Archiver/Désarchiver.
- [x] **Fiche Ticket (`detail.html`)** : Ajouter l'option "Note interne" (case à cocher) pour les commentaires.
- [x] **Fiche Ticket (`detail.html`)** : Ajouter le bloc "Processus IT" (Checklist des étapes).
- [x] **Fiche Ticket (`detail.html`)** : Ajouter le bouton "Marquer l'original comme archivé" pour les formulaires papier (Processus IT).
- [x] **Fiche Ticket (`detail.html`)** : Ajouter le bouton "Automatiser" pour le processus "Accès Sage 100" avec l'affichage des résultats (RDP, Fichiers, SQL).

## Étape 5 : Nouvelles Fonctionnalités (Base de connaissances & Chat)
- [x] **Base de connaissances (`faq/liste.html`)** : Créer l'interface pour lister les guides avec un filtre par catégorie.
- [x] **Base de connaissances (`faq/detail.html`)** : Créer l'interface pour consulter le contenu complet d'un article.
- [x] **Chat (`chat/inbox.html`)** : Créer l'interface de messagerie (liste des conversations à gauche, conversation active à droite).
- [x] **Chat (`chat/inbox.html`)** : Ajouter les actions d'archivage (icône au survol) et le bouton "+ Conversation".

## Étape 6 : Outils Agent / Admin
- [x] **Plan d'action (`admin/plan_action.html`)** : Créer le calendrier pour suivre les tickets assignés et les tâches planifiées.
- [x] **Plan d'action (`admin/plan_action.html`)** : Ajouter le tableau de suivi des projets de l'équipe IT en bas de page.
- [x] **Accès à distance (`admin/acces_distance.html`)** : Créer la page avec la barre de recherche centralisée (nom, poste, société) pour les identifiants de connexion.
