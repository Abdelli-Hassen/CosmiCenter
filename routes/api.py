"""
API REST pour CosmiCenter
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, Ticket, Utilisateur, Departement, Notification, Message
from utils.permissions import visible_tickets_query, can_access_ticket, can_manage_ticket, ticket_visibility_filter
from utils.security import like_escape
from datetime import datetime, timedelta
import logging

# Créer le blueprint
api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

STATUTS_VALIDES = ['nouveau', 'ouvert', 'en_cours', 'en_attente', 'resolu', 'ferme', 'annule']
STATUTS_OUVERTS = ['nouveau', 'ouvert']


def json_response(data=None, message=None, success=True, status=200):
    """Helper pour créer des réponses JSON standardisées"""
    response = {
        'success': success,
        'message': message,
        'data': data
    }
    return jsonify(response), status


def _visibility_clause():
    """Filtre de visibilité à ajouter aux requêtes d'agrégation (aucun filtre si voir_tous)."""
    if current_user.has_permission('tickets.voir_tous'):
        return db.true()
    return ticket_visibility_filter(current_user)


@api_bp.route('/stats/globales')
@login_required
def stats_globales():
    """Statistiques globales (limitées aux tickets visibles par l'utilisateur)"""
    try:
        q = visible_tickets_query(current_user)
        stats = {
            'tickets': {
                'total': q.count(),
                'ouvert': q.filter(Ticket.statut.in_(STATUTS_OUVERTS)).count(),
                'en_cours': q.filter(Ticket.statut == 'en_cours').count(),
                'resolu': q.filter(Ticket.statut == 'resolu').count(),
                'ferme': q.filter(Ticket.statut == 'ferme').count(),
            },
            'utilisateurs': {
                'total': Utilisateur.query.count(),
                'actifs': Utilisateur.query.filter_by(actif=True).count(),
            },
            'departements': {
                'total': Departement.query.count(),
                'actifs': Departement.query.filter_by(actif=True).count(),
            }
        }
        return json_response(data=stats, message='Statistiques récupérées')

    except Exception as e:
        logger.error(f'Erreur lors de la récupération des stats: {e}')
        return json_response(success=False, message='Erreur serveur', status=500)


@api_bp.route('/stats/tickets-par-jour')
@login_required
def stats_tickets_par_jour():
    """Nombre de tickets créés par jour sur les 30 derniers jours"""
    try:
        date_debut = datetime.utcnow() - timedelta(days=30)

        tickets = db.session.query(
            db.func.date(Ticket.date_creation).label('date'),
            db.func.count(Ticket.id).label('count')
        ).filter(
            Ticket.date_creation >= date_debut, _visibility_clause()
        ).group_by(
            db.func.date(Ticket.date_creation)
        ).order_by(db.func.date(Ticket.date_creation)).all()

        data = [{'date': str(t.date), 'count': t.count} for t in tickets]
        return json_response(data=data, message='Statistiques par jour récupérées')

    except Exception as e:
        logger.error(f'Erreur lors de la récupération des stats par jour: {e}')
        return json_response(success=False, message='Erreur serveur', status=500)


@api_bp.route('/stats/tickets-par-departement')
@login_required
def stats_tickets_par_departement():
    """Nombre de tickets par département"""
    try:
        stats = db.session.query(
            Departement.nom,
            db.func.count(Ticket.id).label('count')
        ).join(
            Ticket, Ticket.departement_id == Departement.id
        ).filter(_visibility_clause()).group_by(
            Departement.nom
        ).all()

        data = [{'departement': s.nom, 'count': s.count} for s in stats]
        return json_response(data=data, message='Statistiques par département récupérées')

    except Exception as e:
        logger.error(f'Erreur lors de la récupération des stats par département: {e}')
        return json_response(success=False, message='Erreur serveur', status=500)


@api_bp.route('/stats/tickets-par-priorite')
@login_required
def stats_tickets_par_priorite():
    """Nombre de tickets par priorité"""
    try:
        stats = db.session.query(
            Ticket.priorite,
            db.func.count(Ticket.id).label('count')
        ).filter(_visibility_clause()).group_by(
            Ticket.priorite
        ).all()

        data = [{'priorite': s.priorite, 'count': s.count} for s in stats]
        return json_response(data=data, message='Statistiques par priorité récupérées')

    except Exception as e:
        logger.error(f'Erreur lors de la récupération des stats par priorité: {e}')
        return json_response(success=False, message='Erreur serveur', status=500)


@api_bp.route('/tickets/<ticket_id>/statut', methods=['PUT'])
@login_required
def changer_statut_ticket(ticket_id):
    """Changer le statut d'un ticket"""
    try:
        ticket = Ticket.query.get_or_404(ticket_id)

        if not can_access_ticket(current_user, ticket) or not can_manage_ticket(current_user, ticket):
            return json_response(success=False, message='Accès non autorisé', status=403)

        data = request.get_json(silent=True) or {}
        nouveau_statut = data.get('statut')

        if nouveau_statut not in STATUTS_VALIDES:
            return json_response(success=False, message='Statut invalide', status=400)

        if ticket.statut != nouveau_statut:
            from routes.tickets import _apply_status
            from models import HistoriqueTicket
            db.session.add(HistoriqueTicket(
                ticket_id=ticket.id, utilisateur_id=current_user.id, action='Modification de statut',
                champ_modifie='Statut', ancienne_valeur=ticket.statut, nouvelle_valeur=nouveau_statut))
            _apply_status(ticket, nouveau_statut)
            db.session.commit()
            logger.info(f'Statut du ticket {ticket.numero} changé en {nouveau_statut} par {current_user.email}')

        return json_response(data={'statut': ticket.statut}, message='Statut mis à jour')

    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur lors du changement de statut: {e}')
        return json_response(success=False, message='Erreur serveur', status=500)


