"""
Routes d'administration pour CosmittoDesk
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import db, Utilisateur, Departement, CategorieTicket, Ticket, Statistique
from datetime import datetime, timedelta
import logging

# CrÃ©er le blueprint
admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)


def admin_required(f):
    """DÃ©corateur pour restreindre l'accÃ¨s aux administrateurs (niveau >= 90)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.role or current_user.role.niveau < 90:
            flash('AccÃ¨s rÃ©servÃ© aux administrateurs', 'danger')
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
        Ticket.statut, db.func.count(Ticket.id).label('total_count')
    ).group_by(Ticket.statut).all()
    
    # Tickets par prioritÃ©
    tickets_par_priorite = db.session.query(
        Ticket.priorite, db.func.count(Ticket.id).label('total_count')
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
    from models import Role
    page        = request.args.get('page', 1, type=int)
    search      = request.args.get('search', '').strip()
    role_id     = request.args.get('role_id', '')
    actif_str   = request.args.get('actif', '')
    dept_id     = request.args.get('departement_id', '')

    q = Utilisateur.query
    if search:
        like = f'%{search}%'
        q = q.filter(
            db.or_(
                Utilisateur.nom.ilike(like),
                Utilisateur.prenom.ilike(like),
                Utilisateur.email.ilike(like),
                Utilisateur.poste.ilike(like),
            )
        )
    if role_id:
        q = q.filter(Utilisateur.role_id == role_id)
    if actif_str in ('0', '1'):
        q = q.filter(Utilisateur.actif == (actif_str == '1'))
    if dept_id:
        q = q.filter(Utilisateur.departement_id == dept_id)

    utilisateurs_page = q.order_by(Utilisateur.nom, Utilisateur.prenom).paginate(
        page=page, per_page=20, error_out=False
    )

    total_actifs   = Utilisateur.query.filter_by(actif=True).count()
    total_inactifs = Utilisateur.query.filter_by(actif=False).count()

    roles        = Role.query.filter_by(actif=True).order_by(Role.niveau.desc()).all()
    departements = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()

    return render_template(
        'admin/utilisateurs.html',
        utilisateurs=utilisateurs_page,
        roles=roles,
        departements=departements,
        total_actifs=total_actifs,
        total_inactifs=total_inactifs,
    )


@admin_bp.route('/utilisateurs/nouveau', methods=['GET', 'POST'])
@login_required
@admin_required
def nouvel_utilisateur():
    """CrÃ©er un nouvel utilisateur"""
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip()
            matricule = request.form.get('matricule', '').strip() or None
            
            # VÃ©rifier l'unicitÃ© de l'email
            if Utilisateur.query.filter_by(email=email).first():
                flash(f"L'adresse email {email} est dÃ©jÃ  utilisÃ©e par un autre compte.", 'danger')
                from models import Role
                return render_template('admin/nouvel_utilisateur.html', departements=Departement.query.filter_by(actif=True).all(), roles=Role.query.filter_by(actif=True).order_by(Role.niveau.desc()).all())
            
            # VÃ©rifier l'unicitÃ© du matricule
            if matricule and Utilisateur.query.filter_by(matricule=matricule).first():
                flash(f"Le matricule {matricule} est dÃ©jÃ  utilisÃ©.", 'danger')
                from models import Role
                return render_template('admin/nouvel_utilisateur.html', departements=Departement.query.filter_by(actif=True).all(), roles=Role.query.filter_by(actif=True).order_by(Role.niveau.desc()).all())

            dept_id = request.form.get('departement_id') or None
            utilisateur = Utilisateur(
                nom=request.form.get('nom'),
                prenom=request.form.get('prenom'),
                email=request.form.get('email'),
                role_id=request.form.get('role_id') or None,
                departement_id=dept_id,
                telephone=request.form.get('telephone', '').strip() or None,
                poste=request.form.get('poste', '').strip() or None,
                matricule=matricule,
                anydesk_id=request.form.get('anydesk_id', '').strip() or None,
                anydesk_password=request.form.get('anydesk_password', '').strip() or None,
                teamviewer_id=request.form.get('teamviewer_id', '').strip() or None,
                teamviewer_password=request.form.get('teamviewer_password', '').strip() or None,
                poste_machine=request.form.get('poste_machine', '').strip() or None,
            )
            utilisateur.set_password(request.form.get('password', 'testtest'))
            
            db.session.add(utilisateur)
            db.session.commit()
            
            flash('Utilisateur crÃ©Ã© avec succÃ¨s', 'success')
            logger.info(f'Nouvel utilisateur crÃ©Ã©: {utilisateur.email} par {current_user.email}')
            
            return redirect(url_for('admin.utilisateurs'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la crÃ©ation de l\'utilisateur: {str(e)}')
            flash('Erreur lors de la crÃ©ation de l\'utilisateur', 'danger')
    
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
            email = request.form.get('email', '').strip()
            matricule = request.form.get('matricule', '').strip() or None
            
            # VÃ©rifier l'unicitÃ©
            existing_email = Utilisateur.query.filter_by(email=email).first()
            if existing_email and existing_email.id != utilisateur.id:
                flash(f"L'adresse email {email} est dÃ©jÃ  utilisÃ©e par un autre compte.", 'danger')
                return redirect(url_for('admin.modifier_utilisateur', user_id=user_id))
                
            if matricule:
                existing_mat = Utilisateur.query.filter_by(matricule=matricule).first()
                if existing_mat and existing_mat.id != utilisateur.id:
                    flash(f"Le matricule {matricule} est dÃ©jÃ  utilisÃ©.", 'danger')
                    return redirect(url_for('admin.modifier_utilisateur', user_id=user_id))

            utilisateur.nom = request.form.get('nom')
            utilisateur.prenom = request.form.get('prenom')
            utilisateur.email = email
            utilisateur.role_id = request.form.get('role_id') or None
            utilisateur.departement_id = request.form.get('departement_id') or None
            utilisateur.telephone = request.form.get('telephone', '').strip() or None
            utilisateur.poste = request.form.get('poste', '').strip() or None
            utilisateur.matricule = matricule
            utilisateur.actif = request.form.get('actif') == '1'
            utilisateur.anydesk_id = request.form.get('anydesk_id', '').strip() or None
            utilisateur.anydesk_password = request.form.get('anydesk_password', '').strip() or None
            utilisateur.teamviewer_id = request.form.get('teamviewer_id', '').strip() or None
            utilisateur.teamviewer_password = request.form.get('teamviewer_password', '').strip() or None
            utilisateur.poste_machine = request.form.get('poste_machine', '').strip() or None

            nouveau_mdp = request.form.get('nouveau_password')
            if nouveau_mdp:
                utilisateur.set_password(nouveau_mdp)

            db.session.commit()

            flash('Utilisateur modifiÃ© avec succÃ¨s', 'success')
            logger.info(f'Utilisateur modifiÃ©: {utilisateur.email} par {current_user.email}')

            return redirect(url_for('admin.utilisateurs'))

        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la modification de l\'utilisateur: {str(e)}')
            flash('Erreur lors de la modification', 'danger')

    from models import Role
    departements = Departement.query.filter_by(actif=True).all()
    roles = Role.query.filter_by(actif=True).order_by(Role.niveau.desc()).all()
    return render_template('admin/modifier_utilisateur.html',
                         utilisateur=utilisateur,
                         departements=departements,
                         roles=roles)


@admin_bp.route('/utilisateurs/<user_id>/desactiver', methods=['POST'])
@login_required
@admin_required
def desactiver_utilisateur(user_id):
    """DÃ©sactiver un utilisateur"""
    if user_id == current_user.id:
        flash('Vous ne pouvez pas vous dÃ©sactiver vous-mÃªme', 'danger')
        return redirect(url_for('admin.utilisateurs'))
    
    utilisateur = Utilisateur.query.get_or_404(user_id)
    
    try:
        utilisateur.actif = False
        db.session.commit()
        
        flash('Utilisateur dÃ©sactivÃ©', 'success')
        logger.info(f'Utilisateur dÃ©sactivÃ©: {utilisateur.email} par {current_user.email}')
    
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur lors de la dÃ©sactivation: {str(e)}')
        flash('Erreur lors de la dÃ©sactivation', 'danger')
    
    return redirect(url_for('admin.utilisateurs'))


@admin_bp.route('/utilisateurs/<user_id>/reactiver', methods=['POST'])
@login_required
@admin_required
def reactiver_utilisateur(user_id):
    """RÃ©activer un utilisateur dÃ©sactivÃ©"""
    utilisateur = Utilisateur.query.get_or_404(user_id)
    try:
        utilisateur.actif = True
        utilisateur.verrouille = False
        utilisateur.tentatives_connexion = 0
        db.session.commit()
        flash(f'{utilisateur.prenom} {utilisateur.nom} a Ã©tÃ© rÃ©activÃ©', 'success')
        logger.info(f'Utilisateur rÃ©activÃ©: {utilisateur.email} par {current_user.email}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur lors de la rÃ©activation: {str(e)}')
        flash('Erreur lors de la rÃ©activation', 'danger')
    return redirect(url_for('admin.utilisateurs'))


@admin_bp.route('/roles')
@login_required
@admin_required
def roles():
    """Gestion des rÃ´les et permissions"""
    from models import Role, Permission
    roles = Role.query.order_by(Role.niveau.desc()).all()
    permissions = Permission.query.order_by(Permission.categorie, Permission.nom).all()
    perms_by_cat = {}
    for p in permissions:
        perms_by_cat.setdefault(p.categorie, []).append(p)
    return render_template('admin/roles.html', roles=roles, perms_by_cat=perms_by_cat)

@admin_bp.route('/permissions')
@login_required
@admin_required
def permissions():
    """Liste de toutes les permissions systÃ¨me"""
    from models import Permission
    permissions_list = Permission.query.order_by(Permission.categorie, Permission.nom).all()
    perms_by_cat = {}
    for p in permissions_list:
        perms_by_cat.setdefault(p.categorie, []).append(p)
    return render_template('admin/permissions.html', perms_by_cat=perms_by_cat)

@admin_bp.route('/permissions/creer', methods=['POST'])
@login_required
@admin_required
def creer_permission():
    from models import Permission
    nom = request.form.get('nom')
    code = request.form.get('code')
    description = request.form.get('description')
    categorie = request.form.get('categorie')
    if not nom or not code:
        flash("Le nom et le code sont obligatoires.", "error")
        return redirect(url_for('admin.permissions'))
    if Permission.query.filter_by(code=code).first():
        flash("Ce code de permission existe dÃ©jÃ .", "error")
        return redirect(url_for('admin.permissions'))
    p = Permission(nom=nom, code=code, description=description, categorie=categorie)
    db.session.add(p)
    db.session.commit()
    flash(f"Permission {code} crÃ©Ã©e avec succÃ¨s.", "success")
    return redirect(url_for('admin.permissions'))

@admin_bp.route('/permissions/<string:id>/supprimer', methods=['POST'])
@login_required
@admin_required
def supprimer_permission(id):
    from models import Permission
    p = Permission.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    flash("Permission supprimÃ©e.", "success")
    return redirect(url_for('admin.permissions'))


@admin_bp.route('/roles/<role_id>/permissions', methods=['POST'])
@login_required
@admin_required
def modifier_permissions_role(role_id):
    """Modifier les permissions d'un rÃ´le"""
    from models import Role, Permission
    role = Role.query.get_or_404(role_id)
    perm_ids = request.form.getlist('permissions')
    role.permissions = Permission.query.filter(Permission.id.in_(perm_ids)).all()
    db.session.commit()
    flash(f'Permissions du rÃ´le "{role.nom}" mises Ã  jour.', 'success')
    return redirect(url_for('admin.roles'))


@admin_bp.route('/roles/creer', methods=['POST'])
@login_required
@admin_required
def creer_role():
    from models import Role
    nom = request.form.get('nom', '').strip()
    if not nom:
        flash('Le nom du rÃ´le est requis.', 'danger')
        return redirect(url_for('admin.roles'))
    if Role.query.filter_by(nom=nom).first():
        flash(f'Un rÃ´le nommÃ© "{nom}" existe dÃ©jÃ .', 'danger')
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
    flash(f'RÃ´le "{nom}" crÃ©Ã© avec succÃ¨s.', 'success')
    return redirect(url_for('admin.roles'))


@admin_bp.route('/roles/<role_id>/modifier', methods=['POST'])
@login_required
@admin_required
def modifier_role(role_id):
    from models import Role
    role = Role.query.get_or_404(role_id)
    if role.systeme:
        flash('Les rÃ´les systÃ¨me ne peuvent pas Ãªtre modifiÃ©s.', 'warning')
        return redirect(url_for('admin.roles'))
    role.nom = request.form.get('nom', role.nom).strip()
    role.description = request.form.get('description', '').strip()
    role.couleur = request.form.get('couleur', role.couleur)
    role.niveau = int(request.form.get('niveau', role.niveau))
    db.session.commit()
    flash(f'RÃ´le "{role.nom}" mis Ã  jour.', 'success')
    return redirect(url_for('admin.roles'))


@admin_bp.route('/categories')
@login_required
@admin_required
def categories():
    """Gestion des catÃ©gories de tickets"""
    categories = CategorieTicket.query.order_by(CategorieTicket.nom).all()
    departements = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()
    return render_template('admin/categories.html', categories=categories, departements=departements)


@admin_bp.route('/categories/creer', methods=['POST'])
@login_required
@admin_required
def creer_categorie():
    """CrÃ©er une nouvelle catÃ©gorie de ticket"""
    nom = request.form.get('nom', '').strip()
    if not nom:
        flash('Le nom de la catÃ©gorie est requis.', 'danger')
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
        flash(f'CatÃ©gorie Â« {nom} Â» crÃ©Ã©e avec succÃ¨s.', 'success')
        logger.info(f'CatÃ©gorie crÃ©Ã©e: {nom} par {current_user.email}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur crÃ©ation catÃ©gorie: {e}')
        flash('Erreur lors de la crÃ©ation de la catÃ©gorie.', 'danger')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/categories/<cat_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_categorie(cat_id):
    """Activer/dÃ©sactiver une catÃ©gorie"""
    cat = CategorieTicket.query.get_or_404(cat_id)
    cat.actif = not cat.actif
    db.session.commit()
    return redirect(url_for('admin.categories'))


@admin_bp.route('/parametres', methods=['GET', 'POST'])
@login_required
def parametres_systeme():
    if not current_user.has_permission('admin_parametres.voir'):
        flash("Accès non autorisé.", "error")
        return redirect(url_for('tickets.tous'))
    """Paramètres système"""
    import os
    from dotenv import dotenv_values, set_key
    
    dotenv_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '.env')
    
    if request.method == 'POST':
        try:
            # Update values
            keys_to_update = [
                'MAIL_SERVER', 'MAIL_PORT', 'MAIL_USE_TLS', 'MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_DEFAULT_SENDER',
                'IMAP_SERVER', 'IMAP_PORT', 'IMAP_USE_SSL', 'IMAP_USERNAME', 'IMAP_PASSWORD', 'IMAP_POLL_INTERVAL',
                'TIMEZONE'
            ]
            for key in keys_to_update:
                val = request.form.get(key, '')
                # Handle checkboxes
                if key in ['MAIL_USE_TLS', 'IMAP_USE_SSL']:
                    val = 'True' if request.form.get(key) else 'False'
                
                set_key(dotenv_path, key, val)
                
            flash('Paramètres mis à jour avec succès. Un redémarrage du serveur peut être nécessaire pour appliquer certains changements.', 'success')
            return redirect(url_for('admin.parametres_systeme'))
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des paramètres: {str(e)}")
            flash("Erreur lors de l'enregistrement des paramètres.", "danger")

    # Read current values
    config_vals = dotenv_values(dotenv_path) if os.path.exists(dotenv_path) else {}
    
    return render_template('admin/parametres.html', config=config_vals)


