import logging
import re
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from models import db, PointDeVente, Equipement, Utilisateur, Ticket
from services import referentiels
from utils.permissions import role_level
from utils.security import safe_color, is_hex_color

pdv_bp = Blueprint('pdv', __name__)
logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
EQUIPEMENT_STATUTS = ['actif', 'en_panne', 'maintenance', 'hors_service']


def _can_edit():
    return current_user.has_permission('pdv.modifier')


def _categories(pdvs=None):
    """Catégories issues de la base (cache) + toute catégorie encore portée par un PDV mais absente du référentiel."""
    cats = referentiels.get_categories()
    known = {c['nom'].lower() for c in cats}
    for p in (pdvs if pdvs is not None else PointDeVente.query.all()):
        if p.categorie and p.categorie.lower() not in known:
            cats.append({'id': None, 'nom': p.categorie, 'description': 'Catégorie existante', 'icone': 'circle'})
            known.add(p.categorie.lower())
    return cats


def _default_category():
    cats = referentiels.get_categories()
    return cats[0]['nom'] if cats else 'Urbain'


def _read_pdv_form(pdv=None):
    """Valide le formulaire PDV. Retourne (valeurs, erreurs)."""
    errors = []
    nom = request.form.get('nom', '').strip()
    email = request.form.get('email', '').strip()
    if not nom:
        errors.append('Le nom du point de vente est obligatoire.')
    elif len(nom) > 100:
        errors.append('Le nom du point de vente est trop long (100 caractères maximum).')
    else:
        existing = PointDeVente.query.filter_by(nom=nom).first()
        if existing and (pdv is None or existing.id != pdv.id):
            errors.append('Un point de vente portant ce nom existe déjà.')
    if email and not EMAIL_RE.match(email):
        errors.append("L'adresse email est invalide.")

    # Catégorie : préréglage ou personnalisée
    cat_select = request.form.get('categorie')
    cat_custom = request.form.get('categorie_custom', '').strip()
    categorie = cat_custom if (cat_select == 'custom' and cat_custom) else (cat_select or _default_category())
    if len(categorie) > 50:
        errors.append('La catégorie est trop longue (50 caractères maximum).')

    responsable_id = request.form.get('responsable_id') or None
    if responsable_id and not db.session.get(Utilisateur, responsable_id):
        errors.append('Responsable introuvable.')

    values = dict(
        nom=nom,
        adresse=request.form.get('adresse', '').strip() or None,
        telephone=request.form.get('telephone', '').strip()[:20] or None,
        email=email or None,
        localisation=request.form.get('localisation', '').strip()[:200] or None,
        categorie=categorie[:50],
        responsable_id=responsable_id,
    )
    couleur = request.form.get('couleur')
    if couleur:
        values['couleur'] = safe_color(couleur, pdv.couleur if pdv else '#10b981')
    return values, errors


@pdv_bp.route('/')
@login_required
def liste():
    if not current_user.has_permission('pdv.voir'):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('tickets.tableau_bord'))

    pdvs = PointDeVente.query.order_by(PointDeVente.nom).all()
    return render_template('pdv/liste.html', pdvs=pdvs, categories=_categories(pdvs),
                           themes=referentiels.get_themes(), can_configure=_can_configure())


@pdv_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau():
    if not current_user.has_permission('pdv.creer'):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('pdv.liste'))

    if request.method == 'POST':
        values, errors = _read_pdv_form()
        if errors:
            for msg in errors:
                flash(msg, 'danger')
        else:
            values.setdefault('couleur', (referentiels.get_themes() or [{'couleur': '#10b981'}])[0]['couleur'])
            nouveau_pdv = PointDeVente(**values)
            try:
                referentiels.register_category(values['categorie'])
                db.session.add(nouveau_pdv)
                db.session.commit()
                flash(f"Point de vente '{nouveau_pdv.nom}' créé avec succès.", "success")
                return redirect(url_for('pdv.detail', id=nouveau_pdv.id))
            except IntegrityError:
                db.session.rollback()
                flash('Un point de vente portant ce nom existe déjà.', 'danger')

    utilisateurs = sorted(
        Utilisateur.query.filter_by(actif=True).all(),
        key=lambda u: (u.nom_complet or '').strip().upper()
    )
    return render_template('pdv/formulaire.html', utilisateurs=utilisateurs, categories=_categories(),
                           themes=referentiels.get_themes())


