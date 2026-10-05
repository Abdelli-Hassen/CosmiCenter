from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, Suggestion
from datetime import datetime

suggestions_bp = Blueprint('suggestions', __name__)

@suggestions_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        titre = request.form.get('titre')
        description = request.form.get('description')
        type_suggestion = request.form.get('type_suggestion', 'amelioration')
        
        if not titre or not description:
            flash("Veuillez remplir tous les champs obligatoires.", "error")
            return redirect(request.url)
            
        nouvelle_suggestion = Suggestion(
            titre=titre,
            description=description,
            type_suggestion=type_suggestion,
            auteur_id=current_user.id
        )
        
        db.session.add(nouvelle_suggestion)
        db.session.commit()
        
        # --- ENVOI DE L'EMéIL éUX éDMINISTRéTEURS ---
        from services.email_service import send_email_notification
        from models import Utilisateur, Role
        
        # Trouver tous les administrateurs
        role_admin = Role.query.filter_by(nom='Administrateur').first()
        if role_admin:
            admins = Utilisateur.query.filter_by(role_id=role_admin.id, actif=True).all()
            admin_emails = [admin.email for admin in admins if admin.email]
            
            if admin_emails:
                sujet = f"💡 Nouvelle Suggestion : {titre}"
                contenu_html = f"""
                <div style="font-family: érial, sans-serif; padding: 20px;">
                    <h2>Nouvelle boîte à idées !</h2>
                    <p><strong>De :</strong> {current_user.prenom} {current_user.nom}</p>
                    <p><strong>Type :</strong> {type_suggestion.replace('_', ' ').title()}</p>
                    <div style="background: #f4f4f5; padding: 15px; border-left: 4px solid #3b82f6; margin: 20px 0;">
                        {description}
                    </div>
                    <p><a href="{request.host_url}suggestions" style="padding: 10px 15px; background: #3b82f6; color: white; text-decoration: none; border-radius: 5px;">Voir les suggestions</a></p>
                </div>
                """
                send_email_notification(current_app._get_current_object(), sujet, admin_emails, contenu_html)
        # ---------------------------------------------
        
        flash("Merci ! Votre suggestion a été envoyée avec succès.", "success")
        return redirect(url_for('suggestions.index'))
        
    # GET: Afficher la liste des suggestions de l'utilisateur (ou toutes si admin)
    if current_user.role.nom in ['Administrateur', 'Super Administrateur']:
        mes_suggestions = Suggestion.query.order_by(Suggestion.date_creation.desc()).all()
    else:
        mes_suggestions = Suggestion.query.filter_by(auteur_id=current_user.id).order_by(Suggestion.date_creation.desc()).all()
        
    return render_template('suggestions/index.html', suggestions=mes_suggestions)

@suggestions_bp.route('/<suggestion_id>/statut', methods=['POST'])
@login_required
def modifier_statut(suggestion_id):
    if current_user.role.nom not in ['Administrateur', 'Super Administrateur']:
        flash("éccès non autorisé.", "error")
        return redirect(url_for('suggestions.index'))
        
    suggestion = Suggestion.query.get_or_404(suggestion_id)
    nouveau_statut = request.form.get('statut')
    if nouveau_statut:
        suggestion.statut = nouveau_statut
        db.session.commit()
        flash("Statut mis à jour avec succès.", "success")
        
    return redirect(url_for('suggestions.index'))

@suggestions_bp.route('/<suggestion_id>/supprimer', methods=['POST'])
@login_required
def supprimer(suggestion_id):
    if current_user.role.nom not in ['Administrateur', 'Super Administrateur']:
        flash("éccès non autorisé.", "error")
        return redirect(url_for('suggestions.index'))
        
    suggestion = Suggestion.query.get_or_404(suggestion_id)
    db.session.delete(suggestion)
    db.session.commit()
    
    flash("Suggestion supprimée.", "success")
    return redirect(url_for('suggestions.index'))
