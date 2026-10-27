from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from models import db, Departement, Utilisateur, CategorieTicket, Ticket
from functools import wraps
from sqlalchemy import func
from datetime import datetime, timedelta
import logging
import re

from utils.permissions import role_level
from utils.security import safe_color, parse_int
from utils.uploads import save_upload, remove_upload, UploadError, IMAGE_EXTENSIONS, MAX_IMAGE_BYTES

departements_bp = Blueprint('departements', __name__)
logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
STATUTS_NON_TERMINES = ['nouveau', 'ouvert', 'en_cours', 'en_attente']


def require_permission(permission_code):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.has_permission(permission_code):
                flash('Accès non autorisé.', 'danger')
                return redirect(url_for('tickets.tableau_bord'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def any_permission(*permission_codes):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Accès non autorisé.', 'danger')
                return redirect(url_for('tickets.tableau_bord'))
            has_perm = any(current_user.has_permission(code) for code in permission_codes)
            if not has_perm:
                flash('Accès non autorisé.', 'danger')
                return redirect(url_for('tickets.tableau_bord'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def _can_edit_department(departement):
    """departements.modifier, ou departements.modifier_propre sur son propre département."""
    if current_user.has_permission('departements.modifier'):
        return True
    return (current_user.has_permission('departements.modifier_propre')
            and current_user.departement_id == departement.id)


def _can_manage_members():
    return current_user.has_permission('departements.gerer_membres')


def _read_department_form(departement=None):
    """Lit et valide le formulaire département. Retourne (valeurs, erreurs, nouveau_logo)."""
    errors = []
    nom = request.form.get('nom', '').strip()
    code = request.form.get('code', '').strip().upper()
    email = request.form.get('email', '').strip()
    sla_reponse = parse_int(request.form.get('sla_reponse_heures', 4), None, 1, 10000)
    sla_resolution = parse_int(request.form.get('sla_resolution_heures', 24), None, 1, 100000)

    if not nom:
        errors.append('Le nom du département est requis.')
    elif len(nom) > 100:
        errors.append('Le nom du département est trop long (100 caractères maximum).')
    if len(code) > 20:
        errors.append('Le code est trop long (20 caractères maximum).')
    if email and not EMAIL_RE.match(email):
        errors.append("L'adresse email est invalide.")
    if sla_reponse is None or sla_resolution is None:
        errors.append('Les délais SLA doivent être des nombres entiers positifs.')

    if nom:
        existing = Departement.query.filter_by(nom=nom).first()
        if existing and (departement is None or existing.id != departement.id):
            errors.append('Un département avec ce nom existe déjà.')
    if code:
        existing = Departement.query.filter_by(code=code).first()
        if existing and (departement is None or existing.id != departement.id):
            errors.append('Un département avec ce code existe déjà.')

    responsable_id = request.form.get('responsable_id', '').strip() or None
    if responsable_id and not db.session.get(Utilisateur, responsable_id):
        errors.append('Responsable introuvable.')

    values = dict(
        nom=nom,
        code=code or None,
        description=request.form.get('description', '').strip() or None,
        email=email or None,
        telephone=request.form.get('telephone', '').strip()[:20] or None,
        localisation=request.form.get('localisation', '').strip()[:200] or None,
        couleur=safe_color(request.form.get('couleur', ''), '#3B82F6'),
        responsable_id=responsable_id,
        sla_reponse_heures=sla_reponse,
        sla_resolution_heures=sla_resolution,
    )

    # Logo (images uniquement) : enregistré dans la colonne icone sous un nom aléatoire
    icone = request.form.get('icone', departement.icone if departement else 'building')
    new_logo = None
    logo_file = request.files.get('logo')
    if logo_file and logo_file.filename and not errors:
        try:
            new_logo, _o, _s = save_upload(logo_file, '', IMAGE_EXTENSIONS, MAX_IMAGE_BYTES)
            icone = new_logo
        except UploadError as exc:
            errors.append(str(exc))
    values['icone'] = (icone or 'building')[:50]
    return values, errors, new_logo


def _active_users_sorted():
    return sorted(
        Utilisateur.query.filter_by(actif=True).all(),
        key=lambda u: (u.nom_complet or '').strip().upper()
    )


@departements_bp.route('/')
@login_required
def liste():
    """Liste tous les départements"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Departement.query

    search = request.args.get('search', '').strip()
    if search:
        like = f'%{search}%'
        query = query.filter(
            (Departement.nom.ilike(like)) |
            (Departement.description.ilike(like))
        )

    actif_filter = request.args.get('actif', '')
    if actif_filter == '1':
        query = query.filter_by(actif=True)
    elif actif_filter == '0':
        query = query.filter_by(actif=False)

    departements = query.order_by(Departement.nom).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Statistiques par département (requêtes groupées : un nombre fixe de requêtes quelle que soit la page)
    ids = [d.id for d in departements.items]
    recus = dict(db.session.query(Ticket.departement_id, func.count(Ticket.id)).filter(
        Ticket.departement_id.in_(ids), Ticket.statut.in_(STATUTS_NON_TERMINES)
    ).group_by(Ticket.departement_id).all()) if ids else {}
    totaux = dict(db.session.query(Ticket.departement_id, func.count(Ticket.id)).filter(
        Ticket.departement_id.in_(ids)).group_by(Ticket.departement_id).all()) if ids else {}

    for dept in departements.items:
        # Tickets envoyés = créés par un membre de ce département, adressés à un autre département, non terminés
        membres_ids = [m.id for m in dept.membres]
        if membres_ids:
            tickets_envoyes_ouverts = Ticket.query.filter(
                Ticket.createur_id.in_(membres_ids),
                db.or_(Ticket.departement_id != dept.id, Ticket.departement_id.is_(None)),
                Ticket.statut.in_(STATUTS_NON_TERMINES)
            ).count()
        else:
            tickets_envoyes_ouverts = 0

        dept.stats = {
            'membres_actifs': sum(1 for m in dept.membres if m.actif),
            'membres_total': len(dept.membres),
            'tickets_recus_ouverts': recus.get(dept.id, 0),
            'tickets_envoyes_ouverts': tickets_envoyes_ouverts,
            'tickets_total': totaux.get(dept.id, 0),
        }

    return render_template('departements/liste.html',
                           departements=departements,
                           search=search,
                           actif_filter=actif_filter)


@departements_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
@require_permission('departements.creer')
def nouveau():
    """Créer un nouveau département"""
    if request.method == 'POST':
        values, errors, new_logo = _read_department_form()
        if errors:
            for msg in errors:
                flash(msg, 'danger')
            return render_template('departements/formulaire.html', utilisateurs=_active_users_sorted())

        departement = Departement(actif=True, **values)
        try:
            db.session.add(departement)
            db.session.commit()
            flash(f'Département "{departement.nom}" créé avec succès!', 'success')
            return redirect(url_for('departements.detail', id=departement.id))
        except Exception as e:
            db.session.rollback()
            if new_logo:
                remove_upload(new_logo)
            logger.error(f'Erreur création département: {e}', exc_info=True)
            flash('Erreur lors de la création du département.', 'danger')

    return render_template('departements/formulaire.html', utilisateurs=_active_users_sorted())


@departements_bp.route('/<string:id>')
@login_required
def detail(id):
    """Afficher les détails d'un département"""
    departement = Departement.query.get_or_404(id)

    # Tickets du département (même définition que la liste : ticket.departement_id)
    tickets_dept = Ticket.query.filter(Ticket.departement_id == departement.id)
    par_statut = dict(db.session.query(Ticket.statut, func.count(Ticket.id)).filter(
        Ticket.departement_id == departement.id).group_by(Ticket.statut).all())

    stats = {
        'membres_actifs': len([m for m in departement.membres if m.actif]),
        'membres_total': len(departement.membres),
        'categories': len(departement.categories),
        'tickets_total': sum(par_statut.values()),
        'tickets_nouveaux': par_statut.get('nouveau', 0) + par_statut.get('ouvert', 0),
        'tickets_en_cours': par_statut.get('en_cours', 0),
        'tickets_resolus': par_statut.get('resolu', 0),
    }

    tickets_recents = tickets_dept.order_by(Ticket.date_creation.desc()).limit(10).all()

    membres = sorted(
        Utilisateur.query.filter_by(departement_id=departement.id, actif=True).all(),
        key=lambda u: (u.nom_complet or '').strip().upper()
    )
    tous_utilisateurs = _active_users_sorted()

    from models import PointDeVente
    departements_list = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()
    pdvs_list = PointDeVente.query.filter_by(actif=True).order_by(PointDeVente.nom).all()

    return render_template('departements/detail.html',
                           departement=departement,
                           stats=stats,
                           tickets_recents=tickets_recents,
                           membres=membres,
                           tous_utilisateurs=tous_utilisateurs,
                           departements_list=departements_list,
                           pdvs_list=pdvs_list)


@departements_bp.route('/<string:id>/modifier', methods=['GET', 'POST'])
@login_required
@any_permission('departements.modifier', 'departements.modifier_propre')
def modifier(id):
    departement = Departement.query.get_or_404(id)

    if not _can_edit_department(departement):
        flash('Accès non autorisé. Vous ne pouvez modifier que votre propre département.', 'danger')
        return redirect(url_for('departements.liste'))

    if request.method == 'POST':
        values, errors, new_logo = _read_department_form(departement)
        actif = request.form.get('actif') in ['1', 'on', 'true', 'True']
        if errors:
            for msg in errors:
                flash(msg, 'danger')
            return render_template('departements/formulaire.html',
                                   departement=departement, is_edit=True,
                                   utilisateurs=_active_users_sorted())

        old_logo = departement.icone if new_logo else None
        for key, value in values.items():
            setattr(departement, key, value)
        departement.actif = actif

        try:
            db.session.commit()
            if old_logo and old_logo != new_logo and '.' in old_logo:
                remove_upload(old_logo)
            flash(f'Département "{departement.nom}" modifié avec succès!', 'success')
            return redirect(url_for('departements.detail', id=departement.id))
        except Exception as e:
            db.session.rollback()
            if new_logo:
                remove_upload(new_logo)
            logger.error(f'Erreur modification département: {e}', exc_info=True)
            flash('Erreur lors de la modification du département.', 'danger')

    return render_template('departements/formulaire.html',
                           departement=departement,
                           is_edit=True,
                           utilisateurs=_active_users_sorted())


@departements_bp.route('/<string:id>/supprimer', methods=['POST'])
@login_required
@require_permission('departements.supprimer')
def supprimer(id):
    """Supprimer un département"""
    departement = Departement.query.get_or_404(id)

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
        logger.error(f'Erreur suppression département: {e}', exc_info=True)
        flash('Erreur lors de la suppression du département.', 'danger')
        return redirect(url_for('departements.detail', id=id))


@departements_bp.route('/<string:id>/toggle-actif', methods=['POST'])
@login_required
@any_permission('departements.modifier', 'departements.modifier_propre')
def toggle_actif(id):
    """Activer/Désactiver un département"""
    departement = Departement.query.get_or_404(id)

    if not _can_edit_department(departement):
        flash('Accès non autorisé. Vous ne pouvez modifier que votre propre département.', 'danger')
        return redirect(url_for('departements.liste'))

    departement.actif = not departement.actif

    try:
        db.session.commit()
        status = 'activé' if departement.actif else 'désactivé'
        flash(f'Département "{departement.nom}" {status} avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur toggle département: {e}', exc_info=True)
        flash('Erreur lors de la mise à jour.', 'danger')

    return redirect(url_for('departements.detail', id=id))


@departements_bp.route('/<string:id>/assigner-membre', methods=['POST'])
@login_required
def assigner_membre(id):
    if not _can_manage_members():
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('departements.detail', id=id))

    dept = Departement.query.get_or_404(id)
    user = db.session.get(Utilisateur, request.form.get('utilisateur_id') or '')
    if user:
        user.departement_id = dept.id
        db.session.commit()
        flash(f"{user.nom_complet} a été assigné au département {dept.nom}.", "success")
    else:
        flash("Utilisateur introuvable.", "danger")

    return redirect(url_for('departements.detail', id=id))


@departements_bp.route('/<string:id>/retirer-membre/<string:user_id>', methods=['POST'])
@login_required
def retirer_membre(id, user_id):
    if not _can_manage_members():
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('departements.detail', id=id))

    user = db.session.get(Utilisateur, user_id)
    if user and user.departement_id == id:
        user.departement_id = None
        db.session.commit()
        flash(f"{user.nom_complet} a été retiré de ce département.", "success")

    return redirect(url_for('departements.detail', id=id))
