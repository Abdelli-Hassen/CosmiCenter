# Changelog - CosmiCenter

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

## [2.7.0] - 2026-10-25

### 📱 Compatible téléphones et tablettes
- Nouveau bouton « ☰ » (≤ 1024 px) : le menu latéral s'ouvre en tiroir avec fond assombri (il n'avait aucun bouton d'ouverture sur mobile).
- Nouveau `static/css/mobile.css` (chargé en dernier) : barre du haut allégée, marges réduites, en-têtes empilés, tableaux défilants, grilles en 1–2 colonnes, formulaires à 16 px (pas de zoom iOS), fenêtres et notifications plein écran, `100dvh`.
- Page Ticket : le panneau de droite passe sous le fil de discussion ; correction d'une collision de la classe `.sidebar` qui cachait ce panneau sur petit écran.
- Messagerie : liste des conversations puis conversation plein écran avec bouton retour.
- `run_prod.bat` / `serve.py` : quand le serveur écoute sur le réseau (`0.0.0.0`), la console affiche les adresses à ouvrir depuis un téléphone (la première = celle de la connexion active).

## [2.6.3] - 2026-10-25

### 🎨 Changement de thème
- La barre du haut et le menu latéral changent maintenant complètement de thème dès le clic (avant, ils restaient à moitié dans l'ancien thème jusqu'au changement de page). Cause : un `<style>` `!important` posé au chargement figeait le fond de `html`/`body` derrière ces zones translucides ; le fond est maintenant posé en inline sur `<html>` et mis à jour par `theme.js`. Fondu CSS à la place de `startViewTransition`, flou d'arrière-plan coupé pendant le fondu.

### 🧭 Menu latéral
- La position de défilement du menu est conservée d'une page à l'autre (avant, il revenait en haut puis redescendait en animation à chaque navigation). Le menu ne bouge plus que si l'élément actif est hors de la zone visible, et sans animation.

### 🚀 Lanceurs dev / prod clarifiés
- `run_dev.bat` (`python app.py`) est désormais **toujours** en développement : écoute sur `127.0.0.1` uniquement, débogueur et auto-reload actifs, quel que soit `FLASK_HOST` / `FLASK_ENV` du `.env` (chargé avec `override=True`, il annulait les réglages du `.bat`).
- `run_prod.bat` (`serve.py`, Waitress) reste le seul lanceur pour la production et le partage réseau (`FLASK_HOST=0.0.0.0`), sans débogueur.

## [2.6.2] - 2026-10-20

### 📦 Projet portable (aucun chemin en dur)
- Les lanceurs `start.bat`, `run_dev.bat`, `run_prod.bat`, `Activate_venv.bat` démarrent toujours depuis leur propre dossier (`cd /d "%~dp0"`), même lancés depuis un raccourci ou « en tant qu'administrateur ».
- Nouveau `scripts/ensure_venv.bat` : détecte un environnement Python (`venv`) copié d'un autre emplacement ou d'un autre PC (il mémorise son chemin) et le recrée automatiquement ; accepte les chemins avec espaces et parenthèses.
- `start.sh` réécrit (l'ancien parlait de CosmittoDesk, SQLite et d'un mot de passe par défaut) : mêmes garanties sous Linux/macOS.
- `.env` chargé depuis le dossier du projet par `app.py`, `seed_db.py` et `scripts/check_db.py`, quel que soit le dossier de lancement.
- Nouveau dossier **`tests/`** : les suites d'intégration (navigation, messagerie, PDV, catégories, rapports, agents, production, ProxyFix) + `dbq.py` + `seed_sample_tickets.py`, qui retrouvent la racine seuls. L'assertion obsolète de `nav_test` est corrigée (28/28).
- **`tests/portability_test.py`** : échoue au moindre chemin absolu (lecteur Windows, dossier utilisateur Windows/Mac/Linux, partage réseau) dans le code, les gabarits, les scripts, les docs, le `.env` ou les données de la base, et vérifie que les fichiers référencés en base existent dans le dossier du projet.
- Installateur Ubuntu : `APP_DIR` / `BACKUP_DIR` modifiables, chemins de fichiers acceptés en `~/fichier` ou relatifs au dossier de lancement.
- Documentation : chemins absolus retirés de `DEPLOYMENT_GUIDE.md` ; `.gitattributes` (`.bat` en CRLF, `.sh` en LF) ; `tests/` exclu de l'installation Ubuntu.

