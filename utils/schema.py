"""
Mises à jour de schéma idempotentes (PostgreSQL).

Le projet n'utilise pas encore Alembic : `db.create_all()` crée les tables manquantes mais
n'ajoute pas les colonnes. Ces instructions sont sûres à rejouer à chaque démarrage.
"""
import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)

STATEMENTS = [
    "ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS date_verrouillage TIMESTAMP",
    "ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS session_version INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE pieces_jointes ADD COLUMN IF NOT EXISTS commentaire_id VARCHAR(36) "
    "REFERENCES commentaires(id) ON DELETE CASCADE",
    # Messagerie : fichier joint à un message (nom d'origine, nom stocké, type, taille)
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS fichier_nom VARCHAR(255)",
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS fichier_chemin VARCHAR(100)",
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS fichier_type VARCHAR(150)",
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS fichier_taille INTEGER",
]

# Les mots de passe distants sont désormais chiffrés (jeton plus long que VARCHAR(100)).
WIDEN_COLUMNS = ['anydesk_password', 'teamviewer_password']


def ensure_schema(db):
    if db.engine.dialect.name != 'postgresql':
        return
    for stmt in STATEMENTS:
        try:
            db.session.execute(text(stmt))
            db.session.commit()
        except Exception as exc:  # pragma: no cover - dépend de l'état de la base
            db.session.rollback()
            logger.warning('ensure_schema: %s -> %s', stmt[:70], exc)

    for col in WIDEN_COLUMNS:
        try:
            width = db.session.execute(text(
                "SELECT character_maximum_length FROM information_schema.columns "
                "WHERE table_name='utilisateurs' AND column_name=:c"), {'c': col}).scalar()
            if width is not None and width < 512:
                db.session.execute(text(f"ALTER TABLE utilisateurs ALTER COLUMN {col} TYPE VARCHAR(512)"))
                db.session.commit()
        except Exception as exc:  # pragma: no cover
            db.session.rollback()
            logger.warning('ensure_schema: élargissement %s impossible: %s', col, exc)

    # Séquence atomique pour les numéros de ticket (évite les doublons en cas de création simultanée)
    try:
        exists = db.session.execute(text("SELECT to_regclass('ticket_numero_seq')")).scalar()
        if not exists:
            db.session.execute(text("CREATE SEQUENCE IF NOT EXISTS ticket_numero_seq START 1"))
            db.session.execute(text(
                "SELECT setval('ticket_numero_seq', "
                "GREATEST(COALESCE((SELECT MAX(numero::bigint) FROM tickets WHERE numero ~ '^[0-9]+$'), 0), 1), "
                "(SELECT COUNT(*) > 0 FROM tickets WHERE numero ~ '^[0-9]+$'))"))
            db.session.commit()
    except Exception as exc:  # pragma: no cover
        db.session.rollback()
        logger.warning('ensure_schema: séquence ticket_numero_seq: %s', exc)
