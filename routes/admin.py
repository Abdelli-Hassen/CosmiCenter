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


@admin_bp.route('/parametres')
@login_required
@admin_required
def parametres_systeme():
    """ParamÃ¨tres systÃ¨me"""
    return render_template('admin/parametres.html')


@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    """Visualisation des logs systÃ¨me"""
    # TODO: ImplÃ©menter la lecture des fichiers de logs
    return render_template('admin/logs.html')


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
    flash("TÃ¢che supprimÃ©e.", "success")
    return redirect(url_for('admin.plan_action'))


@admin_bp.route('/acces-distance')
@login_required
@admin_required
def acces_distance():
    from models import Utilisateur, db
    users = Utilisateur.query.filter(db.or_(Utilisateur.anydesk_id.isnot(None), Utilisateur.teamviewer_id.isnot(None))).all()
    return render_template('admin/acces_distance.html', users=users)