@admin_bp.route('/logs')
@login_required
def logs():
    if not current_user.has_permission('admin_logs.voir'):
        flash("Accès non autorisé.", "error")
        return redirect(url_for('tickets.tous'))
    """Visualisation des logs système"""
    import os
    log_file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'logs', 'app.log')
    logs_content = []
    
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                logs_content = lines[-500:]
                logs_content.reverse()
        except Exception as e:
            logs_content = [f"Erreur lors de la lecture des logs: {str(e)}"]
    else:
        logs_content = ["Aucun fichier de log trouvé."]
        
    return render_template('admin/logs.html', logs=logs_content)


@admin_bp.route('/plan-action')
@login_required
@admin_required
def plan_action():
    """Plan d'action - calendrier et projets IT"""
    from models import PlanActionTask, Utilisateur
    tasks = PlanActionTask.query.order_by(PlanActionTask.date_debut).all()
    utilisateurs = Utilisateur.query.filter_by(actif=True).all()
    return render_template('admin/plan_action.html', tasks=tasks, utilisateurs=utilisateurs)

@admin_bp.route('/api/plan-action/tasks')
@login_required
@admin_required
def api_plan_action_tasks():
    from models import PlanActionTask
    from flask import jsonify
    tasks = PlanActionTask.query.all()
    events = []
    for t in tasks:
        events.append({
            'id': t.id,
            'title': t.titre,
            'start': t.date_debut.isoformat(),
            'end': t.date_fin.isoformat() if t.date_fin else None,
            'description': t.description,
            'statut': t.statut,
            'assigne_nom': f'{t.assigne_a.prenom} {t.assigne_a.nom}' if t.assigne_a else 'Non assigné',
            'className': 'urgent' if t.urgent else '',
            'backgroundColor': '#ef4444' if t.urgent else '#6366f1',
            'borderColor': '#ef4444' if t.urgent else '#6366f1',
            'allDay': True if not t.date_fin else False
        })
    return jsonify(events)