@api_bp.route('/tickets/<ticket_id>/assigner', methods=['PUT'])
@login_required
def assigner_ticket(ticket_id):
    """Assigner un ticket à un utilisateur"""
    try:
        if not current_user.has_permission('tickets.assigner'):
            return json_response(success=False, message="Accès réservé aux utilisateurs autorisés à assigner", status=403)

        ticket = Ticket.query.get_or_404(ticket_id)
        if not can_access_ticket(current_user, ticket):
            return json_response(success=False, message='Accès non autorisé', status=403)

        data = request.get_json(silent=True) or {}
        utilisateur_id = data.get('utilisateur_id')

        if utilisateur_id:
            utilisateur = Utilisateur.query.get_or_404(utilisateur_id)
            if not utilisateur.actif:
                return json_response(success=False, message='Utilisateur inactif', status=400)
            ticket.assigne_a_id = utilisateur.id
        else:
            ticket.assigne_a_id = None

        db.session.commit()
        logger.info(f'Ticket {ticket.numero} assigné à {utilisateur_id} par {current_user.email}')

        return json_response(data={'assigne_a_id': ticket.assigne_a_id}, message='Ticket assigné')

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'assignation: {e}")
        return json_response(success=False, message='Erreur serveur', status=500)


@api_bp.route('/recherche/utilisateurs')
@login_required
def rechercher_utilisateurs():
    """Rechercher des utilisateurs"""
    try:
        query = request.args.get('q', '').strip()

        if len(query) < 2:
            return json_response(data=[], message='Requête trop courte')

        like = f'%{like_escape(query)}%'
        utilisateurs = Utilisateur.query.filter(
            db.or_(
                Utilisateur.nom.ilike(like, escape='\\'),
                Utilisateur.prenom.ilike(like, escape='\\'),
                Utilisateur.email.ilike(like, escape='\\')
            )
        ).filter_by(actif=True).limit(10).all()

        data = [
            {
                'id': u.id,
                'nom': u.nom,
                'prenom': u.prenom,
                'email': u.email,
                'nom_complet': f'{u.prenom} {u.nom}'
            }
            for u in utilisateurs
        ]
        return json_response(data=data, message='Résultats de recherche')

    except Exception as e:
        logger.error(f"Erreur lors de la recherche d'utilisateurs: {e}")
        return json_response(success=False, message='Erreur serveur', status=500)


@api_bp.route('/health')
def health_check():
    """Endpoint de santé pour monitoring (vérifie aussi la base de données)"""
    try:
        db.session.execute(db.text('SELECT 1'))
        database = 'ok'
    except Exception:
        db.session.rollback()
        return json_response(data={'status': 'degraded', 'database': 'error'},
                             message='Base de données indisponible', success=False, status=503)
    return json_response(
        data={'status': 'healthy', 'database': database, 'timestamp': datetime.utcnow().isoformat()},
        message='Service opérationnel'
    )


@api_bp.route('/notifications/marquer-lues', methods=['POST'])
@login_required
def marquer_notifications_lues():
    """Marquer toutes les notifications de l'utilisateur comme lues"""
    try:
        Notification.query.filter_by(utilisateur_id=current_user.id, lue=False).update(
            {'lue': True, 'date_lecture': datetime.utcnow()})
        db.session.commit()
        return json_response(success=True, message='Notifications marquées comme lues.')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur marquer_notifications_lues: {e}')
        return json_response(success=False, message='Erreur serveur', status=500)


@api_bp.route('/notifications/poll')
@login_required
def poll_notifications():
    unread_notifs = Notification.query.filter_by(utilisateur_id=current_user.id, lue=False).count()
    unread_msgs = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()

    recent_notifs = Notification.query.filter_by(
        utilisateur_id=current_user.id,
        lue=False
    ).order_by(Notification.date_creation.desc()).limit(10).all()

    notifs_data = [{
        'id': n.id,
        'titre': n.titre,
        'message': n.message,
        'lien': n.lien,
        'date': n.date_creation.strftime('%d/%m/%Y %H:%M')
    } for n in recent_notifs]

    return json_response(data={
        'unread_notifications': unread_notifs,
        'unread_messages': unread_msgs,
        'notifications': notifs_data
    })


@api_bp.route('/notifications/tickets/<ticket_id>/mark-read', methods=['POST'])
@login_required
def mark_ticket_notifs_read(ticket_id):
    """Marque comme lues les notifications liées à un ticket (les identifiants de ticket sont des UUID)."""
    like = f'%/tickets/{like_escape(ticket_id)}%'
    Notification.query.filter(
        Notification.utilisateur_id == current_user.id,
        Notification.lien.like(like, escape='\\'),
        Notification.lue == False  # noqa: E712
    ).update({'lue': True, 'date_lecture': datetime.utcnow()}, synchronize_session=False)
    db.session.commit()
    return json_response(success=True)


@api_bp.route('/notifications/chat/mark-read', methods=['POST'])
@login_required
def mark_chat_notifs_read():
    Notification.query.filter(
        Notification.utilisateur_id == current_user.id,
        Notification.type_notification == 'chat',
        Notification.lue == False  # noqa: E712
    ).update({'lue': True, 'date_lecture': datetime.utcnow()}, synchronize_session=False)
    db.session.commit()
    return json_response(success=True)
