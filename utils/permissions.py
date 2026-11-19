"""Règles d'accès communes (visibilité des tickets, protection du Super Administrateur).

Il n'y a plus de niveaux : seules les permissions cochées dans « Rôles » décident de ce qu'un rôle peut faire.
Seule exception : le rôle « Super Administrateur » ne peut être attribué (ni ses comptes modifiés) que par un
Super Administrateur."""
from sqlalchemy import false, or_

from models import db, Departement, HistoriqueTicket, Message, Ticket, Utilisateur


def is_super_admin(user):
    """Vrai si l'utilisateur porte le rôle Super Administrateur."""
    role = getattr(user, 'role', None)
    return bool(role and role.est_super_admin)


def can_assign_role(actor, role):
    """Le rôle Super Administrateur ne peut être attribué que par un Super Administrateur ; les autres, librement."""
    if role is None:
        return True
    return (not role.est_super_admin) or is_super_admin(actor)


def can_act_on_user(actor, target):
    """Un compte Super Administrateur ne peut être modifié, désactivé ou supprimé que par un Super Administrateur
    (ou par lui-même pour ce qui le concerne)."""
    if target is None or actor.id == target.id:
        return True
    return (not is_super_admin(target)) or is_super_admin(actor)


def user_visibility_filter(user):
    """Critère SQLAlchemy des comptes visibles par `user` (hors permission utilisateurs.voir_tous) : lui-même, les
    personnes de son département, et celles qui partagent au moins un de ses points de vente (principal ou
    supplémentaire). Une personne sans département mais avec des PDV ne voit donc QUE les gens de ses PDV."""
    clauses = [Utilisateur.id == user.id]
    if user.departement_id:
        clauses.append(Utilisateur.departement_id == user.departement_id)
    for pdv in user.tous_pdvs:
        clauses.append(Utilisateur.pdv_id == pdv.id)
        clauses.append(Utilisateur.pdv_extra_ids.contains(pdv.id, autoescape=True))
    return or_(*clauses)


def can_view_user(user, target):
    """Même règle que `user_visibility_filter`, pour un compte déjà chargé (fiche d'un utilisateur)."""
    if target.id == user.id or user.has_permission('utilisateurs.voir_tous'):
        return True
    if not user.has_permission('utilisateurs.voir'):
        return False
    if user.departement_id and target.departement_id == user.departement_id:
        return True
    mine = {p.id for p in user.tous_pdvs}
    return bool(mine & {p.id for p in target.tous_pdvs})


def ticket_visibility_filter(user):
    """Critère SQLAlchemy des tickets visibles par `user` (hors permission tickets.voir_tous)."""
    clauses = [Ticket.createur_id == user.id, Ticket.assigne_a_id == user.id,
               Ticket.collaborateurs.any(Utilisateur.id == user.id)]
    if user.departement_id:
        clauses.append(Ticket.departement_id == user.departement_id)
        clauses.append(Ticket.departements_collab.any(Departement.id == user.departement_id))
    return or_(*clauses) if clauses else false()


def visible_tickets_query(user):
    if user.has_permission('tickets.voir_tous'):
        return Ticket.query
    return Ticket.query.filter(ticket_visibility_filter(user))


def ticket_is_unread(ticket):
    """Ticket jamais ouvert par l'utilisateur connecté (même règle que le compteur de la barre latérale :
    hors tickets créés par lui, fermés ou annulés). Les tickets ouverts sont chargés une seule fois par requête."""
    from flask import g
    from flask_login import current_user
    if not current_user.is_authenticated:
        return False
    if ticket.createur_id == current_user.id or ticket.statut in ('ferme', 'annule'):
        return False
    seen = getattr(g, '_seen_ticket_ids', None)
    if seen is None:
        rows = db.session.query(HistoriqueTicket.ticket_id).filter(
            HistoriqueTicket.utilisateur_id == current_user.id, HistoriqueTicket.action == 'Consultation').all()
        seen = g._seen_ticket_ids = {r[0] for r in rows}
    return ticket.id not in seen