@admin_bp.route('/plan-action/creer', methods=['POST'])
@login_required
@admin_required
def creer_plan_action():
    from models import PlanActionTask
    from datetime import datetime
    from flask import request, flash, redirect, url_for
    from app import db
    from flask_login import current_user
    
    titre = request.form.get('titre')
    description = request.form.get('description')
    date_debut_str = request.form.get('date_debut')
    date_fin_str = request.form.get('date_fin')
    urgent = request.form.get('urgent') == 'on'
    assigne_a_id = request.form.get('assigne_a_id')
    
    if not titre or not date_debut_str:
        flash("Titre et Date de dÃ©but sont obligatoires.", "error")
        return redirect(url_for('admin.plan_action'))
        
    date_debut = datetime.fromisoformat(date_debut_str) if date_debut_str else datetime.utcnow()
    date_fin = datetime.fromisoformat(date_fin_str) if date_fin_str else None
    
    task = PlanActionTask(
        titre=titre,
        description=description,
        date_debut=date_debut,
        date_fin=date_fin,
        urgent=urgent,
        statut='planned',
        createur_id=current_user.id,
        assigne_a_id=assigne_a_id if assigne_a_id else None
    )
    db.session.add(task)
    db.session.commit()
    flash("TÃ¢che ajoutÃ©e au plan d'action.", "success")
    return redirect(url_for('admin.plan_action'))

