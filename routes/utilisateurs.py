from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Utilisateur, Role, Departement
from werkzeug.utils import secure_filename
from functools import wraps
import os
from datetime import datetime

utilisateurs_bp = Blueprint('utilisateurs', __name__)


def admin_required(f):
    """Décorateur pour restreindre l'accès aux administrateurs"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('admin.utilisateurs'):
            flash('Accès non autorisé.', 'danger')
            return redirect(url_for('tickets.tableau_bord'))
        return f(*args, **kwargs)
    return decorated_function


@utilisateurs_bp.route('/')
@login_required
@admin_required
def liste():
    """Liste tous les utilisateurs"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    query = Utilisateur.query
    
    # Filtres
    search = request.args.get('search', '')
    if search:
        query = query.filter(
            (Utilisateur.nom.contains(search)) |
            (Utilisateur.prenom.contains(search)) |
            (Utilisateur.email.contains(search)) |
            (Utilisateur.matricule.contains(search))
        )
    
    role_filter = request.args.get('role', '')
    if role_filter:
        query = query.filter_by(role_id=role_filter)
    
    dept_filter = request.args.get('departement', '')
    if dept_filter:
        query = query.filter_by(departement_id=dept_filter)
    
    actif_filter = request.args.get('actif', '')
    if actif_filter == '1':
        query = query.filter_by(actif=True)
    elif actif_filter == '0':
        query = query.filter_by(actif=False)
    
    utilisateurs = query.order_by(Utilisateur.nom, Utilisateur.prenom).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    roles = Role.query.filter_by(actif=True).all()
    departements = Departement.query.filter_by(actif=True).all()
    
    return render_template('utilisateurs/liste.html',
                         utilisateurs=utilisateurs,
                         roles=roles,
                         departements=departements,
                         search=search,
                         role_filter=role_filter,
                         dept_filter=dept_filter,
                         actif_filter=actif_filter)