@pdv_bp.route('/<string:id>')
@login_required
def detail(id):
    if not current_user.has_permission('pdv.voir'):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('pdv.liste'))

    pdv = PointDeVente.query.get_or_404(id)
    # Exclure les comptes magasin et le responsable actuel de la liste des employés sélectionnables
    utilisateurs = sorted(
        [u for u in Utilisateur.query.filter_by(actif=True).all()
         if u.prenom != 'Store Account' and not (u.nom_complet or '').startswith('Store Account')
         and (not pdv.responsable_id or u.id != pdv.responsable_id)],
        key=lambda u: (u.nom_complet or '').strip().upper()
    )
    from models import Departement
    departements_list = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()
    pdvs_list = PointDeVente.query.filter_by(actif=True).order_by(PointDeVente.nom).all()
    return render_template('pdv/detail.html', pdv=pdv, utilisateurs=utilisateurs,
                           departements_list=departements_list, pdvs_list=pdvs_list)


@pdv_bp.route('/<string:id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier(id):
    if not _can_edit():
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('pdv.detail', id=id))

    pdv = PointDeVente.query.get_or_404(id)

    if request.method == 'POST':
        values, errors = _read_pdv_form(pdv)
        if errors:
            for msg in errors:
                flash(msg, 'danger')
        else:
            for key, value in values.items():
                setattr(pdv, key, value)
            try:
                referentiels.register_category(values['categorie'])
                db.session.commit()
                flash("Point de vente mis à jour.", "success")
                return redirect(url_for('pdv.detail', id=id))
            except IntegrityError:
                db.session.rollback()
                flash('Un point de vente portant ce nom existe déjà.', 'danger')

    utilisateurs = Utilisateur.query.filter_by(actif=True).all()
    return render_template('pdv/formulaire.html', pdv=pdv, utilisateurs=utilisateurs, categories=_categories(),
                           themes=referentiels.get_themes())


@pdv_bp.route('/<string:id>/equipement/nouveau', methods=['POST'])
@login_required
def ajouter_equipement(id):
    if not current_user.has_permission('equipements.gerer'):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('pdv.detail', id=id))

    pdv = PointDeVente.query.get_or_404(id)

    type_equipement = request.form.get('type_equipement', '').strip()
    statut = request.form.get('statut', 'actif')
    if not type_equipement:
        flash("Le type d'équipement est obligatoire.", "danger")
        return redirect(url_for('pdv.detail', id=id))
    if statut not in EQUIPEMENT_STATUTS:
        statut = 'actif'

    # Un numéro de série vide ne doit pas entrer en conflit avec la contrainte d'unicité
    numero_serie = request.form.get('numero_serie', '').strip() or None
    if numero_serie and Equipement.query.filter_by(numero_serie=numero_serie).first():
        flash("Un équipement avec ce numéro de série existe déjà.", "danger")
        return redirect(url_for('pdv.detail', id=id))

    equip = Equipement(
        pdv_id=pdv.id,
        type_equipement=type_equipement[:50],
        marque=request.form.get('marque', '').strip()[:100] or None,
        modele=request.form.get('modele', '').strip()[:100] or None,
        numero_serie=numero_serie[:100] if numero_serie else None,
        adresse_ip=request.form.get('adresse_ip', '').strip()[:50] or None,
        statut=statut,
        notes=request.form.get('notes', '').strip() or None,
        date_installation=datetime.utcnow()
    )
    try:
        db.session.add(equip)
        db.session.commit()
        flash(f"Équipement '{equip.type_equipement}' ajouté avec succès.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Impossible d'ajouter l'équipement (numéro de série déjà utilisé).", "danger")
    return redirect(url_for('pdv.detail', id=id))


