from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Entreprise, Utilisateur, Ticket
from datetime import datetime

companies_bp = Blueprint('companies', __name__)

def can_manage_companies():
    """Verify if current user has permission to manage companies"""
    if not current_user.is_authenticated:
        return False
    if current_user.has_permission('entreprises.modifier') or current_user.has_permission('entreprises.creer') or current_user.has_permission('admin_dashboard.voir'):
        return True
    if current_user.role and current_user.role.niveau >= 60:
        return True
    return False


@companies_bp.route('/')
@login_required
def liste():
    """List all companies and external entities with filtering, archiving and search"""
    if not current_user.has_permission('entreprises.voir') and not current_user.has_permission('pdv.voir') and not current_user.has_permission('utilisateurs.voir'):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('tickets.tableau_bord'))

    type_filter = request.args.get('type', 'all')
    status_filter = request.args.get('statut', 'all')  # 'all', 'actif', 'archive'
    search = request.args.get('search', '').strip()

    query = Entreprise.query

    # Status filter
    if status_filter == 'actif':
        query = query.filter_by(actif=True)
    elif status_filter == 'archive':
        query = query.filter_by(actif=False)

    # Type filter
    if type_filter and type_filter != 'all':
        query = query.filter_by(type_entreprise=type_filter)

    # Search filter
    if search:
        query = query.filter(
            (Entreprise.nom.ilike(f'%{search}%')) |
            (Entreprise.code.ilike(f'%{search}%')) |
            (Entreprise.description.ilike(f'%{search}%')) |
            (Entreprise.email.ilike(f'%{search}%'))
        )

    entreprises = query.order_by(Entreprise.type_entreprise == 'principale', Entreprise.actif.desc(), Entreprise.nom).all()

    # Total metrics
    total_companies = Entreprise.query.count()
    active_companies = Entreprise.query.filter_by(actif=True).count()
    archived_companies = Entreprise.query.filter_by(actif=False).count()
    main_company = Entreprise.query.filter_by(type_entreprise='principale').first()
    external_companies = Entreprise.query.filter(Entreprise.type_entreprise != 'principale', Entreprise.actif == True).count()
    external_users = Utilisateur.query.join(Entreprise).filter(Entreprise.type_entreprise != 'principale').count()

    can_manage = can_manage_companies()

    return render_template(
        'companies/liste.html',
        entreprises=entreprises,
        total_companies=total_companies,
        active_companies=active_companies,
        archived_companies=archived_companies,
        main_company=main_company,
        external_companies=external_companies,
        external_users=external_users,
        current_type=type_filter,
        current_statut=status_filter,
        search_query=search,
        can_manage=can_manage
    )


