"""
Routes d'administration pour CosmiCenter
"""
import io
import json
import os
import re
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user

from models import (db, Utilisateur, Departement, CategorieTicket, Ticket, Role, Permission,
                    PointDeVente, Entreprise, PlanActionTask, ConfigurationSysteme)
from utils.permissions import role_level, can_assign_role
from utils.security import csv_safe, safe_color, parse_int
import logging

# Créer le blueprint
admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
PERMISSION_CODE_RE = re.compile(r'^[a-z0-9_]+(\.[a-z0-9_]+)*$')
TICKET_TYPES = ['demande', 'besoin', 'plainte', 'incident', 'tache']
CATEGORY_PRIORITIES = ['basse', 'moyenne', 'haute', 'urgente', 'critique']
STATUTS_OUVERTS = ['nouveau', 'ouvert']


def admin_required(f):
    """Décorateur pour restreindre l'accès aux administrateurs (niveau >= 90)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.connexion'))
        if role_level(current_user) < 90:
            flash('Accès réservé aux administrateurs', 'danger')
            return redirect(url_for('tickets.tableau_bord'))
        return f(*args, **kwargs)
    return decorated_function


def permission_required(permission_name):
    """Décorateur pour restreindre l'accès selon une permission spécifique"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.connexion'))
            if not current_user.has_permission(permission_name) and role_level(current_user) < 90:
                flash('Accès non autorisé', 'danger')
                return redirect(url_for('tickets.tableau_bord'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def _parse_datetime(value):
    """Date ISO -> datetime ; None si vide ou invalide."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _user_form_context():
    return dict(
        departements=Departement.query.filter_by(actif=True).order_by(Departement.nom).all(),
        roles=Role.query.filter_by(actif=True).order_by(Role.niveau.desc()).all(),
        pdvs=PointDeVente.query.filter_by(actif=True).order_by(PointDeVente.nom).all(),
        entreprises=Entreprise.query.filter_by(actif=True).order_by(Entreprise.nom).all(),
    )


def _check_role_assignment(role_id):
    """Retourne un message d'erreur si le rôle est inexistant ou de niveau supérieur à celui de l'acteur."""
    if not role_id:
        return None
    role = db.session.get(Role, role_id)
    if role is None:
        return 'Rôle introuvable.'
    if not can_assign_role(current_user, role):
        return "Vous ne pouvez pas attribuer un rôle de niveau supérieur au vôtre."
    return None


def _system_health():
    """État réel du système : requête de test sur la base (avec latence), e-mail configuré, dossier d'envoi écrivable."""
    import time
    from flask import current_app
    health = {'db_ok': False, 'db_ms': None, 'mail': False, 'uploads': False}
    try:
        start = time.perf_counter()
        db.session.execute(db.text('SELECT 1'))
        health['db_ms'] = max(1, round((time.perf_counter() - start) * 1000))
        health['db_ok'] = True
    except Exception:
        db.session.rollback()
    cfg = current_app.config
    health['mail'] = bool(cfg.get('MAIL_SERVER') and cfg.get('MAIL_USERNAME') and cfg.get('MAIL_PASSWORD'))
    folder = cfg.get('UPLOAD_FOLDER')
    health['uploads'] = bool(folder and os.path.isdir(folder) and os.access(folder, os.W_OK))
    health['ok'] = health['db_ok'] and health['uploads']
    return health


@admin_bp.route('/tableau-bord')
@login_required
@admin_required
def tableau_bord():
    """Tableau de bord administrateur"""
    stats = {
        'utilisateurs': Utilisateur.query.filter_by(actif=True).count(),
        'departements': Departement.query.filter_by(actif=True).count(),
        'tickets_total': Ticket.query.count(),
        'tickets_ouverts': Ticket.query.filter(Ticket.statut.in_(STATUTS_OUVERTS)).count(),
        'tickets_mois': Ticket.query.filter(
            Ticket.date_creation >= datetime.utcnow() - timedelta(days=30)
        ).count()
    }

    tickets_par_statut = db.session.query(
        Ticket.statut, db.func.count(Ticket.id).label('total_count')
    ).group_by(Ticket.statut).all()

    tickets_par_priorite = db.session.query(
        Ticket.priorite, db.func.count(Ticket.id).label('total_count')
    ).group_by(Ticket.priorite).all()

    return render_template('admin/tableau_bord.html',
                           stats=stats,
                           health=_system_health(),
                           tickets_par_statut=tickets_par_statut,
                           tickets_par_priorite=tickets_par_priorite)


@admin_bp.route('/utilisateurs')
@login_required
@admin_required
def utilisateurs():
    """Liste des utilisateurs"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    role_id = request.args.get('role_id', '')
    actif_str = request.args.get('actif', '')
    dept_id = request.args.get('departement_id', '')

    q = Utilisateur.query
    if search:
        like = f'%{search}%'
        if '@' in search:
            email_cond = Utilisateur.email.ilike(like)
        else:
            email_cond = db.func.split_part(Utilisateur.email, '@', 1).ilike(like)

        q = q.filter(
            db.or_(
                Utilisateur.nom.ilike(like),
                Utilisateur.prenom.ilike(like),
                (db.func.concat(Utilisateur.prenom, ' ', Utilisateur.nom)).ilike(like),
                (db.func.concat(Utilisateur.nom, ' ', Utilisateur.prenom)).ilike(like),
                email_cond,
                Utilisateur.poste.ilike(like),
            )
        )
    if role_id:
        q = q.filter(Utilisateur.role_id == role_id)
    if actif_str in ('0', '1'):
        q = q.filter(Utilisateur.actif == (actif_str == '1'))
    if dept_id:
        q = q.filter(Utilisateur.departement_id == dept_id)
    if search:
        exact = search
        prefix = f'{search}%'
        like_word = f'% {search}%'
        full_name = db.func.concat(Utilisateur.prenom, ' ', Utilisateur.nom)
        full_name_rev = db.func.concat(Utilisateur.nom, ' ', Utilisateur.prenom)

        relevance_score = db.case(
            (Utilisateur.prenom.ilike(exact), 1),
            (Utilisateur.nom.ilike(exact), 1),
            (full_name.ilike(exact), 2),
            (Utilisateur.prenom.ilike(prefix), 3),
            (Utilisateur.nom.ilike(prefix), 4),
            (full_name.ilike(prefix), 4),
            (full_name_rev.ilike(prefix), 4),
            (Utilisateur.poste.ilike(prefix), 5),
            (Utilisateur.poste.ilike(like_word), 6),
            (email_cond if '@' in search else db.func.split_part(Utilisateur.email, '@', 1).ilike(prefix), 7),
            (Utilisateur.prenom.ilike(like), 8),
            (Utilisateur.nom.ilike(like), 9),
            (Utilisateur.poste.ilike(like), 10),
            else_=11
        )
        order_clauses = [relevance_score.asc(), Utilisateur.prenom.asc(), Utilisateur.nom.asc()]
    else:
        order_clauses = [Utilisateur.prenom.asc(), Utilisateur.nom.asc()]

    utilisateurs_page = q.order_by(*order_clauses).paginate(page=page, per_page=20, error_out=False)

    total_actifs = Utilisateur.query.filter_by(actif=True).count()
    total_inactifs = Utilisateur.query.filter_by(actif=False).count()

    roles = Role.query.filter_by(actif=True).order_by(Role.niveau.desc()).all()
    departements = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()

    return render_template(
        'admin/utilisateurs.html',
        utilisateurs=utilisateurs_page,
        roles=roles,
        departements=departements,
        total_actifs=total_actifs,
        total_inactifs=total_inactifs,
    )


def _read_user_form(existing=None):
    """Lit et valide le formulaire utilisateur. Retourne (valeurs, erreurs)."""
    errors = []
    nom = request.form.get('nom', '').strip()
    prenom = request.form.get('prenom', '').strip()
    email = request.form.get('email', '').strip().lower()
    if not nom or not prenom:
        errors.append('Le nom et le prénom sont obligatoires.')
    if not email or not EMAIL_RE.match(email):
        errors.append("L'adresse email est invalide.")
    elif len(email) > 120:
        errors.append("L'adresse email est trop longue (120 caractères maximum).")
    else:
        other = Utilisateur.query.filter(db.func.lower(Utilisateur.email) == email).first()
        if other and (existing is None or other.id != existing.id):
            errors.append(f"L'adresse email {email} est déjà utilisée par un autre compte.")

    role_id = request.form.get('role_id') or None
    err = _check_role_assignment(role_id)
    if err:
        errors.append(err)

    values = dict(
        nom=nom, prenom=prenom, email=email, role_id=role_id,
        departement_id=request.form.get('departement_id') or None,
        pdv_id=request.form.get('pdv_id') or None,
        entreprise_id=request.form.get('entreprise_id') or None,
        telephone=request.form.get('telephone', '').strip()[:20] or None,
        poste=request.form.get('poste', '').strip()[:100] or None,
        anydesk_id=request.form.get('anydesk_id', '').strip()[:50] or None,
        anydesk_password=request.form.get('anydesk_password', '').strip()[:100] or None,
        teamviewer_id=request.form.get('teamviewer_id', '').strip()[:50] or None,
        teamviewer_password=request.form.get('teamviewer_password', '').strip()[:100] or None,
        poste_machine=request.form.get('poste_machine', '').strip()[:100] or None,
    )
    return values, errors


@admin_bp.route('/utilisateurs/nouveau', methods=['GET', 'POST'])
@login_required
@admin_required
def nouvel_utilisateur():
    """Créer un nouvel utilisateur"""
    if request.method == 'POST':
        values, errors = _read_user_form()
        password = request.form.get('password', '')
        min_len = 8
        if len(password) < min_len:
            errors.append(f'Le mot de passe doit contenir au moins {min_len} caractères.')

        if errors:
            for msg in errors:
                flash(msg, 'danger')
            return render_template('admin/nouvel_utilisateur.html', **_user_form_context())

        try:
            utilisateur = Utilisateur(matricule=None, **values)
            utilisateur.set_password(password)
            db.session.add(utilisateur)
            db.session.commit()

            flash('Utilisateur créé avec succès', 'success')
            logger.info(f'Nouvel utilisateur créé: {utilisateur.email} par {current_user.email}')
            return redirect(url_for('admin.utilisateurs'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création de l'utilisateur: {e}", exc_info=True)
            flash("Erreur lors de la création de l'utilisateur", 'danger')

    return render_template('admin/nouvel_utilisateur.html', **_user_form_context())


@admin_bp.route('/utilisateurs/<user_id>/modifier', methods=['GET', 'POST'])
@login_required
@admin_required
def modifier_utilisateur(user_id):
    """Modifier un utilisateur"""
    utilisateur = Utilisateur.query.get_or_404(user_id)

    # Un administrateur ne peut pas modifier un compte de niveau supérieur au sien
    if role_level(utilisateur) > role_level(current_user):
        flash("Vous ne pouvez pas modifier un compte de niveau supérieur au vôtre.", 'danger')
        return redirect(url_for('admin.utilisateurs'))

    if request.method == 'POST':
        values, errors = _read_user_form(existing=utilisateur)
        actif = request.form.get('actif') == '1'
        if utilisateur.id == current_user.id and not actif:
            errors.append('Vous ne pouvez pas vous désactiver vous-même.')
        nouveau_mdp = request.form.get('nouveau_password', '')
        if nouveau_mdp and len(nouveau_mdp) < 8:
            errors.append('Le nouveau mot de passe doit contenir au moins 8 caractères.')

        if errors:
            for msg in errors:
                flash(msg, 'danger')
            return redirect(url_for('admin.modifier_utilisateur', user_id=user_id))

        try:
            for key, value in values.items():
                setattr(utilisateur, key, value)
            if utilisateur.actif and not actif:
                utilisateur.revoke_sessions()
            utilisateur.actif = actif

            if nouveau_mdp:
                utilisateur.set_password(nouveau_mdp)
                utilisateur.revoke_sessions()  # force une reconnexion avec le nouveau mot de passe

            db.session.commit()
            flash('Utilisateur modifié avec succès', 'success')
            logger.info(f'Utilisateur modifié: {utilisateur.email} par {current_user.email}')
            return redirect(url_for('admin.utilisateurs'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la modification de l'utilisateur: {e}", exc_info=True)
            flash('Erreur lors de la modification', 'danger')

    return render_template('admin/modifier_utilisateur.html', utilisateur=utilisateur, **_user_form_context())


@admin_bp.route('/utilisateurs/<user_id>/desactiver', methods=['POST'])
@login_required
@admin_required
def desactiver_utilisateur(user_id):
    """Désactiver un utilisateur"""
    if user_id == current_user.id:
        flash('Vous ne pouvez pas vous désactiver vous-même', 'danger')
        return redirect(url_for('admin.utilisateurs'))

    utilisateur = Utilisateur.query.get_or_404(user_id)
    if role_level(utilisateur) > role_level(current_user):
        flash("Vous ne pouvez pas désactiver un compte de niveau supérieur au vôtre.", 'danger')
        return redirect(url_for('admin.utilisateurs'))

    try:
        utilisateur.actif = False
        utilisateur.revoke_sessions()
        db.session.commit()

        flash('Utilisateur désactivé', 'success')
        logger.info(f'Utilisateur désactivé: {utilisateur.email} par {current_user.email}')

    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur lors de la désactivation: {e}', exc_info=True)
        flash('Erreur lors de la désactivation', 'danger')

    return redirect(url_for('admin.utilisateurs'))


@admin_bp.route('/utilisateurs/<user_id>/reactiver', methods=['POST'])
@login_required
@admin_required
def reactiver_utilisateur(user_id):
    """Réactiver un utilisateur désactivé (et lever un éventuel verrouillage)"""
    utilisateur = Utilisateur.query.get_or_404(user_id)
    if role_level(utilisateur) > role_level(current_user):
        flash("Vous ne pouvez pas modifier un compte de niveau supérieur au vôtre.", 'danger')
        return redirect(url_for('admin.utilisateurs'))
    try:
        utilisateur.actif = True
        utilisateur.verrouille = False
        utilisateur.date_verrouillage = None
        utilisateur.tentatives_connexion = 0
        db.session.commit()
        flash(f'{utilisateur.prenom} {utilisateur.nom} a été réactivé', 'success')
        logger.info(f'Utilisateur réactivé: {utilisateur.email} par {current_user.email}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur lors de la réactivation: {e}', exc_info=True)
        flash('Erreur lors de la réactivation', 'danger')
    return redirect(url_for('admin.utilisateurs'))


@admin_bp.route('/roles')
@login_required
@admin_required
def roles():
    """Gestion des rôles et permissions"""
    roles = Role.query.order_by(Role.niveau.desc()).all()
    permissions = Permission.query.order_by(Permission.categorie, Permission.nom).all()
    perms_by_cat_raw = {}
    for p in permissions:
        cat = 'Espace de travail' if p.categorie == 'Tickets Actions' else p.categorie
        perms_by_cat_raw.setdefault(cat, []).append(p)

    # Ordre enregistré des catégories (s'il existe)
    saved_order_raw = ConfigurationSysteme.get_valeur('roles_categories_order', '[]')
    try:
        saved_order = json.loads(saved_order_raw)
    except Exception:
        saved_order = []

    perms_by_cat = {}
    for cat in saved_order:
        if cat in perms_by_cat_raw:
            perms_by_cat[cat] = perms_by_cat_raw.pop(cat)
    for cat, items in perms_by_cat_raw.items():
        perms_by_cat[cat] = items

    return render_template('admin/roles.html', roles=roles, perms_by_cat=perms_by_cat)


@admin_bp.route('/roles/ordonner-categories', methods=['POST'])
@login_required
@admin_required
def ordonner_categories_roles():
    """Sauvegarde l'ordre permanent des catégories de permissions (drag & drop)"""
    data = request.get_json(silent=True) or {}
    order = data.get('order', [])
    if isinstance(order, list) and order and all(isinstance(c, str) for c in order):
        ConfigurationSysteme.set_valeur(
            cle='roles_categories_order',
            valeur=json.dumps(order, ensure_ascii=False),
            description="Ordre d'affichage des catégories de permissions dans la gestion des rôles"
        )
        return jsonify({'success': True, 'order': order})
    return jsonify({'success': False, 'error': 'Format invalide'}), 400


@admin_bp.route('/permissions')
@login_required
@admin_required
def permissions():
    """Liste de toutes les permissions système"""
    permissions_list = Permission.query.order_by(Permission.categorie, Permission.nom).all()
    perms_by_cat = {}
    for p in permissions_list:
        perms_by_cat.setdefault(p.categorie, []).append(p)
    return render_template('admin/permissions.html', perms_by_cat=perms_by_cat)


@admin_bp.route('/permissions/creer', methods=['POST'])
@login_required
@admin_required
def creer_permission():
    nom = request.form.get('nom', '').strip()
    code = request.form.get('code', '').strip()
    description = request.form.get('description', '').strip()
    categorie = request.form.get('categorie', '').strip()
    if not nom or not code:
        flash("Le nom et le code sont obligatoires.", "danger")
        return redirect(url_for('admin.permissions'))
    if not PERMISSION_CODE_RE.match(code) or len(code) > 100:
        flash("Code invalide : utilisez des minuscules, chiffres, « _ » et « . » (ex. tickets.voir_tous).", "danger")
        return redirect(url_for('admin.permissions'))
    if Permission.query.filter_by(code=code).first():
        flash("Ce code de permission existe déjà.", "danger")
        return redirect(url_for('admin.permissions'))
    db.session.add(Permission(nom=nom[:100], code=code, description=description, categorie=categorie[:50] or None))
    db.session.commit()
    flash(f"Permission {code} créée avec succès.", "success")
    return redirect(url_for('admin.permissions'))


@admin_bp.route('/permissions/<string:id>/supprimer', methods=['POST'])
@login_required
@admin_required
def supprimer_permission(id):
    p = Permission.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    flash("Permission supprimée.", "success")
    return redirect(url_for('admin.permissions'))


@admin_bp.route('/roles/<role_id>/permissions', methods=['POST'])
@login_required
@admin_required
def modifier_permissions_role(role_id):
    """Modifier les permissions d'un rôle"""
    role = Role.query.get_or_404(role_id)
    if (role.niveau or 0) > role_level(current_user):
        flash("Vous ne pouvez pas modifier un rôle de niveau supérieur au vôtre.", 'danger')
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
    nom = request.form.get('nom', '').strip()
    if not nom:
        flash('Le nom du rôle est requis.', 'danger')
        return redirect(url_for('admin.roles'))
    if len(nom) > 100:
        flash('Le nom du rôle est trop long (100 caractères maximum).', 'danger')
        return redirect(url_for('admin.roles'))
    if Role.query.filter_by(nom=nom).first():
        flash(f'Un rôle nommé "{nom}" existe déjà.', 'danger')
        return redirect(url_for('admin.roles'))
    niveau = parse_int(request.form.get('niveau', 0), None, 0, 100)
    if niveau is None:
        flash('Le niveau doit être un entier entre 0 et 100.', 'danger')
        return redirect(url_for('admin.roles'))
    if niveau > role_level(current_user):
        flash("Vous ne pouvez pas créer un rôle de niveau supérieur au vôtre.", 'danger')
        return redirect(url_for('admin.roles'))
    role = Role(
        nom=nom,
        description=request.form.get('description', '').strip(),
        couleur=safe_color(request.form.get('couleur', ''), '#3B82F6'),
        niveau=niveau,
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
    role = Role.query.get_or_404(role_id)
    if role.systeme:
        flash('Les rôles système ne peuvent pas être modifiés.', 'warning')
        return redirect(url_for('admin.roles'))
    if (role.niveau or 0) > role_level(current_user):
        flash("Vous ne pouvez pas modifier un rôle de niveau supérieur au vôtre.", 'danger')
        return redirect(url_for('admin.roles'))
    nom = request.form.get('nom', role.nom).strip()
    niveau = parse_int(request.form.get('niveau', role.niveau), None, 0, 100)
    if not nom or len(nom) > 100 or niveau is None:
        flash('Nom ou niveau invalide (niveau : entier entre 0 et 100).', 'danger')
        return redirect(url_for('admin.roles'))
    if niveau > role_level(current_user):
        flash("Vous ne pouvez pas attribuer un niveau supérieur au vôtre.", 'danger')
        return redirect(url_for('admin.roles'))
    other = Role.query.filter(Role.nom == nom, Role.id != role.id).first()
    if other:
        flash(f'Un rôle nommé "{nom}" existe déjà.', 'danger')
        return redirect(url_for('admin.roles'))
    role.nom = nom
    role.description = request.form.get('description', '').strip()
    role.couleur = safe_color(request.form.get('couleur', ''), role.couleur)
    role.niveau = niveau
    db.session.commit()
    flash(f'Rôle "{role.nom}" mis à jour.', 'success')
    return redirect(url_for('admin.roles'))


@admin_bp.route('/roles/<role_id>/supprimer', methods=['POST'])
@login_required
@admin_required
def supprimer_role(role_id):
    role = Role.query.get_or_404(role_id)
    if role.systeme:
        flash('Les rôles système ne peuvent pas être supprimés.', 'warning')
        return redirect(url_for('admin.roles'))

    if role.utilisateurs:
        flash(f'Impossible de supprimer ce rôle car il est assigné à {len(role.utilisateurs)} utilisateur(s).', 'danger')
        return redirect(url_for('admin.roles'))

    nom = role.nom
    db.session.delete(role)
    db.session.commit()
    flash(f'Le rôle "{nom}" a été supprimé.', 'success')
    return redirect(url_for('admin.roles'))


@admin_bp.route('/roles/<role_id>/toggle-actif', methods=['POST'])
@login_required
@admin_required
def toggle_role_actif(role_id):
    role = Role.query.get_or_404(role_id)
    if role.systeme:
        flash('Les rôles système ne peuvent pas être désactivés.', 'warning')
        return redirect(url_for('admin.roles'))

    role.actif = not role.actif
    db.session.commit()
    etat = "activé" if role.actif else "désactivé"
    flash(f'Le rôle "{role.nom}" a été {etat}.', 'success')
    return redirect(url_for('admin.roles'))


# ─── Catégories de tickets ─────────────────────────────────────────────────
# Accès : permission « admin.categories » (attribuable à n'importe quel rôle depuis Rôles & permissions),
# le Super Administrateur l'a implicitement.
def categories_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.connexion'))
        if not (current_user.has_permission('admin.categories') or role_level(current_user) >= 90):
            flash("Vous n'avez pas la permission de gérer les catégories.", 'danger')
            return redirect(url_for('tickets.tableau_bord'))
        return f(*args, **kwargs)
    return decorated_function


def _categorie_fields():
    """Lit et valide le formulaire de catégorie. Retourne (valeurs, erreur)."""
    nom = request.form.get('nom', '').strip()
    if not nom:
        return None, 'Le nom de la catégorie est requis.'
    if len(nom) > 100:
        return None, 'Le nom de la catégorie est trop long (100 caractères maximum).'
    departement_id = request.form.get('departement_id') or None
    if not departement_id or not db.session.get(Departement, departement_id):
        return None, 'Veuillez choisir un département valide.'
    type_ticket = request.form.get('type_ticket', 'demande')
    priorite = request.form.get('priorite_defaut', 'moyenne')
    delai = parse_int(request.form.get('delai_resolution_jours') or 1, None, 1, 3650)
    if type_ticket not in TICKET_TYPES or priorite not in CATEGORY_PRIORITIES or delai is None:
        return None, 'Type, priorité ou délai de résolution invalide.'
    return {
        'nom': nom,
        'description': request.form.get('description', '').strip() or None,
        'type_ticket': type_ticket,
        'departement_id': departement_id,
        'priorite_defaut': priorite,
        'delai_resolution_jours': delai,
        'couleur': safe_color(request.form.get('couleur', ''), '#3B82F6'),
    }, None


def _nom_deja_pris(nom, departement_id, sauf_id=None):
    q = CategorieTicket.query.filter(db.func.lower(CategorieTicket.nom) == nom.lower(),
                                     CategorieTicket.departement_id == departement_id)
    if sauf_id:
        q = q.filter(CategorieTicket.id != sauf_id)
    return q.first() is not None


@admin_bp.route('/categories')
@login_required
@categories_required
def categories():
    """Gestion des catégories de tickets"""
    categories = CategorieTicket.query.order_by(CategorieTicket.nom).all()
    departements = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()
    nb_tickets = dict(db.session.query(Ticket.categorie_id, db.func.count(Ticket.id))
                      .filter(Ticket.categorie_id.isnot(None)).group_by(Ticket.categorie_id).all())
    return render_template('admin/categories.html', categories=categories, departements=departements,
                           nb_tickets=nb_tickets, ticket_types=TICKET_TYPES, priorites=CATEGORY_PRIORITIES)


@admin_bp.route('/categories/creer', methods=['POST'])
@login_required
@categories_required
def creer_categorie():
    """Créer une nouvelle catégorie de ticket"""
    valeurs, erreur = _categorie_fields()
    if erreur:
        flash(erreur, 'danger')
    elif _nom_deja_pris(valeurs['nom'], valeurs['departement_id']):
        flash('Une catégorie portant ce nom existe déjà dans ce département.', 'danger')
    else:
        try:
            db.session.add(CategorieTicket(**valeurs))
            db.session.commit()
            flash(f"Catégorie « {valeurs['nom']} » créée avec succès.", 'success')
            logger.info(f"Catégorie créée: {valeurs['nom']} par {current_user.email}")
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur création catégorie: {e}', exc_info=True)
            flash('Erreur lors de la création de la catégorie.', 'danger')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/categories/<cat_id>/modifier', methods=['POST'])
@login_required
@categories_required
def modifier_categorie(cat_id):
    """Modifier une catégorie (nom, département, type, priorité, délai, couleur)"""
    cat = CategorieTicket.query.get_or_404(cat_id)
    valeurs, erreur = _categorie_fields()
    if erreur:
        flash(erreur, 'danger')
    elif _nom_deja_pris(valeurs['nom'], valeurs['departement_id'], sauf_id=cat.id):
        flash('Une autre catégorie porte déjà ce nom dans ce département.', 'danger')
    else:
        try:
            for champ, valeur in valeurs.items():
                setattr(cat, champ, valeur)
            db.session.commit()
            flash(f"Catégorie « {cat.nom} » modifiée. Les tickets existants ne sont pas modifiés.", 'success')
            logger.info(f'Catégorie modifiée: {cat.nom} par {current_user.email}')
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur modification catégorie: {e}', exc_info=True)
            flash('Erreur lors de la modification de la catégorie.', 'danger')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/categories/<cat_id>/toggle', methods=['POST'])
@login_required
@categories_required
def toggle_categorie(cat_id):
    """Activer/désactiver une catégorie (désactivée = masquée du formulaire de ticket)"""
    cat = CategorieTicket.query.get_or_404(cat_id)
    cat.actif = not cat.actif
    db.session.commit()
    flash(f"Catégorie « {cat.nom} » {'activée' if cat.actif else 'désactivée'}.", 'success')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/categories/<cat_id>/archiver', methods=['POST'])
@login_required
@categories_required
def archiver_categorie(cat_id):
    """Archiver / restaurer une catégorie (conserve l'historique des tickets)"""
    cat = CategorieTicket.query.get_or_404(cat_id)
    cat.archivee = not cat.archivee
    if cat.archivee:
        cat.actif = False
    db.session.commit()
    flash(f"Catégorie « {cat.nom} » {'archivée' if cat.archivee else 'restaurée (inactive : activez-la pour la proposer)'}.", 'success')
    logger.info(f"Catégorie {'archivée' if cat.archivee else 'restaurée'}: {cat.nom} par {current_user.email}")
    return redirect(url_for('admin.categories'))


@admin_bp.route('/categories/<cat_id>/supprimer', methods=['POST'])
@login_required
@categories_required
def supprimer_categorie(cat_id):
    """Supprimer définitivement une catégorie (uniquement si aucun ticket ne l'utilise)"""
    cat = CategorieTicket.query.get_or_404(cat_id)
    nb = Ticket.query.filter_by(categorie_id=cat.id).count()
    if nb:
        flash(f"« {cat.nom} » est utilisée par {nb} ticket(s) : elle ne peut pas être supprimée. Archivez-la à la place.", 'warning')
        return redirect(url_for('admin.categories'))
    try:
        nom = cat.nom
        db.session.delete(cat)
        db.session.commit()
        flash(f'Catégorie « {nom} » supprimée.', 'success')
        logger.info(f'Catégorie supprimée: {nom} par {current_user.email}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur suppression catégorie: {e}', exc_info=True)
        flash('Erreur lors de la suppression de la catégorie.', 'danger')
    return redirect(url_for('admin.categories'))


# ─── Paramètres système (.env) ─────────────────────────────────────────────
_ENV_KEYS = ['MAIL_SERVER', 'MAIL_PORT', 'MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_DEFAULT_SENDER', 'TIMEZONE']
_ENV_SECRETS = {'MAIL_PASSWORD'}
_ENV_BOOLS = ['MAIL_USE_TLS', 'MAIL_USE_SSL']


@admin_bp.route('/parametres', methods=['GET', 'POST'])
@login_required
def parametres_systeme():
    """Paramètres système (fichier .env)"""
    from dotenv import dotenv_values, set_key

    if not current_user.has_permission('admin_parametres.voir'):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('tickets.tableau_bord'))

    dotenv_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '.env')

    if request.method == 'POST':
        if not current_user.has_permission('admin_parametres.modifier'):
            flash("Vous n'avez pas la permission de modifier les paramètres.", "danger")
            return redirect(url_for('admin.parametres_systeme'))
        try:
            updates = {}
            for key in _ENV_KEYS:
                if key not in request.form:
                    continue
                val = request.form.get(key, '').strip()
                if re.search(r'[\r\n\x00]', val):
                    raise ValueError(f'Valeur invalide pour {key}')
                if key in _ENV_SECRETS and not val:
                    continue  # champ vide = conserver le mot de passe actuel
                if key == 'MAIL_PORT':
                    port = parse_int(val, None, 1, 65535)
                    if port is None:
                        raise ValueError('Le port doit être un entier entre 1 et 65535')
                    val = str(port)
                if key == 'TIMEZONE':
                    import pytz
                    if val not in pytz.all_timezones_set:
                        raise ValueError('Fuseau horaire inconnu')
                updates[key] = val
            if 'MAIL_SERVER' in request.form:
                for key in _ENV_BOOLS:
                    updates[key] = 'True' if request.form.get(key) else 'False'

            for key, val in updates.items():
                set_key(dotenv_path, key, val)

            logger.info("Paramètres système modifiés par %s : %s", current_user.email, sorted(updates))
            flash('Paramètres mis à jour avec succès. Un redémarrage du serveur est nécessaire pour les appliquer.', 'success')
            return redirect(url_for('admin.parametres_systeme'))
        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des paramètres: {e}", exc_info=True)
            flash("Erreur lors de l'enregistrement des paramètres.", "danger")

    config_vals = dict(dotenv_values(dotenv_path)) if os.path.exists(dotenv_path) else {}
    for secret in _ENV_SECRETS:  # ne jamais renvoyer les secrets au navigateur
        config_vals[secret] = ''

    return render_template('admin/parametres.html', config=config_vals)


@admin_bp.route('/parametres/test-email', methods=['POST'])
@login_required
def tester_email():
    """Teste la configuration SMTP enregistrée dans .env : connexion, authentification, envoi à l'administrateur connecté."""
    import smtplib
    import ssl
    from email.message import EmailMessage
    from dotenv import dotenv_values

    if not current_user.has_permission('admin_parametres.modifier'):
        flash("Vous n'avez pas la permission de tester les paramètres.", "danger")
        return redirect(url_for('admin.parametres_systeme'))

    dotenv_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '.env')
    cfg = dotenv_values(dotenv_path) if os.path.exists(dotenv_path) else {}
    server = (cfg.get('MAIL_SERVER') or '').strip()
    user = (cfg.get('MAIL_USERNAME') or '').strip()
    password = cfg.get('MAIL_PASSWORD') or ''
    sender = (cfg.get('MAIL_DEFAULT_SENDER') or user).strip()
    use_ssl = (cfg.get('MAIL_USE_SSL') or '').strip().lower() == 'true'
    use_tls = (cfg.get('MAIL_USE_TLS') or '').strip().lower() == 'true'
    port = parse_int(cfg.get('MAIL_PORT'), 465 if use_ssl else 587, 1, 65535)

    if not (server and user and password):
        flash("Configuration incomplète : serveur, nom d'utilisateur et mot de passe sont nécessaires.", "danger")
        return redirect(url_for('admin.parametres_systeme'))

    smtp = None
    try:
        context = ssl.create_default_context()
        smtp = smtplib.SMTP_SSL(server, port, timeout=15, context=context) if use_ssl else smtplib.SMTP(server, port, timeout=15)
        if use_tls and not use_ssl:
            smtp.starttls(context=context)
        smtp.login(user, password)
        msg = EmailMessage()
        msg['Subject'] = 'Test de configuration e-mail — CosmiCenter'
        msg['From'] = sender
        msg['To'] = current_user.email
        msg.set_content("Ce message confirme que CosmiCenter peut envoyer des e-mails avec la configuration SMTP actuelle.")
        smtp.send_message(msg)
        flash(f"E-mail de test envoyé à {current_user.email} : la configuration SMTP fonctionne.", "success")
        logger.info("Test e-mail SMTP réussi par %s", current_user.email)
    except smtplib.SMTPAuthenticationError as e:
        code = getattr(e, 'smtp_code', '')
        flash(f"Authentification refusée par le serveur (code {code}). Vérifiez l'identifiant et le mot de passe "
              f"(avec Gmail ou Microsoft 365 il faut en général un « mot de passe d'application », et l'authentification "
              f"SMTP doit être autorisée pour la boîte).", "danger")
        logger.warning("Test e-mail SMTP : authentification refusée (code %s)", code)
    except Exception as e:
        flash(f"Échec de l'envoi : {type(e).__name__} — {str(e)[:200]}", "danger")
        logger.warning("Test e-mail SMTP : %s", type(e).__name__)
    finally:
        if smtp is not None:
            try:
                smtp.quit()
            except Exception:
                pass
    return redirect(url_for('admin.parametres_systeme'))