## [2.6.1] - 2026-10-20

### 👥 Performance des agents : refonte simple et lisible
- **Page Performance des agents** : encadré « Comment lire cette page » (20 secondes), 6 chiffres d'équipe (agents actifs, résolus, délai moyen, respect du SLA, en retard, tickets sans agent) et un classement clair : Résolus · En cours · En retard · Délai moyen · Respect SLA · Satisfaction · **Situation** (Au point / À surveiller / Attention, règle expliquée sur la page). Clic sur une ligne = fiche de l'agent.
- **Fiche d'un agent** : résumé en une phrase, 6 chiffres comparés à la moyenne de l'équipe (plus rapide / plus lent), liste « À traiter maintenant » (retards en premier) et liste des tickets résolus (délai, dans les temps / hors délai, note).
- Mêmes définitions et mêmes chiffres que les Rapports globaux (`services/reporting.py`) ; « résolus » selon la date de résolution, « en cours / en retard » = situation du jour.
- **Podium** conservé : les 3 agents ayant résolu le plus de tickets, en grandes cartes cliquables (résolus, délai moyen, respect du SLA).
- Pas d'encadré d'explication : chaque colonne a une info-bulle (survol du « i »), y compris la règle de la colonne Situation.
- Animations rétablies : entrées en cascade (podium, tuiles, tableau), survol du podium (élévation, anneau dégradé, avatar, rang) et des lignes (décalage, flèche animée, accent de couleur). Mêmes entrées et survols sur les Rapports globaux (cartes d'indicateurs, barres qui se remplissent, cartes de chaleur). Respecte « réduire les animations » du système.
- Suppression des taux ambigus et des tris/recherches complexes ; période : 7 j, 30 j, 90 j, 12 mois.

## [2.6.0] - 2026-10-20

### 📊 Rapports globaux entièrement repensés
- **10 indicateurs** avec évolution par rapport à la période précédente de même durée : tickets créés, résolus, en attente, en retard (SLA), taux de résolution, conformité SLA, 1ère réponse, résolution (moyenne + médiane), satisfaction, réouvertures.
- **Filtres** combinables : période (7 j, 30 j, 90 j, 12 mois ou dates personnalisées), département, point de vente, type, priorité, agent. Tous les chiffres, l'export et les liens suivent les filtres.
- **Nouveaux graphiques et tableaux** : courbe créés/résolus (par jour ou par semaine), statut, type, priorité (créés vs en attente), ancienneté des tickets en attente, carte de chaleur jour × heure (planification des équipes), performance par département (volumes, retards, délai, SLA, satisfaction), catégories les plus fréquentes (délai prévu vs réel), points de vente les plus actifs, agents, tickets en retard à traiter en priorité (liens directs), satisfaction (répartition + commentaires).
- **Export CSV** enrichi (point de vente, échéance SLA, 1ère réponse, durée de résolution, SLA respecté) et filtré comme le rapport ; séparateur `;` (ouverture directe dans Excel en français). Bouton **Imprimer / PDF** (mise en page d'impression dédiée).
- Correction : les boutons de période de l'ancienne page ne changeaient rien (paramètre mal nommé).
- `/rapports/satisfaction-client` (page vide) redirige vers la section Satisfaction du rapport global.
- Nouveau module `services/reporting.py` ; aucune nouvelle table.

## [2.5.1] - 2026-10-20

### 🗂️ Gestion complète des catégories de tickets
- Page *Catégories de tickets* : colonnes Type, Département (vis-à-vis), Priorité, Délai de résolution, Nombre de tickets, Statut ; recherche et filtres (type, département, statut) ; tri.
- Actions : **Créer, Modifier, Activer/Désactiver, Archiver/Restaurer, Supprimer** (suppression refusée si des tickets utilisent la catégorie : l'archivage conserve l'historique). Nom unique par département.
- Nouvelle colonne `categories_tickets.archivee` (créée automatiquement). Une catégorie archivée ou désactivée disparaît du formulaire de ticket mais reste visible sur les tickets existants.
- **Permission `admin.categories`** (« Gérer les catégories de tickets », créée automatiquement) attribuable à n'importe quel rôle depuis *Rôles & permissions* : les rôles qui l'ont voient un bouton **Gérer les catégories** sur la page *Nouveau ticket*.

## [2.5.0] - 2026-10-19

### 🚀 Déploiement sur serveur Ubuntu
- **`deploy/install.sh`** : installateur / mise à jour en une commande (`sudo bash deploy/install.sh`) — installe Python, PostgreSQL, Nginx et Certbot, crée la base et le `.env` (mots de passe et clé secrète générés), restaure éventuellement votre base et vos fichiers, crée le service systemd, configure Nginx (50 Mo d'envoi), le pare-feu (SSH, 80, 443) et le HTTPS Let's Encrypt, et programme des sauvegardes quotidiennes. Relançable sans danger ; les relances suivantes mettent simplement à jour.
- **`deploy/backup.sh`** : sauvegarde de la base et des fichiers envoyés (14 jours conservés).
- **`DEPLOYMENT_GUIDE.md`** : guide pas à pas, avec dépannage.
- **Reverse proxy** : option `BEHIND_PROXY=true` (`ProxyFix`) pour que l'application voie la vraie adresse IP, le HTTPS et le nom d'hôte derrière Nginx.
- `.gitattributes` : les scripts `.sh` gardent des fins de ligne Unix.

## [2.4.4] - 2026-10-19

### 🔍 Revue visuelle des pages restantes
- **Info-bulles** : la bulle est désormais dessinée dans un calque flottant (`static/js/tooltip.js`) ; elle n'est plus rognée par les cartes en `overflow: hidden` (rapports), reste dans la fenêtre, se place sous l'icône s'il n'y a pas de place au-dessus, et s'affiche aussi dans les fenêtres modales (`<dialog>`).
- **Performance des agents** : seuls les vrais agents sont classés (rôle autorisé à modifier/clôturer, ou tickets assignés) au lieu des 69 utilisateurs ; le podium n'apparaît que si des tickets ont été résolus ; « — » au lieu d'un « 0 % » rouge pour un agent sans ticket.
- **Administration** : le bandeau d'état est réel (requête de test sur la base avec latence, e-mail configuré, dossier d'envoi accessible) ; « Connectée » était affiché même base arrêtée.
- **Accès à distance** : la page semblait vide (filtre « Avec identifiant » alors que personne n'a d'identifiant) → bascule sur « Tous » et message explicatif ; grille qui passe à la ligne au lieu d'une seule rangée à défilement horizontal.
- **Paramètres système** : cases TLS/SSL alignées ; bouton **« Envoyer un e-mail de test »** (connexion, authentification et envoi à l'administrateur, avec un message d'erreur explicite).
- **Logs système** : une entrée par ligne (les lignes étaient collées après le passage à la lecture par la fin du fichier).
- **Sécurité du compte** : la carte « Sessions actives » affiche le navigateur et le système réels, l'adresse IP et l'heure de connexion (textes génériques auparavant).
- **Notifications** : styles appliqués (le bloc `<style>` était hors de tout bloc et ignoré), champ `type_notification` correct, titre cliquable vers le ticket ou la messagerie.
- **Base de connaissance** : icônes `settings`, `shield`, `tool` des catégories enregistrées en base désormais affichées.

## [2.4.3] - 2026-10-19

### 💬 Messagerie, badges, SLA
- **Pièces jointes dans la messagerie** : bouton trombone (fichier ou image, n'importe quel type, 25 Mo max), aperçu avant envoi, glisser-déposer et collage d'image. Les fichiers sont enregistrés en base (colonnes `fichier_nom`, `fichier_chemin`, `fichier_type`, `fichier_taille` de `messages`) et sur disque dans `instance/chat_files/` (hors dossier public) ; ils sont servis par `/chat/fichier/<id>` uniquement à l'expéditeur et au destinataire. Les images s'affichent dans la conversation, les autres fichiers sont téléchargés.
- **Badges de la barre latérale** : « Tous les tickets » = nombre de tickets que l'utilisateur n'a pas encore ouverts ; « Messagerie » = nombre de messages non lus (chiffre, plus un simple point).
- **Notifications** : retour à une interrogation toutes les 2,5 secondes.
- **SLA** : info-bulle explicative (au-dessus du libellé) sur les SLA de réponse / résolution (formulaire et fiche département), la conformité SLA (rapports) et l'échéance d'un ticket ; le formulaire département permet maintenant de saisir les deux SLA ; **SLA de résolution par défaut : 24 h** (les 9 départements existants, restés à 48 h, passent à 24 h). Le ticket affiche « SLA respecté / dépassé » une fois résolu.
- Contraste de la barre d'actions groupées de la liste des tickets.

## [2.4.2] - 2026-10-19

### 🔎 Revue page par page de la navigation
- **Liste des tickets** : les actions groupées (« Changer le statut », « Assigner à ») fonctionnent (`POST /tickets/bulk`, droits vérifiés ticket par ticket, historique et notifications) ; filtres **Fermé** et **Annulé** ; **recherche** par numéro (`#12`), titre ou description.
- **Satisfaction** : le créateur peut noter (1 à 5) et commenter un ticket résolu ou fermé (`POST /tickets/<id>/evaluer`) ; sans cela le rapport « Satisfaction client » ne pouvait jamais contenir de données.
- **Rapports** : durées moyennes affichées correctement (elles étaient stockées en minutes mais affichées comme des heures : 90 min s'affichait « 90 h ») ; « — » au lieu de « 0 % » / « 0/5 » lorsqu'il n'y a aucune donnée.
- **SLA des départements** : sans délai de catégorie, l'échéance d'un ticket est calculée avec le SLA de résolution du département (il n'était jamais utilisé).
- **Messagerie** : une seule adresse (`/chat/`, l'ancienne `/tickets/chat` redirige) ; menu actif correct ; contact fictif « Amine Larbi » retiré ; boutons sans fonction (« Supprimer la conversation », pièce jointe) retirés.
- **Notifications** : interrogation toutes les 15 s (2,5 s auparavant) et suspendue quand l'onglet est masqué ; le badge de « Tous les tickets » ne compte plus que les notifications de tickets.
- **Profil** : sélecteur de langue (sans effet, rien n'est traduit) remplacé par l'option **notifications par e-mail**, désormais respectée à l'envoi.
- **Annuaire** : filtre par point de vente. **Formulaires de ticket** : limites de longueur, description obligatoire, types de fichiers alignés sur le serveur (`.log` était proposé mais refusé).
- **Fichiers** : seules les images s'affichent dans le navigateur, les autres types (PDF, Office, ZIP) sont téléchargés.
- **Données** : descriptions des rôles passées en français.
- **Retiré** : pages `/tickets/faq` (contenu codé en dur, non liées), texte d'accueil des entreprises avec noms codés en dur.
- **Accessibilité** : lignes et cartes cliquables utilisables au clavier (Entrée / Espace), boutons-icônes nommés (`static/js/a11y.js`).

## [2.4.1] - 2026-10-19

### 🏪 Points de vente : tout vient de la base
- Aucune nouvelle table : la catégorie et la couleur de chaque PDV restent dans `points_de_vente` (`categorie`, `couleur`) ; les listes de choix (catégories avec description et icône, palette de 11 couleurs) sont stockées en JSON dans la table existante `configurations_systeme` (clés `pdv_categories` et `pdv_themes`), amorcées une seule fois avec les valeurs historiques puis gérées en base.
- La page des PDV (filtres, icônes, palette rapide de chaque carte) et le formulaire de création/modification lisent ces listes via un cache ; plus aucune liste codée en dur dans les gabarits.
- Nouvelle page **Catégories & thèmes** (`/pdv/referentiels`, permissions `pdv.modifier` / `pdv.gerer` ou niveau ≥ 90) : ajout, modification, désactivation et suppression des catégories (refusée si des PDV l'utilisent), ajout / retrait de couleurs.
- Une catégorie « personnalisée » saisie dans le formulaire est enregistrée automatiquement dans les catégories en base.
- Cache mémoire des référentiels (`services/referentiels.py`, TTL 5 min), vidé à chaque modification.
- Chaque PDV a désormais sa propre couleur de thème en base (8 PDV, 8 couleurs).
- Corrigé : le changement de thème depuis la carte n'était pas enregistré (mauvaise URL `/pdvs/...`) ; coche de la couleur active ; les champs vides des formulaires PDV / entreprises affichaient « None ».

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
