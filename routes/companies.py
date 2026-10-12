from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Entreprise, Utilisateur, Ticket
from datetime import datetime

companies_bp = Blueprint('companies', __name__)

@companies_bp.route('/')
@login_required
def liste():
    """List all companies and external entities involved in the platform"""
    if not current_user.has_permission('pdv.voir') and not current_user.has_permission('utilisateurs.voir'):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('tickets.tableau_bord'))

    type_filter = request.args.get('type', 'all')
    search = request.args.get('search', '').strip()

    query = Entreprise.query
    if type_filter and type_filter != 'all':
        query = query.filter_by(type_entreprise=type_filter)
    if search:
        query = query.filter(
            (Entreprise.nom.ilike(f'%{search}%')) |
            (Entreprise.code.ilike(f'%{search}%')) |
            (Entreprise.description.ilike(f'%{search}%'))
        )

    entreprises = query.order_by(Entreprise.type_entreprise == 'principale', Entreprise.nom).all()

    # Total counts
    total_companies = Entreprise.query.count()
    main_company = Entreprise.query.filter_by(type_entreprise='principale').first()
    external_companies = Entreprise.query.filter(Entreprise.type_entreprise != 'principale').count()
    external_users = Utilisateur.query.join(Entreprise).filter(Entreprise.type_entreprise != 'principale').count()

    return render_template(
        'companies/liste.html',
        entreprises=entreprises,
        total_companies=total_companies,
        main_company=main_company,
        external_companies=external_companies,
        external_users=external_users,
        current_type=type_filter,
        search_query=search
    )

@companies_bp.route('/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle():
    if not current_user.has_permission('admin_dashboard.voir') and not current_user.role.niveau >= 80:
        flash("Accès réservé aux administrateurs.", "danger")
        return redirect(url_for('companies.liste'))

    if request.method == 'POST':
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
            flash("Le nom de l'entreprise est obligatoire.", "danger")
            return redirect(url_for('companies.nouvelle'))

        if Entreprise.query.filter_by(nom=nom).first():
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
        flash(f"Entreprise '{nom}' ajoutée avec succès.", "success")
        return redirect(url_for('companies.detail', id=ent.id))

    return render_template('companies/formulaire.html', entreprise=None)

@companies_bp.route('/<string:id>')
@login_required
def detail(id):
    ent = Entreprise.query.get_or_404(id)
    employes = sorted(ent.employes.all(), key=lambda u: (u.nom_complet or '').strip().upper())
    all_users = sorted(Utilisateur.query.filter_by(actif=True).all(), key=lambda u: (u.nom_complet or '').strip().upper())
    return render_template('companies/detail.html', entreprise=ent, employes=employes, all_users=all_users)

@companies_bp.route('/<string:id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier(id):
    if not current_user.has_permission('admin_dashboard.voir') and not current_user.role.niveau >= 80:
        flash("Accès réservé aux administrateurs.", "danger")
        return redirect(url_for('companies.detail', id=id))

    ent = Entreprise.query.get_or_404(id)
    if request.method == 'POST':
        ent.nom = request.form.get('nom', '').strip()
        ent.code = request.form.get('code', '').strip().upper() or None
        ent.type_entreprise = request.form.get('type_entreprise', ent.type_entreprise)
        ent.email = request.form.get('email', '').strip() or None
        ent.telephone = request.form.get('telephone', '').strip() or None
        ent.adresse = request.form.get('adresse', '').strip() or None
        ent.site_web = request.form.get('site_web', '').strip() or None
        ent.couleur = request.form.get('couleur', ent.couleur)
        ent.description = request.form.get('description', '').strip() or None

        db.session.commit()
        flash(f"Informations de '{ent.nom}' mises à jour.", "success")
        return redirect(url_for('companies.detail', id=ent.id))

    return render_template('companies/formulaire.html', entreprise=ent)

@companies_bp.route('/<string:id>/assigner-employe', methods=['POST'])
@login_required
def assigner_employe(id):
    if not current_user.has_permission('admin_dashboard.voir') and not current_user.role.niveau >= 80:
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
    if not current_user.has_permission('admin_dashboard.voir') and not current_user.role.niveau >= 80:
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