def unopened_tickets_count(user):
    """Tickets visibles par `user` qu'il n'a jamais ouverts (hors tickets qu'il a créés, fermés ou annulés)."""
    seen = db.session.query(HistoriqueTicket.ticket_id).filter(
        HistoriqueTicket.utilisateur_id == user.id, HistoriqueTicket.action == 'Consultation')
    return visible_tickets_query(user).filter(
        Ticket.createur_id != user.id,
        Ticket.statut.notin_(['ferme', 'annule']),
        ~Ticket.id.in_(seen)
    ).count()


def unread_messages_count(user):
    """Messages privés reçus par `user` et pas encore lus."""
    return Message.query.filter_by(receiver_id=user.id, is_read=False).count()


def can_access_ticket(user, ticket):
    if user.has_permission('tickets.voir_tous'):
        return True
    return ticket_in_my_scope(user, ticket)


def ticket_in_my_scope(user, ticket):
    """Ticket « à moi » : créé par moi, assigné à moi, ou de mon département / en collaboration avec moi."""
    if ticket.createur_id == user.id or ticket.assigne_a_id == user.id:
        return True
    if user.departement_id:
        if ticket.departement_id == user.departement_id:
            return True
        if any(d.id == user.departement_id for d in ticket.departements_collab):
            return True
    return any(c.id == user.id for c in ticket.collaborateurs)


def can_ticket(user, action, ticket=None):
    """Droit d'agir sur les tickets, séparé en deux portées :
    `tickets.<action>` = tous les tickets ; `tickets.<action>_mes` = uniquement mes tickets.
    Sans `ticket`, indique si l'utilisateur détient l'un des deux droits (affichage des boutons)."""
    if user.has_permission(f'tickets.{action}'):
        return True
    if not user.has_permission(f'tickets.{action}_mes'):
        return False
    return ticket is None or ticket_in_my_scope(user, ticket)


CLOSED_STATUSES = ('resolu', 'ferme')


def can_change_status(user, ticket, target):
    """Changer le statut d'un ticket : accès au ticket + permission dédiée, sans exception créateur / assigné.
    Résoudre, fermer ou rouvrir = `tickets.cloturer(_mes)` ; tout autre changement = `tickets.modifier(_mes)`."""
    if not can_access_ticket(user, ticket):
        return False
    if target in CLOSED_STATUSES or ticket.statut in CLOSED_STATUSES:
        return can_ticket(user, 'cloturer', ticket)
    return can_ticket(user, 'modifier', ticket)


def can_work_on_ticket(user, ticket):
    """Droit « technique » sur un ticket (notes internes) : modifier ou clôturer, sur tous ou sur les miens."""
    return can_ticket(user, 'modifier', ticket) or can_ticket(user, 'cloturer', ticket)


# ───────────────────────── Garde d'accès par permission ─────────────────────────
def home_endpoint(user):
    """Page d'accueil sûre pour `user` : le tableau de bord s'il y a droit, sinon son profil (jamais de boucle)."""
    if user.is_authenticated and user.has_permission('dashboard.voir'):
        return 'tickets.tableau_bord'
    return 'parametres.profil'


def deny_access(message="Accès non autorisé."):
    """Refus uniforme : 403 JSON pour les appels d'API, sinon message + retour à une page autorisée."""
    from flask import flash, jsonify, redirect, request, url_for
    from flask_login import current_user
    wants_json = request.is_json or request.path.startswith(('/api/', '/chat/api/')) \
        or request.accept_mimetypes.best == 'application/json'
    if wants_json:
        return jsonify({'success': False, 'error': message, 'message': message}), 403
    flash(message, 'danger')
    return redirect(url_for(home_endpoint(current_user)))


def permission_required(*codes, message="Accès non autorisé."):
    """Décorateur : exige l'une des permissions `codes` (aucun passe-droit lié à un niveau)."""
    from functools import wraps
    from flask import redirect, url_for
    from flask_login import current_user

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.connexion'))
            if not any(current_user.has_permission(c) for c in codes):
                return deny_access(message)
            return f(*args, **kwargs)
        return wrapper
    return decorator