@pdv_bp.route('/equipement/<string:equip_id>/supprimer', methods=['POST'])
@login_required
def supprimer_equipement(equip_id):
    equip = Equipement.query.get_or_404(equip_id)
    if not current_user.has_permission('equipements.gerer'):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('pdv.detail', id=equip.pdv_id))

    pdv_id = equip.pdv_id
    db.session.delete(equip)
    db.session.commit()
    flash("Équipement supprimé.", "success")
    return redirect(url_for('pdv.detail', id=pdv_id))


@pdv_bp.route('/<string:id>/employe/ajouter', methods=['POST'])
@login_required
def ajouter_employe(id):
    if not current_user.has_permission('pdv.gerer_employes'):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('pdv.detail', id=id))

    pdv = PointDeVente.query.get_or_404(id)
    user = db.session.get(Utilisateur, request.form.get('utilisateur_id') or '')

    if user:
        user.pdv_id = pdv.id
        if user.departement and user.departement.code in ['OP', 'Opérationnel']:
            user.departement_id = None
        db.session.commit()
        flash(f"L'employé {user.nom_complet} a été assigné au PDV '{pdv.nom}'.", "success")
    else:
        flash("Utilisateur introuvable.", "danger")

    return redirect(url_for('pdv.detail', id=id))


@pdv_bp.route('/<string:id>/employe/retirer/<string:user_id>', methods=['POST'])
@login_required
def retirer_employe(id, user_id):
    if not current_user.has_permission('pdv.gerer_employes'):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('pdv.detail', id=id))

    user = db.session.get(Utilisateur, user_id)
    if user and user.pdv_id == id:
        user.pdv_id = None
        db.session.commit()
        flash("L'employé a été retiré de ce PDV.", "success")

    return redirect(url_for('pdv.detail', id=id))


@pdv_bp.route('/<string:id>/couleur', methods=['POST'])
@login_required
def changer_couleur(id):
    if not _can_edit():
        return jsonify({'success': False, 'message': 'Non autorisé'}), 403
    pdv = PointDeVente.query.get_or_404(id)
    data = request.get_json(silent=True) or {}
    couleur = data.get('couleur') or request.form.get('couleur')
    safe = safe_color(couleur, None) if couleur else None
    if safe:
        pdv.couleur = safe
        db.session.commit()
        return jsonify({'success': True, 'couleur': pdv.couleur})
    return jsonify({'success': False, 'message': 'Couleur invalide'}), 400


# ─── Référentiels : catégories et palette de thèmes (stockés en base) ─────────

def _can_configure():
    return current_user.has_permission('pdv.referentiels')


def _config_denied():
    flash("Accès non autorisé.", "danger")
    return redirect(url_for('pdv.liste'))


def _back_to_config():
    return redirect(url_for('pdv.gerer_referentiels'))


@pdv_bp.route('/referentiels')
@login_required
def gerer_referentiels():
    if not _can_configure():
        return _config_denied()
    usage = dict(db.session.query(PointDeVente.categorie, db.func.count(PointDeVente.id))
                 .group_by(PointDeVente.categorie).all())
    theme_usage = dict(db.session.query(PointDeVente.couleur, db.func.count(PointDeVente.id))
                       .group_by(PointDeVente.couleur).all())
    return render_template('pdv/referentiels.html', categories=referentiels.get_all_categories(),
                           themes=referentiels.get_themes(), usage=usage, theme_usage=theme_usage,
                           icon_keys=referentiels.ICON_KEYS)


def _find(items, key, value):
    return next((i for i in items if str(i.get(key, '')).lower() == (value or '').lower()), None)


