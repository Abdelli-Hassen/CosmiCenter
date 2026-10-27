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
    # Catégories de tickets : archivage
    "ALTER TABLE categories_tickets ADD COLUMN IF NOT EXISTS archivee BOOLEAN NOT NULL DEFAULT FALSE",
]

# Permissions créées au démarrage si elles manquent :
#   (code, nom, description, catégorie, accordée d'office à…)
# Le dernier champ ne sert qu'à la CRÉATION de la permission : il rend aux rôles existants ce qu'ils pouvaient déjà
# faire avant que l'action ait sa propre case (aucune perte d'accès). Ensuite, tout se règle dans « Rôles ».
#   ('a', 'code')  = rôles qui ont déjà cette permission     ('niveau', n) = rôles de niveau >= n
#   ('tous',)      = tous les rôles                          None          = personne (à cocher à la main)
# Rangement dans la page Rôles : « <page>.<action> » se place sous la case « <page>.voir ».
DEFAULT_PERMISSIONS = [
    ('admin.categories', 'Gérer les catégories de tickets',
     'Créer, modifier, activer, archiver et supprimer les catégories (incidents, demandes...). '
     'Ajoute un bouton « Gérer les catégories » sur la page Nouveau ticket.', 'Espace de travail', None),

    # ── Tickets ──
    ('tickets.commenter', 'Commenter un ticket',
     "Écrire des messages dans la conversation d'un ticket auquel on a accès.", 'Espace de travail', ('tous',)),

    # ── Boîte à idées ──
    ('idees.creer', 'Proposer une idée',
     'Envoyer une nouvelle idée / suggestion (bug, amélioration, nouvelle fonctionnalité).',
     'Espace de travail', ('a', 'idees.voir')),
    ('idees.voir_toutes', 'Voir les idées de tout le monde',
     'Voir toutes les idées envoyées (sinon : seulement les siennes) et être prévenu par e-mail des nouvelles idées.',
     'Espace de travail', ('niveau', 90)),
    ('idees.modifier', "Traiter / changer le statut d'une idée",
     'Marquer une idée comme lue, acceptée, refusée, en cours ou terminée.', 'Espace de travail', ('niveau', 90)),
    ('idees.supprimer', 'Supprimer une idée', 'Supprimer définitivement une idée.', 'Espace de travail', ('niveau', 90)),

    # ── Base de connaissance ──
    ('base_connaissance.gerer_categories', "Gérer les catégories d'articles",
     'Créer des catégories dans la base de connaissance.', 'Opérations', ('a', 'base_connaissance.creer')),
    ('base_connaissance.voir_lecteurs', 'Voir qui a lu un article',
     "Afficher, au survol de l'œil, la liste des personnes qui ont lu l'article et combien de fois.",
     'Opérations', ('a', 'base_connaissance.creer')),

    # ── Départements ──
    ('departements.modifier_propre', 'Modifier son propre département',
     'Modifier la fiche du département auquel on appartient (sans pouvoir modifier les autres).', 'Opérations', None),
    ('departements.gerer_membres', "Gérer les membres d'un département",
     'Ajouter ou retirer des membres dans un département.', 'Opérations', ('a', 'departements.modifier')),

    # ── Points de vente ──
    ('pdv.gerer_employes', "Gérer les employés d'un point de vente",
     "Ajouter / retirer des employés d'un point de vente.", 'Opérations', ('a', 'pdv.modifier')),
    ('pdv.referentiels', 'Gérer les catégories et thèmes des points de vente',
     'Ajouter, renommer, supprimer les catégories et la palette de thèmes des points de vente.',
     'Opérations', ('a', 'pdv.modifier')),

    # ── Entreprises ──
    ('entreprises.archiver', 'Archiver / réactiver une entreprise',
     'Masquer une entreprise sans la supprimer, ou la réactiver.', 'Opérations', ('niveau', 60)),
    ('entreprises.gerer_collaborateurs', 'Rattacher / détacher des collaborateurs',
     "Associer ou retirer des utilisateurs d'une entreprise.", 'Opérations', ('niveau', 60)),

    # ── Utilisateurs ──
    ('utilisateurs.activer', 'Activer / désactiver un compte',
     'Désactiver (ou réactiver) un compte utilisateur sans le supprimer.', 'Opérations', ('a', 'utilisateurs.modifier')),

    # ── Plan d'action ──
    ('admin_plan_action.creer', "Ajouter une tâche au plan d'action",
     "Créer de nouvelles tâches dans le plan d'action.", 'Opérations', ('a', 'admin_plan_action.modifier')),
    ('admin_plan_action.supprimer', "Supprimer une tâche du plan d'action",
     'Supprimer définitivement une tâche.', 'Opérations', ('a', 'admin_plan_action.modifier')),
    ('admin_plan_action.exporter', "Exporter le plan d'action (Excel)",
     "Télécharger le plan d'action au format Excel.", 'Opérations', ('a', 'admin_plan_action.voir')),

    # ── Rapports ──
    ('rapports_globaux.exporter', 'Exporter les rapports (CSV)',
     'Télécharger les données du rapport global au format CSV.', 'Intelligence', ('a', 'rapports_globaux.voir')),
]

# Rattrapages exécutés une seule fois : (identifiant, [(permission, règle), ...])
# Quand une action change de permission, les rôles qui pouvaient déjà la faire la gardent.
ONE_TIME_GRANTS = [
    ('v1-departements-supprimer', [('departements.supprimer', ('a', 'departements.modifier'))]),
    ('v1-entreprises-niveau60', [('entreprises.creer', ('niveau', 60)), ('entreprises.modifier', ('niveau', 60)),
                                 ('entreprises.supprimer', ('niveau', 60))]),
]


def _roles_for(rule):
    from models import Role
    if not rule:
        return []
    kind = rule[0]
    roles = Role.query.all()
    if kind == 'tous':
        return roles
    if kind == 'niveau':
        return [r for r in roles if (r.niveau or 0) >= rule[1]]
    if kind == 'a':
        return [r for r in roles if any(p.code == rule[1] for p in r.permissions)]
    return []


def _grant(code, rule):
    from models import Permission
    perm = Permission.query.filter_by(code=code).first()
    if not perm:
        return
    for role in _roles_for(rule):
        if (role.niveau or 0) < 100 and perm not in role.permissions:
            role.permissions.append(perm)


def ensure_permissions(db):
    """Crée les permissions manquantes (avec les droits d'origine des rôles existants) et rejoue, une seule fois,
    les rattrapages ci-dessus."""
    import json
    from models import Permission, ConfigurationSysteme
    try:
        created = []
        for code, nom, description, categorie, grant in DEFAULT_PERMISSIONS:
            if not Permission.query.filter_by(code=code).first():
                db.session.add(Permission(code=code, nom=nom, description=description, categorie=categorie))
                created.append((code, grant))
        db.session.flush()
        for code, grant in created:
            _grant(code, grant)

        done = set(json.loads(ConfigurationSysteme.get_valeur('permission_rattrapages', '[]') or '[]'))
        for ident, grants in ONE_TIME_GRANTS:
            if ident not in done:
                for code, rule in grants:
                    _grant(code, rule)
                done.add(ident)
        ConfigurationSysteme.set_valeur('permission_rattrapages', json.dumps(sorted(done)),
                                        'Rattrapages de permissions déjà appliqués')
        db.session.commit()
    except Exception as exc:  # pragma: no cover
        db.session.rollback()
        logger.warning('ensure_permissions: %s', exc)


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
