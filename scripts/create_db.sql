-- Création minimale de la base. Le script complet (tables) est cosmicenter.example.sql.
-- Mot de passe d'exemple : testtest (à changer en production) ; ne jamais committer un vrai mot de passe.
CREATE USER "CosHub" WITH PASSWORD 'testtest';
CREATE DATABASE "CosHub" OWNER "CosHub";
GRANT ALL PRIVILEGES ON DATABASE "CosHub" TO "CosHub";