@pdv_bp.route('/referentiels/categorie', methods=['POST'])
@login_required
def ajouter_categorie():
    if not _can_configure():
        return _config_denied()
    nom = request.form.get('nom', '').strip()
    description = request.form.get('description', '').strip()[:200]
    icone = request.form.get('icone', 'circle')
    cats = referentiels.get_all_categories()
    if not nom or len(nom) > 50:
        flash("Le nom de la catégorie est obligatoire (50 caractères maximum).", "danger")
    elif icone not in referentiels.ICON_KEYS:
        flash("Icône invalide.", "danger")
    elif _find(cats, 'nom', nom):
        flash("Cette catégorie existe déjà.", "danger")
    else:
        cats.append({'nom': nom, 'description': description, 'icone': icone,
                     'ordre': max([c['ordre'] for c in cats] + [0]) + 1, 'actif': True})
        referentiels.save_categories(cats)
        db.session.commit()
        flash(f"Catégorie « {nom} » ajoutée.", "success")
    return _back_to_config()


@pdv_bp.route('/referentiels/categorie/modifier', methods=['POST'])
@login_required
def modifier_categorie():
    if not _can_configure():
        return _config_denied()
    cats = referentiels.get_all_categories()
    cat = _find(cats, 'nom', request.form.get('nom'))
    if cat is None:
        flash("Catégorie introuvable.", "danger")
        return _back_to_config()
    icone = request.form.get('icone', cat['icone'])
    try:
        ordre = int(request.form.get('ordre', cat['ordre']))
    except (TypeError, ValueError):
        ordre = cat['ordre']
    if icone not in referentiels.ICON_KEYS:
        flash("Icône invalide.", "danger")
        return _back_to_config()
    cat.update(description=request.form.get('description', '').strip()[:200], icone=icone, ordre=ordre,
               actif=request.form.get('actif') == 'on')
    referentiels.save_categories(cats)
    db.session.commit()
    flash(f"Catégorie « {cat['nom']} » mise à jour.", "success")
    return _back_to_config()


@pdv_bp.route('/referentiels/categorie/supprimer', methods=['POST'])
@login_required
def supprimer_categorie():
    if not _can_configure():
        return _config_denied()
    cats = referentiels.get_all_categories()
    cat = _find(cats, 'nom', request.form.get('nom'))
    if cat is None:
        flash("Catégorie introuvable.", "danger")
        return _back_to_config()
    used = PointDeVente.query.filter(db.func.lower(PointDeVente.categorie) == cat['nom'].lower()).count()
    if used:
        flash(f"Impossible de supprimer « {cat['nom']} » : {used} point(s) de vente l'utilisent. Désactivez-la plutôt.", "danger")
    else:
        referentiels.save_categories([c for c in cats if c is not cat])
        db.session.commit()
        flash("Catégorie supprimée.", "success")
    return _back_to_config()


@pdv_bp.route('/referentiels/theme', methods=['POST'])
@login_required
def ajouter_theme():
    if not _can_configure():
        return _config_denied()
    nom = request.form.get('nom', '').strip()
    couleur = request.form.get('couleur', '').strip().lower()
    themes = referentiels.get_themes()
    if not nom or len(nom) > 50:
        flash("Le nom du thème est obligatoire (50 caractères maximum).", "danger")
    elif not is_hex_color(couleur):
        flash("Couleur invalide (format #RRGGBB).", "danger")
    elif _find(themes, 'couleur', couleur):
        flash("Cette couleur est déjà dans la palette.", "danger")
    else:
        themes.append({'nom': nom, 'couleur': couleur, 'ordre': max([t['ordre'] for t in themes] + [0]) + 1})
        referentiels.save_themes(themes)
        db.session.commit()
        flash(f"Thème « {nom} » ajouté à la palette.", "success")
    return _back_to_config()


@pdv_bp.route('/referentiels/theme/supprimer', methods=['POST'])
@login_required
def supprimer_theme():
    if not _can_configure():
        return _config_denied()
    themes = referentiels.get_themes()
    theme = _find(themes, 'couleur', request.form.get('couleur'))
    if theme is None:
        flash("Thème introuvable.", "danger")
    else:
        # Les PDV qui utilisent déjà cette couleur la conservent : seule la proposition dans la palette disparaît
        referentiels.save_themes([t for t in themes if t is not theme])
        db.session.commit()
        flash("Thème retiré de la palette.", "success")
    return _back_to_config()