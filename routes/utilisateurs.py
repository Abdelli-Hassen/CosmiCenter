from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Utilisateur, Role, Departement, Entreprise, PointDeVente
from functools import wraps
import logging
import re
from datetime import datetime

from utils.permissions import role_level, can_assign_role

utilisateurs_bp = Blueprint('utilisateurs', __name__)
logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
PASSWORD_MIN_LENGTH = 8


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


def _role_error(role_id):
    """Erreur si le rôle n'existe pas ou dépasse le niveau de l'utilisateur connecté."""
    if not role_id:
        return None
    role = db.session.get(Role, role_id)
    if role is None:
        return 'Rôle introuvable.'
    if not can_assign_role(current_user, role):
        return "Vous ne pouvez pas attribuer un rôle de niveau supérieur au vôtre."
    return None

@utilisateurs_bp.route('/')
@login_required
def liste():
    """Liste tous les utilisateurs"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    if current_user.has_permission('utilisateurs.voir_tous'):
        base_query = Utilisateur.query
    else:
        base_query = Utilisateur.query.filter_by(departement_id=current_user.departement_id)
    
    # Counts for header stats (before filters)
    total_actifs = base_query.filter_by(actif=True).count()
    total_inactifs = base_query.filter_by(actif=False).count()

    query = base_query
        
    # Filtres
    search = request.args.get('search', '').strip()
    if search:
        search_pattern = f'%{search}%'
        from sqlalchemy import or_, func, case
        # If the search does not contain '@', only match the local username part (before '@')
        # using split_part (supported across PostgreSQL and SQLAlchemy)
        if '@' in search:
            email_condition = Utilisateur.email.ilike(search_pattern)
        else:
            email_local_part = func.split_part(Utilisateur.email, '@', 1)
            email_condition = email_local_part.ilike(search_pattern)

        # Match individual fields or combined "prenom nom" / "nom prenom"
        query = query.filter(
            or_(
                Utilisateur.nom.ilike(search_pattern),
                Utilisateur.prenom.ilike(search_pattern),
                (func.concat(Utilisateur.prenom, ' ', Utilisateur.nom)).ilike(search_pattern),
                (func.concat(Utilisateur.nom, ' ', Utilisateur.prenom)).ilike(search_pattern),
                email_condition,
                Utilisateur.poste.ilike(search_pattern)
            )
        )
    
    role_filter = request.args.get('role', '')
    if role_filter:
        query = query.filter_by(role_id=role_filter)
    
    dept_filter = request.args.get('departement', '')
    if dept_filter:
        query = query.filter_by(departement_id=dept_filter)
    
    entreprise_filter = request.args.get('entreprise', '')
    if entreprise_filter:
        query = query.filter_by(entreprise_id=entreprise_filter)

    pdv_filter = request.args.get('pdv', '')
    if pdv_filter:
        query = query.filter_by(pdv_id=pdv_filter)
    
    actif_filter = request.args.get('actif', '')
    if actif_filter == '1':
        query = query.filter_by(actif=True)
    elif actif_filter == '0':
        query = query.filter_by(actif=False)
    
    # Sorting / Order By
    sort_by = request.args.get('sort_by', '').strip()
    order = request.args.get('order', 'asc').lower().strip()
    if order not in ['asc', 'desc']:
        order = 'asc'
    is_desc = (order == 'desc')

    order_clauses = []
    
    if sort_by:
        from sqlalchemy import func
        if sort_by == 'nom':
            order_clauses = [Utilisateur.nom.desc() if is_desc else Utilisateur.nom.asc(),
                             Utilisateur.prenom.desc() if is_desc else Utilisateur.prenom.asc()]
        elif sort_by == 'prenom':
            order_clauses = [Utilisateur.prenom.desc() if is_desc else Utilisateur.prenom.asc(),
                             Utilisateur.nom.desc() if is_desc else Utilisateur.nom.asc()]
        elif sort_by == 'email':
            order_clauses = [Utilisateur.email.desc() if is_desc else Utilisateur.email.asc()]
        elif sort_by == 'entreprise':
            query = query.outerjoin(Entreprise, Utilisateur.entreprise_id == Entreprise.id)
            order_clauses = [Entreprise.nom.desc() if is_desc else Entreprise.nom.asc(),
                             Utilisateur.prenom.asc()]
        elif sort_by == 'role':
            query = query.outerjoin(Role, Utilisateur.role_id == Role.id)
            order_clauses = [Role.nom.desc() if is_desc else Role.nom.asc(),
                             Utilisateur.prenom.asc()]
        elif sort_by in ['departement', 'pdv']:
            query = query.outerjoin(Departement, Utilisateur.departement_id == Departement.id)\
                         .outerjoin(PointDeVente, Utilisateur.pdv_id == PointDeVente.id)
            dept_or_pdv_name = func.coalesce(Departement.nom, PointDeVente.nom, '')
            order_clauses = [dept_or_pdv_name.desc() if is_desc else dept_or_pdv_name.asc(),
                             Utilisateur.prenom.asc()]
        elif sort_by == 'statut':
            order_clauses = [Utilisateur.actif.desc() if is_desc else Utilisateur.actif.asc(),
                             Utilisateur.prenom.asc()]
        elif sort_by == 'connexion':
            order_clauses = [Utilisateur.derniere_connexion.desc().nullslast() if is_desc else Utilisateur.derniere_connexion.asc().nullslast(),
                             Utilisateur.prenom.asc()]

    # If no explicit sorting selected but search is present, score relevance
    if not order_clauses:
        if search:
            from sqlalchemy import func, case
            exact = search
            prefix = f'{search}%'
            like_word = f'% {search}%'
            full_name = func.concat(Utilisateur.prenom, ' ', Utilisateur.nom)
            full_name_rev = func.concat(Utilisateur.nom, ' ', Utilisateur.prenom)

            # Relevance score: lower number = higher relevance
            relevance_score = case(
                # Tier 1: Exact matches on name or exact email username
                (Utilisateur.prenom.ilike(exact), 1),
                (Utilisateur.nom.ilike(exact), 1),
                (full_name.ilike(exact), 2),
                # Tier 2: Word starts with search term (e.g. "IT Administrateur" when searching "IT")
                (Utilisateur.prenom.ilike(prefix), 4),
                (Utilisateur.nom.ilike(prefix), 5),
                (full_name.ilike(prefix), 5),
                (full_name_rev.ilike(prefix), 5),
                (Utilisateur.poste.ilike(prefix), 6),
                (Utilisateur.poste.ilike(like_word), 7),
                (email_condition if '@' in search else email_local_part.ilike(prefix), 8),
                # Tier 3: Substring matches
                (Utilisateur.prenom.ilike(search_pattern), 9),
                (Utilisateur.nom.ilike(search_pattern), 10),
                (Utilisateur.poste.ilike(search_pattern), 11),
                else_=12
            )
            order_clauses = [relevance_score.asc(), Utilisateur.prenom.asc(), Utilisateur.nom.asc()]
        else:
            order_clauses = [Utilisateur.prenom.asc(), Utilisateur.nom.asc()]

    utilisateurs = query.order_by(*order_clauses).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    roles = Role.query.filter_by(actif=True).all()
    departements = Departement.query.filter_by(actif=True).all()
    entreprises = Entreprise.query.filter_by(actif=True).order_by(Entreprise.nom.asc()).all()
    
    return render_template('utilisateurs/liste.html',
                         utilisateurs=utilisateurs,
                         roles=roles,
                         departements=departements,
                         entreprises=entreprises,
                         search=search,
                         role_filter=role_filter,
                         dept_filter=dept_filter,
                         entreprise_filter=entreprise_filter,
                         pdv_filter=pdv_filter,
                         pdvs_filtre=PointDeVente.query.filter_by(actif=True).order_by(PointDeVente.nom).all(),
                         actif_filter=actif_filter,
                         sort_by=sort_by,
                         order=order,
                         total_actifs=total_actifs,
                         total_inactifs=total_inactifs)


@utilisateurs_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
@require_permission('utilisateurs.creer')
def nouveau():
    """Créer un nouvel utilisateur"""
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        telephone = request.form.get('telephone', '').strip()
        poste = request.form.get('poste', '').strip()
        role_id = request.form.get('role_id', '').strip() or None
        departement_id = request.form.get('departement_id', '').strip() or None

        # Validation
        from models import Entreprise, PointDeVente
        roles_all = Role.query.filter_by(actif=True).order_by(Role.niveau.desc()).all()
        departements_all = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()
        entreprises_all = Entreprise.query.filter_by(actif=True).order_by(Entreprise.nom).all()
        pdvs_all = PointDeVente.query.filter_by(actif=True).order_by(PointDeVente.nom).all()

        def _back():
            return render_template('utilisateurs/nouveau_utilisateur.html',
                                   roles=roles_all,
                                   departements=departements_all,
                                   entreprises=entreprises_all,
                                   pdvs=pdvs_all)

        if not all([nom, prenom, email, password]):
            flash('Tous les champs obligatoires doivent être remplis.', 'danger')
            return _back()
        if not EMAIL_RE.match(email) or len(email) > 120:
            flash("L'adresse email est invalide.", 'danger')
            return _back()
        if len(password) < PASSWORD_MIN_LENGTH:
            flash(f'Le mot de passe doit contenir au moins {PASSWORD_MIN_LENGTH} caractères.', 'danger')
            return _back()
        role_err = _role_error(role_id)
        if role_err:
            flash(role_err, 'danger')
            return _back()

        # Vérifier l'email unique
        if Utilisateur.query.filter(db.func.lower(Utilisateur.email) == email).first():
            flash('Un utilisateur avec cet email existe déjà.', 'danger')
            return _back()
        
        # Créer l'utilisateur
        entreprise_id = request.form.get('entreprise_id', '').strip() or None
        pdv_id = request.form.get('pdv_id', '').strip() or None
        utilisateur = Utilisateur(
            nom=nom,
            prenom=prenom,
            email=email,
            telephone=telephone if telephone else None,
            poste=poste if poste else None,
            matricule=None,
            anydesk_id=request.form.get('anydesk_id', '').strip() or None,
            anydesk_password=request.form.get('anydesk_password', '').strip() or None,
            teamviewer_id=request.form.get('teamviewer_id', '').strip() or None,
            teamviewer_password=request.form.get('teamviewer_password', '').strip() or None,
            poste_machine=request.form.get('poste_machine', '').strip() or None,
            role_id=role_id,
            departement_id=departement_id,
            entreprise_id=entreprise_id,
            pdv_id=pdv_id,
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
            logger.error(f'Erreur lors de la création utilisateur: {e}', exc_info=True)
            flash('Erreur lors de la création de l\'utilisateur.', 'danger')

    from models import Entreprise, PointDeVente
    roles = Role.query.filter_by(actif=True).order_by(Role.niveau.desc()).all()
    departements = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()
    entreprises = Entreprise.query.filter_by(actif=True).order_by(Entreprise.nom).all()
    pdvs = PointDeVente.query.filter_by(actif=True).order_by(PointDeVente.nom).all()
    return render_template('utilisateurs/nouveau_utilisateur.html',
                         roles=roles,
                         departements=departements,
                         entreprises=entreprises,
                         pdvs=pdvs)


@utilisateurs_bp.route('/<string:id>')
@login_required
def detail(id):
    """Afficher les détails d'un utilisateur"""
    utilisateur = Utilisateur.query.get_or_404(id)
    
    # Pas de restriction stricte pour visualiser un profil
    # Tous les utilisateurs peuvent voir le profil de base des autres
    
    # Statistiques
    stats = {
        'tickets_crees': len(utilisateur.tickets_crees),
        'tickets_assignes': len([t for t in utilisateur.tickets_assignes if t.statut not in ['resolu', 'ferme']]),
        'total_assignes': len(utilisateur.tickets_assignes),
        'tickets_resolus': len([t for t in utilisateur.tickets_assignes if t.statut == 'resolu']),
        'commentaires': len(utilisateur.commentaires),
    }
    
    # Tickets récents (dédupliqués et triés)
    all_tickets = list({t.id: t for t in (utilisateur.tickets_crees + utilisateur.tickets_assignes)}.values())
    tickets_recents = sorted(
        all_tickets,
        key=lambda x: x.date_creation if x.date_creation else datetime.min,
        reverse=True
    )[:10]
    
    # Les mots de passe AnyDesk / TeamViewer ne sont visibles que par l'intéressé et les administrateurs d'accès distant
    can_see_remote_secrets = (current_user.id == utilisateur.id
                              or current_user.has_permission('admin_acces.voir')
                              or role_level(current_user) >= 90)

    return render_template('utilisateurs/detail.html',
                         utilisateur=utilisateur,
                         stats=stats,
                         tickets_recents=tickets_recents,
                         can_see_remote_secrets=can_see_remote_secrets)