def _tail_lines(path, max_bytes=1024 * 1024):
    """Dernières lignes d'un fichier sans le charger entièrement en mémoire."""
    size = os.path.getsize(path)
    with open(path, 'rb') as f:
        if size > max_bytes:
            f.seek(-max_bytes, os.SEEK_END)
            f.readline()  # ligne probablement tronquée
        data = f.read()
    return data.decode('utf-8', errors='replace').splitlines()


@admin_bp.route('/logs')
@login_required
def logs():
    """Visualisation des logs système"""
    if not current_user.has_permission('admin_logs.voir'):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('tickets.tableau_bord'))

    log_file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'logs', 'app.log')
    logs_content = []

    if os.path.exists(log_file_path):
        try:
            lines = _tail_lines(log_file_path)
            # Ne garder que les erreurs/anomalies et les tracebacks
            filtered = [line for line in lines if ' - INFO - ' not in line and ' - DEBUG - ' not in line]
            # chaque ligne garde son saut de ligne : le gabarit les concatène dans un bloc <pre>
            logs_content = [line + '\n' for line in filtered[-500:]]
            logs_content.reverse()
        except Exception as e:
            logger.error(f"Lecture des logs impossible: {e}")
            logs_content = ["Erreur lors de la lecture des logs."]
    else:
        logs_content = ["Aucun fichier de log trouvé."]

    return render_template('admin/logs.html', logs=logs_content)


