from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from models import db, Departement, Utilisateur, CategorieTicket, Ticket
from functools import wraps
from sqlalchemy import func
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

departements_bp = Blueprint('departements', __name__)


def admin_required(f):
    """Décorateur pour restreindre l'accès aux administrateurs"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('departements.gerer'):
            flash('Accès non autorisé.', 'danger')
            return redirect(url_for('tickets.tableau_bord'))
        return f(*args, **kwargs)
    return decorated_function


@departements_bp.route('/')
@login_required
def liste():
    """Liste tous les départements"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = Departement.query
    
    # Filtres
    if not current_user.has_permission('departements.gerer'):
        # Les utilisateurs normaux ne voient que leur département
        if current_user.departement_id:
            query = query.filter_by(id=current_user.departement_id)
        else:
            query = query.filter_by(id=None)  # Aucun résultat
    
    search = request.args.get('search', '')
    if search:
        query = query.filter(
            (Departement.nom.contains(search)) | 
            (Departement.description.contains(search))
        )
    
    actif_filter = request.args.get('actif', '')
    if actif_filter == '1':
        query = query.filter_by(actif=True)
    elif actif_filter == '0':
        query = query.filter_by(actif=False)
    
    departements = query.order_by(Departement.nom).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Statistiques détaillées pour chaque département
    STATUTS_NON_TERMINES = ['nouveau', 'en_cours', 'en_attente']
    for dept in departements.items:
        # Tickets reçus = assignés à ce département, pas terminés
        tickets_recus_ouverts = Ticket.query.filter(
            Ticket.departement_id == dept.id,
            Ticket.statut.in_(STATUTS_NON_TERMINES)
        ).count()

        # Tickets envoyés = créés par un membre de ce département, assignés à un autre département, pas terminés
        membres_ids = [m.id for m in dept.membres]
        if membres_ids:
            tickets_envoyes_ouverts = Ticket.query.filter(
                Ticket.createur_id.in_(membres_ids),
                Ticket.departement_id != dept.id,
                Ticket.statut.in_(STATUTS_NON_TERMINES)
            ).count()
        else:
            tickets_envoyes_ouverts = 0

        # Agents actifs dans ce département
        agents_actifs = sum(1 for m in dept.membres if m.actif)

        dept.stats = {
            'membres_actifs': agents_actifs,
            'membres_total': len(dept.membres),
            'tickets_recus_ouverts': tickets_recus_ouverts,
            'tickets_envoyes_ouverts': tickets_envoyes_ouverts,
            'tickets_total': Ticket.query.filter_by(departement_id=dept.id).count(),
        }
    
    return render_template('departements/liste.html', 
                         departements=departements,
                         search=search,
                         actif_filter=actif_filter)


