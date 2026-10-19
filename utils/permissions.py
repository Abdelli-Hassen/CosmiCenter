"""Règles d'accès communes (visibilité des tickets, niveaux de rôle)."""
from sqlalchemy import false, or_

from models import db, Departement, HistoriqueTicket, Message, Ticket, Utilisateur


def role_level(user):
    if user is None or not getattr(user, 'role', None) or user.role.niveau is None:
        return 0
    return user.role.niveau


def is_admin(user):
    return role_level(user) >= 90


def can_assign_role(actor, role):
    """Un utilisateur ne peut attribuer qu'un rôle de niveau inférieur ou égal au sien."""
    if role is None:
        return True
    return (role.niveau or 0) <= role_level(actor)


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
    if ticket.createur_id == user.id or ticket.assigne_a_id == user.id:
        return True
    if user.departement_id:
        if ticket.departement_id == user.departement_id:
            return True
        if any(d.id == user.departement_id for d in ticket.departements_collab):
            return True
    return any(c.id == user.id for c in ticket.collaborateurs)


def can_manage_ticket(user, ticket):
    """Changer statut / fermer : accès au ticket + (créateur, assigné, admin ou permission dédiée)."""
    if role_level(user) >= 70 or user.has_permission('tickets.modifier') or user.has_permission('tickets.cloturer'):
        return True
    return ticket.createur_id == user.id or ticket.assigne_a_id == user.id
