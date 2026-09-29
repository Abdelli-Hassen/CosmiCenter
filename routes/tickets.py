"""
Routes de gestion des tickets pour CosmittoDesk
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Ticket, Utilisateur, Departement, CategorieTicket, Commentaire
from datetime import datetime, timedelta
import logging

# Créer le blueprint
tickets_bp = Blueprint('tickets', __name__)
logger = logging.getLogger(__name__)


@tickets_bp.route('/tableau-bord')
@login_required
def tableau_bord():
    """Tableau de bord principal"""
    # Statistiques globales
    stats = {
        'total': Ticket.query.count(),
        'ouvert': Ticket.query.filter_by(statut='ouvert').count(),
        'en_cours': Ticket.query.filter_by(statut='en_cours').count(),
        'resolu': Ticket.query.filter_by(statut='resolu').count(),
    }
    
    # Tickets récents
    if current_user.role and current_user.role.niveau >= 70:
        tickets_recents = Ticket.query.order_by(Ticket.date_creation.desc()).limit(10).all()
    else:
        tickets_recents = Ticket.query.filter_by(createur_id=current_user.id)\
            .order_by(Ticket.date_creation.desc()).limit(10).all()
    
    return render_template('tickets/tableau_bord.html', 
                         stats=stats, 
                         tickets=tickets_recents)


@tickets_bp.route('/liste')
@login_required
def liste():
    """Liste de tous les tickets"""
    # Filtres
    statut = request.args.get('statut')
    priorite = request.args.get('priorite')
    departement_id = request.args.get('departement')
    
    # Query de base
    if current_user.role and current_user.role.niveau >= 70:
        query = Ticket.query
    else:
        query = Ticket.query.filter_by(createur_id=current_user.id)
    
    # Appliquer les filtres
    if statut:
        query = query.filter_by(statut=statut)
    if priorite:
        query = query.filter_by(priorite=priorite)
    if departement_id:
        query = query.filter_by(departement_id=departement_id)
    
    # Tri et pagination
    page = request.args.get('page', 1, type=int)
    tickets = query.order_by(Ticket.date_creation.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    departements = Departement.query.filter_by(actif=True).all()
    
    return render_template('tickets/liste.html', 
                         tickets=tickets,
                         departements=departements)


@tickets_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau():
    """Créer un nouveau ticket"""
    if request.method == 'POST':
        try:
            ticket = Ticket(
                titre=request.form.get('titre'),
                description=request.form.get('description'),
                type_ticket=request.form.get('type_ticket', 'demande'),
                priorite=request.form.get('priorite', 'normale'),
                departement_id=request.form.get('departement_id'),
                categorie_id=request.form.get('categorie_id'),
                createur_id=current_user.id
            )
            
            db.session.add(ticket)
            db.session.commit()
            
            flash('Ticket créé avec succès', 'success')
            logger.info(f'Nouveau ticket créé: {ticket.numero} par {current_user.email}')
            
            return redirect(url_for('tickets.detail', ticket_id=ticket.id))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la création du ticket: {str(e)}')
            flash('Erreur lors de la création du ticket', 'danger')
    
    # Récupérer les données pour le formulaire
    departements = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()
    # Group categories by department for display
    cats_par_dept = {}
    for cat in CategorieTicket.query.filter_by(actif=True).order_by(CategorieTicket.nom).all():
        dept = cat.departement
        if not dept:
            continue
        if dept.id not in cats_par_dept:
            cats_par_dept[dept.id] = {
                'id': dept.id, 'nom': dept.nom,
                'couleur': dept.couleur or '#3B82F6', 'cats': []
            }
        cats_par_dept[dept.id]['cats'].append(cat)
    cats_par_dept = sorted(cats_par_dept.values(), key=lambda d: d['nom'])
    categories = CategorieTicket.query.filter_by(actif=True).all()
    
    return render_template('tickets/nouveau.html',
                         departements=departements,
                         categories=categories,
                         cats_par_dept=cats_par_dept)


@tickets_bp.route('/<ticket_id>')
@login_required
def detail(ticket_id):
    """Détail d'un ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Vérifier les permissions
    if not (current_user.role and current_user.role.niveau >= 70):
        if ticket.createur_id != current_user.id and ticket.assigne_a_id != current_user.id:
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('tickets.liste'))
    
    # Récupérer les commentaires
    commentaires = Commentaire.query.filter_by(ticket_id=ticket_id)\
        .order_by(Commentaire.date_creation.asc()).all()
    
    # Récupérer les utilisateurs pour l'assignation
    utilisateurs = Utilisateur.query.filter_by(actif=True).all()
    
    return render_template('tickets/detail.html',
                         ticket=ticket,
                         commentaires=commentaires,
                         utilisateurs=utilisateurs)


@tickets_bp.route('/<ticket_id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier(ticket_id):
    """Modifier un ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Vérifier les permissions
    if not (current_user.role and current_user.role.niveau >= 70):
        if ticket.createur_id != current_user.id:
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    if request.method == 'POST':
        try:
            ticket.titre = request.form.get('titre')
            ticket.description = request.form.get('description')
            ticket.priorite = request.form.get('priorite')
            ticket.statut = request.form.get('statut')

            if current_user.role and current_user.role.niveau >= 70:
                ticket.assigne_a_id = request.form.get('assigne_a_id') or None
            
            db.session.commit()
            
            flash('Ticket modifié avec succès', 'success')
            logger.info(f'Ticket modifié: {ticket.numero} par {current_user.email}')
            
            return redirect(url_for('tickets.detail', ticket_id=ticket_id))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la modification du ticket: {str(e)}')
            flash('Erreur lors de la modification', 'danger')
    
    departements = Departement.query.filter_by(actif=True).all()
    categories = CategorieTicket.query.filter_by(actif=True).all()
    utilisateurs = Utilisateur.query.filter_by(actif=True).all()
    
    return render_template('tickets/modifier.html',
                         ticket=ticket,
                         departements=departements,
                         categories=categories,
                         utilisateurs=utilisateurs)


@tickets_bp.route('/<ticket_id>/commenter', methods=['POST'])
@login_required
def commenter(ticket_id):
    """Ajouter un commentaire à un ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    try:
        commentaire = Commentaire(
            ticket_id=ticket_id,
            auteur_id=current_user.id,
            contenu=request.form.get('contenu'),
            interne=request.form.get('interne', False)
        )
        
        db.session.add(commentaire)
        db.session.commit()
        
        flash('Commentaire ajouté', 'success')
        logger.info(f'Commentaire ajouté au ticket {ticket.numero} par {current_user.email}')
    
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur lors de l\'ajout du commentaire: {str(e)}')
        flash('Erreur lors de l\'ajout du commentaire', 'danger')
    
    return redirect(url_for('tickets.detail', ticket_id=ticket_id))


@tickets_bp.route('/<ticket_id>/fermer', methods=['POST'])
@login_required
def fermer(ticket_id):
    """Fermer un ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Vérifier les permissions
    if not (current_user.role and current_user.role.niveau >= 70):
        if ticket.createur_id != current_user.id and ticket.assigne_a_id != current_user.id:
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    try:
        ticket.statut = 'ferme'
        ticket.date_fermeture = datetime.utcnow()
        db.session.commit()
        
        flash('Ticket fermé', 'success')
        logger.info(f'Ticket fermé: {ticket.numero} par {current_user.email}')
    
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur lors de la fermeture du ticket: {str(e)}')
        flash('Erreur lors de la fermeture', 'danger')
    
    return redirect(url_for('tickets.detail', ticket_id=ticket_id))