@departements_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
@admin_required
def nouveau():
    """Créer un nouveau département"""
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        code = request.form.get('code', '').strip().upper()
        description = request.form.get('description', '').strip()
        email = request.form.get('email', '').strip()
        telephone = request.form.get('telephone', '').strip()
        localisation = request.form.get('localisation', '').strip()
        couleur = request.form.get('couleur', '#3B82F6')
        
        # Gestion du logo (enregistré dans la colonne icone)
        icone = request.form.get('icone', 'building')
        logo_file = request.files.get('logo')
        if logo_file and logo_file.filename:
            filename = secure_filename(logo_file.filename)
            upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, 'static/uploads'))
            os.makedirs(upload_folder, exist_ok=True)
            logo_file.save(os.path.join(upload_folder, filename))
            icone = filename
            
        responsable_id = request.form.get('responsable_id', '').strip() or None
        sla_reponse_heures = int(request.form.get('sla_reponse_heures', 4))
        sla_resolution_heures = int(request.form.get('sla_resolution_heures', 48))
        
        # Validation
        if not nom:
            flash('Le nom du département est requis.', 'danger')
            return render_template('departements/formulaire.html', utilisateurs=Utilisateur.query.all())
        
        # Vérifier l'unicité
        if Departement.query.filter_by(nom=nom).first():
            flash('Un département avec ce nom existe déjà.', 'danger')
            return render_template('departements/formulaire.html', utilisateurs=Utilisateur.query.all())
        
        if code and Departement.query.filter_by(code=code).first():
            flash('Un département avec ce code existe déjà.', 'danger')
            return render_template('departements/formulaire.html', utilisateurs=Utilisateur.query.all())
        
        # Créer le département
        departement = Departement(
            nom=nom,
            code=code if code else None,
            description=description if description else None,
            email=email if email else None,
            telephone=telephone if telephone else None,
            localisation=localisation if localisation else None,
            couleur=couleur,
            icone=icone,
            responsable_id=responsable_id,
            sla_reponse_heures=sla_reponse_heures,
            sla_resolution_heures=sla_resolution_heures,
            actif=True
        )
        
        try:
            db.session.add(departement)
            db.session.commit()
            flash(f'Département "{nom}" créé avec succès!', 'success')
            return redirect(url_for('departements.detail', id=departement.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création du département: {str(e)}', 'danger')
    
    utilisateurs = Utilisateur.query.filter_by(actif=True).order_by(Utilisateur.nom).all()
    return render_template('departements/formulaire.html', utilisateurs=utilisateurs)


@departements_bp.route('/<string:id>')
@login_required
def detail(id):
    """Afficher les détails d'un département"""
    departement = Departement.query.get_or_404(id)
    
    # Vérifier les permissions
    if not current_user.has_permission('admin.departements') and not current_user.has_permission('departements.voir'):
        if current_user.departement_id != departement.id:
            flash('Accès non autorisé.', 'danger')
            return redirect(url_for('tickets.tableau_bord'))
    
    # Statistiques détaillées
    stats = {
        'membres_actifs': len([m for m in departement.membres if m.actif]),
        'membres_total': len(departement.membres),
        'categories': len(departement.categories),
        'tickets_total': sum(len(cat.tickets) for cat in departement.categories),
        'tickets_nouveaux': sum(1 for cat in departement.categories for t in cat.tickets if t.statut == 'nouveau'),
        'tickets_en_cours': sum(1 for cat in departement.categories for t in cat.tickets if t.statut == 'en_cours'),
        'tickets_resolus': sum(1 for cat in departement.categories for t in cat.tickets if t.statut == 'resolu'),
    }
    
    # Tickets récents
    tickets_recents = []
    for categorie in departement.categories:
        tickets_recents.extend(categorie.tickets)
    tickets_recents.sort(key=lambda x: x.date_creation, reverse=True)
    tickets_recents = tickets_recents[:10]
    
    # Membres du département
    membres = Utilisateur.query.filter_by(departement_id=departement.id, actif=True).order_by(Utilisateur.nom).all()
    
    return render_template('departements/detail.html',
                         departement=departement,
                         stats=stats,
                         tickets_recents=tickets_recents,
                         membres=membres)


@departements_bp.route('/<string:id>/modifier', methods=['GET', 'POST'])
@login_required
@admin_required
def modifier(id):
    """Modifier un département"""
    departement = Departement.query.get_or_404(id)
    
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        code = request.form.get('code', '').strip().upper()
        description = request.form.get('description', '').strip()
        email = request.form.get('email', '').strip()
        telephone = request.form.get('telephone', '').strip()
        localisation = request.form.get('localisation', '').strip()
        couleur = request.form.get('couleur', '#3B82F6')
        
        # Gestion du logo (enregistré dans la colonne icone)
        icone = request.form.get('icone', departement.icone)
        logo_file = request.files.get('logo')
        if logo_file and logo_file.filename:
            filename = secure_filename(logo_file.filename)
            upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, 'static/uploads'))
            os.makedirs(upload_folder, exist_ok=True)
            logo_file.save(os.path.join(upload_folder, filename))
            icone = filename
            
        responsable_id = request.form.get('responsable_id', '').strip() or None
        sla_reponse_heures = int(request.form.get('sla_reponse_heures', 4))
        sla_resolution_heures = int(request.form.get('sla_resolution_heures', 48))
        actif = request.form.get('actif') in ['1', 'on', 'true', 'True']
        
        # Validation
        if not nom:
            flash('Le nom du département est requis.', 'danger')
            return render_template('departements/formulaire.html', 
                                 departement=departement,
                                 is_edit=True,
                                 utilisateurs=Utilisateur.query.all())
        
        # Vérifier l'unicité (sauf pour le département actuel)
        existing = Departement.query.filter_by(nom=nom).first()
        if existing and existing.id != departement.id:
            flash('Un département avec ce nom existe déjà.', 'danger')
            return render_template('departements/formulaire.html',
                                 departement=departement,
                                 is_edit=True,
                                 utilisateurs=Utilisateur.query.all())
        
        if code:
            existing = Departement.query.filter_by(code=code).first()
            if existing and existing.id != departement.id:
                flash('Un département avec ce code existe déjà.', 'danger')
                return render_template('departements/formulaire.html',
                                     departement=departement,
                                     is_edit=True,
                                     utilisateurs=Utilisateur.query.all())
        
        # Mettre à jour
        departement.nom = nom
        departement.code = code if code else None
        departement.description = description if description else None
        departement.email = email if email else None
        departement.telephone = telephone if telephone else None
        departement.localisation = localisation if localisation else None
        departement.couleur = couleur
        departement.icone = icone
        departement.responsable_id = responsable_id
        departement.sla_reponse_heures = sla_reponse_heures
        departement.sla_resolution_heures = sla_resolution_heures
        departement.actif = actif
        
        try:
            db.session.commit()
            flash(f'Département "{nom}" modifié avec succès!', 'success')
            return redirect(url_for('departements.detail', id=departement.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification: {str(e)}', 'danger')
    
    utilisateurs = Utilisateur.query.filter_by(actif=True).order_by(Utilisateur.nom).all()
    return render_template('departements/formulaire.html',
                         departement=departement,
                         is_edit=True,
                         utilisateurs=utilisateurs)


@departements_bp.route('/<string:id>/supprimer', methods=['POST'])
@login_required
@admin_required
def supprimer(id):
    """Supprimer un département"""
    departement = Departement.query.get_or_404(id)
    
    # Vérifier s'il y a des dépendances
    if departement.membres:
        flash(f'Impossible de supprimer: le département a {len(departement.membres)} membre(s).', 'danger')
        return redirect(url_for('departements.detail', id=id))
    
    if departement.categories:
        flash(f'Impossible de supprimer: le département a {len(departement.categories)} catégorie(s).', 'danger')
        return redirect(url_for('departements.detail', id=id))
    
    nom = departement.nom
    try:
        db.session.delete(departement)
        db.session.commit()
        flash(f'Département "{nom}" supprimé avec succès!', 'success')
        return redirect(url_for('departements.liste'))
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'danger')
        return redirect(url_for('departements.detail', id=id))


@departements_bp.route('/<string:id>/toggle-actif', methods=['POST'])
@login_required
@admin_required
def toggle_actif(id):
    """Activer/Désactiver un département"""
    departement = Departement.query.get_or_404(id)
    departement.actif = not departement.actif
    
    try:
        db.session.commit()
        status = 'activé' if departement.actif else 'désactivé'
        flash(f'Département "{departement.nom}" {status} avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur: {str(e)}', 'danger')
    
    return redirect(url_for('departements.detail', id=id))