@admin_bp.route('/plan-action/<string:id>/terminer', methods=['POST'])
@login_required
@admin_required
def terminer_plan_action(id):
    from models import PlanActionTask
    from app import db
    from flask import flash, redirect, url_for
    task = PlanActionTask.query.get_or_404(id)
    task.statut = 'completed'
    db.session.commit()
    flash('Tâche marquée comme terminée.', 'success')
    return redirect(url_for('admin.plan_action'))

@admin_bp.route('/plan-action/<string:id>/annuler-terminer', methods=['POST'])
@login_required
@admin_required
def annuler_terminer_plan_action(id):
    from models import PlanActionTask
    from app import db
    from flask import flash, redirect, url_for
    task = PlanActionTask.query.get_or_404(id)
    task.statut = 'planned'
    db.session.commit()
    flash('Le statut de la tâche a été réinitialisé.', 'success')
    return redirect(url_for('admin.plan_action'))

@admin_bp.route('/plan-action/<string:id>/modifier', methods=['POST'])
@login_required
@admin_required
def modifier_plan_action(id):
    from models import PlanActionTask
    from datetime import datetime
    from app import db
    from flask import request, flash, redirect, url_for
    task = PlanActionTask.query.get_or_404(id)
    
    task.titre = request.form.get('titre') or task.titre
    task.description = request.form.get('description')
    
    date_debut_str = request.form.get('date_debut')
    if date_debut_str:
        task.date_debut = datetime.fromisoformat(date_debut_str)
        
    date_fin_str = request.form.get('date_fin')
    task.date_fin = datetime.fromisoformat(date_fin_str) if date_fin_str else None
    
    task.urgent = request.form.get('urgent') == 'on'
    
    assigne_a_id = request.form.get('assigne_a_id')
    task.assigne_a_id = assigne_a_id if assigne_a_id else None
    
    db.session.commit()
    flash('Tâche modifiée avec succès.', 'success')
    return redirect(url_for('admin.plan_action'))