# ─── Plan d'action ─────────────────────────────────────────────────────────

@admin_bp.route('/plan-action')
@login_required
@permission_required('admin_plan_action.voir')
def plan_action():
    """Plan d'action - calendrier et projets IT"""
    tasks = PlanActionTask.query.order_by(PlanActionTask.date_debut).all()
    utilisateurs = Utilisateur.query.filter_by(actif=True).all()
    return render_template('admin/plan_action.html', tasks=tasks, utilisateurs=utilisateurs)


@admin_bp.route('/api/plan-action/tasks')
@login_required
@permission_required('admin_plan_action.voir')
def api_plan_action_tasks():
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


def _plan_action_edit_allowed():
    return current_user.has_permission('admin_plan_action.modifier') or role_level(current_user) >= 90


def _read_plan_action_form():
    """Valide le formulaire du plan d'action. Retourne (valeurs, erreur)."""
    titre = request.form.get('titre', '').strip()
    date_debut = _parse_datetime(request.form.get('date_debut'))
    date_fin_str = request.form.get('date_fin')
    date_fin = _parse_datetime(date_fin_str)
    if not titre:
        return None, "Le titre est obligatoire."
    if len(titre) > 200:
        return None, "Le titre est trop long (200 caractères maximum)."
    if not date_debut:
        return None, "Une date de début valide est obligatoire."
    if date_fin_str and not date_fin:
        return None, "La date de fin est invalide."
    if date_fin and date_fin < date_debut:
        return None, "La date de fin doit être postérieure à la date de début."
    assigne = request.form.get('assigne_a_id') or None
    if assigne and not db.session.get(Utilisateur, assigne):
        return None, "Utilisateur assigné introuvable."
    return dict(titre=titre, description=request.form.get('description', '').strip(),
                date_debut=date_debut, date_fin=date_fin,
                urgent=request.form.get('urgent') == 'on', assigne_a_id=assigne), None


