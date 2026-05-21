"""
Routes d'administration pour CosmittoDesk
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import db, Utilisateur, Departement, CategorieTicket, Ticket, Statistique
from datetime import datetime, timedelta
import logging

# Créer le blueprint
admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)


def admin_required(f):
    """Décorateur pour restreindre l'accès aux administrateurs"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.role or current_user.role.niveau < 70:
            flash('Accès réservé aux administrateurs', 'danger')
            return redirect(url_for('tickets.tableau_bord'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/tableau-bord')
@login_required
@admin_required
def tableau_bord():
    """Tableau de bord administrateur"""
    # Statistiques globales
    stats = {
        'utilisateurs': Utilisateur.query.filter_by(actif=True).count(),
        'departements': Departement.query.filter_by(actif=True).count(),
        'tickets_total': Ticket.query.count(),
        'tickets_ouverts': Ticket.query.filter_by(statut='ouvert').count(),
        'tickets_mois': Ticket.query.filter(
            Ticket.date_creation >= datetime.utcnow() - timedelta(days=30)
        ).count()
    }
    
    # Tickets par statut
    tickets_par_statut = db.session.query(
        Ticket.statut, db.func.count(Ticket.id)
    ).group_by(Ticket.statut).all()
    
    # Tickets par priorité
    tickets_par_priorite = db.session.query(
        Ticket.priorite, db.func.count(Ticket.id)
    ).group_by(Ticket.priorite).all()
    
    return render_template('admin/tableau_bord.html',
                         stats=stats,
                         tickets_par_statut=tickets_par_statut,
                         tickets_par_priorite=tickets_par_priorite)


@admin_bp.route('/utilisateurs')
@login_required
@admin_required
def utilisateurs():
    """Liste des utilisateurs"""
    page = request.args.get('page', 1, type=int)
    utilisateurs = Utilisateur.query.order_by(Utilisateur.nom).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/utilisateurs.html', utilisateurs=utilisateurs)


@admin_bp.route('/utilisateurs/nouveau', methods=['GET', 'POST'])
@login_required
@admin_required
def nouvel_utilisateur():
    """Créer un nouvel utilisateur"""
    if request.method == 'POST':
        try:
            dept_id = request.form.get('departement_id') or None
            matricule = request.form.get('matricule', '').strip() or None
            utilisateur = Utilisateur(
                nom=request.form.get('nom'),
                prenom=request.form.get('prenom'),
                email=request.form.get('email'),
                role_id=request.form.get('role_id') or None,
                departement_id=dept_id,
                telephone=request.form.get('telephone', '').strip() or None,
                poste=request.form.get('poste', '').strip() or None,
                matricule=matricule,
            )
            utilisateur.set_password(request.form.get('password', 'testtest'))
            
            db.session.add(utilisateur)
            db.session.commit()
            
            flash('Utilisateur créé avec succès', 'success')
            logger.info(f'Nouvel utilisateur créé: {utilisateur.email} par {current_user.email}')
            
            return redirect(url_for('admin.utilisateurs'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la création de l\'utilisateur: {str(e)}')
            flash('Erreur lors de la création de l\'utilisateur', 'danger')
    
    from models import Role
    departements = Departement.query.filter_by(actif=True).all()
    roles = Role.query.filter_by(actif=True).order_by(Role.niveau.desc()).all()
    return render_template('admin/nouvel_utilisateur.html', departements=departements, roles=roles)


@admin_bp.route('/utilisateurs/<user_id>/modifier', methods=['GET', 'POST'])
@login_required
@admin_required
def modifier_utilisateur(user_id):
    """Modifier un utilisateur"""
    utilisateur = Utilisateur.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            utilisateur.nom = request.form.get('nom')
            utilisateur.prenom = request.form.get('prenom')
            utilisateur.email = request.form.get('email')
            utilisateur.role = request.form.get('role')
            utilisateur.departement_id = request.form.get('departement_id')
            utilisateur.actif = request.form.get('actif') == 'on'
            
            # Changer le mot de passe si fourni
            nouveau_mdp = request.form.get('nouveau_password')
            if nouveau_mdp:
                utilisateur.definir_mot_de_passe(nouveau_mdp)
            
            db.session.commit()
            
            flash('Utilisateur modifié avec succès', 'success')
            logger.info(f'Utilisateur modifié: {utilisateur.email} par {current_user.email}')
            
            return redirect(url_for('admin.utilisateurs'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la modification de l\'utilisateur: {str(e)}')
            flash('Erreur lors de la modification', 'danger')
    
    departements = Departement.query.filter_by(actif=True).all()
    return render_template('admin/modifier_utilisateur.html', 
                         utilisateur=utilisateur,
                         departements=departements)


@admin_bp.route('/utilisateurs/<user_id>/desactiver', methods=['POST'])
@login_required
@admin_required
def desactiver_utilisateur(user_id):
    """Désactiver un utilisateur"""
    if user_id == current_user.id:
        flash('Vous ne pouvez pas vous désactiver vous-même', 'danger')
        return redirect(url_for('admin.utilisateurs'))
    
    utilisateur = Utilisateur.query.get_or_404(user_id)
    
    try:
        utilisateur.actif = False
        db.session.commit()
        
        flash('Utilisateur désactivé', 'success')
        logger.info(f'Utilisateur désactivé: {utilisateur.email} par {current_user.email}')
    
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur lors de la désactivation: {str(e)}')
        flash('Erreur lors de la désactivation', 'danger')
    
    return redirect(url_for('admin.utilisateurs'))


@admin_bp.route('/roles')
@login_required
@admin_required
def roles():
    """Gestion des rôles et permissions"""
    from models import Role, Permission
    roles = Role.query.order_by(Role.niveau.desc()).all()
    permissions = Permission.query.order_by(Permission.categorie, Permission.nom).all()
    perms_by_cat = {}
    for p in permissions:
        perms_by_cat.setdefault(p.categorie, []).append(p)
    return render_template('admin/roles.html', roles=roles, perms_by_cat=perms_by_cat)


@admin_bp.route('/roles/<role_id>/permissions', methods=['POST'])
@login_required
@admin_required
def modifier_permissions_role(role_id):
    """Modifier les permissions d'un rôle"""
    from models import Role, Permission
    role = Role.query.get_or_404(role_id)
    if role.systeme:
        flash('Les rôles système ne peuvent pas être modifiés.', 'warning')
        return redirect(url_for('admin.roles'))
    perm_ids = request.form.getlist('permissions')
    role.permissions = Permission.query.filter(Permission.id.in_(perm_ids)).all()
    db.session.commit()
    flash(f'Permissions du rôle "{role.nom}" mises à jour.', 'success')
    return redirect(url_for('admin.roles'))


@admin_bp.route('/roles/creer', methods=['POST'])
@login_required
@admin_required
def creer_role():
    from models import Role
    nom = request.form.get('nom', '').strip()
    if not nom:
        flash('Le nom du rôle est requis.', 'danger')
        return redirect(url_for('admin.roles'))
    if Role.query.filter_by(nom=nom).first():
        flash(f'Un rôle nommé "{nom}" existe déjà.', 'danger')
        return redirect(url_for('admin.roles'))
    role = Role(
        nom=nom,
        description=request.form.get('description', '').strip(),
        couleur=request.form.get('couleur', '#3B82F6'),
        niveau=int(request.form.get('niveau', 0)),
        systeme=False,
        actif=True,
    )
    db.session.add(role)
    db.session.commit()
    flash(f'Rôle "{nom}" créé avec succès.', 'success')
    return redirect(url_for('admin.roles'))


@admin_bp.route('/roles/<role_id>/modifier', methods=['POST'])
@login_required
@admin_required
def modifier_role(role_id):
    from models import Role
    role = Role.query.get_or_404(role_id)
    if role.systeme:
        flash('Les rôles système ne peuvent pas être modifiés.', 'warning')
        return redirect(url_for('admin.roles'))
    role.nom = request.form.get('nom', role.nom).strip()
    role.description = request.form.get('description', '').strip()
    role.couleur = request.form.get('couleur', role.couleur)
    role.niveau = int(request.form.get('niveau', role.niveau))
    db.session.commit()
    flash(f'Rôle "{role.nom}" mis à jour.', 'success')
    return redirect(url_for('admin.roles'))


@admin_bp.route('/categories')
@login_required
@admin_required
def categories():
    """Gestion des catégories de tickets"""
    categories = CategorieTicket.query.order_by(CategorieTicket.nom).all()
    departements = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()
    return render_template('admin/categories.html', categories=categories, departements=departements)


@admin_bp.route('/categories/creer', methods=['POST'])
@login_required
@admin_required
def creer_categorie():
    """Créer une nouvelle catégorie de ticket"""
    nom = request.form.get('nom', '').strip()
    if not nom:
        flash('Le nom de la catégorie est requis.', 'danger')
        return redirect(url_for('admin.categories'))
    try:
        cat = CategorieTicket(
            nom=nom,
            description=request.form.get('description', '').strip() or None,
            type_ticket=request.form.get('type_ticket', 'demande'),
            departement_id=request.form.get('departement_id') or None,
            priorite_defaut=request.form.get('priorite_defaut', 'moyenne'),
            delai_resolution_jours=int(request.form.get('delai_resolution_jours') or 7),
            couleur=request.form.get('couleur', '#3B82F6'),
        )
        db.session.add(cat)
        db.session.commit()
        flash(f'Catégorie « {nom} » créée avec succès.', 'success')
        logger.info(f'Catégorie créée: {nom} par {current_user.email}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur création catégorie: {e}')
        flash('Erreur lors de la création de la catégorie.', 'danger')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/categories/<cat_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_categorie(cat_id):
    """Activer/désactiver une catégorie"""
    cat = CategorieTicket.query.get_or_404(cat_id)
    cat.actif = not cat.actif
    db.session.commit()
    return redirect(url_for('admin.categories'))


@admin_bp.route('/parametres')
@login_required
@admin_required
def parametres_systeme():
    """Paramètres système"""
    return render_template('admin/parametres.html')


@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    """Visualisation des logs système"""
    # TODO: Implémenter la lecture des fichiers de logs
    return render_template('admin/logs.html')
