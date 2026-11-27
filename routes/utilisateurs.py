from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from services.reporting import count_resolved_by
from models import db, Utilisateur, Role, Departement, Entreprise, PointDeVente
from functools import wraps
import logging
import re
from datetime import datetime

from utils.permissions import (assignable_roles, can_assign_role, can_act_on_user, permission_required, deny_access, home_endpoint,
                               user_visibility_filter, can_view_user, is_super_admin)

utilisateurs_bp = Blueprint('utilisateurs', __name__)
logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
PASSWORD_MIN_LENGTH = 8


def require_permission(permission_code):
    return permission_required(permission_code)


def _role_error(role_id):
    """Erreur si le rôle n'existe pas ou si l'on n'a pas le droit de l'attribuer (Super Administrateur réservé)."""
    if not role_id:
        return None
    role = db.session.get(Role, role_id)
    if role is None:
        return 'Rôle introuvable.'
    if not can_assign_role(current_user, role):
        return "Seul un Super Administrateur peut attribuer le rôle Super Administrateur."
    return None

@utilisateurs_bp.route('/')
@login_required
@permission_required('utilisateurs.voir')
def liste():
    """Liste tous les utilisateurs"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    if current_user.has_permission('utilisateurs.voir_tous'):
        base_query = Utilisateur.query
    else:
        # Sans voir_tous : son département + les personnes de ses points de vente
        base_query = Utilisateur.query.filter(user_visibility_filter(current_user))
    
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
    
    # Le filtre par rôle est réservé aux Super Administrateurs (ignoré pour les autres, même dans l'URL)
    peut_filtrer_role = is_super_admin(current_user)
    role_filter = request.args.get('role', '') if peut_filtrer_role else ''
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
        query = query.filter(db.or_(Utilisateur.pdv_id == pdv_filter,
                                    Utilisateur.pdv_extra_ids.contains(pdv_filter, autoescape=True)))
    
    # Personnes rattachées nulle part : ni département, ni point de vente (principal ou supplémentaire)
    sans_affectation = db.and_(Utilisateur.departement_id.is_(None), Utilisateur.pdv_id.is_(None),
                               db.func.coalesce(Utilisateur.pdv_extra_ids, '') == '')
    total_sans_affectation = base_query.filter(sans_affectation).count()
    affectation_filter = 'aucune' if request.args.get('affectation') == 'aucune' else ''
    if affectation_filter:
        query = query.filter(sans_affectation)

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
                         peut_filtrer_role=peut_filtrer_role,
                         dept_filter=dept_filter,
                         entreprise_filter=entreprise_filter,
                         pdv_filter=pdv_filter,
                         pdvs_filtre=PointDeVente.query.filter_by(actif=True).order_by(PointDeVente.nom).all(),
                         actif_filter=actif_filter,
                         affectation_filter=affectation_filter,
                         total_sans_affectation=total_sans_affectation,
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
        roles_all = assignable_roles(current_user, Role.query.filter_by(actif=True).order_by(Role.systeme.desc(), Role.nom).all())
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
        pdv_ids = request.form.getlist('pdv_ids')
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
            actif=True
        )
        utilisateur.set_pdvs(pdv_ids)
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
    roles = assignable_roles(current_user, Role.query.filter_by(actif=True).order_by(Role.systeme.desc(), Role.nom).all())
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
    
    # Son propre profil : toujours. Celui d'un autre : permission utilisateurs.voir, et — sans utilisateurs.voir_tous —
    # uniquement les personnes de son département ou de ses points de vente (même règle que la liste).
    if utilisateur.id != current_user.id:
        if not current_user.has_permission('utilisateurs.voir'):
            return deny_access("Vous n'avez pas la permission de consulter les profils.")
        if not can_view_user(current_user, utilisateur):
            return deny_access("Vous ne pouvez consulter que les profils de votre département ou de vos points de vente.")
    
    # Statistiques
    stats = {
        'tickets_crees': len(utilisateur.tickets_crees),
        'tickets_assignes': len([t for t in utilisateur.tickets_assignes if t.statut not in ['resolu', 'ferme']]),
        'total_assignes': len(utilisateur.tickets_assignes),
        'tickets_resolus': count_resolved_by(utilisateur.id),
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
                              )

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
        return redirect(url_for(home_endpoint(current_user)))
    # Un compte Super Administrateur n'est modifiable que par un Super Administrateur (ou par lui-même)
    if not can_act_on_user(current_user, utilisateur):
        flash("Seul un Super Administrateur peut modifier un compte Super Administrateur.", 'danger')
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
            pdv_ids = request.form.getlist('pdv_ids')
            entreprise_id = request.form.get('entreprise_id', '').strip() or None
            actif = request.form.get('actif') == '1'
        else:
            role_id = utilisateur.role_id
            departement_id = utilisateur.departement_id
            pdv_ids = [p.id for p in utilisateur.tous_pdvs]
            entreprise_id = utilisateur.entreprise_id
            actif = utilisateur.actif

        # Mot de passe optionnel (supporte 'nouveau_password' et 'password')
        password = request.form.get('nouveau_password', '') or request.form.get('password', '')
        
        # Validation
        from models import Entreprise, PointDeVente
        roles_all = assignable_roles(current_user, Role.query.filter_by(actif=True).order_by(Role.systeme.desc(), Role.nom).all())
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
        utilisateur.set_pdvs(pdv_ids)
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
    roles = assignable_roles(current_user, Role.query.filter_by(actif=True).order_by(Role.systeme.desc(), Role.nom).all())
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

    # Un compte Super Administrateur n'est modifiable que par un Super Administrateur
    if not can_act_on_user(current_user, utilisateur):
        msg = "Seul un Super Administrateur peut modifier un compte Super Administrateur."
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



# Libellés des données qui bloquent la suppression d'un compte (table -> texte)
LIENS_BLOQUANTS = {
    'tickets': 'ticket(s)', 'commentaires': 'commentaire(s)', 'historique_tickets': "ligne(s) d'historique",
    'notifications': 'notification(s)', 'pieces_jointes': 'pièce(s) jointe(s)', 'taches': 'tâche(s)',
    'departements': 'département(s) dont il est responsable', 'modeles_reponses': 'modèle(s) de réponse',
    'base_connaissance': 'article(s) de la base de connaissance', 'articles_connaissance': 'article(s) de connaissance',
    'messages': 'message(s) privé(s)', 'suggestions': 'idée(s)', 'plan_action_tasks': "tâche(s) du plan d'action",
    'points_de_vente': 'point(s) de vente',
}
# Simples liaisons / compteurs de lecture : retirées avec le compte, elles ne bloquent pas
LIENS_IGNORES = {'ticket_collaborateurs', 'articles_connaissance_vues'}


def donnees_liees(utilisateur):
    """Données qui empêchent de supprimer le compte : [(texte, nombre)].
    Lu dans le catalogue de la VRAIE base (clés étrangères vers `utilisateurs` sans « mise à NULL »), donc fiable même si
    le modèle Python et le schéma réel divergent. En cas d'échec de la vérification, on refuse par prudence."""
    try:
        fks = db.session.execute(db.text(
            "SELECT c.conrelid::regclass::text AS tbl, a.attname AS col "
            "FROM pg_constraint c JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey) "
            "WHERE c.contype = 'f' AND c.confrelid = 'utilisateurs'::regclass AND c.confdeltype <> 'n'")).all()
        trouve = []
        for tbl, col in fks:
            nom = tbl.strip('"')
            if nom in LIENS_IGNORES:
                continue
            n = db.session.execute(db.text(f'SELECT count(*) FROM "{nom}" WHERE "{col}" = :uid'),
                                   {'uid': utilisateur.id}).scalar()
            if n:
                trouve.append((LIENS_BLOQUANTS.get(nom, nom), n))
        return trouve
    except Exception as e:
        db.session.rollback()
        logger.error(f'Vérification des données liées impossible: {e}', exc_info=True)
        return [('données (vérification impossible)', 1)]