@utilisateurs_bp.route('/<string:id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier(id):
    """Modifier un utilisateur"""
    utilisateur = Utilisateur.query.get_or_404(id)
    
    # Vérifier les permissions
    peut_modifier = current_user.has_permission('utilisateurs.modifier')
    if not peut_modifier and current_user.id != utilisateur.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('tickets.tableau_bord'))
    # Pas de modification d'un compte de niveau supérieur au sien (sauf soi-même)
    if current_user.id != utilisateur.id and role_level(utilisateur) > role_level(current_user):
        flash("Vous ne pouvez pas modifier un compte de niveau supérieur au vôtre.", 'danger')
        return redirect(url_for('utilisateurs.detail', id=id))

    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()
        email = request.form.get('email', '').strip().lower()
        telephone = request.form.get('telephone', '').strip()
        poste = request.form.get('poste', '').strip()

        # Les détenteurs de utilisateurs.modifier peuvent modifier rôle / affectations / statut
        if peut_modifier:
            role_id = request.form.get('role_id', '').strip() or None
            departement_id = request.form.get('departement_id', '').strip() or None
            pdv_id = request.form.get('pdv_id', '').strip() or None
            entreprise_id = request.form.get('entreprise_id', '').strip() or None
            actif = request.form.get('actif') == '1'
        else:
            role_id = utilisateur.role_id
            departement_id = utilisateur.departement_id
            pdv_id = utilisateur.pdv_id
            entreprise_id = utilisateur.entreprise_id
            actif = utilisateur.actif

        # Mot de passe optionnel (supporte 'nouveau_password' et 'password')
        password = request.form.get('nouveau_password', '') or request.form.get('password', '')
        
        # Validation
        from models import Entreprise, PointDeVente
        roles_all = Role.query.filter_by(actif=True).order_by(Role.niveau.desc()).all()
        departements_all = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()
        entreprises_all = Entreprise.query.filter_by(actif=True).order_by(Entreprise.nom).all()
        pdvs_all = PointDeVente.query.filter_by(actif=True).order_by(PointDeVente.nom).all()

        def _back():
            return render_template('utilisateurs/modifier_utilisateur.html',
                                   utilisateur=utilisateur,
                                   roles=roles_all,
                                   departements=departements_all,
                                   entreprises=entreprises_all,
                                   pdvs=pdvs_all)

        if not all([nom, prenom, email]):
            flash('Tous les champs obligatoires doivent être remplis.', 'danger')
            return _back()
        if not EMAIL_RE.match(email) or len(email) > 120:
            flash("L'adresse email est invalide.", 'danger')
            return _back()
        if password and len(password) < PASSWORD_MIN_LENGTH:
            flash(f'Le mot de passe doit contenir au moins {PASSWORD_MIN_LENGTH} caractères.', 'danger')
            return _back()
        if peut_modifier and role_id != utilisateur.role_id:
            role_err = _role_error(role_id)
            if role_err:
                flash(role_err, 'danger')
                return _back()
        if utilisateur.id == current_user.id and not actif:
            flash('Vous ne pouvez pas vous désactiver vous-même.', 'danger')
            return _back()

        # Vérifier l'email unique (sauf pour l'utilisateur actuel)
        existing = Utilisateur.query.filter(db.func.lower(Utilisateur.email) == email).first()
        if existing and existing.id != utilisateur.id:
            flash('Un utilisateur avec cet email existe déjà.', 'danger')
            return _back()
        
        # Mettre à jour
        utilisateur.nom = nom
        utilisateur.prenom = prenom
        utilisateur.email = email
        utilisateur.telephone = telephone if telephone else None
        utilisateur.poste = poste if poste else None
        utilisateur.anydesk_id = request.form.get('anydesk_id', '').strip() or None
        utilisateur.anydesk_password = request.form.get('anydesk_password', '').strip() or None
        utilisateur.teamviewer_id = request.form.get('teamviewer_id', '').strip() or None
        utilisateur.teamviewer_password = request.form.get('teamviewer_password', '').strip() or None
        utilisateur.poste_machine = request.form.get('poste_machine', '').strip() or None
        utilisateur.role_id = role_id
        utilisateur.departement_id = departement_id
        utilisateur.pdv_id = pdv_id
        utilisateur.entreprise_id = entreprise_id
        if utilisateur.actif and not actif:
            utilisateur.revoke_sessions()
        utilisateur.actif = actif

        if password:
            utilisateur.set_password(password)
            utilisateur.revoke_sessions()

        try:
            db.session.commit()
            if password and utilisateur.id == current_user.id:
                # L'utilisateur vient de changer son propre mot de passe : rester connecté
                from flask_login import login_user
                login_user(utilisateur, remember=False)
            flash(f'Utilisateur "{utilisateur.nom_complet}" modifié avec succès!', 'success')
            return redirect(url_for('utilisateurs.detail', id=utilisateur.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la modification utilisateur: {e}', exc_info=True)
            flash('Erreur lors de la modification.', 'danger')
    
    from models import Entreprise, PointDeVente
    roles = Role.query.filter_by(actif=True).order_by(Role.niveau.desc()).all()
    departements = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()
    entreprises = Entreprise.query.filter_by(actif=True).order_by(Entreprise.nom).all()
    pdvs = PointDeVente.query.filter_by(actif=True).order_by(PointDeVente.nom).all()
    return render_template('utilisateurs/modifier_utilisateur.html',
                         utilisateur=utilisateur,
                         roles=roles,
                         departements=departements,
                         entreprises=entreprises,
                         pdvs=pdvs)


@utilisateurs_bp.route('/<string:id>/toggle-actif', methods=['POST'])
@login_required
@require_permission('utilisateurs.activer')
def toggle_actif(id):
    """Activer/Désactiver un utilisateur"""
    utilisateur = Utilisateur.query.get_or_404(id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Ne pas se désactiver soi-même
    if utilisateur.id == current_user.id:
        msg = 'Vous ne pouvez pas vous désactiver vous-même.'
        if is_ajax:
            return jsonify({'error': msg}), 403
        flash(msg, 'danger')
        return redirect(url_for('utilisateurs.detail', id=id))

    # Ni un compte de niveau supérieur au sien
    if role_level(utilisateur) > role_level(current_user):
        msg = "Vous ne pouvez pas modifier un compte de niveau supérieur au vôtre."
        if is_ajax:
            return jsonify({'error': msg}), 403
        flash(msg, 'danger')
        return redirect(url_for('utilisateurs.detail', id=id))

    utilisateur.actif = not utilisateur.actif
    if not utilisateur.actif:
        utilisateur.revoke_sessions()
    else:
        utilisateur.verrouille = False
        utilisateur.date_verrouillage = None
        utilisateur.tentatives_connexion = 0

    try:
        db.session.commit()
        status = 'réactivé' if utilisateur.actif else 'désactivé'
        msg = f'Utilisateur « {utilisateur.nom_complet} » {status} avec succès.'
        if is_ajax:
            return jsonify({'actif': utilisateur.actif, 'message': msg})
        flash(msg, 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur toggle_actif: {e}', exc_info=True)
        if is_ajax:
            return jsonify({'error': 'Erreur serveur'}), 500
        flash('Erreur lors de la mise à jour.', 'danger')

    # Hors AJAX : revenir à la page d'origine si elle appartient à l'application
    from utils.security import is_safe_redirect
    from urllib.parse import urlparse
    ref = request.referrer
    if ref and urlparse(ref).netloc == request.host and is_safe_redirect(urlparse(ref).path or '/'):
        return redirect(ref)
    return redirect(url_for('utilisateurs.detail', id=id))



@utilisateurs_bp.route('/<string:id>/supprimer', methods=['POST'])
@login_required
@require_permission('utilisateurs.supprimer')
def supprimer(id):
    """Supprimer un utilisateur"""
    utilisateur = Utilisateur.query.get_or_404(id)
    
    # Ne pas se supprimer soi-même
    if utilisateur.id == current_user.id:
        flash('Vous ne pouvez pas vous supprimer vous-même.', 'danger')
        return redirect(url_for('utilisateurs.detail', id=id))
    
    if role_level(utilisateur) > role_level(current_user):
        flash("Vous ne pouvez pas supprimer un compte de niveau supérieur au vôtre.", 'danger')
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
        logger.error(f'Erreur suppression utilisateur: {e}', exc_info=True)
        flash('Erreur lors de la suppression.', 'danger')
        return redirect(url_for('utilisateurs.detail', id=id))