@admin_bp.route('/plan-action/creer', methods=['POST'])
@login_required
@permission_required('admin_plan_action.voir')
def creer_plan_action():
    if not _plan_action_edit_allowed():
        flash("Vous n'avez pas la permission de modifier le plan d'action.", "danger")
        return redirect(url_for('admin.plan_action'))
    values, error = _read_plan_action_form()
    if error:
        flash(error, "danger")
        return redirect(url_for('admin.plan_action'))

    db.session.add(PlanActionTask(statut='planned', createur_id=current_user.id, **values))
    db.session.commit()
    flash("Tâche ajoutée au plan d'action.", "success")
    return redirect(url_for('admin.plan_action'))


def _set_plan_status(id, statut, message):
    if not _plan_action_edit_allowed():
        flash("Vous n'avez pas la permission de modifier le plan d'action.", "danger")
        return redirect(url_for('admin.plan_action'))
    task = PlanActionTask.query.get_or_404(id)
    task.statut = statut
    db.session.commit()
    flash(message, 'success')
    return redirect(url_for('admin.plan_action'))


@admin_bp.route('/plan-action/<string:id>/terminer', methods=['POST'])
@login_required
@permission_required('admin_plan_action.voir')
def terminer_plan_action(id):
    return _set_plan_status(id, 'completed', 'Tâche marquée comme terminée.')


