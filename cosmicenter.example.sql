-- =============================================================================
--  CosmiCenter — EXEMPLE de création de la base de données (PostgreSQL 14+) : structure, permissions, rôles et données d'exemple
--  Généré à partir de models.py (APP_VERSION 2.7.2). Données entièrement fictives (@example.com) + un compte Super Administrateur par défaut.
--  (Même principe que .env.example : on copie, on adapte, on exécute. La vraie base avec ses données
--   est dans cosmicenter.sql, fichier local ignoré par git.)
--
--  Contenu :
--    0. Rôle et base PostgreSQL            (à exécuter en superutilisateur, base « postgres »)
--    1. Tables, clés, contraintes, index
--    2. Séquence des numéros de ticket     (ticket_numero_seq)
--    3. Permissions, 6 rôles standard et leurs droits (les « policies » de l'application), réglages par défaut
--    3b. Données d'exemple fictives et compte Super Administrateur par défaut (admin@example.com)
--    4. Droits PostgreSQL du rôle applicatif
--
--  Utilisation :
--    1. Mot de passe d'exemple : testtest (à changer en production) puis :  psql -U postgres -f cosmicenter.example.sql
--    2. Se connecter avec le compte par défaut (voir section 3b) et CHANGER LE MOT DE PASSE immédiatement.
-- =============================================================================


-- ───────────────────────────── 0. Rôle et base PostgreSQL ─────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'cosmicenter') THEN
        CREATE ROLE cosmicenter LOGIN PASSWORD 'testtest';
    END IF;
END
$$;

SELECT 'CREATE DATABASE cosmicenter OWNER cosmicenter ENCODING ''UTF8'''
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'cosmicenter')\gexec

\connect cosmicenter

SET client_encoding = 'UTF8';

-- ───────────────────────────── 1. Tables, clés, contraintes, index ─────────────────────────────

BEGIN;

CREATE TABLE categories_connaissance (
	id VARCHAR(36) NOT NULL, 
	nom VARCHAR(100) NOT NULL, 
	description TEXT, 
	icone VARCHAR(50), 
	date_creation TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE configurations_systeme (
	cle VARCHAR(100) NOT NULL, 
	valeur TEXT NOT NULL, 
	description VARCHAR(255), 
	date_mise_a_jour TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (cle)
);

CREATE TABLE departements (
	id VARCHAR(36) NOT NULL, 
	nom VARCHAR(100) NOT NULL, 
	code VARCHAR(20), 
	description TEXT, 
	email VARCHAR(120), 
	telephone VARCHAR(20), 
	localisation VARCHAR(200), 
	couleur VARCHAR(20), 
	icone VARCHAR(50), 
	responsable_id VARCHAR(36), 
	sla_reponse_heures INTEGER, 
	sla_resolution_heures INTEGER, 
	horaires_travail JSON, 
	actif BOOLEAN, 
	date_creation TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (nom), 
	UNIQUE (code)
);

CREATE INDEX ix_departements_responsable_id ON departements (responsable_id);

CREATE TABLE entreprises (
	id VARCHAR(36) NOT NULL, 
	nom VARCHAR(100) NOT NULL, 
	code VARCHAR(20), 
	description TEXT, 
	type_entreprise VARCHAR(50), 
	email VARCHAR(120), 
	telephone VARCHAR(20), 
	adresse TEXT, 
	site_web VARCHAR(200), 
	couleur VARCHAR(30), 
	logo VARCHAR(255), 
	actif BOOLEAN, 
	date_creation TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (nom), 
	UNIQUE (code)
);

CREATE TABLE permissions (
	id VARCHAR(36) NOT NULL, 
	code VARCHAR(100) NOT NULL, 
	nom VARCHAR(100) NOT NULL, 
	description TEXT, 
	categorie VARCHAR(50), 
	date_creation TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

CREATE TABLE points_de_vente (
	id VARCHAR(36) NOT NULL, 
	nom VARCHAR(100) NOT NULL, 
	adresse TEXT, 
	telephone VARCHAR(20), 
	email VARCHAR(120), 
	localisation VARCHAR(200), 
	categorie VARCHAR(50), 
	responsable_id VARCHAR(36), 
	actif BOOLEAN, 
	couleur VARCHAR(30), 
	date_creation TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (nom)
);

CREATE INDEX ix_points_de_vente_responsable_id ON points_de_vente (responsable_id);

CREATE TABLE roles (
	id VARCHAR(36) NOT NULL, 
	nom VARCHAR(100) NOT NULL, 
	description TEXT, 
	couleur VARCHAR(20), 
	niveau INTEGER, 
	systeme BOOLEAN, 
	actif BOOLEAN, 
	date_creation TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (nom)
);

CREATE TABLE utilisateurs (
	id VARCHAR(36) NOT NULL, 
	nom VARCHAR(100) NOT NULL, 
	prenom VARCHAR(100) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	mot_de_passe_hash VARCHAR(255) NOT NULL, 
	telephone VARCHAR(20), 
	poste VARCHAR(100), 
	matricule VARCHAR(50), 
	photo_profil VARCHAR(255), 
	anydesk_id VARCHAR(50), 
	anydesk_password TEXT, 
	teamviewer_id VARCHAR(50), 
	teamviewer_password TEXT, 
	poste_machine VARCHAR(100), 
	role_id VARCHAR(36), 
	departement_id VARCHAR(36), 
	pdv_id VARCHAR(36), 
	entreprise_id VARCHAR(36), 
	langue VARCHAR(10), 
	theme VARCHAR(20), 
	couleur VARCHAR(20), 
	notifications_email BOOLEAN, 
	notifications_push BOOLEAN, 
	actif BOOLEAN, 
	verrouille BOOLEAN, 
	date_verrouillage TIMESTAMP WITHOUT TIME ZONE, 
	session_version INTEGER DEFAULT '0' NOT NULL, 
	tentatives_connexion INTEGER, 
	date_creation TIMESTAMP WITHOUT TIME ZONE, 
	derniere_connexion TIMESTAMP WITHOUT TIME ZONE, 
	derniere_activite TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (matricule)
);

CREATE INDEX ix_utilisateurs_departement_id ON utilisateurs (departement_id);

CREATE UNIQUE INDEX ix_utilisateurs_email ON utilisateurs (email);

CREATE INDEX ix_utilisateurs_entreprise_id ON utilisateurs (entreprise_id);

CREATE INDEX ix_utilisateurs_pdv_id ON utilisateurs (pdv_id);

CREATE INDEX ix_utilisateurs_role_id ON utilisateurs (role_id);

CREATE TABLE articles_connaissance (
	id VARCHAR(36) NOT NULL, 
	titre VARCHAR(255) NOT NULL, 
	contenu TEXT NOT NULL, 
	categorie_id VARCHAR(36) NOT NULL, 
	auteur_id VARCHAR(36) NOT NULL, 
	date_creation TIMESTAMP WITHOUT TIME ZONE, 
	date_mise_a_jour TIMESTAMP WITHOUT TIME ZONE, 
	vues INTEGER, 
	statut VARCHAR(20), 
	PRIMARY KEY (id), 
	FOREIGN KEY(categorie_id) REFERENCES categories_connaissance (id) ON DELETE CASCADE, 
	FOREIGN KEY(auteur_id) REFERENCES utilisateurs (id) ON DELETE CASCADE
);

CREATE TABLE categories_tickets (
	id VARCHAR(36) NOT NULL, 
	nom VARCHAR(100) NOT NULL, 
	description TEXT, 
	type_ticket VARCHAR(20), 
	departement_id VARCHAR(36) NOT NULL, 
	priorite_defaut VARCHAR(20), 
	delai_resolution_jours INTEGER, 
	etapes_workflow JSON, 
	auto_assignation BOOLEAN, 
	couleur VARCHAR(20), 
	icone VARCHAR(50), 
	formulaire_personnalise JSON, 
	actif BOOLEAN, 
	archivee BOOLEAN DEFAULT false NOT NULL, 
	date_creation TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(departement_id) REFERENCES departements (id) ON DELETE CASCADE
);

CREATE INDEX ix_categories_tickets_departement_id ON categories_tickets (departement_id);

CREATE TABLE equipements (
	id VARCHAR(36) NOT NULL, 
	pdv_id VARCHAR(36) NOT NULL, 
	type_equipement VARCHAR(50) NOT NULL, 
	marque VARCHAR(100), 
	modele VARCHAR(100), 
	numero_serie VARCHAR(100), 
	adresse_ip VARCHAR(50), 
	adresse_mac VARCHAR(50), 
	statut VARCHAR(20), 
	date_installation TIMESTAMP WITHOUT TIME ZONE, 
	notes TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(pdv_id) REFERENCES points_de_vente (id) ON DELETE CASCADE, 
	UNIQUE (numero_serie)
);

CREATE INDEX ix_equipements_pdv_id ON equipements (pdv_id);

CREATE TABLE messages (
	id VARCHAR(36) NOT NULL, 
	sender_id VARCHAR(36) NOT NULL, 
	receiver_id VARCHAR(36) NOT NULL, 
	content TEXT NOT NULL, 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	is_read BOOLEAN, 
	fichier_nom VARCHAR(255), 
	fichier_chemin VARCHAR(100), 
	fichier_type VARCHAR(150), 
	fichier_taille INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sender_id) REFERENCES utilisateurs (id) ON DELETE CASCADE, 
	FOREIGN KEY(receiver_id) REFERENCES utilisateurs (id) ON DELETE CASCADE
);

CREATE INDEX ix_messages_receiver_id ON messages (receiver_id);

CREATE INDEX ix_messages_sender_id ON messages (sender_id);

CREATE INDEX ix_messages_timestamp ON messages (timestamp);

CREATE TABLE notifications (
	id VARCHAR(36) NOT NULL, 
	utilisateur_id VARCHAR(36) NOT NULL, 
	titre VARCHAR(200) NOT NULL, 
	message TEXT, 
	type_notification VARCHAR(50), 
	lien VARCHAR(500), 
	lue BOOLEAN, 
	date_creation TIMESTAMP WITHOUT TIME ZONE, 
	date_lecture TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(utilisateur_id) REFERENCES utilisateurs (id) ON DELETE CASCADE
);

CREATE INDEX ix_notifications_utilisateur_id ON notifications (utilisateur_id);

CREATE TABLE plan_action_tasks (
	id VARCHAR(36) NOT NULL, 
	titre VARCHAR(200) NOT NULL, 
	description TEXT, 
	statut VARCHAR(50), 
	urgent BOOLEAN, 
	date_debut TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	date_fin TIMESTAMP WITHOUT TIME ZONE, 
	createur_id VARCHAR(36) NOT NULL, 
	assigne_a_id VARCHAR(36), 
	PRIMARY KEY (id), 
	FOREIGN KEY(createur_id) REFERENCES utilisateurs (id) ON DELETE CASCADE, 
	FOREIGN KEY(assigne_a_id) REFERENCES utilisateurs (id) ON DELETE SET NULL
);

CREATE TABLE roles_permissions (
	role_id VARCHAR(36) NOT NULL, 
	permission_id VARCHAR(36) NOT NULL, 
	PRIMARY KEY (role_id, permission_id), 
	FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE, 
	FOREIGN KEY(permission_id) REFERENCES permissions (id) ON DELETE CASCADE
);

CREATE INDEX ix_roles_permissions_permission_id ON roles_permissions (permission_id);

CREATE INDEX ix_roles_permissions_role_id ON roles_permissions (role_id);

CREATE TABLE suggestions (
	id VARCHAR(36) NOT NULL, 
	titre VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	type_suggestion VARCHAR(50), 
	statut VARCHAR(50), 
	auteur_id VARCHAR(36) NOT NULL, 
	date_creation TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(auteur_id) REFERENCES utilisateurs (id) ON DELETE CASCADE
);

CREATE TABLE articles_connaissance_vues (
	id VARCHAR(36) NOT NULL, 
	article_id VARCHAR(36) NOT NULL, 
	utilisateur_id VARCHAR(36) NOT NULL, 
	nb_vues INTEGER NOT NULL, 
	premiere_vue TIMESTAMP WITHOUT TIME ZONE, 
	derniere_vue TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_article_vue_user UNIQUE (article_id, utilisateur_id), 
	FOREIGN KEY(article_id) REFERENCES articles_connaissance (id) ON DELETE CASCADE, 
	FOREIGN KEY(utilisateur_id) REFERENCES utilisateurs (id) ON DELETE CASCADE
);

CREATE INDEX ix_articles_connaissance_vues_article_id ON articles_connaissance_vues (article_id);

CREATE TABLE modeles_reponses (
	id VARCHAR(36) NOT NULL, 
	titre VARCHAR(200) NOT NULL, 
	contenu TEXT NOT NULL, 
	categorie_id VARCHAR(36), 
	departement_id VARCHAR(36), 
	public BOOLEAN, 
	createur_id VARCHAR(36), 
	utilisation_count INTEGER, 
	date_creation TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(categorie_id) REFERENCES categories_tickets (id) ON DELETE CASCADE, 
	FOREIGN KEY(departement_id) REFERENCES departements (id) ON DELETE CASCADE, 
	FOREIGN KEY(createur_id) REFERENCES utilisateurs (id) ON DELETE SET NULL
);

CREATE INDEX ix_modeles_reponses_categorie_id ON modeles_reponses (categorie_id);

CREATE INDEX ix_modeles_reponses_createur_id ON modeles_reponses (createur_id);

CREATE INDEX ix_modeles_reponses_departement_id ON modeles_reponses (departement_id);

CREATE TABLE statistiques (
	id VARCHAR(36) NOT NULL, 
	date DATE NOT NULL, 
	type_stat VARCHAR(50) NOT NULL, 
	valeur INTEGER, 
	valeur_float FLOAT, 
	departement_id VARCHAR(36), 
	categorie_id VARCHAR(36), 
	meta_data JSON, 
	PRIMARY KEY (id), 
	FOREIGN KEY(departement_id) REFERENCES departements (id) ON DELETE CASCADE, 
	FOREIGN KEY(categorie_id) REFERENCES categories_tickets (id) ON DELETE CASCADE
);

CREATE INDEX ix_statistiques_categorie_id ON statistiques (categorie_id);

CREATE INDEX ix_statistiques_departement_id ON statistiques (departement_id);

CREATE TABLE tickets (
	id VARCHAR(36) NOT NULL, 
	numero VARCHAR(20) NOT NULL, 
	titre VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	type_ticket VARCHAR(20) NOT NULL, 
	priorite VARCHAR(20), 
	statut VARCHAR(20), 
	impact VARCHAR(20), 
	urgence VARCHAR(20), 
	createur_id VARCHAR(36) NOT NULL, 
	assigne_a_id VARCHAR(36), 
	categorie_id VARCHAR(36), 
	departement_id VARCHAR(36), 
	pdv_id VARCHAR(36), 
	date_creation TIMESTAMP WITHOUT TIME ZONE, 
	date_modification TIMESTAMP WITHOUT TIME ZONE, 
	date_echeance TIMESTAMP WITHOUT TIME ZONE, 
	date_premiere_reponse TIMESTAMP WITHOUT TIME ZONE, 
	date_resolution TIMESTAMP WITHOUT TIME ZONE, 
	date_fermeture TIMESTAMP WITHOUT TIME ZONE, 
	sla_respecte BOOLEAN, 
	temps_premiere_reponse_minutes INTEGER, 
	temps_resolution_minutes INTEGER, 
	satisfaction INTEGER, 
	commentaire_satisfaction TEXT, 
	article_demande VARCHAR(200), 
	quantite_demandee INTEGER, 
	unite VARCHAR(50), 
	nature_besoin VARCHAR(200), 
	justification TEXT, 
	personne_concernee VARCHAR(200), 
	date_incident TIMESTAMP WITHOUT TIME ZONE, 
	lieu_incident VARCHAR(200), 
	donnees_personnalisees JSON, 
	tags JSON, 
	PRIMARY KEY (id), 
	FOREIGN KEY(createur_id) REFERENCES utilisateurs (id) ON DELETE RESTRICT, 
	FOREIGN KEY(assigne_a_id) REFERENCES utilisateurs (id) ON DELETE SET NULL, 
	FOREIGN KEY(categorie_id) REFERENCES categories_tickets (id) ON DELETE SET NULL, 
	FOREIGN KEY(departement_id) REFERENCES departements (id) ON DELETE SET NULL, 
	FOREIGN KEY(pdv_id) REFERENCES points_de_vente (id) ON DELETE SET NULL
);

CREATE INDEX ix_tickets_assigne_a_id ON tickets (assigne_a_id);

CREATE INDEX ix_tickets_categorie_id ON tickets (categorie_id);

CREATE INDEX ix_tickets_createur_id ON tickets (createur_id);

CREATE INDEX ix_tickets_departement_id ON tickets (departement_id);

CREATE UNIQUE INDEX ix_tickets_numero ON tickets (numero);

CREATE INDEX ix_tickets_pdv_id ON tickets (pdv_id);

CREATE TABLE commentaires (
	id VARCHAR(36) NOT NULL, 
	ticket_id VARCHAR(36) NOT NULL, 
	auteur_id VARCHAR(36) NOT NULL, 
	contenu TEXT NOT NULL, 
	interne BOOLEAN, 
	type_commentaire VARCHAR(20), 
	date_creation TIMESTAMP WITHOUT TIME ZONE, 
	date_modification TIMESTAMP WITHOUT TIME ZONE, 
	modifie BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id) ON DELETE CASCADE, 
	FOREIGN KEY(auteur_id) REFERENCES utilisateurs (id) ON DELETE CASCADE
);