@admin_bp.route('/plan-action/<string:id>/supprimer', methods=['POST'])
@login_required
@admin_required
def supprimer_plan_action(id):
    from models import PlanActionTask
    from app import db
    from flask import flash, redirect, url_for
    task = PlanActionTask.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    flash("Tâche supprimée.", "success")
    return redirect(url_for('admin.plan_action'))


@admin_bp.route('/plan-action/export-excel')
@login_required
@admin_required
def export_plan_action_excel():
    """Export du plan d'action en fichier Excel formaté"""
    from models import PlanActionTask
    from flask import request, send_file
    import openpyxl
    from openpyxl.styles import (Font, PatternFill, Alignment, Border, Side,
                                  GradientFill)
    from openpyxl.utils import get_column_letter
    from datetime import datetime, date
    import io

    # ── Paramètres de filtrage ──────────────────────────────────
    mode      = request.args.get('mode', 'all')      # all | day | periode
    date_jour = request.args.get('date_jour', '')
    date_from = request.args.get('date_from', '')
    date_to   = request.args.get('date_to', '')

    query = PlanActionTask.query

    if mode == 'day' and date_jour:
        try:
            d = datetime.fromisoformat(date_jour).date()
            query = query.filter(
                db.func.date(PlanActionTask.date_debut) == d
            )
        except ValueError:
            pass
    elif mode == 'periode' and date_from:
        try:
            df = datetime.fromisoformat(date_from)
            query = query.filter(PlanActionTask.date_debut >= df)
            if date_to:
                dt = datetime.fromisoformat(date_to)
                query = query.filter(PlanActionTask.date_debut <= dt)
        except ValueError:
            pass

    tasks = query.order_by(PlanActionTask.date_debut).all()

    # ── Workbook & styles ───────────────────────────────────────
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Plan d'action"

    # Palette
    COLOR_HEADER_BG  = "1E1B4B"   # deep indigo
    COLOR_HEADER_FG  = "FFFFFF"
    COLOR_URGENT     = "FEE2E2"   # light red tint
    COLOR_COMPLETED  = "D1FAE5"   # light green tint
    COLOR_PLANNED    = "F1F5F9"   # light slate
    COLOR_ALT        = "F8FAFC"

    thin = Side(style='thin', color="E2E8F0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    header_font    = Font(bold=True, color=COLOR_HEADER_FG, size=11, name="Calibri")
    header_fill    = PatternFill("solid", fgColor=COLOR_HEADER_BG)
    header_align   = Alignment(horizontal="center", vertical="center", wrap_text=True)

    title_font     = Font(bold=True, size=16, color=COLOR_HEADER_BG, name="Calibri")
    subtitle_font  = Font(size=10, color="64748B", name="Calibri")
    cell_font      = Font(size=10, name="Calibri")
    bold_font      = Font(bold=True, size=10, name="Calibri")

    center = Alignment(horizontal="center", vertical="center")
    left   = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # ── Title block ─────────────────────────────────────────────
    ws.merge_cells("A1:H1")
    ws["A1"] = "Plan d'Action — CosmittoHUB"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 32

    ws.merge_cells("A2:H2")
    label_map = {
        'all':     'Toutes les tâches',
        'day':     f'Jour : {date_jour}',
        'periode': f'Période : {date_from} → {date_to or "…"}',
    }
    ws["A2"] = f"Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}  |  Filtre : {label_map.get(mode, mode)}  |  {len(tasks)} tâche(s)"
    ws["A2"].font = subtitle_font
    ws["A2"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[2].height = 18

    ws.row_dimensions[3].height = 10   # spacer

    # ── Column headers (row 4) ───────────────────────────────────
    headers = ["#", "Titre", "Description", "Statut", "Urgent", "Date début", "Date fin", "Assigné à"]
    widths  = [5,    35,      45,            12,        10,       14,           14,          22]

    for col, (h, w) in enumerate(zip(headers, widths), start=1):
        cell = ws.cell(row=4, column=col, value=h)
        cell.font      = header_font
        cell.fill      = header_fill
        cell.alignment = header_align
        cell.border    = border
        ws.column_dimensions[get_column_letter(col)].width = w

    ws.row_dimensions[4].height = 28

    # ── Data rows ────────────────────────────────────────────────
    statut_labels = {'planned': 'Planifiée', 'progress': 'En cours', 'completed': 'Terminée'}

    for i, task in enumerate(tasks, start=1):
        row = 4 + i

        # Row background
        if task.statut == 'completed':
            row_fill = PatternFill("solid", fgColor=COLOR_COMPLETED)
        elif task.urgent:
            row_fill = PatternFill("solid", fgColor=COLOR_URGENT)
        elif i % 2 == 0:
            row_fill = PatternFill("solid", fgColor=COLOR_ALT)
        else:
            row_fill = PatternFill("solid", fgColor="FFFFFF")

        values = [
            i,
            task.titre,
            task.description or "",
            statut_labels.get(task.statut, task.statut),
            "🔥 Oui" if task.urgent else "Non",
            task.date_debut.strftime('%d/%m/%Y') if task.date_debut else "",
            task.date_fin.strftime('%d/%m/%Y') if task.date_fin else "—",
            f"{task.assigne_a.prenom} {task.assigne_a.nom}" if task.assigne_a else "Non assigné",
        ]
        aligns = [center, left, left, center, center, center, center, left]

        for col, (val, aln) in enumerate(zip(values, aligns), start=1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.font      = bold_font if col == 2 else cell_font
            cell.fill      = row_fill
            cell.alignment = aln
            cell.border    = border

        ws.row_dimensions[row].height = 22

    # Freeze header
    ws.freeze_panes = "A5"

    # ── Summary row ─────────────────────────────────────────────
    summary_row = 4 + len(tasks) + 2
    ws.merge_cells(f"A{summary_row}:C{summary_row}")
    ws[f"A{summary_row}"] = f"Total : {len(tasks)} tâche(s)"
    ws[f"A{summary_row}"].font = bold_font
    ws[f"A{summary_row}"].fill = PatternFill("solid", fgColor="E2E8F0")

    completed_count = sum(1 for t in tasks if t.statut == 'completed')
    urgent_count    = sum(1 for t in tasks if t.urgent)
    ws.merge_cells(f"D{summary_row}:F{summary_row}")
    ws[f"D{summary_row}"] = f"Terminées : {completed_count}  |  Urgentes : {urgent_count}"
    ws[f"D{summary_row}"].font = bold_font
    ws[f"D{summary_row}"].fill = PatternFill("solid", fgColor="E2E8F0")
    ws[f"D{summary_row}"].alignment = center

    # ── Stream to browser ────────────────────────────────────────
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    now_str  = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"plan_action_{now_str}.xlsx"

    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@admin_bp.route('/acces-distance')
@login_required
@admin_required
def acces_distance():
    from models import Utilisateur, db
    # Fetch all active users, sorted by name, so the admin can add IDs for new users
    users = Utilisateur.query.filter_by(actif=True).order_by(Utilisateur.nom, Utilisateur.prenom).all()
    return render_template('admin/acces_distance.html', users=users)


@admin_bp.route('/api/migrate_db')
def migrate_db():
    from models import db
    try:
        db.session.execute('ALTER TABLE pieces_jointes ADD COLUMN commentaire_id VARCHAR(36) REFERENCES commentaires(id) ON DELETE CASCADE;')
        db.session.commit()
        return "Migration successful"
    except Exception as e:
        return f"Migration failed: {str(e)}"