@admin_bp.route('/plan-action/<string:id>/annuler-terminer', methods=['POST'])
@login_required
@permission_required('admin_plan_action.voir')
def annuler_terminer_plan_action(id):
    return _set_plan_status(id, 'planned', 'Le statut de la tâche a été réinitialisé.')


@admin_bp.route('/plan-action/<string:id>/modifier', methods=['POST'])
@login_required
@permission_required('admin_plan_action.voir')
def modifier_plan_action(id):
    if not _plan_action_edit_allowed():
        flash("Vous n'avez pas la permission de modifier le plan d'action.", "danger")
        return redirect(url_for('admin.plan_action'))
    task = PlanActionTask.query.get_or_404(id)
    values, error = _read_plan_action_form()
    if error:
        flash(error, "danger")
        return redirect(url_for('admin.plan_action'))
    for key, value in values.items():
        setattr(task, key, value)
    db.session.commit()
    flash('Tâche modifiée avec succès.', 'success')
    return redirect(url_for('admin.plan_action'))


@admin_bp.route('/plan-action/<string:id>/supprimer', methods=['POST'])
@login_required
@permission_required('admin_plan_action.voir')
def supprimer_plan_action(id):
    if not _plan_action_edit_allowed():
        flash("Vous n'avez pas la permission de modifier le plan d'action.", "danger")
        return redirect(url_for('admin.plan_action'))
    task = PlanActionTask.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    flash("Tâche supprimée.", "success")
    return redirect(url_for('admin.plan_action'))


