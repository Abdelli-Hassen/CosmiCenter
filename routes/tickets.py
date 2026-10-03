"""
Routes de gestion des tickets pour CosmittoDesk
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Ticket, Utilisateur, Departement, CategorieTicket, Commentaire, HistoriqueTicket
from datetime import datetime, timedelta
import logging

# Créer le blueprint
tickets_bp = Blueprint('tickets', __name__)
logger = logging.getLogger(__name__)


@tickets_bp.route('/tableau-bord')
@login_required
def tableau_bord():
    """Tableau de bord principal"""
    
    # Query de base
    from sqlalchemy import or_
    if current_user.has_permission('tickets.voir_tous'):
        base_query = Ticket.query
    else:
        base_query = Ticket.query.filter(
            or_(
                Ticket.createur_id == current_user.id,
                Ticket.assigne_a_id == current_user.id,
                Ticket.departement_id == current_user.departement_id
            )
        )
        
    stats = {
        'total': base_query.count(),
        'ouvert': base_query.filter_by(statut='ouvert').count(),
        'en_cours': base_query.filter_by(statut='en_cours').count(),
        'resolu': base_query.filter_by(statut='resolu').count(),
    }
    
    # Tickets récents
    tickets_recents = base_query.order_by(Ticket.date_creation.desc()).limit(100).all()
    
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
    departement_id = request.args.get('departement_id')
    
    # Query de base
    if current_user.has_permission('tickets.voir_tous'):
        query = Ticket.query
    else:
        from sqlalchemy import or_
        query = Ticket.query.filter(
            or_(
                Ticket.createur_id == current_user.id,
                Ticket.assigne_a_id == current_user.id,
                Ticket.departement_id == current_user.departement_id
            )
        )
    
    # Appliquer les filtres
    if statut:
        query = query.filter_by(statut=statut)
    if priorite:
        query = query.filter_by(priorite=priorite)
    if departement_id:
        query = query.join(CategorieTicket).filter(CategorieTicket.departement_id == departement_id)
    
    # Tri et pagination
    sort_by = request.args.get('sort_by', 'date_creation')
    order = request.args.get('order', 'desc')
    
    sort_column = getattr(Ticket, sort_by, Ticket.date_creation) if hasattr(Ticket, sort_by) else Ticket.date_creation
    if sort_by == 'id':
        sort_column = Ticket.numero
        
    if order == 'asc':
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
        
    page = request.args.get('page', 1, type=int)
    tickets = query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    departements = Departement.query.filter_by(actif=True).all()
    
    return render_template('tickets/liste.html', 
                         tickets=tickets,
                         departements=departements,
                         page_title="Tous les tickets")

@tickets_bp.route('/mes-tickets')
@login_required
def mes_tickets():
    """Liste de mes tickets"""
    # Filtres
    statut = request.args.get('statut')
    priorite = request.args.get('priorite')
    departement_id = request.args.get('departement_id')
    
    # Query de base: créé par, assigné à, ou département
    from sqlalchemy import or_
    query = Ticket.query.filter(
        or_(
            Ticket.createur_id == current_user.id,
            Ticket.assigne_a_id == current_user.id,
            Ticket.departement_id == current_user.departement_id
        )
    )
    
    # Appliquer les filtres
    if statut:
        query = query.filter_by(statut=statut)
    if priorite:
        query = query.filter_by(priorite=priorite)
    if departement_id:
        query = query.join(CategorieTicket).filter(CategorieTicket.departement_id == departement_id)
    
    # Tri et pagination
    sort_by = request.args.get('sort_by', 'date_creation')
    order = request.args.get('order', 'desc')
    
    sort_column = getattr(Ticket, sort_by, Ticket.date_creation) if hasattr(Ticket, sort_by) else Ticket.date_creation
    if sort_by == 'id':
        sort_column = Ticket.numero
        
    if order == 'asc':
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
        
    page = request.args.get('page', 1, type=int)
    tickets = query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    departements = Departement.query.filter_by(actif=True).all()
    
    return render_template('tickets/liste.html', 
                         tickets=tickets,
                         departements=departements,
                         page_title="Mes tickets")


@tickets_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau():
    """Créer un nouveau ticket"""
    if request.method == 'POST':
        try:
            type_ticket = request.form.get('type_ticket', 'demande')
            if type_ticket == 'autre':
                type_ticket = request.form.get('custom_type', 'Autre')
                
            routing_type = request.form.get('routing_type', 'all')
            
            ticket = Ticket(
                numero=Ticket.generer_numero(),
                titre=request.form.get('titre'),
                description=request.form.get('description'),
                type_ticket=type_ticket,
                priorite=request.form.get('priorite', 'normale'),
                departement_id=request.form.get('departement_id') or None,
                createur_id=current_user.id
            )
            
            if routing_type == 'specific':
                ticket.assigne_a_id = request.form.get('assigne_a_id') or None
            
            db.session.add(ticket)
            db.session.flush() # Ensure we have the ticket ID
            
            if routing_type == 'collab':
                # Handle Collaboration Departments
                collab_depts = request.form.getlist('collab_departements[]')
                for dept_id in collab_depts:
                    if dept_id:
                        dept = Departement.query.get(dept_id)
                        if dept:
                            ticket.departements_collab.append(dept)
                
                # Handle Collaboration Users
                collab_users = request.form.getlist('collab_users[]')
                for user_id in collab_users:
                    if user_id:
                        user = Utilisateur.query.get(user_id)
                        if user:
                            ticket.collaborateurs.append(user)
            
            db.session.add(ticket)
            db.session.flush() # Ensure we have the ticket ID
            
            # Handle Sub-tasks (Checklist)
            from models import Tache
            taches_titres = request.form.getlist('taches[]')
            for i, titre in enumerate(taches_titres):
                titre = titre.strip()
                if titre:
                    tache = Tache(
                        ticket_id=ticket.id,
                        titre=titre,
                        ordre=i
                    )
                    db.session.add(tache)
            
            # Handle File Attachments
            import os
            import uuid
            from werkzeug.utils import secure_filename
            from models import PieceJointe
            
            UPLOAD_FOLDER = os.path.join(request.root_path, 'static', 'uploads', 'tickets')
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)
                
            fichiers = request.files.getlist('attachments')
            for f in fichiers:
                if f and f.filename:
                    nom_original = secure_filename(f.filename)
                    ext = nom_original.rsplit('.', 1)[1].lower() if '.' in nom_original else 'bin'
                    nouveau_nom = f"{uuid.uuid4().hex}.{ext}"
                    chemin = os.path.join(UPLOAD_FOLDER, nouveau_nom)
                    f.save(chemin)
                    
                    taille = os.path.getsize(chemin)
                    pj = PieceJointe(
                        ticket_id=ticket.id,
                        nom_fichier=nouveau_nom,
                        nom_original=nom_original,
                        type_mime=f.content_type,
                        taille=taille,
                        chemin=f'uploads/tickets/{nouveau_nom}',
                        uploade_par_id=current_user.id
                    )
                    db.session.add(pj)
            
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
    utilisateurs = Utilisateur.query.filter_by(actif=True).order_by(Utilisateur.nom).all()
    
    return render_template('tickets/nouveau.html',
                         departements=departements,
                         utilisateurs=utilisateurs)


@tickets_bp.route('/<ticket_id>')
@login_required
def detail(ticket_id):
    """Détail d'un ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Vérifier les permissions
    if not current_user.has_permission('tickets.voir_tous'):
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
    
    # Seul le créateur ou un manager/admin peut modifier complètement le ticket
    est_admin = current_user.role and current_user.role.niveau >= 70
    if not est_admin and ticket.createur_id != current_user.id:
        flash("Seul le créateur du ticket peut en modifier les détails. Les agents peuvent uniquement changer le statut.", "danger")
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    if request.method == 'POST':
        try:
            type_ticket = request.form.get('type_ticket', 'demande')
            if type_ticket == 'autre':
                type_ticket = request.form.get('custom_type', 'Autre')

            # Track changes
            changes = []
            if ticket.titre != request.form.get('titre'):
                changes.append(('Titre', ticket.titre, request.form.get('titre')))
            if ticket.type_ticket != type_ticket:
                changes.append(('Type', ticket.type_ticket, type_ticket))
            if ticket.priorite != request.form.get('priorite'):
                changes.append(('Priorité', ticket.priorite, request.form.get('priorite')))
            if ticket.statut != request.form.get('statut'):
                changes.append(('Statut', ticket.statut, request.form.get('statut')))

            for champ, old_val, new_val in changes:
                db.session.add(HistoriqueTicket(
                    ticket_id=ticket.id,
                    utilisateur_id=current_user.id,
                    action=f"Modification: {champ}",
                    champ_modifie=champ,
                    ancienne_valeur=old_val,
                    nouvelle_valeur=new_val
                ))

            ticket.titre = request.form.get('titre')
            ticket.description = request.form.get('description')
            ticket.priorite = request.form.get('priorite')
            ticket.statut = request.form.get('statut')
            ticket.type_ticket = type_ticket
            ticket.departement_id = request.form.get('departement_id') or None

            # Routing type
            routing_type = request.form.get('routing_type', 'all')

            if routing_type == 'specific':
                ticket.assigne_a_id = request.form.get('assigne_a_id') or None
                ticket.collaborateurs.clear()
                ticket.departements_collab.clear()
            elif routing_type == 'collab':
                ticket.assigne_a_id = None
                # Update collaboration departments
                ticket.departements_collab.clear()
                for dept_id in request.form.getlist('collab_departements[]'):
                    if dept_id:
                        dept = Departement.query.get(dept_id)
                        if dept:
                            ticket.departements_collab.append(dept)
                # Update collaboration users
                ticket.collaborateurs.clear()
                for user_id in request.form.getlist('collab_users[]'):
                    if user_id:
                        user = Utilisateur.query.get(user_id)
                        if user:
                            ticket.collaborateurs.append(user)
            else:  # 'all'
                ticket.assigne_a_id = None
                ticket.collaborateurs.clear()
                ticket.departements_collab.clear()

            # Handle existing checklist tasks (update titles + completion)
            from models import Tache
            taches_terminees = set(request.form.getlist('taches_terminees[]'))
            taches_existantes = {k.split('[')[1].rstrip(']'): v
                                 for k, v in request.form.items()
                                 if k.startswith('taches_existantes[')}

            # Load current tasks by ID to update or delete
            existing_ids = {t.id for t in ticket.taches}
            submitted_ids = set(taches_existantes.keys())

            for tache in ticket.taches:
                if tache.id in submitted_ids:
                    titre = taches_existantes[tache.id].strip()
                    if titre:
                        tache.titre = titre
                        tache.terminee = tache.id in taches_terminees
                        if tache.terminee and not tache.date_completion:
                            tache.date_completion = datetime.utcnow()
                        elif not tache.terminee:
                            tache.date_completion = None
                    else:
                        db.session.delete(tache)
                else:
                    # Was removed from form (user clicked ×)
                    db.session.delete(tache)

            # Add brand-new checklist items
            new_taches = request.form.getlist('taches[]')
            max_ordre = max((t.ordre for t in ticket.taches), default=-1) + 1
            for i, titre in enumerate(new_taches):
                titre = titre.strip()
                if titre:
                    db.session.add(Tache(ticket_id=ticket.id, titre=titre, ordre=max_ordre + i))

            # Handle new file attachments
            import os, uuid as uuid_mod
            from werkzeug.utils import secure_filename
            from models import PieceJointe
            UPLOAD_FOLDER = os.path.join(request.root_path, 'static', 'uploads', 'tickets')
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            for f in request.files.getlist('attachments'):
                if f and f.filename:
                    nom_original = secure_filename(f.filename)
                    ext = nom_original.rsplit('.', 1)[1].lower() if '.' in nom_original else 'bin'
                    nouveau_nom = f"{uuid_mod.uuid4().hex}.{ext}"
                    chemin = os.path.join(UPLOAD_FOLDER, nouveau_nom)
                    f.save(chemin)
                    db.session.add(PieceJointe(
                        ticket_id=ticket.id,
                        nom_fichier=nouveau_nom,
                        nom_original=nom_original,
                        type_mime=f.content_type,
                        taille=os.path.getsize(chemin),
                        chemin=f'uploads/tickets/{nouveau_nom}',
                        uploade_par_id=current_user.id
                    ))

            db.session.commit()
            flash('Ticket modifié avec succès', 'success')
            logger.info(f'Ticket modifié: {ticket.numero} par {current_user.email}')
            return redirect(url_for('tickets.detail', ticket_id=ticket_id))

        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la modification du ticket: {str(e)}')
            flash('Erreur lors de la modification', 'danger')

    departements = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()
    utilisateurs = Utilisateur.query.filter_by(actif=True).order_by(Utilisateur.nom).all()

    return render_template('tickets/modifier.html',
                         ticket=ticket,
                         departements=departements,
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


@tickets_bp.route('/<ticket_id>/statut', methods=['POST'])
@login_required
def changer_statut(ticket_id):
    """Mettre à jour rapidement le statut ou l'assignation d'un ticket depuis la barre latérale"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Vérification des droits : l'agent assigné, le créateur, ou un admin
    est_admin = current_user.role and current_user.role.niveau >= 70
    if not est_admin and ticket.createur_id != current_user.id and ticket.assigne_a_id != current_user.id:
        flash("Vous n'êtes pas autorisé à modifier ce ticket.", "danger")
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    nouveau_statut = request.form.get('statut')
    nouvel_assigne = request.form.get('assigne_a_id')

    try:
        modifie = False
        if nouveau_statut and nouveau_statut in ['nouveau', 'en_cours', 'en_attente', 'resolu', 'ferme', 'annule']:
            if ticket.statut != nouveau_statut:
                hist = HistoriqueTicket(ticket_id=ticket.id, utilisateur_id=current_user.id, action='Modification de statut', champ_modifie='Statut', ancienne_valeur=ticket.statut, nouvelle_valeur=nouveau_statut)
                db.session.add(hist)
                ticket.statut = nouveau_statut
                if nouveau_statut == 'resolu' and not ticket.date_resolution:
                    ticket.date_resolution = datetime.utcnow()
                modifie = True

        # Mise à jour de l'assignation si l'utilisateur a le droit
        if nouvel_assigne is not None and current_user.has_permission('tickets.assigner'):
            nouvel_assigne_val = nouvel_assigne if nouvel_assigne else None
            if ticket.assigne_a_id != nouvel_assigne_val:
                ancien_nom = (ticket.assigne_a.prenom + ' ' + ticket.assigne_a.nom) if ticket.assigne_a else 'Non assigné'
                nouvel_user = Utilisateur.query.get(nouvel_assigne_val) if nouvel_assigne_val else None
                nouveau_nom = (nouvel_user.prenom + ' ' + nouvel_user.nom) if nouvel_user else 'Non assigné'
                hist = HistoriqueTicket(ticket_id=ticket.id, utilisateur_id=current_user.id, action='Changement d\'assignation', champ_modifie='Assigné à', ancienne_valeur=ancien_nom, nouvelle_valeur=nouveau_nom)
                db.session.add(hist)
                ticket.assigne_a_id = nouvel_assigne_val
                modifie = True

        if modifie:
            db.session.commit()
            flash('Le ticket a été mis à jour.', 'success')
            logger.info(f"Ticket {ticket.numero} mis à jour via action rapide par {current_user.email}")
            
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur lors de la mise à jour rapide: {str(e)}')
        flash('Erreur lors de la mise à jour.', 'danger')
            
    return redirect(url_for('tickets.detail', ticket_id=ticket_id))


@tickets_bp.route('/<ticket_id>/fermer', methods=['POST'])
@login_required
def fermer(ticket_id):
    """Fermer un ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Vérifier les permissions
    if not current_user.has_permission('tickets.fermer'):
        if ticket.createur_id != current_user.id and ticket.assigne_a_id != current_user.id:
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    try:
        hist = HistoriqueTicket(ticket_id=ticket.id, utilisateur_id=current_user.id, action='Fermeture de ticket', champ_modifie='Statut', ancienne_valeur=ticket.statut, nouvelle_valeur='ferme')
        db.session.add(hist)
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

@tickets_bp.route('/<ticket_id>/reouvrir', methods=['POST'])
@login_required
def reouvrir(ticket_id):
    """Réouvrir un ticket fermé"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Vérifier les permissions (idem fermer)
    if not current_user.has_permission('tickets.fermer'):
        if ticket.createur_id != current_user.id and ticket.assigne_a_id != current_user.id:
            flash('Accès non autorisé', 'danger')
            return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    try:
        hist = HistoriqueTicket(ticket_id=ticket.id, utilisateur_id=current_user.id, action='Réouverture de ticket', champ_modifie='Statut', ancienne_valeur=ticket.statut, nouvelle_valeur='en_cours')
        db.session.add(hist)
        ticket.statut = 'en_cours'
        ticket.date_fermeture = None
        db.session.commit()
        
        flash('Ticket réouvert avec succès', 'success')
        logger.info(f'Ticket réouvert: {ticket.numero} par {current_user.email}')
    
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur lors de la réouverture du ticket: {str(e)}')
        flash('Erreur lors de la réouverture', 'danger')
    
    return redirect(url_for('tickets.detail', ticket_id=ticket_id))

@tickets_bp.route('/tache/<tache_id>/toggle', methods=['POST'])
@login_required
def toggle_tache(tache_id):
    """Marquer une sous-tâche comme terminée ou non"""
    from models import Tache
    from flask import jsonify
    
    tache = Tache.query.get_or_404(tache_id)
    ticket = tache.ticket
    
    # Check permissions (basic check)
    if not current_user.has_permission('tickets.voir_tous'):
        if ticket.createur_id != current_user.id and ticket.assigne_a_id != current_user.id:
            return jsonify({'error': 'Accès non autorisé'}), 403
            
    try:
        tache.terminee = not tache.terminee
        if tache.terminee:
            tache.date_completion = datetime.utcnow()
        else:
            tache.date_completion = None
        db.session.commit()
        return jsonify({'success': True, 'terminee': tache.terminee})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ─── Base de connaissances (FAQ) ────────────────────────────────────────────

@tickets_bp.route('/faq')
@login_required
def faq_liste():
    """Liste des guides de la base de connaissances"""
    return render_template('faq/liste.html')


@tickets_bp.route('/faq/<article_id>')
@login_required
def faq_detail(article_id):
    """Lecture d'un article de la base de connaissances"""
    return render_template('faq/detail.html')


# ─── Chat / Messagerie ───────────────────────────────────────────────────────

@tickets_bp.route('/chat')
@login_required
def chat_inbox():
    """Centre de messagerie"""
    return render_template('chat/inbox.html')