CREATE INDEX ix_commentaires_auteur_id ON commentaires (auteur_id);

CREATE INDEX ix_commentaires_ticket_id ON commentaires (ticket_id);

CREATE TABLE historique_tickets (
	id VARCHAR(36) NOT NULL, 
	ticket_id VARCHAR(36) NOT NULL, 
	utilisateur_id VARCHAR(36), 
	action VARCHAR(100) NOT NULL, 
	details TEXT, 
	champ_modifie VARCHAR(100), 
	ancienne_valeur TEXT, 
	nouvelle_valeur TEXT, 
	date_creation TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id) ON DELETE CASCADE, 
	FOREIGN KEY(utilisateur_id) REFERENCES utilisateurs (id) ON DELETE SET NULL
);

CREATE INDEX ix_historique_tickets_ticket_id ON historique_tickets (ticket_id);

CREATE INDEX ix_historique_tickets_utilisateur_id ON historique_tickets (utilisateur_id);

CREATE TABLE taches (
	id VARCHAR(36) NOT NULL, 
	ticket_id VARCHAR(36) NOT NULL, 
	titre VARCHAR(200) NOT NULL, 
	description TEXT, 
	assigne_a_id VARCHAR(36), 
	terminee BOOLEAN, 
	ordre INTEGER, 
	date_creation TIMESTAMP WITHOUT TIME ZONE, 
	date_echeance TIMESTAMP WITHOUT TIME ZONE, 
	date_completion TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id) ON DELETE CASCADE, 
	FOREIGN KEY(assigne_a_id) REFERENCES utilisateurs (id) ON DELETE SET NULL
);

CREATE INDEX ix_taches_assigne_a_id ON taches (assigne_a_id);

CREATE INDEX ix_taches_ticket_id ON taches (ticket_id);

CREATE TABLE ticket_collaborateurs (
	ticket_id VARCHAR(36) NOT NULL, 
	utilisateur_id VARCHAR(36) NOT NULL, 
	PRIMARY KEY (ticket_id, utilisateur_id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id) ON DELETE CASCADE, 
	FOREIGN KEY(utilisateur_id) REFERENCES utilisateurs (id) ON DELETE CASCADE
);

CREATE INDEX ix_ticket_collaborateurs_ticket_id ON ticket_collaborateurs (ticket_id);

CREATE INDEX ix_ticket_collaborateurs_utilisateur_id ON ticket_collaborateurs (utilisateur_id);

CREATE TABLE ticket_departements_collab (
	ticket_id VARCHAR(36) NOT NULL, 
	departement_id VARCHAR(36) NOT NULL, 
	PRIMARY KEY (ticket_id, departement_id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id) ON DELETE CASCADE, 
	FOREIGN KEY(departement_id) REFERENCES departements (id) ON DELETE CASCADE
);

CREATE INDEX ix_ticket_departements_collab_departement_id ON ticket_departements_collab (departement_id);

CREATE INDEX ix_ticket_departements_collab_ticket_id ON ticket_departements_collab (ticket_id);

CREATE TABLE pieces_jointes (
	id VARCHAR(36) NOT NULL, 
	ticket_id VARCHAR(36) NOT NULL, 
	commentaire_id VARCHAR(36), 
	nom_fichier VARCHAR(255) NOT NULL, 
	nom_original VARCHAR(255) NOT NULL, 
	type_mime VARCHAR(100), 
	taille INTEGER, 
	chemin VARCHAR(500) NOT NULL, 
	miniature VARCHAR(500), 
	date_upload TIMESTAMP WITHOUT TIME ZONE, 
	uploade_par_id VARCHAR(36), 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id) ON DELETE CASCADE, 
	FOREIGN KEY(commentaire_id) REFERENCES commentaires (id) ON DELETE CASCADE, 
	FOREIGN KEY(uploade_par_id) REFERENCES utilisateurs (id) ON DELETE SET NULL
);

CREATE INDEX ix_pieces_jointes_commentaire_id ON pieces_jointes (commentaire_id);

CREATE INDEX ix_pieces_jointes_ticket_id ON pieces_jointes (ticket_id);

CREATE INDEX ix_pieces_jointes_uploade_par_id ON pieces_jointes (uploade_par_id);

ALTER TABLE utilisateurs ADD FOREIGN KEY(departement_id) REFERENCES departements (id) ON DELETE SET NULL;

ALTER TABLE points_de_vente ADD FOREIGN KEY(responsable_id) REFERENCES utilisateurs (id) ON DELETE SET NULL;

ALTER TABLE utilisateurs ADD FOREIGN KEY(entreprise_id) REFERENCES entreprises (id) ON DELETE SET NULL;

ALTER TABLE departements ADD FOREIGN KEY(responsable_id) REFERENCES utilisateurs (id) ON DELETE SET NULL;

ALTER TABLE utilisateurs ADD FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE SET NULL;

ALTER TABLE utilisateurs ADD FOREIGN KEY(pdv_id) REFERENCES points_de_vente (id) ON DELETE SET NULL;

-- ───────────────────────────── 2. Numéros de ticket (séquence atomique) ─────────────────────────────
CREATE SEQUENCE IF NOT EXISTS ticket_numero_seq START 1;

-- ───────────────────────────── 3. Données ─────────────────────────────

