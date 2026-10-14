from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, PointDeVente, Equipement, Utilisateur, Ticket
from datetime import datetime

pdv_bp = Blueprint('pdv', __name__)

@pdv_bp.route('/')
@login_required
def liste():
    if not current_user.has_permission('pdv.voir'):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('tickets.tableau_bord'))
    
    pdvs = PointDeVente.query.order_by(PointDeVente.nom).all()
    # Default presets + all categories stored in DB
    db_cats = [p.categorie for p in pdvs if p.categorie]
    categories = list(dict.fromkeys(['Urbain', 'Express', 'Mall'] + [c for c in db_cats if c and c not in ['Urbain', 'Express', 'Mall']]))
    return render_template('pdv/liste.html', pdvs=pdvs, categories=categories)

@pdv_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau():
    if not (current_user.has_permission('pdv.creer') or current_user.has_permission('pdv.gerer')):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('pdv.liste'))
    
    if request.method == 'POST':
        nom = request.form.get('nom')
        adresse = request.form.get('adresse')
        telephone = request.form.get('telephone')
        email = request.form.get('email')
        localisation = request.form.get('localisation')
        
        # Category: preset or custom
        cat_select = request.form.get('categorie')
        cat_custom = request.form.get('categorie_custom', '').strip()
        categorie = cat_custom if (cat_select == 'custom' and cat_custom) else (cat_select or 'Urbain')
        
        responsable_id = request.form.get('responsable_id') or None
        couleur = request.form.get('couleur') or '#10b981'
        
        nouveau_pdv = PointDeVente(
            nom=nom,
            adresse=adresse,
            telephone=telephone,
            email=email,
            localisation=localisation,
            categorie=categorie,
            responsable_id=responsable_id,
            couleur=couleur
        )
        db.session.add(nouveau_pdv)
        db.session.commit()
        flash(f"Point de vente '{nom}' créé avec succès.", "success")
        return redirect(url_for('pdv.detail', id=nouveau_pdv.id))
        
    utilisateurs = sorted(
        Utilisateur.query.filter_by(actif=True).all(),
        key=lambda u: (u.nom_complet or '').strip().upper()
    )
    db_cats = [p.categorie for p in PointDeVente.query.all() if p.categorie]
    categories = list(dict.fromkeys(['Urbain', 'Express', 'Mall'] + [c for c in db_cats if c and c not in ['Urbain', 'Express', 'Mall']]))
    return render_template('pdv/formulaire.html', utilisateurs=utilisateurs, categories=categories)

@pdv_bp.route('/<string:id>')
@login_required
def detail(id):
    if not current_user.has_permission('pdv.voir'):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('pdv.liste'))
        
    pdv = PointDeVente.query.get_or_404(id)
    # Exclude Store Accounts and the current responsable from the selectable employees list
    utilisateurs = sorted(
        [u for u in Utilisateur.query.filter_by(actif=True).all()
         if u.prenom != 'Store Account' and not (u.nom_complet or '').startswith('Store Account')
         and (not pdv.responsable_id or u.id != pdv.responsable_id)],
        key=lambda u: (u.nom_complet or '').strip().upper()
    )
    from models import Departement
    departements_list = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()
    pdvs_list = PointDeVente.query.filter_by(actif=True).order_by(PointDeVente.nom).all()
    return render_template('pdv/detail.html', pdv=pdv, utilisateurs=utilisateurs, departements_list=departements_list, pdvs_list=pdvs_list)

@pdv_bp.route('/<string:id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier(id):
    if not (current_user.has_permission('pdv.modifier') or current_user.has_permission('pdv.gerer')):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('pdv.detail', id=id))
        
    pdv = PointDeVente.query.get_or_404(id)
    
    if request.method == 'POST':
        pdv.nom = request.form.get('nom')
        pdv.adresse = request.form.get('adresse')
        pdv.telephone = request.form.get('telephone')
        pdv.email = request.form.get('email')
        pdv.localisation = request.form.get('localisation')
        
        # Category: preset or custom
        cat_select = request.form.get('categorie')
        cat_custom = request.form.get('categorie_custom', '').strip()
        pdv.categorie = cat_custom if (cat_select == 'custom' and cat_custom) else (cat_select or 'Urbain')
        
        pdv.responsable_id = request.form.get('responsable_id') or None
        if request.form.get('couleur'):
            pdv.couleur = request.form.get('couleur')
        
        db.session.commit()
        flash("Point de vente mis à jour.", "success")
        return redirect(url_for('pdv.detail', id=id))
        
    utilisateurs = Utilisateur.query.filter_by(actif=True).all()
    db_cats = [p.categorie for p in PointDeVente.query.all() if p.categorie]
    categories = list(dict.fromkeys(['Urbain', 'Express', 'Mall'] + [c for c in db_cats if c and c not in ['Urbain', 'Express', 'Mall']]))
    return render_template('pdv/formulaire.html', pdv=pdv, utilisateurs=utilisateurs, categories=categories)