@utilisateurs_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
@admin_required
def nouveau():
    """Créer un nouvel utilisateur"""
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        telephone = request.form.get('telephone', '').strip()
        poste = request.form.get('poste', '').strip()
        matricule = request.form.get('matricule', '').strip()
        role_id = request.form.get('role_id', '').strip() or None
        departement_id = request.form.get('departement_id', '').strip() or None
        
        # Validation
        if not all([nom, prenom, email, password]):
            flash('Tous les champs obligatoires doivent être remplis.', 'danger')
            return render_template('utilisateurs/formulaire.html',
                                 roles=Role.query.filter_by(actif=True).all(),
                                 departements=Departement.query.filter_by(actif=True).all())
        
        # Vérifier l'email unique
        if Utilisateur.query.filter_by(email=email).first():
            flash('Un utilisateur avec cet email existe déjà.', 'danger')
            return render_template('utilisateurs/formulaire.html',
                                 roles=Role.query.filter_by(actif=True).all(),
                                 departements=Departement.query.filter_by(actif=True).all())
        
        # Vérifier le matricule unique
        if matricule and Utilisateur.query.filter_by(matricule=matricule).first():
            flash('Un utilisateur avec ce matricule existe déjà.', 'danger')
            return render_template('utilisateurs/formulaire.html',
                                 roles=Role.query.filter_by(actif=True).all(),
                                 departements=Departement.query.filter_by(actif=True).all())
        
        # Créer l'utilisateur
        utilisateur = Utilisateur(
            nom=nom,
            prenom=prenom,
            email=email,
            telephone=telephone if telephone else None,
            poste=poste if poste else None,
            matricule=matricule if matricule else None,
            role_id=role_id,
            departement_id=departement_id,
            actif=True
        )
        utilisateur.set_password(password)
        
        try:
            db.session.add(utilisateur)
            db.session.commit()
            flash(f'Utilisateur "{utilisateur.nom_complet}" créé avec succès!', 'success')
            return redirect(url_for('utilisateurs.detail', id=utilisateur.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création: {str(e)}', 'danger')
    
    roles = Role.query.filter_by(actif=True).order_by(Role.niveau.desc()).all()
    departements = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()
    return render_template('utilisateurs/formulaire.html',
                         roles=roles,
                         departements=departements)


@utilisateurs_bp.route('/<string:id>')
@login_required
def detail(id):
    """Afficher les détails d'un utilisateur"""
    utilisateur = Utilisateur.query.get_or_404(id)
    
    # Vérifier les permissions
    if not current_user.has_permission('admin.utilisateurs'):
        if current_user.id != utilisateur.id:
            flash('Accès non autorisé.', 'danger')
            return redirect(url_for('tickets.tableau_bord'))
    
    # Statistiques
    stats = {
        'tickets_crees': len(utilisateur.tickets_crees),
        'tickets_assignes': len([t for t in utilisateur.tickets_assignes if t.statut not in ['resolu', 'ferme']]),
        'tickets_resolus': len([t for t in utilisateur.tickets_assignes if t.statut == 'resolu']),
        'commentaires': len(utilisateur.commentaires),
    }
    
    # Tickets récents
    tickets_recents = sorted(
        utilisateur.tickets_crees + utilisateur.tickets_assignes,
        key=lambda x: x.date_creation,
        reverse=True
    )[:10]
    
    return render_template('utilisateurs/detail.html',
                         utilisateur=utilisateur,
                         stats=stats,
                         tickets_recents=tickets_recents)


@utilisateurs_bp.route('/<string:id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier(id):
    """Modifier un utilisateur"""
    utilisateur = Utilisateur.query.get_or_404(id)
    
    # Vérifier les permissions
    if not current_user.has_permission('admin.utilisateurs'):
        if current_user.id != utilisateur.id:
            flash('Accès non autorisé.', 'danger')
            return redirect(url_for('tickets.tableau_bord'))
    
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()
        email = request.form.get('email', '').strip().lower()
        telephone = request.form.get('telephone', '').strip()
        poste = request.form.get('poste', '').strip()
        matricule = request.form.get('matricule', '').strip()
        
        # Les admins peuvent modifier plus de champs
        if current_user.has_permission('admin.utilisateurs'):
            role_id = request.form.get('role_id', '').strip() or None
            departement_id = request.form.get('departement_id', '').strip() or None
            actif = request.form.get('actif') == 'on'
        else:
            role_id = utilisateur.role_id
            departement_id = utilisateur.departement_id
            actif = utilisateur.actif
        
        # Mot de passe optionnel
        password = request.form.get('password', '').strip()
        
        # Validation
        if not all([nom, prenom, email]):
            flash('Tous les champs obligatoires doivent être remplis.', 'danger')
            return render_template('utilisateurs/formulaire.html',
                                 utilisateur=utilisateur,
                                 roles=Role.query.filter_by(actif=True).all(),
                                 departements=Departement.query.filter_by(actif=True).all())
        
        # Vérifier l'email unique (sauf pour l'utilisateur actuel)
        existing = Utilisateur.query.filter_by(email=email).first()
        if existing and existing.id != utilisateur.id:
            flash('Un utilisateur avec cet email existe déjà.', 'danger')
            return render_template('utilisateurs/formulaire.html',
                                 utilisateur=utilisateur,
                                 roles=Role.query.filter_by(actif=True).all(),
                                 departements=Departement.query.filter_by(actif=True).all())
        
        # Vérifier le matricule unique
        if matricule:
            existing = Utilisateur.query.filter_by(matricule=matricule).first()
            if existing and existing.id != utilisateur.id:
                flash('Un utilisateur avec ce matricule existe déjà.', 'danger')
                return render_template('utilisateurs/formulaire.html',
                                     utilisateur=utilisateur,
                                     roles=Role.query.filter_by(actif=True).all(),
                                     departements=Departement.query.filter_by(actif=True).all())
        
        # Mettre à jour
        utilisateur.nom = nom
        utilisateur.prenom = prenom
        utilisateur.email = email
        utilisateur.telephone = telephone if telephone else None
        utilisateur.poste = poste if poste else None
        utilisateur.matricule = matricule if matricule else None
        utilisateur.role_id = role_id
        utilisateur.departement_id = departement_id
        utilisateur.actif = actif
        
        if password:
            utilisateur.set_password(password)
        
        try:
            db.session.commit()
            flash(f'Utilisateur "{utilisateur.nom_complet}" modifié avec succès!', 'success')
            return redirect(url_for('utilisateurs.detail', id=utilisateur.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification: {str(e)}', 'danger')
    
    roles = Role.query.filter_by(actif=True).order_by(Role.niveau.desc()).all()
    departements = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()
    return render_template('utilisateurs/formulaire.html',
                         utilisateur=utilisateur,
                         roles=roles,
                         departements=departements)


@utilisateurs_bp.route('/<string:id>/toggle-actif', methods=['POST'])
@login_required
@admin_required
def toggle_actif(id):
    """Activer/Désactiver un utilisateur"""
    utilisateur = Utilisateur.query.get_or_404(id)
    
    # Ne pas se désactiver soi-même
    if utilisateur.id == current_user.id:
        flash('Vous ne pouvez pas vous désactiver vous-même.', 'danger')
        return redirect(url_for('utilisateurs.detail', id=id))
    
    utilisateur.actif = not utilisateur.actif
    
    try:
        db.session.commit()
        status = 'activé' if utilisateur.actif else 'désactivé'
        flash(f'Utilisateur "{utilisateur.nom_complet}" {status} avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur: {str(e)}', 'danger')
    
    return redirect(url_for('utilisateurs.detail', id=id))


@utilisateurs_bp.route('/<string:id>/supprimer', methods=['POST'])
@login_required
@admin_required
def supprimer(id):
    """Supprimer un utilisateur"""
    utilisateur = Utilisateur.query.get_or_404(id)
    
    # Ne pas se supprimer soi-même
    if utilisateur.id == current_user.id:
        flash('Vous ne pouvez pas vous supprimer vous-même.', 'danger')
        return redirect(url_for('utilisateurs.detail', id=id))
    
    # Vérifier s'il y a des tickets
    if utilisateur.tickets_crees or utilisateur.tickets_assignes:
        flash('Impossible de supprimer: cet utilisateur a des tickets associés. Désactivez-le plutôt.', 'danger')
        return redirect(url_for('utilisateurs.detail', id=id))
    
    nom = utilisateur.nom_complet
    try:
        db.session.delete(utilisateur)
        db.session.commit()
        flash(f'Utilisateur "{nom}" supprimé avec succès!', 'success')
        return redirect(url_for('utilisateurs.liste'))
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'danger')
        return redirect(url_for('utilisateurs.detail', id=id))