-- permissions (62)
INSERT INTO permissions (id, code, nom, description, categorie, date_creation) VALUES
    ('eca5c65c-7f64-4b51-9d5c-6dac181b0d17', 'admin_acces.voir', 'Accès à distance', 'Consulter les identifiants AnyDesk et TeamViewer', 'Administration', '2026-10-12 14:08:13.094182'),
    ('f2c94810-a8ce-44d8-aa2e-50bffefb5d72', 'admin_dashboard.voir', 'Panneau d''administration', 'Accéder au panneau d''administration', 'Administration', '2026-10-12 14:08:13.094182'),
    ('4458e877-8c1d-4a39-925c-a015768a5e33', 'admin_logs.voir', 'Journaux d''activité (Logs)', 'Consulter les journaux d''audit et de sécurité', 'Administration', '2026-10-12 14:08:13.094182'),
    ('047b5e23-7c1a-40d0-b542-aa8fccfaac24', 'admin_parametres.modifier', 'Gérer les paramètres', 'Modifier les paramètres généraux de l''application', 'Administration', '2026-10-12 14:08:13.094182'),
    ('03df436b-4b5a-44a9-8895-1b688826ba95', 'admin_parametres.voir', 'Paramètres système', 'Consulter les configurations système', 'Administration', '2026-10-12 14:08:13.094182'),
    ('46cb6df9-e867-4317-a18e-eea031166daa', 'admin_roles.modifier', 'Gérer les rôles', 'Créer et modifier des rôles personnalisés', 'Administration', '2026-10-12 14:08:13.094182'),
    ('fab745cf-d748-4a09-b749-a62b78ea48b5', 'admin_roles.voir', 'Rôles et permissions', 'Consulter les rôles et permissions', 'Administration', '2026-10-12 14:08:13.094182'),
    ('0734078e-c4a6-4701-a62b-0f4aac08f0b4', 'admin.categories', 'Gérer les catégories de tickets', 'Créer, modifier, activer, archiver et supprimer les catégories (incidents, demandes...). Ajoute un bouton « Gérer les catégories » sur la page Nouveau ticket.', 'Espace de travail', '2026-10-20 15:40:31.246410'),
    ('a3cb7466-d4fe-4627-9f07-9320542c734a', 'dashboard.voir', 'Tableau de bord', 'Afficher le tableau de bord', 'Espace de travail', '2026-10-12 14:08:13.094182'),
    ('b2216d1a-0fcc-48f6-aa68-a63492d08a6a', 'idees.creer', 'Proposer une idée', 'Envoyer une nouvelle idée / suggestion (bug, amélioration, nouvelle fonctionnalité).', 'Espace de travail', '2026-10-27 10:30:17.162171'),
    ('62986ebe-50dd-47dc-b307-a1dc99e1a5a6', 'idees.modifier', 'Traiter / changer le statut d''une idée', 'Marquer une idée comme lue, acceptée, refusée, en cours ou terminée.', 'Espace de travail', '2026-10-27 10:30:17.165191'),
    ('4e3a55ef-5e25-4fa3-9522-2b93b2816ab9', 'idees.supprimer', 'Supprimer une idée', 'Supprimer définitivement une idée.', 'Espace de travail', '2026-10-27 10:30:17.166189'),
    ('5c82af9d-26de-404c-a7fe-735f0ebc074b', 'idees.voir', 'Boîte à idées', 'Accéder à la boîte à idées', 'Espace de travail', '2026-10-12 14:08:13.094182'),
    ('04431d31-90c7-45f0-a41e-721301a84aee', 'idees.voir_toutes', 'Voir les idées de tout le monde', 'Voir toutes les idées envoyées (sinon : seulement les siennes) et être prévenu par e-mail des nouvelles idées.', 'Espace de travail', '2026-10-27 10:30:17.164200'),
    ('0340e75f-53aa-4f0f-99db-02eb0e85b7b9', 'messagerie.voir', 'Messagerie', 'Accéder à la messagerie interne', 'Espace de travail', '2026-10-12 14:08:13.094182'),
    ('f484a0b5-5679-48c9-a238-1cf6ee2ebea2', 'tickets.assigner', 'Assigner un ticket', 'Assigner des tickets aux agents ou départements', 'Espace de travail', '2026-10-12 14:08:13.094182'),
    ('538f7e5b-c507-409e-8baf-173c3ed69e41', 'tickets.cloturer', 'Clôturer un ticket', 'Résoudre et fermer les tickets', 'Espace de travail', '2026-10-12 14:08:13.094182'),
    ('823251d4-bdbd-4d04-b787-a5c1483785f3', 'tickets.commenter', 'Commenter un ticket', 'Écrire des messages dans la conversation d''un ticket auquel on a accès.', 'Espace de travail', '2026-10-27 10:30:17.140296'),
    ('e3aac624-83c9-4bdf-b7f3-43ebd394e963', 'tickets.creer', 'Nouveau ticket', 'Créer de nouveaux tickets', 'Espace de travail', '2026-10-12 14:08:13.094182'),
    ('1ff3e383-385d-46b8-a5ca-c84a256117d4', 'tickets.modifier', 'Modifier un ticket', 'Modifier les tickets existants', 'Espace de travail', '2026-10-12 14:08:13.094182'),
    ('c6295f57-b5c6-4618-9347-20405e82bd94', 'tickets.supprimer', 'Supprimer un ticket', 'Supprimer des tickets', 'Espace de travail', '2026-10-12 14:08:13.094182'),
    ('f303b68b-e0b6-4125-b576-77cde8c58a5d', 'tickets.voir_mes', 'Mes tickets / Tickets département', 'Afficher les tickets du département ou assignés', 'Espace de travail', '2026-10-12 14:08:13.094182'),
    ('d0d355cb-14df-4d49-aa0d-fe404705a762', 'tickets.voir_tous', 'Tous les tickets', 'Visibilité globale sur tous les tickets', 'Espace de travail', '2026-10-12 14:08:13.094182'),
    ('6d59b369-aa13-4355-95a6-be43d539dd1f', 'rapports_globaux.exporter', 'Exporter les rapports (CSV)', 'Télécharger les données du rapport global au format CSV.', 'Intelligence', '2026-10-27 10:30:17.208021'),
    ('252ba45e-ddca-45de-b51c-270a9ef2d4e9', 'rapports_globaux.voir', 'Rapports globaux', 'Consulter les rapports et indicateurs clés', 'Intelligence', '2026-10-12 14:08:13.094182'),
    ('c5fba854-2afe-47fd-8803-dae1d38bcd0c', 'rapports_performance.voir', 'Performance des équipes', 'Consulter les métriques de performance des agents', 'Intelligence', '2026-10-12 14:08:13.094182'),
    ('7f033a77-2e01-4e61-a412-aad3bb42f94a', 'admin_plan_action.creer', 'Ajouter une tâche au plan d''action', 'Créer de nouvelles tâches dans le plan d''action.', 'Opérations', '2026-10-27 10:30:17.202453'),
    ('a49cc8ef-eced-4686-9d6a-9fe586e8c87b', 'admin_plan_action.exporter', 'Exporter le plan d''action (Excel)', 'Télécharger le plan d''action au format Excel.', 'Opérations', '2026-10-27 10:30:17.206360'),
    ('f15bac9a-9792-44c1-ba61-c88322775d2c', 'admin_plan_action.modifier', 'Modifier le plan d''action', 'Modifier les tâches du plan d''action', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('1d46e937-a5a0-4bcb-8fd4-d92f39464ef5', 'admin_plan_action.supprimer', 'Supprimer une tâche du plan d''action', 'Supprimer définitivement une tâche.', 'Opérations', '2026-10-27 10:30:17.204851'),
    ('fe09001e-2ab0-4217-b267-8982f5ff9bbf', 'admin_plan_action.voir', 'Plan d''action', 'Consulter le plan d''action', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('0f990f82-bff2-41b4-a175-d006e850efbb', 'base_connaissance.creer', 'Créer un article', 'Publier de nouveaux articles', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('e48ffc72-0527-4d5d-a591-6690f5d3b6cf', 'base_connaissance.gerer_categories', 'Gérer les catégories d''articles', 'Créer des catégories dans la base de connaissance.', 'Opérations', '2026-10-27 10:30:17.166189'),
    ('c60943aa-1a51-477b-883b-3bd05423232b', 'base_connaissance.modifier', 'Modifier un article', 'Modifier les articles existants', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('5f252230-6c03-46f3-98cd-29c56634aa67', 'base_connaissance.supprimer', 'Supprimer un article', 'Supprimer des articles ou des catégories', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('ad11f22c-0f46-4222-ab9a-215aa2b94cb7', 'base_connaissance.voir', 'Base de connaissance', 'Consulter les articles de la base de connaissance', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('d69631d5-9e40-41cb-88b7-fe15ad578855', 'base_connaissance.voir_lecteurs', 'Voir qui a lu un article', 'Afficher, au survol de l''œil, la liste des personnes qui ont lu l''article et combien de fois.', 'Opérations', '2026-10-27 10:30:17.167209'),
    ('00b215f5-f614-47d3-bfd5-53ec4e733e8c', 'departements.creer', 'Créer un département', 'Ajouter un nouveau département', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('606de1b2-b2b5-4917-b53e-2d9eca36c672', 'departements.gerer_membres', 'Gérer les membres d''un département', 'Ajouter ou retirer des membres dans un département.', 'Opérations', '2026-10-27 10:30:17.170263'),
    ('c31c0ecb-5a61-464d-b0b6-1a57eeca1710', 'departements.modifier', 'Modifier un département', 'Modifier les informations d''un département', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('396fb382-80c7-437f-904f-e1d38e988b27', 'departements.modifier_propre', 'Modifier son propre département', 'Modifier la fiche du département auquel on appartient (sans pouvoir modifier les autres).', 'Opérations', '2026-10-27 10:30:17.168201'),
    ('6a84c38c-ec5e-46f8-aa7e-28204f8b8a6e', 'departements.supprimer', 'Supprimer un département', 'Supprimer un département', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('22db6721-5e77-4cef-b984-a8177b9d6b01', 'departements.voir', 'Départements', 'Consulter la liste des départements', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('7c35eab4-c78b-47b8-a9b9-b46c3137bbc3', 'entreprises.archiver', 'Archiver / réactiver une entreprise', 'Masquer une entreprise sans la supprimer, ou la réactiver.', 'Opérations', '2026-10-27 10:30:17.182432'),
    ('be11e2a2-0302-4931-93de-57ad4633336f', 'entreprises.creer', 'Créer une entreprise', 'Ajouter une nouvelle entreprise ou partenaire', 'Opérations', '2026-10-14 11:25:47.774792'),
    ('ee32aa14-2688-4b0b-bc61-dec962fb405b', 'entreprises.gerer_collaborateurs', 'Rattacher / détacher des collaborateurs', 'Associer ou retirer des utilisateurs d''une entreprise.', 'Opérations', '2026-10-27 10:30:17.185458'),
    ('357a8c25-9946-4d0d-8f1d-03de9afa5ca8', 'entreprises.modifier', 'Modifier une entreprise', 'Modifier les informations d''une entreprise', 'Opérations', '2026-10-14 11:25:47.775796'),
    ('d2e43ce3-ca67-402a-9165-c6a94cef9679', 'entreprises.supprimer', 'Supprimer une entreprise', 'Archiver ou supprimer une entreprise', 'Opérations', '2026-10-14 11:25:47.775796'),
    ('3229a390-8f13-4bb3-91ce-4477fd560d2e', 'entreprises.voir', 'Entreprises', 'Consulter la liste des entreprises et partenaires', 'Opérations', '2026-10-14 11:25:47.759254'),
    ('16abbdbb-1a31-40bc-adf7-a8b8d71a7b53', 'equipements.gerer', 'Gérer les équipements', 'Gérer les équipements et matériels d''un PDV', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('8e1d06a4-bf18-45e8-b39d-e67e5d7dc64e', 'pdv.creer', 'Créer un point de vente', 'Ajouter un nouveau point de vente', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('7b906f50-a6c3-4f9f-baed-847aaf2c55f6', 'pdv.gerer_employes', 'Gérer les employés d''un point de vente', 'Ajouter / retirer des employés d''un point de vente.', 'Opérations', '2026-10-27 10:30:17.175869'),
    ('18f1eafb-8f24-4537-af56-b5cbcb99922d', 'pdv.modifier', 'Modifier un point de vente', 'Modifier les détails du point de vente', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('d27b5dd3-61e2-467e-90ea-5c798360a013', 'pdv.referentiels', 'Gérer les catégories et thèmes des points de vente', 'Ajouter, renommer, supprimer les catégories et la palette de thèmes des points de vente.', 'Opérations', '2026-10-27 10:30:17.178850'),
    ('57cd1a5d-7427-4c60-a524-cb9027b2702c', 'pdv.supprimer', 'Supprimer un point de vente', 'Archiver ou supprimer un point de vente', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('282ab556-b741-4f2d-be68-a94a0a683cb1', 'pdv.voir', 'Points de Vente', 'Consulter les points de vente', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('64ccba2c-1dfa-4ee3-a562-76d414e52f74', 'utilisateurs.activer', 'Activer / désactiver un compte', 'Désactiver (ou réactiver) un compte utilisateur sans le supprimer.', 'Opérations', '2026-10-27 10:30:17.196078'),
    ('d18fee28-43e2-44a6-a0b6-711f3fb77bed', 'utilisateurs.creer', 'Créer un utilisateur', 'Créer de nouveaux comptes utilisateurs', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('3c07f745-9a84-4f94-83da-926c29923d0c', 'utilisateurs.modifier', 'Modifier un utilisateur', 'Modifier les profils utilisateurs existants', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('7d2aa02c-e3a6-49a1-96d9-0158626aec24', 'utilisateurs.supprimer', 'Supprimer un utilisateur', 'Désactiver ou supprimer des utilisateurs', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('8ddc431c-6418-41e3-b109-f03aa3b589a1', 'utilisateurs.voir', 'Utilisateurs (Département)', 'Consulter les collaborateurs de son département', 'Opérations', '2026-10-12 14:08:13.094182'),
    ('54cba514-acd5-4bd6-a3a7-68ea314363a3', 'utilisateurs.voir_tous', 'Tous les utilisateurs', 'Consulter l''ensemble des utilisateurs du système', 'Opérations', '2026-10-12 14:08:13.094182')
ON CONFLICT DO NOTHING;

-- roles (6)
INSERT INTO roles (id, nom, description, couleur, niveau, systeme, actif, date_creation) VALUES
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'Super Administrateur', 'Contrôle total du système : visibilité globale et administration complète', '#EF4444', 100, TRUE, TRUE, '2026-10-12 14:08:13.132792'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', 'Directrice Réseau', 'Direction réseau : supervision de tous les points de vente, rapports et visibilité globale des tickets', '#8B5CF6', 85, FALSE, TRUE, '2026-10-12 14:08:13.132792'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'Responsable Département', 'Responsable de département : supervise et assigne les tickets du département, suit la performance', '#F59E0B', 60, FALSE, TRUE, '2026-10-12 14:08:13.132792'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', 'Agent', 'Agent: traite et résout les tickets de son département', '#3b82f6', 50, FALSE, TRUE, '2026-10-12 14:08:13.132792'),
    ('901f273f-ed3d-4f4c-9ee5-0f2a0d283fa9', 'Responsable Point de Vente', 'Responsable de point de vente : crée des tickets pour son magasin, gère le matériel et assure le suivi', '#10B981', 30, FALSE, TRUE, '2026-10-12 14:08:13.132792'),
    ('5e900431-fca7-4363-ad4c-a2b441423c7a', 'Personnel Point de Vente', 'Personnel de point de vente (baristas, équipiers) : consulte et crée des demandes de support', '#6B7280', 10, FALSE, TRUE, '2026-10-12 14:08:13.132792')
ON CONFLICT DO NOTHING;

-- configurations_systeme (4)
INSERT INTO configurations_systeme (cle, valeur, description, date_mise_a_jour) VALUES
    ('pdv_categories', '[{"nom": "Urbain", "description": "Centre-ville & quartiers", "icone": "building", "ordre": 1, "actif": true}, {"nom": "Express", "description": "Station-service, kiosque", "icone": "bolt", "ordre": 2, "actif": true}, {"nom": "Mall", "description": "Centre commercial", "icone": "bag", "ordre": 3, "actif": true}]', 'Catégories de points de vente (JSON)', '2026-10-27 10:33:04.206701'),
    ('pdv_themes', '[{"nom": "Émeraude", "couleur": "#10b981", "ordre": 1}, {"nom": "Azur", "couleur": "#0ea5e9", "ordre": 2}, {"nom": "Saphir", "couleur": "#2563eb", "ordre": 3}, {"nom": "Indigo", "couleur": "#6366f1", "ordre": 4}, {"nom": "Violet", "couleur": "#8b5cf6", "ordre": 5}, {"nom": "Rose", "couleur": "#ec4899", "ordre": 6}, {"nom": "Corail", "couleur": "#f97316", "ordre": 7}, {"nom": "Ambre", "couleur": "#f59e0b", "ordre": 8}, {"nom": "Rouge", "couleur": "#ef4444", "ordre": 9}, {"nom": "Sarcelle", "couleur": "#14b8a6", "ordre": 10}, {"nom": "Ardoise", "couleur": "#64748b", "ordre": 11}]', 'Palette de thèmes des points de vente (JSON)', '2026-10-27 10:33:03.964041'),
    ('permission_rattrapages', '["v1-departements-supprimer", "v1-entreprises-niveau60"]', 'Rattrapages de permissions déjà appliqués', '2026-10-27 10:30:17.597866'),
    ('roles_categories_order', '["Espace de travail", "Opérations", "Intelligence", "Administration"]', 'Ordre d''affichage des catégories de permissions dans la gestion des rôles', '2026-10-27 10:24:51.576090')
ON CONFLICT DO NOTHING;

-- roles_permissions (159)
INSERT INTO roles_permissions (role_id, permission_id) VALUES
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '00b215f5-f614-47d3-bfd5-53ec4e733e8c'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '0340e75f-53aa-4f0f-99db-02eb0e85b7b9'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '03df436b-4b5a-44a9-8895-1b688826ba95'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '047b5e23-7c1a-40d0-b542-aa8fccfaac24'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '0f990f82-bff2-41b4-a175-d006e850efbb'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '16abbdbb-1a31-40bc-adf7-a8b8d71a7b53'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '18f1eafb-8f24-4537-af56-b5cbcb99922d'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '1ff3e383-385d-46b8-a5ca-c84a256117d4'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '22db6721-5e77-4cef-b984-a8177b9d6b01'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '252ba45e-ddca-45de-b51c-270a9ef2d4e9'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '282ab556-b741-4f2d-be68-a94a0a683cb1'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '3229a390-8f13-4bb3-91ce-4477fd560d2e'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '357a8c25-9946-4d0d-8f1d-03de9afa5ca8'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '3c07f745-9a84-4f94-83da-926c29923d0c'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '4458e877-8c1d-4a39-925c-a015768a5e33'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '46cb6df9-e867-4317-a18e-eea031166daa'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '538f7e5b-c507-409e-8baf-173c3ed69e41'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '54cba514-acd5-4bd6-a3a7-68ea314363a3'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '57cd1a5d-7427-4c60-a524-cb9027b2702c'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '5c82af9d-26de-404c-a7fe-735f0ebc074b'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '5f252230-6c03-46f3-98cd-29c56634aa67'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '6a84c38c-ec5e-46f8-aa7e-28204f8b8a6e'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '7d2aa02c-e3a6-49a1-96d9-0158626aec24'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '8ddc431c-6418-41e3-b109-f03aa3b589a1'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', '8e1d06a4-bf18-45e8-b39d-e67e5d7dc64e'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'a3cb7466-d4fe-4627-9f07-9320542c734a'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'ad11f22c-0f46-4222-ab9a-215aa2b94cb7'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'be11e2a2-0302-4931-93de-57ad4633336f'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'c31c0ecb-5a61-464d-b0b6-1a57eeca1710'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'c5fba854-2afe-47fd-8803-dae1d38bcd0c'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'c60943aa-1a51-477b-883b-3bd05423232b'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'c6295f57-b5c6-4618-9347-20405e82bd94'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'd0d355cb-14df-4d49-aa0d-fe404705a762'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'd18fee28-43e2-44a6-a0b6-711f3fb77bed'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'd2e43ce3-ca67-402a-9165-c6a94cef9679'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'e3aac624-83c9-4bdf-b7f3-43ebd394e963'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'eca5c65c-7f64-4b51-9d5c-6dac181b0d17'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'f15bac9a-9792-44c1-ba61-c88322775d2c'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'f2c94810-a8ce-44d8-aa2e-50bffefb5d72'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'f303b68b-e0b6-4125-b576-77cde8c58a5d'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'f484a0b5-5679-48c9-a238-1cf6ee2ebea2'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'fab745cf-d748-4a09-b749-a62b78ea48b5'),
    ('30883ace-9470-44f8-bcc7-e1f723b0242a', 'fe09001e-2ab0-4217-b267-8982f5ff9bbf'),
    ('5e900431-fca7-4363-ad4c-a2b441423c7a', '5c82af9d-26de-404c-a7fe-735f0ebc074b'),
    ('5e900431-fca7-4363-ad4c-a2b441423c7a', '823251d4-bdbd-4d04-b787-a5c1483785f3'),
    ('5e900431-fca7-4363-ad4c-a2b441423c7a', 'ad11f22c-0f46-4222-ab9a-215aa2b94cb7'),
    ('5e900431-fca7-4363-ad4c-a2b441423c7a', 'b2216d1a-0fcc-48f6-aa68-a63492d08a6a'),
    ('5e900431-fca7-4363-ad4c-a2b441423c7a', 'e3aac624-83c9-4bdf-b7f3-43ebd394e963'),
    ('5e900431-fca7-4363-ad4c-a2b441423c7a', 'f303b68b-e0b6-4125-b576-77cde8c58a5d'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', '0340e75f-53aa-4f0f-99db-02eb0e85b7b9'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', '16abbdbb-1a31-40bc-adf7-a8b8d71a7b53'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', '18f1eafb-8f24-4537-af56-b5cbcb99922d'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', '1ff3e383-385d-46b8-a5ca-c84a256117d4'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', '22db6721-5e77-4cef-b984-a8177b9d6b01'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', '252ba45e-ddca-45de-b51c-270a9ef2d4e9'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', '282ab556-b741-4f2d-be68-a94a0a683cb1'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', '3229a390-8f13-4bb3-91ce-4477fd560d2e'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', '357a8c25-9946-4d0d-8f1d-03de9afa5ca8'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', '538f7e5b-c507-409e-8baf-173c3ed69e41'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', '54cba514-acd5-4bd6-a3a7-68ea314363a3'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', '5c82af9d-26de-404c-a7fe-735f0ebc074b'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', '6d59b369-aa13-4355-95a6-be43d539dd1f'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', '7b906f50-a6c3-4f9f-baed-847aaf2c55f6'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', '7c35eab4-c78b-47b8-a9b9-b46c3137bbc3'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', '823251d4-bdbd-4d04-b787-a5c1483785f3'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', 'a3cb7466-d4fe-4627-9f07-9320542c734a'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', 'a49cc8ef-eced-4686-9d6a-9fe586e8c87b'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', 'ad11f22c-0f46-4222-ab9a-215aa2b94cb7'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', 'b2216d1a-0fcc-48f6-aa68-a63492d08a6a'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', 'be11e2a2-0302-4931-93de-57ad4633336f'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', 'c5fba854-2afe-47fd-8803-dae1d38bcd0c'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', 'd0d355cb-14df-4d49-aa0d-fe404705a762'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', 'd27b5dd3-61e2-467e-90ea-5c798360a013'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', 'd2e43ce3-ca67-402a-9165-c6a94cef9679'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', 'e3aac624-83c9-4bdf-b7f3-43ebd394e963'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', 'ee32aa14-2688-4b0b-bc61-dec962fb405b'),
    ('792163c0-4acc-47d2-9c4e-dc29521586d9', 'fe09001e-2ab0-4217-b267-8982f5ff9bbf'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '0340e75f-53aa-4f0f-99db-02eb0e85b7b9'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '0f990f82-bff2-41b4-a175-d006e850efbb'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '16abbdbb-1a31-40bc-adf7-a8b8d71a7b53'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '18f1eafb-8f24-4537-af56-b5cbcb99922d'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '1d46e937-a5a0-4bcb-8fd4-d92f39464ef5'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '1ff3e383-385d-46b8-a5ca-c84a256117d4'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '22db6721-5e77-4cef-b984-a8177b9d6b01'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '252ba45e-ddca-45de-b51c-270a9ef2d4e9'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '282ab556-b741-4f2d-be68-a94a0a683cb1'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '3229a390-8f13-4bb3-91ce-4477fd560d2e'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '357a8c25-9946-4d0d-8f1d-03de9afa5ca8'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '538f7e5b-c507-409e-8baf-173c3ed69e41'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '54cba514-acd5-4bd6-a3a7-68ea314363a3'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '5c82af9d-26de-404c-a7fe-735f0ebc074b'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '5f252230-6c03-46f3-98cd-29c56634aa67'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '6d59b369-aa13-4355-95a6-be43d539dd1f'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '7b906f50-a6c3-4f9f-baed-847aaf2c55f6'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '7c35eab4-c78b-47b8-a9b9-b46c3137bbc3'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '7f033a77-2e01-4e61-a412-aad3bb42f94a'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '823251d4-bdbd-4d04-b787-a5c1483785f3'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '8ddc431c-6418-41e3-b109-f03aa3b589a1'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'a3cb7466-d4fe-4627-9f07-9320542c734a'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'a49cc8ef-eced-4686-9d6a-9fe586e8c87b'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'ad11f22c-0f46-4222-ab9a-215aa2b94cb7'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'b2216d1a-0fcc-48f6-aa68-a63492d08a6a'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'be11e2a2-0302-4931-93de-57ad4633336f'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'c5fba854-2afe-47fd-8803-dae1d38bcd0c'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'c60943aa-1a51-477b-883b-3bd05423232b'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'c6295f57-b5c6-4618-9347-20405e82bd94'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'd0d355cb-14df-4d49-aa0d-fe404705a762'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'd27b5dd3-61e2-467e-90ea-5c798360a013'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'd2e43ce3-ca67-402a-9165-c6a94cef9679'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'd69631d5-9e40-41cb-88b7-fe15ad578855'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'e3aac624-83c9-4bdf-b7f3-43ebd394e963'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'e48ffc72-0527-4d5d-a591-6690f5d3b6cf'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'ee32aa14-2688-4b0b-bc61-dec962fb405b'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'f15bac9a-9792-44c1-ba61-c88322775d2c'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'f484a0b5-5679-48c9-a238-1cf6ee2ebea2'),
    ('7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'fe09001e-2ab0-4217-b267-8982f5ff9bbf'),
    ('901f273f-ed3d-4f4c-9ee5-0f2a0d283fa9', '0340e75f-53aa-4f0f-99db-02eb0e85b7b9'),
    ('901f273f-ed3d-4f4c-9ee5-0f2a0d283fa9', '16abbdbb-1a31-40bc-adf7-a8b8d71a7b53'),
    ('901f273f-ed3d-4f4c-9ee5-0f2a0d283fa9', '282ab556-b741-4f2d-be68-a94a0a683cb1'),
    ('901f273f-ed3d-4f4c-9ee5-0f2a0d283fa9', '5c82af9d-26de-404c-a7fe-735f0ebc074b'),
    ('901f273f-ed3d-4f4c-9ee5-0f2a0d283fa9', '823251d4-bdbd-4d04-b787-a5c1483785f3'),
    ('901f273f-ed3d-4f4c-9ee5-0f2a0d283fa9', 'a3cb7466-d4fe-4627-9f07-9320542c734a'),
    ('901f273f-ed3d-4f4c-9ee5-0f2a0d283fa9', 'ad11f22c-0f46-4222-ab9a-215aa2b94cb7'),
    ('901f273f-ed3d-4f4c-9ee5-0f2a0d283fa9', 'b2216d1a-0fcc-48f6-aa68-a63492d08a6a'),
    ('901f273f-ed3d-4f4c-9ee5-0f2a0d283fa9', 'e3aac624-83c9-4bdf-b7f3-43ebd394e963'),
    ('901f273f-ed3d-4f4c-9ee5-0f2a0d283fa9', 'f303b68b-e0b6-4125-b576-77cde8c58a5d'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '0340e75f-53aa-4f0f-99db-02eb0e85b7b9'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '16abbdbb-1a31-40bc-adf7-a8b8d71a7b53'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '18f1eafb-8f24-4537-af56-b5cbcb99922d'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '1d46e937-a5a0-4bcb-8fd4-d92f39464ef5'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '1ff3e383-385d-46b8-a5ca-c84a256117d4'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '22db6721-5e77-4cef-b984-a8177b9d6b01'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '282ab556-b741-4f2d-be68-a94a0a683cb1'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '3229a390-8f13-4bb3-91ce-4477fd560d2e'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '357a8c25-9946-4d0d-8f1d-03de9afa5ca8'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '3c07f745-9a84-4f94-83da-926c29923d0c'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '538f7e5b-c507-409e-8baf-173c3ed69e41'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '54cba514-acd5-4bd6-a3a7-68ea314363a3'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '5c82af9d-26de-404c-a7fe-735f0ebc074b'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '64ccba2c-1dfa-4ee3-a562-76d414e52f74'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '7b906f50-a6c3-4f9f-baed-847aaf2c55f6'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '7c35eab4-c78b-47b8-a9b9-b46c3137bbc3'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '7f033a77-2e01-4e61-a412-aad3bb42f94a'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '823251d4-bdbd-4d04-b787-a5c1483785f3'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', '8ddc431c-6418-41e3-b109-f03aa3b589a1'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', 'a3cb7466-d4fe-4627-9f07-9320542c734a'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', 'a49cc8ef-eced-4686-9d6a-9fe586e8c87b'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', 'ad11f22c-0f46-4222-ab9a-215aa2b94cb7'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', 'b2216d1a-0fcc-48f6-aa68-a63492d08a6a'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', 'be11e2a2-0302-4931-93de-57ad4633336f'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', 'c5fba854-2afe-47fd-8803-dae1d38bcd0c'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', 'd18fee28-43e2-44a6-a0b6-711f3fb77bed'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', 'd27b5dd3-61e2-467e-90ea-5c798360a013'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', 'e3aac624-83c9-4bdf-b7f3-43ebd394e963'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', 'eca5c65c-7f64-4b51-9d5c-6dac181b0d17'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', 'ee32aa14-2688-4b0b-bc61-dec962fb405b'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', 'f15bac9a-9792-44c1-ba61-c88322775d2c'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', 'f303b68b-e0b6-4125-b576-77cde8c58a5d'),
    ('c5534002-f938-4c55-8a5b-2549336b3c7c', 'fe09001e-2ab0-4217-b267-8982f5ff9bbf')
ON CONFLICT DO NOTHING;


-- ───────────────────────────── 3b. Données d'exemple + compte administrateur par défaut ─────────────────────────────
-- Données d'EXEMPLE entièrement fictives (adresses @example.com). À supprimer ou remplacer par vos données.
-- Compte par défaut : admin@example.com / testtest  →  CHANGEZ CE MOT DE PASSE dès la première connexion.
-- Les autres utilisateurs d'exemple sont INACTIFS (aucune connexion possible) : activez-les ou supprimez-les.

-- entreprises (1)
INSERT INTO entreprises (id, nom, code, description, type_entreprise, email, telephone, adresse, site_web, couleur, logo, actif, date_creation) VALUES
    ('d1aacb5a-4d7a-55a5-9a0a-ff3ed9ec03c4', 'Entreprise Exemple', 'EXE', 'Exemple d''entreprise (à remplacer par la vôtre).', 'Siège', 'contact@example.com', NULL, NULL, NULL, '#E8213F', NULL, TRUE, '2026-01-05 09:00:00')
ON CONFLICT DO NOTHING;

-- departements (7)
INSERT INTO departements (id, nom, code, description, email, telephone, localisation, couleur, icone, responsable_id, sla_reponse_heures, sla_resolution_heures, horaires_travail, actif, date_creation) VALUES
    ('f105965b-b185-5391-b1e4-c98554f2866f', 'Stock', 'STK', 'Approvisionnement et inventaire', 'stk@example.com', NULL, NULL, '#10B981', 'box', NULL, 4, 24, NULL, TRUE, '2026-01-05 09:00:00'),
    ('3af8649a-1b54-5d9f-8a15-684893974b91', 'Qualité & Hygiène', 'QHSE', 'Normes, contrôles et hygiène', 'qhse@example.com', NULL, NULL, '#06B6D4', 'shield', NULL, 4, 24, NULL, TRUE, '2026-01-05 09:00:00'),
    ('dad4dbcb-2a8e-5f3d-ab4d-19aa560a1ed7', 'Finance & Comptabilité', 'FIN', 'Paiements, factures, caisse', 'fin@example.com', NULL, NULL, '#EAB308', 'dollar-sign', NULL, 4, 24, NULL, TRUE, '2026-01-05 09:00:00'),
    ('ff87813d-a7a4-5836-91ac-58ea9e61677b', 'Opérationnel', 'OP', 'Organisation des points de vente', 'op@example.com', NULL, NULL, '#F59E0B', 'settings', NULL, 4, 24, NULL, TRUE, '2026-01-05 09:00:00'),
    ('31777259-74e3-5779-b6b9-4ad9d453a0fd', 'Support IT', 'IT', 'Informatique, caisses, réseau', 'it@example.com', NULL, NULL, '#3B82F6', 'monitor', NULL, 4, 24, NULL, TRUE, '2026-01-05 09:00:00'),
    ('4605ecc0-c2c3-5acb-841f-92d81012df17', 'Maintenance', 'MAINT', 'Équipements et locaux', 'maint@example.com', NULL, NULL, '#EA580C', 'tool', NULL, 4, 24, NULL, TRUE, '2026-01-05 09:00:00'),
    ('af4e1baf-4d2e-57c0-8326-8f9680984692', 'Ressources Humaines', 'RH', 'Personnel et démarches', 'rh@example.com', NULL, NULL, '#EC4899', 'users', NULL, 4, 24, NULL, TRUE, '2026-01-05 09:00:00')
ON CONFLICT DO NOTHING;

-- points_de_vente (4)
INSERT INTO points_de_vente (id, nom, adresse, telephone, email, localisation, categorie, responsable_id, actif, couleur, date_creation) VALUES
    ('88e4a071-64fe-5947-9af7-f3ff8b8e4db3', 'PDV Exemple Mall', NULL, NULL, 'pdv.mall@example.com', 'Ville exemple', 'Mall', NULL, TRUE, '#a855f7', '2026-01-05 09:00:00'),
    ('b3890436-28d2-5df9-bbf1-d5447ee818ac', 'PDV Exemple Gare', NULL, NULL, 'pdv.gare@example.com', 'Ville exemple', 'Express', NULL, TRUE, '#f97316', '2026-01-05 09:00:00'),
    ('68ec9829-a142-5022-9bcd-f9bf08cce073', 'PDV Exemple Nord', NULL, NULL, 'pdv.nord@example.com', 'Ville exemple', 'Express', NULL, TRUE, '#0ea5e9', '2026-01-05 09:00:00'),
    ('a62042d2-a17c-5626-b9ac-0832ce8a9cc4', 'PDV Exemple Centre', NULL, NULL, 'pdv.centre@example.com', 'Ville exemple', 'Urbain', NULL, TRUE, '#10b981', '2026-01-05 09:00:00')
ON CONFLICT DO NOTHING;

-- utilisateurs (13)
INSERT INTO utilisateurs (id, nom, prenom, email, mot_de_passe_hash, telephone, poste, matricule, photo_profil, anydesk_id, anydesk_password, teamviewer_id, teamviewer_password, poste_machine, role_id, departement_id, pdv_id, entreprise_id, langue, theme, couleur, notifications_email, notifications_push, actif, verrouille, date_verrouillage, session_version, tentatives_connexion, date_creation, derniere_connexion, derniere_activite) VALUES
    ('24070edd-2a0f-5537-90f9-81efa273c4c8', 'Administrateur', 'Cosmitto', 'admin@example.com', 'scrypt:32768:8:1$FB0pB4blPifVjPAZ$3f98c42ee82671fa0be8c81f726121e9b5ce77db6ea90a466b509cd4d09e0a1dc30dc09265e2b9ea28d74e7b5ead59ec384ba5f0c8e46f5e0f066b9a9d1ec539', NULL, 'Administrateur système', 'ADMIN001', NULL, NULL, NULL, NULL, NULL, NULL, '30883ace-9470-44f8-bcc7-e1f723b0242a', NULL, NULL, 'd1aacb5a-4d7a-55a5-9a0a-ff3ed9ec03c4', 'fr', 'light', '#E8213F', TRUE, TRUE, TRUE, FALSE, NULL, 0, 0, '2026-01-05 09:30:00', NULL, NULL),
    ('1d96e0d0-e385-55b9-9260-1137826fb513', 'Exemple', 'Sarra', 'directrice.reseau@example.com', 'scrypt:32768:8:1$FB0pB4blPifVjPAZ$3f98c42ee82671fa0be8c81f726121e9b5ce77db6ea90a466b509cd4d09e0a1dc30dc09265e2b9ea28d74e7b5ead59ec384ba5f0c8e46f5e0f066b9a9d1ec539', NULL, 'Directrice Réseau', 'EX001', NULL, NULL, NULL, NULL, NULL, NULL, '792163c0-4acc-47d2-9c4e-dc29521586d9', NULL, NULL, 'd1aacb5a-4d7a-55a5-9a0a-ff3ed9ec03c4', 'fr', 'light', '#E8213F', TRUE, TRUE, FALSE, FALSE, NULL, 0, 0, '2026-01-05 09:30:00', NULL, NULL),
    ('f2a5cc55-be1e-5a1b-a2eb-81660b26cd30', 'Exemple', 'Karim', 'responsable.it@example.com', 'scrypt:32768:8:1$FB0pB4blPifVjPAZ$3f98c42ee82671fa0be8c81f726121e9b5ce77db6ea90a466b509cd4d09e0a1dc30dc09265e2b9ea28d74e7b5ead59ec384ba5f0c8e46f5e0f066b9a9d1ec539', NULL, 'Responsable Support IT', 'EX002', NULL, NULL, NULL, NULL, NULL, NULL, '7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '31777259-74e3-5779-b6b9-4ad9d453a0fd', NULL, 'd1aacb5a-4d7a-55a5-9a0a-ff3ed9ec03c4', 'fr', 'light', '#E8213F', TRUE, TRUE, FALSE, FALSE, NULL, 0, 0, '2026-01-05 09:30:00', NULL, NULL),
    ('9f89f51f-f0e2-5ddc-8d35-d322488ebbef', 'Exemple', 'Hatem', 'responsable.maintenance@example.com', 'scrypt:32768:8:1$FB0pB4blPifVjPAZ$3f98c42ee82671fa0be8c81f726121e9b5ce77db6ea90a466b509cd4d09e0a1dc30dc09265e2b9ea28d74e7b5ead59ec384ba5f0c8e46f5e0f066b9a9d1ec539', NULL, 'Responsable Maintenance', 'EX003', NULL, NULL, NULL, NULL, NULL, NULL, '7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', '4605ecc0-c2c3-5acb-841f-92d81012df17', NULL, 'd1aacb5a-4d7a-55a5-9a0a-ff3ed9ec03c4', 'fr', 'light', '#E8213F', TRUE, TRUE, FALSE, FALSE, NULL, 0, 0, '2026-01-05 09:30:00', NULL, NULL),
    ('c8cd5767-cd54-55ea-b8e3-4420833eea81', 'Exemple', 'Ines', 'responsable.rh@example.com', 'scrypt:32768:8:1$FB0pB4blPifVjPAZ$3f98c42ee82671fa0be8c81f726121e9b5ce77db6ea90a466b509cd4d09e0a1dc30dc09265e2b9ea28d74e7b5ead59ec384ba5f0c8e46f5e0f066b9a9d1ec539', NULL, 'Responsable RH', 'EX004', NULL, NULL, NULL, NULL, NULL, NULL, '7b9ccdb9-9b86-4832-9ebf-ca2712f39fbf', 'af4e1baf-4d2e-57c0-8326-8f9680984692', NULL, 'd1aacb5a-4d7a-55a5-9a0a-ff3ed9ec03c4', 'fr', 'light', '#E8213F', TRUE, TRUE, FALSE, FALSE, NULL, 0, 0, '2026-01-05 09:30:00', NULL, NULL),
    ('e4f4d43b-6084-5ad7-8752-dff878f52f6a', 'Exemple', 'Lina', 'agent.support@example.com', 'scrypt:32768:8:1$FB0pB4blPifVjPAZ$3f98c42ee82671fa0be8c81f726121e9b5ce77db6ea90a466b509cd4d09e0a1dc30dc09265e2b9ea28d74e7b5ead59ec384ba5f0c8e46f5e0f066b9a9d1ec539', NULL, 'Agent Support IT', 'EX005', NULL, '123 456 789', NULL, '987 654 321', NULL, 'PC-SUPPORT-01', 'c5534002-f938-4c55-8a5b-2549336b3c7c', '31777259-74e3-5779-b6b9-4ad9d453a0fd', NULL, 'd1aacb5a-4d7a-55a5-9a0a-ff3ed9ec03c4', 'fr', 'light', '#E8213F', TRUE, TRUE, FALSE, FALSE, NULL, 0, 0, '2026-01-05 09:30:00', NULL, NULL),
    ('11a5c7b8-dbeb-5f99-aa14-d6cb98e3347c', 'Exemple', 'Yassine', 'agent.maintenance@example.com', 'scrypt:32768:8:1$FB0pB4blPifVjPAZ$3f98c42ee82671fa0be8c81f726121e9b5ce77db6ea90a466b509cd4d09e0a1dc30dc09265e2b9ea28d74e7b5ead59ec384ba5f0c8e46f5e0f066b9a9d1ec539', NULL, 'Technicien de maintenance', 'EX006', NULL, NULL, NULL, NULL, NULL, NULL, 'c5534002-f938-4c55-8a5b-2549336b3c7c', '4605ecc0-c2c3-5acb-841f-92d81012df17', NULL, 'd1aacb5a-4d7a-55a5-9a0a-ff3ed9ec03c4', 'fr', 'light', '#E8213F', TRUE, TRUE, FALSE, FALSE, NULL, 0, 0, '2026-01-05 09:30:00', NULL, NULL),
    ('7e3723a4-830b-5ae0-901e-b5f90daa736e', 'Exemple', 'Mariem', 'agent.stock@example.com', 'scrypt:32768:8:1$FB0pB4blPifVjPAZ$3f98c42ee82671fa0be8c81f726121e9b5ce77db6ea90a466b509cd4d09e0a1dc30dc09265e2b9ea28d74e7b5ead59ec384ba5f0c8e46f5e0f066b9a9d1ec539', NULL, 'Gestionnaire de stock', 'EX007', NULL, NULL, NULL, NULL, NULL, NULL, 'c5534002-f938-4c55-8a5b-2549336b3c7c', 'f105965b-b185-5391-b1e4-c98554f2866f', NULL, 'd1aacb5a-4d7a-55a5-9a0a-ff3ed9ec03c4', 'fr', 'light', '#E8213F', TRUE, TRUE, FALSE, FALSE, NULL, 0, 0, '2026-01-05 09:30:00', NULL, NULL),
    ('efba5e13-3757-5fb1-a081-5605595c4a70', 'Exemple', 'Omar', 'responsable.pdv@example.com', 'scrypt:32768:8:1$FB0pB4blPifVjPAZ$3f98c42ee82671fa0be8c81f726121e9b5ce77db6ea90a466b509cd4d09e0a1dc30dc09265e2b9ea28d74e7b5ead59ec384ba5f0c8e46f5e0f066b9a9d1ec539', NULL, 'Responsable de point de vente', 'EX008', NULL, NULL, NULL, NULL, NULL, NULL, '901f273f-ed3d-4f4c-9ee5-0f2a0d283fa9', NULL, 'a62042d2-a17c-5626-b9ac-0832ce8a9cc4', 'd1aacb5a-4d7a-55a5-9a0a-ff3ed9ec03c4', 'fr', 'light', '#E8213F', TRUE, TRUE, FALSE, FALSE, NULL, 0, 0, '2026-01-05 09:30:00', NULL, NULL),
    ('87251909-d48d-5ad7-b88d-2c6c8bc4a6a8', 'Exemple', 'Rania', 'responsable.nord@example.com', 'scrypt:32768:8:1$FB0pB4blPifVjPAZ$3f98c42ee82671fa0be8c81f726121e9b5ce77db6ea90a466b509cd4d09e0a1dc30dc09265e2b9ea28d74e7b5ead59ec384ba5f0c8e46f5e0f066b9a9d1ec539', NULL, 'Responsable de point de vente', 'EX009', NULL, NULL, NULL, NULL, NULL, NULL, '901f273f-ed3d-4f4c-9ee5-0f2a0d283fa9', NULL, '68ec9829-a142-5022-9bcd-f9bf08cce073', 'd1aacb5a-4d7a-55a5-9a0a-ff3ed9ec03c4', 'fr', 'light', '#E8213F', TRUE, TRUE, FALSE, FALSE, NULL, 0, 0, '2026-01-05 09:30:00', NULL, NULL),
    ('80408191-2577-5a24-86bd-09a3e5342429', 'Exemple', 'Nour', 'personnel.pdv@example.com', 'scrypt:32768:8:1$FB0pB4blPifVjPAZ$3f98c42ee82671fa0be8c81f726121e9b5ce77db6ea90a466b509cd4d09e0a1dc30dc09265e2b9ea28d74e7b5ead59ec384ba5f0c8e46f5e0f066b9a9d1ec539', NULL, 'Barista', 'EX010', NULL, NULL, NULL, NULL, NULL, NULL, '5e900431-fca7-4363-ad4c-a2b441423c7a', NULL, 'a62042d2-a17c-5626-b9ac-0832ce8a9cc4', 'd1aacb5a-4d7a-55a5-9a0a-ff3ed9ec03c4', 'fr', 'light', '#E8213F', TRUE, TRUE, FALSE, FALSE, NULL, 0, 0, '2026-01-05 09:30:00', NULL, NULL),
    ('1bb33247-1a04-5c5e-9e60-2294692a3257', 'Exemple', 'Walid', 'barista.nord@example.com', 'scrypt:32768:8:1$FB0pB4blPifVjPAZ$3f98c42ee82671fa0be8c81f726121e9b5ce77db6ea90a466b509cd4d09e0a1dc30dc09265e2b9ea28d74e7b5ead59ec384ba5f0c8e46f5e0f066b9a9d1ec539', NULL, 'Barista', 'EX011', NULL, NULL, NULL, NULL, NULL, NULL, '5e900431-fca7-4363-ad4c-a2b441423c7a', NULL, '68ec9829-a142-5022-9bcd-f9bf08cce073', 'd1aacb5a-4d7a-55a5-9a0a-ff3ed9ec03c4', 'fr', 'light', '#E8213F', TRUE, TRUE, FALSE, FALSE, NULL, 0, 0, '2026-01-05 09:30:00', NULL, NULL),
    ('733b37be-2514-5f45-85e1-73f05c478961', 'Exemple', 'Amel', 'caissiere.mall@example.com', 'scrypt:32768:8:1$FB0pB4blPifVjPAZ$3f98c42ee82671fa0be8c81f726121e9b5ce77db6ea90a466b509cd4d09e0a1dc30dc09265e2b9ea28d74e7b5ead59ec384ba5f0c8e46f5e0f066b9a9d1ec539', NULL, 'Caissière', 'EX012', NULL, NULL, NULL, NULL, NULL, NULL, '5e900431-fca7-4363-ad4c-a2b441423c7a', NULL, '88e4a071-64fe-5947-9af7-f3ff8b8e4db3', 'd1aacb5a-4d7a-55a5-9a0a-ff3ed9ec03c4', 'fr', 'light', '#E8213F', TRUE, TRUE, FALSE, FALSE, NULL, 0, 0, '2026-01-05 09:30:00', NULL, NULL)
ON CONFLICT DO NOTHING;

-- equipements (4)
INSERT INTO equipements (id, pdv_id, type_equipement, marque, modele, numero_serie, adresse_ip, adresse_mac, statut, date_installation, notes) VALUES
    ('9bef3d07-240c-5512-a864-98668d971330', 'a62042d2-a17c-5626-b9ac-0832ce8a9cc4', 'Routeur Wi-Fi', 'MarqueExemple', 'RX-100', 'EXEMPLE-0001', NULL, NULL, 'actif', '2025-11-15 10:00:00', NULL),
    ('1ca4c70b-5557-57b4-9ef9-e1a1101111ba', 'a62042d2-a17c-5626-b9ac-0832ce8a9cc4', 'Imprimante tickets', 'MarqueExemple', 'PR-58', 'EXEMPLE-0002', NULL, NULL, 'actif', '2025-11-15 10:00:00', NULL),
    ('662757b8-ef5c-573d-90f4-fb697e01e63a', '68ec9829-a142-5022-9bcd-f9bf08cce073', 'Caméra', 'MarqueExemple', 'CAM-2', 'EXEMPLE-0003', NULL, NULL, 'en_panne', '2025-11-15 10:00:00', NULL),
    ('7d2bba78-ec85-5e3b-964f-feaf7d4bc0d4', '88e4a071-64fe-5947-9af7-f3ff8b8e4db3', 'Terminal de paiement', 'MarqueExemple', 'TPE-9', 'EXEMPLE-0004', NULL, NULL, 'actif', '2025-11-15 10:00:00', NULL)
ON CONFLICT DO NOTHING;

-- categories_tickets (17)
INSERT INTO categories_tickets (id, nom, description, type_ticket, departement_id, priorite_defaut, delai_resolution_jours, etapes_workflow, auto_assignation, couleur, icone, formulaire_personnalise, actif, archivee, date_creation) VALUES
    ('2380d411-f382-5f1f-98b6-358e69afe2b8', 'Panne de caisse', NULL, 'incident', '31777259-74e3-5779-b6b9-4ad9d453a0fd', 'moyenne', 7, NULL, FALSE, '#3B82F6', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00'),
    ('66ec794e-cf06-5512-8b04-d5214ba31433', 'Wi-Fi / réseau', NULL, 'incident', '31777259-74e3-5779-b6b9-4ad9d453a0fd', 'moyenne', 7, NULL, FALSE, '#6366F1', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00'),
    ('cf66fb6e-18d7-52bf-bdfc-9aef604b7719', 'Demande d''accès / compte', NULL, 'demande', '31777259-74e3-5779-b6b9-4ad9d453a0fd', 'moyenne', 7, NULL, FALSE, '#0EA5E9', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00'),
    ('7a7f0bda-ce0e-5f69-b1c3-ba19306f7f38', 'Imprimante / ticket de caisse', NULL, 'incident', '31777259-74e3-5779-b6b9-4ad9d453a0fd', 'moyenne', 7, NULL, FALSE, '#2563EB', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00'),
    ('0b1be7f5-733b-57d1-9552-77cbff55948b', 'Machine à café en panne', NULL, 'incident', '4605ecc0-c2c3-5acb-841f-92d81012df17', 'moyenne', 7, NULL, FALSE, '#EA580C', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00'),
    ('14c791bc-d628-56de-9304-ab95b1726a85', 'Réparation du local', NULL, 'demande', '4605ecc0-c2c3-5acb-841f-92d81012df17', 'moyenne', 7, NULL, FALSE, '#F97316', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00'),
    ('e6e2afc6-09d9-5096-9bf5-6396f473f928', 'Frigo / chambre froide', NULL, 'incident', '4605ecc0-c2c3-5acb-841f-92d81012df17', 'moyenne', 7, NULL, FALSE, '#FB923C', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00'),
    ('91104b72-dc4d-5f64-afcb-bd85fa41cbb6', 'Attestation de travail', NULL, 'demande', 'af4e1baf-4d2e-57c0-8326-8f9680984692', 'moyenne', 7, NULL, FALSE, '#EC4899', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00'),
    ('d7abfd95-672b-5848-b7be-90144bb89d39', 'Question congés / planning', NULL, 'demande', 'af4e1baf-4d2e-57c0-8326-8f9680984692', 'moyenne', 7, NULL, FALSE, '#DB2777', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00'),
    ('04b8e954-76a8-58b7-b0d8-2b729eaf29bd', 'Plainte / conflit', NULL, 'plainte', 'af4e1baf-4d2e-57c0-8326-8f9680984692', 'moyenne', 7, NULL, FALSE, '#BE185D', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00'),
    ('bc7bcfc2-a6b4-5afc-9542-9e2d00eb8b7f', 'Réapprovisionnement', NULL, 'besoin', 'f105965b-b185-5391-b1e4-c98554f2866f', 'moyenne', 7, NULL, FALSE, '#10B981', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00'),
    ('72f44adc-988d-51f8-bbb6-84b6768afa81', 'Casse / produit périmé', NULL, 'incident', 'f105965b-b185-5391-b1e4-c98554f2866f', 'moyenne', 7, NULL, FALSE, '#059669', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00'),
    ('12a71020-088b-5ee5-92e6-7033fac706ee', 'Contrôle d''hygiène', NULL, 'tache', '3af8649a-1b54-5d9f-8a15-684893974b91', 'moyenne', 7, NULL, FALSE, '#06B6D4', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00'),
    ('2a92c3a4-ef4a-5682-a668-5aa218755d31', 'Plainte client (qualité)', NULL, 'plainte', '3af8649a-1b54-5d9f-8a15-684893974b91', 'moyenne', 7, NULL, FALSE, '#0891B2', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00'),
    ('a3d6a3dc-2a54-575f-9b57-7c818f090efc', 'Erreur de paiement carte', NULL, 'incident', 'dad4dbcb-2a8e-5f3d-ab4d-19aa560a1ed7', 'moyenne', 7, NULL, FALSE, '#EAB308', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00'),
    ('f8211afc-ea07-5356-937d-8766b1015bf9', 'Question de facturation', NULL, 'demande', 'dad4dbcb-2a8e-5f3d-ab4d-19aa560a1ed7', 'moyenne', 7, NULL, FALSE, '#CA8A04', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00'),
    ('a204be22-deb5-5ed6-9f8f-33f9d6e479c5', 'Organisation du planning', NULL, 'tache', 'ff87813d-a7a4-5836-91ac-58ea9e61677b', 'moyenne', 7, NULL, FALSE, '#F59E0B', 'ticket', NULL, TRUE, FALSE, '2026-01-05 10:00:00')
ON CONFLICT DO NOTHING;

-- tickets (12)
INSERT INTO tickets (id, numero, titre, description, type_ticket, priorite, statut, impact, urgence, createur_id, assigne_a_id, categorie_id, departement_id, pdv_id, date_creation, date_modification, date_echeance, date_premiere_reponse, date_resolution, date_fermeture, sla_respecte, temps_premiere_reponse_minutes, temps_resolution_minutes, satisfaction, commentaire_satisfaction, article_demande, quantite_demandee, unite, nature_besoin, justification, personne_concernee, date_incident, lieu_incident, donnees_personnalisees, tags) VALUES
    ('68491f4d-c77d-51fa-aa56-03ffc8052b96', '1', 'Exemple : la caisse ne démarre plus', 'La caisse principale reste sur l''écran noir depuis ce matin.', 'incident', 'critique', 'nouveau', NULL, NULL, '80408191-2577-5a24-86bd-09a3e5342429', NULL, '2380d411-f382-5f1f-98b6-358e69afe2b8', '31777259-74e3-5779-b6b9-4ad9d453a0fd', 'a62042d2-a17c-5626-b9ac-0832ce8a9cc4', '2026-01-12 08:15:00', '2026-01-12 08:15:00', '2026-01-13 08:15:00', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    ('b6891082-bdee-5319-892a-decba73b0ce7', '2', 'Exemple : demande de compte pour un nouveau barista', 'Merci de créer un compte pour le nouvel employé.', 'demande', 'moyenne', 'en_cours', NULL, NULL, 'efba5e13-3757-5fb1-a081-5605595c4a70', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', 'cf66fb6e-18d7-52bf-bdfc-9aef604b7719', '31777259-74e3-5779-b6b9-4ad9d453a0fd', 'a62042d2-a17c-5626-b9ac-0832ce8a9cc4', '2026-01-12 09:00:00', '2026-01-12 09:00:00', '2026-01-13 09:00:00', '2026-01-12 09:40:00', NULL, NULL, NULL, 40, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    ('95e51995-5693-5c01-a34e-8c453c743239', '3', 'Exemple : Wi-Fi lent en salle', 'Le Wi-Fi se coupe aux heures de pointe.', 'incident', 'basse', 'resolu', NULL, NULL, 'efba5e13-3757-5fb1-a081-5605595c4a70', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', '66ec794e-cf06-5512-8b04-d5214ba31433', '31777259-74e3-5779-b6b9-4ad9d453a0fd', 'a62042d2-a17c-5626-b9ac-0832ce8a9cc4', '2026-01-10 14:00:00', '2026-01-10 14:00:00', '2026-01-11 14:00:00', '2026-01-10 14:30:00', '2026-01-10 16:00:00', NULL, TRUE, 30, 120, 5, 'Rapide et efficace, merci !', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    ('618d66ae-99b4-5d73-90dd-f7e1b58a5ea3', '4', 'Exemple : la machine à café fuit', 'De l''eau coule sous la machine principale.', 'incident', 'urgente', 'en_cours', NULL, NULL, '87251909-d48d-5ad7-b88d-2c6c8bc4a6a8', '11a5c7b8-dbeb-5f99-aa14-d6cb98e3347c', '0b1be7f5-733b-57d1-9552-77cbff55948b', '4605ecc0-c2c3-5acb-841f-92d81012df17', '68ec9829-a142-5022-9bcd-f9bf08cce073', '2026-01-12 07:30:00', '2026-01-12 07:30:00', '2026-01-13 07:30:00', '2026-01-12 07:50:00', NULL, NULL, NULL, 20, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    ('c140cf1b-f4ae-5cd8-a19e-0fd1a346401c', '5', 'Exemple : commande de gobelets et de lait', 'Stock presque épuisé avant le week-end.', 'besoin', 'haute', 'en_attente', NULL, NULL, '733b37be-2514-5f45-85e1-73f05c478961', '7e3723a4-830b-5ae0-901e-b5f90daa736e', 'bc7bcfc2-a6b4-5afc-9542-9e2d00eb8b7f', 'f105965b-b185-5391-b1e4-c98554f2866f', '88e4a071-64fe-5947-9af7-f3ff8b8e4db3', '2026-01-11 16:00:00', '2026-01-11 16:00:00', '2026-01-12 16:00:00', '2026-01-11 16:20:00', NULL, NULL, NULL, 20, NULL, NULL, NULL, 'Gobelets 12 oz', 500, 'pièces', 'Consommable', 'Rupture prévue samedi.', NULL, NULL, NULL, NULL, NULL),
    ('a9618a61-15ec-5789-b86e-838fd25880e3', '6', 'Exemple : attestation de travail', 'Besoin d''une attestation pour une démarche bancaire.', 'demande', 'basse', 'ferme', NULL, NULL, '1bb33247-1a04-5c5e-9e60-2294692a3257', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', '91104b72-dc4d-5f64-afcb-bd85fa41cbb6', 'af4e1baf-4d2e-57c0-8326-8f9680984692', '68ec9829-a142-5022-9bcd-f9bf08cce073', '2026-01-05 10:00:00', '2026-01-05 10:00:00', '2026-01-06 10:00:00', '2026-01-05 11:00:00', '2026-01-05 15:00:00', '2026-01-06 09:00:00', TRUE, 60, 300, 4, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    ('25fdce9d-dce1-52a6-b1b5-bcf3c58c88c1', '7', 'Exemple : client mécontent du café', 'Un client se plaint d''un café trop amer.', 'plainte', 'moyenne', 'nouveau', NULL, NULL, '733b37be-2514-5f45-85e1-73f05c478961', NULL, '2a92c3a4-ef4a-5682-a668-5aa218755d31', '3af8649a-1b54-5d9f-8a15-684893974b91', '88e4a071-64fe-5947-9af7-f3ff8b8e4db3', '2026-01-12 12:00:00', '2026-01-12 12:00:00', '2026-01-13 12:00:00', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'Client (ticket de caisse n° 4521)', NULL, NULL, NULL, NULL),
    ('e08c9dae-11fe-5e1b-b3ad-1b4cafd3c1ad', '8', 'Exemple : contrôle d''hygiène mensuel', 'Préparer la visite d''hygiène du mois.', 'tache', 'basse', 'en_cours', NULL, NULL, '1d96e0d0-e385-55b9-9260-1137826fb513', '7e3723a4-830b-5ae0-901e-b5f90daa736e', '12a71020-088b-5ee5-92e6-7033fac706ee', '3af8649a-1b54-5d9f-8a15-684893974b91', 'a62042d2-a17c-5626-b9ac-0832ce8a9cc4', '2026-01-08 09:00:00', '2026-01-08 09:00:00', '2026-01-20 09:00:00', '2026-01-08 10:00:00', NULL, NULL, NULL, 60, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    ('46b4d164-92c5-5933-bd55-59ff2bb4428a', '9', 'Exemple : double débit sur un paiement carte', 'Un client a été débité deux fois.', 'incident', 'haute', 'resolu', NULL, NULL, '87251909-d48d-5ad7-b88d-2c6c8bc4a6a8', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', 'a3d6a3dc-2a54-575f-9b57-7c818f090efc', 'dad4dbcb-2a8e-5f3d-ab4d-19aa560a1ed7', '68ec9829-a142-5022-9bcd-f9bf08cce073', '2026-01-09 11:00:00', '2026-01-09 11:00:00', '2026-01-10 11:00:00', '2026-01-09 11:30:00', '2026-01-10 13:00:00', NULL, FALSE, 30, 1560, 3, 'Résolu mais un peu long.', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    ('0fee31cf-d611-5f63-9c37-3105f72f3841', '10', 'Exemple : imprimante de tickets bloquée', 'Le papier se coince à chaque ticket.', 'incident', 'moyenne', 'ferme', NULL, NULL, '80408191-2577-5a24-86bd-09a3e5342429', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', '7a7f0bda-ce0e-5f69-b1c3-ba19306f7f38', '31777259-74e3-5779-b6b9-4ad9d453a0fd', 'a62042d2-a17c-5626-b9ac-0832ce8a9cc4', '2026-01-07 09:00:00', '2026-01-07 09:00:00', '2026-01-08 09:00:00', '2026-01-07 09:20:00', '2026-01-07 11:00:00', '2026-01-07 18:00:00', TRUE, 20, 120, 5, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    ('e146b2d7-0e8f-5cb1-8422-205ac324d6a7', '11', 'Exemple : question sur le planning de la semaine', 'Doublon du ticket précédent, à ignorer.', 'demande', 'basse', 'annule', NULL, NULL, '733b37be-2514-5f45-85e1-73f05c478961', NULL, 'd7abfd95-672b-5848-b7be-90144bb89d39', 'af4e1baf-4d2e-57c0-8326-8f9680984692', '88e4a071-64fe-5947-9af7-f3ff8b8e4db3', '2026-01-06 08:00:00', '2026-01-06 08:00:00', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    ('0b4c2c6e-e475-5622-9d78-4b5adeb6b723', '12', 'Exemple : frigo qui ne refroidit plus', 'La température du frigo monte à 12 °C.', 'incident', 'urgente', 'nouveau', NULL, NULL, 'efba5e13-3757-5fb1-a081-5605595c4a70', NULL, 'e6e2afc6-09d9-5096-9bf5-6396f473f928', '4605ecc0-c2c3-5acb-841f-92d81012df17', 'a62042d2-a17c-5626-b9ac-0832ce8a9cc4', '2026-01-12 10:00:00', '2026-01-12 10:00:00', '2026-01-13 10:00:00', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL)
ON CONFLICT DO NOTHING;

-- ticket_collaborateurs (2)
INSERT INTO ticket_collaborateurs (ticket_id, utilisateur_id) VALUES
    ('e08c9dae-11fe-5e1b-b3ad-1b4cafd3c1ad', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a'),
    ('e08c9dae-11fe-5e1b-b3ad-1b4cafd3c1ad', '7e3723a4-830b-5ae0-901e-b5f90daa736e')
ON CONFLICT DO NOTHING;

-- ticket_departements_collab (1)
INSERT INTO ticket_departements_collab (ticket_id, departement_id) VALUES
    ('e08c9dae-11fe-5e1b-b3ad-1b4cafd3c1ad', 'f105965b-b185-5391-b1e4-c98554f2866f')
ON CONFLICT DO NOTHING;

-- taches (6)
INSERT INTO taches (id, ticket_id, titre, description, assigne_a_id, terminee, ordre, date_creation, date_echeance, date_completion) VALUES
    ('24347362-515a-5f14-a205-96edd862023a', 'b6891082-bdee-5319-892a-decba73b0ce7', 'Créer le compte', NULL, 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', TRUE, 1, '2026-01-12 09:10:00', NULL, '2026-01-12 10:00:00'),
    ('7cba8d1c-088d-5de6-837b-2a31edef0462', 'b6891082-bdee-5319-892a-decba73b0ce7', 'Envoyer les identifiants au responsable', NULL, 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', FALSE, 0, '2026-01-12 09:10:00', NULL, NULL),
    ('4fa7f780-0ca0-5684-b813-e9ee8872935e', '618d66ae-99b4-5d73-90dd-f7e1b58a5ea3', 'Couper l''eau et sécuriser la zone', NULL, '11a5c7b8-dbeb-5f99-aa14-d6cb98e3347c', TRUE, 1, '2026-01-12 09:10:00', NULL, '2026-01-12 08:00:00'),
    ('5597c09b-d924-5031-a075-0b256b0e2cfe', '618d66ae-99b4-5d73-90dd-f7e1b58a5ea3', 'Remplacer le joint', NULL, '11a5c7b8-dbeb-5f99-aa14-d6cb98e3347c', FALSE, 0, '2026-01-12 09:10:00', NULL, NULL),
    ('9de15c2b-632b-5d8a-8994-d5a232bd90c2', 'e08c9dae-11fe-5e1b-b3ad-1b4cafd3c1ad', 'Vérifier les températures', NULL, '7e3723a4-830b-5ae0-901e-b5f90daa736e', FALSE, 1, '2026-01-12 09:10:00', NULL, NULL),
    ('f3ca952c-2278-58e8-9d97-07f9b00cc800', 'e08c9dae-11fe-5e1b-b3ad-1b4cafd3c1ad', 'Contrôler les dates limites', NULL, '7e3723a4-830b-5ae0-901e-b5f90daa736e', FALSE, 0, '2026-01-12 09:10:00', NULL, NULL)
ON CONFLICT DO NOTHING;

-- commentaires (9)
INSERT INTO commentaires (id, ticket_id, auteur_id, contenu, interne, type_commentaire, date_creation, date_modification, modifie) VALUES
    ('b2456cb7-6af3-5fdd-9753-895220044349', 'b6891082-bdee-5319-892a-decba73b0ce7', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', 'Bonjour, j''ai commencé la création du compte. Je reviens vers vous dans la journée.', FALSE, 'commentaire', '2026-01-12 09:40:00', '2026-01-12 09:40:00', FALSE),
    ('638ec3c6-0b2d-5bc3-8903-d6e090847f3b', '95e51995-5693-5c01-a34e-8c453c743239', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', 'Canal Wi-Fi changé et routeur redémarré : la connexion est stable.', FALSE, 'solution', '2026-01-10 16:00:00', '2026-01-10 16:00:00', FALSE),
    ('e1af4191-ae0d-57e8-81de-bcd22c0aec0a', '618d66ae-99b4-5d73-90dd-f7e1b58a5ea3', '11a5c7b8-dbeb-5f99-aa14-d6cb98e3347c', 'Technicien en route, coupez l''arrivée d''eau de la machine en attendant.', FALSE, 'commentaire', '2026-01-12 07:50:00', '2026-01-12 07:50:00', FALSE),
    ('a4030f7d-83be-5880-a2a4-534d1224b085', '618d66ae-99b4-5d73-90dd-f7e1b58a5ea3', '87251909-d48d-5ad7-b88d-2c6c8bc4a6a8', 'C''est fait, merci. La fuite continue au sol.', FALSE, 'commentaire', '2026-01-12 08:05:00', '2026-01-12 08:05:00', FALSE),
    ('0b28d00c-e185-5f1c-b7e4-8ff7ffb741e5', 'c140cf1b-f4ae-5cd8-a19e-0fd1a346401c', '7e3723a4-830b-5ae0-901e-b5f90daa736e', 'Commande passée chez le fournisseur, livraison prévue lundi.', FALSE, 'commentaire', '2026-01-11 16:20:00', '2026-01-11 16:20:00', FALSE),
    ('249d0d0c-0ae7-5aaa-b830-ce43c061ad6b', 'a9618a61-15ec-5789-b86e-838fd25880e3', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', 'Attestation envoyée par e-mail au responsable.', FALSE, 'solution', '2026-01-05 15:00:00', '2026-01-05 15:00:00', FALSE),
    ('59e5de04-77d1-59a4-b760-e84e9e185149', '46b4d164-92c5-5933-bd55-59ff2bb4428a', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', 'Remboursement lancé auprès de la banque, délai de 24 à 48 h.', FALSE, 'solution', '2026-01-10 13:00:00', '2026-01-10 13:00:00', FALSE),
    ('73011d3e-9fea-5f2a-b346-67e8c4da19c5', '0fee31cf-d611-5f63-9c37-3105f72f3841', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', 'Rouleau remplacé et guide papier nettoyé.', FALSE, 'solution', '2026-01-07 11:00:00', '2026-01-07 11:00:00', FALSE),
    ('abf190f9-262f-5d93-a68c-8db9c750be74', 'e08c9dae-11fe-5e1b-b3ad-1b4cafd3c1ad', '1d96e0d0-e385-55b9-9260-1137826fb513', 'Merci de joindre la liste de contrôle au ticket une fois terminée.', TRUE, 'note', '2026-01-08 10:30:00', '2026-01-08 10:30:00', FALSE)
ON CONFLICT DO NOTHING;

-- historique_tickets (9)
INSERT INTO historique_tickets (id, ticket_id, utilisateur_id, action, details, champ_modifie, ancienne_valeur, nouvelle_valeur, date_creation) VALUES
    ('28a41384-a0ab-569c-b6fe-bfb24441d2a5', '68491f4d-c77d-51fa-aa56-03ffc8052b96', '80408191-2577-5a24-86bd-09a3e5342429', 'Ticket créé', NULL, NULL, NULL, NULL, '2026-01-12 08:15:00'),
    ('1a49fad9-b200-557f-a89d-6b77590f66b5', 'b6891082-bdee-5319-892a-decba73b0ce7', 'efba5e13-3757-5fb1-a081-5605595c4a70', 'Ticket créé', NULL, NULL, NULL, NULL, '2026-01-12 09:00:00'),
    ('23457dc0-e105-579a-9bbd-a139ecca4e25', 'b6891082-bdee-5319-892a-decba73b0ce7', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', 'Statut modifié', NULL, 'statut', 'nouveau', 'en_cours', '2026-01-12 09:40:00'),
    ('66297db8-42c4-5305-b32b-484077891cf6', '95e51995-5693-5c01-a34e-8c453c743239', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', 'Statut modifié', NULL, 'statut', 'en_cours', 'resolu', '2026-01-10 16:00:00'),
    ('9842e9d9-4916-57b1-949f-873d387c64cb', '618d66ae-99b4-5d73-90dd-f7e1b58a5ea3', '87251909-d48d-5ad7-b88d-2c6c8bc4a6a8', 'Ticket créé', NULL, NULL, NULL, NULL, '2026-01-12 07:30:00'),
    ('e689a4b8-753e-50c3-9b73-7fde9bec9ecd', '618d66ae-99b4-5d73-90dd-f7e1b58a5ea3', '11a5c7b8-dbeb-5f99-aa14-d6cb98e3347c', 'Statut modifié', NULL, 'statut', 'nouveau', 'en_cours', '2026-01-12 07:50:00'),
    ('7c37e2de-3921-5382-983e-ba9313416286', 'c140cf1b-f4ae-5cd8-a19e-0fd1a346401c', '7e3723a4-830b-5ae0-901e-b5f90daa736e', 'Statut modifié', NULL, 'statut', 'en_cours', 'en_attente', '2026-01-11 16:30:00'),
    ('022cc8de-d5cf-5aae-815a-3dd186f6b35b', 'a9618a61-15ec-5789-b86e-838fd25880e3', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', 'Statut modifié', NULL, 'statut', 'resolu', 'ferme', '2026-01-06 09:00:00'),
    ('4832f500-42c5-56f8-a228-fe623d108380', 'e146b2d7-0e8f-5cb1-8422-205ac324d6a7', '733b37be-2514-5f45-85e1-73f05c478961', 'Statut modifié', NULL, 'statut', 'nouveau', 'annule', '2026-01-06 08:30:00')
ON CONFLICT DO NOTHING;

-- notifications (3)
INSERT INTO notifications (id, utilisateur_id, titre, message, type_notification, lien, lue, date_creation, date_lecture) VALUES
    ('db5afdab-241c-5100-9680-74de3935c45a', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', 'Nouveau ticket : Exemple', 'Un ticket vous a été assigné.', 'ticket', NULL, FALSE, '2026-01-12 09:00:00', NULL),
    ('159ec2ef-fbbc-582f-a6d5-94db5d77e727', '11a5c7b8-dbeb-5f99-aa14-d6cb98e3347c', 'Ticket urgent : machine à café', 'Une fuite est signalée au PDV Nord.', 'ticket', NULL, FALSE, '2026-01-12 07:30:00', NULL),
    ('e234cbd3-fc85-5cfd-88db-89abd5e7eb74', 'efba5e13-3757-5fb1-a081-5605595c4a70', 'Ticket résolu', 'Votre ticket « Wi-Fi lent en salle » est résolu.', 'ticket', NULL, TRUE, '2026-01-10 16:00:00', '2026-01-10 16:30:00')
ON CONFLICT DO NOTHING;

-- messages (3)
INSERT INTO messages (id, sender_id, receiver_id, content, timestamp, is_read, fichier_nom, fichier_chemin, fichier_type, fichier_taille) VALUES
    ('f20ca7d5-bcea-5fec-ad9c-01112aee6b0b', 'f2a5cc55-be1e-5a1b-a2eb-81660b26cd30', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', 'Bonjour Lina, peux-tu traiter le ticket n°2 en priorité ?', '2026-01-12 09:05:00', TRUE, NULL, NULL, NULL, NULL),
    ('8295a18f-9c90-5477-bc94-aaa8d790a56e', 'e4f4d43b-6084-5ad7-8752-dff878f52f6a', 'f2a5cc55-be1e-5a1b-a2eb-81660b26cd30', 'C''est en cours, je termine d''ici midi.', '2026-01-12 09:12:00', FALSE, NULL, NULL, NULL, NULL),
    ('0b1834d1-9b8f-5704-b4ec-ecb89bfcbebd', '87251909-d48d-5ad7-b88d-2c6c8bc4a6a8', '11a5c7b8-dbeb-5f99-aa14-d6cb98e3347c', 'Merci d''être intervenu pour la machine, tout refonctionne.', '2026-01-12 11:00:00', FALSE, NULL, NULL, NULL, NULL)
ON CONFLICT DO NOTHING;

-- suggestions (3)
INSERT INTO suggestions (id, titre, description, type_suggestion, statut, auteur_id, date_creation) VALUES
    ('7eef3e62-a167-552c-8ace-48f0bf51728f', 'Imprimer le rapport global en un clic', 'Ce serait pratique d''imprimer le rapport global en un clic.', 'amelioration', 'nouveau', 'efba5e13-3757-5fb1-a081-5605595c4a70', '2026-01-11 11:00:00'),
    ('b785a2e2-9053-5f6b-9d0d-9e8906a7b0ce', 'Le bouton « Enregistrer » ne répond pas sur téléphone', 'Sur certains téléphones, il faut appuyer deux fois.', 'bug', 'en_cours', '80408191-2577-5a24-86bd-09a3e5342429', '2026-01-09 15:00:00'),
    ('75172180-08b3-5e9e-a561-875b41df3dd9', 'Ajouter un mode sombre automatique', 'Passer en sombre le soir selon l''heure.', 'nouvelle_fonctionnalite', 'accepte', '1bb33247-1a04-5c5e-9e60-2294692a3257', '2026-01-08 18:00:00')
ON CONFLICT DO NOTHING;

-- plan_action_tasks (3)
INSERT INTO plan_action_tasks (id, titre, description, statut, urgent, date_debut, date_fin, createur_id, assigne_a_id) VALUES
    ('274443ce-0a84-5f61-a2f9-fa218f4b17ba', 'Former l''équipe au nouvel outil', 'Session de 30 minutes par point de vente.', 'planned', FALSE, '2026-02-01 09:00:00', '2026-02-15 18:00:00', '1d96e0d0-e385-55b9-9260-1137826fb513', 'f2a5cc55-be1e-5a1b-a2eb-81660b26cd30'),
    ('e5a31476-518a-5dd9-9ea2-6fd22e6407ee', 'Remplacer les routeurs Wi-Fi', 'Remplacement des routeurs les plus anciens.', 'progress', TRUE, '2026-01-10 09:00:00', '2026-01-31 18:00:00', '1d96e0d0-e385-55b9-9260-1137826fb513', '9f89f51f-f0e2-5ddc-8d35-d322488ebbef'),
    ('d52ee8f9-a112-5dd7-823a-0d2ef425901f', 'Mettre à jour la liste des contacts', NULL, 'completed', FALSE, '2026-01-02 09:00:00', '2026-01-05 18:00:00', '1d96e0d0-e385-55b9-9260-1137826fb513', 'c8cd5767-cd54-55ea-b8e3-4420833eea81')
ON CONFLICT DO NOTHING;

-- modeles_reponses (3)
INSERT INTO modeles_reponses (id, titre, contenu, categorie_id, departement_id, public, createur_id, utilisation_count, date_creation) VALUES
    ('c93e23fe-f34d-54d8-8544-717ed888a6ba', 'Accusé de réception', 'Bonjour, nous avons bien reçu votre demande et la traitons dans les meilleurs délais.', 'cf66fb6e-18d7-52bf-bdfc-9aef604b7719', '31777259-74e3-5779-b6b9-4ad9d453a0fd', TRUE, 'f2a5cc55-be1e-5a1b-a2eb-81660b26cd30', 0, '2026-01-06 10:00:00'),
    ('e5b9d184-60cd-5fae-9985-38b4f6b9f836', 'Demande de précisions', 'Bonjour, pouvez-vous préciser l''heure et le poste concerné par le problème ?', NULL, '31777259-74e3-5779-b6b9-4ad9d453a0fd', TRUE, 'f2a5cc55-be1e-5a1b-a2eb-81660b26cd30', 0, '2026-01-06 10:05:00'),
    ('81df3d36-408a-54f5-974e-9eae5771a638', 'Intervention planifiée', 'Bonjour, un technicien passera dans la journée. Merci de rester joignable.', '0b1be7f5-733b-57d1-9552-77cbff55948b', '4605ecc0-c2c3-5acb-841f-92d81012df17', FALSE, '9f89f51f-f0e2-5ddc-8d35-d322488ebbef', 0, '2026-01-06 10:10:00')
ON CONFLICT DO NOTHING;

-- categories_connaissance (4)
INSERT INTO categories_connaissance (id, nom, description, icone, date_creation) VALUES
    ('268bdd1f-1802-5244-8151-952f9683a244', 'Maintenance & IT', 'Guides de dépannage caisses, Wi-Fi et matériel', 'tool', '2026-01-06 09:00:00'),
    ('db871316-2298-5ecf-9f4a-8eca206dfe0a', 'Ressources Humaines', 'Attestations, fiches et démarches RH', 'users', '2026-01-06 09:00:00'),
    ('0dec61aa-4036-581f-befd-2c18a6a8122c', 'Opérations & Points de Vente', 'Procédures opérationnelles', 'settings', '2026-01-06 09:00:00'),
    ('2eb95484-4997-538c-adc7-da7841c326a7', 'Qualité & Hygiène', 'Fiches techniques et normes qualité', 'shield', '2026-01-06 09:00:00')
ON CONFLICT DO NOTHING;

-- articles_connaissance (5)
INSERT INTO articles_connaissance (id, titre, contenu, categorie_id, auteur_id, date_creation, date_mise_a_jour, vues, statut) VALUES
    ('3cbcdad8-1e8d-51b4-a659-695d4b9442c3', 'Redémarrer la caisse en cas d''écran noir', '1. Éteindre la caisse 10 secondes.
2. Débrancher puis rebrancher l''alimentation.
3. Si le problème persiste, créer un ticket « Panne de caisse ».', '268bdd1f-1802-5244-8151-952f9683a244', 'f2a5cc55-be1e-5a1b-a2eb-81660b26cd30', '2026-01-06 11:00:00', '2026-01-06 11:00:00', 0, 'publie'),
    ('dfa03f49-9ab5-5805-9af7-3fcac11de675', 'Que faire quand le Wi-Fi est lent ?', '1. Vérifier que le routeur est allumé.
2. Le redémarrer 30 secondes.
3. Prévenir le support si cela dure.', '268bdd1f-1802-5244-8151-952f9683a244', 'f2a5cc55-be1e-5a1b-a2eb-81660b26cd30', '2026-01-06 11:00:00', '2026-01-06 11:00:00', 0, 'publie'),
    ('0391af46-12b8-5170-b5d7-6d33ae402dd7', 'Demander une attestation de travail', 'Créer un ticket « Attestation de travail » en indiquant l''usage prévu. Délai : 24 h.', 'db871316-2298-5ecf-9f4a-8eca206dfe0a', 'c8cd5767-cd54-55ea-b8e3-4420833eea81', '2026-01-06 11:00:00', '2026-01-06 11:00:00', 0, 'publie'),
    ('0670e5d6-d061-5430-8401-214bc9924314', 'Les 5 gestes d''hygiène au comptoir', '1. Se laver les mains.
2. Nettoyer le plan de travail.
3. Ranger les produits au frais.
4. Porter la tenue propre.
5. Jeter les produits périmés.', '2eb95484-4997-538c-adc7-da7841c326a7', '1d96e0d0-e385-55b9-9260-1137826fb513', '2026-01-06 11:00:00', '2026-01-06 11:00:00', 0, 'publie'),
    ('bba6b64d-3915-528f-936b-4e7f1541fa16', 'Ouverture d''un point de vente', 'Allumer les machines, vérifier la caisse, contrôler les stocks, afficher le menu du jour.', '0dec61aa-4036-581f-befd-2c18a6a8122c', '1d96e0d0-e385-55b9-9260-1137826fb513', '2026-01-06 11:00:00', '2026-01-06 11:00:00', 0, 'publie')
ON CONFLICT DO NOTHING;

-- Responsables des départements et des points de vente
UPDATE departements SET responsable_id = 'f2a5cc55-be1e-5a1b-a2eb-81660b26cd30' WHERE id = '31777259-74e3-5779-b6b9-4ad9d453a0fd';
UPDATE departements SET responsable_id = '9f89f51f-f0e2-5ddc-8d35-d322488ebbef' WHERE id = '4605ecc0-c2c3-5acb-841f-92d81012df17';
UPDATE departements SET responsable_id = 'c8cd5767-cd54-55ea-b8e3-4420833eea81' WHERE id = 'af4e1baf-4d2e-57c0-8326-8f9680984692';
UPDATE points_de_vente SET responsable_id = '87251909-d48d-5ad7-b88d-2c6c8bc4a6a8' WHERE id = '68ec9829-a142-5022-9bcd-f9bf08cce073';
UPDATE points_de_vente SET responsable_id = 'efba5e13-3757-5fb1-a081-5605595c4a70' WHERE id = 'a62042d2-a17c-5626-b9ac-0832ce8a9cc4';

-- Le prochain ticket créé portera le n°13
SELECT setval('ticket_numero_seq', 12);

-- ───────────────────────────── 4. Droits PostgreSQL du rôle applicatif ─────────────────────────────
ALTER DATABASE cosmicenter OWNER TO cosmicenter;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cosmicenter;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cosmicenter;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO cosmicenter;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO cosmicenter;

COMMIT;

-- Les tickets repartent de zéro : la séquence ticket_numero_seq démarre à 1.