@admin_bp.route('/plan-action/export-excel')
@login_required
@permission_required('admin_plan_action.voir')
def export_plan_action_excel():
    """Export du plan d'action en fichier Excel formaté"""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    # ── Paramètres de filtrage ──────────────────────────────────
    mode = request.args.get('mode', 'all')      # all | day | periode
    date_jour = request.args.get('date_jour', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = PlanActionTask.query

    if mode == 'day' and date_jour:
        d = _parse_datetime(date_jour)
        if d:
            query = query.filter(db.func.date(PlanActionTask.date_debut) == d.date())
    elif mode == 'periode' and date_from:
        df = _parse_datetime(date_from)
        if df:
            query = query.filter(PlanActionTask.date_debut >= df)
            dt = _parse_datetime(date_to)
            if dt:
                query = query.filter(PlanActionTask.date_debut <= dt)

    tasks = query.order_by(PlanActionTask.date_debut).all()

    # ── Workbook & styles ───────────────────────────────────────
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Plan d'action"

    COLOR_HEADER_BG = "1E1B4B"
    COLOR_HEADER_FG = "FFFFFF"
    COLOR_URGENT = "FEE2E2"
    COLOR_COMPLETED = "D1FAE5"
    COLOR_ALT = "F8FAFC"

    thin = Side(style='thin', color="E2E8F0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    header_font = Font(bold=True, color=COLOR_HEADER_FG, size=11, name="Calibri")
    header_fill = PatternFill("solid", fgColor=COLOR_HEADER_BG)
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    title_font = Font(bold=True, size=16, color=COLOR_HEADER_BG, name="Calibri")
    subtitle_font = Font(size=10, color="64748B", name="Calibri")
    cell_font = Font(size=10, name="Calibri")
    bold_font = Font(bold=True, size=10, name="Calibri")

    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # ── Bloc titre ──────────────────────────────────────────────
    ws.merge_cells("A1:H1")
    ws["A1"] = "Plan d'Action — CosmiCenter"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 32

    ws.merge_cells("A2:H2")
    label_map = {
        'all': 'Toutes les tâches',
        'day': f'Jour : {date_jour}',
        'periode': f'Période : {date_from} → {date_to or "…"}',
    }
    ws["A2"] = f"Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}  |  Filtre : {csv_safe(label_map.get(mode, 'Toutes les tâches'))}  |  {len(tasks)} tâche(s)"
    ws["A2"].font = subtitle_font
    ws["A2"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[3].height = 10

    # ── En-têtes (ligne 4) ──────────────────────────────────────
    headers = ["#", "Titre", "Description", "Statut", "Urgent", "Date début", "Date fin", "Assigné à"]
    widths = [5, 35, 45, 12, 10, 14, 14, 22]

    for col, (h, w) in enumerate(zip(headers, widths), start=1):
        cell = ws.cell(row=4, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = border
        ws.column_dimensions[get_column_letter(col)].width = w
    ws.row_dimensions[4].height = 28

    # ── Lignes de données ───────────────────────────────────────
    statut_labels = {'planned': 'Planifiée', 'progress': 'En cours', 'completed': 'Terminée'}

    for i, task in enumerate(tasks, start=1):
        row = 4 + i

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
            csv_safe(task.titre),
            csv_safe(task.description or ""),
            statut_labels.get(task.statut, task.statut),
            "🔥 Oui" if task.urgent else "Non",
            task.date_debut.strftime('%d/%m/%Y') if task.date_debut else "",
            task.date_fin.strftime('%d/%m/%Y') if task.date_fin else "—",
            f"{task.assigne_a.prenom} {task.assigne_a.nom}" if task.assigne_a else "Non assigné",
        ]
        aligns = [center, left, left, center, center, center, center, left]

        for col, (val, aln) in enumerate(zip(values, aligns), start=1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.font = bold_font if col == 2 else cell_font
            cell.fill = row_fill
            cell.alignment = aln
            cell.border = border

        ws.row_dimensions[row].height = 22

    ws.freeze_panes = "A5"

    # ── Ligne de synthèse ───────────────────────────────────────
    summary_row = 4 + len(tasks) + 2
    ws.merge_cells(f"A{summary_row}:C{summary_row}")
    ws[f"A{summary_row}"] = f"Total : {len(tasks)} tâche(s)"
    ws[f"A{summary_row}"].font = bold_font
    ws[f"A{summary_row}"].fill = PatternFill("solid", fgColor="E2E8F0")

    completed_count = sum(1 for t in tasks if t.statut == 'completed')
    urgent_count = sum(1 for t in tasks if t.urgent)
    ws.merge_cells(f"D{summary_row}:F{summary_row}")
    ws[f"D{summary_row}"] = f"Terminées : {completed_count}  |  Urgentes : {urgent_count}"
    ws[f"D{summary_row}"].font = bold_font
    ws[f"D{summary_row}"].fill = PatternFill("solid", fgColor="E2E8F0")
    ws[f"D{summary_row}"].alignment = center

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"plan_action_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@admin_bp.route('/acces-distance')
@login_required
@permission_required('admin_acces.voir')
def acces_distance():
    users = Utilisateur.query.filter_by(actif=True).order_by(Utilisateur.prenom.asc(), Utilisateur.nom.asc()).all()
    return render_template('admin/acces_distance.html', users=users)