@companies_bp.route('/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle():
    """Create a new company"""
    if not (current_user.has_permission('entreprises.creer') or can_manage_companies()):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Accès réservé aux administrateurs.'}), 403
        flash("Accès réservé aux administrateurs.", "danger")
        return redirect(url_for('companies.liste'))

    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        
        nom = request.form.get('nom', '').strip()
        code = request.form.get('code', '').strip().upper()
        type_ent = request.form.get('type_entreprise', 'externe')
        email = request.form.get('email', '').strip()
        telephone = request.form.get('telephone', '').strip()
        adresse = request.form.get('adresse', '').strip()
        site_web = request.form.get('site_web', '').strip()
        couleur = request.form.get('couleur', '#6366F1')
        description = request.form.get('description', '').strip()

        if not nom:
            if is_ajax:
                return jsonify({'success': False, 'message': "Le nom de l'entreprise est obligatoire."}), 400
            flash("Le nom de l'entreprise est obligatoire.", "danger")
            return redirect(url_for('companies.nouvelle'))

        if Entreprise.query.filter_by(nom=nom).first():
            if is_ajax:
                return jsonify({'success': False, 'message': "Une entreprise avec ce nom existe déjà."}), 400
            flash("Une entreprise avec ce nom existe déjà.", "danger")
            return redirect(url_for('companies.nouvelle'))

        ent = Entreprise(
            nom=nom,
            code=code or None,
            type_entreprise=type_ent,
            email=email or None,
            telephone=telephone or None,
            adresse=adresse or None,
            site_web=site_web or None,
            couleur=couleur,
            description=description or None,
            actif=True
        )
        db.session.add(ent)
        db.session.commit()

        msg = f"Entreprise '{nom}' ajoutée avec succès."
        if is_ajax:
            return jsonify({'success': True, 'id': ent.id, 'message': msg})
        flash(msg, "success")
        return redirect(url_for('companies.detail', id=ent.id))

    return render_template('companies/formulaire.html', entreprise=None)


@companies_bp.route('/<string:id>')
@login_required
def detail(id):
    """View company details and its associated staff"""
    ent = Entreprise.query.get_or_404(id)
    employes = sorted(ent.employes.all(), key=lambda u: (u.nom_complet or '').strip().upper())
    all_users = sorted(Utilisateur.query.filter_by(actif=True).all(), key=lambda u: (u.nom_complet or '').strip().upper())
    can_manage = can_manage_companies()
    return render_template('companies/detail.html', entreprise=ent, employes=employes, all_users=all_users, can_manage=can_manage)


@companies_bp.route('/<string:id>/json')
@login_required
def get_json(id):
    """Get company details as JSON for interactive modals"""
    ent = Entreprise.query.get_or_404(id)
    return jsonify({
        'id': ent.id,
        'nom': ent.nom,
        'code': ent.code or '',
        'type_entreprise': ent.type_entreprise,
        'email': ent.email or '',
        'telephone': ent.telephone or '',
        'adresse': ent.adresse or '',
        'site_web': ent.site_web or '',
        'couleur': ent.couleur or '#6366F1',
        'description': ent.description or '',
        'actif': ent.actif,
        'nombre_employes': ent.nombre_employes
    })


@companies_bp.route('/<string:id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier(id):
    """Edit company attributes"""
    if not (current_user.has_permission('entreprises.modifier') or can_manage_companies()):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Accès réservé aux administrateurs.'}), 403
        flash("Accès réservé aux administrateurs.", "danger")
        return redirect(url_for('companies.detail', id=id))

    ent = Entreprise.query.get_or_404(id)
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json

        nom = request.form.get('nom', '').strip()
        if not nom:
            if is_ajax:
                return jsonify({'success': False, 'message': "Le nom est obligatoire."}), 400
            flash("Le nom est obligatoire.", "danger")
            return redirect(url_for('companies.modifier', id=id))

        # Check unique name if changed
        existing = Entreprise.query.filter(Entreprise.nom == nom, Entreprise.id != ent.id).first()
        if existing:
            if is_ajax:
                return jsonify({'success': False, 'message': "Une autre entreprise porte déjà ce nom."}), 400
            flash("Une autre entreprise porte déjà ce nom.", "danger")
            return redirect(url_for('companies.modifier', id=id))

        ent.nom = nom
        ent.code = request.form.get('code', '').strip().upper() or None
        # Main company type cannot be demoted
        if ent.type_entreprise != 'principale':
            ent.type_entreprise = request.form.get('type_entreprise', ent.type_entreprise)
        ent.email = request.form.get('email', '').strip() or None
        ent.telephone = request.form.get('telephone', '').strip() or None
        ent.adresse = request.form.get('adresse', '').strip() or None
        ent.site_web = request.form.get('site_web', '').strip() or None
        ent.couleur = request.form.get('couleur', ent.couleur)
        ent.description = request.form.get('description', '').strip() or None

        db.session.commit()
        msg = f"Informations de '{ent.nom}' mises à jour."
        if is_ajax:
            return jsonify({'success': True, 'message': msg})
        flash(msg, "success")
        return redirect(url_for('companies.detail', id=ent.id))

    return render_template('companies/formulaire.html', entreprise=ent)


@companies_bp.route('/<string:id>/toggle-archive', methods=['POST'])
@login_required
def toggle_archive(id):
    """Archive or unarchive a company"""
    if not (current_user.has_permission('entreprises.supprimer') or current_user.has_permission('entreprises.modifier') or can_manage_companies()):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Accès réservé aux administrateurs.'}), 403
        flash("Accès réservé aux administrateurs.", "danger")
        return redirect(url_for('companies.liste'))

    ent = Entreprise.query.get_or_404(id)
    if ent.type_entreprise == 'principale':
        msg = "La société principale ne peut pas être archivée."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, "warning")
        return redirect(url_for('companies.liste'))

    ent.actif = not ent.actif
    db.session.commit()

    action_str = "réactivée" if ent.actif else "archivée"
    msg = f"Entreprise '{ent.nom}' {action_str} avec succès."
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'success': True, 'actif': ent.actif, 'message': msg})
    flash(msg, "success")
    return redirect(request.referrer or url_for('companies.liste'))


@companies_bp.route('/<string:id>/supprimer', methods=['POST'])
@login_required
def supprimer(id):
    """Delete a company and detach associated users"""
    if not (current_user.has_permission('entreprises.supprimer') or can_manage_companies()):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Accès réservé aux administrateurs.'}), 403
        flash("Accès réservé aux administrateurs.", "danger")
        return redirect(url_for('companies.liste'))

    ent = Entreprise.query.get_or_404(id)
    if ent.type_entreprise == 'principale':
        msg = "La société principale ne peut pas être supprimée."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, "danger")
        return redirect(url_for('companies.liste'))

    # Detach any employees attached to this enterprise
    for user in ent.employes:
        user.entreprise_id = None

    nom = ent.nom
    db.session.delete(ent)
    db.session.commit()

    msg = f"Entreprise '{nom}' supprimée définitivement."
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'success': True, 'message': msg})
    flash(msg, "success")
    return redirect(url_for('companies.liste'))


@companies_bp.route('/<string:id>/assigner-employe', methods=['POST'])
@login_required
def assigner_employe(id):
    """Attach an employee to this company"""
    if not can_manage_companies():
        flash("Accès réservé aux administrateurs.", "danger")
        return redirect(url_for('companies.detail', id=id))

    ent = Entreprise.query.get_or_404(id)
    user_id = request.form.get('utilisateur_id')
    user = Utilisateur.query.get_or_404(user_id)
    user.entreprise_id = ent.id
    db.session.commit()
    flash(f"{user.nom_complet} est maintenant rattaché à {ent.nom}.", "success")
    return redirect(url_for('companies.detail', id=id))


@companies_bp.route('/retirer-employe/<string:user_id>', methods=['POST'])
@login_required
def retirer_employe(user_id):
    """Detach an employee from their company"""
    if not can_manage_companies():
        flash("Accès réservé aux administrateurs.", "danger")
        return redirect(url_for('companies.liste'))

    user = Utilisateur.query.get_or_404(user_id)
    old_ent_id = user.entreprise_id
    user.entreprise_id = None
    db.session.commit()
    flash(f"{user.nom_complet} n'est plus rattaché à cette entreprise.", "info")
    if old_ent_id:
        return redirect(url_for('companies.detail', id=old_ent_id))
    return redirect(url_for('companies.liste'))
