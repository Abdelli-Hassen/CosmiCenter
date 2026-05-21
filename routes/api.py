"""
API REST pour CosmittoDesk
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, Ticket, Utilisateur, Departement, CategorieTicket
from datetime import datetime, timedelta
import logging

# Créer le blueprint
api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)


def json_response(data=None, message=None, success=True, status=200):
    """Helper pour créer des réponses JSON standardisées"""
    response = {
        'success': success,
        'message': message,
        'data': data
    }
    return jsonify(response), status


@api_bp.route('/stats/globales')
@login_required
def stats_globales():
    """Statistiques globales du système"""
    try:
        stats = {
            'tickets': {
                'total': Ticket.query.count(),
                'ouvert': Ticket.query.filter_by(statut='ouvert').count(),
                'en_cours': Ticket.query.filter_by(statut='en_cours').count(),
                'resolu': Ticket.query.filter_by(statut='resolu').count(),
                'ferme': Ticket.query.filter_by(statut='ferme').count(),
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
        logger.error(f'Erreur lors de la récupération des stats: {str(e)}')
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
            Ticket.date_creation >= date_debut
        ).group_by(
            db.func.date(Ticket.date_creation)
        ).all()
        
        data = [
            {'date': str(t.date), 'count': t.count}
            for t in tickets
        ]
        
        return json_response(data=data, message='Statistiques par jour récupérées')
    
    except Exception as e:
        logger.error(f'Erreur lors de la récupération des stats par jour: {str(e)}')
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
        ).group_by(
            Departement.nom
        ).all()
        
        data = [
            {'departement': s.nom, 'count': s.count}
            for s in stats
        ]
        
        return json_response(data=data, message='Statistiques par département récupérées')
    
    except Exception as e:
        logger.error(f'Erreur lors de la récupération des stats par département: {str(e)}')
        return json_response(success=False, message='Erreur serveur', status=500)


@api_bp.route('/stats/tickets-par-priorite')
@login_required
def stats_tickets_par_priorite():
    """Nombre de tickets par priorité"""
    try:
        stats = db.session.query(
            Ticket.priorite,
            db.func.count(Ticket.id).label('count')
        ).group_by(
            Ticket.priorite
        ).all()
        
        data = [
            {'priorite': s.priorite, 'count': s.count}
            for s in stats
        ]
        
        return json_response(data=data, message='Statistiques par priorité récupérées')
    
    except Exception as e:
        logger.error(f'Erreur lors de la récupération des stats par priorité: {str(e)}')
        return json_response(success=False, message='Erreur serveur', status=500)


@api_bp.route('/tickets/<ticket_id>/statut', methods=['PUT'])
@login_required
def changer_statut_ticket(ticket_id):
    """Changer le statut d'un ticket"""
    try:
        ticket = Ticket.query.get_or_404(ticket_id)
        
        # Vérifier les permissions
        if current_user.role not in ['admin', 'responsable']:
            if ticket.createur_id != current_user.id and ticket.assigne_id != current_user.id:
                return json_response(
                    success=False, 
                    message='Accès non autorisé', 
                    status=403
                )
        
        data = request.get_json()
        nouveau_statut = data.get('statut')
        
        if nouveau_statut not in ['ouvert', 'en_cours', 'resolu', 'ferme', 'en_attente']:
            return json_response(
                success=False, 
                message='Statut invalide', 
                status=400
            )
        
        ticket.statut = nouveau_statut
        
        if nouveau_statut == 'ferme':
            ticket.date_fermeture = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f'Statut du ticket {ticket.numero} changé en {nouveau_statut} par {current_user.email}')
        
        return json_response(
            data={'statut': ticket.statut},
            message='Statut mis à jour'
        )
    
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur lors du changement de statut: {str(e)}')
        return json_response(success=False, message='Erreur serveur', status=500)


@api_bp.route('/tickets/<ticket_id>/assigner', methods=['PUT'])
@login_required
def assigner_ticket(ticket_id):
    """Assigner un ticket à un utilisateur"""
    try:
        # Vérifier les permissions
        if current_user.role not in ['admin', 'responsable']:
            return json_response(
                success=False, 
                message='Accès réservé aux administrateurs et responsables', 
                status=403
            )
        
        ticket = Ticket.query.get_or_404(ticket_id)
        data = request.get_json()
        utilisateur_id = data.get('utilisateur_id')
        
        if utilisateur_id:
            utilisateur = Utilisateur.query.get_or_404(utilisateur_id)
            if not utilisateur.actif:
                return json_response(
                    success=False, 
                    message='Utilisateur inactif', 
                    status=400
                )
            
            ticket.assigne_id = utilisateur_id
        else:
            ticket.assigne_id = None
        
        db.session.commit()
        
        logger.info(f'Ticket {ticket.numero} assigné à {utilisateur_id} par {current_user.email}')
        
        return json_response(
            data={'assigne_id': ticket.assigne_id},
            message='Ticket assigné'
        )
    
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur lors de l\'assignation: {str(e)}')
        return json_response(success=False, message='Erreur serveur', status=500)


@api_bp.route('/recherche/utilisateurs')
@login_required
def rechercher_utilisateurs():
    """Rechercher des utilisateurs"""
    try:
        query = request.args.get('q', '')
        
        if len(query) < 2:
            return json_response(data=[], message='Requête trop courte')
        
        utilisateurs = Utilisateur.query.filter(
            db.or_(
                Utilisateur.nom.ilike(f'%{query}%'),
                Utilisateur.prenom.ilike(f'%{query}%'),
                Utilisateur.email.ilike(f'%{query}%')
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
        logger.error(f'Erreur lors de la recherche d\'utilisateurs: {str(e)}')
        return json_response(success=False, message='Erreur serveur', status=500)


@api_bp.route('/health')
def health_check():
    """Endpoint de santé pour monitoring"""
    return json_response(
        data={
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat()
        },
        message='Service opérationnel'
    )