@pdv_bp.route('/<string:id>/equipement/nouveau', methods=['POST'])
@login_required
def ajouter_equipement(id):
    if not current_user.has_permission('equipements.gerer'):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('pdv.detail', id=id))
        
    pdv = PointDeVente.query.get_or_404(id)
    
    type_equipement = request.form.get('type_equipement')
    marque = request.form.get('marque')
    modele = request.form.get('modele')
    numero_serie = request.form.get('numero_serie')
    adresse_ip = request.form.get('adresse_ip')
    statut = request.form.get('statut', 'actif')
    notes = request.form.get('notes')
    
    equip = Equipement(
        pdv_id=pdv.id,
        type_equipement=type_equipement,
        marque=marque,
        modele=modele,
        numero_serie=numero_serie,
        adresse_ip=adresse_ip,
        statut=statut,
        notes=notes,
        date_installation=datetime.utcnow()
    )
    db.session.add(equip)
    db.session.commit()
    flash(f"Équipement '{type_equipement}' ajouté avec succès.", "success")
    return redirect(url_for('pdv.detail', id=id))

@pdv_bp.route('/equipement/<string:equip_id>/supprimer', methods=['POST'])
@login_required
def supprimer_equipement(equip_id):
    if not current_user.has_permission('equipements.gerer'):
        flash("Accès non autorisé.", "danger")
        return redirect(request.referrer)
        
    equip = Equipement.query.get_or_404(equip_id)
    pdv_id = equip.pdv_id
    db.session.delete(equip)
    db.session.commit()
    flash("Équipement supprimé.", "success")
    return redirect(url_for('pdv.detail', id=pdv_id))

@pdv_bp.route('/<string:id>/employe/ajouter', methods=['POST'])
@login_required
def ajouter_employe(id):
    if not (current_user.has_permission('pdv.modifier') or current_user.has_permission('pdv.gerer')):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('pdv.detail', id=id))
        
    pdv = PointDeVente.query.get_or_404(id)
    user_id = request.form.get('utilisateur_id')
    user = Utilisateur.query.get(user_id)
    
    if user:
        user.pdv_id = pdv.id
        if user.departement and user.departement.code in ['OP', 'Opérationnel']:
            user.departement_id = None
        db.session.commit()
        flash(f"L'employé {user.nom_complet} a été assigné au PDV '{pdv.nom}'.", "success")
        
    return redirect(url_for('pdv.detail', id=id))

@pdv_bp.route('/<string:id>/employe/retirer/<string:user_id>', methods=['POST'])
@login_required
def retirer_employe(id, user_id):
    if not (current_user.has_permission('pdv.modifier') or current_user.has_permission('pdv.gerer')):
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('pdv.detail', id=id))
        
    user = Utilisateur.query.get(user_id)
    if user and user.pdv_id == id:
        user.pdv_id = None
        db.session.commit()
        flash("L'employé a été retiré de ce PDV.", "success")
        
    return redirect(url_for('pdv.detail', id=id))

@pdv_bp.route('/<string:id>/couleur', methods=['POST'])
@login_required
def changer_couleur(id):
    if not (current_user.has_permission('pdv.modifier') or current_user.has_permission('pdv.gerer')):
        return jsonify({'success': False, 'message': 'Non autorisé'}), 403
    pdv = PointDeVente.query.get_or_404(id)
    data = request.get_json(silent=True) or {}
    couleur = data.get('couleur') or request.form.get('couleur')
    if couleur:
        pdv.couleur = couleur
        db.session.commit()
        return jsonify({'success': True, 'couleur': pdv.couleur})
    return jsonify({'success': False, 'message': 'Couleur invalide'}), 400