@utilisateurs_bp.route('/<string:id>/supprimer', methods=['POST'])
@login_required
@require_permission('utilisateurs.supprimer')
def supprimer(id):
    """Supprimer un utilisateur — refusé (avec le détail) s'il a des données liées : on le désactive alors."""
    utilisateur = Utilisateur.query.get_or_404(id)

    if utilisateur.id == current_user.id:
        flash('Vous ne pouvez pas vous supprimer vous-même.', 'danger')
        return redirect(url_for('utilisateurs.detail', id=id))

    if not can_act_on_user(current_user, utilisateur):
        flash("Seul un Super Administrateur peut supprimer un compte Super Administrateur.", 'danger')
        return redirect(url_for('utilisateurs.detail', id=id))

    liens = donnees_liees(utilisateur)
    if liens:
        detail = ', '.join(f'{n} {txt}' for txt, n in liens)
        flash(f"Suppression impossible : ce compte est lié à {detail}. Désactivez-le plutôt (l'historique est conservé).", 'danger')
        return redirect(url_for('utilisateurs.detail', id=id))

    nom = utilisateur.nom_complet
    try:
        db.session.delete(utilisateur)
        db.session.commit()
        logger.info(f'Utilisateur supprimé par {current_user.email}')
        flash(f'Utilisateur « {nom} » supprimé avec succès.', 'success')
        return redirect(url_for('utilisateurs.liste'))
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur suppression utilisateur: {e}', exc_info=True)
        flash('Erreur lors de la suppression.', 'danger')
        return redirect(url_for('utilisateurs.detail', id=id))
